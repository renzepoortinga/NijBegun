# BUILD_LOG — tool/  (autonome bouwsessie, nacht 7 juni 2026)

Gebouwd en **offline getest** tegen je échte voorbeeldbestanden. De energie­berekening
doet de pijplijn nooit zelf — dat blijft Vabi EPA-W (zie Blueprint §2/§9.1).

## Wat werkt (getest ✓)
| Bouwsteen | Bestand | Status |
|---|---|---|
| Canoniek datamodel | `core/dossier.py` (+ `core/canonical_schema.json`) | ✓ round-trip getest |
| Catalogus-parser | `catalog/parse_maatregelencatalogus.py` → `catalog/catalog.json` | ✓ 333 maatregelen + 12 Rc-tabellen |
| Beprijzing | `catalog/price_dossier.py` | ✓ spouw €23,09/m², vloer €45,10, dak €124,82 |
| Isolatieplan-invuller | `isolatieplan/fill_template.py` → `out/isolatieplan_Essenhage32.docx` | ✓ Gegevens + Onderdeel A/C/D + totaal €11.136,67 |
| VABI monitor-parser | `vabi/monitor_xml.py` → `out/dossier_from_monitor.json` | ✓ Standaard 64,0 kWh/m²·jr, label B, 25 schildelen, round-trip ok |
| KWACO-validator | `validator/validate.py` | ✓ sample=SLUITEND(1 waarsch.), incompleet=5 blok+27 waarsch. |
| MagicPlan CSV-parser | `magicplan/parse_statistics_csv.py` → `out/dossier_from_csv.json` | ✓ Ag 56,31 m², 4 ramen |
| MagicPlan API-client | `magicplan/extractor.py` | ⏳ skeleton, klaar om door jou LIVE te draaien |

## Hoe draaien (lokaal, in `tool/`)
```bash
pip install python-docx lxml openpyxl
python3 core/dossier.py                                   # genereer sample_dossier.json
python3 catalog/parse_maatregelencatalogus.py "../Maatregelencatalogus-...xlsx"
python3 catalog/price_dossier.py                          # → sample_dossier_priced.json
python3 isolatieplan/fill_template.py --template "../Nij Begun_isolatieplan template 23-04-2026.docx" \
        --dossier sample_dossier_priced.json --out out/isolatieplan_Essenhage32.docx
python3 vabi/monitor_xml.py --xml "../9501TP-32-- (monitor).xml"   # VABI → dossier (incl. Standaard)
python3 validator/validate.py --dossier sample_dossier_priced.json
# LIVE (jij, met .env): python3 magicplan/extractor.py --project-id <ID>
```

## De volledige lus
MagicPlan (API) → `dossier.json` → **jij rekent in Vabi EPA-W** → exporteer monitoringbestand →
`monitor_xml.py` leest Standaard + warmteverlies terug → `price_dossier.py` (catalogusprijzen) →
`fill_template.py` (isolatieplan PDF/Word) → `validate.py` (poortwachter) → indienen.

## Bekende beperkingen / TODO (volgende iteraties)
1. **MagicPlan API-mapping (`extractor.py`) 1× verifiëren** tegen een echt project: draai
   `--project-id <ID>`, bekijk `out/plan_raw.json`, vul de echte JSON-sleutels in
   `map_plan_to_dossier()` + bevestig de auth-header (Bearer vs X-API-Key).
2. **Monitor-parser: glas-U via GUID-referenties.** Ramen krijgen nu U=None omdat U/G in
   aparte `<Constructie>`-definities staan (referentie via Guid). v0.2: refs resolven.
   Ook ramen als type 'kozijn' i.p.v. 'gevel' classificeren.
3. **Monitor-GENERATOR** (canoniek → importeerbaar monitoringbestand) vergt de officiële XSD
   (schemas.ep-online.nl/monitoringbestand) + import-test in jouw EPA-W. Nu alleen parser + round-trip.
4. **Maatregel-engine** (kies goedkoopste pakket → Standaard) nog te bouwen; nu beprijzen we
   reeds-gekozen maatregelen. Catalogus-API (leveranciers@nijbegun.nl) als bron i.p.v. xlsx-parse.
5. **Template-invuller**: V2 glas/V3 vloer/V4 dak "huidige staat" (T4/T5) en prijsopbouw (T7-9)
   nog niet gevuld; voorblad-tekstvakken (drawing-XML) worden nog niet vervangen.

## Schema v0.2 — opnameregels om in MagicPlan-forms toe te voegen (uit "Handleiding woningopname")
- **Veldkit-checklist**: afstandsmeter (Leica DISTO), fietsspaak/breinaald (spouwdiepte),
  boormachine (spouw boren), aansteker (HR-coating test), endoscoop, rolmaat, zaklamp.
- **Glas**: herken via code/U in glaslat óf aanstekertest (coating = HR). Ruit < 0,65 m² →
  altijd rekenen als 0,65 m². Deur >65% glas → geheel als raam opnemen.
- **Zolder/dak**: meet gordingdikte (= max isolatiedikte); meet bestaande isolatie (zo nodig
  destructief); noteer niet-beloopbare delen + dakramen.
- **Kruipruimte**: < 35 cm → vloerisolatie meestal niet mogelijk (al in validator verwerkt);
  kruipluik-afmetingen/toegankelijkheid.
- **Perimeter**: omtrek vloer binnen thermische schil; woningscheidende wand telt niet mee.
- **Ventilatie**: type (A1 natuurlijk…), (ZR-)roosters, afzuigpunten keuken/bad/toilet,
  benodigde meters koofwerk (cat. 2-kosten).
- **Thermische schil**: check of aanbouw/bijkeuken/garage binnen of buiten de schil valt.

## ⚠️ Belangrijk — OneDrive corrumpeerde codebestanden
Tijdens het bouwen werden .py-bestanden die in de OneDrive-map werden weggeschreven door
sync/een linter **afgekapt of met null-bytes gevuld**. Daarom is alles gebouwd en getest in
een aparte werkmap en daarna hierheen gekopieerd. **Advies voor het verder bouwen:**
- Bewerk de code in een **niet-gesynchroniseerde map** (bv. `C:\dev\nijbegun-tool`), of pauzeer
  OneDrive-sync tijdens het bewerken; of werk via **Claude Code** lokaal (git = versiebeheer +
  audit-trail, precies wat je later voor tool-validatie wilt).
- Verifieer na elke save: `python -c "import ast,glob; [ast.parse(open(f,encoding='utf-8').read()) for f in glob.glob('**/*.py',recursive=True)]"`.

## Next iteration (voorstel)
A) MagicPlan API-mapping verifiëren tegen 1 echt project → `extractor.py` afmaken.
B) Maatregel-engine (laagste kosten → Standaard) met catalogus-API.
C) Monitor-generator met XSD + import-test in EPA-W.

---
## Update (8 juni 2026, nacht-3) — testsuite + template compleet
- **tests/run_tests.py**: 24 automatische tests over de hele keten (core, catalogus, monitor-parser,
  engine, ventilatie, invullen incl. huidige staat, validator, orchestrator end-to-end). Alles groen.
  Monitor-fixture gebundeld in tests/fixtures/ -> tests zijn draagbaar (ook voor andere gebruikers).
- **Prijsopbouw (template T7-T9)** wordt nu gevuld (maatregel + categorie 1 + subtotaal per blok).
- Draai de tests na elke wijziging:  python tests/run_tests.py
- Resterende grote TODO: VABI monitoringbestand-GENERATOR (dossier -> importeerbare XML) voor de
  MagicPlan->VABI-richting; daarna prijsopbouw voor >3 maatregelen (blok clonen) en live catalogus-API.
