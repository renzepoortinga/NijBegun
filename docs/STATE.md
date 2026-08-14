# STATE — dashboard

> Dit is een overzicht, geen administratie. De taken zelf staan in `tasks/`.
> Houd dit kort: als het langer wordt dan één scherm, hoort iets in een taakbestand.

Bijgewerkt: 2026-08-14 door Codex (taken 003, 005 en 006 afgerond)

## Nu
De keten werkt end-to-end: MagicPlan-opname → canoniek dossier → alle drie
VABI-bibliotheken (foutloos importeerbaar in EPA 12.0.1) → isolatieplan
(Word/PDF) + ventilatie + fotochecklist + KWACO-validatie, met een lokaal
dashboard. 746 functionele checks groen; de Git-Bash-verificatie houdt de Python-run
nog advisory totdat taak 002 `python3` op Windows draagbaar maakt (zie
Technische schuld). Historie staat in `BUILD_LOG.md` en
`STATUS_NACHT_2026-06-13.md`; vanaf nu is dít bestand + `tasks/` de stand.

## Actief
Zie `tasks/active/`. Draai `./scripts/status.sh` voor het actuele beeld.

Taak 003 (kwaliteitsverklaring in `SchilDeel.rc_bron` blokkeert Vabi-export)
is afgerond en staat in `tasks/done/`: onafhankelijke herreview van commit
`4dd8221` met VERDICT PASS.

Taak 004 (visuele laag SVG voor dak/dakkapel + gebouwoverzicht) is klaar en
staat in `tasks/done/`: 4 reviewrondes (Codex), laatste VERDICT PASS. Onderweg
ontdekt en meegefixt: een bestaande test in `tests/run_tests.py` verwachtte
nog het oude gedrag van `vabi/constructie_generate.write()` vóór taak 003 —
crashte de testrunner stil, waardoor `verify.sh` een tijdje geen volledige
testrun meer liet zien. `python tests/run_tests.py`: 733/733 groen.

Taak 005 (isometrische dak- en dakkapelwizards) is klaar en staat in
`tasks/done/`: dependencyvrije 3D→2D-projectie, live maatvaste previews,
renderingmetadata inclusief geometriegroepen/moederdakreferentie en identieke
client/servervalidatie voor asymmetrische en steile daken. Onafhankelijke
review op commit `9734d09`: PASS. `python tests/run_tests.py`: 742/742 groen.

Taak 006 (isometrisch gebouwoverzicht) is klaar en staat in `tasks/done/`:
vier consistente MagicPlan-gevels leveren een maatvaste isometrische box;
onvolledige/inconsistente invoer krijgt een expliciete niet-3D fallback.
Taak-005-daken renderen exact na geometrievalidatie, legacy-daken zichtbaar
benaderd en dakkapellen via hun moederdakrelatie. Onafhankelijke herreview op
commit `e157ce0`: PASS MET RISICO'S, geen blockers. 746 checks groen; lokaal
blijven uitsluitend de twee bekende taak-002-omgevingschecks over.

## Blokkades
- Geen bekende.

## Openstaande beslissingen
- Geen.

## Technische schuld
- 2 ketentests hangen aan lokale bestanden buiten de repo
  (`config.json`, een plan-json) en falen in elke verse omgeving/CI. De
  testcheck in `verify.sh` staat daarom tijdelijk op advisory — taak 002
  maakt de tests draagbaar en zet hem terug op blocking.
- `CLAUDE.md` is 465 regels operationeel geheugen; werkt, maar migreer
  stukken naar `docs/` wanneer je ze toch aanraakt (geen aparte
  verbouwtaak waard op dit moment).
- Gebouw-SVG gebruikt een vaste paintervolgorde; uitzonderlijke samengestelde
  geometrie kan daardoor visueel overlappen. Legacy renderingmetadata met
  niet-eindige getallen heeft nog geen eigen defensieve foutstaat.

## Niet doen
- Geen nieuwe dependencies zonder overleg.
- Nooit zelf NTA 8800 rekenen — Vabi EPA-W is de rekenkern (gouden regel).
