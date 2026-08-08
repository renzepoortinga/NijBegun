---
id: 001
assigned:
branch:
depends_on: []
---

# Task 001 — Nulmeting afronden en de gate aanzetten

## Goal
Het zojuist geïnstalleerde AI Project OS scherp zetten: CI groen, daarna
branch protection aan.

## Scope
- CI-uitslag van de installatie-PR bevestigen (verify draait de greps +
  Python-tests als advisory)
- Na de merge en één groene CI-run op main: `bash scripts/protect.sh`

## Out of scope
- De twee omgevingsafhankelijke tests fixen (dat is taak 002)

## Acceptance criteria
- [ ] `verify` is groen op main
- [ ] Branch protection actief met `verify` als required check

## Sessions
- 2026-08-08 Claude (Fable 5): OS geïnstalleerd; verify aangepast voor
  Python (draait tests/run_tests.py); nulmeting: 706/708 groen, geen
  secrets in git.

## Notes
