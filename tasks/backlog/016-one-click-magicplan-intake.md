---
id: 016
assigned:
branch:
depends_on: [014, 015]
---

# Task 016 — Veilige one-click MagicPlan-intake

## Goal
Een adviseur laat een compleet MagicPlan-project met minimale handelingen in een correct gekoppeld dossier landen.

## Scope
- Projectselectie en importpakket (identiteit, Statistics, rapport, geometrie) als één workflow.
- Preview/diff vóór merge; identiteit en form fingerprint bewaken.
- Mergebeleid voor handmatige dakvlakken, foto’s, maatregelen en eerdere Vabi-resultaten.
- Actiepunten groeperen in identiteit, schil, dak, installaties en bewijs.
- Leg vóór implementatie één concrete complete referentiefixture vast met exact verwachte resttaken.

## Out of scope
- Live API-calls in tests.
- Vabi desktop automatiseren.
- Uitzonderingen verbergen of normgegevens gokken.

## Acceptance criteria
- [ ] Verkeerd project/dossier kan niet stil worden gekoppeld.
- [ ] Herimport heeft aantoonbaar behoud-/vervanggedrag per gegevensgroep.
- [ ] De vastgelegde complete referentiefixture resulteert in exact de vooraf benoemde resttaken en dakcontrole.
- [ ] Offline dry-run dekt de volledige merge.
- [ ] `./scripts/verify.sh` slaagt.
- [ ] AI-review PASS door een andere agent dan de bouwer.

## Sessions

## Notes
Afhankelijk van dakmigratie en een stabiel mappingmanifest.
