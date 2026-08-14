---
id: 007
assigned: claude
branch: feat/gebouwoverzicht-echte-contour
depends_on: [006]
---

<!-- De map ís de status: backlog/ ready/ active/ done/. Geen status-veld hier. -->

# Task 007 — Gebouwoverzicht op de echte plattegrondcontour

## Goal
Het isometrische gebouwoverzicht (`dashboard/gebouw_svg.py`, taak 006) tekent altijd een
rechthoekige doos, afgeleid uit gevel-m² ÷ gevelhoogte — nooit de werkelijke vorm van het huis
(L-vormige aanbouw, erker). Onderzoek wees uit dat MagicPlan's eigen API (`plan_data.floors[].
image_map`, `symbol_id: "floor"`) de échte plattegrondcontour als pixel-polygon teruggeeft, tot nu
toe volledig ongebruikt (`magicplan/assemble.py:geometry_from_plan` gooit 'm weg en benadert de
omtrek met `4·√opp·1,15`). Deze taak ontsluit die contour en gebruikt 'm in het gebouwoverzicht,
als eerste stap richting een Inbrix-achtige visuele kwaliteit met het gemak van de MagicPlan-scan.

## Scope
- `core/dossier.py`: `VloerInfo.contour_m` — optioneel, backward-compatible veld
  (`Optional[List[List[float]]]`), grondvlak-contour in meter, oorsprong linksboven.
- `core/geometry.py`: `polygon_oppervlakte_m2(punten)` — generieke schoenveter-formule, herbruikbaar.
- `magicplan/assemble.py`: `_floor_contour_m(fl)` — leest `image_map`'s `symbol_id: "floor"`-polygon
  (pixels), kalibreert de schaal op `statistics.area_with_walls` (m², bruto incl. wanden — dezelfde
  grootheid als de polygon beschrijft), normaliseert naar oorsprong (0,0). Geen data of ontaarde
  polygon → `None`, nooit een gegokte vorm (zelfde "niet gokken"-regel als de rest van de keten).
  Gewired in `geometry_from_plan` op elke `VloerInfo`.
- `dashboard/gebouw_svg.py`: `_polygon_footprint(dos)` (contour van de grootste bouwlaag, mits
  `gevelhoogte_m` bekend) + `_muurvlakken(punten, wall_h)` (één gevelvlak per zichtbare contourrand,
  backface-culling + painter's-order-sortering voor déze iso-camera). `gebouw_svg()` probeert de
  polygon-footprint eerst; zonder bruikbare contour blijft het bestaande rechthoek-pad (taak 006)
  ongewijzigd de fallback. Traceerbaarheids-/metadatalaag generiek gemaakt zodat hij in beide paden
  werkt (contourranden zijn niet 1-op-1 aan een gevelnaam te koppelen).
- Tests (`tests/run_tests.py`): `polygon_oppervlakte_m2`, `_floor_contour_m` (kalibratie, missende
  data, ontaarde vorm), `geometry_from_plan`-doorgifte, en een L-vormig gebouwoverzicht (>2 zichtbare
  gevelvlakken i.p.v. de rechthoek-reductie van 2).

## Out of scope
- Het dák volgt de polygon nog niet — `_roof_faces` blijft op de rechthoekige bounding-box van de
  contour werken (zelfde aanpak als taak 006). Een dak dat zelf een niet-rechthoekige footprint volgt
  is een vervolgstap.
- `dashboard/static/isometrie.js` (de client-side wizard-previews voor dak/dakkapel-invoer) is niet
  aangeraakt — dat blijft op door de gebruiker ingevoerde maten werken, niet op een MagicPlan-contour.
- Geen visuele stijl-upgrade (shading/schaduw/"Inbrix-look") — dat is een aparte, expliciet nog niet
  ingeplande vervolgstap (zie gesprek: SVG uitbouwen i.p.v. Three.js, om vector-inbedding in het
  Word/PDF-isolatieplan te behouden).
- Geen validatie tegen een tweede/derde echte MagicPlan-export — de kalibratie is geverifieerd tegen
  precies één echte capture (`out/plan_raw.json`, niet gecommit, bevat een echt klantproject).

## Acceptance criteria
- [x] `core/dossier.py`: `VloerInfo.contour_m` toegevoegd, backward compatible (default `None`).
- [x] `core/geometry.py`: `polygon_oppervlakte_m2` toegevoegd + getest.
- [x] `magicplan/assemble.py`: contour-extractie + kalibratie, gewired in `geometry_from_plan`.
- [x] `dashboard/gebouw_svg.py`: polygon-footprint-pad met backface-culling, rechthoek-pad blijft
      intacte fallback.
- [x] `./scripts/verify.sh` slaagt (Python-tests draaien via PowerShell, niet via de kapotte
      `python3`-alias in Git Bash — zie Notes; 768/768 groen).
- [x] AI-review PASS door een andere agent dan de bouwer (`/code-review high`, zie Sessions).

## Sessions
- 2026-08-14 (claude): Bouwde eerst tegen een VERALTE lokale branch-tip
  (`feat/isometrisch-gebouwoverzicht`, commit `ab2a2ed`) — bleek niet de versie die daadwerkelijk
  via PR #8 naar `main` was gemerged (`gebouw_svg.py` was daar tussentijds 558 regels herschreven,
  `_footprint`/face-structuur veranderd). Ontdekt via `git diff --stat` vóór het aanmaken van de
  branch. Hersteld: stash, nieuwe branch vanaf actuele `main`, backend-wijzigingen (dossier/geometry/
  assemble — bleken ONgewijzigd tussen de twee versies) schoon toegepast, `gebouw_svg.py`- en
  testintegratie helemaal opnieuw geschreven tegen de actuele structuur. 763/763 tests groen.
  Onderliggende MagicPlan-contourdata (image_map/symbol_id="floor") geverifieerd tegen een echte
  capture (`out/plan_raw.json`, niet gecommit — bevat een echt klantproject) inclusief onafhankelijke
  kruiscontrole van de schaal via een kamer-omtrek (~3% afwijking, binnen orde van grootte van
  bestaande benaderingen in de tool).
- 2026-08-14 (claude), vervolg: `/code-review high` (fork, andere doorloop dan de bouwer) leverde
  9 bevindingen op; 7 verwerkt, 2 bewust niet:
  - **Echte bug gefixt**: `_muurvlakken`'s zichtbaarheidstest gebruikte het gemiddelde van de
    hoekpunten als "binnen de veelhoek"-referentiepunt — valt bij een concaaf grondvlak (U-vorm)
    buiten de veelhoek en draait dan de buiten-normaal van sommige randen om. Herschreven naar een
    schoenveter-teken-gebaseerde normaal (geen referentiepunt nodig, correct voor élke enkelvoudige
    veelhoek). Test toegevoegd op een U-vorm met handmatig nagerekende verwachte zichtbaarheid.
  - **Robuustheid**: `_floor_contour_m` faalde hard (TypeError) op een niet-numerieke coördinaat;
    verwerpt nu ook >1 `"floor"`-entry (welke hoort bij `area_with_walls`?) en een bruto/netto-
    oppervlakteverhouding die niet aannemelijk is (>1,5x) — een nieuwe, onafhankelijke plausibiliteits-
    check bovenop de bestaande kalibratie.
  - **Traceerbaarheid**: contourmuren droegen geen enkel `data-*`-attribuut terwijl de SVG's eigen
    bijschrift claimde dat "alle vlakken herleidbaar" zijn — nu `data-contour="true"` +
    `data-geometrie`/`data-punten-3d`, en het bijschrift is conditioneel op de footprint-bron.
  - **Opgeruimd**: gedeelde `_geldige_hoogte`-helper (was gedupliceerd), en `_footprint(dos)` wordt
    niet meer volledig (incl. de 25%-consistentiecheck) uitgevoerd en weer weggegooid als de
    polygon-contour toch al wint — alleen `_hoofgevels(dos)` (nodig voor dakzijde-oriëntatie).
  - **Bewust niet gefixt**: contour wordt per bouwlaag berekend ook al gebruikt de renderer alleen
    de grootste (verwaarloosbare kosten; assemble.py hoort geometrie op te slaan, niet te kiezen wélke
    bouwlaag de render straks gebruikt — dat is een presentatiekeuze van `gebouw_svg.py`); en de
    "grootste-bouwlaag-als-footprint-proxy"-heuristiek staat op twee plekken (verschillende
    invoervormen — een schaalgetal in `assemble.py` vs. een `VloerInfo`-object in `gebouw_svg.py` —
    een gedeelde helper zou de twee modules onnodig aan elkaar koppelen voor een kleine heuristiek).
  768/768 tests groen. Twee losse commits: bugfix/robuustheid (assemble.py + geometry) en
  gebouw_svg.py-opschoning, beide op deze branch.

## Notes
- **Val niet in dezelfde kuil**: controleer bij het starten van een taak op een bestaande feature-
  branch altijd `git diff --stat <lokale-tip> origin/main -- <bestanden>` vóórdat je erop voortbouwt.
  Een lokale branch kan stiekem stale zijn t.o.v. wat er via een PR gemerged is.
- `python3` bestaat niet in de Git-Bash-omgeving hier (Windows Store-alias-foutmelding) — dat is
  bekende, in `STATE.md`/taak 002 vastgelegde technische schuld, geen nieuw probleem van deze taak.
  Tests zijn geverifieerd via `python tests/run_tests.py` in PowerShell (763/763 groen).
- Kalibratie-aanname (uniforme pixel→meter-schaal x/y) is gevalideerd tegen precies één echte export;
  bij de eerstvolgende echte MagicPlan-opname die via de API-route loopt: controleer de gerenderde
  contour tegen de werkelijke plattegrond voordat je 'm blind vertrouwt.
