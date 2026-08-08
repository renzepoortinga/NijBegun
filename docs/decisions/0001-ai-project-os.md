# 0001 — Repo als source of truth, rollen gescheiden

**Context.** Werken via lange chats kost veel tokens, maakt parallel werken
onmogelijk en bindt het project aan één leverancier.

**Besluit.** Context in de repo, verdeeld over `AGENTS.md` (contract),
`docs/` (toestand, architectuur, design, historie) en `tasks/` (werk).
Definition of Done in twee poorten: `scripts/verify.sh` machinaal, plus een
onafhankelijke AI-review door een andere leverancier. Beide required checks
in CI; branch protection is de echte gate, lokale hooks zijn alleen snelheid.
Rollen gescheiden: de Manager schrijft geen feature-code, de Builder reviewt
zijn eigen werk niet.

**Gevolgen.** Sessies zijn wegwerpbaar, taken niet. Wisselen van tool kost
niets. Prijs: elke sessie eindigt met een update van het taakbestand.
