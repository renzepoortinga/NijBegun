"""
VABI NTA8800-monitoringbestand (XML) -> canoniek dossier (parser).
Transparante delen (Raam/Deur/Paneel) hebben de U/g inline; opaak (Dicht) heeft Rc.
Generator (canoniek -> importeerbare XML) = volgende iteratie (vergt XSD + import-test EPA-W).
"""
import os, sys, argparse
from lxml import etree
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.dossier import (Dossier, Identificatie, Geometrie, Berekening, SchilDeel, save_json)  # noqa

def L(e): return etree.QName(e).localname
def first(e, name):
    if e is None: return None
    for d in e.iter():
        if L(d) == name: return d
    return None
def child(e, name):
    if e is None: return None
    for d in e:
        if L(d) == name: return d
    return None
def txt(e, name, cast=None):
    d = first(e, name) if e is not None else None
    if d is None or d.text is None: return None
    s = d.text.strip()
    if not s: return None
    try: return cast(s) if cast else s
    except ValueError: return None

def parse(path):
    root = etree.parse(path).getroot()
    main = first(root, "MainBuilding"); summary = first(root, "Summary")
    dos = Dossier()
    dos.identificatie = Identificatie(
        bag_vboid=txt(main, "BAGResidenceId") or "", postcode=txt(main, "ZipCode") or "",
        huisnummer=txt(main, "Number") or "", bouwjaar=txt(main, "ConstructionYear", int))
    dos.geometrie = Geometrie(
        gebruiksoppervlakte_ag_m2=(txt(summary, "Gebruiksoppervlakte", float)
                                   or txt(main, "SurfaceArea", float) or 0.0))
    # Standaard-toets = netto warmtebehoefte van de schil, niet de bredere energiebehoefte-indicator
    # (die installaties meeweegt); val terug op die laatste bij oudere exports zonder
    # NettoWarmtebehoefte. Zie vabi/result_reader.py voor dezelfde afweging.
    _nwb = txt(summary, "NettoWarmtebehoefte", float)
    dos.berekening = Berekening(
        kwh_m2_huidig=_nwb if _nwb is not None else txt(summary, "IndicatorEnergiebehoefte", float),
        standaard_eis_kwh_m2=txt(summary, "Standaard", float),
        label_huidig=txt(summary, "Labelklasse") or "",
        bron="Vabi EPA-W (NTA8800) monitoringbestand",
        indicator_type_huidig="NettoWarmtebehoefte" if _nwb is not None else "IndicatorEnergiebehoefte")
    schil = []
    for cd in root.iter():
        if L(cd) != "Constructiedeel": continue
        dicht = child(cd, "Dicht")
        trans = child(cd, "Raam")
        if trans is None: trans = child(cd, "Deur")
        if trans is None: trans = child(cd, "Paneel")
        is_kozijn = trans is not None
        oms = txt(cd, "Omschrijving") or ""
        vlaktype = (txt(cd, "Vlaktype") or "").lower()
        if is_kozijn: typ = "kozijn"
        elif "gevel" in vlaktype: typ = "gevel"
        elif "vloer" in vlaktype: typ = "vloer"
        elif "dak" in vlaktype: typ = "dak"
        else: typ = vlaktype or "gevel"
        schil.append(SchilDeel(
            id=txt(cd, "Guid") or "", type=typ, subtype=oms,
            begrenzing=txt(cd, "Begrenzing") or "", orientatie=txt(cd, "Orientatie") or "",
            oppervlakte_m2=txt(cd, "Oppervlakte", float) or 0.0,
            rc_huidig=(txt(dicht, "Rc", float) if dicht is not None else None),
            u_huidig=(txt(trans, "U", float) if trans is not None else None),
            isolatiedikte_mm=(txt(dicht, "Isolatiedikte", float) if dicht is not None else None),
            glastype=(txt(trans, "Beglazing") or "" if trans is not None else ""),
            kozijnmateriaal=(txt(trans, "Kozijnmateriaal") or "" if trans is not None else "")))
    dos.schil = schil
    return dos, root

def roundtrip_ok(root):
    s = etree.tostring(root); re_root = etree.fromstring(s)
    n1 = sum(1 for e in root.iter() if L(e) == "Constructiedeel")
    n2 = sum(1 for e in re_root.iter() if L(e) == "Constructiedeel")
    return n1, n2, n1 == n2

def main():
    here = os.path.dirname(os.path.abspath(__file__)); root_dir = os.path.dirname(here)
    ap = argparse.ArgumentParser()
    ap.add_argument("--xml", required=True)
    ap.add_argument("--out", default=os.path.join(root_dir, "out", "dossier_from_monitor.json"))
    a = ap.parse_args()
    dos, root = parse(a.xml)
    os.makedirs(os.path.dirname(a.out), exist_ok=True); save_json(dos, a.out)
    n1, n2, ok = roundtrip_ok(root)
    print("OK: " + a.out)
    print("  %s %s, bouwjaar %s | label %s | warmtebehoefte(schil) %s | Standaard %s | Ag %s m2" % (
        dos.identificatie.postcode, dos.identificatie.huisnummer, dos.identificatie.bouwjaar,
        dos.berekening.label_huidig, dos.berekening.kwh_m2_huidig,
        dos.berekening.standaard_eis_kwh_m2, dos.geometrie.gebruiksoppervlakte_ag_m2))
    print("  schildelen: %d (round-trip %d==%d:%s)" % (len(dos.schil), n1, n2, ok))
    for s in dos.schil[:8]:
        print("    %-7s %-16s %-4s opp=%.2f Rc=%s U=%s glas=%s" % (
            s.type, s.subtype[:16], s.orientatie, s.oppervlakte_m2, s.rc_huidig, s.u_huidig, s.glastype))

if __name__ == "__main__":
    main()
