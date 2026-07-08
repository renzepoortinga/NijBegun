# Nieuwe website uploaden naar Cloud86

De hele site is **één bestand**: `index.html` (alle CSS/JS/afbeeldingen zitten erin, geen
externe bestanden nodig). Uploaden duurt 5 minuten.

## Stap 0 — Vooraf controleren (lokaal)
Dubbelklik op `index.html` in deze map: de site moet er in de browser compleet uitzien
(label-animatie in de hero, tellend subsidiebedrag verderop). Ziet dat er goed uit? Dan uploaden.

## Stap 1 — Backup van de oude site (belangrijk!)
1. Log in op het klantenpaneel van Cloud86 (mijn.cloud86.nl) en open het controlepaneel
   van de hosting (bij Cloud86 is dat meestal **Plesk**: knop "Login to Plesk" / "Beheer").
2. Open **File Manager** (Bestandsbeheer).
3. Ga naar de webroot van het domein: de map heet **`public_html`** of bij Plesk vaak
   **`httpdocs`** (de map waar de huidige `index.html` / `index.php` van de oude site staat).
4. Selecteer **alle bestanden**, kies **Archive/Zip** (of download ze), en bewaar het archief
   bijv. als `backup-oude-site-2026-07.zip`. Zet de zip eventueel één map hoger (buiten de
   webroot), of download hem naar je pc. Zo kun je altijd terug.

## Stap 2 — Nieuwe `index.html` uploaden
1. Blijf in de File Manager in de webroot (`public_html` / `httpdocs`).
2. Klik **Upload** en kies de nieuwe `index.html` uit deze map.
3. Bevestig **overschrijven** als er al een `index.html` staat.
4. **Let op oude startbestanden:** staat er nog een `index.php` of `index.htm` van de oude
   site? Hernoem die naar bijv. `index.php.oud` (of verwijder hem) — anders kan de server die
   vóór de nieuwe `index.html` blijven tonen.
5. Oude losse mappen/bestanden van de vorige site (css/, images/, js/ …) mogen blijven staan
   of later opgeruimd worden; de nieuwe site gebruikt ze niet.

## Stap 3 — Controleren
1. Open https://poortinga-energieadvies.nl in een **incognito-venster** (of forceer verversen
   met Ctrl+F5) — anders zie je mogelijk nog de oude site uit de cache.
2. Check kort: hero met bewegend energielabel, prijs **€ 375 incl. btw**, stappenplan met knop
   naar isolatie.nijbegun.nl, en test de site ook even op je telefoon.

## Alternatief: via FTP (bijv. FileZilla)
1. FTP-gegevens staan in het Cloud86-paneel (host = ftp.jouwdomein of het serveradres,
   gebruikersnaam/wachtwoord van het hostingaccount; kies FTPS/expliciete TLS indien mogelijk).
2. Verbind, ga naar `public_html` / `httpdocs`.
3. Download eerst de bestaande bestanden naar een backupmap op je pc (= stap 1).
4. Sleep de nieuwe `index.html` naar de webroot en bevestig overschrijven.
5. Controleer zoals in stap 3.

## Terugdraaien (mocht het nodig zijn)
Pak de backup-zip uit stap 1 weer uit in de webroot (of upload de gedownloade bestanden terug)
en de oude site staat er weer.
