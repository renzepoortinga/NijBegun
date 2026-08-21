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
- [x] `verify` is groen op main
- [x] Branch protection actief met `verify` als required check

## Sessions
- 2026-08-08 Claude (Fable 5): OS geïnstalleerd; verify aangepast voor
  Python (draait tests/run_tests.py); nulmeting: 706/708 groen, geen
  secrets in git.
- 2026-08-21 Codex Manager: na merge van taak 002 is `verify` blocking en lokaal 786/786
  groen; GitHub-run `32475627070` op `main` is geslaagd. `scripts/protect.sh` uitgevoerd:
  `verify` is strict required, ook voor admins; force-push en deletion staan uit.
- 2026-08-21 Codex Reviewer: onafhankelijke review PASS. Actuele main-SHA, groene CI-run,
  lokale blocking verify en branch-protectioninstellingen via GitHub API bevestigd.

## Notes
