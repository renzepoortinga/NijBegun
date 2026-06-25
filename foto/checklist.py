"""
Foto-checklist generator (Handleiding Fotowerkwijze Isolatieplan).
Geeft per voorgestelde maatregel de vereiste foto's + algemene foto's, als checklist
voor op locatie en voor het verplichte fotoblad in het dossier.
"""
import os, sys, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.dossier import load_json  # noqa

FOTO_EISEN = {
    "V1-1": ["Overzichtsfoto per gevel", "Foto boorgat + binnenzijde spouw (endoscoop)",
             "Foto voegwerk", "Foto bijzonderheden (betonlatei, overkapping)",
             "Indien hoogwerker nodig: foto staplaats"],
    "V1-2": ["Overzichtsfoto per gevel", "Foto aansluiting maaiveld", "Foto aansluiting dakrand"],
    "V1-3": ["Overzichtsfoto per ruimte", "Foto aansluitingen (gevel/plafond, gevel/vloer, gevel/kozijn)",
             "Detailfoto cat.2 (WCD, leidingwerk, radiatoren)"],
    "V2": ["Overzichtsfoto's van alle gevels met glas", "Foto van de glaslat"],
    "V3-1": ["Foto in de kruipruimte", "Foto diepte kruipruimte (duimstok/rolmaat zichtbaar)",
             "Foto kruipluik + locatie"],
    "V3-2": ["Overzichtsfoto van de vloer", "Foto aansluiting dak/muur"],
    "V4-1": ["Overzichtsfoto dakvlak (binnenzijde)", "Foto aansluitingen/dakdoorvoeren",
             "Foto gordingdikte (max isolatiedikte)"],
    "V4-2": ["Overzichtsfoto plat dak", "Foto dakranden/aansluitingen"],
    "V5": ["Foto ventilatie-unit/box", "Foto roosters en afvoerpunten (keuken/bad/toilet)"],
}
ALGEMEEN = [
    "Voorbladfoto: vooraanzicht van de woning (moet overeenkomen met het adres)",
    "Huisnummerfoto (dossier-marker; start van de opname)",
    "Overzichtsfoto per bouwdeel van de thermische schil",
    "Per categorie 2-post minimaal 1 detailfoto (aansluitingen, naden, leidingen)",
    "Per categorie 3-post minimaal 1 detailfoto (moeilijke aansluitingen, schades)",
]

def prefix_for(code):
    for p in ("V1-1", "V1-2", "V1-3", "V3-1", "V3-2", "V4-1", "V4-2", "V2", "V5"):
        if code.startswith(p):
            return p
    return code[:2]

def generate(dossier):
    L = ["FOTO-CHECKLIST (Fotowerkwijze Isolatieplan)", "", "Algemeen / altijd:"]
    for f in ALGEMEEN:
        L.append("  [ ] " + f)
    seen = set()
    for m in dossier.maatregelen:
        p = prefix_for(m.code)
        if p in seen:
            continue
        seen.add(p)
        L.append("")
        L.append("%s  (%s):" % (m.code, m.omschrijving[:48]))
        for f in FOTO_EISEN.get(p, ["Overzichtsfoto + detailfoto van de maatregel"]):
            L.append("  [ ] " + f)
    L.append("")
    L.append("LET OP: geen persoonlijke bezittingen/bewoners in beeld; scherp, recht, goed belicht.")
    L.append("Alle foto's + ingevuld formulier naar de kwaliteitscommissie.")
    return "\n".join(L)

def main():
    here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
    ap = argparse.ArgumentParser()
    ap.add_argument("--dossier", default=os.path.join(root, "sample_dossier_auto.json"))
    a = ap.parse_args()
    print(generate(load_json(a.dossier)))

if __name__ == "__main__":
    main()
