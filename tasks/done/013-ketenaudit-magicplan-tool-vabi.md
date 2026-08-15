---
id: 013
assigned: Codex (manager/auditor)
branch: fix/magicplan-ssl-python314
depends_on: []
---

# Task 013 — Keten- en gebruiksaudit MagicPlan → tool → Vabi

## Goal
Vaststellen welke invoer, dropdowns en overdrachten de adviseur nog laten corrigeren, en een bewijsbaar verbeterpad formuleren naar vrijwel invoervrije verwerking na een goede MagicPlan-opname.

## Scope
- Kennisbank, voorbeeldplannen, live MagicPlan-formulieren, webapp en Vabi-overdracht onderling vergelijken.
- Een bestaand of gedupliceerd voorbeeldproject veilig door de keten volgen.
- Dropdownwaarden, normalisatie, vereiste velden, import/export en fout-/herstelpaden toetsen.
- Bevindingen met bewijs, ernst, advies en uitvoerbare vervolgtaakjes vastleggen.
- Geen feature-code; uitsluitend auditdocumentatie en taak-/statusbeheer.

## Out of scope
- Zelf NTA 8800 rekenen of Vabi-uitkomsten vervangen.
- Productiedossiers overschrijven, live formulieren publiceren of broncode aanpassen.
- Secrets lezen of nieuwe dependencies toevoegen.
- Definitieve bouwkundige beoordeling van een niet-zichtbaar dak; dat blijft adviseurswerk.

## Acceptance criteria
- [x] Documentenkaart en voorbeeldplannen zijn herleidbaar geanalyseerd.
- [x] MagicPlan-, canonieke en Vabi-vocabulaire/dropdowns zijn systematisch vergeleken.
- [x] Minimaal één representatieve ketenroute is live of, waar technisch onmogelijk, reproduceerbaar offline beproefd.
- [x] Import/export-resultaten en adviseurshandelingen zijn vastgelegd.
- [x] Bevindingen zijn geprioriteerd en vertaald naar afgebakende vervolgitems.
- [x] `./scripts/verify.sh` is uitgevoerd; bestaande omgevingsafwijkingen zijn apart benoemd.
- [x] Onafhankelijke review is geregeld voordat implementatiewerk uit deze audit als gereed geldt.

## Sessions
- 2026-08-15 — Audit gestart: projectstatus, managercontract, bestaande audits en Chrome-werkbladen geïnventariseerd; bestaande ongerelateerde worktreewijzigingen worden ongemoeid gelaten.
- 2026-08-15 — 790/790 tests groen; live Essenhage-route, drie voorbeeldplannen en offline Vabi-export onderzocht. Reviewbevinding over niet-atomische export verwerkt; backlog 014-017 geformuleerd.
- 2026-08-15 — Onafhankelijke review: PASS MET RISICO'S, geen blockers. Risico's verwerkt in taken 015-017. Git-Bash `verify.sh`: PASS met bekende taak-002-advisory; directe Python-run: 790/790 groen.

## Notes
- De gebruiker staat alleen wijzigingen in een duplicaat van Essenhage of een ander willekeurig MagicPlan-project toe.
- Vabi EPA-W blijft de geattesteerde rekenkern; deze audit controleert invoer/overdracht en workflow, niet de normberekening zelf.
