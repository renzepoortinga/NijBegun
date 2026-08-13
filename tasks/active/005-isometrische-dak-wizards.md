---
id: 005
assigned: claude
branch: feat/isometrische-dak-wizards
depends_on: []
---

<!-- De map ís de status: backlog/ ready/ active/ done/. Geen status-veld hier. -->

# Task 005 — Isometrische dak/dakkapel-invoerwizards

## Goal
Taak 004 gaf de opname-editor een visuele laag, maar die is schematisch (vast
"WONING"-rechthoekje + labelkaartjes, 2D-zijaanzicht met geclampte/nep-
proporties in `dakPrev()`), niet geometrisch. Renze vergeleek dit met Inbrix
(concurrent) en wil een echte, volledig isometrische, live meebewegende
tekening bij het invoeren van dak/dakkapel-maten. Dit is het eerste van twee
taken (zie `tasks/ready/006-isometrisch-gebouwoverzicht.md`, `depends_on:
[005]`) — dit deel behandelt de invoerwizards, waar de echte maten al worden
getypt maar nog niet bewaard blijven.

Volledig uitgewerkte aanpak + achtergrond staat in het plan-document van de
sessie waarin dit is afgebakend (context hieronder is zelfstandig leesbaar,
maar bij twijfel: de Sessions-log van deze taak is de waarheid, niet het
oorspronkelijke plan-bestand — dat leeft buiten de repo).

## Scope
- Nieuw `dashboard/static/isometrie.js` (eerste losse JS-bestand — nu staat
  alles inline in `<script>`-blokken in `dashboard/app.py`): een kleine,
  afhankelijkheidsvrije 3D→2D isometrische projectie (standaard 2:1 dimetrie:
  `sx=(x-z)*cos30, sy=(x+z)*sin30-y`) + helpers om een blok (extrusie van een
  rechthoekige footprint) en een hellend vlak als SVG-polygonen te tekenen.
- Plat dak, zadeldak/driehoek en de dakkapel-stap (app.py: de 3
  dak-toevoegvormen + `opname_dakkapel`) herbouwd: de bestaande
  formuliervelden (breedte/lange_zijde/helling/diepte/hoogte — al live
  ingevuld) voeden nu de isometrische projectie i.p.v. het huidige 2D-
  zijaanzicht (`dakPrev()`/`kapelPrev()`). Zelfde architectuurgrens als nu:
  puur client-side, `oninput`, geen serverroundtrip.
- `core/dossier.py` `SchilDeel`: nieuwe **optionele** velden (bv.
  `breedte_m`/`diepte_m`, eventueel `hoogte_m` voor de dakkapel — kies bij
  implementatie wat het schoonst aansluit) als pure rendering-metadata:
  default `None`, niets bestaands leest ze, dus geen impact op VABI-export
  of beslislogica. Gevuld door de bestaande routes `opname_dak_plat`,
  `opname_dak_driehoek` en `opname_dakkapel`, die deze maten al als
  formuliervelden binnenkrijgen en ze nu niet meer weggooien na de
  m²-berekening.
- Tests in `tests/run_tests.py`: nieuwe checks dat de routes de nieuwe
  velden correct zetten; bestaande dakkapel-routetests moeten ongewijzigd
  blijven slagen (gedrag zelf verandert niet, alleen extra opgeslagen data).

## Out of scope
- De "9 geometrieën"/kompas-stap (het "afwijkend"-vangnet): blijft
  functioneel ongewijzigd. Dit is bewust de vrije/handmatige invoerroute,
  geen vaste vorm om te renderen.
- `core/geometry.py` zelf wijzigen — de bestaande scalar-functies
  (`dak_vlakken_zadeldak` e.a.) blijven exact zoals ze zijn; alleen de
  call-sites in app.py geven er straks ook de ruwe maten bovenop mee.
- Taak 006 (het opgeslagen gebouwoverzicht, `dashboard/gebouw_svg.py`) —
  aparte taak, hangt af van de velden die deze taak toevoegt.
- Geen build-stap/bundler introduceren voor het nieuwe JS-bestand; gewoon
  een los `<script src=...>`-bestand, consistent met hoe `app.css` al
  wordt geserveerd.

## Acceptance criteria
- [ ] Plat dak, zadeldak/driehoek en dakkapel tonen een echte isometrische
      wireframe (3D-projectie, geen 2D-zijaanzicht/geclampte waarden) die
      live meebeweegt met de ingevoerde maten
- [ ] De nieuwe `SchilDeel`-velden worden door de betreffende routes gevuld
      en overleven een save/reload-cyclus van het dossier
- [ ] Bestaande dakkapel/dak-routetests blijven groen; nieuwe tests dekken
      de nieuwe velden
- [ ] Voldoet aan `docs/design-system.md` (kleur/typografie uitsluitend via
      bestaande CSS-tokens incl. `--svg-fs-1..8`, geen losse hex/pixels,
      volgt `prefers-color-scheme` + `[data-theme]`, animatie met
      `prefers-reduced-motion`-fallback, geen horizontale scroll op
      390/768/1024/1440)
- [ ] `python tests/run_tests.py` slaagt
- [ ] `./scripts/verify.sh` slaagt
- [ ] AI-review PASS door een andere agent dan de bouwer (zelfde model of
      leverancier toegestaan)

## Sessions
- 2026-08-14 (Claude/Sonnet 5, Manager): taak afgebakend na feedback van
  Renze op taak 004's visuele laag ("statisch", "10x niks" t.o.v. Inbrix).
  Verkend: `core/geometry.py` + `core/dossier.py SchilDeel` kennen alleen
  m²+hoek+kompasrichting, geen coördinaten/afmetingen — vandaar de knip in
  twee taken (deze + 006) en de nieuwe optionele dossiervelden hier. Plan
  besproken en goedgekeurd met Renze (volledig isometrisch, 100%).
- 2026-08-14 (Codex, Builder): plat dak, zadeldak en dakkapel omgebouwd naar
  een losse dependencyvrije 3D→2D-projectiemodule (`isometrie.js`). Plat dak
  vraagt nu breedte+diepte; de routes bewaren `breedte_m`, `diepte_m`,
  `hoogte_m` en voor dakkapeldelen een stabiele `moedervlak_id`. Dakkapel
  wordt zonder beschikbare offsets gecentreerd op het moederdakvlak. Nieuwe
  route- en roundtriptests toegevoegd: 739/739 groen; `verify.sh` PASS (de
  bekende taak-002 Python-advisory doordat Git Bash geen `python3` vindt;
  dezelfde suite is apart met `python` volledig groen). JS-syntax en
  `git diff --check` groen. In-app browser was niet verbonden, dus geen
  screenshot-QA; responsive/dark/reduced-motion contracten statisch getoetst.

## Notes
- Referentie voor de gewenste stijl: taak 004's Notes verwijzen naar
  Inbrix' publieke handleiding-video's (inbrix.nl/handleidingen) — daar is
  een isometrische wireframe met vlaklabels + paars actief vlak te zien bij
  dak/dakkapel-invoer. `docs/dak-invoer-marktonderzoek.md` (11-7) heeft de
  bredere marktvergelijking (Inbrix/Sobolt/Vabi), maar geen exacte
  variabelen-per-daktype (niet publiek gedocumenteerd).
- Kies bij implementatie bewust de veldnamen/structuur voor de nieuwe
  `SchilDeel`-metadata zodat taak 006 er direct op kan bouwen (zie dat
  taakbestand voor hoe de velden daar gebruikt worden).
