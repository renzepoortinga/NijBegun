---
id: 024
assigned: Codex Builder
branch: feat/024-catalogus-api
depends_on: []
---

# Task 024 — Maatregelencatalogus uit de publieke API importeren

## Goal
Maak de publieke Nij Begun API de herleidbare bron voor `catalog/catalog.json`, zodat het project
niet langer afhankelijk is van een handmatig aangeleverde XLSX-catalogus.

## Scope
- Gebruik de bestaande `catalog/api_client.py` en de publieke endpoint
  `GET https://api.nij-begun.project.abl.nu/api/v1/measures` (live call expliciet toegestaan door
  de gebruiker op 2026-08-21).
- Leg de technische API-specversie (`1.0`), ophaaltijd en een reproduceerbare contentfingerprint
  vast; de API geeft zelf geen inhoudelijke catalogusversie of wijzigingsdatum.
- Maak de mapping categoriegedreven waar nodig; nieuwe codes zoals `B5-*` mogen niet met lege
  `onderdeel`/`level` worden geïmporteerd.
- Genereer en commit de actuele `catalog/catalog.json` uit de live API.
- Maak een controleerbaar verschilrapport versus de huidige XLSX-snapshot: toegevoegde,
  verwijderde en inhoudelijk gewijzigde codes. Controleer expliciet alle codeverwijzingen in
  engine, validator, prijslogica en tests voordat verwijderde API-codes verdwijnen.
- Voeg offline fixtures/tests toe voor mapping, fingerprint/versionering en verschilvalidatie;
  CI mag nooit van de live API afhangen.
- Documenteer het expliciete refreshcommando en de bron-/versiebetekenis in `docs/`.

## Out of scope
- Prijzen of codes zelf corrigeren wanneer de API ze anders levert dan de XLSX; afwijkingen worden
  gerapporteerd, niet gegokt.
- Een automatische geplande live refresh of deploymentwijziging.
- Nieuwe dependencies.
- Andere catalogus- of maatregelkeuzelogica refactoren buiten noodzakelijke compatibiliteitsfixes.

## Acceptance criteria
- [ ] `catalog/catalog.json` is uit de live API gegenereerd en bevat bron, API-specversie,
      ophaaltijd en contentfingerprint.
- [ ] Geen geïmporteerde regel heeft leeg `onderdeel`, `level`, `code` of een ongeldige prijs.
- [ ] Een gecommit verschilrapport verklaart toegevoegde/verwijderde codes en materiële
      prijsverschillen; alle projectreferenties naar verwijderde codes zijn afgehandeld of luid
      geblokkeerd.
- [ ] Offline tests bewijzen de mapping en CI doet geen live netwerkcall.
- [ ] `./scripts/verify.sh` slaagt met de Python-testcheck blocking.
- [ ] AI-review PASS door een andere agent dan de bouwer.

## Sessions

- 2026-08-21 Codex integrator (plan na expliciet gebruikersbesluit): (1) leg een benoemde,
  exact gematchte bronoverride vast die uitsluitend bij code `V1-2-X3` de rolsteiger
  EUR 250,43/st behoudt en de hoogwerker EUR 569,25/wk negeert; (2) bewijs offline dat de uitkomst
  API-volgorde-onafhankelijk is en ieder ander duplicateconflict blijft blokkeren; (3) voer de
  expliciet toegestane publieke live refresh uit naar `catalog/catalog.json` plus verschilrapport,
  scan alle verwijderde codes tegen productiereferenties; (4) draai blocking verify, commit/push en
  vraag onafhankelijke review door een andere agent. Geen `.env` lezen en geen deployment.

- 2026-08-21 Codex integrator (uitvoering): gecontroleerde bronoverride geïmplementeerd; alleen de
  exact bekende `V1-2-X3`-hoogwerker (EUR 569,25/wk, V2-3) wordt genegeerd wanneer de exact gekozen
  rolsteiger (EUR 250,43/st, V1-2) aanwezig is. Afwijkende prijzen/velden en alle andere conflicten
  blijven blokkeren; API-volgorde-onafhankelijkheid en zichtbaarheid in catalogus/rapport zijn
  offline getest. Publieke live refresh zonder `.env` uitgevoerd: 291 regels, fingerprint
  `sha256:696d5894e3f8491c33892c16094e4fc5b847c23105b414b2a372942015e44951`, vier genegeerde
  hoogwerkervoorkomens expliciet vastgelegd. Verschil versus XLSX: 6 toegevoegd, 52 verwijderd,
  285 gewijzigd; exacte scan vond nul productiereferenties naar verwijderde codes. Blocking
  `verify.sh`: PASS (1034/1034). Geen deployment uitgevoerd; onafhankelijke review volgt.

- 2026-08-21 Codex Manager (live hercontrole): de publieke endpoint opnieuw read-only opgehaald,
  zonder `.env` of API-key. De API levert nog steeds 192 measures en de gevalideerde mapper stopt
  nog steeds luid op `V1-2-X3`: vijfmaal rolsteiger EUR 250,43/st onder V1-2 tegenover viermaal
  hoogwerker EUR 569,25/wk onder V2-3. Er is niets gepubliceerd of aan `catalog/catalog.json`
  gewijzigd; broncorrectie blijft noodzakelijk voordat de live-importcriteria veilig kunnen worden
  afgevinkt.

- 2026-08-21 Codex Manager: live API geïnventariseerd. API-spec `1.0`, 192 measures; bestaande
  mapper levert 291 regels versus 338 XLSX-regels: 6 codes toegevoegd, 52 verwijderd en 285
  gemeenschappelijke regels gewijzigd. Nieuwe `B5-*`-codes tonen dat de huidige vaste V1–V6-
  prefixmapping niet blind kan worden gebruikt. Taak daarom afgebakend vóór import.

- 2026-08-21 Codex Builder: publieke endpoint live opgehaald zonder `.env`; 192 measures zijn naar
  291 gevalideerde catalogusregels gemapt. API-relaties sturen de categorie (daardoor vallen
  `B5-1-A1/A2` correct onder V5), en bron-URL, specversie 1.0, UTC-ophaaltijd en canonieke
  SHA-256-fingerprint zijn vastgelegd. Verschilrapport commitklaar gemaakt: 6 toegevoegd, 52
  verwijderd, 285 gewijzigd; exacte scan vond geen productiereferenties naar verwijderde codes.
  Offline fixture/tests dekken B5, fingerprint, metadata, validatie en diff. `verify.sh`: PASS,
  801/801 Python-checks groen. Onafhankelijke AI-review is nog aan de Manager.

- 2026-08-21 Codex Builder (reviewfix): review FAIL terecht verwerkt. Duplicatecodes worden nu
  alleen identiek gededupliceerd; conflicten blokkeren onafhankelijk van API-volgorde. Daardoor is
  een echte API-bronfout ontdekt: `V1-2-X3` is zowel rolsteiger EUR 250,43/st onder V1-2 als
  hoogwerker EUR 569,25/wk onder V2-3. De orderafhankelijke API-snapshot is teruggedraaid naar de
  geldige XLSX-catalogus; lokaal kiezen is expliciet out-of-scope. Fingerprint baseert zich voortaan
  op gevalideerde gemapte regels. Catalogus en optioneel rapport worden volledig gestaged/gefsynct
  en transactioneel vervangen met rollback en tempcleanup bij schrijf-/replacefouten. Offline
  regressies dekken omgekeerde volgorde, conflicterende duplicates, disk-/replacefouten en ontbrekende
  `previous` vóór mutatie. Eerste blocking run gaf incidenteel 804/805 zonder bewaarde foutregel;
  een directe run en vijf extra volledige suites gaven elk 805/805. Niet deterministisch
  reproduceerbaar en geen relatie met cataloguscode gevonden. Definitieve Git-Bash `verify.sh` na
  extra gedeeltelijke-stagingregressie: PASS met 806/806; herreview blijft aan de Manager.

- 2026-08-21 Codex Builder (draft na rebase): gerebased op `origin/main` na afronding van taken
  020 en 023; inhoudelijke code en geldige XLSX-productiecatalogus behouden. Onafhankelijke
  herreview: **CODE PASS** voor duplicatevalidatie, mapped-outputfingerprint en transactionele
  publicatie. Taak blijft extern geblokkeerd en actief: de live API levert code `V1-2-X3`
  gelijktijdig als rolsteiger EUR 250,43/st onder V1-2 en als hoogwerker EUR 569,25/wk onder V2-3.
  Zonder correctie door de API-eigenaar kan de actuele API-catalogus niet veilig worden gepubliceerd;
  de live-import-acceptatiecriteria blijven daarom bewust ongecheckt. Blocking Git-Bash
  `verify.sh` na rebase: PASS, 974/974.

- 2026-08-21 Codex integratieonderhoud: branch opnieuw gerebased op actuele `origin/main`
  (`1867e96`, inclusief afgeronde taken 016 en 021). De conflictblokkade voor `V1-2-X3` bleef
  ongewijzigd en `catalog/catalog.json` bleef byte-identiek aan de geldige XLSX-productiesnapshot
  (Git-blob `c396767c652b33974e39e1ebfe9d531f2664347b`). Geen live refresh of publicatie uitgevoerd;
  taak blijft actief/draft in afwachting van correctie door de API-eigenaar. Twee eerste runs
  raakten opnieuw de al gedocumenteerde incidentele atomische-VABI-test; zonder bronwijziging was
  de daaropvolgende volledige suite groen en de definitieve blocking `verify.sh` PASS (1029/1029).

## Notes
De API-response bevat geen inhoudelijke catalogusversie of `updatedAt`; noem de live stand dus
niet bijvoorbeeld “Q4” zonder bronbewijs. Gebruik ophaaltijd + fingerprint voor herleidbaarheid.
