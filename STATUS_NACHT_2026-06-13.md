# Nachtbouw 12→13 juni 2026 — wat er staat, waar we heen gaan

## 🎯 De grote doorbraak
**Alle 3 VABI-bibliotheken genereren uit een MagicPlan-dossier en importeren FOUTLOOS in EPA 12.0.1**
(live getest met jouw Oosterkade-opname): Constructies (5) + Objecten (geometrie) + Installaties.
Eén commando:
```
python vabi/generate_all.py --dossier out/Oosterkade_23/dossier_9503HN_23.json --outdir out/vabi_import
```
→ 3 XML's + `IMPORTEREN.txt`. In EPA per tegel importeren (Constructies → Objecten → Installaties),
dan zelf Algemeen invullen → Rekenen.

## Wat ik vannacht heb gebouwd
| Onderdeel | Bestand | Status |
|---|---|---|
| VABI-"taal" uit de binary | `vabi/extract_strings.py` | 237 dropdowns / 22 domeinen → `refs/vabi_enum_inventory.json` |
| Master enum-catalogus | `vabi/build_enum_catalog.py` | `refs/vabi_enums.json` — 142/237 velden met codes |
| Monitor-enums + verplicht | `vabi/harvest_monitor.py` | 14 monitors → verplicht-velden voor een resultaat |
| Constructie-generator | `vabi/constructie_generate.py` | ✅ importeert (refactor: gedeelde guid/naam) |
| Objecten-generator (geometrie) | `vabi/objecten_generate.py` | ✅ importeert (Hoofdvlak/Deelvlak) |
| Installatie-generator | `vabi/installatie_generate.py` | ✅ importeert (ventilatie + sjabloon) |
| Alles-in-één | `vabi/generate_all.py` | 1 commando → 3 bibliotheken |
| Resultaat teruglezen | `vabi/result_reader.py` | Standaard-toets: energiebehoefte vs Standaard |
| MagicPlan forms/fields-spec | `../MagicPlan-VABI-veldenmapping.md` | klaar om in MagicPlan te bouwen |
| Nij Begun-workflow | `docs/nijbegun_workflow.md` | volledige keten + qv;10/renovatiejaar-logica |

**Tests: 71/71 groen.** Alle persoonsdata uit de sjablonen gestript.

## Belangrijke inzichten
- **De configurator draait offline, 0 tokens.** Pure Python; AI alleen nodig om te bouwen.
- **Standaard is geen vast getal** — VABI rekent 'm per woning. Voor Oosterkade: energiebehoefte
  118,45 vs Standaard 91 → **voldoet niet** → maatregelen nodig (precies waar Nij Begun voor is).
- **Import lukt gegarandeerd** doordat we klonen uit een echte export + een harde poort die elke
  enum-waarde vooraf tegen VABI's bekende codes checkt.

## Waar we heen gaan (morgen + daarna)
1. **MagicPlan forms/fields aanmaken** volgens `MagicPlan-VABI-veldenmapping.md` (samen, of jij).
   - Fields = constructies; Forms = installaties; dak-m² handmatig (hellingshoek + m²-veld).
2. **Installatie-enums verder vullen**: exporteer in EPA 5–6 diverse projecten (warmtepomp/PV/WTW/
   blok/VvE) per tegel → `python vabi/harvest.py <map>/*.xml` → dekking groeit richting 237/237.
3. **qv;10 na maatregelen**: exacte waarde (jouw "1.iets") + bron bevestigen → automatisch zetten.
4. **Toekomstige-staat-generatie**: maatregelen in de schil verwerken → herrekenen → Standaard-toets.
5. **Rapport koppelen**: `result_reader` → huidige staat + Standaard in het isolatieplan/template.
6. Gevel-m² per oriëntatie verfijnen (nu één benaderd geveloppervlak; adviseur verifieert in Vabi).

## Aandachtspunten / open
- Installatie-generator neemt verwarming/tapwater nu uit het sjabloon over als het dossier geen
  installatiedata heeft (Nij Begun-opname = alleen ventilatie). Adviseur verifieert in Vabi.
- MagicPlan-forms heb ik bewust NIET automatisch in je live-account gebouwd (risico op je bestaande
  templates); de spec ligt klaar zodat we het morgen samen/gecontroleerd doen.
