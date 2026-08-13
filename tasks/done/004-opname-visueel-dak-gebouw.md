---
id: 004
assigned: claude
branch: feat/opname-visueel-dak-gebouw
depends_on: []
---

<!-- De map ís de status: backlog/ ready/ active/ done/. Geen status-veld hier. -->

# Task 004 — Visuele laag voor dak/dakkapel + gebouwoverzicht in de opname-editor

## Goal
De opname-editor toont dak, gevels en dakkapellen nu puur als formuliervelden — je ziet
nooit een tekening. Inbrix (concurrent, onderzocht via hun publieke handleidingvideo's)
laat wél een live wireframe zien bij dak-invoer en een lettergelabelde dakkapel-module.
Renze's klacht: "ik zie de dakkapel niet, ik zie het dak niet." Doel: een visuele laag
toevoegen zonder de architectuur te veranderen (MagicPlan blijft de bron voor gevels).

## Scope
- Nieuw `dashboard/gebouw_svg.py`: `gebouw_svg(dos)` — read-only overzichtstekening
  (compass-huis + dakstrook) van wat al in het dossier staat, getoond boven de
  "Gebouw"-kaart in de opname-editor.
- Live SVG-wireframe (client-side, oninput) naast de 3 bestaande dak-toevoegvormen
  (plat / zadeldak-driehoek / 9-geometrieën), ter vervanging van de tekst-only
  `dakPrev()`-preview.
- Nieuwe stap "Dakkapel toevoegen" (bestaat nog niet): formulier + wireframe + route
  `opname_dakkapel(tag)` die `core/geometry.py:dakkapel_vlakken()` gebruikt, 3
  SchilDelen aanmaakt (voorvlak/2 wangen/plat dakje) en het moederdakvlak verkleint.
- Tests in `tests/run_tests.py` naar het patroon van de bestaande
  ventilatieplan-svg-test + webapp-testclient-checks.

## Out of scope
- Geen nieuwe parametrische invoerweg voor gevels (geen "woonlaag-wizard"); gevels
  blijven via MagicPlan binnenkomen. De overzichtstekening is read-only.
- Geen wijziging aan de bestaande dak-POST-routes (`opname_dak_plat/driehoek/negen`) —
  de wireframe bij die stappen is puur client-side, geen serverroundtrip.
- Geen tekenmodule ("tekenen op plattegronden" à la Inbrix) — MagicPlan is en blijft
  onze tekenlaag.

## Acceptance criteria
- [x] `gebouw_svg(dos)` levert een geldige, well-formed SVG-string die de geladen
      gevels/daken van een dossier labelt (id + m² + oriëntatie)
- [x] De 3 dak-toevoegvormen tonen een live-meebewegende wireframe i.p.v. alleen tekst
- [x] Nieuwe dakkapel-stap: invoer levert 3 nieuwe SchilDelen op + het gekozen
      moederdakvlak wordt met het juiste gat-oppervlak verkleind (flag bij onbekende
      hellingshoek, zoals `dakkapel_vlakken()` al teruggeeft)
- [x] `python tests/run_tests.py` slaagt (bestaande 643 + nieuwe checks) — 733/733
- [x] `./scripts/verify.sh` slaagt
- [x] AI-review PASS door een andere agent dan de bouwer (zelfde model/leverancier
      toegestaan) — Codex, reviewronde 4

## Sessions
- 2026-08-13 (Claude/Sonnet 5): plan opgesteld + goedgekeurd (zie
  `.claude/plans/mellow-purring-sun.md` in de sessie), taak aangemaakt, branch
  `feat/opname-visueel-dak-gebouw` afgesplitst. Implementatie start.
- 2026-08-13 (Claude/Sonnet 5, vervolg): alle 3 onderdelen gebouwd —
  `dashboard/gebouw_svg.py` (gebouwoverzicht, ingeplugd in `opname()` +
  OPNAME_TMPL), live SVG-wireframes bij de 3 dak-toevoegvormen (plat/
  zadeldak-driehoek/9-geometrieën-kompas, JS-only, geen serverwijziging),
  en de nieuwe "Dakkapel toevoegen"-stap (SVG + `opname_dakkapel()`-route,
  gebruikt `core/geometry.dakkapel_vlakken()`, verkleint het moederdakvlak).
  Tests toegevoegd (`tests/run_tests.py`): gebouw-svg well-formed/labels,
  webapp-dakkapel-route (4 nieuwe vlakken + gat afgetrokken). Suite: 726/726
  groen. Onderweg een PRE-EXISTING crash in de testrunner gevonden en gefixt
  (regel ~799, verouderde test tegen `vabi/constructie_generate.write()` na
  taak 003's `VabiExportBlocked` — los van deze taak, in overleg met Renze
  meegenomen). Handmatig geverifieerd met headless Chrome-screenshots
  (gerenderde opname-pagina + auto-gevulde formulieren): gebouwoverzicht
  toont geladen gevels/dakvlakken/dakkapel correct gegroepeerd; alle 4
  wireframes (plat/zadeldak/kompas/dakkapel) renderen en updaten live bij
  invoer. `./scripts/verify.sh` PASS. Nog open: onafhankelijke AI-review
  (andere leverancier/model dan de bouwer) vóór de taak naar `tasks/done/`
  kan — dat is niet in deze sessie uitgevoerd.

- 2026-08-13 (Codex, onafhankelijke review): VERDICT FAIL. `python
  tests/run_tests.py` geeft 726/726 groen en `verify.sh` PASS met de bekende
  Python-advisory (`python3` ontbreekt in deze Windows/Git-Bash-omgeving; de
  suite is daarom apart met `python` gedraaid). Blokkerend gevonden: SVG kan
  ongeldige XML produceren doordat geëscapete ids/subtypes midden in een entity
  worden afgekapt; dakkapelroute accepteert platte daken/dakkapeldakjes als
  moederdak en niet-positieve maten; nieuwe SVG/CSS gebruikt losse kleuren,
  lettergroottes en spacing in strijd met `docs/design-system.md`; werkboom bevat
  daarnaast niet-taakgebonden proceswijzigingen die niet in taak-004-commit/PR
  horen. Reviewdetails gerapporteerd aan de bouwer/gebruiker.
- 2026-08-14 (Claude/Sonnet 5): alle 4 blokkerende punten uit de Codex-review
  verwerkt. (1) `dashboard/gebouw_svg.py`: id/subtype eerst AFKAPPEN, dan
  escapen (`_esc((s.id or "")[:20])` i.p.v. `_esc(s.id)[:20]`) — de oude volgorde
  kon een entity als `&amp;` middendoor knippen tot ongeldige XML; geverifieerd
  met een gestripte id die exact op de afkapgrens een `&`/`<` bevat. (2)
  `opname_dakkapel()`: server-side afgedwongen dat het moederdak een HELLEND
  vlak is (`hellingshoek > 0`, geen dakkapel-dakje) — ISSO 82.1 §8.2.1, een
  dakkapel breekt door een schuin vlak heen; plus `b/h/d <= 0` expliciet
  geweigerd (was alleen `not (b and h and d)`, negatieve waarden kwamen erdoor).
  Dropdown (`dakkapel_moeder_opts`) en foutmelding meegewerkt. 2 nieuwe tests.
  (3) Alle losse hex-kleuren in `gebouw_svg.py` + de 4 inline dak-wireframes in
  `dashboard/app.py` (óók de JS die attributen live bijwerkt) vervangen door de
  bestaande CSS-tokens uit `dashboard/static/app.css` (`var(--blue)`,
  `var(--ink)`, `var(--sub)`, `var(--tint)`, `var(--info-bg)`, `var(--warn-bg)`,
  `var(--orange)`, `var(--card)`) — dit was niet alleen een stijlpunt: de SVG's
  gebruikten toevallig exact de DARK-MODE-waarden van die tokens als vaste hex,
  dus braken in light mode en volgden niet mee bij een modus-wissel. Fractionele
  font-sizes (9.5/10.5/12.5) rondgezet naar de bestaande hele-getallen-schaal;
  `.dakwire`-padding/margin van 14px naar `var(--s4)` (16px, veelvoud van 4);
  dode `var(--card2,var(--card))`-fallback vervangen door `var(--tint)` (bestaand
  patroon, zie `.hint`). (4) Niet gecommit: bij het committen worden alleen de
  taak-004-bestanden gestaged (`dashboard/gebouw_svg.py`, `dashboard/app.py`,
  `dashboard/static/app.css`, `tests/run_tests.py`, `docs/STATE.md`, dit
  taakbestand) — de al vóór deze sessie aanwezige, losstaande wijzigingen in
  `AGENTS.md`/`agents/*.md`/`docs/decisions/0001-ai-project-os.md`/
  `tasks/TEMPLATE.md`/`tasks/ready/002-*.md` blijven ongemoeid in de werkboom en
  gaan niet mee in deze PR. Testsuite na de fixes: 728/728 groen (2 nieuwe
  edge-case-tests voor punt 2). `verify.sh` PASS. Tweede Codex-reviewronde volgt.

- 2026-08-14 (Codex, onafhankelijke reviewronde 2): VERDICT FAIL. De fixes
  voor XML-escaping en het weigeren van platte/dakkapel-moederdaken zijn
  bevestigd; `python tests/run_tests.py` geeft 728/728 groen en `verify.sh`
  PASS met opnieuw de bekende `python3`-advisory. Nog blokkerend: een
  dakkapelgat groter dan het moederdak wordt nog stil tot 0 m² afgeknipt;
  `NaN`/`Infinity` passeren `_f2` en de positieve-matencontrole; de nieuwe
  inline SVG's bevatten nog losse `font-size`-waarden in strijd met het
  bindende typografie-tokencontract. Ook staan de niet-taakgebonden
  proceswijzigingen nog in de diff tegen `main`; alleen selectief stagen bij
  een toekomstige commit maakt de huidige reviewdiff niet schoon. Details
  gerapporteerd aan bouwer/gebruiker.

- 2026-08-14 (Codex, onafhankelijke reviewronde 3): VERDICT FAIL. Bevestigd
  opgelost: `NaN`/`Infinity` worden geweigerd, SVG-typografie gebruikt nu
  gedeelde tokens, XML-escaping en moederdakfilters blijven correct. De
  feature staat in commit `58892ba`; de niet-taakgebonden proceswijzigingen
  zijn niet in die commit opgenomen, al blijven ze zichtbaar in de totale
  werkboomdiff. `python tests/run_tests.py`: 732/732 groen; `verify.sh` PASS
  met de bekende `python3`-advisory. Nog blokkerend: een dakkapelgat groter
  dan het moederdak wordt ondanks een luide flag wel opgeslagen en zet het
  canonieke moederdak op 0 m²; een gemanipuleerde `rekenzone` gaat nog door
  een onbeschermde `int(...)` en kan een HTTP 500 veroorzaken. Details
  gerapporteerd aan bouwer/gebruiker.
- 2026-08-14 (Claude/Sonnet 5): laatste 2 blokkerende punten uit reviewronde 3
  opgelost. (1) Dakkapelgat > moederdak: niet meer flaggen-en-toch-opslaan,
  maar HARD GEWEIGERD — de check verhuisd naar vóór het aanmaken van de 4
  SchilDelen; past de dakkapel niet, dan wordt er niets toegevoegd en niets
  aan het moederdak veranderd (consistent met de andere validaties in deze
  route: fysiek onmogelijke invoer weigeren, niet zwijgend/deels doorvoeren).
  (2) `rekenzone = int(f.get(...))` had geen bescherming tegen een niet-
  numerieke waarde (crafted POST buiten de dropdown om) → `ValueError` →
  HTTP 500; nu in try/except met terugval op `moeder.rekenzone or 1`, zelfde
  patroon als de bestaande `moeder_i`-parsing. Tests bijgewerkt (het
  "LUIDE FLAG"-scenario bestaat niet meer, vervangen door "geweigerd, geen
  nieuwe vlakken" + "moederdak ongewijzigd") en een nieuwe test voor de
  rekenzone-crash. Suite: 733/733 groen. `verify.sh` PASS. Gecommit
  bovenop `58892ba` (alleen taak-004-bestanden). Derde Codex-reviewronde
  op deze fix volgt.

- 2026-08-14 (Codex, onafhankelijke reviewronde 4): VERDICT PASS. Gericht
  gecontroleerd dat een dakkapelgat groter dan het moederdak atomair wordt
  geweigerd en dat een niet-numerieke rekenzone geen HTTP 500 meer geeft.
  Eerdere fixes voor XML-escaping, moederdakselectie, niet-finiete/negatieve
  maten en design-tokens blijven intact. `python tests/run_tests.py`:
  733/733 groen. `verify.sh`: PASS met uitsluitend de bekende advisory dat
  Git Bash hier geen `python3` vindt; daarom is de suite apart met `python`
  uitgevoerd. Geen resterende merge-blokkades voor taak 004.

- 2026-08-14 (Claude/Sonnet 5, Manager): afronding. Onafhankelijke review is
  PASS (reviewronde 4, Codex), alle acceptatiecriteria voldaan. Herbevestigd
  op de huidige branch: `python tests/run_tests.py` → 733/733 groen,
  `./scripts/verify.sh` → PASS (enige melding is de bekende `python3`-
  advisory uit taak 002, niet aan deze taak). De feature-commits staan al op
  `feat/opname-visueel-dak-gebouw` (`58892ba`, `c1d4d2b`); de werkboom bevat
  daarnaast nog ongecommitte, niet-taakgebonden wijzigingen in `AGENTS.md`/
  `agents/*.md`/`docs/decisions/0001-ai-project-os.md`/`tasks/TEMPLATE.md`/
  `tasks/ready/002-*.md` — bewust ongemoeid gelaten (zie sessie 2026-08-14
  hierboven), horen niet in deze taak/PR thuis. Taak naar `tasks/done/`
  verplaatst. Openstaand voor Renze: PR openen vanaf deze branch naar `main`
  en, indien gewenst, de losstaande proceswijzigingen apart beoordelen/
  committen.

## Notes
- Onderzoek Inbrix (`docs/dak-invoer-marktonderzoek.md`, 11-7) had alleen marketingtekst;
  deze sessie heeft de daadwerkelijke UI bekeken via hun publiek gehoste
  handleiding-mp4's (inbrix.nl/handleidingen — `data-handleiding-video`-attributen in de
  paginabron wijzen direct naar de bestanden). Bevestigd: isometrische wireframe met
  A/B/C/D-vlaklabels naast elk formulier; dakkapel/erker als iconen-picker met dezelfde
  wireframe + paars actief vlak.
- Rekenkundige basis bestaat al volledig in `core/geometry.py`; dit is uitsluitend een
  presentatielaag erbovenop.
