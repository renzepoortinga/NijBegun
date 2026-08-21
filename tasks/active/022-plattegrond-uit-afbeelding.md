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
- [ ] Op minimaal tien echte plattegronden is de oppervlakteafwijking per ruimte <5%, of het model
      meldt expliciet dat schaal niet betrouwbaar bepaalbaar is.
- [ ] Elke waarde is vóór rekenen corrigeerbaar en expliciet bevestigd.
- [ ] Onzekerheden zijn aandachtspunten, nooit stille aannames.
- [ ] Herkomst per waarde staat in het dossier.
- [ ] `./scripts/verify.sh` slaagt.
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

## Notes
De repository bevat bij start geen aantoonbare set van tien gelabelde echte plattegronden. Dit kan
een externe acceptatieblokkade worden; bouw geen synthetische nauwkeurigheidsclaim.
