"""Veilige, offline MagicPlan-intake uit een controleerbaar importpakket.

Het pakket is een ZIP met manifest.json, statistics.csv, report.txt (of report.pdf)
en geometry.json. Preview en merge zijn pure functies; netwerkverkeer hoort hier niet.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import zipfile

from magicplan.form_fingerprint import snapshot_fingerprint
from magicplan.report_parser import parse as parse_report_pdf, parse_text
from magicplan.statistics_csv import build_dossier

VERPLICHT = {"manifest.json", "statistics.csv", "geometry.json"}
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


def _lees_pakket(pad, werkmap):
    with zipfile.ZipFile(pad) as zf:
        namen = _veilig_leden(zf)
        ontbreekt = VERPLICHT - namen
        if ontbreekt or not ({"report.txt", "report.pdf"} & namen):
            raise IntakeError("Importpakket mist: %s" % ", ".join(sorted(ontbreekt or {"report.txt of report.pdf"})))
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        for naam, verwacht in (manifest.get("sha256") or {}).items():
            if naam not in namen or _sha256(zf.read(naam)) != verwacht:
                raise IntakeError("Bestandscontrole mislukt voor %s" % naam)
        os.makedirs(werkmap, exist_ok=True)
        csv_pad = os.path.join(werkmap, "statistics.csv")
        geo_pad = os.path.join(werkmap, "geometry.json")
        with open(csv_pad, "wb") as f: f.write(zf.read("statistics.csv"))
        with open(geo_pad, "wb") as f: f.write(zf.read("geometry.json"))
        if "report.txt" in namen:
            antwoorden, _ = parse_text(zf.read("report.txt").decode("utf-8"))
        else:
            rp = os.path.join(werkmap, "report.pdf")
            with open(rp, "wb") as f: f.write(zf.read("report.pdf"))
            antwoorden, _ = parse_report_pdf(rp)
    return manifest, csv_pad, geo_pad, antwoorden


def bouw_preview(pakket_pad, huidig, werkmap, verwacht_project_id=""):
    manifest, csv_pad, geo_pad, rapport = _lees_pakket(pakket_pad, werkmap)
    if not str(manifest.get("project_id") or "").strip():
        raise IntakeError("manifest.json mist project_id")
    if verwacht_project_id and str(manifest["project_id"]) != str(verwacht_project_id):
        raise IntakeError("MagicPlan-project-id wijkt af: pakket %s, dossier %s" %
                          (manifest["project_id"], verwacht_project_id))
    fp = str(manifest.get("form_fingerprint") or "")
    if fp != snapshot_fingerprint():
        raise IntakeError("Formulierfingerprint wijkt af: pakket %s, verwacht %s" % (fp or "leeg", snapshot_fingerprint()))
    mi = manifest.get("identity") or {}
    sleutel = identiteit_sleutel(mi)
    if not sleutel:
        raise IntakeError("Pakketidentiteit mist BAG-id of postcode + huisnummer")
    nieuw, notes = build_dossier(csv_pad, straat=mi.get("straat", ""), huisnummer=mi.get("huisnummer", ""),
                                 postcode=mi.get("postcode", ""), plaats=mi.get("plaats", ""),
                                 woningtype=mi.get("woningtype", ""))
    if identiteit_sleutel(nieuw) != sleutel:
        raise IntakeError("Statistics en manifest horen niet bij dezelfde woning")
    rapp_sleutel = identiteit_sleutel({"bag_vboid": rapport.get("bag_vboid", ""),
                                      "postcode": rapport.get("postcode", ""),
                                      "huisnummer": rapport.get("huisnummer", "")})
    if rapp_sleutel and rapp_sleutel != sleutel:
        raise IntakeError("Rapport en manifest horen niet bij dezelfde woning")
    bestaand = identiteit_sleutel(huidig)
    if bestaand and bestaand != sleutel:
        raise IntakeError("Dit pakket hoort bij %s, het dossier bij %s" % (sleutel, bestaand))
    with open(geo_pad, encoding="utf-8") as f:
        geo = json.load(f)
    if str(geo.get("project_id") or "") != str(manifest["project_id"]):
        raise IntakeError("Geometrie en manifest hebben een verschillend project-id")
    contouren = geo.get("floor_contours") or {}
    for vloer in nieuw.geometrie.vloeren:
        if vloer.naam in contouren:
            vloer.contour_m = contouren[vloer.naam]
    nieuw.meta.magicplan_form_fingerprint = fp
    acties = groepeer_acties(nieuw, notes)
    oud_ids = {s.id for s in huidig.schil}
    nieuw_ids = {s.id for s in nieuw.schil}
    diff = {
        "identiteit": {"voor": _identiteit(huidig), "na": _identiteit(nieuw)},
        "schil": {"voor": len(huidig.schil), "na": len(nieuw.schil),
                  "toegevoegd": sorted(nieuw_ids - oud_ids), "verwijderd": sorted(oud_ids - nieuw_ids)},
        "installaties": "vervangen uit Statistics",
        "behoud": dict(BEHOUD_BELEID),
    }
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
