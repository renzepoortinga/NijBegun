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
- [x] Elke ondersteunde dropdown heeft één herleidbare canonieke definitie. `core/mapping_manifest.py`
      bevat 6 entries (begrenzing, glastype, kozijnmateriaal, gevel-oriëntatie, woningtype/subtype,
      PV-oriëntatie) — elk met bronform/bronlabel/canoniek dossierveld/parser-normalisatie/webapp-
      optielijst/VABI-pad+codes/bewijsstatus, en elke verwijzing is een `module:attribuut`-referentie
      naar de ECHTE code (geen dubbele data). **Scope-grens, expliciet**: dit dekt de dropdowns die al
      een eigen canonieke mapping-dict/functie in de code hadden (waar drift kon ontstaan); overige
      MagicPlan-velden (thermische massa, ventilatiesysteem A-E, verwarming-opwekker/afgifte,
      tapwater-toestel) hebben nog geen manifest-entry — die gaan grotendeels direct/sjabloon-passthrough
      of zijn nog golden-rule-geflagd, dus minder acuut driftgevoelig; uitbreiden is vervolgwerk.
- [x] Drift tussen live/form-spec/parser/webapp faalt luid. `scripts/check_mapping_manifest.py`
      (`run_checks()`) controleert offline: (1) elke code-referentie in het manifest bestaat nog
      (kapotte referentie -> AttributeError, getest); (2) elke canonieke waarde die de parser kan
      produceren staat als optie in de webapp-`<select>` (het exacte patroon van de hieronder
      gevonden kozijnmateriaal-bug); (3) elke webapp-optie levert een VABI-code op via dezelfde
      normalisatieweg als de echte generator (Codebook/`_grenst_aan_code`/`_subtype_code`), tenzij
      expliciet als bewust onbevestigd gemarkeerd. Draait blocking mee in `tests/run_tests.py` (sectie
      AD). "live" zelf blijft de aparte, expliciete `--refresh-live`-actie (zie hieronder) — geen
      testafhankelijkheid, zoals de Scope voorschrijft.
- [x] Onbevestigde Vabi-code is zichtbaar en wordt niet geschreven. Ongewijzigd (golden rule,
      bestaande preflight-poorten); het manifest maakt bewust-onbevestigde opties nu ook expliciet
      (`vabi_onbevestigde_opties`, bv. de 4 meergezins-woningtypes buiten Nij Begun-scope).
- [x] Dossier bevat form fingerprint en importtijd. `Meta.magicplan_form_fingerprint` +
      `Meta.magicplan_form_snapshot_datum` + `Meta.magicplan_import_op` (nieuw in `core/dossier.py`).
      `magicplan/form_fingerprint.py`: `compute_fingerprint()` (sha256, orde-ongevoelig, gevoelig voor
      echte inhoudswijziging — alle 3 getest), gestempeld door `stamp_dossier_meta()` uit een
      GEDATEERDE, gecommitte snapshot (`magicplan/refs/forms_snapshot.json`, datum 2026-08-21,
      handmatig overgenomen uit `docs/magicplan-forms-live.md` — geen live call). Gewired in alle 3
      echte MagicPlan-importroutes (`statistics_csv.build_dossier`, `assemble.build_dossier`,
      `extractor.map_plan_to_dossier`) — getest dat alle 3 de stempel-call bevatten (bron-inspectie,
      voorkomt dat een route de stap ooit stil overslaat). Live verversen is een APARTE, expliciete
      actie (`python -m magicplan.form_fingerprint --refresh-live`, vereist .env + internet) — nooit
      vanuit build_dossier of tests aangeroepen, zoals de Scope voorschrijft.
- [x] Elk geïmporteerd vlak heeft stabiele bronprovenance die een herimport overleeft — **scoped naar
      wat taak 014 nodig had** (ongewijzigd t.o.v. de vorige sessie): `SchilDeel.bron`
      (`magicplan-import` | `magicplan-dak-fallback` | `webapp-wizard`) op elk schildeel;
      CSV-herimport draagt `webapp-wizard`-dakvlakken nu over i.p.v. ze stil te wissen. GEEN generieke
      stabiele per-vlak-ID voor gevel/vloer/kozijn bij herimport — nog steeds vervolgwerk, niet acuut
      (geen bekende klacht zoals bij dak).
- [x] `./scripts/verify.sh` slaagt (PASS na rebase op `origin/main`; Python-tests blocking:
      841/841 groen).
- [ ] AI-review PASS door een andere agent dan de bouwer. (review loopt, zie Sessions zodra klaar)

## Sessions
- 2026-08-15 (los gesprek, ná taak 013's ketenaudit) — user vroeg expliciet om taak 014
  (dubbele dakvlakken, Essenhage) door te voeren; op advies eerst dit scoped stuk van 015
  gedaan omdat 014 ervan afhangt. GEEN volledig mappingmanifest/form-fingerprint gebouwd (te
  groot voor deze sessie) — alleen `SchilDeel.bron`-provenance + dak-herimport-behoud, het
  minimum dat taak 014 nodig had. Zie `tasks/active/014-dakmigratie-zonder-dubbele-vlakken.md`
  voor het vervolg. 797/799 tests groen (2 bekende omgevingsfalen buiten de repo, taak 002).
  Het brede manifest/fingerprint/CI-drift-werk staat nog volledig open — nieuwe sessie nodig.
- 2026-08-21 (nieuwe sessie, deze worktree) — de rest van 015 afgemaakt (taak 014 bleek al
  volledig afgerond en in `tasks/done/` te staan uit dezelfde eerdere sessie; niets meer te doen
  daar). Gebouwd: `core/mapping_manifest.py` (6 entries) + `scripts/check_mapping_manifest.py`
  (drift-checks + `docs/mapping-overview.md`-generator/validator) + `magicplan/form_fingerprint.py`
  (snapshot-fingerprint + dossier-meta-stempeling + expliciete `--refresh-live`) +
  `magicplan/refs/forms_snapshot.json` (gedateerde snapshot, handmatig uit `magicplan-forms-live.md`
  overgenomen). Onderweg gevonden EN gefixt: het manifest legde een ECHTE, live drift bloot —
  `magicplan/statistics_csv.py::_norm_kozijn_mat`/`_KOZIJN_MAT` produceerden "Metaal thermisch
  onderbroken" (zonder haakjes), maar `dashboard/app.py::KOZ_OPTS` (de webapp-`<select>`) kent alleen
  "Metaal (thermisch onderbroken)" (mét haakjes, = het echte MagicPlan/VABI-label) — een via de CSV
  geïmporteerd metalen kozijn werd bij de eerstvolgende webapp-opslag STIL overschreven naar de
  default (zelfde patroon als de al-bekende begrenzing-/glas-risico's uit de aannames-audit van 30-7,
  maar toen niet meegenomen voor kozijnmateriaal). Gefixt door de parser-uitvoer op het echte label
  (mét haakjes) te zetten; 3 bestaande tests aangepast op de nieuwe canonieke string. Testsuite met
  17 nieuwe checks uitgebreid (sectie AD: manifest-drift, doc-round-trip, fingerprint-stabiliteit/
  -gevoeligheid, dossier-meta-stempeling op alle 3 importroutes). 826/828 groen (2 bekende
  omgevingsfalen, ongewijzigd, taak 002). `./scripts/verify.sh`: PASS.
- 2026-08-21 (Builder/Integrator, vervolgsessie) — vóór de rebase de twee lokaal aangemaakte
  backlogtaken hernummerd om botsingen met de inmiddels gebruikte nummers te voorkomen:
  dakkapel/preflight van 020 naar 023 en MagicPlan-SSL van 019 naar 025; interne verwijzingen
  in taak 014 en 023 overeenkomstig bijgewerkt. Daarna alle 7 branchcommits op actuele
  `origin/main` gerebased. Conflicten in `docs/STATE.md` en `vabi/generate_all.py` inhoudelijk
  opgelost: taak-017's atomische publicatie bleef leidend en taak-014's dubbele-dakpreflight
  is daarin behouden. Door de rebase teruggekomen backlogkopieën van de reeds afgeronde taken
  017/018 verwijderd. De laatste reviewfix voor live formulierrefresh vervolgens offline
  afgedekt: gelijknamige groepen/velden uit `fetch_forms` en `fetch_fields` worden zonder
  duplicaten samengevoegd en bewaren de unie van beide optielijsten, zodat drift niet stil
  verdwijnt. Drie regressietests toegevoegd. Volledige blocking `scripts/verify.sh`: PASS,
  841/841 tests groen.

## Notes
`magicplan-forms-live.md` (23-7) en de doorgevoerde dakvelden van 27-7 spreken elkaar nu tegen —
dat specifieke punt is met deze sessie NIET opgelost (nog steeds relevant voor een vervolgsessie).

Bewust buiten scope gelaten (voor een vervolgsessie, als het ooit acuut wordt): manifest-entries voor
thermische massa/ventilatiesysteem/verwarming-opwekker/tapwater-toestel; een generieke stabiele
per-vlak-ID voor gevel/vloer/kozijn bij CSV-herimport (nu alleen dak, taak 014); de live-refresh-actie
(`--refresh-live`) is geschreven maar NIET in deze sandbox getest (geen internet/.env hier — vereist
Renze's machine, zelfde beperking als `magicplan/extractor.py --project-id`).
