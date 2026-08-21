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

## Notes
De API-response bevat geen inhoudelijke catalogusversie of `updatedAt`; noem de live stand dus
niet bijvoorbeeld “Q4” zonder bronbewijs. Gebruik ophaaltijd + fingerprint voor herleidbaarheid.
