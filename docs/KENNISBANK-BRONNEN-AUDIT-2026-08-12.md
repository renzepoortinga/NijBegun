# Kennisbank — actualiteit, fouten en aandachtspunten

**Controlepeildatum:** 12 augustus 2026.

## Managementconclusie

De kernset is inhoudelijk bruikbaar: NTA 8800:2025+C1:2026, ISSO 82.1 7e druk, BRL 9500-W:2026 en
de Nij Begun-maatregelencatalogus Q3 2026 sluiten qua generatie op elkaar aan. Niet ieder aanwezig
document is echter normatief of geschikt voor onbeperkt gedeeld AI-gebruik.

## Actieve kernbronnen

| Bron | Vastgestelde status | Gebruik |
|---|---|---|
| NTA 8800:2025+C1:2026 | vervangt NTA 8800:2025; maart 2026 | formele bepalingsmethode; licentiebeperkt |
| ISSO 82.1, 7e druk | publicatiedatum 12-01-2026; document noemt status Actueel | opnameprotocol EP-W; licentiebeperkt |
| BRL 9500-W:2026 | vastgesteld 9-10-2025, bindend 14-10-2025, aangewezen 29-05-2026 | proces en certificering |
| Maatregelencatalogus Q3 2026 | bestand 21-07-2026; actieve JSON noemt dezelfde bron en 338 maatregelen | maatregelen en prijzen |
| VABI EPA Online Help | officiële online bron; zichtbare wijzigingsdatum 22-07-2025 | software-uitleg, niet de norm |

## Gevonden fouten of risico's

### 1. BRL-metadata spreekt de inhoud tegen

De PDF-metadata noemt een werknaam met “Bindend nog niet vastgesteld”. De titelpagina vermeldt echter
expliciet vaststelling, bindendverklaring en ministeriële aanwijzing op 29-05-2026. De titelpagina is
inhoudelijk leidend; de misleidende metadata wordt niet als status gebruikt.

### 2. Twee identieke opdrachtbrieven

`Opdrachtbrief 2026 Poortinga Energieadvies.pdf` en de variant “tot en met september” hebben exact
dezelfde SHA-256 en bestandsgrootte. De vraagbaak behandelt de tweede automatisch als duplicaat.

### 3. Persoonlijke downloadgeldigheid is geen publicatieversie

Veel ISSO-PDF's tonen “geldig tot en met” januari/juni 2026. Dit is een toegangs-/downloadmarkering,
niet automatisch de inhoudelijke vervaldatum van de publicatie. Het is wel een licentiesignaal: niet
publiceren, niet onbeperkt delen en vóór gedeeld AI-gebruik de licentievoorwaarden controleren.

### 4. NTA-netwerkgebruik is beperkt

Het voorblad van het aanwezige NTA-exemplaar staat installatie op een stand-alone pc toe. Netwerkgebruik
vereist volgens dat voorblad een aanvullende licentie. Daarom gebruikt de vraagbaak gelicentieerde
NTA-/ISSO-bronnen standaard niet; activering vereist expliciete licentiebevestiging.

### 5. Achtergrondbronnen zijn niet automatisch actueel of normatief

ISSO-SBR 812 (2011), ISSO 61 (2010), het ventilatie-instructieboek (2011), oudere bouwfysicapraktijkboeken
en documenten die nog naar Bouwbesluit 2012 of NTA 8800:2024 verwijzen blijven bruikbaar als achtergrond.
Ze mogen geen actuele NTA-, ISSO- of Nij Begun-regel overschrijven.

### 6. Voorbeeldplannen zijn voorbeelden

De drie voorbeeldplannen tonen vorm en uitwerking, maar zijn geen algemene normbron. Adres-, maatregel-
en woningkeuzes uit een voorbeeld mogen nooit naar een ander dossier worden gekopieerd.

## Cataloguscontrole

De originele spreadsheet en actieve JSON hebben dezelfde versie-/bronnaam:
`Maatregelencatalogus-Q3_2026_21072026.xlsx`. De productie-JSON bevat 338 maatregelen. Er is daarom geen
catalogusmigratie nodig. Bij een volgende spreadsheetversie moet de JSON opnieuw worden gegenereerd en
moeten versie, aantallen, codes en prijsverschillen vóór activering worden gerapporteerd.

## Nog open

- Nij Begun-webpagina's kunnen veranderen zonder lokaal versienummer; maak periodiek een gecontroleerde export.
- Bevestig met NEN/ISSO of en hoe de vraagbaak door meerdere collega's mag worden gebruikt.
- Leg de werkelijk gebruikte VABI EPA-versie per project vast; Online Help is geen versiebewijs van een berekening.

