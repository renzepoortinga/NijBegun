# Kennisbank beheren

Je hoeft geen vaste mappenstructuur of handmatig register bij te houden. Elk ondersteund PDF-, DOCX-,
XLSX-, Markdown- of tekstbestand onder `knowledge/` wordt automatisch ontdekt. `sources.json` bevat
alleen de expliciet gecontroleerde kernbronnen en hun voorrang/status.

## Document toevoegen of vervangen

1. Controleer of gebruik en interne verwerking volgens de licentie zijn toegestaan.
2. Zet het bestand ergens onder `knowledge/`; de applicatie ontdekt het automatisch.
3. Open **Kennisbank** en controleer categorie, duplicaatmelding en aanwezigheid.
4. Voor een nieuwe normatieve kernversie laat je de bronstatus en toolmapping controleren.
5. Stel drie bekende controlevragen en controleer antwoord én bronpassages.

PDF-, DOCX- en spreadsheetbronnen onder `knowledge/` worden niet in Git opgenomen. De applicatie gebruikt
gelicentieerde NTA-/ISSO-inhoud standaard niet totdat `NIJBEGUN_KENNISBANK_LICENTIE=1` expliciet is gezet.

## Minimale actieve set

- actuele NTA 8800;
- toepasselijke ISSO 82.1;
- actuele BRL 9500-W;
- actuele Nij Begun-regeling/kennisbank en maatregelencatalogus;
- VABI EPA-W-handleiding, attest en gebruikte versie;
- interne herkomst, werkwijze, beslislogica en aannames-audit.

De vraagbaak mag uitsluitend uit actieve, geregistreerde bronnen antwoorden. De bevoegde adviseur blijft
verantwoordelijk voor de toepassing op een concreet dossier.
