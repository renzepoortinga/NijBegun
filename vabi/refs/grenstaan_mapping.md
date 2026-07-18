# VABI Objecten-enumcodes — LIVE GEVERIFIEERD in EPA 12.0.1 (22-6-2026)

Geverifieerd door `out/probe_objecten.xml` (bekende integers in de vlaknamen "PROBE GA=n" +
TypeBouwwijzeWanden=0/Vloeren=2) te importeren in EPA en de labels af te lezen. Conclusie: de
**EPA-dropdownvolgorde = de integercode**. Onderstaande mappings worden door de generator automatisch
geschreven (golden rule: alleen bevestigde codes).

## GrenstAan (begrenzing per vlak)
Dropdown-volgorde "Grens aan (vloer)" = index = code:
| Code | Begrenzing | Bron |
|---|---|---|
| 0 | Buitenlucht | probe ✅ |
| 1 | Water | dropdown-volgorde (zeldzaam; niet in 14 exports) |
| 2 | Grond | probe ✅ |
| 3 | Kruipruimte | probe ✅ |
| 4 | Aangrenzende onverwarmde ruimte (AOR) | probe ✅ |
| 5 | Aangrenzende onverwarmde serre (AOS) | probe ✅ |
| 6 | Aangrenzend sterk geventileerde ruimte (ASGR) | probe ✅ |
| 7 | Aangrenzende onverwarmde kelder | dropdown-volgorde |
| 8 | Aangrenzende verwarmde ruimte (AVR) | dropdown-volgorde |
| 9 | Ander gebouw | dropdown-volgorde |

**Basisopname-regel** (officieel NTA8800-opnameformulier p.4 + ISSO §6.3.4): AOR/AOS/ASGR tellen als
**Buitenlucht (0)**. In de detailopname krijgen ze hun eigen code 4/5/6. AVR (8) is adiabatisch en wordt
in de parser meestal al uit de schil gefilterd (woningscheidende wand → geen oriëntatie of naam-tag "AVR").
Wiring: `vabi/objecten_generate.py` (`GRENST_AAN_CODE` + `_DETAIL_CODE` + `_grenst_aan_code(begrenzing, basis)`).

## TypeBouwwijzeWanden / TypeBouwwijzeVloeren (thermische massa) — Rekenzone>Algemeen
| Code | Klasse | Bron |
|---|---|---|
| 0 | Licht (hsb/sfb/binnenzijde geïsoleerd) | probe ✅ (wanden=0 → "Licht") |
| 1 | Zwaar (dragend metselwerk / staal-beton-vloer) | eerder bevestigd |
| 2 | Zeer zwaar (massieve beton) | probe ✅ (vloeren=2 → "Zeer zwaar") |

## Daktype — Object>Algemeen (Classificatie)
| Code | Daktype | Bron |
|---|---|---|
| 0 | Hellend dak / puntdak | probe ✅ (template=0 → "Hellend dak") |
| 1 | Deels plat dak (gedeeltelijk plat) | dropdown-volgorde |
| 2 | Plat dak / zonder kap | dropdown-volgorde |

## Orientatie (Geometrie hoofdvlak) — LIVE GEVERIFIEERD in EPA 12.0.1 (18-7-2026)
Geometrie-export van het voorbeeldproject 'hoekwoning': Gevel Zuid->0, Noord->4, Oost->6 (+ Dak
Noord=4, Zuid=0, Vloer=-1). De EPA "Orientatie voorgevel"-dropdownVOLGORDE (Zuid,ZW,W,NW,N,NO,O,ZO)
== de integercode, op 3 punten (0/4/6) rechtstreeks tegen de export gematcht -> hele kompasrotatie
vanaf Zuid bevestigd:
| Code | Orientatie | Code | Orientatie |
|---|---|---|---|
| 0 | Zuid (Z)        | 4 | Noord (N)       |
| 1 | Zuid-West (ZW)  | 5 | Noord-Oost (NO) |
| 2 | West (W)        | 6 | Oost (O)        |
| 3 | Noord-West (NW) | 7 | Zuid-Oost (ZO)  |
Vloer/plat = -1. **LET OP:** dit is ANDERS dan de PV-orientatie-enum (0=N..7=NW; installatie_enums_EPA.md).
Wiring: `vabi/objecten_generate.py` `ORIENTATIE_CODE`. De oriëntatie-flag (audit F1, Z/W/O) is VERVALLEN.

## Gebouwtype / Subtype (woningpositie) / Ligging — Object>Algemeen>Classificatie (LIVE 18-7-2026)
Bevestigd via de Objecten-export (hoekwoning: Gebouwtype=0, Subtype=1) + de monitor-fixture
(tussenwoning: Gebouwtype=0, Subtype=2). Dropdown-index = code.
- **Gebouwtype** (0-9): 0=Eengezinswoning · 1=Woning in een appartementencomplex · 2=Appartementencomplex
  met zelfstandige wooneenheden · 3=idem niet-zelfstandige · 4=Vakantiewoning (niet in woongebouw) ·
  5=Woonboot bestaande ligplaats tot 1-1-2018 · 6=Woonboot nieuwe ligplaats vanaf 1-1-2018 · 7=Woonwagen
  · 8=Eengezinswoning met niet-zelfstandige wooneenheden · 9=Woning in appartementencomplex met
  niet-zelfstandige wooneenheden.
- **Subtype = WONINGPOSITIE** (grondgebonden): 0=Vrijstaand · 1=Kop-/eind-/hoekligging · 2=Tussenligging
  · 3=Twee onder een kap.
- **Ligging**: appartement-only (Onderste/…/Bovenste verdieping); bij een eengezinswoning nvt (sjabloon).
Wiring: `vabi/objecten_generate.py` (`_subtype_code` + Gebouwtype 0). **LIVE RE-IMPORT bewezen (18-7):** een
gegenereerde objecten-lib (Hoekwoning) importeert FOUTLOOS in EPA 12.0.1 -> "Eengezinswoning /
Kop-/eind- of hoekligging". De Gebouwtype/Ligging-flag is hiermee VERVALLEN (alleen nog een flag bij
meergezins/onbekende positie).

## Objecten-import valkuilen — LIVE GEDIAGNOSTICEERD 23-6-2026 (bisectie in EPA 12.0.1)
Drie oorzaken van "Enum mismatch" bij objecten-import, één voor één empirisch geïsoleerd (clean template
importeert → transformaties één voor één toegevoegd tot het brak):

1. **`<Gebruiksoppervlakte>` in Rekenzone>Algemeen is GEEN m²-veld maar een ENUM/vlag.** Echte export = "1"
   (ook bij een 185 m²-woning). De generator overschreef dit met de gemeten m² (120) → **"Enum mismatch"**.
   FIX: dit veld NIET zetten (sjabloon-default "1" behouden). De Ag dragen we via de **Verdiepingen-som**
   (per-laag `<Gebruiksoppervlakte>` = ECHTE area, sjabloon ~28,86) + de vloer-hoofdvlakken in de geometrie.
   `AantalBouwlagenRekenzone` + Verdiepingen-rebuild (3→2) zijn wél vrij en werken (live bevestigd).
2. **Versie-consistentie sjabloon.** Het objecten-sjabloon was geëxporteerd uit EPA **12.0.0** (XmlVersie
   120000061) terwijl de constructie-sjabloon 12.0.1 is. Het 12.0.0-sjabloon importeert op zichzelf prima
   (EPA upgradet), maar voor consistentie is `objecten_template.xml` nu een **verse 12.0.1-export**
   (XmlVersie 120001001; bron-kopie: `vabi/refs/objecten_template_v1201_source.xml`, oude: `*_v1200.xml.bak`).
   Regressietest in run_tests.py bewaakt XmlVersie==120001001.
3. **Constructie-GUIDs deterministisch** (uuid5 op naam, niet random uuid4): de objecten verwijzen naar
   exact dezelfde constructie-guids als de Constructiebibliotheek → geen dangling refs. (Was al gefixt; nu
   ook live geverifieerd: constructie- én objecten-import beide foutloos.)

EINDRESULTAAT (live): Constructie- én volledige Objectenbibliotheek importeren **foutloos** in EPA 12.0.1.

**TypeBouwwijzeVloeren=0 (Licht)**: nu OOK direct bevestigd (H1-test: clean template + vloeren=0 → import OK,
TO-juli steeg zoals verwacht). Eerder alleen via wanden-probe geïnfereerd; nu rechtstreeks gevalideerd.

## Nog open (niet uit deze probe)
- **Gebouwtype/Ligging + Orientatie: BEVESTIGD 18-7** (zie de twee secties hierboven) — flags vervallen.
- Installatie-enums: het meeste is nu bevestigd (zie installatie_enums_EPA.md, 18-7). Resterend: de
  ventilatie-SUBSYSTEEM-codes zijn GLOBAAL (D5a=33 bevestigd) → per gekozen subsysteem via een export te
  bevestigen; dit blijft een bewuste adviseurskeuze in Vabi (flag). Biomassa/WKK + WP-bron overige codes.
