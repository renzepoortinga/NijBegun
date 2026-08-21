# MagicPlan-intakepakket

De veilige dashboardintake gebruikt één ZIP-bestand. Het dashboard doet geen
live API-call tijdens preview of import.

## Inhoud

- `manifest.json`: `schema`, stabiel `project_id`, `form_fingerprint` en
  `identity` (BAG-id of minimaal postcode + huisnummer; daarnaast straat,
  plaats en woningtype).
- `statistics.csv`: ongewijzigde MagicPlan Statistics-export.
- `report.txt` of `report.pdf`: MagicPlan-projectrapport met formulierwaarden.
- `geometry.json`: hetzelfde `project_id` en `floor_contours`, gemapt op de
  exacte verdiepingsnamen uit Statistics.
- Optioneel `sha256` in het manifest: mapping van bestandsnaam naar volledige
  SHA-256. Als een hash is opgegeven, is die verplicht correct.

Paden buiten de ZIP, pakketten groter dan 100 MB uitgepakt, ontbrekende delen,
een afwijkende formulierfingerprint en conflicterende woning- of project-
identiteiten worden geweigerd.

## Preview en merge

Upload toont eerst identiteit, schildelen-diff, mergebeleid en gegroepeerde
actiepunten. Tot bevestiging wordt het dossier niet gewijzigd. Bevestiging is
gebonden aan de SHA-256 van exact het gepreviewde pakket.

Statistics vervangt opname, geometrie, schil en installaties. Deze groepen
blijven uit het bestaande dossier behouden:

- handmatige dak- en dakkapelvlakken met bron `webapp-wizard`, tenzij dezelfde
  id al in de nieuwe import zit;
- foto's;
- maatregelen en haalbaarheidsbeoordelingen;
- eerdere Vabi-resultaten (`berekening`);
- adviseursgegevens.

De offline contractfixture staat in `tests/fixtures/intake_complete/`. De exact
verwachte resttaken en verplichte dakcontrole staan vóór de implementatie
vastgelegd in `expected.json` en worden in de ketentest letterlijk vergeleken.
