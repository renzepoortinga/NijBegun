# MagicPlan live forms — stand 25-6-2026 (via custom-forms/-fields API, geverifieerd)

Forms: **Object · Constructies · Installaties** + element-field-groepen **Gevel per wand · Vloer · Raam/paneel · Deur**
(workspace R.poortinga). Save/publish-roundtrip live bewezen. Backup: `magicplan_*_backup.json` (eerdere sessie) +
in-sessie `window.__BK_FORMS__/__BK_FIELDS__`. Geldige dataTypes: **list/number/image/bool** (GEEN vrije tekst →
Bron/Opmerkingen niet mogelijk in een custom-form). Section-node = minimaal `{id,name,type:'section',children,comparisonValue}`.

## Constructies = VABI-beslisboom (FORM = standaard, ELEMENT = override) — KERN
Per bouwdeel (GEVEL / VLOER / DAK) identiek opgebouwd, 1-op-1 als VABI EPA:
```
Invoer:  ① Kwaliteitsverklaring → 📷 Foto factuur (verplicht op form-niveau)
         ② Beslisschema → Isolatie aanwezig?
              ├ Ja      → Isolatiedikte onbekend?  ├ Ja → Bouwjaar (12 VABI-klassen)
              │                                     └ Nee → Isolatiedikte (mm) [+ Spouw? bij <40mm, alleen GEVEL]
              ├ Nee     → Spouw aanwezig? (alleen GEVEL)
              └ Onbekend→ Bouwjaar
+ Thermische massa (Licht/Zwaar/Zeer zwaar) + Begrenzing (Buitenlucht/Grond/Kruipruimte/AOR/AOS/AVR)
```
- **GEVEL** = met spouw-tak. **VLOER** = zonder spouw. **DAK** = per dakvlak (Dakvlak 1 + "Tweede/Derde dakvlak aanwezig?")
  elk met daktype·oriëntatie·m²·hellingshoek + dezelfde isolatie-boom + begrenzing; + **9 m²-vakjes** (N..NW + Horizontaal)
  als fallback bij type "Anders".
- **Element-override**: "Gevel per wand" (All Walls) + "Vloer" (**All Rooms = PER KAMER**, context 'room') dragen **exact dezelfde
  boom** (+ wand: oriëntatie-override; +rekenzone; +vloer: telt-mee-voor-Ag). Leeg = neem form-standaard; invullen = overrule per stuk.
  Vloer-override hangt nu per KAMER (living room→kelder, bedroom→AOS), niet meer op verdieping-niveau.
- **Rekenzone overal default 1**: MagicPlan kent geen veld-default → parser `_rz()` vult leeg → 1 (alleen invoeren bij overrulen).
- **2e ventilatie + 2e tapwater**: conditionele blokken ("Tweede ventilatiesysteem?" / "Tweede tapwaterinstallatie?") naast 2e verwarming.
  Parser leest 2e tapwater (tapwater_extra) + flagt 2e ventilatie (golden rule). Tests #37–#39, 246/246 groen.
- **Raam/paneel + Deur opgeschoond** (26-6): waren vol cruft (dubbele Type glas/Toevoerrooster + leftover wand-velden). Nu schoon:
  Raam = Type glas (Enkel/Voorzetglas/Dubbel/HR/HR+/HR++/TripleHR/Vacuümglas/Onbekend) · Kozijnmateriaal (hout-kunststof / metaal TO / metaal niet-TO) ·
  Toevoerrooster aanwezig?→type · Begrenzing-override · Raam/paneel-toggle. Deur = Type constructie · Type glas · Oppervlakte raam-in-deur · Kozijnmateriaal · Begrenzing.
  **Verwijderd** (hoorde niet bij glas): isolatiedikte, Rc-bron, oriëntatie, bron, spouw. Oriëntatie + begrenzing erft een raam/deur van de moederwand (parser parent/child).
  TODO generator-check: vabi/constructie_generate glas-enum-mapping voor HR+/HR++/TripleHR/Vacuümglas verifiëren (bij CSV-kalibratie).
- "Gevel - project" (oude plan-groep) **leeggemaakt** (overbodig; Constructies-form dekt gevel-standaard).
- Bouwjaar-klassen exact: Tot 1965 · 1965–74 · 1975–82 · 1983–87 · 1988–91 · 1992–2013 · 2014 · 2015–17 ·
  2018–20 (1 jan/Overig) · 2021 (1 jan/Overig).

## Object / Installaties
Aanvoertemp 80/60+90/70; foto vooraanzicht+huisnummer → Object; spouwdikte-dak weg; PV-kwaliteitsverklaring; multi-PV (PV-2).
**Installaties VABI-getrouw (laatste ronde):**
- **Ventilatie-subsysteem conditioneel per type A–E** (VABI-labels uit refs: A1/A2a-c+onbekend, B1-3, C1..C5b, D1..D5c, E1;
  Type WTW conditioneel bij D/E). Oude platte "Subsysteem (zie type)" verwijderd.
- **Rekenzone inline** bij elke installatie (ventilatie/verwarming/koeling/tapwater/PV); losse REKENZONE-sectie weg; leeg = zone 1.
- **"Tweede verwarmingsinstallatie? (2e ketel / hybride)"** (hernoemd van hybride) → 2e volledige verwarming (2 CV-ketels of WP+ketel).

## Dak geconsolideerd naar Constructies (Optie A)
Alle dak-velden uit **Object** verwijderd (Object houdt: oriëntatie voorgevel, Qv10, renovatiejaar, woningtype,
gevelhoogte, Ag-aftrek zolder, 2 foto's). **Constructies → DAK** heeft nu bovenin een geometrie-blok
(Dak - vloerbreedte / nokhoogte / knieschothoogte / kopgevel oriëntatie 1+2) → standaard daktype = tool rekent
m² + kopgevel-driehoek vóór; type "Anders" = de 9 m²-vakjes. Per dakvlak: type/oriëntatie/m²/hellingshoek + isolatie-boom + begrenzing.

## Parser-stand (magicplan/statistics_csv.py) — GEWIRED + getest (243/243)
- Leest per bouwdeel de **VABI-beslisboom**: `<Gevel|Vloer|Dakvlak 1> - invoer` (KV→flag / Beslisschema) → isolatie
  aanwezig (Ja/Nee/Onbekend) → isolatiedikte onbekend?/bouwjaar/dikte (mm)/spouw → begrenzing → rc_bron/isolatie/dikte op SchilDeel.
- **DAK** uit Constructies: `Dakvlak 1 - daktype/hellingshoek/oriëntatie` + `Dak - vloerbreedte/kopgevel oriëntatie 1/2`
  → zadeldak/lessenaar/schild (auto-m² + kopgevel-driehoek); type Anders → `Dak m² <N..NW/Horizontaal>` (9 vakjes); plat → dakvlak.
- **Ventilatie subsysteem** conditioneel: leest `Subsysteem (A..E)` (whichever gevuld). **Rekenzone inline** per installatie.
- Alles met **fallback naar de oude platte velden** (oudere CSV's blijven werken). Tests #37/#38.

## RESTERENDE kalibratie — alleen op de eerste ECHTE Statistics-CSV
De **element-overrides** (per-wand/vloer invoer-boom: `Gevel/Vloer - invoer/isolatie aanwezig?/...`) exporteren als
WALL/FLOOR-attribuutkolommen; die kolomnamen/-posities ken ik pas uit een echte export. De parser leest de per-wand
override nu nog via de naamconventie + positionele kolommen — dat verfijn ik 1-op-1 zodra Renze één CSV exporteert,
plus de exacte project-veld-kolomnamen (MagicPlan kan ze net iets anders schrijven dan de form-labels).
