---
id: 004
assigned: Codex (OpenAI), Builder
branch: feat/bcrg-code-en-dikte
depends_on: []
---

# Task 004 — Kwaliteitsverklaring compleet invoeren met BCRG-code

## Goal
Een kwaliteitsverklaring expliciet en volledig vanuit MagicPlan vastleggen,
zodat een ontbrekende code/dikte de Vabi-export blokkeert en Vabi vervolgens
zelf via zijn BCRG-koppeling de verklaring en rekenwaarden kan ophalen.

## Scope
- Breid `SchilDeel` en `BouwdeelStandaard` uit met een optionele BCRG-code.
- Voeg in de MagicPlan-constructieboom bij `Isolatie aanwezig?` de vierde optie
  `Ja — kwaliteitsverklaring` toe.
- Voeg daaronder conditionele velden `BCRG-code` en `Isolatiedikte (mm)` toe
  voor gevel, vloer en dak, inclusief relevante per-elementoverride.
- Lees beide velden uit Statistics-CSV en report-PDF en bewaar ze in het
  canonieke dossier; dakvlakken erven de code van `dak_standaard`.
- Gebruik uitsluitend deze expliciete isolatiekeuze om de nieuwe route te
  activeren. Gewoon `Ja`, `Nee` en `Onbekend` behouden exact hun huidige
  betekenis en exportgedrag.
- Kwaliteitsverklaring zonder BCRG-code of zonder isolatiedikte: harde,
  concrete preflightfout met de betrokken schildeel-id's.
- Kwaliteitsverklaring met code+dikte: exporteer de minimale, door Vabi
  verwachte kwaliteitsverklaringroute. Vabi haalt via zijn eigen
  BCRG-koppeling UUID, merk, toepassingsvariant en Rc/U op; de tool rekent of
  kopieert die waarden niet zelf.
- Werk dashboardmeldingen, opname-instructie en live-formdocumentatie bij.
- Voeg ketentests toe voor MagicPlan -> dossier -> alle Vabi-bibliotheken.

## Referentie en validatie
Het geüploade Vabi-monitoringbestand bewijst de kwaliteitsverklaringvelden en
codes voor dak en vloer. De definitieve DoD bevat een echte import in de
ondersteunde Vabi EPA-W-versie: Vabi moet op basis van BCRG-code+dikte de
verklaring herkennen en de juiste variant/rekenwaarde ophalen. Tot die test
slaagt mag geen forfaitaire fallback worden gebruikt.

## Out of scope
- BCRG-gegevens, Rc/U-waarden of Vabi-enumcodes gokken.
- Zelf NTA 8800 rekenen.
- Een eigen BCRG-API-client of API-key in deze tool; Vabi verzorgt de lookup.
- Installatiekwaliteitsverklaringen, glas/kozijnverklaringen of automatische
  live BCRG-API-opzoeking.
- Bestaande dossiers stil migreren naar de nieuwe kwaliteitsverklaringroute.
- Live MagicPlan API-calls zonder afzonderlijke expliciete toestemming en een
  ondersteunde geheimenroute.

## Acceptance criteria
- [ ] `Isolatie aanwezig? = Onbekend` blijft exporteerbaar via de bestaande
      beslisschema-/forfaitaire route.
- [ ] Gewoon `Ja` en `Nee` blijven ongewijzigd werken.
- [ ] `Ja — kwaliteitsverklaring` zonder BCRG-code of zonder isolatiedikte
      blokkeert vóór enig Vabi-exportbestand wordt geschreven.
- [ ] De BCRG-code blijft behouden van MagicPlan-export tot dossier en
      dak-erfenis.
- [ ] Met BCRG-code+dikte bevat de constructie-export de door de referentie
      bewezen invoermethode en minimale verklaringvelden en geen
      `Onbekend`-/forfaitaire fallback.
- [ ] Constructie- en objectbibliotheek verwijzen naar dezelfde deterministische
      constructie-GUID.
- [ ] De gegenereerde bibliotheken zijn daadwerkelijk importeerbaar in de
      ondersteunde Vabi EPA-W-versie en Vabi haalt de verklaring/rekenwaarde
      zelf via BCRG op.
- [ ] Dashboard toont onderscheid tussen ontbrekende BCRG-code en andere
      exportproblemen.
- [ ] Bestaande tests en nieuwe regressietests slagen via `./scripts/verify.sh`.

## Sessions
- 2026-08-13 Codex (OpenAI), Manager: plan door gebruiker goedgekeurd. Taak in
  backlog geplaatst omdat een echte Vabi-referentie-export nog ontbreekt. De
  bestaande harde gate blijft bewust actief totdat de mapping bewezen is.
- 2026-08-13 Codex (OpenAI), Manager: geüpload monitoringbestand
  `9501TP-32-- (monitor).xml` onderzocht. Dit bewijst voor dak en vloer:
  `Invoer=0`, `KwaliteitsverklaringInvoermethode=1` en daarnaast Code,
  KwaliteitsverklaringId (UUID), Merk, toepassings-Type, isolatiedikte en Rc.
  Alleen een handmatig ingevoerde BCRG-code is dus onvoldoende om de juiste
  constructie te reconstrueren. Het bestand bevat geen gevel met
  kwaliteitsverklaring; de gevel gebruikt `Invoer=6` (forfaitair). Het bestand
  bevat adres-/objectgegevens en mag niet ongeschoond als testfixture worden
  gecommit.
- 2026-08-13 Codex (OpenAI), Manager: gebruiker kiest de aanbevolen route:
  automatische gecontroleerde BCRG-opzoeking op basis van de code. Officiële
  BCRG-informatie bevestigt dat hiervoor een afzonderlijk aan te vragen
  API-key/dataverbinding nodig is. Implementatie moet een injecteerbare offline
  client + gesaniteerde responsefixture krijgen; sleutel uitsluitend via de
  bestaande geheimen/configuratiestroom, nooit in code, logs of fixtures.
- 2026-08-13 Codex (OpenAI), Manager: gebruiker corrigeert de architectuur:
  Vabi heeft zelf de BCRG-koppeling; BCRG-code + isolatiedikte zijn de benodigde
  invoer. Besluit herzien: geen eigen API-client/key. Taak naar ready verplaatst;
  Vabi-import is de harde praktijkvalidatie.
- 2026-08-13 Codex (OpenAI), Builder: implementatie op
  `feat/bcrg-code-en-dikte`. Canoniek model, Statistics-CSV, report-PDF/API-route,
  dakstandaard-erfenis, webeditor, MagicPlan-formmerge en documentatie uitgebreid.
  Alleen `Isolatie aanwezig? = Ja — kwaliteitsverklaring` activeert de route;
  oude `rc_bron`/`Invoer`-waarden doen dat niet. Preflight onderscheidt ontbrekende
  BCRG-code en ontbrekende dikte en blokkeert vóór de uitvoermap. Complete invoer
  schrijft uitsluitend de door de monitor bewezen velden (`Invoer=0`, methode `1`,
  Code, KV-isolatiedikte), met Rc/U, merk, UUID en toepassingsvariant leeg/nul; geen
  forfaitaire fallback. Gerichte offline proeven voor CSV, report-parser, formmerge,
  blokkade en alle drie bibliotheken slagen. `./scripts/verify.sh` PASS; de bestaande
  advisory blijft dat de volledige Python-suite in deze kale omgeving niet start
  doordat `lxml` ontbreekt (taak 002). Het privacygevoelige monitorbestand bleef
  untracked en is niet als fixture gekopieerd. Nog verplicht: echte import in de
  ondersteunde Vabi EPA-W-versie om te bewijzen dat Vabi code+dikte resolveert;
  MagicPlan-formwijziging is alleen offline voorbereid en niet live gepubliceerd.

## Notes
Taak 003 blokkeert nu iedere `rc_bron=Kwaliteitsverklaring`, omdat het dossier
geen BCRG-code bevat en de repository alleen forfaitaire Vabi-constructies als
referentie heeft. Taak 004 vervangt die grove toestand door een expliciete,
complete route zonder de gewone keuze `Onbekend` te veranderen.

Architectuurbesluit: deze tool exporteert alleen code+dikte op de bewezen
kwaliteitsverklaringroute. Vabi verzorgt de BCRG-lookup en bepaalt de
toepassingsvariant en Rc/U. De tool neemt die rekenrol niet over.
