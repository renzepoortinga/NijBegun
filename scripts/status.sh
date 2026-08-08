#!/usr/bin/env bash
# status.sh — de cockpit. Werkt vanaf je telefoon via een agent-sessie.
set -uo pipefail
c() { ls "$1" 2>/dev/null | grep -vc '^\.gitkeep$' || echo 0; }

printf "\nPROJECT: %s\n\n" "$(basename "$PWD")"

if command -v gh >/dev/null 2>&1; then
  printf "CI / PR's\n"
  gh pr list --limit 10 --json number,title,statusCheckRollup,isDraft \
    --template '{{range .}}  {{if eq .statusCheckRollup nil}}·{{else}}{{range .statusCheckRollup}}{{if eq .conclusion "SUCCESS"}}{{else}}{{end}}{{break}}{{end}}{{end}} #{{.number}} {{.title}}
{{end}}' 2>/dev/null || printf "  (gh niet ingelogd)\n"
else
  printf "CI / PR's\n  (gh CLI niet geïnstalleerd — zie cli.github.com)\n"
fi

printf "\nTaken\n"
printf "  backlog %s · ready %s · active %s · done %s\n" \
  "$(c tasks/backlog)" "$(c tasks/ready)" "$(c tasks/active)" "$(c tasks/done)"
for f in tasks/active/*.md; do
  [ -e "$f" ] || continue
  A=$(grep -m1 '^assigned:' "$f" | cut -d: -f2- | xargs)
  B=$(grep -m1 '^branch:'   "$f" | cut -d: -f2- | xargs)
  printf "  → %s  [%s | %s]\n" "$(basename "$f" .md)" "${A:-?}" "${B:-?}"
done

printf "\nGit\n"
printf "  branch: %s · niet-gecommit: %s bestand(en)\n" \
  "$(git branch --show-current)" "$(git status --porcelain | wc -l | xargs)"
printf "  worktrees: %s\n" "$(git worktree list | wc -l | xargs)"

printf "\nBlokkades (uit docs/STATE.md)\n"
sed -n '/^## Blokkades/,/^## /p' docs/STATE.md 2>/dev/null | grep '^-' | sed 's/^/  /' || printf "  —\n"
printf "\n"
