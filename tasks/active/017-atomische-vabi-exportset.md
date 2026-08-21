---
id: 017
assigned: Codex Builder
branch: feat/017-atomische-vabi-exportset
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
- [x] Elke geïnjecteerde writerfout laat de vorige complete eindset onaangetast.
- [x] Succes publiceert precies één onderling consistente set.
- [x] Tijdelijke bestanden worden na succes en fout veilig opgeruimd.
- [x] `./scripts/verify.sh` slaagt.
- [ ] AI-review PASS door een andere agent dan de bouwer.

## Sessions

- 2026-08-21 (Codex Builder): `vabi/generate_all.py` publiceert writers voortaan eerst naar een unieke staging-directory, valideert drie niet-lege/well-formed XML-bestanden plus `IMPORTEREN.txt`, promoveert die naar een immutable UUID-set en wisselt daarna atomisch `CURRENT.json` met `os.replace`. Bij elke writerfout blijven manifest en vorige set intact en verdwijnen staging/onzichtbare sets. Dashboard-download en bestandslijst lezen de actuele setdirectory. Foutinjectietests voor constructie-, objecten-, installatie- en instructiewriter toegevoegd. `python tests/run_tests.py`: 786 PASS, uitsluitend de 2 reeds bekende taak-002-omgevingschecks FAIL (extern `config.json`/plan-json); nieuwe X3-tests alle PASS. `C:\Program Files\Git\bin\bash.exe scripts/verify.sh`: PASS met uitsluitend dezelfde bekende taak-002 advisory.
- 2026-08-21 (Codex Builder, reviewfix): dashboard-downloadroute en volledige projectexport resolveren nu de actuele `CURRENT.json`-set; zonder manifest blijven bestaande vlakke `vabi_huidig`/`vabi_na`-exports werken. Daardoor bevat `02_VABI` weer de echte bibliotheken en nooit manifest-/setinfrastructuur. Prefix is vóór enige directoryaanmaak beperkt tot een veilig bestandsnaamcomponent. Regressies toegevoegd voor CURRENT-download, legacy-download, projectzip, traversal, geweigerde manifestwissel (pointer en setinventaris onveranderd) en twee gelijktijdige publicaties. `python tests/run_tests.py`: 791 PASS, alleen de 2 bekende taak-002-omgevingschecks FAIL. `C:\Program Files\Git\bin\bash.exe scripts/verify.sh`: PASS met uitsluitend dezelfde bekende taak-002 advisory; `py_compile` en `git diff --check` schoon.

## Notes
Auditreview 15-8-2026: `generate_all.py` doet wel preflight vóór schrijven, maar schrijft daarna sequentieel naar eindpaden.
