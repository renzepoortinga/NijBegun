---
id: 006
assigned: Codex Builder
branch: feat/isometrisch-gebouwoverzicht
depends_on: [005]
---

<!-- De map ís de status: backlog/ ready/ active/ done/. Geen status-veld hier. -->

# Task 006 — Isometrisch gebouwoverzicht

## Goal
Vervolg op taak 005: het read-only gebouwoverzicht boven de "Gebouw"-kaart
in de opname-editor (`dashboard/gebouw_svg.py`) is nog steeds een schematisch
"WONING"-rechthoekje met kompaspositie-labelkaartjes, geen echte tekening.
Deze taak vervangt dat door een echte isometrische 3D-tekening van wat er in
het dossier staat, in dezelfde visuele taal als de taak-005-invoerwizards.

## Scope
- Kernprobleem: gevels die uit MagicPlan komen hebben géén breedte/lengte,
  alleen `oppervlakte_m2` + `orientatie` + `gevel_naam` (voor/achter/links/
  rechts) + project-brede `Opname.gevelhoogte_m`/`gebouwhoogte_m`. Oplossing:
  **footprint afleiden**, geen nieuwe invoerweg voor gevels (blijft binnen de
  bestaande grens uit taak 004 — MagicPlan blijft de bron voor gevels):
  - `breedte_voorgevel = m2_voor / gevelhoogte_m`,
    `diepte = m2_links / gevelhoogte_m`
  - Sanity: voor- en achtergevel-breedte moeten (nagenoeg) gelijk zijn —
    bouwt voort op de al bestaande dubbeltel-/onmogelijke-hoek-checks (zie
    CLAUDE.md-status 15-7); hergebruiken, niet dupliceren.
  - Ontbreekt `gevelhoogte_m`, of zijn de gevels inconsistent/onvolledig →
    **geen gegokte 3D-box**: terugvallen op een duidelijk gelabeld
    vereenvoudigd aanzicht (hergebruik van het bestaande "Nog geen
    gevels"-lege-state-patroon, uitgebreid met "kon geen 3D-vorm afleiden").
- `dashboard/gebouw_svg.py` vervangen (functienaam `gebouw_svg(dos)` blijft
  — enige call-site is `dashboard/app.py` + de bestaande SVG-validity/
  traceability-tests, dus minimale churn elders):
  - Footprint afleiden zoals boven; extrudeer naar een 3D-blok (hoogte =
    `gebouwhoogte_m`, anders `gevelhoogte_m`), teken als isometrische
    polygonen; elke gevel-face gelabeld/gekleurd naar bekend/onbekend Rc
    (zelfde `C_KNOWN`/`C_UNKNOWN`-logica als de huidige implementatie).
  - Dakvlakken bovenop de box: voor elementen mét de taak-005-velden
    (`breedte_m`/`diepte_m`) exacte reconstructie; voor legacy-dakvlakken
    zonder die velden, benader met footprint-breedte + `m2/breedte` als
    diepte-langs-helling, met een zichtbare "benaderd"-markering.
  - Dakkapel: plaatsen op de juiste dakvlak-face met de taak-005-velden.
  - De isometrische projectiewiskunde uit `dashboard/static/isometrie.js`
    (taak 005) wordt hier in Python herhaald (geen gedeelde runtime tussen
    server en browser) — dun houden, zelfde formule zodat overzicht en
    invoer-preview identiek ogen.
- Tests: vervang de huidige `gebouw_svg`-tests (geldige/well-formed SVG,
  element-ids traceerbaar) door equivalenten tegen de nieuwe isometrische
  output; nieuwe tests voor footprint-afleiding (happy path + fallback bij
  ontbrekende hoogte/inconsistente breedtes) + dakreconstructie met en
  zonder taak-005-velden + dakkapel-plaatsing.

## Out of scope
- Gevels blijven uitsluitend via MagicPlan binnenkomen — geen nieuwe
  parametrische gevel-invoerweg.
- Geen wijziging aan de taak-005-invoerwizards zelf (die staan al vast).
- Geen tekenmodule ("tekenen op plattegronden" à la Inbrix) — MagicPlan
  blijft de tekenlaag.

## Acceptance criteria
- [ ] `gebouw_svg(dos)` levert een geldige, well-formed isometrische
      SVG-tekening op (geen labelkaartjes-lay-out) die de geladen gevels/
      daken/dakkapellen van een dossier toont, met id/m²/oriëntatie
      herleidbaar in de markup
- [ ] Footprint wordt correct afgeleid uit de 4 gevelnamen + gevelhoogte,
      met een zichtbare, niet-gegokte fallback als dat niet kan
- [ ] Dakvlakken met taak-005-metadata renderen exact; legacy-dakvlakken
      zonder die metadata renderen benaderd én zichtbaar gemarkeerd als
      benadering
- [ ] Dakkapel wordt op de juiste dakvlak-face geplaatst
- [ ] Voldoet aan `docs/design-system.md` (zie taak 005 voor de exacte eisen)
- [ ] `python tests/run_tests.py` slaagt
- [ ] `./scripts/verify.sh` slaagt
- [ ] AI-review PASS door een andere agent dan de bouwer (zelfde model of
      leverancier toegestaan)

## Sessions
- 2026-08-14 (Claude/Sonnet 5, Manager): taak afgebakend samen met taak 005
  (zie dat taakbestand voor de volledige context/aanleiding). Deze taak kan
  pas starten nadat taak 005 gemerged is (de nieuwe `SchilDeel`-velden
  moeten bestaan).
- 2026-08-14 (Codex, Builder): `gebouw_svg` vervangen door een server-side
  isometrische projector met herleidbare gevel-, dak- en dakkapelvlakken.
  Een 3D-footprint vereist vier benoemde gevels en een positieve gevelhoogte;
  tegenoverliggende maten gebruiken dezelfde 25%-signaleringsgrens als de
  bestaande MagicPlan-dubbeltelcheck. Bij ontbrekende of inconsistente data
  volgt een gelabelde niet-3D fallback. De gevelbox stopt bij gevelhoogte en
  de nok gebruikt de expliciete gebouwhoogte; taak-005-metadata rendert exact,
  legacy-daken zijn zichtbaar `benaderd`, en dakkapellen volgen hun expliciete
  `moedervlak_id`. XML-escaping, footprint/fallback, exact/legacy-dak en
  dakkapelplaatsing zijn getest. `python tests/run_tests.py`: 742 PASS en 2
  bekende taak-002-omgevingsfouten (extern plan-json en lokaal config-adres);
  `verify.sh`: PASS met dezelfde Python-advisory; `py_compile` en
  `git diff --check`: PASS. Browser-QA was niet mogelijk omdat geen browser
  aan deze sessie verbonden was; responsive/darkmode/tokens statisch getoetst.

## Notes
- Zie taak 005 se Notes voor de Inbrix-referentie en marktonderzoek-pointer.
- Bij het kiezen van de exacte veldnamen in taak 005: controleer dat ze hier
  bruikbaar zijn vóórdat taak 005 wordt gemerged, anders moet deze taak
  eerst een dossier-migratie/hernoeming doen.
