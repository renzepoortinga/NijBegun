# MagicPlan live forms — wijzigingen 25-6-2026 (via custom-forms API, geverifieerd)

Forms: **Object · Constructies · Installaties** (workspace R.poortinga). Backup vóór deze ronde:
`magicplan_*_backup.json` (eerdere sessie) + in-sessie `window.__BK_FORMS__`. Save/publish-roundtrip
live bewezen (save 200 `success`, publish 200; geen dubbele forms — bleef 3).

## Doorgevoerd + geverifieerd
1. **Aanvoertemperatuur** (Installaties → Verwarming): opties **80/60 + 90/70** toegevoegd (ging tot 70/60).
2. **Foto vooraanzicht + huisnummer**: verplaatst van Installaties → **Object** (overige foto's blijven in Installaties).
3. **Vloer-constructie** ("Begrenzing (vloer)" + "Bouwjaar-klasse (vloer)"): verplaatst van Object → **Constructies**.
4. **"Spouwdikte (dak, mm)"**: verwijderd uit Constructies (spouw = gevel-begrip; gevel-spouwdikte staat op het wand-element).
5. **PV via kwaliteitsverklaring?**: nieuw, conditioneel bij PV-panelen (ja → rest niet nodig, jij zet het in Vabi).
6. **Meerdere PV-systemen (2e)?**: nieuw, conditioneel; PV-2-blok (paneeltype/oriëntatie/hellingshoek/aantal/oppervlak/Wp).
7. **Tweede opwekker (hybride)?**: nieuw, in Verwarming; Verwarming-2-blok (opwekker/afgifte/aanvoertemp/jaar).
8. **Dak m² zijde 1/2 (override uit rapport)**: nieuw in Object (gemeten m² overrulen).

## Parser-stand (magicplan/statistics_csv.py)
- Leest AL: multi-PV (`_pv_from`, PV-2..5), extra verwarming/tapwater/koeling, foto's, oriëntatie-voorgevel,
  rekenzone-per-installatie, en de **element-overrides op wand/vloer** (begrenzing/isolatie/Rc-bron/rekenzone).
- **Nog te wiren** (TODO, blokkeren geen opname): lezen van **"Dak m² zijde 1/2 (override)"** → dakvlak-m² overschrijven,
  en **"PV via kwaliteitsverklaring?"** → PV-systeem flaggen (zoals rc_bron=Kwaliteitsverklaring bij de schil).

## Per-element afwijking (vloer/gevel) — WAAR
Niet in een project-form maar op het **element** zelf: tik in de plattegrond de specifieke vloer/wand aan →
custom fields → **Begrenzing (indien anders dan buitenlucht)** + isolatie/Rc-bron/rekenzone. Groepen "Gevel per wand"
(All Walls) en "Vloer" (All Floors) zijn gepubliceerd. Dak heeft géén element → afwijkend dakvlak via Object (#8 hierboven).

## Nog open (bewust niet gedaan — koppelt aan de parser / risicovol)
- **Ventilatie subsysteem conditioneel per type** (A→A1/A2.., C→C1.. enz. i.p.v. één lange lijst): vereist per-type
  subsysteem-velden + parser die de juiste leest → samen met de parser doen.
- **Element-fields opschonen**: dubbele velden (3× isolatiedikte) + overbodige plan-groep "Gevel - project" → voorzichtig
  opruimen (mag de werkende per-element overrides niet breken).
