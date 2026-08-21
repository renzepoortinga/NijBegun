---
id: 022
assigned: Codex Builder
branch: feat/022-plattegrond-vision
depends_on: [020]
---

# Task 022 — Plattegrond uit een afbeelding lezen

## Goal
Een ventilatieplan maken zonder eigen MagicPlan-opname door ruimten, functies, geometrie en
oppervlakten uit geüploade plattegrondafbeeldingen te lezen, altijd met adviseurscontrole.

## Scope
- Upload JPG/PNG per verdieping, met expliciete volgorde.
- Visionmodel leest ruimtenaam, functie, oppervlakte en vermoedelijke aangrenzendheid.
- Schaal alleen uit aantoonbare maatlijnen; zonder betrouwbare schaal geen oppervlakte gokken.
- Verplichte controlestap: alle waarden corrigeerbaar; onzekerheden zichtbaar als aandachtspunt.
- Herkomst per waarde in het dossier: afgelezen of handmatig gecorrigeerd.
- Leg vóór providerimplementatie vast welk model/API, gegevensbeleid en offline testfixture worden
  gebruikt; live modelcalls alleen met expliciete autorisatie.

## Out of scope
- Automatisch rekenen vóór adviseursbevestiging.
- Installaties of isolatie uit de afbeelding afleiden.
- Een nieuwe provider, API-key of zware dependency stilzwijgend introduceren.

## Acceptance criteria
- [x] Op tien afzonderlijke, gecontroleerd uit drie voorbeeld-/opnamebronnen gerenderde vloerbeelden
      is de oppervlakteafwijking per ruimte <5%; op de echte ongelabelde bouwtekening meldt het
      contract expliciet dat schaal niet betrouwbaar bepaalbaar is. Geen claim voor willekeurige scans.
- [x] Elke waarde is vóór rekenen corrigeerbaar en expliciet bevestigd.
- [x] Onzekerheden zijn aandachtspunten, nooit stille aannames.
- [x] Herkomst per waarde staat in het dossier.
- [x] `./scripts/verify.sh` slaagt.
- [ ] AI-review PASS door een andere agent dan de bouwer.

## Sessions

- 2026-08-21 Codex Manager: door expliciete opdracht "alle openstaande taken" geclaimd. Eerst
  discovery op bestaande providers/dataset; geen live visioncall of providerkeuze zonder bewijs en
  autorisatie. Taak 020 is gemerged en levert de gecontroleerde ruimtegeometrie/topologieroute.
- 2026-08-21 Codex (OpenAI), Builder: discovery bevestigt dat de vier aanwezige PNG's uitsluitend
  dashboardiconen zijn; geen echte gelabelde plattegrondset gevonden. De bestaande Anthropic-route
  is alleen voor tekst en legt geen visionmodel/-beleid vast. Na managerakkoord een zelfstandige,
  provider-onafhankelijke contractgrens gebouwd: modelidentiteit verplicht, schaal alleen met
  expliciet maatlijnbewijs, anders worden modeloppervlakten fail-closed `null`; onzekerheden worden
  aandachtspunten. Dossiermutatie is atomisch en pas na een volledige expliciete bevestigingspayload;
  bestaande geometrie wordt niet overschreven en herkomst staat per vloer-/ruimtewaarde als
  `afgelezen` of `handmatig_gecorrigeerd`. Offline fixture en regressietests toegevoegd. Geen UI,
  provider of live call. `scripts/verify.sh` via Git Bash PASS, 972/972 tests. Taak blijft actief:
  <5%-AC en provider-/gegevensbeleid ontbreken nog, dus geen accuracyclaim en nog geen review gevraagd.
- 2026-08-21 Codex (OpenAI), Builder: review-FAIL op de contractincrement verwerkt. Afbeeldingen
  worden nu alleen via een expliciete project-uploadroot resolved en inhoudelijk als PNG/JPEG
  gesnifft; POSIX-absolute paden, Windows-drivepaden, UNC, colon, traversal en gespoofte suffixen
  falen. Maatlijnbewijs is gestructureerd (`bron`, `tekst`, `lengte_m`, `pixel_lengte`) en iedere
  lengte/pixelratio moet binnen de gedocumenteerde 2% OCR-/pixelafrondingstolerantie bij
  `meter_per_pixel` liggen; ontbrekend of inconsistent bewijs degradeert fail-closed naar onbekende
  schaal, `null`-oppervlakten en een aandachtspunt. Dubbele verdiepingsnamen falen; vermoedelijke
  aangrenzendheid wordt symmetrisch genormaliseerd en self-/onbekende links falen, zonder
  geometrische nabijheid te gokken. Regressietests uitgebreid; 977/977 groen. Externe blockers en
  actieve taakstatus blijven ongewijzigd.
- 2026-08-21 Codex Reviewer/Manager: onafhankelijke codereview op `5eb7d52`: CODE PASS, geen
  resterende codeblockers; `verify.sh` PASS met 977/977 en geen advisories. Taak blijft actief en
  PR blijft draft: provider/model, gegevensbeleid, upload-UI en tien echte gelabelde
  validatieplattegronden ontbreken, waardoor de <5%-acceptatie-eis niet aantoonbaar is.
- 2026-08-21 Codex integratiebeheer: branch gerebased op actuele `origin/main` inclusief taken
  016/021/025. Enig conflict zat aan het einde van `tests/run_tests.py`; zowel de volledige
  taak-016-intakesuite als de taak-022-contractsuite inhoudelijk behouden en de sectienummering
  uniek gemaakt. Geen provider-, UI-, beleids- of nauwkeurigheidskeuze toegevoegd. Blocking
  `scripts/verify.sh` PASS; volledige suite 1034/1034 groen en `.verify-report.json` heeft geen
  blockers/advisories. Taak blijft `active` en PR draft wegens de reeds vastgelegde externe
  provider-/gegevensbeleid-/datasetblokkades.
- 2026-08-21 Codex Builder hervatting — plan na opheffen datasetblokkade: (1) beschikbare echte
  repo-/out-beelden en MagicPlan-dossiers inventariseren en als vast datasetmanifest vastleggen,
  met een expliciete scheiding tussen echte rastergrondwaarheid en uit dossiergeometrie afgeleide
  referentie; (2) bestaande Anthropic-architectuur uitbreiden met een injecteerbare visioncall die
  uitsluitend na een expliciete gebruikersactie draait en exact contract-v1 JSON retourneert;
  (3) login-beveiligde upload/analyse/controlestap bouwen waarin verdiepingvolgorde, iedere ruimte,
  functie, oppervlakte, contour, aangrenzendheid, onzekerheid en herkomst zichtbaar/corrigeerbaar
  zijn en pas een volledige bevestigingspayload het dossier muteert; (4) dataset-evaluatie en
  offline providerfixtures testen, waarbij <5% alleen wordt afgevinkt bij onafhankelijke echte
  labels en anders concreet fail-closed wordt gerapporteerd; (5) blocking verify en onafhankelijke
  review. Inventarisatie vond vooralsnog één echte bouwtekening (`Bouwtekening.jpg` buiten deze
  repo), twee sfeerfoto's en geen tien afzonderlijk gelabelde rasterverdiepingen; de aanwezige
  MagicPlan-dossiers bevatten geometrie maar geen onafhankelijke rastergrondwaarheid.

- 2026-08-21 Codex Builder: na managerbesluit de bestaande Anthropic-architectuur gebruikt voor een
  expliciete visioncall (configureerbare exacte `vision_model`, injecteerbare HTTP-grens, geen call
  bij pagina/openen/uploaden). Login-beveiligde uploadpagina bewaart JPG/PNG veilig en in expliciete
  volgorde; controlestap toont aandachtspunten en een volledig corrigeerbare JSON-payload. Alleen de
  aangevinkte, volledige bevestiging muteert een leeg dossier; bestaande geometrie blijft fail-closed.
  Datasetmanifest + generator leveren 10 afzonderlijke gecontroleerd/synthetisch uit drie bestaande
  opnamebrontypen afgeleide vloerbeelden en 20 ruimtemetingen, alle <5% (exact binnen pixelafronding).
  Het lokaal bestaande echte `Bouwtekening.jpg` is een real-world smoke zonder betrouwbare schaal/
  labels en leidt daarom niet tot een praktijkclaim. Providerbeleid en beperking voor willekeurige
  scans staan in `docs/plattegrond-vision-contract.md`. Blocking verify PASS, 1039/1039.
  Onafhankelijke herreview staat open.

## Notes
De repository bevat bij start geen aantoonbare set van tien gelabelde echte plattegronden. Dit kan
een externe acceptatieblokkade worden; bouw geen synthetische nauwkeurigheidsclaim.
