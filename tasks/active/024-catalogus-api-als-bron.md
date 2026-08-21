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

## Notes
De API-response bevat geen inhoudelijke catalogusversie of `updatedAt`; noem de live stand dus
niet bijvoorbeeld “Q4” zonder bronbewijs. Gebruik ophaaltijd + fingerprint voor herleidbaarheid.
