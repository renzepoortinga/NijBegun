---
id: 017
assigned:
branch:
depends_on: []
---

# Task 017 — Vabi-exportset atomisch publiceren

## Goal
Voorkomen dat een fout in een latere writer een gedeeltelijke of oud/nieuw gemengde Vabi-importset achterlaat.

## Scope
- Genereer constructie-, objecten- en installatiebibliotheek plus instructie als immutable/versioned set.
- Valideer complete set vóór publicatie.
- Publiceer pas na volledig succes via een atomische manifest-/pointerwissel; behoud bij fout de vorige geldige set (ook op Windows).
- Voeg foutinjectietests toe voor elke writerfase.

## Out of scope
- Vabi-enummappings wijzigen.
- Kwaliteitsverklaring inhoudelijk automatiseren.
- Oude exportsets zonder expliciet retentiebeleid verwijderen.

## Acceptance criteria
- [ ] Elke geïnjecteerde writerfout laat de vorige complete eindset onaangetast.
- [ ] Succes publiceert precies één onderling consistente set.
- [ ] Tijdelijke bestanden worden na succes en fout veilig opgeruimd.
- [ ] `./scripts/verify.sh` slaagt.
- [ ] AI-review PASS door een andere agent dan de bouwer.

## Sessions

## Notes
Auditreview 15-8-2026: `generate_all.py` doet wel preflight vóór schrijven, maar schrijft daarna sequentieel naar eindpaden.
