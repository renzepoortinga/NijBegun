# MagicPlan-intakepakket

De veilige dashboardintake gebruikt één ZIP-bestand. Het dashboard doet geen
live API-call tijdens preview of import.

## Inhoud

- `manifest.json`: `schema`, stabiel `project_id`, `form_fingerprint` en
  `identity` (BAG-id of minimaal postcode + huisnummer; daarnaast straat,
  plaats en woningtype).
- `statistics.csv`: ongewijzigde MagicPlan Statistics-export.
- `report.txt` of `report.pdf`: MagicPlan-projectrapport met formulierwaarden.
- `geometry.json`: schema `nijbegun-magicplan-geometry/1`, hetzelfde
  `project_id`, verplichte `unit: "m"`, `area_basis:
  "VloerInfo.oppervlakte_m2"` en `floor_contours`, gemapt op de exacte
  verdiepingsnamen uit Statistics. `contour_m` blijft metrisch en is op `(0,0)`
  genormaliseerd, zoals het bestaande API-assemblepad. Een contour heeft
  minimaal drie unieke eindige punten, kruist zichzelf niet en de m²-oppervlakte
  komt op twee decimalen overeen met de gemeten vloeroppervlakte. Alleen de
  eenvoudige-polygonkern wordt gedeeld met het interactieve ventilatieplan;
  diens relatieve `0..1`-coördinatencontract geldt nadrukkelijk niet voor
  `VloerInfo.contour_m`.

Als inputveiligheidsgrens (geen bouwkundige of NTA-norm) moeten bounding-box-
breedte en -diepte positief/eindig zijn. Aspectratio en de verhouding tussen
bounding-boxoppervlak en polygonoppervlak mogen maximaal `10^6` zijn. Deze zeer
ruime conditioneringsgrens weigert IEEE-754-extremen die ondanks gelijke m² door
de shoelace-check komen; een gewone langwerpige contour van 40×1 m blijft geldig.
- Optioneel `sha256` in het manifest: mapping van bestandsnaam naar volledige
  SHA-256. Als een hash is opgegeven, is die verplicht correct.

Paden buiten de ZIP, pakketten groter dan 100 MB uitgepakt, ontbrekende delen,
een afwijkende formulierfingerprint en conflicterende woning- of project-
identiteiten worden geweigerd. BAG en adres worden naast elkaar gecontroleerd:
een gelijk BAG-id maskeert geen afwijkend adres. Elke niet-lege bron moet via
hetzelfde sleuteltype aantoonbaar aan het manifest zijn gekoppeld; een BAG-only
bron wordt dus niet stil aan een adres-only bron gekoppeld.

## Preview en merge

Upload toont eerst identiteit, schildelen-diff, mergebeleid en gegroepeerde
actiepunten. Tot bevestiging wordt het dossier niet gewijzigd. Bevestiging is
gebonden aan een onvoorspelbaar, eenmalig previewtoken. Elke preview krijgt een
eigen stagingdirectory. De metadata wordt pas na alle bestanden atomisch
gepubliceerd en bevat SHA-256-hashes van pakket, staged dossier en de
basisrevisie van het actuele dossier. Bevestigen claimt de metadata atomisch,
hercontroleert alle hashes plus basisidentiteit en ruimt staging op bij succes,
annuleren en fouten. Een gewijzigde basis vereist een nieuwe preview.

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
