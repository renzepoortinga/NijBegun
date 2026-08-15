---
id: 015
assigned:
branch:
depends_on: []
---

# Task 015 — Mappingmanifest en MagicPlan-formulierversie

## Goal
Dropdown- en veldendrift tussen MagicPlan, parser, dossier, webapp en Vabi automatisch detecteren.

## Scope
- Eén machineleesbaar manifest per veld: bronlabel, opties, verplicht/conditioneel, canoniek veld/enum, webappopties, Vabi-pad/code en bewijsstatus.
- Fingerprint van de live MagicPlan-formulieren bij import opslaan.
- Bewaar stabiele bronprovenance per geïmporteerd schildeel/geometriegroep, zodat herimport en dakmigratie dezelfde vlakken kunnen herkennen.
- Gebruik in CI een gedateerde live snapshot; live refresh blijft een aparte expliciete controle en is geen testafhankelijkheid.
- Documentatieoverzicht uit het manifest genereren of valideren.
- Tests uitbreiden van glas/begrenzing naar alle gemapte enums.

## Out of scope
- Onbevestigde Vabi-codes raden.
- Live formulieren zonder review publiceren.
- Wijzigingen aan normrekenlogica.

## Acceptance criteria
- [ ] Elke ondersteunde dropdown heeft één herleidbare canonieke definitie. **NIET gedaan** — het
      volledige manifest (bronlabel/opties/canoniek veld/webappopties/Vabi-pad per dropdown) is niet
      gebouwd; alleen het dak-specifieke stuk hieronder.
- [ ] Drift tussen live/form-spec/parser/webapp faalt luid. **NIET gedaan.**
- [x] Onbevestigde Vabi-code is zichtbaar en wordt niet geschreven. Was al zo (golden rule,
      bestaande preflight-poorten); niet nieuw werk deze sessie.
- [ ] Dossier bevat form fingerprint en importtijd. **NIET gedaan** — geen form-fingerprint of
      MagicPlan-projectversie in de dossier-meta opgeslagen.
- [x] Elk geïmporteerd vlak heeft stabiele bronprovenance die een herimport overleeft — **scoped naar
      wat taak 014 nodig had**: `SchilDeel.bron` (`magicplan-import` | `magicplan-dak-fallback` |
      `webapp-wizard`) op elk schildeel; CSV-herimport draagt `webapp-wizard`-dakvlakken nu over i.p.v.
      ze stil te wissen (zie `dashboard.app.opname_magicplan`). GEEN generieke stabiele per-vlak-ID
      voor gevel/vloer/kozijn bij herimport (die blijven bij een CSV-herimport gewoon volledig
      vervangen, zoals voorheen) — alleen dak is opgelost, want dat was de concrete klacht (taak 014).
- [x] `./scripts/verify.sh` slaagt.
- [ ] AI-review PASS door een andere agent dan de bouwer.

## Sessions
- 2026-08-15 (los gesprek, ná taak 013's ketenaudit) — user vroeg expliciet om taak 014
  (dubbele dakvlakken, Essenhage) door te voeren; op advies eerst dit scoped stuk van 015
  gedaan omdat 014 ervan afhangt. GEEN volledig mappingmanifest/form-fingerprint gebouwd (te
  groot voor deze sessie) — alleen `SchilDeel.bron`-provenance + dak-herimport-behoud, het
  minimum dat taak 014 nodig had. Zie `tasks/active/014-dakmigratie-zonder-dubbele-vlakken.md`
  voor het vervolg. 797/799 tests groen (2 bekende omgevingsfalen buiten de repo, taak 002).
  Het brede manifest/fingerprint/CI-drift-werk staat nog volledig open — nieuwe sessie nodig.

## Notes
`magicplan-forms-live.md` (23-7) en de doorgevoerde dakvelden van 27-7 spreken elkaar nu tegen —
dat specifieke punt is met deze sessie NIET opgelost (nog steeds relevant voor een vervolgsessie).
