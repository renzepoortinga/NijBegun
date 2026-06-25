"""
Parser: MagicPlan 'Project Statistics' CSV -> partieel canoniek dossier (geometrie).
LET OP: deze CSV bevat alleen geometrie (geen bouwfysica). De volledige opname
(forms/fields per schildeel) komt via de Project Plan API (zie extractor.py).
Deze parser is een bootstrap/fallback en vult geometrie + ruwe tellingen.
"""
import os, sys, csv, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.dossier import Dossier, Geometrie, VloerInfo, Ruimte, save_json  # noqa
from ventilatie.ventilatie import classify  # noqa

def fnum(s):
    if s is None:
        return None
    s = str(s).replace(" m³", "").replace(" m²", "").replace(" m", "").replace(",", ".").strip()
    try:
        return float(s)
    except ValueError:
        return None

def parse(path):
    with open(path, encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))
    plan = {}
    floors = []
    rooms = []
    section = None
    floor_hdr = None
    for r in rows:
        if not any(c.strip() for c in r):
            section = None
            continue
        head = r[0].strip()
        if head == "PLAN ATTRIBUTES":
            section = "plan"; continue
        if head.startswith("FLOOR ATTRIBUTES"):
            section = "floor"; floor_hdr = r; continue
        if head.startswith("ROOM ATTRIBUTES"):
            section = "room"; continue
        if head.endswith("ATTRIBUTES") or head in ("OBJECT COUNT", "Object Attributes"):
            section = "other"; continue
        if section == "plan" and len(r) >= 2:
            plan[head] = r[1].strip()
        elif section == "room" and len(r) >= 2 and head and fnum(r[1]) is not None:
            rooms.append({"naam": head, "oppervlakte_m2": fnum(r[1]) or 0.0, "functie": classify(head)})
        elif section == "floor" and len(r) >= 3 and head:
            floors.append({
                "naam": head,
                "oppervlakte_m2": fnum(r[1]) or 0.0,
                "hoogte_m": fnum(r[9]) if len(r) > 9 else None,
            })
    dos = Dossier()
    dos.geometrie = Geometrie(
        gebruiksoppervlakte_ag_m2=fnum(plan.get("Total living area: m²")) or 0.0,
        verwarmd_volume_m3=fnum(plan.get("Volume: m³")),
        perimeter_m=fnum(plan.get("Exterior perimeter: m")),
        vloeren=[VloerInfo(**f) for f in floors],
        ruimtes=[Ruimte(**rm) for rm in rooms],
    )
    meta = {
        "floors": plan.get("Floor"), "rooms": plan.get("Rooms"),
        "windows": plan.get("Windows"),
        "walls_with_openings_m2": fnum(plan.get("Walls with openings: m²")),
    }
    return dos, meta

def main():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", default=os.path.join(root, "out", "dossier_from_csv.json"))
    a = ap.parse_args()
    dos, meta = parse(a.csv)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    save_json(dos, a.out)
    g = dos.geometrie
    print("OK: " + a.out)
    print("  Ag(woonopp): %s m2 | volume: %s m3 | perimeter: %s m" % (
        g.gebruiksoppervlakte_ag_m2, g.verwarmd_volume_m3, g.perimeter_m))
    print("  bouwlagen: %d | ramen(tel): %s | rooms: %s" % (
        len(g.vloeren), meta.get("windows"), meta.get("rooms")))
    for v in g.vloeren:
        print("    vloer '%s': %.2f m2, hoogte %s m" % (v.naam, v.oppervlakte_m2, v.hoogte_m))
    print("  NB: bouwfysica (Rc/U/begrenzing/ventilatie) komt via de Project Plan API, niet uit deze CSV.")

if __name__ == "__main__":
    main()
