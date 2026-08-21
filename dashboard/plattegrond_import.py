"""Veilige contractgrens voor plattegrondanalyse uit afbeeldingen.

Dit bestand kiest of benadert geen visionprovider. Het valideert uitsluitend een
providerresultaat en zet dat pas na expliciete adviseursbevestiging om naar canonieke
dossiergeometrie. Een onbetrouwbare schaal levert nooit een afgelezen oppervlakte op.
"""
from __future__ import annotations

import math
import os
from pathlib import Path, PureWindowsPath

from core.dossier import Ruimte, VloerInfo
from dashboard.ventilatieplan import valideer_ruimtepolygonen


FUNCTIES = {
    "verblijfsgebied", "verblijfsruimte", "keuken", "badkamer",
    "toilet", "wasruimte", "verkeer", "overig",
}
BRON_AFGELEZEN = "afgelezen"
BRON_HANDMATIG = "handmatig_gecorrigeerd"
MAATLIJN_TOLERANTIE = 0.02  # 2%: ruimte voor OCR-/pixelafronding, niet voor een andere schaal.


class PlattegrondImportFout(ValueError):
    pass


def _getal(waarde, label, *, nul_toegestaan=False):
    if isinstance(waarde, bool):
        raise PlattegrondImportFout(f"{label} moet een getal zijn.")
    try:
        getal = float(waarde)
    except (TypeError, ValueError):
        raise PlattegrondImportFout(f"{label} moet een getal zijn.") from None
    if not math.isfinite(getal) or (getal < 0 if nul_toegestaan else getal <= 0):
        raise PlattegrondImportFout(f"{label} moet een eindig positief getal zijn.")
    return getal


def _veilige_afbeelding(uploadroot, pad):
    """Resolve en sniff een upload onder de expliciete project-uploadroot."""
    raw = str(pad or "").strip()
    winpad = PureWindowsPath(raw)
    genormaliseerd = raw.replace("\\", "/")
    if (not genormaliseerd or genormaliseerd.startswith("/") or winpad.is_absolute()
            or winpad.drive or ":" in genormaliseerd or ".." in genormaliseerd.split("/")):
        raise PlattegrondImportFout("Afbeeldingspad moet relatief en projectgebonden zijn.")
    suffix = os.path.splitext(genormaliseerd)[1].lower()
    if suffix not in {".jpg", ".jpeg", ".png"}:
        raise PlattegrondImportFout("Alleen JPG- en PNG-plattegronden zijn toegestaan.")
    if uploadroot is None:
        raise PlattegrondImportFout("Een expliciete project-uploadroot is verplicht.")
    try:
        root = Path(uploadroot).resolve(strict=True)
        bestand = (root / Path(*genormaliseerd.split("/"))).resolve(strict=True)
    except (OSError, RuntimeError):
        raise PlattegrondImportFout("Project-uploadroot of plattegrondafbeelding bestaat niet.") from None
    try:
        bestand.relative_to(root)
    except ValueError:
        raise PlattegrondImportFout("Afbeelding valt buiten de project-uploadroot.") from None
    if not bestand.is_file():
        raise PlattegrondImportFout("Plattegrondafbeelding bestaat niet.")
    with bestand.open("rb") as fh:
        kop = fh.read(16)
    werkelijk = "png" if kop.startswith(b"\x89PNG\r\n\x1a\n") else \
        "jpeg" if kop.startswith(b"\xff\xd8\xff") else None
    verwacht = "png" if suffix == ".png" else "jpeg"
    if werkelijk != verwacht:
        raise PlattegrondImportFout("Bestandsinhoud komt niet overeen met JPG/PNG-extensie.")
    return genormaliseerd


def valideer_vision_resultaat(data, uploadroot):
    """Normaliseer onbetrouwbare provideruitvoer tot een corrigeerbaar concept.

    De returnwaarde is gewone JSON-data. Er wordt nooit een dossier gemuteerd.
    """
    if not isinstance(data, dict) or data.get("contractversie") != "1":
        raise PlattegrondImportFout("Onbekende of ontbrekende vision-contractversie.")
    model = data.get("model") or {}
    if not all(str(model.get(k) or "").strip() for k in ("provider", "naam", "versie")):
        raise PlattegrondImportFout("Provider, modelnaam en modelversie moeten herleidbaar zijn.")
    verdiepingen = data.get("verdiepingen")
    if not isinstance(verdiepingen, list) or not verdiepingen:
        raise PlattegrondImportFout("Minimaal een verdieping is vereist.")

    resultaat = {"contractversie": "1", "model": {
        "provider": str(model["provider"]).strip(), "naam": str(model["naam"]).strip(),
        "versie": str(model["versie"]).strip()}, "verdiepingen": [], "aandachtspunten": []}
    namen = set()
    for index, vloer in enumerate(verdiepingen):
        if not isinstance(vloer, dict):
            raise PlattegrondImportFout(f"Verdieping {index + 1} is geen object.")
        naam = str(vloer.get("naam") or "").strip()
        if not naam or naam in namen:
            raise PlattegrondImportFout("Elke verdieping moet een unieke naam hebben.")
        namen.add(naam)
        schaal = vloer.get("schaal") or {}
        betrouwbaar_gevraagd = schaal.get("betrouwbaar") is True
        betrouwbaar = betrouwbaar_gevraagd
        bewijzen = schaal.get("maatlijn_bewijzen") or []
        meter_per_pixel = schaal.get("meter_per_pixel")
        if betrouwbaar:
            try:
                meter_per_pixel = _getal(meter_per_pixel, f"{naam}: meter_per_pixel")
                if not isinstance(bewijzen, list) or not bewijzen:
                    raise PlattegrondImportFout("geen gestructureerd maatlijnbewijs")
                for bewijs in bewijzen:
                    if not isinstance(bewijs, dict):
                        raise PlattegrondImportFout("maatlijnbewijs is geen object")
                    if not str(bewijs.get("tekst") or "").strip() \
                            or not str(bewijs.get("bron") or "").strip():
                        raise PlattegrondImportFout("maatlijnbewijs mist concrete tekst of bron")
                    px = _getal(bewijs.get("pixel_lengte"), f"{naam}: maatlijn pixel_lengte")
                    lengte = _getal(bewijs.get("lengte_m"), f"{naam}: maatlijn lengte_m")
                    verhouding = lengte / px
                    if abs(verhouding - meter_per_pixel) / meter_per_pixel > MAATLIJN_TOLERANTIE:
                        raise PlattegrondImportFout("maatlijnbewijs is inconsistent met meter_per_pixel")
            except PlattegrondImportFout as fout:
                betrouwbaar = False
                meter_per_pixel = None
                bewijzen = []
                resultaat["aandachtspunten"].append(
                    f"{naam}: schaalbewijs ongeldig ({fout}); oppervlakten moeten handmatig worden ingevuld.")
        else:
            meter_per_pixel = None
        if not betrouwbaar and not betrouwbaar_gevraagd:
            resultaat["aandachtspunten"].append(
                f"{naam}: schaal niet betrouwbaar; oppervlakten moeten handmatig worden ingevuld.")

        ruimtes_in = vloer.get("ruimtes")
        if not isinstance(ruimtes_in, list) or not ruimtes_in:
            raise PlattegrondImportFout(f"{naam}: minimaal een ruimte is vereist.")
        ruimte_namen = [str(r.get("naam") or "").strip() for r in ruimtes_in if isinstance(r, dict)]
        if len(ruimte_namen) != len(ruimtes_in) or any(not n for n in ruimte_namen) \
                or len(set(ruimte_namen)) != len(ruimte_namen):
            raise PlattegrondImportFout(f"{naam}: ruimtenamen moeten gevuld en uniek zijn.")
        ruimtes = []
        adjacency = {ruimte_naam: set() for ruimte_naam in ruimte_namen}
        for r, ruimte_naam in zip(ruimtes_in, ruimte_namen):
            buren = r.get("aangrenzend") or []
            if not isinstance(buren, list) or any(b not in ruimte_namen or b == ruimte_naam for b in buren):
                raise PlattegrondImportFout(f"{naam}/{ruimte_naam}: ongeldige aangrenzendheid.")
            for buur in buren:
                adjacency[ruimte_naam].add(buur)
                adjacency[buur].add(ruimte_naam)
        for r, ruimte_naam in zip(ruimtes_in, ruimte_namen):
            functie = str(r.get("functie") or "").strip()
            if functie not in FUNCTIES:
                raise PlattegrondImportFout(f"{naam}/{ruimte_naam}: onbekende functie '{functie}'.")
            contouren, fout = valideer_ruimtepolygonen(
                {ruimte_naam: r.get("contour_relatief")}, {ruimte_naam})
            if fout:
                raise PlattegrondImportFout(f"{naam}: {fout}")
            aangrenzend = sorted(adjacency[ruimte_naam])
            opp = _getal(r.get("oppervlakte_m2"), f"{naam}/{ruimte_naam}: oppervlakte_m2") \
                if betrouwbaar else None
            onzeker = r.get("onzekerheden") or []
            if not isinstance(onzeker, list) or any(not str(x).strip() for x in onzeker):
                raise PlattegrondImportFout(f"{naam}/{ruimte_naam}: onzekerheden moeten teksten zijn.")
            ruimtes.append({"naam": ruimte_naam, "functie": functie,
                            "oppervlakte_m2": opp, "contour_relatief": contouren[ruimte_naam],
                            "aangrenzend": list(dict.fromkeys(aangrenzend)),
                            "onzekerheden": [str(x).strip() for x in onzeker],
                            "bron_per_waarde": {k: BRON_AFGELEZEN for k in
                                                ("naam", "functie", "contour_relatief", "aangrenzend")}
                            | ({"oppervlakte_m2": BRON_AFGELEZEN} if opp is not None else {})})
            resultaat["aandachtspunten"].extend(
                f"{naam}/{ruimte_naam}: {x}" for x in onzeker)
        resultaat["verdiepingen"].append({
            "volgorde": index, "naam": naam,
            "afbeelding": _veilige_afbeelding(uploadroot, vloer.get("afbeelding")),
            "schaal": {"betrouwbaar": betrouwbaar, "meter_per_pixel": meter_per_pixel,
                       "maatlijn_bewijzen": bewijzen if betrouwbaar else []}, "ruimtes": ruimtes})
    return resultaat


def bevestig_in_dossier(dossier, concept, bevestiging):
    """Vervang geometrie pas na volledige, expliciete adviseursbevestiging.

    `bevestiging` bevat alle uiteindelijke waarden; zo kan geen verborgen conceptwaarde
    ongemerkt rekeninvoer worden. Bestaande geometrie wordt niet overschreven.
    """
    if dossier.geometrie.vloeren or dossier.geometrie.ruimtes:
        raise PlattegrondImportFout("Bestaande dossiergeometrie wordt niet overschreven.")
    if not isinstance(bevestiging, dict) or bevestiging.get("expliciet_bevestigd") is not True:
        raise PlattegrondImportFout("De adviseur moet alle waarden expliciet bevestigen.")
    vloeren_in = bevestiging.get("verdiepingen")
    if not isinstance(vloeren_in, list) or len(vloeren_in) != len(concept["verdiepingen"]):
        raise PlattegrondImportFout("Bevestiging moet alle verdiepingen bevatten.")

    nieuwe_vloeren, nieuwe_ruimtes = [], []
    bevestigde_vloernamen = [str(v.get("naam") or "").strip() for v in vloeren_in]
    if any(not n for n in bevestigde_vloernamen) \
            or len(set(bevestigde_vloernamen)) != len(bevestigde_vloernamen):
        raise PlattegrondImportFout("Bevestigde verdiepingsnamen moeten gevuld en uniek zijn.")
    for bronvloer, bevestigd in zip(concept["verdiepingen"], vloeren_in):
        if bevestigd.get("bron_volgorde") != bronvloer["volgorde"]:
            raise PlattegrondImportFout("Verdiepingsvolgorde wijkt af van het concept.")
        vloer_naam = str(bevestigd.get("naam") or "").strip()
        if not vloer_naam:
            raise PlattegrondImportFout("Bevestigde verdiepingsnaam ontbreekt.")
        ruimten = bevestigd.get("ruimtes")
        if not isinstance(ruimten, list) or len(ruimten) != len(bronvloer["ruimtes"]):
            raise PlattegrondImportFout(f"{vloer_naam}: bevestig alle ruimtes.")
        bevestigd_namen = [str(r.get("naam") or "").strip() for r in ruimten]
        if any(not n for n in bevestigd_namen) or len(set(bevestigd_namen)) != len(bevestigd_namen):
            raise PlattegrondImportFout(f"{vloer_naam}: bevestigde ruimtenamen moeten uniek zijn.")
        adjacency = {naam: set() for naam in bevestigd_namen}
        for r, ruimte_naam in zip(ruimten, bevestigd_namen):
            buren = r.get("aangrenzend") or []
            if not isinstance(buren, list) or any(b not in bevestigd_namen or b == ruimte_naam
                                                  for b in buren):
                raise PlattegrondImportFout(f"{vloer_naam}/{ruimte_naam}: ongeldige aangrenzendheid.")
            for buur in buren:
                adjacency[ruimte_naam].add(buur)
                adjacency[buur].add(ruimte_naam)
        vloer_bron = BRON_AFGELEZEN if vloer_naam == bronvloer["naam"] else BRON_HANDMATIG
        nieuwe_vloeren.append(VloerInfo(
            naam=vloer_naam, plattegrond_afbeelding=bronvloer["afbeelding"],
            bron_per_waarde={"naam": vloer_bron, "plattegrond_afbeelding": BRON_AFGELEZEN}))
        for bronruimte, r, ruimte_naam in zip(bronvloer["ruimtes"], ruimten, bevestigd_namen):
            functie = str(r.get("functie") or "").strip()
            if functie not in FUNCTIES:
                raise PlattegrondImportFout(f"{vloer_naam}/{r.get('naam')}: ongeldige functie.")
            opp = _getal(r.get("oppervlakte_m2"), f"{vloer_naam}/{r.get('naam')}: oppervlakte_m2")
            contouren, fout = valideer_ruimtepolygonen(
                {ruimte_naam: r.get("contour_relatief")}, {ruimte_naam})
            if fout:
                raise PlattegrondImportFout(f"{vloer_naam}: {fout}")
            aangrenzend = sorted(adjacency[ruimte_naam])
            waarden = {"naam": ruimte_naam, "functie": functie, "oppervlakte_m2": opp,
                       "contour_relatief": contouren[ruimte_naam], "aangrenzend": aangrenzend}
            bronwaarden = {}
            for veld, waarde in waarden.items():
                concept_veld = "aangrenzend" if veld == "aangrenzend" else veld
                bronwaarden[veld] = (BRON_AFGELEZEN if waarde == bronruimte.get(concept_veld)
                                     else BRON_HANDMATIG)
            # Zonder betrouwbare schaal kan oppervlakte per definitie niet afgelezen zijn.
            if bronruimte["oppervlakte_m2"] is None:
                bronwaarden["oppervlakte_m2"] = BRON_HANDMATIG
            nieuwe_ruimtes.append(Ruimte(
                naam=ruimte_naam, functie=functie, oppervlakte_m2=opp, verdieping=vloer_naam,
                contour_relatief=contouren[ruimte_naam], aangrenzende_ruimtes=list(aangrenzend),
                bron_per_waarde=bronwaarden))
    dossier.geometrie.vloeren = nieuwe_vloeren
    dossier.geometrie.ruimtes = nieuwe_ruimtes
    return dossier
