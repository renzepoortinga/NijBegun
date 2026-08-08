---
id: 002
assigned:
branch:
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
- [ ] `python3 tests/run_tests.py` → 708/708 groen in een verse clone
- [ ] Testcheck weer blocking en `./scripts/verify.sh` slaagt
- [ ] AI-review PASS door een andere leverancier dan de bouwer

## Sessions

## Notes
Nulmeting 2026-08-08 in een kale container: 706 geslaagd, 2 gefaald —
beide door ontbrekende lokale bestanden, geen code-regressies.
