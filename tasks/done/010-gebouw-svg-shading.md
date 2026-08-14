---
id: 010
assigned: claude
branch: feat/gebouw-svg-shading
depends_on: [007]
---

<!-- De map ís de status: backlog/ ready/ active/ done/. Geen status-veld hier. -->

# Task 010 — Richtingsafhankelijke shading + grondschaduw (visuele stijl-slag, stap 1)

## Goal
Aanleiding: de isometrische tekeningen (gebouwoverzicht + de drie dak-wizard-previews) waren
volledig plat gekleurd — elk vlak dezelfde tint, alleen onderscheiden door een rand. De gebruiker
wil een kwaliteit die aanvoelt als Inbrix, met het gemak van de bestaande MagicPlan-scan (taak 007)
als basis. Eerder in het gesprek is bewust gekozen voor **SVG uitbouwen** i.p.v. een 3D-library
(Three.js): geen nieuwe dependency, en de tekening blijft direct bruikbaar als vector in het
Word/PDF-isolatieplan. Deze taak is de eerste, in scope begrensde stap van die stijl-slag:
richtingsafhankelijke helderheid ("shading") + een zachte grondschaduw. Geen kleurenpalet-
wijziging, geen interactieve rotatie — dat blijft toekomstig werk.

## Scope
- `dashboard/gebouw_svg.py`: nieuwe `_shade(points)` — helderheidsfactor uit de vlaknormaal
  (3D cross-product van de eerste twee randen) t.o.v. een vaste 'zon'-richting linksvoor-boven
  (`_ZON = (-0.25, 0.85, -0.45)`), toegepast als CSS `filter="brightness(...)"` op elk `<polygon>`.
  Werkt bovenop de BESTAANDE kleurtokens (`var(--info-bg)` etc.) — geen hex-waarden geïntroduceerd,
  blijft dus vanzelf correct in licht/donker thema (`docs/design-system.md`: "uitsluitend tokens").
  `bovenzijde-contour` (de platte dakbasis uit de MagicPlan-contour, taak 007) krijgt altijd de
  vaste helderste tint — de winding van die specifieke polygon volgt de externe contourdata en is
  daarom niet betrouwbaar genoeg om de normaal geometrisch te vertrouwen.
- Zachte grondschaduw: een geblurde ellips (`feGaussianBlur`) onder de voetafdruk, op basis van de
  geprojecteerde grondvlak-punten (`y == 0`). Kleur/dekking via bestaande token (`C_INK`) +
  `fill-opacity`, geen nieuwe kleur.
- `dashboard/static/isometrie.js` (de drie dak-wizard-previews): zelfde `_ZON`/shading-formule
  1-op-1 overgezet naar JS (`shade()`), toegepast op elk vlak in `draw()`. Houdt de invoer-previews
  visueel consistent met het definitieve gebouwoverzicht.

## Out of scope
- Geen kleurenpalet-wijziging (tokens blijven exact zoals ze waren).
- Geen interactieve rotatie/3D — blijft statische isometrie (nodig voor Word/PDF-inbedding).
- Het dak volgt nog steeds de bounding-box i.p.v. de echte polygon-vorm (taak 007-scope-grens,
  ongewijzigd).
- Geen visuele QA in een echte browser uitgevoerd — de Claude-in-Chrome-extensie verbond niet
  vanuit deze sessie (zie Notes). Geverifieerd via directe numerieke/geometrische controle i.p.v.
  een screenshot.

## Acceptance criteria
- [x] Elk vlaktype (gevel/dakvlak/dakkapel/contourmuur/platte dakbasis) krijgt een
      richtingsafhankelijke `brightness()`-filter, zonder nieuwe kleurwaarden.
- [x] Zelfde shading-logica in `isometrie.js`, numeriek geverifieerd tegen de Python-versie
      (identieke uitkomsten voor dezelfde geometrie).
- [x] Zachte grondschaduw onder het gebouwoverzicht.
- [x] `python tests/run_tests.py` blijft groen (772/772 — geen nieuwe assertie op exacte
      `filter`-waarden, dat zou de tests te veel aan de gekozen lichtrichting vastklinken; wel
      bestaande structuur-/XML-validiteitstests ongewijzigd geslaagd).
- [x] `./scripts/verify.sh` slaagt.
- [x] AI-review PASS door een andere agent dan de bouwer (`/code-review high`, zie Sessions).

## Sessions
- 2026-08-14 (claude): shading-formule ontworpen als vlak-normaal (3D cross-product) · vaste
  lichtrichting, i.p.v. per-`kind`-string hardcoded waarden — werkt daardoor automatisch correct
  voor élk vlaktype (ook de willekeurige polygon-contourmuren uit taak 007) zonder per geval een
  aparte tabel te onderhouden. Winding-consistentie (nodig voor een correcte 'naar buiten wijzende'
  normaal) geverifieerd door de daadwerkelijke geproduceerde `brightness()`-waarden numeriek uit te
  printen voor de rechthoek-box (voor > links > rechts > achter, exact zoals verwacht), de
  L-vormige contour uit taak 007, en dakkapel-vlakken — geen enkele onverwacht omgekeerde/negatieve
  waarde. De `isometrie.js`-poort apart doorgerekend via `node -e` voor alle vier previewvormen
  (plat/zadeldak-front/achter/kopgevels/dakkapel) en 1-op-1 vergeleken met de Python-uitkomsten
  voor dezelfde geometrie — identiek.
  Tussendoor per ongeluk op `main` beginnen te werken i.p.v. een eigen branch (na de VPS-deploy-
  stap niet teruggeschakeld) — hersteld door de wijziging te stashen, op de juiste branch te
  zetten en terug te poppen; geen wijzigingen verloren, wel een expliciete les voor mezelf: na een
  `git checkout main` altijd eerst `git branch --show-current` checken vóór nieuw werk.
  Geen browser-visuele-QA gedaan: de Claude-in-Chrome-extensie verbond niet (zelfde probleem als
  eerder in het gesprek). Geverifieerd via numerieke normaal-/shading-uitkomsten i.p.v. een
  screenshot — Renze: bekijk het gebouwoverzicht in de echte webapp voor het definitieve oordeel.
- 2026-08-14 (claude), vervolg: `/code-review high` vond 2 ECHTE bugs (geen ander-bestandencluster
  deze keer):
  1. `_shade()` leest de vlaknormaal uit de eerste twee randen zonder de omlooprichting van de
     broncontour te kennen — een MagicPlan-contour die met de klok mee i.p.v. tegen de klok in is
     aangeleverd (externe data, niet gegarandeerd) gaf daardoor de PRECIES OMGEKEERDE schaduw voor
     fysiek hetzelfde gebouw. Gereproduceerd (zelfde rechthoek CW vs CCW gaf shade 0.85/0.99 vs
     0.95/0.81) en gefixt: `_muurvlakken` canoniseert nu de omlooprichting van elk vlak vóórdat het
     de punten opbouwt (`teken == -1` -> punten omwisselen), zodat `_shade()` altijd een consistent
     gewonden vlak krijgt, ongeacht de bronvolgorde. Regressietest toegevoegd (dezelfde rechthoek
     CW/CCW moet identieke shades geven).
  2. De grondschaduw-ellips gebruikte `C_INK` (`var(--ink)`) — bijna zwart in licht thema, maar
     bijna WIT in donker thema (`app.css`), dus een lichtgevende halo i.p.v. een schaduw. Gefixt
     naar een vast `fill="black"`, dezelfde conventie als de bestaande `--shadow`/`--shadow-sm`-
     tokens in `app.css` die zelf ook in beide thema's `rgba(0,0,0,...)` blijven — een schaduw
     hoort niet met het thema mee te draaien.
  773/773 tests groen (772 + 1 nieuwe regressietest).

## Notes
- Vervolgstappen voor de stijl-slag (niet in deze taak): dak op de echte polygon-vorm i.p.v. de
  bounding-box; eventueel subtielere kleurverlopen per vlak (gradient i.p.v. platte brightness);
  visuele QA zodra de browserkoppeling weer werkt.
