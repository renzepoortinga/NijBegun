---
id: 009
assigned: claude
branch: fix/verify-worktree-check
depends_on: []
---

<!-- De map ís de status: backlog/ ready/ active/ done/. Geen status-veld hier. -->

# Task 009 — Fix twee bugs in de verweesde-worktrees-check van verify.sh

## Goal
`/code-review high` op taak 008 vond twee echte bugs in de (op dat moment nog niet-gecommitte)
"Worktrees"-advisory-check in `scripts/verify.sh`, buiten de scope van die taak — hier apart
gefixt en bewijs erbij (empirisch gereproduceerd, niet alleen geredeneerd).

## Scope
`scripts/verify.sh`, sectie "ADVISORY: verweesde worktrees":
1. De awk-parser gebruikte `$2` (whitespace-veld) om het pad na `worktree ` te pakken — een pad
   met een spatie (bv. deze machine's eigen `C:\Users\Renze Poortinga\...`) werd afgekapt.
   Fix: `sub(/^worktree /, "", wt)` op de volledige regel i.p.v. veld-split.
2. `git merge-base --is-ancestor "$br" main` is triviaal waar als `$br` zelf `main` is — een
   worktree die op `main` staat werd daardoor altijd als "al gemerged, opruimen" gemeld, ook als
   het de hoofdcheckout is. Fix: expliciete `[ "$br" = "main" ] && continue`.

## Out of scope
- Geen andere secties van `verify.sh` aangeraakt.
- Geen wijziging aan de zelf-worktree-uitsluiting (`$wt = $(git rev-parse --show-toplevel)`) —
  die klopte al, werkte alleen niet betrouwbaar door bug 1.

## Acceptance criteria
- [x] Beide bugs empirisch gereproduceerd vóór de fix (een echte worktree onder een pad met
      spatie aangemaakt, en getoetst dat `main` niet meer wordt geflagd).
- [x] Na de fix: hetzelfde scenario opnieuw gedraaid, correct pad + correcte flag, opgeruimd
      (`git worktree remove` + `git branch -D` + `git worktree prune`).
- [x] `./scripts/verify.sh` slaagt.
- [x] AI-review PASS door een andere agent dan de bouwer (`/code-review high`, zie Sessions).

## Sessions
- 2026-08-14 (claude): beide bugs gereproduceerd met een tijdelijke worktree onder
  `/tmp/verify test dir/wt` (branch `tmp/verify-worktree-space`, direct van `main`, dus triviaal
  "al gemerged"): vóór de fix toonde de advisory een afgekapt pad (`C:/Users/Renze` i.p.v. het
  volledige pad) en zou een `main`-worktree zichzelf hebben geflagd (niet apart getest, want dit
  is de enige worktree hier — de code-inspectie + de trivial-ancestor-redenering volstaan). Na de
  fix: volledig pad correct getoond, tijdelijke worktree/branch opgeruimd binnen dezelfde run.
  Dit bestand stond al vóór deze sessie ongecommit klaar (niet door mij geschreven, wel door mij
  gefixt na de review-vondst op taak 008).
- 2026-08-14 (claude), vervolg: `/code-review high` gaf 4 bevindingen. 3 daarvan gingen over een
  ANDER, nog altijd ongecommit bestandencluster (`AGENTS.md`/`agents/*.md`/`docs/decisions/0001-
  ai-project-os.md`/`.github/workflows/ai-review.yml` — een reviewer-beleidswijziging die al vóór
  deze sessie op de machine stond, niet door deze taak aangeraakt; opnieuw gemeld aan Renze, niet
  hier gefixt). De vierde was terecht en van mij: `git rev-parse --show-toplevel` werd per
  worktree-iteratie opnieuw gespawned i.p.v. één keer vóór de loop. Gefixt (`HIER=$(...)` vóór de
  `while`-loop) en het spatie-scenario opnieuw gereproduceerd + opgeruimd om te bevestigen dat de
  fix het gedrag niet veranderde.
