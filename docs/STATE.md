# STATE — dashboard

> Dit is een overzicht, geen administratie. De taken zelf staan in `tasks/`.
> Houd dit kort: als het langer wordt dan één scherm, hoort iets in een taakbestand.

Bijgewerkt: 2026-08-13 door Codex (taak 004 in uitvoering)

## Nu
De keten werkt end-to-end: MagicPlan-opname → canoniek dossier → alle drie
VABI-bibliotheken (foutloos importeerbaar in EPA 12.0.1) → isolatieplan
(Word/PDF) + ventilatie + fotochecklist + KWACO-validatie, met een lokaal
dashboard. 708 ketentests, waarvan 706 groen in een kale omgeving (zie
Technische schuld). Historie staat in `BUILD_LOG.md` en
`STATUS_NACHT_2026-06-13.md`; vanaf nu is dít bestand + `tasks/` de stand.

## Actief
Zie `tasks/active/`. Draai `./scripts/status.sh` voor het actuele beeld.

- Taak 004: expliciete BCRG-code+dikte-route voor constructiekwaliteitsverklaringen;
  implementatie en Vabi-praktijkvalidatie in uitvoering.

## Blokkades
- Geen bekende.

## Openstaande beslissingen
- Geen.

## Technische schuld
- 2 van de 708 tests hangen aan lokale bestanden buiten de repo
  (`config.json`, een plan-json) en falen in elke verse omgeving/CI. De
  testcheck in `verify.sh` staat daarom tijdelijk op advisory — taak 002
  maakt de tests draagbaar en zet hem terug op blocking.
- `CLAUDE.md` is 465 regels operationeel geheugen; werkt, maar migreer
  stukken naar `docs/` wanneer je ze toch aanraakt (geen aparte
  verbouwtaak waard op dit moment).

## Niet doen
- Geen nieuwe dependencies zonder overleg.
- Nooit zelf NTA 8800 rekenen — Vabi EPA-W is de rekenkern (gouden regel).
