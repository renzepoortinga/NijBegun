"""
NTA 8800-geometrie/beleidsformules die de tool WEL zelf mag rekenen (geen warmtebalans):
  - verliesoppervlak(dos): gewogen verliesoppervlakte Als volgens NTA 8800 §6.7.3
  - standaard_eis(dos):     de Standaard voor woningisolatie volgens NTA 8800 §5.3.2

Gouden regel blijft: de energiebehoefte/Standaard-uitkomst komt uit Vabi (de rekenkern). Deze twee
functies zijn puur beleids-/geometrieformules uit de norm (geen NTA-warmtebalans) en dienen als
0-meting-verwachting + sanity-check op de geometrie (wijkt onze Als/Ag of het woningtype af, dan
klopt de opname niet). Zie docs/nta8800-analyse-vs-tool.md (punten A en B).
"""

# NTA 8800 §6.7.3 — weegfactoren fls voor de verliesoppervlakte:
#   fls = 0    inwendige scheiding / naar andere rekenzone of aangrenzende verwarmde ruimte (AVR)
#   fls = 0,7  naar de grond of een kruipruimte
#   fls = 1    buitenlucht, water, AOR, AOS, (aangrenzende) sterk geventileerde ruimte
_FLS_NUL = ("avr", "aangrenzende woning", "aangrenzende verwarmde ruimte", "andere rekenzone")
_FLS_GROND = ("grond", "kruipruimte", "kruip")


def fls(begrenzing):
    """Weegfactor fls voor één scheidingsconstructie (NTA 8800 §6.7.3)."""
    b = (begrenzing or "").strip().lower()
    if b in _FLS_NUL:
        return 0.0
    if any(k in b for k in _FLS_GROND):
        return 0.7
    return 1.0                     # buitenlucht/water/AOR/AOS/sterk geventileerd/onbekend (conservatief)


def verliesoppervlak(dos):
    """Gewogen verliesoppervlakte Als in m² (NTA 8800 §6.7.3).

    Grond/kruipruimte telt voor 0,7; AVR/woningscheidend voor 0; de rest voor 1,0. Kozijnen en
    panelen tellen NIET apart mee: de gevels zijn BRUTO (ramen/deuren zitten er al in), dus apart
    optellen zou dubbeltellen (beide hebben fls=1 naar buitenlucht → bruto-gevel = netto-gevel + raam).
    """
    return sum((s.oppervlakte_m2 or 0) * fls(s.begrenzing)
               for s in dos.schil if s.type not in ("kozijn", "paneel"))


# NTA 8800 §5.3.2 — grondgebonden woonfunctie vs. woonfunctie in een woongebouw (gestapeld).
_GESTAPELD = ("galerij", "portiek", "maisonnette", "appartement", "flat", "meergezins",
              "bovenwoning", "boven bedrijf", "gestapeld", "woongebouw")


def is_grondgebonden(woningtype):
    """True = grondgebonden woning (vrijstaand/2^1kap/hoek/tussen); False = woning in een woongebouw."""
    w = (woningtype or "").lower()
    return not any(k in w for k in _GESTAPELD)


# (basiswaarde, helling) per categorie — sleutel = (grondgebonden, bouwjaar t/m 1945)
_STANDAARD = {
    (True,  True):  (60, 105),     # grondgebonden, t/m 1945
    (True,  False): (43, 40),      # grondgebonden, na 1945
    (False, True):  (95, 70),      # woongebouw, t/m 1945
    (False, False): (45, 45),      # woongebouw, na 1945
}


def standaard_eis(dos):
    """Standaard voor woningisolatie in kWh/m²·jr (NTA 8800 §5.3.2), zelf voorgerekend.

    Alleen afhankelijk van Als/Ag, grondgebonden vs. woongebouw en bouwjaar (t/m 1945 of erna):
      Als/Ag < 1,0 → basiswaarde;  Als/Ag ≥ 1,0 → basiswaarde + helling × (Als/Ag − 1,0).
    Retourneert None als Ag of het bouwjaar ontbreekt (dan kan de norm de eis niet vaststellen).
    Bedoeld als 0-meting-verwachting en kruiscontrole op de Vabi-Standaard, NIET als vervanging.
    """
    ag = dos.geometrie.gebruiksoppervlakte_ag_m2 or 0
    bouwjaar = dos.identificatie.bouwjaar
    if not ag or bouwjaar is None:
        return None
    ratio = verliesoppervlak(dos) / ag
    base, slope = _STANDAARD[(is_grondgebonden(dos.identificatie.woningtype), bouwjaar <= 1945)]
    eis = base if ratio < 1.0 else base + slope * (ratio - 1.0)
    return round(eis)               # NTA §5.3.2: afronden op een geheel getal
