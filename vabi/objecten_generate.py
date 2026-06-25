"""
Dossier -> VABI Objectenbibliotheek-XML (geometrie: rekenzone + vlakken), importeerbaar via
de Objecten-tegel. Dit is het geometrie-kroonjuweel.

GARANTIE-OP-IMPORT-ONTWERP (zelfde principe als de constructie-generator): we starten van een
ECHTE Objecten-export (een compleet, geldig project) als sjabloon en vervangen alleen de
GEOMETRIE (de Hoofdvlakken/Deelvlakken in Geometrie) door die uit het dossier. Alle overige
(enorme) standaard-structuur blijft verbatim -> de import kan niet struikelen.

Geometrie-model in VABI:
  Rekenzone > Geometrie > Hoofdvlak (gevel/dak/vloer: oppervlak, orientatie, begrenzing,
              constructie-ref) > DeelvlakList > Deelvlak (raam/deur: oppervlak, constructie-ref)

Constructie-verwijzingen (NaamConstructie + Constructie-GUID) komen uit dezelfde matcher als de
constructie-generator (resolve_constructies) -> de Constructie- en Objecten-bibliotheek wijzen
naar IDENTIEKE constructies. We embedden die constructies ook in dit bestand (self-contained).

    python vabi/objecten_generate.py --dossier out/dossier.json --out out/Objectenbibliotheek.xml

Let op: gevel-m2 per orientatie is een benadering uit MagicPlan; de adviseur verifieert in Vabi
(Vabi blijft de rekenkern). Dak-oppervlak via helling of handmatig veld.
"""
import os, sys, copy, uuid, argparse
import xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.dossier import load_json                                  # noqa: E402
from vabi.constructie_generate import resolve_constructies, _classify, TemplatePool  # noqa: E402
from vabi.codebook import Codebook                                  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
# sjabloon: een echte volledige Objecten-export (compleet geldig project)
TEMPLATE = os.path.join(HERE, "refs", "objecten_template.xml")


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _set(el, tag, value):
    c = el.find(tag)
    if c is not None:
        c.text = "" if value is None else str(value)
    return c


def _get(el, tag):
    c = el.find(tag)
    return (c.text or "").strip() if c is not None else None


def _face_kind(hv):
    """Type van een sjabloon-Hoofdvlak afleiden uit NaamConstructie."""
    n = (_get(hv, "NaamConstructie") or "").lower()
    if n.startswith("vloer"):
        return "vloer"
    if n.startswith("dak"):
        return "dak"
    return "gevel"


# VABI Orientatie-enum (Geometrie), afgeleid uit vabi/refs/code_universe.json: ZW=1, NW=3,
# N=4, NO=5, ZO=7 (geverifieerd) -> kompasrotatie vanaf Z. Horizontaal/plat/vloer = -1.
ORIENTATIE_CODE = {"z": "0", "zw": "1", "w": "2", "nw": "3", "n": "4", "no": "5", "o": "6",
                   "zo": "7", "horizontaal": "-1"}


def _orient_code(orientatie):
    return ORIENTATIE_CODE.get((orientatie or "").strip().lower())


# VABI GrenstAan-enum (begrenzing per vlak) — LIVE GEVERIFIEERD in EPA 12.0.1 via probe-import
# (22-6-2026): de dropdown-index = de integercode. Zie vabi/refs/grenstaan_mapping.md.
# 0=Buitenlucht 1=Water 2=Grond 3=Kruipruimte 4=AOR 5=AOS 6=ASGR 7=Onverwarmde kelder 8=AVR 9=Ander gebouw.
# (0/2/3/4/5/6 direct probe-bevestigd; 1/7/8/9 uit de bevestigde dropdown-volgorde.)
GRENST_AAN_CODE = {
    "buitenlucht": "0", "buiten": "0",
    "water": "1",
    "grond": "2",
    "kruipruimte": "3", "kruip": "3",
    "onverwarmde kelder": "7", "kelder": "7",
    "ander gebouw": "9",
}
# AOR/AOS/sterk-geventileerd: in de BASISOPNAME tellen ze als BUITENLUCHT (0) — officieel NTA8800-
# opnameformulier p.4 + ISSO 82.1 par. 6.3.4. In de DETAILOPNAME hebben ze eigen codes (4/5/6).
_DETAIL_CODE = {
    "aor": "4", "aangrenzende onverwarmde ruimte": "4", "onverwarmde ruimte": "4",
    "aos": "5", "aangrenzende onverwarmde serre": "5", "serre": "5",
    "asgr": "6", "aangrenzend sterk geventileerde ruimte": "6",
    "sterk geventileerd": "6", "sterk geventileerde ruimte": "6",
}
_AVR = {"avr", "aangrenzende verwarmde ruimte", "buurwoning", "aangrenzende woning"}


def _grenst_aan_code(begrenzing, basis=True):
    """Begrenzing-string -> VABI GrenstAan-code. basis=True (basisopname): AOR/AOS/sterk-geventileerd
    tellen als buitenlucht (0); detail -> eigen code 4/5/6. AVR=8 (adiabatisch, meestal al uitgesloten)."""
    b = (begrenzing or "").strip().lower()
    if not b:
        return None
    if b in _DETAIL_CODE:
        return "0" if basis else _DETAIL_CODE[b]
    if b in _AVR:
        return "8"
    return GRENST_AAN_CODE.get(b)


class GeoTemplates:
    """Sjabloon-Hoofdvlakken (per type) + een sjabloon-Deelvlak, uit de echte export."""
    def __init__(self, root):
        self.hoofd = {"gevel": None, "dak": None, "vloer": None}
        self.deelvlak = None
        for hv in root.iter():
            if _local(hv.tag) == "Hoofdvlak":
                k = _face_kind(hv)
                if self.hoofd.get(k) is None:
                    self.hoofd[k] = hv
                if self.deelvlak is None:
                    dv = hv.find("DeelvlakList")
                    if dv is not None:
                        for d in dv:
                            if _local(d.tag) == "Deelvlak":
                                self.deelvlak = d
                                break
        # fallback: gebruik gevel-sjabloon voor ontbrekende types
        base = self.hoofd["gevel"]
        if base is None:
            base = next((h for h in self.hoofd.values() if h is not None), None)
        for k in self.hoofd:
            if self.hoofd[k] is None:
                self.hoofd[k] = base


def _new_guid(el):
    g = el.find("Guid")
    if g is not None:
        g.text = str(uuid.uuid4())


def _build_hoofdvlak(gt, kind, area, naam_constructie, constructie_guid, orientatie_code=None,
                     perimeter=None, grenst_aan_code=None, hellingshoek_code=None):
    hv = copy.deepcopy(gt.hoofd[kind])
    _new_guid(hv)
    _set(hv, "Constructie", constructie_guid)
    _set(hv, "NaamConstructie", naam_constructie)
    _set(hv, "Oppervlakte", "%.2f" % area)
    _set(hv, "BrutoOppervlakte", "%.2f" % area)
    _set(hv, "NettoOppervlakte", "%.2f" % area)
    if orientatie_code is not None:
        _set(hv, "Orientatie", orientatie_code)
    if grenst_aan_code is not None:
        _set(hv, "GrenstAan", grenst_aan_code)
    if hellingshoek_code is not None:
        # VABI Objecten-Hellingshoek is een ENUM (geverifieerd in vabi_enums.json): 3 = "Dak hellend",
        # 6 = "Dak plat"/"Gevel". GEEN rauwe graden (die horen bij de losse monitoring-route). De
        # gemeten graden blijven in het dossier voor de dak-m2-berekening (footprint/cos).
        _set(hv, "Hellingshoek", hellingshoek_code)
    if perimeter is not None and float(perimeter) > 0:
        # randverlies (vloer): handmatige perimeter -> AutoPerimeter uit
        _set(hv, "Perimeter", "%.2f" % float(perimeter))
        _set(hv, "AutoPerimeter", "0")
    # leeg de deelvlakken (worden hieronder per raam/deur gevuld)
    dvl = hv.find("DeelvlakList")
    if dvl is not None:
        gid = dvl.find("Guid")
        for ch in list(dvl):
            if ch is not gid:
                dvl.remove(ch)
    return hv


def _add_deelvlak(gt, hoofdvlak, area, naam_constructie, constructie_guid, naam_hoofdvlak):
    if gt.deelvlak is None:
        return False
    dvl = hoofdvlak.find("DeelvlakList")
    if dvl is None:
        return False
    dv = copy.deepcopy(gt.deelvlak)
    _new_guid(dv)
    _set(dv, "Constructie", constructie_guid)
    _set(dv, "NaamConstructie", naam_constructie)
    _set(dv, "Oppervlakte", "%.2f" % area)
    _set(dv, "RelevanteOppervlakte", "%.2f" % area)
    _set(dv, "NaamHoofdvlak", naam_hoofdvlak)
    dvl.append(dv)
    return True


def build_tree(dos):
    root = ET.parse(TEMPLATE).getroot()
    # 1) gedeelde constructies (zelfde guid/naam als de constructie-bibliotheek)
    clones, mapping, issues = resolve_constructies(dos)
    # embed ze in de Constructies-node (self-contained)
    cons = next((c for c in root.iter() if _local(c.tag) == "Constructies"), None)
    if cons is not None:
        gid = cons.find("Guid")
        for ch in list(cons):
            if ch is not gid:
                cons.remove(ch)
        for i, cl in enumerate(clones):
            cl.set("Index", str(i))
            cons.append(cl)
    # 2) geometrie opbouwen
    gt = GeoTemplates(root)
    geo = next((g for g in root.iter() if _local(g.tag) == "Geometrie"), None)
    if geo is None:
        raise ValueError("Geen Geometrie-node in sjabloon")
    gid = geo.find("Guid")
    for ch in list(geo):
        if ch is not gid:
            geo.remove(ch)

    # basisopname (default) -> AOR/AOS/sterk-geventileerd tellen als buitenlucht (ISSO/officieel formulier)
    is_basis = "detail" not in (getattr(getattr(dos, "opname", None), "type_advies", "") or "").lower()
    # vloer-perimeter (randverlies) alleen bij grond/kruipruimte/(onverwarmde) kelder (ISSO 8.3)
    _PERIM_BEGR = ("grond", "kruip", "kelder")
    gevels = []   # (hoofdvlak_el, naam, orientatie) voor deelvlak-toewijzing
    for s in dos.schil:
        kind = _classify(s)
        m = mapping.get(s.id)
        if m is None:
            continue
        if kind in ("gevel", "vloer", "dak"):
            area = float(getattr(s, "oppervlakte_m2", 0) or 0)
            orient = getattr(s, "orientatie", "") or ""
            oc = _orient_code(orient)
            if kind == "vloer":
                oc = "-1"                       # vloer = horizontaal
            elif kind == "dak" and not oc:
                oc = "-1"                       # plat/onbekend dak -> horizontaal (fallback)
            elif kind == "gevel" and oc is None:
                issues.append("gevel %s: onbekende orientatie %r -> sjabloon-default" % (s.id, orient))
            # begrenzing -> GrenstAan (alleen bevestigde codes; onbekend -> sjabloon-default + flag)
            begr = getattr(s, "begrenzing", "") or ""
            # perimeter (randverlies) ALLEEN voor vloeren grenzend aan grond/kruipruimte/kelder (ISSO 8.3)
            per = (getattr(s, "perimeter_m", None)
                   if kind == "vloer" and any(k in begr.lower() for k in _PERIM_BEGR) else None)
            gc = _grenst_aan_code(begr, basis=is_basis)
            if begr and gc is None:
                issues.append("%s %s: begrenzing %r nog niet in GrenstAan-mapping (5/6/woning) -> "
                              "sjabloon-default, verifieer in Vabi" % (kind, s.id, begr))
            # dak: Hellingshoek-enum expliciet zetten (plat=6, hellend=3) zodat een plat dakvlak niet
            # de hellend-sjabloonwaarde (3) erft. Gevels houden de sjabloon-default (6).
            hc = None
            if kind == "dak":
                h_deg = getattr(s, "hellingshoek", None)
                if "plat" in (getattr(s, "subtype", "") or "").lower() or (h_deg is not None and float(h_deg) <= 0):
                    hc = "6"
                elif h_deg is not None and float(h_deg) > 0:
                    hc = "3"
            hv = _build_hoofdvlak(gt, kind, area, m["naam"], m["guid"], orientatie_code=oc,
                                  perimeter=per, grenst_aan_code=gc, hellingshoek_code=hc)
            naam = "%s %s" % (kind.capitalize(), s.id)
            _set(hv, "Naam", naam)
            _set(hv, "AutoNaam", "0")
            geo.append(hv)
            if kind == "gevel":
                gevels.append((hv, naam, orient))
    # ramen/deuren als deelvlakken: in de gevel met DEZELFDE orientatie (anders round-robin)
    placed = 0
    for s in dos.schil:
        kind = _classify(s)
        if kind not in ("raam", "deur"):
            continue
        m = mapping.get(s.id)
        if m is None or not gevels:
            if not gevels:
                issues.append("geen gevel om %s in te plaatsen" % s.id)
            continue
        so = (getattr(s, "orientatie", "") or "").strip().lower()
        match = next(((hv, naam) for hv, naam, go in gevels
                      if so and (go or "").strip().lower() == so), None)
        if match is None:
            hv, naam, _go = gevels[placed % len(gevels)]
        else:
            hv, naam = match
        area = float(getattr(s, "oppervlakte_m2", 0) or 0)
        if _add_deelvlak(gt, hv, area, m["naam"], m["guid"], naam):
            placed += 1
    # 3) Algemeen: bouwjaar/renovatiejaar/qv10. LET OP: er zijn twee <Algemeen>-knopen — de
    # project-Algemeen (alleen Projectgegevens) staat vóór de REKENZONE-Algemeen (met Bouwjaar/
    # Qv10/Gebruiksoppervlakte). Selecteer expliciet de rekenzone-knoop (die met Bouwjaar).
    alg = next((a for a in root.iter()
                if _local(a.tag) == "Algemeen" and a.find("Bouwjaar") is not None), None)
    if alg is not None:
        bj = getattr(dos.identificatie, "bouwjaar", None)
        rj = getattr(dos.identificatie, "renovatiejaar", None)
        if bj:
            _set(alg, "Bouwjaar", bj)
        if rj:
            _set(alg, "Renovatiejaar", rj)
        # qv10 alleen schrijven als GEMETEN (ISSO 7.1.5); anders forfaitair laten (Qv10Gemeten=0 ->
        # VABI rekent op bouwjaar/renovatiejaar). Een ingevulde-maar-niet-gemeten waarde negeren we.
        _opn = getattr(dos, "opname", None)
        qv = getattr(_opn, "qv10_waarde", None)
        if qv is not None and bool(getattr(_opn, "qv10_gemeten", False)):
            _set(alg, "Qv10Gemeten", "1")
            _set(alg, "Qv10Waarde", "%.3f" % float(qv))
        elif qv is not None:
            issues.append("qv10=%.2f genegeerd (niet-gemeten; ISSO 7.1.5 -> forfaitair op bouwjaar/renovatiejaar)" % float(qv))
        # thermische massa (Rekenzone>Algemeen) — LIVE GEVERIFIEERD in EPA (22-6-2026): 0=Licht,
        # 1=Zwaar, 2=Zeer zwaar (TypeBouwwijzeWanden/Vloeren). Alle drie worden nu automatisch gezet.
        opn = getattr(dos, "opname", None)
        _MASSA_CODE = {"licht": "0", "zwaar": "1", "zeer zwaar": "2"}
        for veld, waarde in (("TypeBouwwijzeWanden", getattr(opn, "thermische_massa_wanden", "")),
                             ("TypeBouwwijzeVloeren", getattr(opn, "thermische_massa_vloeren", ""))):
            w = (waarde or "").strip().lower()
            code = _MASSA_CODE.get(w)
            if code is not None:
                _set(alg, veld, code)
            elif w:
                issues.append("%s='%s': onbekende thermische-massaklasse (verwacht Licht/Zwaar/Zeer zwaar)" % (veld, waarde))
        # gebruiksoppervlakte (Ag): de rekenzone-Ag dragen we via de PER-VERDIEPING-oppervlakken
        # (Verdiepingen) + de vloer-hoofdvlakken in de geometrie. De DIRECTE Rekenzone>Algemeen-knoop
        # <Gebruiksoppervlakte> is GEEN m2-veld maar een enum/vlag (echte EPA-export = "1", ook bij een
        # 185 m2-woning) -> die met de gemeten m2 overschrijven gaf EPA "Enum mismatch" (live bewezen
        # 23-6, zie vabi/refs/grenstaan_mapping.md). Daarom NIET zetten: sjabloon-default behouden.
        geom = getattr(dos, "geometrie", None)
        ag = float(getattr(geom, "gebruiksoppervlakte_ag_m2", 0) or 0)
        if ag > 0:
            n_lagen = max(len(getattr(geom, "vloeren", []) or []), 1)
            _set(alg, "AantalBouwlagenRekenzone", str(n_lagen))
            verd = alg.find("Verdiepingen")
            if verd is not None:
                vg = verd.find("Guid")
                tmpl_v = next((c for c in verd if _local(c.tag) == "Verdieping"), None)
                for ch in list(verd):
                    if ch is not vg:
                        verd.remove(ch)
                if tmpl_v is not None:
                    per_laag = round(ag / n_lagen, 2)
                    for i in range(n_lagen):
                        v = copy.deepcopy(tmpl_v)
                        v.set("Index", str(i))
                        _new_guid(v)
                        _set(v, "Gebruiksoppervlakte", "%.2f" % per_laag)
                        verd.append(v)
            issues.append("Ag=%.1f m2 + %d bouwlaag/lagen gezet (per-laag verdeeld; totaal exact)" % (ag, n_lagen))
    # 3b) Gebouw-niveau: Gebouwhoogte (vrije float, geen enum-risico) uit de opname; Gebouwtype/Daktype
    # zijn ENUMS waarvan de codes nog in EPA bevestigd moeten worden -> NIET gokken (golden rule), flaggen.
    gh = getattr(getattr(dos, "opname", None), "gevelhoogte_m", None)
    if gh and float(gh) > 0:
        gh_node = next((e for e in root.iter() if _local(e.tag) == "Gebouwhoogte"), None)
        if gh_node is not None:
            gh_node.text = "%.2f" % float(gh)
    wt = getattr(getattr(dos, "identificatie", None), "woningtype", "")
    td = getattr(getattr(dos, "identificatie", None), "type_dak", "") or \
         getattr(getattr(dos, "opname", None), "type_dak", "")
    if wt:
        issues.append("Gebouwtype/Ligging (woningtype=%r): VABI-enumcode nog te bevestigen in EPA -> "
                      "sjabloon-default; zet woningpositie handmatig in Vabi (golden rule)." % wt)
    if td:
        # Daktype LIVE GEVERIFIEERD in EPA: 0=Hellend dak, 1=Deels plat dak, 2=Plat dak/zonder kap.
        tdl = td.lower()
        dc = ("1" if ("deels plat" in tdl or "gedeeltelijk plat" in tdl)
              else "2" if "plat" in tdl
              else "0" if any(k in tdl for k in ("hellend", "zadel", "lessenaar", "punt")) else None)
        if dc is not None:
            dt_node = next((e for e in root.iter() if _local(e.tag) == "Daktype"), None)
            if dt_node is not None:
                dt_node.text = dc
        else:
            issues.append("Daktype %r niet herkend -> sjabloon-default; verifieer in Vabi." % td)
    # 4) persoonsgegevens blanken (adviseur vult Algemeen zelf in EPA)
    for adr in root.iter():
        if _local(adr.tag) == "Adresgegevens":
            for t in ("Straat", "Huisnummer", "Postcode", "Woonplaats", "BagObjectId",
                      "BagPandId", "BagIdentificatie"):
                _set(adr, t, "")
    return root, mapping, issues, {"hoofdvlakken": len(gevels), "deelvlakken_geplaatst": placed}


def write(dos, path):
    if not os.path.exists(TEMPLATE):
        raise FileNotFoundError(
            "Objecten-sjabloon ontbreekt: %s\n  Maak het eenmalig: exporteer in EPA de "
            "Objectenbibliotheek van een echt project en kopieer naar dit pad." % TEMPLATE)
    root, mapping, issues, stats = build_tree(dos)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    body = ET.tostring(root, encoding="utf-8")
    with open(path, "wb") as fh:
        fh.write(b'<?xml version="1.0" encoding="UTF-8"?>\n' + body)
    return mapping, issues, stats


def main():
    root_dir = os.path.dirname(HERE)
    ap = argparse.ArgumentParser(description="Dossier -> importeerbare VABI Objectenbibliotheek")
    ap.add_argument("--dossier", required=True)
    ap.add_argument("--out", default=os.path.join(root_dir, "out", "Objectenbibliotheek.xml"))
    a = ap.parse_args()
    dos = load_json(a.dossier)
    mapping, issues, stats = write(dos, a.out)
    print("OK: %s" % a.out)
    print("  geometrie: %d hoofdvlakken (gevel) + %d deelvlakken (raam/deur) geplaatst" % (
        stats["hoofdvlakken"], stats["deelvlakken_geplaatst"]))
    for it in issues:
        print("  ! " + it)
    print("  -> import in EPA: tegel Objecten > Importeren.")


if __name__ == "__main__":
    main()
