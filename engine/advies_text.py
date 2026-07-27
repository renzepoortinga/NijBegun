"""
Maatregel-advies met BEGELEIDENDE TEKST (SOBOLT-achtig), deterministisch en OFFLINE (geen AI/tokens).
Zet het dossier + het gekozen maatregelpakket (engine) + optioneel het VABI-resultaat (result_reader)
om in adviseur-kwaliteit Nederlandse tekst voor het isolatieplan/rapport.

    from engine.advies_text import genereer_advies
    tekst = genereer_advies(dossier, maatregelen, resultaat_huidig=..., resultaat_na=...)

Ontwerp: per bouwdeel een vaste, vakinhoudelijke rationale (waarom isoleren, wat het oplevert,
aandacht voor ventilatie/vocht), aangevuld met de concrete maatregel (Rc/U-doel, m2, kosten).
Optioneel kan een LLM-hook de tekst later verrijken; de basis blijft tokenvrij en reproduceerbaar.
"""
from __future__ import annotations

# vakinhoudelijke rationale per onderdeel (A-E). Kort, feitelijk, adviseur-toon.
_RATIONALE = {
    "A": ("Gevelisolatie", "De gevel is vaak het grootste verliesoppervlak. Na-isolatie (spouw, "
          "binnen- of buitenzijde) verlaagt het warmteverlies fors en verhoogt het comfort doordat "
          "koudeval langs de wand verdwijnt."),
    "B": ("Glas en kozijnen", "Beter glas (HR++/triple) en kierdichte kozijnen verminderen verlies "
          "en tocht. Let op de balans met ventilatie: betere kierdichting vraagt om voldoende "
          "gecontroleerde toevoer."),
    "C": ("Vloerisolatie", "Vloerisolatie (bodem/kruipruimte of onderzijde vloer) haalt koude eruit "
          "en voelt direct comfortabeler. Combineer met bodemisolatie waar de kruipruimte dat toelaat."),
    "D": ("Dakisolatie", "Warmte stijgt; een ongeisoleerd dak is een groot lek. Dakisolatie levert "
          "veel rendement en is meestal goed uitvoerbaar bij hellend en plat dak."),
    "E": ("Ventilatie", "Isoleren maakt de woning luchtdichter; goede, gebalanceerde ventilatie "
          "(bij voorkeur met WTW) borgt een gezond binnenklimaat en voorkomt vocht/schimmel."),
}

# BOUWFYSISCHE AANDACHTSPUNTEN per bouwdeel (Praktijkboek Bouwfysica & bouwtechniek; Nij Begun-eis
# "technische haalbaarheid": dampremmende laag · ruimtefunctie onder een koud dak · ventilatie).
# Kernregel: een dampremmende laag hoort ALTIJD aan de WARME (binnen)zijde van de isolatie — ligt hij
# aan de koude zijde, dan ontstaat inwendige condensatie in de constructie.
_BOUWFYSICA = {
    "A": "Aandachtspunt: bij binnenisolatie (voorzetwand) hoort de dampremmende laag aan de warme "
         "binnenzijde; controleer waar houten vloerbalken in de gevel liggen (balkkoppen kunnen gaan "
         "rotten als ze in de koude zone belanden). Bij spouwisolatie eerst vochtdoorslag en open "
         "stootvoegen beoordelen.",
    "B": "Aandachtspunt: betere kierdichting verlaagt de natuurlijke toevoer — borg de ventilatie "
         "(roosters/WTW), anders verschuift het vochtprobleem naar het binnenklimaat.",
    "C": "Aandachtspunt: vochtige kruipruimtelucht kan inwendige condensatie in de vloerconstructie "
         "geven; combineer vloer-/bodemisolatie met een goed geventileerde kruipruimte en een "
         "dampremmende laag aan de warme zijde.",
    "D": "Aandachtspunt: isoleer je aan de binnenzijde van het dak, leg de dampremmende laag dan aan "
         "de warme binnenzijde en houd de ventilatiespouw boven de isolatie open. Let op de "
         "ruimtefunctie onder een koud dak (slaapkamer = meer vochtproductie).",
    "E": "Aandachtspunt: stem toe- en afvoer op elkaar af (balans) en zorg voor overstroom tussen de "
         "ruimten; een afzuiging zonder toevoer trekt vocht en koude via kieren naar binnen.",
}


def _euro(v):
    try:
        return "EUR %s" % format(int(round(v)), ",d").replace(",", ".")
    except (TypeError, ValueError):
        return "n.t.b."


def begeleidende_tekst(m):
    """Eén maatregel -> begeleidende alinea."""
    letter = (m.onderdeel or " ")[0].upper()
    titel, rationale = _RATIONALE.get(letter, (m.onderdeel or "Maatregel", ""))
    delen = [rationale] if rationale else []
    concreet = m.omschrijving or titel
    z = "Voorgesteld: %s" % concreet
    if m.rc_u_doel:
        z += " (streefwaarde %s)" % m.rc_u_doel
    if m.oppervlakte_m2:
        z += ", circa %.0f %s" % (m.oppervlakte_m2, m.eenheid)
    if m.kosten:
        z += ", indicatie %s" % _euro(m.kosten)
    z += "."
    delen.append(z)
    if m.biobased:
        delen.append("Biobased variant beschikbaar (natuurlijke isolatie).")
    bf = _BOUWFYSICA.get(letter)
    if bf:
        delen.append(bf)
    return " ".join(delen)


def _staat_regel(resultaat, label):
    if not resultaat:
        return None
    eb = resultaat.get("IndicatorEnergiebehoefte")
    std = resultaat.get("Standaard")
    lab = resultaat.get("Labelklasse")
    parts = []
    if lab:
        parts.append("energielabel %s" % lab)
    if eb:
        parts.append("energiebehoefte %s kWh/m2.jr" % eb)
    if std:
        parts.append("Standaard-eis %s kWh/m2.jr" % std)
    return "%s: %s." % (label, ", ".join(parts)) if parts else None


def genereer_advies(dossier, maatregelen, resultaat_huidig=None, resultaat_na=None):
    """Volledige adviestekst (markdown) voor het isolatieplan/rapport."""
    idf = dossier.identificatie
    adres = " ".join(x for x in [getattr(idf, "straat", ""), str(getattr(idf, "huisnummer", "") or ""),
                                 getattr(idf, "postcode", ""), getattr(idf, "plaats", "")] if x).strip()
    out = ["# Isolatieadvies", ""]
    if adres:
        out.append("**Woning:** %s" % adres)
    # huidige staat
    hs = _staat_regel(resultaat_huidig, "Huidige staat")
    if hs:
        out.append("**" + hs + "**")
    out.append("")
    out.append("## Toelichting")
    out.append("Onderstaand pakket brengt de woning met de **laagste investeringskosten** naar de "
               "Standaard voor woningisolatie. Isoleren en ventileren van de thermische schil is het "
               "uitgangspunt; Vabi EPA-W (geattesteerd) rekent de exacte waarden.")
    out.append("")
    # maatregelen per onderdeel, in vaste volgorde A-E
    out.append("## Voorgestelde maatregelen")
    order = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5}
    for m in sorted(maatregelen, key=lambda x: order.get((x.onderdeel or " ")[0].upper(), 9)):
        letter = (m.onderdeel or " ")[0].upper()
        titel = _RATIONALE.get(letter, (m.onderdeel or "Maatregel", ""))[0]
        out.append("### %s — %s" % (letter, titel))
        out.append(begeleidende_tekst(m))
        if m.subposten:
            out.append("")
            out.append("_Meerwerk (cat. 2/3) ter overweging:_ " +
                       "; ".join(sp.omschrijving for sp in m.subposten if getattr(sp, "omschrijving", "")))
        out.append("")
    # kosten + conclusie
    totaal = sum(m.kosten for m in maatregelen if m.kosten)
    if totaal:
        out.append("**Indicatieve totale investering (cat. 1): %s**" % _euro(totaal))
        out.append("")
    out.append("## Resultaat na maatregelen")
    na = _staat_regel(resultaat_na, "Na maatregelen")
    if na:
        out.append("**" + na + "**")
        voldoet = resultaat_na.get("_voldoet_aan_standaard")
        if voldoet is True:
            out.append("De woning **voldoet aan de Standaard** na uitvoering van dit pakket.")
        elif voldoet is False:
            out.append("De woning voldoet **nog niet** aan de Standaard; pakket uitbreiden of "
                       "kwaliteit verhogen (Vabi herrekenen).")
    else:
        out.append("_Herreken in Vabi met de toekomstige staat om de Standaard-toets te bevestigen._")
    out.append("")
    out.append("> Vabi EPA-W is en blijft de geattesteerde rekenkern; deze tekst is een toelichting "
               "bij de berekende waarden.")
    return "\n".join(out)


if __name__ == "__main__":
    # mini-demo met dummy-maatregelen
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.dossier import Maatregel, Dossier
    dos = Dossier()
    ms = [Maatregel(onderdeel="A Gevel", omschrijving="Spouwmuurisolatie", rc_u_doel="Rc 1.1",
                    oppervlakte_m2=60, kosten=1800, categorie=1),
          Maatregel(onderdeel="D Daken", omschrijving="Dakisolatie hellend", rc_u_doel="Rc 3.5",
                    oppervlakte_m2=55, kosten=4200, categorie=1, biobased=True),
          Maatregel(onderdeel="E Ventilatie", omschrijving="CO2-gestuurde mechanische afvoer (C.4)",
                    kosten=1500, categorie=1)]
    print(genereer_advies(dos, ms,
                          resultaat_huidig={"Labelklasse": "D", "IndicatorEnergiebehoefte": "165", "Standaard": "110"},
                          resultaat_na={"Labelklasse": "A", "IndicatorEnergiebehoefte": "98", "Standaard": "110", "_voldoet_aan_standaard": True}))
