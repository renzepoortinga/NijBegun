# AGENTS.md — Nij Begun & EPA-tool

Contract voor elke AI-agent in dit project. Onder de 200 regels houden:
dit bestand verwijst, het bevat niet.

## Project
Standalone Python-tool die één woningopname (MagicPlan) omzet naar
energielabel-invoer (Vabi EPA-W) én een Nij Begun isolatieplan: ingevuld
Word/PDF + JSON + ventilatieberekening + fotochecklist + KWACO-validatie.
Draait zelfstandig (Python of .exe) met een lokaal Flask-dashboard.

Stack: Python ≥3.11 · python-docx/lxml/openpyxl · Flask (dashboard) ·
geen database (JSON-dossiers in `out/`)

## De gouden regel (architectuur)
**Reken NTA 8800 nooit zelf.** Vabi EPA-W (geattesteerd) is de rekenkern;
deze tool levert invoer aan en leest uitkomsten (monitoringbestand). Zo
blijft de eigenaar in de toegestane handmatige adviseur-route en buiten de
tool-validatieplicht.

## Waar staat wat
- `CLAUDE.md` — het operationele geheugen: modules, commando's,
  domeinregels. Groot maar leidend; migreer stukken naar `docs/` per taak,
  niet en passant.
- `docs/STATE.md` — huidige stand (dashboard)
- `docs/` — de kennisbank: ISSO/BRL-gidsen, opname-instructies,
  beslislogica, flowcharts. Domeinkennis hoort dáár.
- `docs/decisions/` — waarom keuzes zijn gemaakt
- `tasks/` — het werk: backlog → ready → active → done
- `agents/` — rolcontracten (manager, builder, reviewer, visual-qa)
- `scripts/verify.sh` — de machinale Definition of Done
- `BUILD_LOG.md` / `STATUS_NACHT_*.md` — historische bouwverslagen
  (alleen-lezen; nieuwe stand gaat naar STATE.md en taakbestanden)

## Start van elke sessie
1. Lees dit bestand, `docs/STATE.md` en de kop van `CLAUDE.md`.
2. Werk je aan een taak? Lees het taakbestand in `tasks/active/` volledig,
   inclusief de Sessions-log.
3. Twijfel over een domeinregel? De kennisbank in `docs/` gaat vóór je
   trainingsdata — NTA 8800/ISSO-details verzin je niet.

## Einde van elke sessie
Werk het taakbestand bij: voeg een regel toe aan `## Sessions`. Een sessie
die dit overslaat heeft niets opgeleverd, ook niet als er code is geschreven.

## Definition of Done
1. `./scripts/verify.sh` slaagt (machinale checks; draait o.a.
   `python3 tests/run_tests.py` — 708 ketentests)
2. AI-review PASS door een agent van een ándere leverancier dan de bouwer
3. Het taakbestand staat in `tasks/done/` en `docs/STATE.md` klopt

## Werkwijze
- Eén taak = één branch = één PR. Branch: `feat/`, `fix/`, `chore/`.
- Niet-triviale taak: eerst een plan, wacht op akkoord, dan pas wijzigen.
- Blijf binnen de scope van het taakbestand. Geen ongevraagde refactors.
- Nooit direct naar `main`.

## Harde regels
- `git commit --no-verify` is verboden. Slaagt verify niet, repareer de oorzaak.
- Nooit `.env*` lezen, bewerken of committen (MagicPlan- en catalogus-keys).
  Geen secrets in code, logs of PR-teksten.
- `core/dossier.py` is het canonieke datamodel — wijzigingen daar raken de
  hele keten; altijd de volledige testsuite draaien.
- Geen nieuwe dependency zonder dit te melden en te motiveren.
- Onderdruk nooit een test, assertie of typefout om iets groen te krijgen.
- Live API-calls (MagicPlan, catalogus) alleen expliciet gevraagd; offline
  dry-runs bestaan voor bijna alles — gebruik die.

## Taakstatus
De map ís de status (backlog/ready/active/done). Geen status in de frontmatter.

## Rollen
Zie `agents/`. Een Builder reviewt nooit zijn eigen werk. De Manager schrijft
geen feature-code. De Reviewer is nooit dezelfde leverancier als de Builder.

## Parallel werken
Eén agent per worktree, één worktree per branch. Een taakbestand wordt alleen
verplaatst door de agent die de taak heeft geclaimd, of door de Manager.

## Design en UI
Alleen relevant voor `dashboard/` en `website/`; volg daar
`docs/design-system.md`.

## Stijl
Wees direct. Is mijn aanpak slechter dan een alternatief, zeg dat.
Verzin geen paden, API's, kolomnamen of normwaarden — controleer ze.
Lukt iets na twee pogingen niet: stop, leg uit wat je probeerde, wat je hebt
uitgesloten en wat je vermoedt.
