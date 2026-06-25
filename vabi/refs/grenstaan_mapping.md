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
- **Gebouwtype/Ligging** (woningpositie vrijstaand/2¹kap/hoek/tussen → infiltratie): enumcodes nog te
  verifiëren; generator flagt het en de adviseur zet de woningpositie in Vabi.
- Installatie-enums (verwarming/koeling/tapwater/PV) + PV-sjabloonknoop: aparte EPA-export-harvest nodig.
