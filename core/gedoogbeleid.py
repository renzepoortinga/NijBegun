"""
Gedoogbeleid vleermuizen / eDNA — provincie Groningen, per 1 juli 2026.

Bij SPOUWMUURISOLATIE in de provincie Groningen zijn eDNA-sporenonderzoek, 'natuurvrij maken' en een
alternatieve verblijfplaats VERPLICHT in het isolatieplan (werkwijze Nij Begun 1-7-2026, BRL IC-200).
Provincie Drenthe valt hier NIET onder: daar checkt de bewoner bij de gemeente of er een SMP is.

Besluit Renze (19-7-2026): de tool voegt deze codes NIET automatisch toe — de adviseur kiest ze zelf
uit de catalogus (V1-1-X13..X17). De tool geeft alleen een LUIDE reminder + bepaalt de provincie
(standaard Groningen; Drenthe wordt apart geflagd). Zo kan een verkeerde postcode-gok nooit stil een
verplichte maatregel toevoegen of weglaten.
"""

# Maatregelcodes uit de werkwijze (hoofdcategorie 1 Gevelisolatie), gesplitst op woningtype.
EDNA_CODES = {
    "V1-1-X13": "Natuurvrij maken tussen- of rijwoning",
    "V1-1-X14": "Natuurvrij maken hoek- of vrijstaande woning",
    "V1-1-X15": "eDNA sporenonderzoek tussen- of rijwoning",
    "V1-1-X16": "eDNA sporenonderzoek hoek- of vrijstaande woning",
    "V1-1-X17": "Alternatieve verblijfplaats (stelpost, altijd opnemen)",
}


def provincie_uit_postcode(postcode):
    """(provincie, onzeker) uit de postcode. Default 'Groningen' (veilige kant: dan volgt de eDNA-
    reminder). Duidelijke Drenthe-ranges -> 'Drenthe'. Grensgebied 93xx -> 'Groningen' + onzeker=True.
    Het blijft een SIGNAAL: de adviseur bevestigt de provincie altijd zelf."""
    pc = "".join(ch for ch in (postcode or "") if ch.isdigit())[:4]
    if len(pc) < 4:
        return ("Groningen", True)                      # onbekend -> default + verifieer
    n = int(pc)
    if (7700 <= n <= 7999) or (9400 <= n <= 9499):      # Zuid/Midden-Drenthe + Assen (eenduidig)
        return ("Drenthe", False)
    if 9300 <= n <= 9399:                               # Roden/Leek e.o. = grens Groningen/Drenthe
        return ("Groningen", True)
    return ("Groningen", False)                         # 95xx-99xx e.d. = Groningen


def gedoogbeleid_reminders(postcode, spouwmuurisolatie_geadviseerd):
    """Lijst reminder-strings voor het isolatieplan/de webapp. Leeg als er geen spouwmuurisolatie
    speelt. De adviseur kiest de codes zelf; dit herinnert er alleen aan (besluit Renze 19-7)."""
    if not spouwmuurisolatie_geadviseerd:
        return []
    provincie, onzeker = provincie_uit_postcode(postcode)
    msgs = []
    if provincie == "Drenthe":
        msgs.append(
            "GEDOOGBELEID — postcode %s valt in provincie DRENTHE: eDNA is GEEN verplicht onderdeel. "
            "Laat de bewoner bij de gemeente checken of er een soortenmanagementplan (SMP) is. "
            "(Alleen provincie Groningen valt onder het eDNA-gedoogbeleid van 1-7-2026.)" % (postcode or "?"))
    else:
        msgs.append(
            "GEDOOGBELEID GRONINGEN — spouwmuurisolatie geadviseerd. Voeg ZELF de verplichte codes toe "
            "in de maatregelen (staan in de catalogus, hoofdcat. 1 Gevel): 'natuurvrij maken' "
            "(V1-1-X13 tussen-/rij of V1-1-X14 hoek-/vrijstaand), 'eDNA sporenonderzoek' conform "
            "BRL IC-200 (V1-1-X15 tussen-/rij of V1-1-X16 hoek-/vrijstaand) en ALTIJD 'alternatieve "
            "verblijfplaats' (V1-1-X17). Kies de tussen-/rij- of hoek-/vrijstaand-variant op woningtype.")
        if onzeker:
            msgs.append(
                "LET OP: postcode %s ligt in het grensgebied Groningen/Drenthe — controleer de provincie. "
                "Bij Drenthe geldt het eDNA-gedoogbeleid niet." % (postcode or "?"))
    return msgs
