# BRL 9500-W — proceshandleiding (de laag rondom de tool)

Bron: **BRL 9500-W**, Nationale Beoordelingsrichtlijn voor het NL-EPBD®-procescertificaat
'Energieprestatie gebouwen' — bepalen energieprestatie van woningen en woongebouwen,
**aangewezen door de minister op 29-05-2026** (vastgesteld CCvD InstallQ 09-10-2025). Uitsluitend
dit document + ISSO 82.1 (7e druk) als bron. Paragraafnummers (§) verwijzen naar de BRL.

> **Waarom deze doc?** De tool dekt de **opname-INVOER** sterk (geometrie/schil/installaties → 3 VABI-
> bibliotheken → Vabi EPA-W). Maar de BRL stelt ook **proces-, adviseur- en dossiereisen** die *buiten*
> de rekenkern en grotendeels buiten de tool vallen. Die staan hier, zodat het energielabel rechtsgeldig
> wordt afgegeven. Zie de gap-analyse (`docs/ISSO-BRL-gap-analyse.md`) voor wat de tool al borgt.

---

## 0. Twee routes — niet verwarren
| | **Route A — Energielabel** | **Route B — Nij Begun isolatieplan** |
|---|---|---|
| Norm | BRL 9500-W + ISSO 82.1 + NTA 8800 | Nij Begun Maatregel 29 (subsidie) |
| Eindproduct | geregistreerd energieprestatie-rapport (label) | isolatieplan + ventilatie + KWACO |
| Registratie EP-Online | **verplicht** (binnen 3 mnd) | n.v.t. |
| Projectdossier (Bijlage 3) | **verplicht**, 15 jaar bewaren | aanbevolen, lichter |
| Certificaat-/adviseur-eisen | BRL 9500-W-gecertificeerd bedrijf, EP-W/B of /D | handmatige adviseur-route met Vabi |

De tool bedient beide; **de BRL-procesplichten gelden alleen voor Route A.**

---

## 1. Vóór de opname — opdracht & opname-soort vaststellen (§4.2.2, §3.1)

### 1.1 Opname-soort kiezen: basis (EP-W/B) of detail (EP-W/D)
De **afbakeningstabel** (§3.1) bepaalt wat is toegestaan:
| Situatie | Toegestane opname |
|---|---|
| **Toets Bbl** (omgevingsvergunning/aannemelijk maken nieuwbouw) | **Detailopname verplicht** |
| **Oplevering** nieuwbouw / vernieuwing na sloop met nieuwe schil / volledige renovatie naar nieuwbouweisen (na 1-1-2021) | **Detailopname verplicht** |
| **Bestaande woning** | Basis- **óf** detailopname (keuze) |
| Bestaand **woongebouw** | (geen vinkje — zie BRL) |

- **Basisopname → EP-W/B-adviseur** mag; **detailopname → EP-W/D-adviseur** vereist (§4.2.2, §5.3).
- **Gevolg voor invoer:** bij **detailopname** moeten Rc/U/g **onderbouwd** zijn met DoP /
  BCRG-kwaliteitsverklaring / opgemeten dikte — *niet* de forfaitaire bouwjaar-constructies die de tool
  standaard kiest. De adviseur vervangt/onderbouwt dit in Vabi + projectdossier.
- ⚠️ In onze tool is `opname.type_advies` (Basis/Uitgebreid/Label) een **Nij Begun-as** — dat is **niet**
  hetzelfde als de ISSO/BRL-opnameklasse. Leg de opnameklasse apart vast (roadmap-actie).

### 1.2 Doel/bouwfase + aanleiding
Leg vast: **doel** (toets Bbl | oplevering | bestaand) en **aanleiding** (omgevingsvergunning | melding Wkb
| oplevering | verkoop/verhuur). Dit stuurt opname-soort, registratie-termijn en controle-regime.

### 1.3 Gebruiksfunctie-routing (§ onderwerp/doel)
- Andere functie ≤ ½ Ag-woonfunctie **én** ≤ 50 m² → alles woonfunctie (9500-W). Anders splitsen / 9500-U.
- Meerdere recreatiewoningen op gemeenschappelijke verkeersroute → 9500-U.

### 1.4 Opdrachtgever schriftelijk informeren (§4.2.2)
Verplichte onderwerpen vóór aanvang: **EP-Online-registratie**, **recht op het projectdossier**,
**CI-controle** (de woning kan gecontroleerd worden), **klachtenprocedure**, en **WLC-GWP vanaf 2028**
(nieuwbouw > 1000 m²). Plus afspraken over aan te leveren gegevens (Bijlage 4).

---

## 2. Tijdens de opname — eisen aan de werkzaamheden (§4.2.2)

- **Opnemende adviseur** legt feitelijk op; bij gebruik van tekeningen/schema's geldt **controleplicht
  ter plaatse** (nagaan of verstrekte gegevens juist/nauwkeurig zijn).
- **Door derden aangeleverde gegevens** (plattegronden/oppervlakken): controleren + **controlebewijs** in
  het projectdossier; herkomst per gegeven vastleggen (opdrachtgever/aannemer/eigen waarneming).
- **Marges** (kritieke afwijking bij overschrijding): Ag max **grootste van 3% of 2 m²**; totaal
  verliesoppervlak Als max **grootste van 5% of 3,5 m²**.
- **'Onbekend' is niet toegestaan bij goed-waarneembare gegevens** (oppervlakte/glas/kozijn/oriëntatie) →
  geldt als kritieke afwijking. Onbekend bij niet-waarneembaar → forfaitair (ISSO 82.1).
- **Kwaliteitsverklaring/DoP**: verplicht gebruiken indien beschikbaar (BCRG); **merk + type** vaststellen
  en aantonen met **foto of factuur**.
- **Installaties** uit feitelijke waarneming of installatieschema's; niet-aangesloten installaties buiten
  beschouwing.
- **Foto's**: overzichts- **én** detailfoto's, met zichtbare samenhang, **door de adviseur zelf** gemaakt,
  **fotodatum ≤ opnamedatum**. Bij opgemeten isolatiedikte: **duimstok-foto** (aanliggend/loodrecht).
- **PV/zonthermisch**: meerekenen met **beschaduwing via foto's**; alleen bij exclusieve fysieke koppeling
  + opbrengst aan de woning.
- **Software**: bepaling uitsluitend met **BRL 9501-geattesteerde, meest actuele** EP-software (NTA 8800).
  → onze golden rule (Vabi = rekenkern) sluit hierop aan.

---

## 3. Datums & adviseurs (§4.2.4, §4.2.5)
- **Opnamedatum** = start wettelijke geldigheid; meerdaagse opname → **startdatum**; preventieve
  **toets Bbl → opnamedatum = registratiedatum**.
- **Registratiedatum** = datum registratie bij RVO/EP-Online.
- **Max. 2 adviseurs**: een **opnemende** en een **registrerende** adviseur (mogen dezelfde zijn).
  De **registrerende adviseur is eindverantwoordelijk**. Van **beiden**: naam + **vakbekwaamheidsnummer**.
- **Software-versie**: vastleggen welke geattesteerde versie is gebruikt (geldig op registratiedatum; bij
  oplevering = versie geldend bij oplevering). Bij **herlabelen**: oorspronkelijke versie + opnamedatum
  behouden, berichttype 'herlabelen' (≤ 24 mnd).

---

## 4. Registreren & leveren (§4.2.5, §4.2.6)
- **Registreren in EP-Online**: **binnen 3 maanden** na opnamedatum (oplevering/bestaand); **binnen 6
  maanden** bij seriematige nieuwbouw/renovatie.
- Alleen registreren **in opdracht van de opdrachtgever**; juiste **berichttype** (regulier vs herlabelen).
- **Levering pas ná registratie**. Schriftelijk rapport aan opdrachtgever conform wet + BRL + ISSO 82.1,
  **incl. uitdraai van de uitvoerfile**; op verzoek papier en/of het volledige projectdossier.

---

## 5. Projectdossier (§4.2.7, Bijlage 3) — 15 jaar bewaren
Het dossier maakt de invoer **reproduceerbaar en toetsbaar**. Bewaarplicht **min. 15 jaar** (§6.7.4).
Volledige afvinklijst: zie **`docs/projectdossier-checklist-bijlage3.md`**. Kern:
opdrachtgever · plattegrond + doorsnede · foto's (overzicht + detail, herleidbaar) · productinfo/DoP/BCRG
met merk + type + bewijs · **herkomst per gegeven + controlebewijs** · onderbouwing schematisering/
inklappen/forfait · EPA-uitvoerfile + **software-versie** · EP-Online-registratiegegevens. AVG-conform opslaan.

---

## 6. Representativiteit & herlabelen (§4.3) — BUITEN TOOLSCOPE
- **Representativiteit**: alleen de **bezochte referentiewoning** krijgt een individueel rapport;
  gelijkende niet-bezochte woningen → **referentie-rapport**. Gelijkendheid bepalen conform ISSO 82.1.
- **Herlabelen** (≤ 24 mnd): als **addendum** op het oorspronkelijke dossier; oorspronkelijke
  softwareversie/opnamedatum; alleen toegestane maatregelen (Bijlage 6a) meerekenen; fysieke-waarneming-
  foto's bij PV/zonthermisch.
- De tool ondersteunt dit **niet** — de adviseur doet het handmatig (zie ISSO H17).

---

## 7. Organisatie & controle (§5–§7) — bij het bedrijf, niet de tool
Vrijwel volledig **buiten toolscope** (certificaathouder-eisen): BRL 9500-W-certificaat + KvK-inschrijving,
vakbekwame adviseurs (Bijlage 2a/2b, EP-W/B of /D, zichtbaar in Centraal Register Techniek),
**projectenregistratie** met onmiddellijke CI-toegang, **interne audits** (≥ 2% per adviseur per
subdeelgebied; oplevering/bestaand 50% dossier + 50% in het werk), **kwaliteitshandboek** (5 procedures),
klachtenprocedure (Bijlage 7), en het **externe** CI-onderzoek (organisatie- + projectgericht, min. 4 u
basis / 5 u detail). De tool helpt hooguit met de **projectenregistratie-export** (roadmap).

---

## Wat hiervan in de tool zit / kan komen
Zie de geprioriteerde roadmap in `docs/ISSO-BRL-gap-analyse.md`. Kort: een **projectdossier-/uitgangspunten-
blok** (herkomst + bewijslast per gegeven), **opdrachtgever + adviseur-rollen splitsen**,
**opnameklasse basis/detail** expliciet, **EPA-softwareversie** vastleggen, en een **BRL-dossier-
volledigheidscheck** (naast de bestaande KWACO-validator). De rest (registratie/audits/certificering)
blijft procesmatig bij de adviseur/het bedrijf.
