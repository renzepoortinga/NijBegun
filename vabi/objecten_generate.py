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
from vabi.preflight import assert_no_schil_kwaliteitsverklaring      # noqa: E402

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


# VABI Orientatie-enum (Geometrie) — LIVE GEVERIFIEERD in EPA 12.0.1 via Geometrie-export (18-7-2026,
# voorbeeldproject 'hoekwoning'): Gevel Zuid->0, Noord->4, Oost->6 (+ Dak Noord=4, Zuid=0). De EPA
# "Orientatie voorgevel"-dropdownVOLGORDE (Zuid,ZW,W,NW,N,NO,O,ZO) == de integercode, op 3 punten
# (0/4/6) rechtstreeks tegen de export gematcht -> hele kompasrotatie vanaf Zuid bevestigd. LET OP:
# dit is ANDERS dan de PV-orientatie-enum (0=N..7=NW; zie installatie_enums_EPA.md). Vloer/plat = -1.
ORIENTATIE_CODE = {"z": "0", "zw": "1", "w": "2", "nw": "3", "n": "4", "no": "5", "o": "6",
                   "zo": "7", "horizontaal": "-1"}


def _orient_code(orientatie):
    return ORIENTATIE_CODE.get((orientatie or "").strip().lower())


# VABI Object-classificatie — LIVE GEVERIFIEERD in EPA 12.0.1 (18-7-2026): Gebouwtype 0=Eengezinswoning
# (Objecten-export hoekwoning + monitor-fixture) en Subtype = WONINGPOSITIE (dropdown-index = code):
# 0=Vrijstaand · 1=Kop-/eind-/hoekligging · 2=Tussenligging · 3=Twee onder een kap. Bevestigd: export
# Subtype=1 (hoekwoning) + monitor Subtype=2 (tussenwoning). Ligging is appartement-only -> bij een
# eengezinswoning 0 (=nvt). Nij Begun-scope = grondgebonden eengezinswoningen -> Gebouwtype altijd 0.
GEBOUWTYPE_EENGEZINSWONING = "0"


def _subtype_code(woningtype):
    """woningtype (WONINGTYPE_OPTS) -> EPA Subtype/woningpositie-code, of None als onbekend/meergezins
    (dan flaggen i.p.v. gokken). Zelfde positie-logica als core.geometry.aantal_woningscheidende_wanden,
    maar 'twee onder een kap' is een EIGEN code (3), niet gelijk aan hoek (1)."""
    w = (woningtype or "").strip().lower()
    if not w:
        return None
    if "vrijstaand" in w:
        return "0"
    if ("onder een kap" in w or "onder-een-kap" in w or w.startswith("twee")
            or "2-onder" in w or "2 onder" in w or "2^1" in w):
        return "3"
    if "tussen" in w:
        return "2"
    if any(k in w for k in ("hoek", "kop", "eind")):
        return "1"
    return None


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
    "asgr": "6", "asv": "6", "aangrenzend sterk geventileerde ruimte": "6",   # 'asv' = tolerante alias (officieel ASGR)
    "sterk geventileerd": "6", "sterk geventileerde ruimte": "6",
}
_AVR = {"avr", "aangrenzende verwarmde ruimte", "buurwoning", "aangrenzende woning"}
# De VOLLEDIGE GrenstAan-dropdown (0-9) is LIVE afgelezen in EPA 12.0.1 (19-7, steekproef) en matcht
# exact de probe-volgorde 0=Buitenlucht..9=Ander gebouw -> 1/7/8/9 zijn nu óók bevestigd; er is geen
# 'onbevestigd'-flag meer nodig (leeg gelaten i.p.v. verwijderd zodat de check-plek intact blijft).
_GRENST_ONBEVESTIGD = {}


_KOMPAS8 = ["N", "NO", "O", "ZO", "Z", "ZW", "W", "NW"]


def _locatie_code(kind, s, orientatie_voorgevel):
    """EPA Geometrie-tabblad per hoofdvlak: 0=Vloeren 1=Daken 2=Voorgevel 3=Achtergevel
    4=Linkergevel 5=Rechtergevel (uit echte export; ordening, geen rekensemantiek). Gevel: eerst
    het naam-token (voor/achter/links/rechts), anders oriëntatie t.o.v. de voorgevel (links=+90,
    rechts=-90 — zelfde conventie als de parser). Onbepaald -> None (sjabloonwaarde blijft)."""
    if kind == "vloer":
        return "0"
    if kind == "dak":
        return "1"
    if kind != "gevel":
        return None
    naam_l = ("%s %s" % (getattr(s, "gevel_naam", "") or "", s.id or "")).lower()
    if "achter" in naam_l:
        return "3"
    if "link" in naam_l:
        return "4"
    if "recht" in naam_l:
        return "5"
    if "voor" in naam_l and "kopg" not in naam_l:
        return "2"
    vo, so = (orientatie_voorgevel or "").upper(), (getattr(s, "orientatie", "") or "").upper()
    if vo in _KOMPAS8 and so in _KOMPAS8:
        d = (_KOMPAS8.index(so) - _KOMPAS8.index(vo)) % 8
        return {0: "2", 4: "3", 2: "4", 6: "5"}.get(d)
    return None


def _grenst_aan_code(begrenzing, basis=True):
    """Begrenzing-string -> VABI GrenstAan-code. basis=True (basisopname): AOR/AOS/sterk-geventileerd
    tellen als buitenlucht (0); detail -> eigen code 4/5/6. AVR=8 (adiabatisch, meestal al uitgesloten)."""
    b = (begrenzing or "").strip().lower()
    if not b:
        return None
    # MagicPlan labelt beschrijvend ('AOR (onverwarmd)', 'ASGR (sterk geventileerd)') -> pak ook de
    # kale afkorting vóór ' (' zodat die labels net zo goed mappen als de kale ('AOR', 'ASGR').
    for key in (b, b.split(" (")[0].strip()):
        if key in _DETAIL_CODE:
            return "0" if basis else _DETAIL_CODE[key]
        if key in _AVR:
            return "8"
        code = GRENST_AAN_CODE.get(key)
        if code is not None:
            return code
    return None


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
    elif kind == "vloer":
        # SJABLOON-LEK dichten (audit 12-7): het gekloonde vloer-sjabloon draagt de HANDMATIGE
        # perimeter van de sjabloonwoning (28.14 m, AutoPerimeter=0). Zonder eigen meting zetten
        # we 0 + AutoPerimeter aan (VABI rekent zelf) — nooit andermans randverlies.
        _set(hv, "Perimeter", "0.00")
        _set(hv, "AutoPerimeter", "1")
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
    daken = []    # idem: dak-hoofdvlakken (voor DAKRAMEN als deelvlak in het dakvlak)
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
                oc = "-1"                       # plat dak -> horizontaal
                if (getattr(s, "hellingshoek", 0) or 0) > 0:
                    # audit 13-7: een HELLEND vlak zonder oriëntatie werd stil horizontaal gezet
                    issues.append("dak %s: HELLEND vlak ZONDER oriëntatie -> horizontaal gezet; "
                                  "zet de oriëntatie in Vabi." % s.id)
            elif kind == "gevel" and oc is None:
                issues.append("gevel %s: onbekende orientatie %r -> sjabloon-default" % (s.id, orient))
            # begrenzing -> GrenstAan (alleen bevestigde codes; onbekend -> sjabloon-default + flag)
            begr = getattr(s, "begrenzing", "") or ""
            # perimeter (randverlies) ALLEEN voor vloeren grenzend aan grond/kruipruimte/kelder (ISSO 8.3)
            per = (getattr(s, "perimeter_m", None)
                   if kind == "vloer" and any(k in begr.lower() for k in _PERIM_BEGR) else None)
            gc = _grenst_aan_code(begr, basis=is_basis)
            if gc in _GRENST_ONBEVESTIGD:
                issues.append("%s %s: begrenzing '%s' -> GrenstAan-code %s (%s) is NIET probe-bevestigd "
                              "in EPA -> controleer de begrenzing in Vabi." % (kind, s.id, begr, gc,
                              _GRENST_ONBEVESTIGD[gc]))
            # dak: Hellingshoek-enum expliciet zetten (plat=6, hellend=3) zodat een plat dakvlak niet
            # de hellend-sjabloonwaarde (3) erft. Gevels houden de sjabloon-default (6).
            hc = None
            if kind == "dak":
                h_deg = getattr(s, "hellingshoek", None)
                if "plat" in (getattr(s, "subtype", "") or "").lower() or (h_deg is not None and float(h_deg) <= 0):
                    hc = "6"
                elif h_deg is not None and float(h_deg) > 0:
                    hc = "3"
            if gc is None:
                # audit 12-7: OOK een LEGE begrenzing flaggen — de kloon houdt anders stil de
                # sjabloon-GrenstAan (vloer-sjabloon = 3/kruipruimte!) zonder dat iemand het ziet.
                issues.append("%s %s: begrenzing %s -> sjabloon-GrenstAan blijft staan; zet de "
                              "juiste begrenzing in Vabi" % (kind, s.id,
                              ("%r nog niet in de mapping" % begr) if begr else "ONTBREEKT"))
            if area <= 0:
                issues.append("%s %s: OPPERVLAKTE 0 m2 weggeschreven — meting ontbreekt; vul de "
                              "echte m2 in de webapp of in Vabi in." % (kind, s.id))
            if per is None and kind == "vloer" and any(k in begr.lower() for k in _PERIM_BEGR):
                issues.append("vloer %s: perimeter (randverlies) ONTBREEKT -> AutoPerimeter aan "
                              "gezet; controleer de omtrek in Vabi." % s.id)
            hv = _build_hoofdvlak(gt, kind, area, m["naam"], m["guid"], orientatie_code=oc,
                                  perimeter=per, grenst_aan_code=gc, hellingshoek_code=hc)
            naam = "%s %s" % (kind.capitalize(), s.id)
            _set(hv, "Naam", naam)
            _set(hv, "AutoNaam", "0")
            # Locatie = het EPA-Geometrie-TABBLAD (puur ordening, geen rekensemantiek):
            # 0=Vloeren 1=Daken 2=Voorgevel 3=Achtergevel 4=Linkergevel 5=Rechtergevel.
            # Codes afgeleid uit de echte sjabloon-export + live bevestigd (alles-op-Voorgevel
            # bleek de kloon-default Locatie=2, 12-7). Zonder dit belandt elke gevel op één tab.
            loc = _locatie_code(kind, s, getattr(dos.identificatie, "orientatie_voorgevel", ""))
            if loc is not None:
                _set(hv, "Locatie", loc)
            geo.append(hv)
            if kind == "gevel":
                gevels.append((hv, naam, orient))
            elif kind == "dak":
                daken.append((hv, naam, orient))
    # ramen/deuren/panelen als deelvlakken: in de gevel met DEZELFDE orientatie (anders round-robin).
    # Een paneel-in-kozijn is óók een opening in de wand (dichte constructie) -> deelvlak, net als een raam.
    placed = 0
    for s in dos.schil:
        kind = _classify(s)
        if kind not in ("raam", "deur", "paneel"):
            continue
        m = mapping.get(s.id)
        _is_dakraam = "dakraam" in (getattr(s, "subtype", "") or "").lower()
        doelen = daken if (_is_dakraam and daken) else gevels
        if _is_dakraam and not daken:
            issues.append("dakraam %s: geen dak-hoofdvlak om in te plaatsen -> in gevel geplaatst; "
                          "verplaats in Vabi naar het dakvlak" % s.id)
        if m is None or not doelen:
            if not doelen:
                issues.append("geen hoofdvlak om %s in te plaatsen" % s.id)
            continue
        so = (getattr(s, "orientatie", "") or "").strip().lower()
        kandidaten = [(hv, naam) for hv, naam, go in doelen if so and (go or "").strip().lower() == so]
        if not kandidaten:
            hv, naam, _go = doelen[placed % len(doelen)]
            issues.append("%s %s (orientatie %r): geen hoofdvlak met die orientatie -> in '%s' "
                          "geplaatst; controleer/verplaats in Vabi." % (kind, s.id,
                          getattr(s, "orientatie", ""), naam))
        else:
            hv, naam = kandidaten[0]
            if len(kandidaten) > 1:
                # audit 12-7: meerdere vlakken met dezelfde orientatie (bv. hoofdgevel + kopgevel)
                # -> plaatsing in het EERSTE is een keuze, geen meting: flaggen.
                issues.append("%s %s: %d vlakken met orientatie %r -> in '%s' geplaatst; controleer "
                              "of hij daar hoort (Vabi: deelvlak verslepen)." % (kind, s.id,
                              len(kandidaten), getattr(s, "orientatie", ""), naam))
        area = float(getattr(s, "oppervlakte_m2", 0) or 0)
        if area <= 0:
            issues.append("%s %s: OPPERVLAKTE 0 m2 als deelvlak weggeschreven — vul de echte m2 in." % (kind, s.id))
        if _add_deelvlak(gt, hv, area, m["naam"], m["guid"], naam):
            placed += 1
        else:
            # audit 12-7: mislukte plaatsing verdween geruisloos (raam/deur ONTBRAK dan in de import)
            issues.append("%s %s: kon NIET als deelvlak geplaatst worden (sjabloon mist deelvlak-"
                          "structuur) — voeg het element handmatig toe in Vabi!" % (kind, s.id))
    # NETTO herrekenen (audit 12-7, geverifieerd in de echte export): NettoOppervlakte =
    # BrutoOppervlakte - som(deelvlakken). Wij schreven netto=bruto en voegden daarna deelvlakken
    # toe; het echte exportgedrag trekt ze af.
    for hv in geo:
        if _local(hv.tag) != "Hoofdvlak":
            continue
        dvl = hv.find("DeelvlakList")
        som_dv = sum(float(c.findtext("Oppervlakte") or 0)
                     for c in (list(dvl) if dvl is not None else []) if _local(c.tag) == "Deelvlak")
        if som_dv > 0:
            bruto = float(hv.findtext("BrutoOppervlakte") or 0)
            netto = bruto - som_dv
            if netto < 0:
                issues.append("%s: deelvlakken (%.2f m2) GROTER dan het vlak (%.2f m2) -> netto op 0; "
                              "controleer de maten." % (hv.findtext("Naam") or "?", som_dv, bruto))
                netto = 0.0
            _set(hv, "NettoOppervlakte", "%.2f" % netto)
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
        else:
            # NOOIT het sjabloon-bouwjaar laten staan (kloon van een echte export -> stil fout jaar,
            # live gezien 12-7: '1994' lekte mee). Zet 0 = zichtbaar leeg + luide actie.
            _set(alg, "Bouwjaar", "0")
            issues.append("BOUWJAAR ONTBREEKT -> 0 gezet in Objecten>Algemeen: vul het echte bouwjaar "
                          "in Vabi in (anders bleef het sjabloon-jaar staan).")
        # Renovatiejaar ALTIJD expliciet schrijven (audit 12-7: zelfde patroon als het bouwjaar-lek;
        # bij leeg = 0 = 'geen renovatie opgegeven' — nooit op de sjabloonwaarde vertrouwen).
        _set(alg, "Renovatiejaar", rj if rj else "0")
        # qv10 alleen schrijven als GEMETEN (ISSO 7.1.5); anders forfaitair laten (Qv10Gemeten=0 ->
        # VABI rekent op bouwjaar/renovatiejaar). Een ingevulde-maar-niet-gemeten waarde negeren we.
        _opn = getattr(dos, "opname", None)
        qv = getattr(_opn, "qv10_waarde", None)
        if qv is not None and bool(getattr(_opn, "qv10_gemeten", False)):
            _set(alg, "Qv10Gemeten", "1")
            _set(alg, "Qv10Waarde", "%.3f" % float(qv))
        elif qv is not None:
            issues.append("qv10=%.2f genegeerd (niet-gemeten; ISSO 7.1.5 -> forfaitair op bouwjaar/renovatiejaar)" % float(qv))
        elif bool(getattr(_opn, "qv10_gemeten", False)):
            # audit 15-7: gemeten=Ja maar geen waarde -> viel stil terug op forfaitair; nu luide flag
            issues.append("Qv10 GEMETEN=Ja maar GEEN waarde -> sjabloon (forfaitair) blijft staan; "
                          "vul de gemeten qv10-waarde in Vabi in.")
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
            else:
                # audit 15-7 (HIGH): LEEG lekte stil de sjabloonwaarde 'Zwaar' (code 1) -> nu luide flag
                # (zelfde patroon als bouwjaar/verdiepingen). Beïnvloedt de warmtebehoefte/TOjuli.
                issues.append("%s ONTBREEKT -> sjabloon 'Zwaar' blijft staan; zet de thermische massa "
                              "(Licht/Zwaar/Zeer zwaar) in Vabi. Bij een lichte constructie (HSB) is 'Zwaar' fout." % veld)
        # gebruiksoppervlakte (Ag): de rekenzone-Ag dragen we via de PER-VERDIEPING-oppervlakken
        # (Verdiepingen) + de vloer-hoofdvlakken in de geometrie. De DIRECTE Rekenzone>Algemeen-knoop
        # <Gebruiksoppervlakte> is GEEN m2-veld maar een enum/vlag (echte EPA-export = "1", ook bij een
        # 185 m2-woning) -> die met de gemeten m2 overschrijven gaf EPA "Enum mismatch" (live bewezen
        # 23-6, zie vabi/refs/grenstaan_mapping.md). Daarom NIET zetten: sjabloon-default behouden.
        geom = getattr(dos, "geometrie", None)
        ag = float(getattr(geom, "gebruiksoppervlakte_ag_m2", 0) or 0)
        # per-verdieping: de ECHTE gemeten MagicPlan-oppervlakken (VloerInfo.oppervlakte_m2)
        # als die er zijn; alleen als fallback Ag gelijk verdelen (met flag). Gelijk verdelen
        # terwijl de meting er wél is gaf 3x29.04 i.p.v. 55.6/44.4/22.2 (live gezien 12-7).
        alle_vloeren = list(getattr(geom, "vloeren", None) or [])
        vlagen = [v for v in alle_vloeren if float(getattr(v, "oppervlakte_m2", 0) or 0) > 0]
        for v in alle_vloeren:
            if float(getattr(v, "oppervlakte_m2", 0) or 0) <= 0 and vlagen:
                # audit 12-7: een verdieping ZONDER m2 telde wel mee in AantalBouwlagen maar kreeg
                # geen Verdieping-knoop -> aantal en som liepen uiteen. Nu: niet meetellen + flag.
                issues.append("verdieping '%s': geen gemeten m2 -> NIET meegeteld; vul de m2 in "
                              "Vabi aan (Verdiepingen)." % (getattr(v, "naam", "") or "?"))
        # aantal lagen = het aantal LAGEN DAT WE SCHRIJVEN (met meting), anders de vloerenlijst
        n_lagen = len(vlagen) if vlagen else max(len(alle_vloeren), 1)
        verd = alg.find("Verdiepingen")
        if verd is not None:
            vg = verd.find("Guid")
            tmpl_v = next((c for c in verd if _local(c.tag) == "Verdieping"), None)
            for ch in list(verd):
                if ch is not vg:
                    verd.remove(ch)
            if tmpl_v is not None:
                if vlagen:
                    waarden = [float(v.oppervlakte_m2) for v in vlagen]
                elif ag > 0:
                    waarden = [round(ag / n_lagen, 2)] * n_lagen
                else:
                    # audit 12-7 (HOOG): zonder Ag én zonder metingen bleven de SJABLOON-verdiepingen
                    # (3 lagen, ~185 m2 van de sjabloonwoning) stil staan. Nu: 1 lege laag + luide actie.
                    waarden = [0.0]
                    n_lagen = 1
                for i, w in enumerate(waarden):
                    v = copy.deepcopy(tmpl_v)
                    v.set("Index", str(i))
                    _new_guid(v)
                    _set(v, "Gebruiksoppervlakte", "%.2f" % w)
                    verd.append(v)
        _set(alg, "AantalBouwlagenRekenzone", str(n_lagen))
        if vlagen:
            issues.append("Verdiepingen: gemeten m² per bouwlaag gezet (%s; som %.2f) — controleer "
                          "of berging/zolderstrook <1,5 m niet meetellen (Ag is heilig)."
                          % ("/".join("%.1f" % float(v.oppervlakte_m2) for v in vlagen),
                             sum(float(v.oppervlakte_m2) for v in vlagen)))
        elif ag > 0:
            issues.append("Ag=%.1f m2 over %d bouwlagen GELIJK verdeeld (geen per-verdieping-meting "
                          "in het dossier) — corrigeer de verdieping-m² in Vabi." % (ag, n_lagen))
        else:
            issues.append("AG/VERDIEPINGEN ONTBREKEN -> 1 bouwlaag met 0 m2 gezet: vul de echte "
                          "m² per verdieping in Vabi in (anders bleven de sjabloon-verdiepingen staan).")
    # 3b) Gebouw-niveau: Gebouwhoogte = HANDMATIGE opname-invoer (gebouwhoogte_m, tot de nok).
    # GEEN fallback op gevelhoogte of berekening (eis Renze 12-7) en NOOIT de sjabloonwaarde laten
    # staan (sjabloon-lek): ontbreekt de invoer -> 0 + luide actie.
    # Gebouwtype/Ligging zijn ENUMS zonder bevestigde codes -> niet gokken (golden rule), flaggen.
    gh = getattr(getattr(dos, "opname", None), "gebouwhoogte_m", None)
    gh_node = next((e for e in root.iter() if _local(e.tag) == "Gebouwhoogte"), None)
    if gh_node is not None:
        if gh and float(gh) > 0:
            gh_node.text = "%.2f" % float(gh)
        else:
            gh_node.text = "0"
            issues.append("GEBOUWHOOGTE ONTBREEKT -> 0 gezet: meet/vul de gebouwhoogte tot de nok "
                          "in (MagicPlan-veld 'Gebouwhoogte tot de nok (m)') of zet hem in Vabi.")
    wt = getattr(getattr(dos, "identificatie", None), "woningtype", "")
    td = getattr(getattr(dos, "identificatie", None), "type_dak", "") or \
         getattr(getattr(dos, "opname", None), "type_dak", "")
    if wt:
        # Gebouwtype/Subtype (woningpositie) — LIVE GEVERIFIEERD in EPA (18-7): schrijf de bevestigde
        # codes i.p.v. flaggen. Nij Begun = grondgebonden eengezinswoningen -> Gebouwtype 0 (Eengezins-
        # woning), Subtype = woningpositie. Ligging is appartement-only (nvt bij eengezinswoning) -> laat
        # de sjabloon-default staan (die importeert bewezen foutloos; niet nodeloos aanpassen).
        st = _subtype_code(wt)
        if st is not None:
            for _tag, _val in (("Gebouwtype", GEBOUWTYPE_EENGEZINSWONING), ("Subtype", st)):
                _n = next((e for e in root.iter() if _local(e.tag) == _tag), None)
                if _n is not None:
                    _n.text = _val
        else:
            # meergezins/onbekende positie -> niet gokken (golden rule): sjabloon-default + flag
            issues.append("Woningpositie uit woningtype=%r niet herkend (geen grondgebonden "
                          "eengezinswoning?) -> Gebouwtype/Subtype op de sjabloon; zet ze in Vabi." % wt)
    else:
        # audit 15-7: leeg woningtype liet Gebouwtype/Subtype stil op de sjabloon staan (geen flag)
        issues.append("WONINGTYPE ONTBREEKT -> Gebouwtype/Subtype blijven op de sjabloon staan; "
                      "kies het woningtype (webapp/MagicPlan) en zet de woningpositie in Vabi.")
    if td:
        # Daktype LIVE GEVERIFIEERD in EPA: 0=Hellend dak, 1=Deels plat dak, 2=Plat dak/zonder kap.
        tdl = td.lower()
        dc = ("1" if ("deels plat" in tdl or "gedeeltelijk plat" in tdl)
              else "2" if "plat" in tdl
              else "0" if any(k in tdl for k in ("hellend", "zadel", "lessenaar", "schild", "tent", "punt")) else None)
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
    assert_no_schil_kwaliteitsverklaring(dos)
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
