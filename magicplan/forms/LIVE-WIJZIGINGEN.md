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
- **Element-override**: "Gevel per wand" (All Walls) + "Vloer" (All Floors) dragen **exact dezelfde boom** (+ wand: oriëntatie-
  override; +rekenzone; +vloer: telt-mee-voor-Ag). Leeg = neem form-standaard; invullen = overrule per stuk.
- "Gevel - project" (oude plan-groep) **leeggemaakt** (overbodig; Constructies-form dekt gevel-standaard).
- Bouwjaar-klassen exact: Tot 1965 · 1965–74 · 1975–82 · 1983–87 · 1988–91 · 1992–2013 · 2014 · 2015–17 ·
  2018–20 (1 jan/Overig) · 2021 (1 jan/Overig).

## Object / Installaties (eerder deze sessie)
Aanvoertemp 80/60+90/70; foto vooraanzicht+huisnummer → Object; spouwdikte-dak weg; PV-kwaliteitsverklaring; multi-PV
(PV-2); hybride (Verwarming 2); dak m²-override (zijde 1/2). Rekenzone per installatie + 7 foto's stonden al.

## TODO parser (tool-side, blokkeert opname-INVOER niet, wel de export naar VABI-libs)
`magicplan/statistics_csv.py` moet de **nieuwe boom-veldnamen** lezen i.p.v. de oude platte velden:
- per bouwdeel: `<Gevel|Vloer|Dak> - invoer` (Kwaliteitsverklaring→flag; Beslisschema), `- isolatie aanwezig?`
  (Ja/Nee/Onbekend), `- isolatiedikte onbekend?`, `- bouwjaar` / `- bouwjaar (onbekend)`, `- isolatiedikte (mm)`,
  `- spouw aanwezig?` (gevel), `- thermische massa`, `- begrenzing`.
- DAK: `Dakvlak 1/2/3 - daktype/oriëntatie/oppervlak/hellingshoek/begrenzing` + isolatie-boom; `Dak m² <ori>` (9 vakjes).
- Element-overrides (wand/vloer) met dezelfde namen → per-element overrule.
Daarna: end-to-end test (synthetische CSV → dossier → generate_all) + regressietests groen.
