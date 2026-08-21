---
id: 018
assigned: Codex Builder
branch: feat/018-fix-aanvoertemperatuur-undot
depends_on: []
---

# Task 018 — Fix aanvoertemperatuur-normalisatie (`_undot` breekt `.` → `/`-herstel)

## Goal
De automatische codering van `Verwarming - aanvoertemperatuur` naar VABI's
`WaterAanvoertemperatuur`-enum werkt voor GEEN enkel project, omdat de waarde al kapot is
vóórdat de bestaande dot→slash-fix in `installatie_generate.py` haar kan toepassen.

## Scope
- `magicplan/statistics_csv.py`: `G2()` haalt elk Installaties-veld door `_undot()`, die élke
  `.` (behalve `t.m`) naar een spatie vervangt. MagicPlan exporteert de dropdown-waarde `90/70`
  in de Statistics-CSV als `90.70` — `_undot()` maakt daar `90 70` van.
- `vabi/installatie_generate.py:235-247` verwacht die punt nog en herstelt `.` → `/` vóór de
  lookup in `_AANVOERTEMP` — maar de punt is dan al vervangen door een spatie, dus de herstelpoging
  vindt niets meer om te herstellen en elke aanvoertemperatuur eindigt als "onbekende klasse".
- Live gereproduceerd op 15-8-2026 (zie `docs/stresstest-magicplan-vabi-tool-15-8-2026.md`,
  bevinding 1): dossier-JSON van een echt MagicPlan-testproject bevat
  `"aanvoertemperatuur": "90 70"` i.p.v. `"90/70"`.
- Fix: `aanvoertemperatuur` niet (langer) door de generieke `_undot()` halen — het is geen
  categorische t/m-waarde — óf de dot→slash-herstelpoging in `installatie_generate.py` ook op
  spatie-gescheiden 2-cijferige paren laten matchen. Eerste optie is zuiverder.
- Regressietest: CSV-cel `90.70` (en een paar andere codes, bv. `80.60`) moet na de volledige
  keten (`statistics_csv.py` → `installatie_generate.py`) op `WaterAanvoertemperatuur` de juiste
  code zetten, zonder "onbekende klasse"-flag.

## Out of scope
- Andere Installaties-velden herzien (steekproef op 15-8 vond alleen dit veld met een
  `X/Y`-vocabulaire; zie de stresstest-doc).
- De bredere mappingmanifest-taak (015) — dit is een gerichte, kleine bugfix.

## Acceptance criteria
- [x] CSV-waarde `90.70` (en de andere 11 aanvoertemperatuur-codes) wordt na de volledige keten
      correct als `WaterAanvoertemperatuur`-code geschreven, zonder "onbekende klasse"-flag.
- [x] Regressietest toegevoegd (unit of keten) die dit vastlegt.
- [x] `./scripts/verify.sh` slaagt (incl. volledige testrun).
- [x] AI-review PASS door een andere agent dan de bouwer.

## Sessions

- 2026-08-21 — Codex Builder: `aanvoertemperatuur` leest nu als enige installatieveld de ruwe
  Statistics-CSV-waarde, zodat de bestaande gerichte punt-naar-slashnormalisatie in de
  Vabi-generator werkt. Ketenregressie voor alle 12 bevestigde codes toegevoegd. `python
  tests/run_tests.py`: 784 PASS, 2 bekende taak-002-omgevingsfails (`config.json`/plan-json en
  loginconfig); de nieuwe regressie is PASS. Git-Bash `./scripts/verify.sh`: PASS met hetzelfde
  bekende Python-advisory. Het genoemde stresstestdocument was niet aanwezig in deze branch of
  historie; het bewijs en de isolatiereproductie in dit taakbestand waren wel beschikbaar.
- 2026-08-21 — Codex Reviewer/Manager: onafhankelijke review van commit `9d519c8`:
  PASS zonder bevindingen. Alle 12 codes zijn door de volledige CSV → dossier → Vabi-keten
  gecontroleerd, inclusief afwezigheid van de onbekend-flag. `verify.sh` PASS; alleen de bekende
  taak-002-advisory bleef over. Taak naar `done` verplaatst.

## Notes
Gevonden tijdens een losse stresstest-sessie (15-8-2026, ander gesprek dan taak 013's
ketenaudit) door een verse Statistics-CSV van het live Essenhage-testproject door de hele
keten te halen. Zie `docs/stresstest-magicplan-vabi-tool-15-8-2026.md` voor het volledige bewijs
(inclusief de isolatie-reproductie: `statistics_csv._undot("90.70") == "90 70"`).
