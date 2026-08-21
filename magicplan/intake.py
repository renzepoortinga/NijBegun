"""Veilige, offline MagicPlan-intake uit een controleerbaar importpakket.

Het pakket is een ZIP met manifest.json, statistics.csv, report.txt (of report.pdf)
en geometry.json. Preview en merge zijn pure functies; netwerkverkeer hoort hier niet.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import zipfile
import dataclasses

from magicplan.form_fingerprint import snapshot_fingerprint
from magicplan.report_parser import parse as parse_report_pdf, parse_text
from magicplan.statistics_csv import build_dossier
from core.polygon import oppervlakte as polygon_oppervlakte, zelfsnijdend

VERPLICHT = {"manifest.json", "statistics.csv", "geometry.json"}
MANIFEST_SCHEMA = "nijbegun-magicplan-intake/1"
GEOMETRY_SCHEMA = "nijbegun-magicplan-geometry/1"
# Numerieke conditioneringsgrens, geen woning-/NTA-norm. Verhoudingen boven 10^6 maken een
# 2D-vlak praktisch lijnvormig en laten extreme maar eindige IEEE-754-invoer door area-checks glippen.
MAX_BBOX_ASPECT = 1_000_000.0
MAX_BBOX_AREA_FACTOR = 1_000_000.0
BEHOUD_BELEID = {
    "handmatige_daken": "behouden",
    "fotos": "behouden",
    "maatregelen": "behouden",
    "vabi_resultaten": "behouden",
}


class IntakeError(ValueError):
    pass


def _norm(v):
    return re.sub(r"[^a-z0-9]", "", str(v or "").lower())


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _veilig_leden(zf):
    namen = set()
    totaal = 0
    for info in zf.infolist():
        naam = info.filename.replace("\\", "/")
        if naam.startswith("/") or ".." in naam.split("/") or ":" in naam:
            raise IntakeError("Onveilig pad in importpakket: %s" % info.filename)
        if not info.is_dir():
            if naam in namen:
                raise IntakeError("Dubbele bestandsnaam in importpakket")
            totaal += info.file_size
            if totaal > 100 * 1024 * 1024:
                raise IntakeError("Importpakket is uitgepakt groter dan 100 MB")
            namen.add(naam)
    return namen


def _identiteit(dos):
    i = dos.identificatie
    return {"bag_vboid": i.bag_vboid, "postcode": i.postcode,
            "huisnummer": i.huisnummer, "straat": i.straat, "plaats": i.plaats}


def identiteit_sleutel(obj):
    i = obj.identificatie if hasattr(obj, "identificatie") else obj
    bag = _norm(getattr(i, "bag_vboid", "") if not isinstance(i, dict) else i.get("bag_vboid"))
    if bag:
        return "bag:" + bag
    get = (lambda k: i.get(k, "")) if isinstance(i, dict) else (lambda k: getattr(i, k, ""))
    pc, nr = _norm(get("postcode")), _norm(get("huisnummer"))
    return "adres:%s:%s" % (pc, nr) if pc and nr else ""


def _identity_dict(obj):
    if hasattr(obj, "identificatie"):
        obj = obj.identificatie
    if isinstance(obj, dict):
        return {k: str(obj.get(k) or "").strip() for k in
                ("bag_vboid", "postcode", "huisnummer", "straat", "plaats")}
    return {k: str(getattr(obj, k, "") or "").strip() for k in
            ("bag_vboid", "postcode", "huisnummer", "straat", "plaats")}


def _adres_sleutel(i):
    pc, nr = _norm(i.get("postcode")), _norm(i.get("huisnummer"))
    return (pc, nr) if pc and nr else None


def valideer_identiteiten(bronnen):
    """Alle aanwezige BAG-id's én complete adressen moeten onderling coherent zijn.

    BAG wint dus niet stil van een tegensprekend adres. Een bron mag een van beide missen;
    ontbrekende waarden worden pas na deze controle aangevuld.
    """
    items = [(naam, _identity_dict(obj)) for naam, obj in bronnen if obj is not None]
    bags = {(_norm(i["bag_vboid"])) for _, i in items if _norm(i["bag_vboid"])}
    adressen = {_adres_sleutel(i) for _, i in items if _adres_sleutel(i)}
    if len(bags) > 1:
        raise IntakeError("BAG-identiteit komt niet overeen tussen de pakketonderdelen")
    if len(adressen) > 1:
        raise IntakeError("Adresidentiteit komt niet overeen tussen de pakketonderdelen")
    if not bags and not adressen:
        raise IntakeError("Pakketidentiteit mist BAG-id of postcode + huisnummer")
    # Het manifest is de koppelpin. Een bron met alleen een BAG-id kan niet veilig aan een
    # manifest met alleen een adres worden gekoppeld (of andersom), ook als er geen conflict is.
    manifest = items[0][1]
    m_bag, m_adres = _norm(manifest["bag_vboid"]), _adres_sleutel(manifest)
    for naam, ident in items[1:]:
        bag, adres = _norm(ident["bag_vboid"]), _adres_sleutel(ident)
        if (bag or adres) and not ((bag and m_bag) or (adres and m_adres)):
            raise IntakeError("Identiteit van %s is niet verifieerbaar tegen het manifest" % naam)
    return items


def _valideer_geometry(geo, verdiepingen, project_id):
    if not isinstance(geo, dict) or geo.get("schema") != GEOMETRY_SCHEMA:
        raise IntakeError("geometry.json heeft een onbekend schema")
    if not isinstance(geo.get("project_id"), str) or geo["project_id"] != project_id:
        raise IntakeError("Geometrie en manifest hebben een verschillend project-id")
    if geo.get("unit") != "m":
        raise IntakeError("geometry.json moet unit 'm' voor metrische contour_m-coördinaten bevatten")
    if geo.get("area_basis") != "VloerInfo.oppervlakte_m2":
        raise IntakeError("geometry.json mist de ondersteunde metrische area_basis")
    contouren = geo.get("floor_contours")
    if not isinstance(contouren, dict):
        raise IntakeError("geometry.floor_contours moet een object zijn")
    bekend = {v.naam: v for v in verdiepingen}
    for naam, poly in contouren.items():
        if not isinstance(naam, str) or naam not in bekend:
            raise IntakeError("Geometrie verwijst naar een onbekende verdieping")
        if not isinstance(poly, list) or len(poly) < 3:
            raise IntakeError("Een grondvlakcontour moet minimaal drie punten hebben")
        schoon = []
        for punt in poly:
            if (not isinstance(punt, list) or len(punt) != 2
                    or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x)
                           for x in punt)):
                raise IntakeError("Grondvlakcoördinaten moeten eindige getallenparen zijn")
            schoon.append([float(punt[0]), float(punt[1])])
        if len({tuple(p) for p in schoon}) != len(schoon):
            raise IntakeError("Grondvlakcontour bevat dubbele punten")
        if zelfsnijdend(schoon):
            raise IntakeError("Grondvlakcontour kruist zichzelf")
        area = polygon_oppervlakte(schoon)
        if area < 1e-6:
            raise IntakeError("Grondvlakcontour heeft geen oppervlakte")
        # Het bestaande assemble-pad normaliseert contour_m naar oorsprong (0,0). De package-route
        # volgt exact dat metrische contract; zo lekken pixel-/wereldcoördinaten niet stil door.
        if min(p[0] for p in schoon) != 0.0 or min(p[1] for p in schoon) != 0.0:
            raise IntakeError("Metrische grondvlakcontour moet op oorsprong (0,0) zijn genormaliseerd")
        breedte = max(p[0] for p in schoon) - min(p[0] for p in schoon)
        diepte = max(p[1] for p in schoon) - min(p[1] for p in schoon)
        bbox_area = breedte * diepte
        if (not all(math.isfinite(x) and x > 0 for x in (breedte, diepte, bbox_area))
                or max(breedte, diepte) / min(breedte, diepte) > MAX_BBOX_ASPECT
                or bbox_area / area > MAX_BBOX_AREA_FACTOR):
            raise IntakeError("Metrische grondvlakcontour is numeriek te slecht geconditioneerd")
        vloer_area = float(bekend[naam].oppervlakte_m2 or 0)
        if vloer_area <= 0 or round(area, 2) != round(vloer_area, 2):
            raise IntakeError("Contour-oppervlakte komt niet overeen met VloerInfo.oppervlakte_m2")
        contouren[naam] = schoon
    return contouren


def _lees_pakket(pad, werkmap):
    with open(pad, "rb") as f:
        if f.read(4)[:2] != b"PK":
            raise IntakeError("Bestand is geen ZIP-importpakket")
    with zipfile.ZipFile(pad) as zf:
        namen = _veilig_leden(zf)
        ontbreekt = VERPLICHT - namen
        reports = {"report.txt", "report.pdf"} & namen
        if ontbreekt or len(reports) != 1:
            raise IntakeError("Importpakket mist: %s" % ", ".join(sorted(ontbreekt or {"report.txt of report.pdf"})))
        try:
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            raise IntakeError("manifest.json is geen geldige UTF-8 JSON")
        if not isinstance(manifest, dict) or manifest.get("schema") != MANIFEST_SCHEMA:
            raise IntakeError("manifest.json heeft een onbekend schema")
        if not isinstance(manifest.get("identity"), dict):
            raise IntakeError("manifest.identity moet een object zijn")
        for naam, verwacht in (manifest.get("sha256") or {}).items():
            if (not isinstance(naam, str) or not isinstance(verwacht, str)
                    or not re.fullmatch(r"[0-9a-f]{64}", verwacht)
                    or naam not in namen or _sha256(zf.read(naam)) != verwacht):
                raise IntakeError("Bestandscontrole mislukt voor %s" % naam)
        os.makedirs(werkmap, exist_ok=True)
        csv_pad = os.path.join(werkmap, "statistics.csv")
        geo_pad = os.path.join(werkmap, "geometry.json")
        csv_data = zf.read("statistics.csv")
        geo_data = zf.read("geometry.json")
        try:
            csv_text = csv_data.decode("utf-8-sig")
            json.loads(geo_data.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            raise IntakeError("Statistics of geometrie heeft niet het verwachte bestandstype")
        if "PLAN ATTRIBUTES" not in csv_text or "FLOOR ATTRIBUTES" not in csv_text:
            raise IntakeError("statistics.csv is geen MagicPlan Statistics-export")
        with open(csv_pad, "wb") as f: f.write(csv_data)
        with open(geo_pad, "wb") as f: f.write(geo_data)
        if "report.txt" in namen:
            try:
                antwoorden, _ = parse_text(zf.read("report.txt").decode("utf-8"))
            except UnicodeError:
                raise IntakeError("report.txt is geen UTF-8 tekstbestand")
        else:
            if not zf.read("report.pdf").startswith(b"%PDF-"):
                raise IntakeError("report.pdf is geen PDF-bestand")
            rp = os.path.join(werkmap, "report.pdf")
            with open(rp, "wb") as f: f.write(zf.read("report.pdf"))
            antwoorden, _ = parse_report_pdf(rp)
    return manifest, csv_pad, geo_pad, antwoorden


def bouw_preview(pakket_pad, huidig, werkmap, verwacht_project_id=""):
    manifest, csv_pad, geo_pad, rapport = _lees_pakket(pakket_pad, werkmap)
    if (not isinstance(manifest.get("project_id"), str)
            or not re.fullmatch(r"[A-Za-z0-9._-]{1,200}", manifest["project_id"])):
        raise IntakeError("manifest.json mist project_id")
    if verwacht_project_id and str(manifest["project_id"]) != str(verwacht_project_id):
        raise IntakeError("MagicPlan-project-id wijkt af: pakket %s, dossier %s" %
                          (manifest["project_id"], verwacht_project_id))
    fp = str(manifest.get("form_fingerprint") or "")
    if fp != snapshot_fingerprint():
        raise IntakeError("Formulierfingerprint wijkt af: pakket %s, verwacht %s" % (fp or "leeg", snapshot_fingerprint()))
    mi = manifest.get("identity") or {}
    stats_dos, _ = build_dossier(csv_pad)
    rapport_i = {"bag_vboid": rapport.get("bag_vboid", ""), "postcode": rapport.get("postcode", ""),
                 "huisnummer": rapport.get("huisnummer", ""), "straat": "", "plaats": ""}
    valideer_identiteiten((("manifest", mi), ("Statistics", stats_dos), ("rapport", rapport_i),
                           ("huidig dossier", huidig)))
    nieuw, notes = build_dossier(csv_pad, straat=mi.get("straat", ""), huisnummer=mi.get("huisnummer", ""),
                                 postcode=mi.get("postcode", ""), plaats=mi.get("plaats", ""),
                                 woningtype=mi.get("woningtype", ""))
    # Statistics is inhoudelijk leidend; alleen ontbrekende identiteit komt uit het gecontroleerde manifest.
    for attr in ("bag_vboid", "postcode", "huisnummer", "straat", "plaats", "woningtype"):
        if not getattr(nieuw.identificatie, attr, "") and mi.get(attr):
            setattr(nieuw.identificatie, attr, mi[attr])
    with open(geo_pad, encoding="utf-8") as f:
        geo = json.load(f)
    contouren = _valideer_geometry(geo, nieuw.geometrie.vloeren, manifest["project_id"])
    for vloer in nieuw.geometrie.vloeren:
        if vloer.naam in contouren:
            vloer.contour_m = contouren[vloer.naam]
    nieuw.meta.magicplan_form_fingerprint = fp
    acties = groepeer_acties(nieuw, notes)
    diff = maak_diff(huidig, nieuw)
    with open(pakket_pad, "rb") as f:
        pakket_hash = _sha256(f.read())
    return {"manifest": manifest, "nieuw": nieuw, "notes": notes, "acties": acties,
            "diff": diff, "pakket_sha256": pakket_hash}


def groepeer_acties(dos, notes=()):
    groepen = {k: [] for k in ("identiteit", "schil", "dak", "installaties", "bewijs")}
    i = dos.identificatie
    if not i.bag_vboid: groepen["identiteit"].append("BAG-verblijfsobject-id controleren en invullen.")
    if any(not s.orientatie for s in dos.schil if s.type in ("gevel", "kozijn")):
        groepen["schil"].append("Oriëntaties van gevels en kozijnen controleren.")
    echte_daken = [s for s in dos.schil if s.type == "dak" and s.bron != "magicplan-dak-fallback"]
    if not echte_daken: groepen["dak"].append("Dakgeometrie in de webapp-wizard vastleggen en controleren.")
    inst = dos.installaties
    if not inst.verwarming.type_opwekker: groepen["installaties"].append("Warmteopwekker controleren en aanvullen.")
    if not dos.fotos: groepen["bewijs"].append("Bewijsfoto's en eventuele kwaliteitsverklaringen toevoegen.")
    for note in notes or ():
        tekst = str(note)
        laag = tekst.lower()
        groep = "dak" if "dak" in laag else "installaties" if any(x in laag for x in ("verwarm", "ventil", "tapwater", "pv")) else "schil"
        if tekst not in groepen[groep]: groepen[groep].append(tekst)
    return groepen


def merge(huidig, nieuw):
    """Importgroepen vervangen; adviseurswerk en Vabi-uitkomsten expliciet behouden."""
    uit = copy.deepcopy(nieuw)
    nieuwe_ids = {s.id for s in uit.schil}
    wizard = [copy.deepcopy(s) for s in huidig.schil
              if s.bron == "webapp-wizard" and s.id not in nieuwe_ids]
    if wizard:
        # Statistics kan alleen een footprint-placeholder leveren. Die mag niet naast het
        # behouden, handmatig ingemeten dak blijven staan (taak 014-contract).
        uit.schil = [s for s in uit.schil
                     if not (s.type == "dak" and s.bron == "magicplan-dak-fallback")]
        uit.schil.extend(wizard)
    uit.fotos = copy.deepcopy(huidig.fotos)
    uit.maatregelen = copy.deepcopy(huidig.maatregelen)
    uit.haalbaarheid = copy.deepcopy(huidig.haalbaarheid)
    uit.berekening = copy.deepcopy(huidig.berekening)
    uit.adviseur = copy.deepcopy(huidig.adviseur)
    return uit


def _installatie_count(dos):
    i = dos.installaties
    return (int(bool(i.verwarming.type_opwekker or i.verwarming.systeem))
            + len(i.verwarming_extra) + int(bool(i.tapwater.type_toestel or i.tapwater.type_installatie))
            + len(i.tapwater_extra) + int(bool(i.koeling.aanwezig)) + len(i.koeling_extra)
            + len(i.zonne_energie) + int(bool(dos.ventilatie.systeem)))


def maak_diff(huidig, nieuw):
    """Diff van de daadwerkelijke merge-uitkomst, niet van de ruwe import."""
    na = merge(huidig, nieuw)
    oud_ids, nieuw_ids = {s.id for s in huidig.schil}, {s.id for s in na.schil}
    wizard_voor = sum(s.bron == "webapp-wizard" for s in huidig.schil)
    wizard_na = sum(s.bron == "webapp-wizard" for s in na.schil)
    return {
        "identiteit": {"beleid": "vervangen na identiteitscontrole",
                       "voor": _identiteit(huidig), "na": _identiteit(na)},
        "schil": {"beleid": "vervangen; handmatige daken/dakkapellen behouden",
                  "voor": len(huidig.schil), "import": len(nieuw.schil), "na": len(na.schil),
                  "wizard_voor": wizard_voor, "wizard_na": wizard_na,
                  "toegevoegd": sorted(nieuw_ids - oud_ids), "verwijderd": sorted(oud_ids - nieuw_ids)},
        "installaties": {"beleid": "vervangen uit Statistics", "voor": _installatie_count(huidig),
                         "na": _installatie_count(na)},
        "fotos": {"beleid": "behouden", "voor": len(huidig.fotos), "na": len(na.fotos)},
        "maatregelen": {"beleid": "behouden", "voor": len(huidig.maatregelen), "na": len(na.maatregelen)},
        "vabi_resultaten": {"beleid": "behouden", "voor": dataclasses.asdict(huidig.berekening),
                            "na": dataclasses.asdict(na.berekening)},
    }
