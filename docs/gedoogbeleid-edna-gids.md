# Gedoogbeleid vleermuizen & eDNA — bij spouwmuurisolatie

> **Sinds 1 juli 2026, alleen provincie GRONINGEN.** Bron: Nij Begun "Werkwijze nieuw gedoogbeleid
> isolatieadviseurs per 01-07-2026" + mail Marjet Poorta (13-7-2026). Vragen over het beleid:
> m.i.poorta@provinciegroningen.nl

## Waar gaat dit over?

Vleermuizen zitten vaak in spouwmuren. Om verduurzaming en soortenbescherming in balans te brengen
geldt er een nieuw, gerichter gedoogbeleid: **vóórdat een spouw wordt geïsoleerd moet met de
eDNA-methode worden vastgesteld of er vleermuizen zitten — en welke soort.** Het DNA wordt in een
lab getest (conform **BRL IC-200**).

**Dit raakt jouw advies direct:** adviseer je spouwmuurisolatie in Groningen, dan **moeten** de
eDNA- en natuurvrij-maatregelen in het isolatieplan staan. Ontbreken ze, dan is het plan niet
compleet.

## Groningen of Drenthe? — eerst dit checken

| | |
|---|---|
| **Provincie Groningen** | eDNA-onderzoek is **verplicht** bij spouwmuurisolatie. Codes hieronder opnemen. |
| **Provincie Drenthe** (ook de 3 deelnemende Drentse gemeenten) | **Geen** eDNA-verplichting. De woningeigenaar checkt bij de **gemeente** of er een **soortenmanagementplan (SMP)** is. |

De tool gaat standaard uit van Groningen en waarschuwt apart als de postcode op Drenthe wijst.
Twijfel je bij een grensgemeente? Controleer het zelf — het bepaalt of deze codes verplicht zijn.

## De drie mogelijke uitkomsten van de eDNA-test

1. **Geen vleermuizen gevonden** → isoleren mag. Het isolatiebedrijf plaatst **altijd** een nieuwe
   verblijfplaats als vervanging.
2. **Gewone of ruige dwergvleermuis** → isoleren mag doorgaan. Het bedrijf moet dan: de vleermuizen
   de woning laten verlaten vóór de start, een **alternatieve verblijfplaats** regelen, en **buiten
   de kraam- en winterperiode** werken.
3. **Bijzondere soort** (bv. meervleermuis of laatvlieger) → **maatwerk**. De isolatie wordt
   **uitgesteld** tot de gemeente hiervoor een werkwijze in een SMP heeft opgenomen.

> Let op: ook bij uitkomst 1 (géén vleermuizen) is de **alternatieve verblijfplaats verplicht**
> wanneer de bewoner gebruik wil maken van de isolatiesubsidie.

## De maatregelcodes (hoofdcategorie 1 — Gevelisolatie)

Kies de variant die past bij het **woningtype**. Prijzen incl. btw.

| Code | Maatregel | Eenheid | Prijs |
|---|---|---|---|
| **V1-1-X13** | Natuurvrij maken — **tussen- of rijwoning** | woning | € 435,60 |
| **V1-1-X14** | Natuurvrij maken — **hoek- of vrijstaande woning** | woning | € 496,10 |
| **V1-1-X15** | eDNA sporenonderzoek — **tussen- of rijwoning** | woning | € 484,00 |
| **V1-1-X16** | eDNA sporenonderzoek — **hoek- of vrijstaande woning** | woning | € 484,00 |
| **V1-1-X17** | **Alternatieve verblijfplaats** (stelpost) | stuks | € 151,25 |

**Vuistregel bij spouwmuurisolatie in Groningen:** één natuurvrij-code (X13 óf X14) + één
eDNA-code (X15 óf X16) + **altijd** X17.

Alle genoemde kosten worden — afhankelijk van postcodegebied en inkomen — voor **50% of 100%**
vergoed, net als de andere maatregelen.

## Wat doet de tool, en wat doe jij?

De tool **voegt deze codes bewust niet automatisch toe**. Reden: welke variant klopt (tussen/rij vs
hoek/vrijstaand) en of de woning echt in Groningen ligt, is een bewuste adviseurskeuze — een
verkeerde automatische gok zou stil een verplichte maatregel toevoegen of weglaten.

Wat de tool wél doet: zodra er **spouw aanwezig** is, verschijnt in de stap **Maatregelen** een
luide melding:

- **Groningen** → "voeg zelf V1-1-X13/X14 + X15/X16 + X17 toe (eDNA conform BRL IC-200)"
- **Drenthe** → "geen eDNA-verplichting; laat de bewoner de SMP bij de gemeente checken"

Je vindt de codes onder **"Zelf kiezen uit de catalogus"** → hoofdcategorie **1 Gevel**.

## Checklist bij een plan met spouwmuurisolatie

- [ ] Ligt de woning in provincie **Groningen**? (zo nee → geen eDNA, wel SMP-advies aan bewoner)
- [ ] **Natuurvrij maken** opgenomen — juiste variant voor het woningtype (X13 of X14)
- [ ] **eDNA sporenonderzoek** opgenomen — juiste variant (X15 of X16)
- [ ] **Alternatieve verblijfplaats** (X17) opgenomen — **altijd**, ook bij een negatieve test
- [ ] Bewoner geïnformeerd dat bij een bijzondere soort de isolatie kan worden **uitgesteld**

---
*Codes en prijzen komen uit de officiële werkwijze (1-7-2026) en staan in `catalog/catalog.json`.
De maatregelencatalogus (MC) van Nij Begun is leidend — draai `python catalog/api_client.py --refresh`
om de live-versie op te halen.*
