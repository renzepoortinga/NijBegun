---
id: 016
assigned: Codex Builder
branch: feat/016-one-click-magicplan-intake
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
- [x] Verkeerd project/dossier kan niet stil worden gekoppeld.
- [x] Herimport heeft aantoonbaar behoud-/vervanggedrag per gegevensgroep.
- [x] De vastgelegde complete referentiefixture resulteert in exact de vooraf benoemde resttaken en dakcontrole.
- [x] Offline dry-run dekt de volledige merge.
- [x] `./scripts/verify.sh` slaagt.
- [ ] AI-review PASS door een andere agent dan de bouwer.

## Sessions

- 2026-08-21 Codex Manager: afhankelijkheden 014/015 zijn gemerged; taak geclaimd op een eigen
  worktree vanaf actuele `main` en vrijgegeven voor implementatie.
- 2026-08-21 Codex Builder: vóór implementatie de complete offline referentie-intake vastgelegd
  (`tests/fixtures/intake_complete/`) met letterlijk verwachte resttaken en dakcontrole. Daarna
  `magicplan/intake.py` en de dashboardpreview/bevestiging gebouwd: woning- én project-id-gate,
  formfingerprint, ZIP-/hashcontrole, diff, gegroepeerde actiepunten en expliciet behoud van
  wizarddaken, foto's, maatregelen, haalbaarheid, adviseur en eerdere Vabi-resultaten. Pakketcontract
  gedocumenteerd; geen live API-call en geen dependency toegevoegd. Ketensuite 854/854 groen.
  Eerste blocking verify-run raakte één niet-reproduceerbare bestaande webapptest; directe losse
  herhaling en de volledige blocking herhaling waren groen (`VERIFY PASS`). Wacht op onafhankelijke review.
- 2026-08-21 Codex Builder: review-FAIL volledig verwerkt. Identiteit controleert BAG én adres
  coherent over manifest/Statistics/rapport/huidig dossier en weigert onbewezen BAG-only ↔ adres-only
  koppelingen. Fixed staging vervangen door unieke cryptografische previewtokens, eigen directories,
  atomisch gepubliceerde metadata en one-time confirm met hashes van pakket/staged dossier/basisrevisie
  plus basisidentiteit. Alle paden ruimen op zonder raw fouttekst; parallelle confirms wissen elkaars
  staging niet. Diff komt nu uit de daadwerkelijke merge en toont echte behoud-/vervangaantallen.
  ZIP-, MIME-, schema- en geometrievalidatie aangescherpt. Adversariële offline regressies toegevoegd
  voor BAG, adres, traversal, duplicaten, ziplimiet, polygonen, tamper/TOCTOU, concurrency, cleanup,
  authenticatie en CSRF. Blocking `verify.sh`: PASS met 875/875 checks. Geen live calls of
  dependencies; wacht op herreview.
- 2026-08-21 Codex Builder: tweede herreview-FAIL verwerkt na rebase op `origin/main` met taak 020.
  Confirm is nu per project geserialiseerd met een thread- én interprocess-filelock; binnen de lock
  worden dossier/state opnieuw geladen en wordt de preview als compare-and-swap tegen hash plus
  identiteit uitgevoerd. Twee gelijktijdige geldige tokens vanaf dezelfde basis leveren via een
  deterministische barrier-test exact één commit en één expliciete revisiemismatch. Dossier en
  projectstate worden als voorbereid paar atomisch vervangen; een geïnjecteerde fout op de tweede
  replace rolt het dossier terug en behoudt de vorige byte-identieke consistente pair. De strikte
  polygonkern uit taak 020 is naar `core/polygon.py` gecentraliseerd en wordt nu ook voor intake-
  geometrie gebruikt (unieke punten, niet zelfsnijdend/degeneratief, eindig en relatief `0..1`).
  Volledige lokale ketensuite: 989/989 groen; blocking verify volgt na de laatste rebase.

## Notes
Afhankelijk van dakmigratie en een stabiel mappingmanifest.
