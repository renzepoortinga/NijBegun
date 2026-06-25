# Nij Begun & EPA — Automatiseringspijplijn (`tool/`)

Werkende bouwstenen voor de pijplijn uit het *Master Blueprint*. Eén MagicPlan-opname → energielabel (Vabi EPA-W) én Nij Begun isolatieplan (JSON + PDF).

## Architectuur (kort)
```
MagicPlan ──API──► canoniek dossier (JSON) ──► Vabi EPA-W (NTA8800-engine, via monitoringbestand)
                            │                         │ kWh/m².jr huidig + Standaard + na maatregelen
                            ├──► maatregel-engine (catalog.json, laagste kosten → Standaard)
                            ├──► isolatieplan: Word-template invullen → PDF + JSON
                            └──► validator (KWACO-checklist) ── poortwachter vóór indienen
```

## Mappen
- `core/` — het canonieke datamodel (`dossier.py`) = single source of truth + `canonical_schema.json`.
- `catalog/` — parser van de Nij Begun Maatregelencatalogus-xlsx → `catalog.json`.
- `magicplan/` — CSV-statistics-parser + Project Plan API-client (live door jou te draaien).
- `vabi/` — NTA8800-monitoringbestand: parser + generator (round-trip getest).
- `isolatieplan/` — vult het officiële Word-template vanuit een dossier.
- `validator/` — toetst het dossier aan de KWACO "sluitend"-checklist.
- `tests/` — offline tests tegen de échte voorbeeldbestanden in de bovenliggende map.
- `out/` — gegenereerde output (gitignore-waardig).

## Draaien
1. `pip install python-docx lxml openpyxl`
2. Kopieer `.env.example` → `.env` en vul je MagicPlan-credentials in (NIET committen / niet in OneDrive laten staan).
3. Zie `BUILD_LOG.md` voor de status per bouwsteen en exacte commando's.

> Belangrijk: de pijplijn berekent **nooit zelf** de energieprestatie — dat doet je geattesteerde Vabi EPA-W. Wij leveren de invoer aan en lezen de uitkomsten. Dit houdt je in de toegestane handmatige adviseur-route (zie Blueprint §9.1).
