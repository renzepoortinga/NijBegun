---
id: 006
assigned: codex
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
- Expliciete gebruikersuitbreiding (2026-08-14): ook het vrije 9-vlakken-
  vangnet in "Dak toevoegen" krijgt een isometrische live indicatie. De
  opgeslagen m² en serverlogica blijven ongewijzigd; zonder vaste vorm kan
  deze preview alleen indicatief zijn.

## Out of scope
- Gevels blijven uitsluitend via MagicPlan binnenkomen — geen nieuwe
  parametrische gevel-invoerweg.
- Geen wijziging aan de maatvaste taak-005-invoerwizards zelf; alleen het
  destijds bewust uitgezonderde vrije 9-vlakken-vangnet wordt gelijkgetrokken.
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
- 2026-08-14 (Codex, Builder): taak geclaimd op
  `feat/isometrisch-gebouwoverzicht`. `gebouw_svg()` vervangen door een
  dependencyvrije isometrische projectie met footprint-afleiding uit vier
  benoemde gevels, expliciete fallback bij ontbrekende/inconsistente maten,
  exacte en als zodanig gemarkeerde legacy-dakrendering en dakkapel-
  moederdakrelaties. Op expliciet verzoek ook de vrije 9-vlakken-dakpreview
  van kompas naar isometrische indicatie omgezet. 746/746 tests, JS-syntax en
  `git diff --check` groen. Browser-QA kon niet starten omdat geen browser aan
  de sessie gekoppeld was; geen alternatieve browserlaag gebruikt.
- 2026-08-14 (Codex, Builder, reviewfix): eerste onafhankelijke review FAIL
  verwerkt. Elk dakvlak wordt nu afzonderlijk vanuit zijn kompasvector en
  eigen hellingshoek geprojecteerd (ook vierzijdig en asymmetrisch); dak- en
  dakkapelpolygonen dragen id/m²/oriëntatie; `<title>` staat geldig binnen
  de polygon. Dakkapellen worden geometrisch vanuit het gekozen moederdak
  geplaatst, ook op de tegenoverliggende of gedraaide zijde. Nieuwe
  regressies controleren vier dakrichtingen, eigen hoeken en wisselende
  moederdakpositie. 749/749 tests, JS-syntax en diff-check groen.
- 2026-08-14 (Codex, Builder, reviewfix 2): herreview-FAIL voor het verschil
  tussen volledige overspanning (plat/lessenaar) en goot-tot-nok-run
  (zadeldak) hersteld. Platte en enkelvoudige hellende vlakken liggen nu
  tussen beide footprint-randen; zadeldakparen blijven naar de centrale nok
  lopen. Bounds-regressies toegevoegd. 751/751 tests en diff-check groen.

## Notes
- Zie taak 005 se Notes voor de Inbrix-referentie en marktonderzoek-pointer.
- Bij het kiezen van de exacte veldnamen in taak 005: controleer dat ze hier
  bruikbaar zijn vóórdat taak 005 wordt gemerged, anders moet deze taak
  eerst een dossier-migratie/hernoeming doen.
