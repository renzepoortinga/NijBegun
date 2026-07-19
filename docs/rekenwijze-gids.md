# Rekenwijze-gids — hoe de tool élk oppervlak en elke waarde berekent

Voor de adviseur. Dit document beschrijft **exact** wat de tool nu doet: welke bron-kolom uit de
MagicPlan **Statistics-CSV** wordt gelezen, welke formule erop wordt toegepast, en waar het resultaat
in de VABI-import (Objecten-/Constructiebibliotheek) belandt. Inclusief alle benaderingen en flags —
niets is mooier voorgesteld dan het is. Bronnen in de code: `magicplan/statistics_csv.py` (parser),
`core/geometry.py` (dak-/toeslagformules), `vabi/objecten_generate.py` (VABI-geometrie),
`ventilatie/ventilatie.py` (ventilatiebalans), `dashboard/app.py` (webapp-kengetallen).

**Gouden regel:** de tool rekent de NTA 8800 nooit zelf. Alles hieronder is *invoer*-voorbereiding;
Vabi EPA-W is en blijft de rekenkern. Waar de tool benadert, staat dat erbij én wordt het geflagd in
de run-output ("LET OP / nameten").

---

## 1. Buitengevels

### 1.1 Bron en sommatie

| Stap | Bron | Wat er gebeurt |
|---|---|---|
| Wand-m² netto | WALL ATTRIBUTES, kolom **"Surface without openings"** (positioneel kolom 4) per rij met Type=`Wall` | **Binnenwerks** gemeten wandoppervlak, ramen/deuren er al af. Dit is het gevel-m² dat de tool gebruikt — er wordt níét hoogte×lengte gerekend, de scan-waarde is leidend. |
| Wand-m² bruto | Kolom **"Surface"** (kolom 3) | Alleen voor de volledigheidscheck (§1.5), niet voor de schil. |
| Wandnaam | Kolom 1 (wandnaam) + kolom 0 (kamernaam) + de tikbare kolom **"Gevelnaam"** (op naam gezocht in de header) | Alle drie samengevoegd; daarin zoekt de tool de tokens (gevelnaam, begrenzing, isolatie, narekenen, rekenzone, kompas). |
| Sommatie | — | Per unieke sleutel **(oriëntatie, begrenzing, isolatie-override, nareken-vlag, rekenzone)** worden de netto-m² opgeteld tot één gevel-schildeel. Vier voorgevel-wandstukken op het Zuiden met dezelfde begrenzing worden dus één "gevel-voor" van de som. |

### 1.2 Oriëntatie-afleiding (gevelnaam → kompas)

Prioriteitsvolgorde per wand:

1. **Kolom "Oriëntatie (override)"** op het wand-element (op naam gezocht; in legacy-exports was dit
   positioneel kolom 11). Ingevuld = wint altijd.
2. **Kompastoken in de wandnaam** — het *laatste* losse token telt (zodat "Rechtergevel ZW" als ZW
   wordt gelezen en het woord "rechter" zelf niet als richting). Synoniemen (noord→N enz.) worden
   herkend; 8-puntsroos N/NO/O/ZO/Z/ZW/W/NW.
3. **Afgeleid uit gevelnaam + projectveld "Oriëntatie voorgevel"** (PLAN ATTRIBUTES). Conventie
   *vanaf de straat gezien*, in stappen van 45° op de 8-puntsroos:

   | Gevelnaam-token | Rotatie t.o.v. voorgevel |
   |---|---|
   | voorgevel / voorzijde | 0° |
   | rechtergevel / rechter zijgevel | **−90°** |
   | linkergevel / linker zijgevel | **+90°** |
   | achtergevel / achterzijde | **+180°** |

   Voorbeeld: voorgevel = O → rechter = N, linker = Z, achter = W. De run print de vier afgeleide
   oriëntaties als controleregel; corrigeren kan via het projectveld of een kompastoken in de naam.

Een wand **zonder** oriëntatie (geen override-kolom, geen kompastoken, geen gevelnaam of geen
voorgevel-oriëntatie) telt **niet mee**: dat is per definitie een binnenwand. Staat er helemaal geen
buitengevel in het resultaat, dan flagt de tool dit expliciet.

### 1.3 Wat NIET meetelt

- **AVR-/buurwanden** (token `avr`, `buurwand`, `buurwoning`, `woningscheidend`, …): de héle wand
  wordt overgeslagen, **inclusief alle ramen en deuren in die wand** (ISSO: woningscheidende wand is
  geen thermische schil; adiabatisch).
- **Binnenwanden zonder gevelnaam/oriëntatie**: vallen automatisch weg (zie §1.2).
- Ramen/deuren in zo'n wand vallen mee weg omdat ze de oriëntatie van de moederwand erven.

### 1.4 Hart-op-hart-toeslag (woningscheidende wand, ISSO 82.1 §8.2)

MagicPlan meet binnenwerks; ISSO schrijft voor dat je bij een gebouwscheidende wand tot de
**hartmaat** meet. Is de wanddikte niet gemeten, dan geldt +11 cm gevelbreedte per buurwand
(uitgangspunt: 22 cm dikke scheidingswand, halve dikte 0,11 m), voor zowel voor- als achtergevel:

> **toeslag_totaal (m²) = 2 × n_buur × 0,11 × gevelhoogte**

met `n_buur` uit het woningtype: vrijstaand = 0 · hoekwoning/eindwoning/2-onder-1-kap = 1 ·
tussenwoning = 2. Dus: tussenwoning = 0,44 × gevelhoogte; hoekwoning = 0,22 × gevelhoogte.

**De tool past deze toeslag BEWUST NIET automatisch toe** (besluit 19-7): de correcte verdeling over
de juiste gevels is te foutgevoelig om altijd goed te doen. In plaats daarvan geeft de tool één
**luide melding** ("HART-OP-HART GEVEL-TOESLAG — ZELF TOEVOEGEN IN VABI") met de geschatte m², zodat
de adviseur de toeslag zelf op de voor- én achtergevel in VABI zet. Ontbreekt het woningtype, dan
kan de tool de positie niet bepalen en volgt er een aparte flag.

### 1.5 Volledigheidscheck

De tool schat: **verwacht ≈ omtrek × gevelhoogte × (4 − n_buur)/4** (bij tussenwoning telt de helft
van de omtrek als buitengevel). Is de getagde bruto gevel < 60% daarvan, dan volgt de flag "Gevel
mogelijk ONVOLLEDIG" met het aantal getagde buitenmuren — meestal betekent dit dat een buitenmuur
geen gevelnaam/oriëntatie kreeg.

### 1.6 Begrenzing, isolatie, narekenen, rekenzone (per wand)

| Kenmerk | Bron | Regels |
|---|---|---|
| Begrenzing | Token in de wandnaam | AVR (→ weg) · onverwarmde kelder · kruipruimte · grond/talud/souterrain · AOS/serre · sterk geventileerd/ASGR · AOR/garage/onverwarmd · water. Default **Buitenlucht**. Eerste match wint (AVR heeft hoogste prioriteit). Ramen/deuren erven de begrenzing van de moederwand. |
| Isolatie-override | Token in de wandnaam | "ongeïsoleerd"/"niet geïsoleerd" → Nee; "geïsoleerd"/"nageïsoleerd"/"na-isolatie" → Ja; anders projectdefault uit de Constructies-bouwdeelboom ("Gevel - isolatie aanwezig?", met fallback naar de oude platte velden). |
| Narekenen | Naam-token ("narekenen", "splits", "deels buiten", …) óf het vinkje-veld "Deels binnen/deels buiten? (narekenen)" (kolom op naam gezocht) | De tool neemt de **hele** muur mee en flagt: handmatig in Vabi het afwijkende deel corrigeren. |
| Rekenzone | "zone 2" / "rekenzone 3" / "rz2" in de naam | Default 1. Multi-zone wordt geflagd; multi-zone-VABI-geometrie is nog niet geautomatiseerd. |

### 1.7 Waar het in VABI belandt

Elk gevel-schildeel wordt één **Hoofdvlak** in Rekenzone > Geometrie van de Objectenbibliotheek:
`Oppervlakte` = `BrutoOppervlakte` = `NettoOppervlakte` = het gesommeerde gevel-m²;
`Orientatie` via de VABI-enum (**Z=0, ZW=1, W=2, NW=3, N=4, NO=5, O=6, ZO=7**; horizontaal = −1);
`GrenstAan` via de live-geverifieerde enum (0=Buitenlucht, 1=Water, 2=Grond, 3=Kruipruimte, 4=AOR,
5=AOS, 6=ASGR, 7=Onverwarmde kelder, 8=AVR, 9=Ander gebouw). **Let op:** in de *basisopname*
(default) worden AOR/AOS/sterk-geventileerd conform het officiële opnameformulier als **Buitenlucht
(0)** geschreven; alleen bij detailopname krijgen ze code 4/5/6. De constructie-verwijzing
(naam + GUID) komt uit dezelfde matcher als de Constructiebibliotheek, zodat beide bibliotheken
naar identieke constructies wijzen.

---

## 2. Ramen (kozijnen)

| Stap | Bron | Formule / regel |
|---|---|---|
| Oppervlak | WALL ATTRIBUTES rij Type=`Window`, kolom **"Surface"** (kolom 3) | = breedte × hoogte van het venster-element zoals in MagicPlan getekend. Geen eigen berekening. |
| Kleine ruiten | — | **0 < opp < 0,65 m² → gerekend als 0,65 m²** (Nij Begun opname-handleiding). De echte maat blijft in de opmerking staan. |
| Oriëntatie | Kolom "Oriëntatie (override)" (op naam; legacy kolom 17), anders **geërfd van de moederwand** | Geen oriëntatie (ook niet via de wand) → binnenraam → niet in de schil. |
| Begrenzing | Geërfd van de moederwand (parent/child) | Raam in een AOR-gevel grenst dus ook aan AOR. |
| Glastype | Kolom **"Type glas"** (exacte kop-match, zodat "Type glas (indien glas in deur)" niet per ongeluk gepakt wordt; legacy kolom 16) | Ontbreekt het → opmerking "GLASTYPE ONTBREEKT". |
| Kozijnmateriaal | Kolom "Kozijnmateriaal" (legacy kolom 15), kozijntype **A/B/C** van het officiële formulier | A → Hout of kunststof · B → Metaal thermisch onderbroken · C → Metaal niet thermisch onderbroken. Default: Hout of kunststof. |

**Paneel-in-kozijn:** staat het veld "Raam = Ja \| Paneel = Nee" op *paneel*, dan wordt het element
géén glas maar een **dichte constructie** (type paneel), met isolatie/dikte/bouwjaarklasse uit de
paneel-velden (default isolatie *Onbekend* → forfaitair via bouwjaar). De CSV geeft geen Rc voor
panelen; de tool flagt dit — verfijnen in de webapp-opname of in Vabi.

**VABI:** elk raam/paneel wordt een **Deelvlak** (Oppervlakte + RelevanteOppervlakte) geplaatst in
het gevel-Hoofdvlak met **dezelfde oriëntatie**. Bestaat er geen gevel met die oriëntatie, dan wordt
round-robin over de aanwezige gevels verdeeld — controleer bij afwijkende oriëntaties dus de
plaatsing in Vabi.

---

## 3. Deuren

| Stap | Bron | Regel |
|---|---|---|
| Oppervlak | Rij Type=`Door`, kolom "Surface" (kolom 3) | Direct uit de scan. |
| Oriëntatie/begrenzing | Als bij ramen: override-kolom (legacy 17), anders moederwand | Geen oriëntatie én geen "Type constructie (deur)" → binnendeur → weg. |
| ≥65%-glas-vlag | "Type constructie (deur)" (kolom op naam; legacy 18) | Bevat de gekozen optie "65" → VABI-vlag **deur met raam ≥65% glas**. "Deur met raam" zónder 65 = gewone deur met glas < 65% (géén vlag). |
| Glas-in-deur m² | Kolommen "Oppervlakte glas 65…" of "Oppervlakte raam in deur" (op naam; legacy kolom 19), glastype uit "Type glas (65…)"/"Type glas (indien…)" (legacy kolom 20) | Naam-kolommen winnen; positioneel is alleen fallback voor oude exports. |
| Bovenlicht | "Bovenlicht - oppervlak glas" resp. "Bovenlicht-paneel - oppervlak" | Glas-bovenlicht wordt **opgeteld bij het glas-in-deur**; paneel-bovenlicht wordt een **apart paneel-schildeel** (dichte constructie boven de deur) met eigen isolatie-velden. |
| Kozijnmateriaal | vast | Altijd "Hout of kunststof" (geen deur-materiaalveld in de opname). |

VABI-plaatsing: identiek aan ramen (Deelvlak in de gevel met dezelfde oriëntatie, anders round-robin).

### 3b. Dakramen (gecorrigeerd 15-7)

Een dakraam wordt een **kozijn met subtype `Dakraam`** en de oriëntatie van het dakvlak waarin het zit.
In VABI komt het als **Deelvlak op het DAK-hoofdvlak** met dezelfde oriëntatie (niet op een gevel).

**Belangrijk — de aftrek gebeurt precies één keer.** Het dakvlak blijft in het dossier **BRUTO** (net als
een gevel: die is ook bruto, met de ramen als deelvlak erin). De netto-aftrek doet de objecten-generator:
`netto = bruto − Σ deelvlakken`. Tot 15-7 trok de parser het dakraam-glas er *óók* al af, waardoor het
**dubbel** wegviel en het dakvlak te laag in VABI kwam — dat is gefixt (beide dakramen-invoerpaden).

Is er geen dakvlak met die oriëntatie, dan volgt een flag (het dakraam belandt dan mogelijk op een gevel).

---

## 4. Dak — per daktype

Volgorde van beslissen (eerste die raak is, wint):

### 4.1 Direct ingevoerde m² winnen altijd

Elk **"Dakvlak N - oppervlak (m²)"** (N = 1..3, PLAN ATTRIBUTES) met een waarde wordt 1-op-1 een
dakvlak met eigen daktype, oriëntatie, hellingshoek, begrenzing en bouwdeelboom ("Dakvlak N - …").
De geometrie-benadering hieronder wordt dan overgeslagen (geflagd in de run). SOBOLT-principe: de
adviseur weet het beste.

### 4.2 Hellingshoek

- Direct: "Dakvlak 1 - hellingshoek (°)" (of legacy "Hellingshoek dak").
- Anders uit de meetinstructie-maten: **α = atan( (nokhoogte − knieschothoogte) / (vloerbreedte / n_schuine_zijden) )**
  met n = 2 voor een symmetrisch zadeldak (nok in het midden), n = 1 voor een lessenaarsdak.

### 4.3 Formules per daktype (uit `core/geometry.py`)

| Daktype | Formule | Oriëntaties | Benadering / let op |
|---|---|---|---|
| **Zadeldak** | Totaal schuin dak = **footprint / cos(α)**; per schuin vlak de **helft**, op "Dakvlak 1/2 - oriëntatie". Kopgevel-driehoek per stuk = **0,5 × B × (B/2)·tan(α)**, waarbij **B = de OVERSPANNING** (de maat loodrecht op de nok, waarover het dak schuin loopt) — **niet** de noklengte. Vanaf 15-7 leidt de tool die af als `footprint ÷ noklengte`, of je vult 'overspanning (m)' expliciet in. Komt als **extra gevelvlak** op de kopgevel-oriëntaties, en **alleen als die kopgevel aan buiten grenst** (tussenwoning = buurwand → niet meetellen). | o1, o2 (schuin) + k1, k2 (kopgevel) | Geldt voor nok in het midden (symmetrisch). Asymmetrisch dak → m² handmatig per vlak. |
| **Lessenaarsdak** | Eén schuin vlak = **footprint / cos(α)**. | één oriëntatie | De twee zijgevel-driehoeken (trapezium-top) worden **niet** gegenereerd — zo nodig handmatig in Vabi. |
| **Schilddak/tentdak** | Totaal = **footprint / cos(α)**, **gelijk verdeeld** over alle opgegeven oriëntaties (o1, o2, k1, k2). Géén verticale kopgevel-driehoeken. | alle opgegeven zijden | Gelijk verdelen is een benadering; de echte hoofd-/schildvlak-verhouding verfijn je in Vabi (wordt geflagd). |
| **Plat dak** | m² = Dakvlak 1-oppervlak, of legacy "Plat dak m2", of anders **= footprint**. Helling 0. | evt. één (of Horizontaal) | — |
| **Anders/complex** | 9 handmatige m²-vakjes: "Dak m² N/NO/…/NW/Horizontaal". | per vakje | Volledig handmatig. |
| **Fallback** | Geen helling en geen vlakken bekend → **dak-m² = footprint** + luide flag ("HELLINGSHOEK/dakvlakken ONTBREKEN"). | geen | Bij een hellend dak is dit een **onderschatting** (cos-factor mist) — altijd aanvullen. |

`footprint` = de begane-grond-**"Ground surface without walls"** uit FLOOR ATTRIBUTES (verdieping met
"ground/grond/begane" in de naam; anders de grootste niet-kelderverdieping; fallback "Above grade
living area"). Dat de *begane-grond*-footprint als dakprojectie dient, is een benadering die alleen
klopt als de bovenste verdieping dezelfde plattegrond heeft — bij terugliggende verdiepingen zelf
corrigeren.

### 4.4 Dak in VABI

Elk dakvlak wordt een Hoofdvlak met de m² uit bovenstaande formules. **`Hellingshoek` is in de
Objecten-XML een ENUM, geen graden: 3 = "Dak hellend", 6 = "Dak plat".** De gemeten graden dienen
alleen voor de m²-berekening (cos-factor) en blijven in het dossier. Plat/onbekend dak krijgt
Orientatie −1 (horizontaal). Kopgevel-driehoeken uit een zadeldak zijn `kind=gevel` en komen dus als
extra gevel-hoofdvlakken binnen.

---

## 5. Vloer (begane grond)

| Stap | Bron | Regel |
|---|---|---|
| Hoofdvloer-m² | Begane-grond-footprint (zie §4.3), fallback "Above grade living area" | **Niet** de meerlaagse som. Opmerking in het schildeel: "opp = begane-grond-footprint (benadering); verifieer in Vabi". |
| Begrenzing | "Vloer - begrenzing" (bouwdeelboom) of legacy "Begrenzing (vloer)" | Default **Kruipruimte**. |
| Afwijkende vloerdelen | **Ruimtenaam-tokens** in ROOM ATTRIBUTES (bv. "Bijkeuken grond", "Slaapkamer AOR") | Per afwijkende begrenzing wordt de kamer-m² van de hoofdvloer **afgetrokken** en als apart vloerdeel gezet (hoofdvloer = footprint − Σ splits). Room-based → m²-verdeling in Vabi controleren (geflagd). |
| Perimeter | PLAN "Exterior perimeter" | Volledige buitenomtrek. |
| **Perimeter-guard** | — | In VABI wordt de perimeter (randverlies, `Perimeter` + `AutoPerimeter=0`) **alleen** gezet op vloer-hoofdvlakken met begrenzing **grond/kruipruimte/kelder** (ISSO 8.3). Andere begrenzingen: geen perimeter. |
| Buurwand-correctie | — | Bij hoek-/tussenwoning flagt de tool: de woningscheidende wand(en) tellen **niet** mee in de vloer-perimeter (opname-handleiding §3.4) — de tool schrijft toch de volle omtrek; **handmatig corrigeren in Vabi**. |

VABI: vloer-hoofdvlak met Orientatie −1, GrenstAan volgens §1.7.

---

## 6. Ag, verliesoppervlak en compactheid (webapp)

| Kengetal | Formule | Bron / bestemming |
|---|---|---|
| **Ag** | "Total living area" (PLAN); ontbreekt die → Σ kamer-m² uit ROOM ATTRIBUTES. Daarna **minus "Ag-aftrek zolder (m2)"** (vloer onder schuin dak met netto hoogte < 1,5 m, ISSO 7.2.1 — MagicPlan meet op vloerniveau inclusief de lage strook, dus de adviseur vult de aftrek zelf in het formveld). | Naar VABI **niet** via Rekenzone>Algemeen>`Gebruiksoppervlakte` (dat is daar een enum/vlag, geen m² — live bewezen "Enum mismatch"), maar via **Verdiepingen**: n_lagen = aantal verdiepingen met Ceiling Height, per verdieping Ag/n_lagen (totaal exact), plus `AantalBouwlagenRekenzone`. |
| **Verliesoppervlak** (webapp-indicatie) | **Σ oppervlakte van álle schildelen met begrenzing ≠ AVR** (gevels + dak + vloer + ramen + deuren + panelen). | Alleen ter indicatie op de Opname- en VABI-toets-pagina. Let op: dit is de *dossier*-som; de **officiële** Verliesoppervlakte/Compactheid komt uit de VABI-export terug (result_reader). In de basisopname tellen ook AOR/AOS/ASGR-vlakken hier gewoon mee (ze zitten in de schil als buitenlucht). |
| **Compactheid** | **verliesoppervlak / Ag** | Idem: webapp-indicatie; VABI's eigen Compactheid is leidend. |

---

## 7. Verdiepingshoogte en gebouwhoogte

- **Wandhoogte zit impliciet in de wand-m²**: de per-wand "Surface (without openings)" komt
  rechtstreeks uit de scan (gescande wandhoogte × lengte). De tool vermenigvuldigt zelf nergens
  hoogte × lengte voor gevels — de scan is de maat.
- **Gevelhoogte/gebouwhoogte** (nodig voor de hart-op-hart-toeslag, de volledigheidscheck en het
  VABI-veld `Gebouwhoogte`): prioriteit (1) CLI-argument, (2) formveld "Gevelhoogte (m)",
  (3) **som van de "Ceiling Height"-waarden per verdieping** (FLOOR ATTRIBUTES). Die som is een
  benadering: vloer-/verdiepingsdiktes zitten er niet in. Meet je de gevelhoogte buiten na, vul dan
  het formveld — dat wint.
- De per-verdieping Ceiling Height wordt verder alleen gebruikt als **controle-informatie**
  (VloerInfo in het dossier) en om het **aantal bouwlagen** voor de Ag-verdeling te bepalen (§6);
  hij bepaalt géén gevel-m².

---

## 8. Ventilatieberekening (kort)

Nij Begun-vuistregels (BBL-gebaseerd, bindend), op de kamers uit ROOM ATTRIBUTES; functie wordt uit
de ruimtenaam geclassificeerd (keuken/badkamer/toilet/wasruimte/verkeer/slaapkamer/verblijfsruimte):

- **Toevoer** per verblijfsgebied (woon-/slaap-/studeerkamer + keuken): **0,7 dm³/s·m²**, met een
  minimum van **7 l/s per leefruimte**. (0,9 is alleen de nieuwbouw-variant, niet Nij Begun.)
- **Afvoer** natte ruimten (vaste minima): keuken **21**, badkamer **14**, toilet **7**, wasruimte
  **14** dm³/s.
- **Maatgevend debiet = max(Σ toevoer, Σ afvoer)** (balans); overstroom = min van beide.
- Waarschuwingen: afvoerpunt in een slaapkamer (verboden), onbalans > 0,5 dm³/s. De checklist met de
  7 bindende vuistregels (max 2 deuren overstroom, ≥50% van buiten, deurrooster bij >15 l/s,
  afstand tot rookkanaal, C4c-CO₂-sturing) staat in het rapport.

---

## 9. Overige waarden die meegaan naar VABI

| Waarde | Bron | Regel |
|---|---|---|
| Bouwjaar | Eerste jaartal uit de bouwjaarklasse ("1992 t/m 2013" → 1992) | Rekenzone>Algemeen>Bouwjaar. |
| Renovatiejaar | Formveld; alleen bij aantoonbare maatregel (ISSO 7.1.4) | Rekenzone>Algemeen>Renovatiejaar. |
| qv;10 | "Qv10-waarde" + "Qv10 gemeten?" | Alleen geschreven als **gemeten** (blowerdoor, ISSO 7.1.5); anders genegeerd + flag → VABI rekent forfaitair op bouwjaar/renovatiejaar. |
| Thermische massa | "Gevel/Vloer - thermische massa" | TypeBouwwijzeWanden/-Vloeren: Licht=0, Zwaar=1, Zeer zwaar=2 (live geverifieerd). Onbekende klasse → flag. |
| Daktype (gebouwniveau) | "Type dak" | 0=Hellend, 1=Deels plat, 2=Plat (live geverifieerd); niet herkend → sjabloon-default + flag. |
| Woningtype/Ligging | formveld | Enum-code nog **niet** bevestigd → sjabloon-default + flag; woningpositie handmatig in Vabi zetten. |
| Rc-bron "Kwaliteitsverklaring" | Bouwdeelboom "… - invoer" | De tool kiest een forfaitaire constructie en **flagt**: zet Invoer=Kwaliteitsverklaring + de Rc/U-waarde zelf in VABI (golden rule: niet gokken). |
| Extra installaties / 2e ventilatiesysteem | "Verwarming 2 - …", "Ventilatie 2 - …" | Exemplaar 1 gaat volledig door; extra's worden geflagd en handmatig in Vabi toegevoegd. Meerdere PV-systemen (PV-2…PV-5) gaan wél allemaal mee. |

---

## 10. Samenvattend: waar je als adviseur altijd op controleert

1. De **afgeleide gevel-oriëntaties** in de run-output (voor/rechts/achter/links).
2. De **hart-op-hart-toeslag** zelf op voor+achtergevel toevoegen (de tool doet dit NIET automatisch — zie §1.4).
3. **Vloer-perimeter** bij hoek-/tussenwoning (buurwand eruit halen) en de m²-verdeling bij room-based vloersplits.
4. **Dak**: schilddak-verdeling, lessenaars-zijgeveldriehoeken, footprint-fallback-flags, terugliggende verdiepingen.
5. **Deelvlak-plaatsing** van ramen/deuren zonder gevel op dezelfde oriëntatie (round-robin).
6. Alle regels onder **"LET OP / nameten"** in de run-output — elke benadering hierboven produceert daar een flag.