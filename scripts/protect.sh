#!/usr/bin/env bash
# Eenmalig per repo, nádat CI minstens één keer gedraaid heeft
# (de check-naam moet bestaan voordat je hem required kunt maken).
#
# Zodra ai-review draait, voeg je "ai-review" toe aan contexts hieronder.
set -euo pipefail
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
gh api -X PUT "repos/$REPO/branches/main/protection" --input - <<'JSON'
{
  "required_status_checks": { "strict": true, "contexts": ["verify"] },
  "enforce_admins": true,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
echo "Branch protection actief op $REPO — required check: verify"
