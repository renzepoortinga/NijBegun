---
id: 029
assigned: Claude Code
branch: feat/029-ventilatieplan-achtergrond-upload
depends_on: []
---

# Task 029 — Referentieafbeelding uploaden voor het ventilatieplan (bestaande projecten)

## Goal
Op project 9502CS_26 toonde de ventilatieplan-pagina "Geen plattegrond beschikbaar" en
"Ruimtecontouren ontbreken" — de webapp had géén achtergrondafbeelding of contour voor de vloeren, dus
de bestaande handmatige "Ruimtecontouren kalibreren"-tool (klik-punten-tekenen) had niets om op te
klikken. De volledige plattegrond-vision-import (taak 022, `/project/<tag>/plattegrond-import`) lost dit
niet op voor dit soort projecten: die route weigert bewust te draaien zodra er al opname-geometrie is
("bestaande geometrie wordt niet overschreven"), en 9502CS_26 heeft die geometrie al (MagicPlan-opname +
dak-wizard). Deze taak voegt een kleine, veilige aanvulling toe: alleen een referentieafbeelding
uploaden per verdieping, zonder AI-call en zonder enige geometrie-/ruimtemutatie, zodat de bestaande
kalibratietool weer bruikbaar is.

## Scope
- `dashboard/app.py`: nieuwe route `POST /project/<tag>/ventilatieplan/achtergrond` — valideert de
  upload met de bestaande `plattegrond_import.valideer_afbeeldingsbytes()` (volledige Pillow-decode,
  25 MB-/PNG-IEND/JPEG-EOI-grenzen, hergebruikt i.p.v. gedupliceerd), slaat op onder
  `out/projects/<tag>/ventilatieplan_achtergrond/<verdieping-slug>.<ext>` en zet uitsluitend
  `VloerInfo.plattegrond_afbeelding` op de betreffende vloer. Onbekende verdieping of ontbrekend
  bestand geeft een nette flash-melding, geen 500.
- Ventilatieplan-template: een klein upload-formulier binnen "Ruimtecontouren kalibreren", alleen
  zichtbaar wanneer `achtergrond_soort == 'geen'` (dus geen dubbele/overbodige UI zodra er al een
  achtergrond is); dat `<details>`-blok staat dan ook meteen open.
- Regressietests in `tests/run_tests.py` (sectie 67, ventilatieplan-route): upload zet
  `plattegrond_afbeelding` correct, bestand staat echt in de projectmap, geometrie/markers blijven
  ongemoeid, onbekende verdieping wordt geweigerd zonder 500.

## Out of scope
- Automatisch ruimtecontouren AFLEZEN uit de afbeelding (dat is taak 022, vision-based, blijft blocked
  op de <5%-praktijk-AC met 10 echte gelabelde plattegronden).
- Wijzigingen aan de bestaande vision-importroute of aan de handmatige kalibratie-JS zelf.
- Vervangen van een bestaande achtergrond (form verschijnt alleen als er nog geen is); een adviseur die
  een betere scan wil neerzetten kan dat voorlopig niet via de UI — bewust klein gehouden.

## Acceptance criteria
- [x] Upload van een geldige PNG/JPEG zet `VloerInfo.plattegrond_afbeelding` op de juiste vloer en
  persisteert dat in het dossier.
- [x] Er wordt geen enkele ruimte-/markergeometrie aangeraakt door deze route.
- [x] Onbekende verdieping of ontbrekend bestand geeft een nette melding, geen 500/crash.
- [x] Bestandsvalidatie hergebruikt de bestaande, al geharde `plattegrond_import`-grens (geen nieuwe
  eigen decode-/limietlogica).
- [x] Regressietests toegevoegd.
- [x] `./scripts/verify.sh` slaagt (1071/1071 Python-tests).
- [ ] AI-review door een andere leverancier — nog niet gedraaid op deze specifieke branch (wel op de
  parallelle taak 028; zelfde repo-brede beperking: geen CI-route voor een andere-leverancier-review).

## Sessions
- 2026-08-22 Claude Code: gebouwd tijdens dezelfde sessie als taak 028, op verzoek van Renze om het
  ventilatieplan voor 9502CS_26 bruikbaar te maken. Eerste versie ging abusievelijk verloren doordat een
  gelijktijdig lopende `codex exec`-reviewsessie (met schrijftoegang, voor taak 028) de ongecommitte
  wijziging in dezelfde werkmap zag als een bijeffect van zijn eigen testrun en 'm terugzette om zelf
  read-only te blijven — logisch vanuit zijn instructies, maar onbedoeld verlies van eigen werk (zie ook
  taak 028's sessielog). Opnieuw toegepast op een schone branch vanaf `main` (losstaand van taak 028, dat
  nog niet gemerged is) zodat de twee taken niet vermengd raken in één PR. `verify.sh` PASS (1071/1071).
