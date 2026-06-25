"""
Ventilatieberekening + balans volgens de **Nij Begun-vuistregels** (BBL-gebaseerd; bindend — een plan
dat afwijkt wordt afgekeurd). Zie ventilatie/nijbegun_vuistregels.md. NIET de NTA8800-nieuwbouwwaarde 0,9.
- Toevoer/capaciteit: **0,7 dm³/s·m² per verblijfsgebied** (bestaande bouw), **min 7 l/s per leefruimte**.
  Verblijfsgebied = woon-/slaap-/studeerkamer + (woon)keuken. ('nieuwbouw'=0,9 is alleen een variant.)
- Afvoer natte ruimten: keuken 21, badkamer 14, toilet 7, wasruimte 14 dm³/s.
- Balans: aan- en afvoer in balans (maatgevend = max(som toevoer, som afvoer)).
- Aanvullende vuistregels (checklist in het rapport): overstroom max 2 deuren, >=50% lucht van buiten,
  geen afvoerpunt in slaapkamer, >15 l/s onder deur -> deurrooster, afstand af/toevoer + rookkanaal, C4c.
Werkt op dossier.geometrie.ruimtes (uit de MagicPlan-plattegrond).
"""
import os, sys, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.dossier import load_json  # noqa

RATE = {"bestaand": 0.7, "nieuwbouw": 0.9}   # Nij Begun = 'bestaand' (0,7 per verblijfsgebied)
MIN_LEEFRUIMTE = 7.0                          # iedere leefruimte minimaal 7 l/s
AFVOER = {"keuken": 21.0, "badkamer": 14.0, "toilet": 7.0, "wasruimte": 14.0}
# verblijfsgebied (krijgt toevoer): woon-/slaapkamer + (woon)keuken
TOEVOER_FUNCTIES = {"verblijfsruimte", "slaapkamer", "keuken"}
OVERSTROOM_DEURROOSTER_DM3S = 15.0           # >15 l/s onder een deur -> rooster in de deur (vuistregel 5)

# Bindende Nij Begun-vuistregels (checklist; zie ventilatie/nijbegun_vuistregels.md)
VUISTREGELS = [
    "Overstroom: lucht onder deuren door, maximaal onder 2 deuren.",
    "Minimaal 50% van alle lucht komt direct van buiten.",
    "Geen afvoerpunt in een slaapkamer (geen vuile lucht door de slaapkamer).",
    ">15 l/s onder een deur -> rooster in de deur (deurroosters nog niet in catalogus M29).",
    "Af- en toevoer niet te dicht bij elkaar (vermenging voorkomen).",
    "Toevoer niet te dicht bij een rookkanaal (~6-10 m horizontaal of 2 m hoogteverschil).",
    "C4c: CO2-sturing op de afvoer van woonkamer + hoofdslaapkamer.",
]

KEYWORDS = [
    ("keuken", ["keuken", "kitchen"]),
    ("badkamer", ["bad", "douche", "bathroom"]),
    ("toilet", ["toilet", "wc"]),
    ("wasruimte", ["was", "bijkeuken", "utility"]),
    ("verkeer", ["hal", "hallway", "overloop", "gang", "trap", "entree", "portaal", "vestibule", "corridor"]),
    ("slaapkamer", ["slaap", "bed"]),
    ("verblijfsruimte", ["woon", "living", "studeer", "kantoor", "eet", "zit", "room"]),
]


def classify(naam):
    n = (naam or "").lower()
    for functie, kws in KEYWORDS:
        if any(k in n for k in kws):
            return functie
    return "overig"


def bereken(ruimtes, situatie="bestaand"):
    """Ventilatieberekening + balans per Nij Begun-vuistregels. situatie 'bestaand'=0,7 (Nij Begun)."""
    rate = RATE.get(situatie, 0.7)
    rows = []
    toevoer_tot = afvoer_tot = 0.0
    waarschuwingen = []
    for r in ruimtes:
        functie = r.functie if (r.functie and r.functie != "overig") else classify(r.naam)
        opp = r.oppervlakte_m2 or 0
        toevoer = afvoer = 0.0
        if functie in TOEVOER_FUNCTIES:           # verblijfsgebied: 0,7*opp, min 7 l/s/leefruimte
            toevoer = max(round(opp * rate, 1), MIN_LEEFRUIMTE)
        if functie in AFVOER:                     # natte ruimte: vaste minimale afvoer
            afvoer = AFVOER[functie]
        if functie == "slaapkamer" and afvoer > 0:
            waarschuwingen.append("%s: afvoerpunt in slaapkamer is NIET toegestaan (vuistregel 3)." % r.naam)
        toevoer_tot += toevoer
        afvoer_tot += afvoer
        rows.append({"naam": r.naam, "functie": functie, "opp": opp, "toevoer": toevoer, "afvoer": afvoer})
    toevoer_tot = round(toevoer_tot, 1)
    afvoer_tot = round(afvoer_tot, 1)
    maatgevend = round(max(toevoer_tot, afvoer_tot), 1)
    # overstroom = lucht die van de verblijfsruimten naar de natte ruimten stroomt (~ de afvoer die niet
    # rechtstreeks in de natte ruimte wordt toegevoerd). In dit model is alle toevoer direct van buiten,
    # dus de >=50%-van-buiten-regel is gehaald zolang elke verblijfsruimte eigen toevoer heeft.
    overstroom = round(min(toevoer_tot, afvoer_tot), 1)
    if afvoer_tot > toevoer_tot + 0.5:
        waarschuwingen.append("Afvoer (%.0f) > toevoer (%.0f) dm3/s: voeg toevoer (roosters/WTW-ventielen) "
                              "toe om de balans te halen." % (afvoer_tot, toevoer_tot))
    elif toevoer_tot > afvoer_tot + 0.5:
        waarschuwingen.append("Toevoer (%.0f) > afvoer (%.0f) dm3/s: voorzie voldoende afvoercapaciteit "
                              "in de natte ruimten." % (toevoer_tot, afvoer_tot))
    return {"situatie": situatie, "rate": rate, "rows": rows,
            "toevoer_totaal": toevoer_tot, "afvoer_totaal": afvoer_tot,
            "overstroom_dm3s": overstroom,
            "maatgevend_dm3s": maatgevend, "maatgevend_m3h": round(maatgevend * 3.6, 0),
            "vuistregels": VUISTREGELS, "waarschuwingen": waarschuwingen}


def rapport(res):
    L = ["VENTILATIEBEREKENING — Nij Begun-vuistregels (BBL); %.1f dm3/s.m2 per verblijfsgebied"
         % res["rate"],
         "%-22s %-15s %7s %9s %8s" % ("Ruimte", "Functie", "opp m2", "toevoer", "afvoer")]
    for r in res["rows"]:
        L.append("%-22s %-15s %7.1f %9.1f %8.1f" % (r["naam"][:22], r["functie"], r["opp"], r["toevoer"], r["afvoer"]))
    L.append("-" * 64)
    L.append("%-38s %9.1f %8.1f  dm3/s" % ("TOTAAL", res["toevoer_totaal"], res["afvoer_totaal"]))
    L.append("Overstroom (verblijf -> nat): %.1f dm3/s" % res["overstroom_dm3s"])
    L.append("Maatgevende ventilatiehoeveelheid (balans): %.1f dm3/s  (~%.0f m3/h)"
             % (res["maatgevend_dm3s"], res["maatgevend_m3h"]))
    for w in res.get("waarschuwingen", []):
        L.append("  [!] " + w)
    L.append("")
    L.append("Vuistregels (toetsen vóór indienen — Nij Begun keurt af bij afwijking):")
    for v in res.get("vuistregels", []):
        L.append("  - " + v)
    return "\n".join(L)


def main():
    here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
    ap = argparse.ArgumentParser()
    ap.add_argument("--dossier", default=os.path.join(root, "sample_dossier.json"))
    ap.add_argument("--situatie", default="bestaand", choices=list(RATE))
    a = ap.parse_args()
    dos = load_json(a.dossier)
    res = bereken(dos.geometrie.ruimtes, a.situatie)
    print(rapport(res))


if __name__ == "__main__":
    main()
