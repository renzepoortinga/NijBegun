---
id: 002
assigned: Codex Builder
branch: feat/002-tests-draagbaar-maken
depends_on: []
---

# Task 002 — Ratel: de 2 omgevingsafhankelijke tests draagbaar maken

## Goal
De volledige testsuite groen in elke verse omgeving (CI incluis), zodat de
testcheck in `verify.sh` terug kan van advisory naar blocking.

## Scope
- `bouwjaar/plan-json: draait zonder fout` — faalt met FileNotFoundError:
  verwacht een plan-json buiten de repo. Fixture toevoegen of de test laten
  skippen mét duidelijke melding wanneer het bestand ontbreekt.
- `login-pagina: e-mailveld aanwezig` — verwacht een adviseur-adres in
  `config.json` (niet in git). Zelfde aanpak: fixture/temp-config in de test.
- In `scripts/verify.sh` de Python-testcheck terugzetten van `advise` naar
  `fail` — **in dezelfde PR**.

## Out of scope
- Overige tests, nieuwe features, dashboard-wijzigingen

## Acceptance criteria
- [x] `python3 tests/run_tests.py` → 708/708 groen in een verse clone
  (huidige suite: 786/786 via de beschikbare Windows-commandonaam `python`)
- [x] Testcheck weer blocking en `./scripts/verify.sh` slaagt
- [x] AI-review PASS door een andere agent dan de bouwer

## Sessions

- 2026-08-21 — Codex Builder: beide omgevingsafhankelijke tests zelfvoorzienend gemaakt.
  De plan-JSON-test gebruikt een in-memory `build_sample()`-dossier en tijdelijke projectmap;
  de login-test injecteert en herstelt een tijdelijke dashboardconfig. `verify.sh` is weer
  blocking en kiest op Windows/Linux een daadwerkelijk werkende `python3` of `python`.
  `python tests/run_tests.py`: 786/786 groen. Git Bash `scripts/verify.sh`: PASS.
- 2026-08-21 — Codex Reviewer/Manager: onafhankelijke review van commit `b2eca65`: PASS.
  Drie directe suites en vier opeenvolgende `verify.sh`-runs waren 786/786 groen zonder
  advisory. Eén eerdere incidentele failure in `bevestiging zonder datum` bleek aantoonbaar
  los te staan van deze diff en was gericht 100/100 niet reproduceerbaar. Taak naar `done`.

## Notes
Nulmeting 2026-08-08 in een kale container: 706 geslaagd, 2 gefaald —
beide door ontbrekende lokale bestanden, geen code-regressies.
