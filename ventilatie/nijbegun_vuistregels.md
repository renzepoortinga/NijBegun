# Nij Begun — Vuistregels voor ventilatie (BINDEND)

Bron: adviseurs-nijbegun.nl/support/solutions/articles/206000062898 ("Vuistregels voor ventilatie",
gewijzigd 23 mrt 2026). **Een plan dat hiervan afwijkt wordt afgekeurd.** Gebaseerd op het **Besluit
bouwwerken en leefomgeving (BBL)** waaraan Nij Begun zich committeert. Te hanteren bron voor detail:
ISSO-kleintje Ventilatie. Dit is de leidende ventilatiemethode voor de tool (NIET de NTA8800-nieuwbouw 0,9).

## Toevoer / capaciteit
- **0,7 dm³/s·m² per VERBLIJFSGEBIED** (bestaande bouw; niet 0,9).
- **Iedere leefruimte: minimaal 7 l/s.**
- Toevoer via roosters (raambreedte bepaalt rooster-lengte) of WTW-toevoerventielen; evt. dakraam-toevoer.
  Zelfregulerende roosters: vastleggen. Onvoldoende roosters → ramen vervangen of gevel-/dakdoorvoer
  (duur, comfort, (nog) niet in catalogus M29).

## Minimale afvoer (natte ruimten)
- **Keuken 21 · Badkamer 14 · Toilet 7 l/s.** Afvoerpunten zitten altijd in de natte ruimten; extra punt
  kan in bijkeuken/zolder/cv-ruimte. Houd rekening met ventielgeluid en max debiet per ventiel.

## Stappenplan
1. Bepaal oppervlakte ruimte. 2. Bepaal minimale afvoer (met keuken/bad/toilet-eisen, leefruimte min 7).
3. Plaats afvoerpunten (natte ruimten). 4. Bepaal toevoer (roosters/WTW). 5. Aan- en afvoer in **balans**.

## Aanvullende (binnende) regels
1. **Overstroom**: lucht onder deuren door — **max onder 2 deuren**.
2. **Minimaal 50%** van alle lucht moet van **buiten** komen.
3. **Nooit afvoerpunt in een slaapkamer** (geen vuile lucht door slaapkamer zuigen).
4. Raambreedte bepaalt toevoer via roosters; evt. geveldoorvoer (niet in catalogus M29).
5. **>15 l/s onder een deur → rooster in de deur** (deurroosters (nog) niet in catalogus M29).
6. Luchtverplaatsing maakt geluid → let op locatie afvoerpunten.
7. Af- en toevoer niet te dicht bij elkaar (vermenging voorkomen).
8. Toevoer via roosters óf WTW-ventielen.
9. Toevoer niet te dicht bij rookkanaal: ~6–10 m horizontaal of 2 m hoogteverschil.
10. C4c: CO₂-sturing op de **afvoer** van woonkamer + hoofdslaapkamer.

> Implicatie voor `ventilatie/ventilatie.py`: rate = **0,7 per verblijfsgebied** (min 7 l/s/leefruimte),
> afvoer keuken21/bad14/toilet7, balans (aan=afvoer), + de aanvullende regels (overstroom max 2,
> ≥50% buiten, geen afvoer slaapkamer, >15 l/s→deurrooster). De verzonnen `MAX_AFVOER_PER_VENTIEL=14`
> heeft géén basis in deze vuistregels → vervangen door ISSO-kleintje-waarde of flag.
