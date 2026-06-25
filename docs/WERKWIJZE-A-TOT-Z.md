# Van woning tot isolatieplan — de complete werkwijze (A tot Z)

## 🧒 ELI5 (in één adem)
Je loopt door de woning met **MagicPlan** en tekent de plattegrond. Je geeft elke buitenmuur een
**kompasrichting** (en als-ie niet aan buitenlucht grenst, zet je dat in de **naam** van de muur). Je
vult een paar **projectvelden** in (woningtype, hoogte, bouwjaar, dak, ventilatie). Thuis exporteer je
de **Statistics-CSV** en draai je **één commando**: de tool maakt 3 bestanden die je **in Vabi importeert**,
plus een kant-en-klaar **Nij Begun isolatieplan**. In Vabi druk je op **Rekenen**. Klaar.

---

## Wat je nodig hebt
- **MagicPlan** (app op de iPad/telefoon) met de forms **"Schil & zone"** + **"Installaties"** (incl. foto's) — beide al gepubliceerd.
- De **tool** (deze map) — `python` of de `.exe`.
- **Vabi EPA-W** (de geattesteerde rekenkern; de tool rekent NTA8800 nooit zelf).

> 📋 **In het veld?** Gebruik de korte **per-kamer-werkinstructie**: [`docs/OPNAME-WERKINSTRUCTIE.md`](OPNAME-WERKINSTRUCTIE.md).
> Belangrijkste tijdwinst: benoem buitenmuren **voorgevel/achtergevel/linkergevel/rechtergevel** en geef alléén de
> **oriëntatie van de voorgevel** op — de tool leidt de rest af (zie [`docs/gevel-kompas.svg`](gevel-kompas.svg)).
> Nieuwe formvelden nog niet in MagicPlan? Draai eenmalig `magicplan/push_forms.bat` (zet ze uit code, idempotent).

---

## Twee routes — kies vooraf
- **Route A — Energielabel (BRL 9500-W + ISSO 82.1):** registratie in EP-Online + volledig projectdossier
  verplicht. Heeft de extra BRL-stappen (1a/1b/5/6) hieronder. Opnamesoort **basis (EP-W/B)** óf **detail (EP-W/D)**.
- **Route B — Nij Begun isolatieplan (Maatregel 29):** isolatieplan + ventilatie + KWACO. **Géén**
  EP-Online-registratie- of projectdossierplicht. Sla 1a/1b/5 over; STAP 6 (archiveren) is hier licht.

> De MagicPlan-opname (STAP 2) en de tool (STAP 3) zijn voor **beide** routes identiek — één opname voedt allebei.

## STAP 1 — Voorbereiding (kantoor, 5 min)
1. BAG-gegevens + adres opzoeken (pand-ID + VBO-ID). Screenprint Google Maps (voor het dossier, BRL 9500).
2. Offerte/opdrachtbevestiging in de projectmap.

## STAP 1a — Opname-soort bepalen ⭐ (Route A · BRL §4.2.2 / afbakeningstabel)
Kies vóór je de deur uitgaat de **opnamesoort**, want die is deels wettelijk afgedwongen:

| Bouwfase / doel | Opnamesoort | Adviseur |
|---|---|---|
| **Toets Bbl** (omgevingsvergunning/tekeningen) | **Detailopname** verplicht | EP-W/D |
| **Oplevering** nieuwbouw/renovatie (ook later) | **Detailopname** verplicht | EP-W/D |
| **Bestaande woning** (de Nij Begun-praktijk) | **Basis** óf detail (keuze) | EP-W/B of /D |

Detail óók verplicht bij: vernieuwing-na-sloop met nieuwe schil · volledige renovatie naar nieuwbouweisen (na
1-1-2021) · EPV · BENG aantonen · eerder detail geregistreerd. **Bij detail mag je niet forfaitair inklappen**
— Rc/U onderbouwen met DoP/kwaliteitsverklaring/opgemeten dikte (dat is EP-W/D-werk in Vabi).

## STAP 1b — Opdrachtgever schriftelijk informeren (Route A · BRL §4.2.2)
Stuur (of overhandig) vóór registratie de standaard kennisgeving: **EP-Online-registratie · recht op
projectdossier · controleonderzoek door de CI · mogelijkheid tot intrekken · klachtenprocedure**
(+ WLC-GWP bij grote nieuwbouw). Bewaar het bewijs (datum + bestand) in de projectmap.

## STAP 2 — In de woning: de MagicPlan-opname 🏠
Dit is het echte werk. Doe het zoals je een VABI-invoer zou opbouwen.

### 2a. Scan de plattegrond
Loop elke ruimte in en scan. MagicPlan maakt de plattegrond + de wanden + m².

### 2b. Geef elke BUITENMUUR een oriëntatie ⭐
- Tag **iedere buitenmuur** met een kompasrichting (N/NO/O/ZO/Z/ZW/W/NW).
- Een **woningscheidende wand** (naar de buren) geef je **géén** oriëntatie → die valt automatisch uit de schil.
- Ramen/deuren **erven** de richting van hun muur — die hoef je niet apart te richten.

### 2c. Begrenzing per gevel via de WANDNAAM ⭐ (de truc)
MagicPlan heeft geen apart begrenzing-veld per gevel, dus zet het **in de naam van de muur**:

| In de wandnaam | Betekenis | In VABI (basisopname) |
|---|---|---|
| *(gewone naam)* | Buitenlucht | 0 |
| `... AOR ...` / `... garage ...` | grenst aan onverwarmde ruimte | telt als buiten (0) |
| `... grond ...` / `souterrain` | tegen grond | 2 |
| `... kruipruimte ...` | kruipruimte | 3 |
| `... kelder ...` | onverwarmde kelder | 7 |
| `... AVR ...` / `buurwand` / `buurwoning` | naar verwarmde buur | **valt uit de schil** |

*Voorbeelden:* `Achtergevel AOR garage` · `Kelderwand grond` · `Zijwand buurwand AVR` · `Voorgevel`.

### 2c-bis. Extra naam-tokens (de dropdowns in MagicPlan slaan niet betrouwbaar op → gebruik de NAAM) ⭐
| In de naam van… | Token | Effect in de tool |
|---|---|---|
| een **wand** | `ongeisoleerd` / `niet geisoleerd` | die gevel krijgt isolatie **Nee** (overschrijft de projectdefault) |
| een **wand** | `geisoleerd` / `nageisoleerd` | die gevel krijgt isolatie **Ja** |
| een **wand** | `narekenen` (of `splits` / `deels buiten`) | de gevel wordt **geflagd**: "handmatig narekenen in Vabi" — voor een muur die deels buiten/deels binnen grenst (de tool neemt de héle muur) |
| een **ruimte** | begrenzing-token (`grond`/`kruipruimte`/`kelder`) | dat vloerdeel komt apart in de schil met die begrenzing (rest = projectvloer) |

*Voorbeelden:* `Zijgevel ongeisoleerd` · `Voorgevel narekenen` · `Studeerkamer grond` (vloer op grond i.p.v. kruipruimte).
Zo geldt: **één keer de projectdefault invullen, en alléén bij een afwijkend vlak een token in de naam.**

### 2c-ter. Schuin dak: Ag-aftrek onder 1,5 m
Onder een hellend dak telt het vloeroppervlak waar de netto hoogte **< 1,5 m** is **niet** mee voor de
gebruiksoppervlakte (ISSO 7.2.1). MagicPlan meet op vloerniveau (inclusief die lage strook). Meet die
strook en vul de m² in het form-veld **`Ag-aftrek zolder (m2)`** (kommavrij!) → de tool trekt het van Ag af.

### 2d. Het dak (projectvelden in de form)
- `Type dak`: Zadeldak / Lessenaar / Plat.
- **Óf** `Hellingshoek dak` (graden) invullen, **óf** `Dak vloerbreedte` + `Dak nokhoogte` (+ `Dak knieschothoogte`)
  — de tool rekent de helling dan zelf.
- `Dak orientatie zijde 1/2` (de twee schuine vlakken) + `Kopgevel orientatie 1/2`.
- Moeilijk dak/dakkapel? Voer de vlakken handmatig in (alle oriëntaties + horizontaal).

### 2e. Benoem de ruimtes (voor de ventilatie)
Noem ruimtes herkenbaar: **Woonkamer, Keuken, Slaapkamer 1, Badkamer, Toilet, Bijkeuken** (NL of EN mag).
De tool leidt hieruit de ventilatiebalans af (0,7/verblijfsgebied, afvoer keuken 21 / bad 14 / toilet 7).

### 2f. Vul de projectvelden in ("Schil & zone")
Woningtype · Gevelhoogte (m) · Bouwjaar-klasse · (Renovatiejaar) · Thermische massa wanden + vloeren
(Licht/Zwaar/Zeer zwaar) · Begrenzing (vloer) · `Qv10 gemeten?` (Ja/Nee) · Isolatie aanwezig · Type dak.

### 2f-bis. Vul de installaties in ("Installaties"-form) ⚙️
De form is **conditioneel** (VABI-getrouw): je kiest een type en alléén de relevante vervolgvelden verschijnen.
- **Ventilatie:** systeem (A natuurlijk / C mechanisch afzuig / D balans-WTW …) + subsysteem + systeem (ind./coll.).
- **Verwarming:** opwekker (gasketel / warmtepomp / …) → bij ketel de **HR-klasse**, bij WP **medium/bron**;
  daarna afgiftesysteem + aanvoertemperatuur + bouwjaar toestel.
- **Koeling:** aanwezig? → type (compressie/absorptie/passief) + split.
- **Tapwater:** toestel (combitoestel / warmtepompboiler / …) + bouwjaar.
- **Zonne-energie:** PV aanwezig? → **paneeltype (mono/poly/…)** + **fabricagejaar** + **bouwintegratie** +
  **oriëntatie** + **hellingshoek** + **aantal panelen** + **Wp**; daarnaast zonneboiler en accu.
> De tool zet PV + verwarming-opwekker(gasketel) + tapwater(combi) + ventilatie automatisch door naar VABI.
> Warmtepomp-bron/koeling/biomassa/WKK-detailcodes zijn nog niet geharvest → die flagt de tool (golden rule)
> en vul je in Vabi aan; voor de **Nij Begun-route** volstaat ventilatie + schil.

### 2g. Foto's 📷 — nu IN MagicPlan
De Installaties-form heeft **7 foto-velden**: **vooraanzicht woning** + **huisnummer** (beide verplicht),
gevels/zijkanten, meterkast/installatie-typeplaatjes, kruipruimte/dak, en een vrij detailveld. Maak ze
volgens de Fotowerkwijze; ze reizen mee in de opname (handig voor het BRL-projectdossier en de foto-checklist).

## STAP 3 — Na de opname: de tool draaien 💻
Exporteer in MagicPlan de **Statistics-CSV** (+ Report-PDF). Dan op kantoor:

```
# 1) opname -> dossier
python magicplan/statistics_csv.py --csv "Project Statistics.csv" \
    --straat .. --huisnummer .. --postcode .. --plaats ..

# 2) dossier -> 3 VABI-bibliotheken (de EPA-import)
python vabi/generate_all.py --dossier out/dossier_csv.json

# 3) dossier -> Nij Begun isolatieplan + ventilatie + foto-checklist + validator
python run.py --dossier out/dossier_csv.json
```
Lees de **LET OP / nameten**-meldingen — dat is je "nog te checken"-lijst.

## STAP 4 — In Vabi EPA-W (de rekenkern) 🧮
1. **Nieuw project** → Algemeen: **Objecttype = Woning · Bouwfase = Bestaande bouw · Opname = Basisopname**
   (eerst invullen, anders weigert de objecten-import).
2. Importeer in volgorde: **Constructies → Objecten → Installaties** (uit `out/vabi_import/`). Alle drie
   importeren foutloos (live bewezen in EPA 12.0.1, 23-6); krijg je tóch "Enum mismatch", check dat het
   objecten-sjabloon 12.0.1 is — zie `vabi/refs/grenstaan_mapping.md`.
3. Vul aan/controleer wat de tool flagt (vooral: **woningpositie/infiltratie**, en de **installaties** —
   verwarming-detail/koeling/tapwater/PV vul je hier in tot die kant geharvest is).
4. **Rekenen** → je krijgt het EP/label + de **Standaard-eis** voor deze woning.

## STAP 5 — Registreren in EP-Online (Route A · BRL §4.2.5)
> Alleen de energielabel-route. Route B (Nij Begun) slaat dit over.
1. Registreer **binnen 3 maanden na de opnamedatum** (6 mnd bij seriematige nieuwbouw) — gebeurt vanuit EPA.
2. Gebruik de **juiste software-versie**: bij registratie de meest actuele; bij herlabelen de oorspronkelijke.
3. Uit de registratie blijken **opnemende én registrerende adviseur** met naam + vakbekwaamheidsnummer
   (max. 2; registrerende is eindverantwoordelijk). Alleen registreren **in opdracht** van een opdrachtgever.
4. Let op: de opnamedatum mag bij een herrun/herlabel **niet** stilzwijgend op 'vandaag' worden gezet.

## STAP 5b — Nij Begun isolatieplan afronden 📋 (Route B)
1. De tool heeft het isolatieplan (Word) al gevuld met het **goedkoopste maatregelpakket per vlak** +
   ventilatieberekening + foto-checklist + meerwerk-subposten.
2. Controleer in Vabi of het pakket de **Standaard** haalt (zo niet: pakket uitbreiden).
3. Vul de **bewijslast** aan (foto's, kierdichting, kruipruimtediepte) en meld af.

## STAP 6 — Projectdossier archiveren (Route A · BRL Bijlage 3 / §4.2.7 · ISSO §5.7)
Maak het dossier **compleet, herleidbaar en reproduceerbaar** — een controleur moet elke invoerwaarde naar
bewijs kunnen terugleiden. Bewaar **15 jaar** (back-up buiten OneDrive-sync). In de projectmap horen:
- **Algemeen:** opdrachtgever · doel/bouwfase · basis/detail · opname- + registratiedatum · adviseur(s) + nr.
- **Opname:** opnameformulier/invoerfile · MagicPlan-plattegrond + doorsnede · BAG pand-/VBO-ID.
- **Bewijs (met inhoudsopgave):** overzicht- + detailfoto's (typeplaatjes, isolatiedikte met duimstok,
  installatie-locatie, PV-beschaduwing) · facturen op naam · DoP/BCRG-kwaliteitsverklaringen (merk+type) ·
  per gegeven de **herkomst** (opdrachtgever/derden/eigen waarneming) + **gecontroleerd ter plaatse ja/nee**.
- **Berekening:** Vabi **uitvoerfile + softwareversie** (EPA, bv. 12.0.1) · de 3 VABI-import-XML's ·
  registratiegegevens EP-Online (registratiedatum + registratienummer rapport).
- **Onderbouwing:** schematisering/rekenzone-keuze · forfaitair/inklap-keuzes · afwijkende rekenwaarden.

> **Wat de tool nú levert vs. wat je zelf aanvult:** de tool genereert de opname-invoer + isolatieplan +
> foto-checklist en bewaart per project in `out/projects/<postcode_huisnr>/`. De **bewijsbijlagen-koppeling,
> opdrachtgever-/adviseursplitsing, EPA-softwareversie en de Bijlage-3-volledigheidscheck** doet de adviseur
> nog handmatig — zie `docs/ISSO-BRL-gap-analyse.md` (roadmap) en `docs/BRL-9500W-proceshandleiding.md`.

---

## 🧾 Spiekbriefje — wat de tool AUTOMATISCH doet vs. wat JIJ in Vabi doet
**Automatisch (uit de opname):** gevels per oriëntatie + begrenzing, ramen/deuren (glas/kozijn), dak per
vlak, vloer + perimeter, Ag + bouwlagen, bouwjaar, qv10 (alleen als gemeten), **thermische massa (0/1/2),
Daktype, Gebouwhoogte**, ventilatiesysteem + **ventilatiebalans (Nij Begun-vuistregels)**, verwarming-opwekker,
forfaitaire Rc per bouwjaar.

**Jij in Vabi:** woningpositie/infiltratie bevestigen · installatie-detail (verwarming/koeling/tapwater/PV)
· BCRG-/kwaliteitsverklaringen · exacte Rc/U/g · **Rekenen** (de Standaard). De tool gokt nooit een
VABI-code — alles wat niet zeker is, wordt geflagd.

**Jij in het BRL-proces (alleen Route A):** opname-soort kiezen (1a) · opdrachtgever informeren (1b) ·
registreren EP-Online (5) · projectdossier compleet maken + 15 jaar bewaren (6). Zie de proceshandleiding.
