"""
Voorschot-factuur-specificatie voor de Provincie Groningen (opdracht isolatieplannen 2026).

Opdrachtbrief 2026-102825: per opgesteld isolatieplan geldt een vast adviestarief (excl. btw),
afhankelijk van woningtype x Basis/Uitgebreid. LET OP (Startpakket Isolatieadviseur, maart 2026):
  **Basis     = woning gebouwd VANAF 1 januari 1945**
  **Uitgebreid = woning gebouwd VÓÓR  1 januari 1945**
"Het bouwjaar bepaalt of het B of U tarief van toepassing is en NIET de kwalificatie van de adviseur."
Gebruik dus `uitgebreid_uit_bouwjaar()` en niet het opnametype. Een voorschot bedraagt 75% van de
totale kosten en
kan worden aangevraagd op ingediende (nog niet goedgekeurde) plannen. De voorschotfactuur moet een
specificatie op adresniveau bevatten (postcode, huisnummer, bedrag) en de vaste factuurgegevens.

De tool levert de SPECIFICATIE; de daadwerkelijke factuur (XML+PDF) dient Renze in bij
crediteurenadministratie@provinciegroningen.nl.
"""

# Vaste factuurgegevens uit de opdrachtbrief (verplicht op elke factuur).
FACTUUR_HEADER = {
    "aan": "Provincie Groningen — basisteam Herstel en Perspectief",
    "tav": "Danielle Hughes-Ross",
    "vpl_nummer": "VPL-015187",
    "documentnummer_opdracht": "2026-102825",
    "email": "crediteurenadministratie@provinciegroningen.nl",
    "kenmerk": "Voorschot isolatieplannen Nij Begun",
    "btw_pct": 21,
    "voorschot_pct": 75,
}

# Adviestarief EXCL. btw per bucket: (Basis, Uitgebreid). Bron: opdrachtbrief 2026 Poortinga.
_TARIEF = {
    "vrijstaand_groot": (750.0, 825.0),   # Vrijstaand > 300 m2
    "vrijstaand_klein": (625.0, 700.0),   # Vrijstaand < 300 m2
    "hoek_2onder1kap":  (500.0, 575.0),   # 2-onder-1-kap / hoek-/eind-/kopwoning
    "tussen":           (350.0, 425.0),
    "meergezins":       (325.0, 400.0),
    "repeterend":       (250.0, 325.0),
}


def _bucket(woningtype, ag_m2):
    w = (woningtype or "").strip().lower()
    if "vrijstaand" in w:
        return "vrijstaand_groot" if (ag_m2 or 0) > 300 else "vrijstaand_klein"
    if "tussen" in w:
        return "tussen"
    if "meergezins" in w or "appartement" in w:
        return "meergezins"
    if "repeter" in w:
        return "repeterend"
    if any(k in w for k in ("hoek", "kop", "eind", "twee", "2-onder", "2 onder", "onder een kap", "2^1")):
        return "hoek_2onder1kap"
    return None


def uitgebreid_uit_bouwjaar(bouwjaar):
    """True = U-tarief (woning gebouwd VÓÓR 1-1-1945), False = B-tarief (vanaf 1945).
    None als het bouwjaar ontbreekt -> de aanroeper moet dat flaggen i.p.v. gokken (scheelt geld)."""
    if bouwjaar in (None, "", 0):
        return None
    try:
        return int(bouwjaar) < 1945
    except (TypeError, ValueError):
        return None


def tarief_excl(woningtype, ag_m2, uitgebreid):
    """Adviestarief excl. btw, of None als het woningtype niet herkend wordt (dan flaggen)."""
    b = _bucket(woningtype, ag_m2)
    return None if b is None else _TARIEF[b][1 if uitgebreid else 0]


def build_specificatie(plannen):
    """plannen: iterable van dicts met postcode, huisnummer, woningtype, ag_m2, uitgebreid (bool).
    -> dict met regels (per plan: adres, woningtype, tarief_excl), onbekende plannen (woningtype niet
    herkend), en totalen: subtotaal_excl, voorschot 75% excl, 21% btw, totaal incl."""
    regels, onbekend = [], []
    for p in plannen:
        adres = ("%s %s" % ((p.get("postcode") or "?").strip(), (p.get("huisnummer") or "?"))).strip()
        t = tarief_excl(p.get("woningtype"), p.get("ag_m2"), bool(p.get("uitgebreid")))
        if t is None:
            onbekend.append({"adres": adres, "woningtype": p.get("woningtype", "")})
            continue
        regels.append({"adres": adres, "woningtype": p.get("woningtype", ""),
                       "uitgebreid": bool(p.get("uitgebreid")), "tarief_excl": round(t, 2)})
    subtotaal = round(sum(r["tarief_excl"] for r in regels), 2)
    pct = FACTUUR_HEADER["voorschot_pct"] / 100.0
    voorschot_excl = round(subtotaal * pct, 2)
    btw = round(voorschot_excl * FACTUUR_HEADER["btw_pct"] / 100.0, 2)
    return {
        "regels": regels, "onbekend": onbekend,
        "subtotaal_excl": subtotaal,
        "voorschot_excl": voorschot_excl,
        "btw": btw,
        "totaal_incl": round(voorschot_excl + btw, 2),
        "header": FACTUUR_HEADER,
    }
