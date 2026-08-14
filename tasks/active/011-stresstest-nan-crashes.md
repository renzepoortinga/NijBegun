---
id: 011
assigned: claude
branch: fix/stresstest-nan-crashes
depends_on: [007, 010]
---

<!-- De map ís de status: backlog/ ready/ active/ done/. Geen status-veld hier. -->

# Task 011 — Stresstest van de contour-/gebouwoverzicht-pijplijn (NaN/Infinity/crashes)

## Goal
Na de shading-stap (taak 010) gevraagd om zelf te stresstesten i.p.v. te wachten op een volgende
review-ronde. Gerichte fuzz-/adversarial tests op `magicplan/assemble.py:_floor_contour_m`/
`geometry_from_plan` en `dashboard/gebouw_svg.py` (contour-extractie t/m gerenderde SVG) vonden
5 echte problemen — 300 willekeurige polygon/dak-combinaties op de renderer zelf gaven overigens
GEEN enkele fout, dus de kern (schoenveter-visibility, shading, painter's-order) staat stevig.

## Scope
`magicplan/assemble.py`:
1. `_floor_contour_m`: NaN/Infinity in `area_with_walls` werd niet gevangen (`nan <= 0` is False in
   Python -> glipte door de bestaande guard, `sqrt(nan/opp_px)` besmette daarna elke coördinaat met
   NaN). Expliciete `math.isfinite`-check toegevoegd.
2. `_floor_contour_m(None)` en niet-dict `fl` crashten (`AttributeError` op `.get`). Guard
   toegevoegd.
3. `image_map` of `coordinates` die geen lijst zijn (bv. een string uit kapotte JSON) crashten
   (`AttributeError`/iteratie over tekens). Type-checks toegevoegd.
4. `geometry_from_plan`: een negatieve vloeroppervlakte (`statistics.area < 0`, onbetrouwbare
   brondata) liet `math.sqrt()` een `ValueError` gooien bij de perimeter-benadering. Guard
   `footprint > 0` (vangt ook NaN, want `nan > 0` is False) i.p.v. de zwakkere `if footprint`.

`dashboard/gebouw_svg.py`:
5. `_polygon_footprint`: bewaakte alleen puntenaantal, niet of de coördinaten zelf eindig zijn.
   Nieuwe `_contour_geldig(contour)`-helper (tweede verdedigingslinie — punt 1 hierboven had de
   brontransformatie al gefixt, maar een handmatig bewerkt of anders aangeleverd dossier kan de
   contour ook buiten `assemble.py` om bevatten) — een NaN/Infinity-punt laat de polygon-footprint
   nu netjes terugvallen op de rechthoek-fallback i.p.v. NaN in de gerenderde SVG te zetten.

## Out of scope
- Geen wijziging aan de rest van `geometry_from_plan` (kozijnen/ruimtes) — alleen het specifieke
  perimeter/sqrt-pad dat crashte.
- Geen bredere input-validatie-laag voor de hele MagicPlan-API-respons — gericht op wat de
  stresstest daadwerkelijk liet crashen of NaN liet lekken, niet een uitputtende schema-validatie.

## Acceptance criteria
- [x] Gerichte stresstest (`_floor_contour_m` + `geometry_from_plan`): 200+ adversariële
      plan-structuren (None/verkeerde types/NaN/Infinity/negatieve waarden) — 0 crashes, 0
      niet-eindige waarden in het resultaat.
- [x] Gerichte stresstest (`gebouw_svg`): 300 willekeurige polygon-/dakcombinaties + 16 met de hand
      gekozen randgevallen (zelfdoorsnijdend, extreme schaal, negatieve coördinaten, bijna-verticaal
      dak, etc.) — 0 crashes, 0 niet-eindige SVG-coördinaten, 0 brightness-waarden buiten bereik.
- [x] Regressietests toegevoegd aan `tests/run_tests.py` voor alle 5 gevonden problemen.
- [x] `python tests/run_tests.py` groen (781/781).
- [x] `./scripts/verify.sh` slaagt.
- [ ] AI-review PASS door een andere agent dan de bouwer.

## Sessions
- 2026-08-14 (claude): twee losse fuzz-scripts geschreven (niet in de repo, scratchpad) — één tegen
  `gebouw_svg.py` (16 handmatige randgevallen + 300 random-seed-42 trials), één tegen
  `assemble.py` (16 handmatige adversariële `image_map`-structuren + 200 random-seed-7 trials met
  `None`/verkeerde types/NaN/Infinity gemengd in coördinaten en oppervlaktes). Eerste ronde vond
  2 issues in `gebouw_svg` (NaN/Infinity-coördinaten propageerden ongefilterd) en na het fixen
  daarvan 5 issues in `assemble.py` bij een dieper fuzz-niveau (malformed structuren, negatieve
  oppervlakte). Alle 5 gefixt, beide fuzz-runs daarna 0 fouten op respectievelijk 316 en 216+
  gevallen. Ontdekt tijdens het opzetten: per ongeluk wéér op `main` beginnen te werken i.p.v. een
  branch (derde keer deze sessie) — dit keer meteen bij het opmerken gecorrigeerd vóórdat er iets
  gecommit werd.
