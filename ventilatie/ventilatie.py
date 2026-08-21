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

`bereken()` geeft per ruimte behalve toevoer/afvoer ook `afvoerpunt` (bool), `toevoer_herkomst`
('oppervlakte'|'minimum'|None) en `afvoer_herkomst`/`afvoer_advies_ls` (aanvankelijk gelijk aan het
minimum). `verdeel_balans(res)` hoogt de afvoer van de natte ruimten op tot de som gelijk is aan de
toevoer (naar rato van elke ruimte z'n minimum, `afvoer_herkomst` wordt dan 'balansophoging') —
zie docs/decisions/0002-ventilatie-afronding.md voor de afrondingskeuze. `deurbelasting(res, topologie)`
en `toets_vuistregels(res, plan)` toetsen resp. de overstroombelasting per deur en alle 7 vuistregels;
zie hun eigen docstrings voor het formaat van `topologie`/`plan` (nog geen dossiermodel — komt met de
tekenlaag in taak 020).
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
    # BERGING/OPSLAG vóór 'verblijfsruimte' — anders matcht 'Storage Room'/'Closet' op het brede
    # trefwoord 'room' en krijgt een bergruimte ten onrechte 0,7 dm3/s.m2 toevoer.
    # ISSO 82.1 §6.3.1: het WERKELIJK GEBRUIK is leidend (bergzolder = geen verblijfsgebied).
    ("overig", ["berging", "storage", "opslag", "kast", "closet", "schuur", "meterkast",
                "zolder", "attic", "vliering", "kruipruimte", "garage"]),
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
        toevoer_herkomst = None
        # verblijfsgebied: 0,7*opp, min 7 l/s/leefruimte. De vloer van 7 l/s geldt alleen als de ruimte
        # ook echt oppervlak heeft — een 0 m2-ruimte (bv. een 'Keuken'-regel die alleen dient om de
        # afvoereis vast te leggen omdat het oppervlak al in een andere ruimte is meegemeten) mag geen
        # fantoom-toevoer krijgen. Maar 0 m2 kan ook een kapotte opname zijn (oppervlakte niet
        # doorgekomen uit MagicPlan) — dat mag nooit stil 0 l/s worden, dus altijd een waarschuwing.
        if functie in TOEVOER_FUNCTIES:
            if opp > 0:
                opp_toevoer = round(opp * rate, 1)
                toevoer = max(opp_toevoer, MIN_LEEFRUIMTE)
                toevoer_herkomst = "oppervlakte" if opp_toevoer >= MIN_LEEFRUIMTE else "minimum"
            else:
                # toon het WERKELIJKE getal (kan ook negatief zijn, bv. een MagicPlan-editfout) —
                # anders claimt de melding '0 m2' terwijl er iets ergers aan de hand is (gevonden
                # in code review bij taak 020).
                waarschuwingen.append("%s: %.1f m2 geregistreerd (%s) — toevoer niet meegerekend; "
                    "controleer of het oppervlak elders is meegeteld of dat de opname ontbreekt."
                    % (r.naam, opp, functie))
        afvoerpunt = functie in AFVOER
        if afvoerpunt:                             # natte ruimte: vaste minimale afvoer
            afvoer = AFVOER[functie]
        if functie == "slaapkamer" and afvoer > 0:
            waarschuwingen.append("%s: afvoerpunt in slaapkamer is NIET toegestaan (vuistregel 3)." % r.naam)
        toevoer_tot += toevoer
        afvoer_tot += afvoer
        rows.append({"naam": r.naam, "functie": functie, "opp": opp, "toevoer": toevoer, "afvoer": afvoer,
                     "toevoer_herkomst": toevoer_herkomst, "afvoerpunt": afvoerpunt,
                     "afvoer_advies_ls": afvoer, "afvoer_herkomst": "minimum" if afvoerpunt else None})
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


def verdeel_balans(res):
    """Hoogt de afvoer per natte ruimte op tot de som gelijk is aan de toevoer (zoals een geïnstalleerd
    ventilatiesysteem dat ook moet: de afzuigcapaciteit moet minstens de toevoer bijhouden). Puur —
    retourneert een NIEUWE resultaatdict, wijzigt `res` niet.

    Verdeling: naar rato van elke natte ruimte z'n eigen minimum-afvoer (grotere minimale afnemers als
    de keuken krijgen dus het grootste deel van het tekort — 'de keuken als grootste afnemer'), met de
    grootste-restmethode (Hamilton/largest remainder) in eenheden van 0,1 l/s: elke regel krijgt eerst
    naar beneden afgeronde eenheden, de resterende eenheden gaan één voor één naar de regels met de
    grootste afgeronde fractie. Zo sluit de som altijd exact ÉN kan geen enkele regel door de afronding
    onder zijn eigen aandeel zakken (een simpele 'grootste afnemer krijgt de rest' bleek dat wél te
    kunnen doen bij >=5 natte ruimten — vaste-punt-rondingsfout, gevonden in code review).

    Doet niets als de afvoerminima al gelijk zijn aan of groter dan de toevoer — dan is er geen tekort
    om te verdelen (ophogen van de toevoer zelf is geen onderdeel van deze functie).
    """
    rows = [dict(r) for r in res.get("rows", [])]
    natte = [r for r in rows if r["afvoerpunt"]]
    som_min = round(sum(r["afvoer"] for r in natte), 1)
    tekort = round(res.get("toevoer_totaal", 0.0) - som_min, 1)
    if natte and tekort > 0 and som_min > 0:
        eenheden_tekort = round(tekort * 10)                  # in stappen van 0,1 l/s (gehele getallen)
        ruw = [eenheden_tekort * (r["afvoer"] / som_min) for r in natte]
        eenheden = [int(x) for x in ruw]                       # naar beneden afgerond, dus nooit negatief
        rest = eenheden_tekort - sum(eenheden)
        volgorde = sorted(range(len(natte)), key=lambda i: ruw[i] - eenheden[i], reverse=True)
        for i in range(rest):
            eenheden[volgorde[i % len(volgorde)]] += 1
        for r, e in zip(natte, eenheden):
            deel = round(e / 10.0, 1)
            r["afvoer_advies_ls"] = round(r["afvoer"] + deel, 1)
            if deel > 0:
                r["afvoer_herkomst"] = "balansophoging"
    afvoer_advies_totaal = round(sum(r["afvoer_advies_ls"] for r in natte), 1)
    nieuw = dict(res)
    nieuw["rows"] = rows
    nieuw["afvoer_advies_totaal"] = afvoer_advies_totaal
    return nieuw


def deurbelasting(res, topologie):
    """Berekent per overstroomweg de l/s onder elke deur (vuistregel 5: >15 l/s -> deurrooster).

    `topologie` is een lijst van overstroomwegen; elke weg is een lijst ruimtenamen die BEGINT bij de
    natte ruimte met het afvoerpunt en vervolgens de ruimten opsomt waar de lucht doorheen naar buiten/
    de supply-ruimte stroomt, bv. `["Badkamer", "Overloop"]` of bij een langere weg
    `["Badkamer", "Overloop", "Woonkamer"]`. Er is geen adjacency-data in het dossier (die komt pas met
    de tekenlaag, taak 020) — de aanroeper levert de topologie aan.

    De l/s onder elke deur op een weg = de advies-afvoer van de natte ruimte aan het begin van de weg
    (massabalans: die lucht moet van de aangrenzende ruimte onder de deur door naar binnen om de afzuiging
    te voeden; overstroomlucht wordt zelf niet afgezogen, dus elke deur op de weg draagt dezelfde last).
    Geef `res` liefst NA `verdeel_balans` mee, anders wordt de kale minimum-afvoer gebruikt.

    Een ruimtenaam in `topologie` die niet in `res['rows']` voorkomt (tikfout, of losgeraakt van de
    geometrie) is een fout in de aanroep, geen 'geen belasting' — die wordt niet stilgehouden als 0 l/s
    (dan zou toets_vuistregels vuistregel 4 een node deurrooster kunnen missen) maar geeft een harde
    ValueError.
    """
    by_naam = {r["naam"]: r for r in res.get("rows", [])}
    regels = []
    for pad in topologie:
        if len(pad) < 2:
            continue
        # ALLE ruimten op de weg controleren, niet alleen het begin — een tikfout verderop in het
        # pad (de 'naar'-kant van een deur) mag net zo min stil doorglippen (gevonden in code
        # review bij taak 020: dit valideerde eerder alleen pad[0]).
        onbekend = [naam for naam in pad if naam not in by_naam]
        if onbekend:
            raise ValueError("deurbelasting: ruimte(s) %s (in een overstroomweg) komen niet voor "
                              "in res['rows']." % ", ".join(repr(n) for n in onbekend))
        eind = by_naam[pad[0]]
        ls = round(eind.get("afvoer_advies_ls", eind.get("afvoer", 0.0)), 1)
        boven = ls > OVERSTROOM_DEURROOSTER_DM3S
        for a, b in zip(pad, pad[1:]):
            regels.append({
                "van": a, "naar": b, "ls": ls, "boven_norm": boven,
                "tekst": "%s-%s: %.1f l/s%s" % (a, b, ls,
                          " (>15 l/s), deurrooster geadviseerd" if boven else "")})
    return regels


def toets_vuistregels(res, plan=None):
    """Toetst alle 7 Nij Begun-vuistregels tegen `res` (het resultaat van `bereken()`, liefst na
    `verdeel_balans`) en optioneel `plan` — een dict met geometrie-/installatiekeuzes die niet uit de
    ventilatieberekening zelf komen (nog geen dossiermodel, zie taak 020):
      topologie: lijst overstroomwegen, zie `deurbelasting()`.
      deurroosters: verzameling "Van-Naar"-strings van deuren die al een rooster hebben.
      afstand_toe_afvoer_m: kleinste gemeten afstand tussen een toevoer- en afvoerpunt (m).
      afstand_rookkanaal_m / hoogteverschil_rookkanaal_m: afstand resp. hoogteverschil toevoer-rookkanaal.
      co2_sturing_woonkamer / co2_sturing_hoofdslaapkamer: bool, CO2-sturing (C4c) aanwezig.

    Geeft voor elke vuistregel status 'voldoet' | 'voldoet niet' | 'niet te bepalen' + reden. Ontbrekende
    geometrie/installatiekeuzes leveren ALTIJD 'niet te bepalen' — nooit een stille 'voldoet' (taak 019).
    """
    plan = plan or {}
    topologie = plan.get("topologie")
    uitkomsten = []  # (status, reden), in dezelfde volgorde als VUISTREGELS

    # 1. Overstroom: max 2 deuren op een weg
    if not topologie:
        uitkomsten.append(("niet te bepalen", "Topologie (deuren tussen ruimten) niet aangeleverd."))
    else:
        hops = [len(p) - 1 for p in topologie if len(p) >= 2]
        if not hops:
            uitkomsten.append(("niet te bepalen", "Topologie bevat geen bruikbare overstroomwegen."))
        elif max(hops) <= 2:
            uitkomsten.append(("voldoet", "Langste overstroomweg is %d deur(en)." % max(hops)))
        else:
            uitkomsten.append(("voldoet niet", "Overstroomweg van %d deuren gevonden (max 2)." % max(hops)))

    # 2. Minimaal 50% van de lucht komt direct van buiten
    if res.get("toevoer_totaal", 0.0) > 0:
        uitkomsten.append(("voldoet", "Alle toevoer in dit rekenmodel komt rechtstreeks van buiten "
                                       "(roosters/WTW-ventielen); dat is altijd >=50%."))
    else:
        uitkomsten.append(("niet te bepalen", "Geen toevoer berekend."))

    # 3. Geen afvoerpunt in een slaapkamer
    slaapkamers = [r["naam"] for r in res.get("rows", []) if r.get("functie") == "slaapkamer" and r.get("afvoerpunt")]
    if slaapkamers:
        uitkomsten.append(("voldoet niet", "Afvoerpunt in slaapkamer: %s." % ", ".join(slaapkamers)))
    else:
        uitkomsten.append(("voldoet", "Geen afvoerpunten in een slaapkamer."))

    # 4. >15 l/s onder een deur -> deurrooster
    if not topologie:
        uitkomsten.append(("niet te bepalen", "Topologie (deuren tussen ruimten) niet aangeleverd."))
    else:
        deuren = deurbelasting(res, topologie)
        if not deuren:
            uitkomsten.append(("niet te bepalen", "Topologie bevat geen bruikbare deuren."))
        else:
            aanwezig = set(plan.get("deurroosters") or [])
            ontbrekend = [d for d in deuren if d["boven_norm"] and "%s-%s" % (d["van"], d["naar"]) not in aanwezig]
            if ontbrekend:
                uitkomsten.append(("voldoet niet", "Deurrooster ontbreekt; deurrooster geadviseerd bij: %s." % ", ".join(
                    "%s-%s (%.1f l/s)" % (d["van"], d["naar"], d["ls"]) for d in ontbrekend)))
            else:
                uitkomsten.append(("voldoet", "Geen deur boven 15 l/s zonder rooster."))

    # 5. Af- en toevoer niet te dicht bij elkaar
    afstand = plan.get("afstand_toe_afvoer_m")
    if afstand is None:
        uitkomsten.append(("niet te bepalen", "Afstand toevoer-afvoer niet aangeleverd."))
    elif afstand >= 2.0:
        uitkomsten.append(("voldoet", "Kleinste afstand toevoer-afvoer is %.1f m." % afstand))
    else:
        uitkomsten.append(("voldoet niet", "Toevoer en afvoer liggen %.1f m uit elkaar (te dicht)." % afstand))

    # 6. Toevoer niet te dicht bij een rookkanaal
    afstand_rk = plan.get("afstand_rookkanaal_m")
    hoogte_rk = plan.get("hoogteverschil_rookkanaal_m")
    if afstand_rk is None and hoogte_rk is None:
        uitkomsten.append(("niet te bepalen", "Afstand/hoogteverschil tot rookkanaal niet aangeleverd."))
    elif (afstand_rk is not None and afstand_rk >= 6.0) or (hoogte_rk is not None and hoogte_rk >= 2.0):
        uitkomsten.append(("voldoet", "Toevoer ligt ver genoeg van het rookkanaal."))
    else:
        uitkomsten.append(("voldoet niet", "Toevoer ligt te dicht bij het rookkanaal."))

    # 7. C4c: CO2-sturing op de afvoer van woonkamer + hoofdslaapkamer
    co2_wk = plan.get("co2_sturing_woonkamer")
    co2_hs = plan.get("co2_sturing_hoofdslaapkamer")
    if co2_wk is None or co2_hs is None:
        uitkomsten.append(("niet te bepalen", "CO2-sturing woonkamer/hoofdslaapkamer niet aangeleverd."))
    elif co2_wk and co2_hs:
        uitkomsten.append(("voldoet", "CO2-sturing (C4c) aanwezig op woonkamer en hoofdslaapkamer."))
    else:
        uitkomsten.append(("voldoet niet", "CO2-sturing (C4c) ontbreekt op woonkamer en/of hoofdslaapkamer."))

    return [{"regel": regel, "status": status, "reden": reden}
            for regel, (status, reden) in zip(VUISTREGELS, uitkomsten)]


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
