---
id: 019
assigned:
branch:
depends_on: []
---

# Task 019 — Ventilatie-rekenlaag uitbreiden (balans, deurbelasting, vuistregeltoets)

## Goal
De ventilatieberekening levert alles wat een tekenbaar ventilatieplan nodig heeft: een
sluitende balans per ruimte, de deurbelasting en een pass/fail op alle zeven Nij
Begun-vuistregels, met per waarde de herkomst.

## Scope
Alleen `ventilatie/ventilatie.py` plus tests. Geen webapp, geen tekening, geen PDF.

- `verdeel_balans(res)`: hoog de afvoer per natte ruimte op tot de som gelijk is aan de
  toevoer. Verdeel naar rato van het minimum, met de keuken als grootste afnemer. Elke
  ruimte houdt zijn `min_ls` en krijgt er een `advies_ls` bij.
- `afvoerpunt` per natte ruimte (ja/nee) in het resultaat, zodat de tabel die kolom kan tonen.
- `deurbelasting(res, topologie)`: per overstroomweg de l/s onder de deur, met een vlag boven
  15 l/s (deurrooster). Levert een regel als "Badkamer-Overloop: 23.0 l/s (>15 l/s),
  deurrooster geadviseerd".
- `toets_vuistregels(res, plan)`: geeft per regel uit `VUISTREGELS` een status
  `voldoet | voldoet niet | niet te bepalen` met een reden. Regels die geometrie of
  installatiekeuzes nodig hebben die er niet zijn, worden `niet te bepalen`, nooit stil
  `voldoet`.
- Herkomst per waarde: elke toevoer- en afvoerregel krijgt een veld `herkomst` met
  `oppervlakte` (0,7 x m2), `minimum` of `balansophoging`.

## Out of scope
- Afronding wijzigen zonder besluit (zie Notes).
- De webapp aanraken.
- Nieuwe dependencies.

## Acceptance criteria
- [ ] Fixture "demo-woning" uit `docs/ventilatieplan-webapp-spec.md` zit in de tests met
      exact verwachte uitkomsten: toevoer woonkamer 40,0 (0,7 x 57,2 = woonkamer 38,7 plus
      keuken 18,5), slaapkamers 12,7 / 8,5 / 7,0 / 7,0 bij onze huidige afronding.
- [ ] Na `verdeel_balans` geldt som toevoer = som afvoer, en geen enkele natte ruimte zakt
      onder zijn minimum.
- [ ] Deurbelasting boven 15 l/s levert een expliciete deurrooster-regel.
- [ ] Alle zeven vuistregels komen terug in de uitvoer, ook de niet te bepalen.
- [ ] `bereken()` blijft puur: geen Flask, geen bestand-IO, offline testbaar.
- [ ] `./scripts/verify.sh` slaagt.
- [ ] AI-review PASS door een andere agent dan de bouwer.

## Sessions
- 2026-08-21: Afrondingsbeslissing eerst vastgelegd in `docs/decisions/0002-ventilatie-afronding.md`
  (blijft 0,1 l/s; overstappen naar hele l/s is een eigen, latere beslissing). Daarna `ventilatie/
  ventilatie.py` uitgebreid: `verdeel_balans()` (proportioneel naar rato van elke natte ruimte se
  minimum, afrondingsrest naar de grootste afnemer zodat de som exact sluit), `afvoerpunt`-vlag +
  `toevoer_herkomst`/`afvoer_herkomst` per regel (oppervlakte/minimum/balansophoging — geen enkele
  waarde meer zonder herkomst), `deurbelasting(res, topologie)` en `toets_vuistregels(res, plan)` met
  alle 7 Nij Begun-vuistregels, elk ontbrekend gegeven levert 'niet te bepalen', nooit een stille
  'voldoet'. Kleine bijfix nodig om de fixture kloppend te krijgen: de MIN_LEEFRUIMTE-vloer van 7 l/s
  gold voorheen ook voor een 0 m2-ruimte (fantoom-toevoer); geldt nu alleen als er echt oppervlak is.
  Fixture "demo-woning" (uit de Aira-naberekening in de spec) 1-op-1 overgenomen met exacte
  toevoerwaarden uit de acceptatiecriteria; alle overige uitkomsten (afvoerverdeling, deurbelasting,
  vuistregeltoetsen) zelf doorgerekend en als test vastgelegd, incl. edge cases (>2 deuren, afvoerpunt
  in slaapkamer, ontbrekende plan-gegevens). 30 nieuwe checks, 821/821 tests groen; `verify.sh` PASS
  (Python-tests blijven advisory op deze Windows-sessie zonder `python3`-alias, zie taak 002 — met
  `python` draaien ze wél, 821/0 gefaald).
- 2026-08-21: AI-review (`/code-review high`, andere agent) vond 5 punten. 2 ervan (magicplan/
  extractor.py) horen bij taak 012 op de onderliggende, nog niet gemerged branch — buiten scope van
  deze taak, niet aangeraakt. 3 echte bevindingen in eigen werk verwerkt: (1) `verdeel_balans()` kon
  bij >=5 natte ruimten door een vastgeklikte 0,1 l/s-afrondingsfout de grootste regel juist ÓNDER
  zijn eigen minimum duwen — vervangen door de grootste-restmethode (Hamilton) in eenheden van 0,1 l/s,
  die per constructie nooit een negatief aandeel geeft; (2) een 0 m2-regel op een verblijfsgebied gaf
  stil 0 l/s toevoer i.p.v. de oude vloer van 7 l/s, wat een echt ontbrekende MagicPlan-oppervlakte kon
  maskeren — geeft nu een expliciete waarschuwing; (3) `deurbelasting()` viel stil terug op 0 l/s bij
  een onbekende ruimtenaam in de topologie — geeft nu een harde `ValueError` (vergelijkbaar met de
  bestaande validatie-poorten elders in de tool). 4 nieuwe regressietests. 825/825 groen, verify.sh
  PASS. Taak gereed voor tasks/done/.

## Notes
**Beslissing die eerst vastgelegd moet worden in `docs/decisions/`:** Aira rondt af op hele
l/s (12,74 wordt 13,0; 8,54 wordt 9,0; 40,04 wordt 40,0), wij op 0,1. Hele l/s leest
prettiger op een tekening en ligt aan de veilige kant bij de capaciteitsvraag, maar het
wijzigt uitkomsten van bestaande dossiers. Niet en passant doorvoeren.

Het rekenhart van Aira is aantoonbaar hetzelfde als het onze (0,7 dm3/s per m2
verblijfsgebied, minimum 7 l/s per leefruimte, keuken 21 / bad 14 / toilet 7). Zie de
naberekening in `docs/ventilatieplan-webapp-spec.md`. Deze taak haalt alleen in wat zij
extra doen, plus onze eigen vuistregeltoets die zij niet hebben.
