# Nij Begun & EPA-tool — systeemuitleg (voor engineers & collega's)

Doel: één woningopname omzetten naar (A) een **energielabel-invoer voor Vabi EPA-W** en
(B) een **Nij Begun isolatieplan** (Maatregel 29). De tool levert invoer aan en leest uitkomsten;
hij rekent zelf nooit NTA 8800.

## Gouden regel (architectuurprincipe)
**Vabi EPA-W (geattesteerd) is de rekenkern.** Onze tool genereert *invoer* en leest *resultaten*.
Zo blijft de adviseur in de toegestane handmatige route en buiten de tool-validatieplicht van Nij Begun.
Elke benadering (gevel-m², gevel-oriëntatie) wordt door de adviseur in Vabi geverifieerd.

## End-to-end pijplijn
```
MagicPlan-opname ─(API: geometrie)─┐
                  ─(report-PDF: form-antwoorden)─┐
                                                  ▼
                                   core/dossier.py  (canoniek datamodel = single source of truth)
                                                  │
        ┌─────────────────────────────────────────┼───────────────────────────────────────┐
        ▼                                          ▼                                        ▼
  isolatieplan/ + ventilatie/ + foto/        vabi/generate_all.py                    engine/measure_engine
  + validator/  (Nij Begun-plan)         (3 bibliotheek-XML's)                     (goedkoopste pakket → Standaard)
                                                  │                                        │
                                                  ▼                                        ▼
                                   EPA-import (Constructies/Objecten/Installaties)   engine/advies_text.py
                                                  │                                  (begeleidende tekst)
                                                  ▼
                                          Vabi rekent → vabi/result_reader.py (Standaard-toets)
```

## Hoe de VABI-koppeling werkt (de kern)
VABI's `.epa`-projectbestanden zijn **versleuteld**. De koppeling loopt daarom via de **per-tegel
import/export** van EPA (onversleutelde XML). Drie bibliotheken samen = een compleet project:
- **Constructiebibliotheek** — constructie-*types* (Rc/isolatie/glas), integer enum-codes.
- **Objectenbibliotheek** — geometrie: Rekenzone → Hoofdvlak (gevel/dak/vloer) → Deelvlak (raam/deur).
- **Installatiebibliotheek** — ventilatie/verwarming/tapwater/koeling.

**"De taal van VABI" ontcijferd zonder documentatie:**
- `vabi/extract_strings.py` ript de native exe → de C++-namen `Combo_Enum_Base<Enum,Domein>` geven de
  **complete kaart van 237 dropdowns / 22 domeinen** (`refs/vabi_enum_inventory.json`).
- De integer-codes per veld komen uit **echte exports** (`vabi/harvest.py` → `code_universe.json`) en
  uit het monitoringbestand (`vabi/harvest_monitor.py`, incl. *verplicht*-detectie).
- `vabi/build_enum_catalog.py` voegt alles samen tot `refs/vabi_enums.json` (master-catalogus).

**Garantie-op-import-ontwerp (geen "enum mismatch"):**
1. **Sjabloon** = een echte VABI-export (header/versie + structuur kloppen per definitie).
2. De generator **kloont** per bouwdeel de best passende standaard-constructie en zet alleen Guid/Naam/
   geometrie; verzint nooit een enum-waarde.
3. **Harde validatie-poort** (`vabi/codebook.py`): elke gezette enum-waarde moet in de door-VABI-bekende
   set zitten, anders → "NIET klaar voor import: veld X" en géén bestand.
→ Live bewezen: alle 3 bibliotheken importeren foutloos in EPA 12.0.1.

## De twee paden
- **Energielabel**: volledige schil + installaties → 3 bibliotheken → Vabi → afmelden.
- **Nij Begun isolatieplan**: schil + alleen ventilatie → huidige staat naar Vabi → engine kiest
  goedkoopste pakket → toekomstige staat opnieuw naar Vabi → Standaard gehaald? → isolatieplan-template
  (Word) + ventilatieberekening + foto-checklist + validator. Standaard = géén vast getal (Vabi rekent
  hem per woning). qv;10 na maatregelen óf renovatiejaar (zie `docs/nijbegun_workflow.md`).

## Modules (kort)
| Map/bestand | Rol |
|---|---|
| `core/dossier.py` | canoniek datamodel (single source of truth), JSON-(de)serialiseerbaar |
| `magicplan/` | extractor (API-geometrie) + report_parser (PDF-antwoorden) + assemble (hybride → dossier) |
| `catalog/` | Maatregelencatalogus.xlsx → catalog.json |
| `engine/measure_engine.py` | kiest goedkoopste maatregelpakket per vlak (Rc/U-drempels) |
| `engine/advies_text.py` | begeleidende advies-tekst (offline, deterministisch) |
| `vabi/codebook.py` | enum-codes + harde validatie-poort |
| `vabi/{constructie,objecten,installatie}_generate.py` | dossier → 3 importeerbare bibliotheken |
| `vabi/generate_all.py` | 1 commando → alle 3 + importinstructie |
| `vabi/result_reader.py` | VABI-resultaat (Summary) → Standaard-toets |
| `isolatieplan/`, `ventilatie/`, `foto/`, `validator/` | Nij Begun-plan-bouwstenen |

## Draait offline — geen AI/tokens
De hele tool is **pure Python**. AI (Claude) was alleen nodig om te *bouwen*; in gebruik draait alles
lokaal: `python run.py` / `python vabi/generate_all.py …` of als `.exe`. Geen internet, geen tokens.
De enum-data is afgeleid uit VABI's eigen export/binary en wordt bij een VABI-update simpel opnieuw
geoogst (re-export → `harvest.py`/`extract_strings.py`) — self-healing, niets gehardcode.

## Voor de software engineer (uitbreiden)
- Datamodel is het contract: voeg velden toe in `core/dossier.py`, map ze in `magicplan/assemble.py`,
  vertaal in de juiste `vabi/*_generate.py`, dek af met `tests/run_tests.py` (nu 75/75).
- MagicPlan-velden ↔ VABI-mapping: zie `../MagicPlan-VABI-veldenmapping.md`.
- Multi-rekenzone objecten-generatie is de eerstvolgende grotere uitbreiding (nu 1 zone).
