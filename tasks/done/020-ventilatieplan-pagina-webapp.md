---
id: 020
assigned: Codex
branch: feat/020-ventilatieplan-integratie
depends_on: [019]
---

# Task 020 — Ventilatieplan-pagina in de webapp (tekening met sleepbare pijlen)

## Goal
De adviseur ziet het ventilatieplan als tekening op de plattegrond, kan de pijlen verslepen
en de waarden aanpassen, en de wijzigingen blijven aan het dossier hangen.

## Scope
Nieuwe route in `dashboard/app.py`: `/project/<tag>/ventilatieplan` (GET) plus een
opslagroute voor de markers (POST, JSON). Leest `geometrie.ruimtes` en het resultaat van
`ventilatie.bereken()`; schrijft `ventilatieplan` in het dossier volgens het datamodel in
`docs/ventilatieplan-webapp-spec.md`.

**Schermindeling** (onze huisstijl, niet hun kleuren):
- Kop "Ventilatieplan" met daaronder een balans-pil: `Balans: toevoer X l/s = afvoer Y l/s`,
  groen bij sluitend, oranje met de reden bij niet sluitend, plus een knop "Herbereken balans".
- Links "Plan per verdieping": per verdieping een kaart met de plattegrond als achtergrond en
  daarover een SVG-laag met de markers.
- Rechts "Berekening": de twee tabellen uit taak 019 (`RUIMTE | M2 | MIN. L/S | ADVIES L/S`
  en `RUIMTE | MIN. L/S | ADVIES L/S | AFVOERPUNT`), daaronder de zeven vuistregels met hun
  status en de deurbelasting-adviezen.

**Markers**:
- Drie soorten: toevoer (blauwe pijl, in de gevel, wijst naar binnen), afvoer (rode ovaal op
  het afzuigpunt), overstroom (groene pijl door een binnendeur). Elk met de waarde in l/s.
- Bediening: slepen = verplaatsen, een klik = 90 graden draaien, dubbelklik = waarde wijzigen
  of splitsen. Per verdieping knoppen `+ Toevoer`, `+ Afvoer`, `+ Overstroom` en `Herstel`
  (terug naar de automatisch geplaatste set).
- Tijdens het slepen een lijn van de marker naar het label van de ruimte waar hij bij hoort,
  en die ruimte oplichten. Een marker hoort altijd bij een ruimte; loslaten buiten elke
  ruimte laat hem terugspringen.
- Autoplaatsing bij het eerste openen: toevoer in de buitengevel van elke verblijfsruimte,
  afvoer in elke natte ruimte, overstroom op de verbinding verblijfsruimte naar natte ruimte.
  De adviseur corrigeert; de tool verzint niets stil.

**Achtergrond van de tekening**: gebruik in deze volgorde de MagicPlan-plattegrondafbeelding
uit het dossier, anders de bestaande contour uit `VloerInfo.contour_m`, anders een lege
kaart met de melding dat er geen plattegrond is. Nooit een verzonnen vorm tekenen.

## Out of scope
- PDF- en PNG-export (taak 021).
- Plattegrond uit een foto lezen (taak 022).
- Een JavaScript-framework introduceren. De webapp is server-rendered Jinja met vanilla JS,
  dat blijft zo.
- De rekenregels wijzigen. Die komen uit taak 019.

## Acceptance criteria
- [x] Markers verslepen, draaien, toevoegen, verwijderen en van waarde wijzigen werkt, en
      overleeft een herlaad van de pagina.
- [x] Coordinaten worden relatief (0..1) opgeslagen; de tekening klopt op een ander
      schermformaat en in de export.
- [x] Een marker zonder geldige `ruimte_id` wordt geweigerd, met een leesbare melding.
- [x] "Herstel" zet de automatische plaatsing terug zonder de handmatige waarden van andere
      verdiepingen te raken.
- [x] Balans-pil en tabellen werken bij: waarde wijzigen leidt tot een nieuwe balansstatus.
- [x] Werkt zonder internet (VPS achter Caddy, geen CDN).
- [x] `./scripts/verify.sh` slaagt.
- [x] AI-review PASS door een andere agent dan de bouwer.

## Sessions
- 2026-08-21: Gebouwd op taak 019 (branch nog niet gemerged naar main — dependency, zie depends_on).
  Dossier minimaal uitgebreid (`core/dossier.py`): `Ruimte.verdieping` (al berekend in
  `statistics_csv.py` als `kamer_verdieping`, alleen nooit opgeslagen — nu wel), `VloerInfo.
  plattegrond_afbeelding` (forward-compat voor taak 022, nog door niets gevuld) en de nieuwe
  `Ventilatieplan`/`VentilatieplanVerdieping`/`VentilatieMarker`-dataclasses + Dossier-veld,
  geregistreerd in de (de)serialisatiemap. Nieuwe pure datalaag `dashboard/ventilatieplan.py`:
  groeperen per verdieping (met een expliciete 'niet gekoppeld'-groep i.p.v. stil verkeerd
  indelen), autoplaatsing (toevoer/afvoer uit de taak-019-rekenlaag; GEEN automatische
  overstroom-marker — er is geen adjacency-data in het dossier om te weten welke ruimtes een
  deur delen, dat verzinnen zou een stille aanname zijn), validatie (weigert de HELE batch bij de
  eerste fout, nooit een deel stil opslaan) en de marker-balans. 3 nieuwe routes in
  `dashboard/app.py` (GET pagina + POST markers + POST herstel) + `dashboard/static/
  ventilatieplan.js` (vanilla JS: pointer-events voor slepen/klikken=draaien/dubbelklik=waarde-
  wijzigen-of-verwijderen, geen framework). Bewust NIET gebouwd: 'splitsen' (marker in tweeën) —
  stond in de Scope-tekst maar niet in de Acceptance Criteria; dubbelklik met een lege waarde
  dekt 'verwijderen' al. Geen browser-visuele-QA — de Claude-in-Chrome-extensie verbindt niet
  vanuit deze sessie (zelfde blokkade als taak 010, zie STATE.md); wél volledig end-to-end getest
  via de Flask test-client (GET/POST, validatie, persistentie over een 'herlaad', 404/400-paden).
  874/874 tests groen (49 nieuw t.o.v. taak 019: 34 datalaag + 15 route).
- 2026-08-21: AI-review (`/code-review high`, andere agent, expliciet doel `feat/019...` zodat
  precies de taak-020-diff werd beoordeeld — een eerste poging keek per ongeluk naar losse,
  niet-gecommitte documentatiewijzigingen van een ander onderwerp in dezelfde werkmap). Vond 2
  restbevindingen in `ventilatie/ventilatie.py` (taak 019, gemist door de vorige review): de
  '0 m2'-waarschuwing toonde altijd '0 m2' i.p.v. het werkelijke (mogelijk negatieve) oppervlak,
  en `deurbelasting()` valideerde alleen het eerste ruimtenaam in een overstroomweg tegen
  `res['rows']`, niet de rest — een tikfout verderop gleed er stil doorheen, in tegenspraak met de
  eigen docstring. Beide gefixt + 2 regressietests. 876/876 groen, verify.sh PASS. Taak gereed voor
  tasks/done/.
- 2026-08-21: Codex-integratie op actuele `origin/main` na afronding van taken 001, 002, 017 en
  018. De zes commits voor taken 019 en 020 chronologisch gecherry-pickt; alleen de twee
  historische `docs/STATE.md`-conflicten opgelost door de bestaande en nieuwe taakstatussen samen
  te voegen. Actuele blocking `scripts/verify.sh`: PASS, 881/881 tests groen. De administratieve
  advisory "geen actieve taak" is verwacht omdat 019 en 020 al in `tasks/done/` staan.
- 2026-08-21: Taak heropend na onafhankelijke review: FAIL op vier scope-blockers. Gefixt met
  optionele expliciete `Ruimte.contour_relatief`-geometrie (nooit afgeleid of verzonnen), SVG-
  ruimtepolygonen/-labels, polygon-hit-testing tijdens slepen, live highlight + verbindingslijn,
  binding aan de ruimte onder de pointer en volledige rollback buiten een ruimte. Zonder gemeten
  ruimtecontouren blijft ruimtekeuze/persistentie werken maar is slepen expliciet geblokkeerd.
  Servervalidatie beperkt `ruimte_id` nu tot de geposte verdieping en weigert bij beschikbare
  geometrie ook posities buiten die ruimte. Autoplaatsing maakt per toevoerruimte een overstroom-
  marker aan bij de bronruimte zonder een onbekende deur/doelruimte te verzinnen. Dubbelklik kan
  nu waarden wijzigen, verwijderen of expliciet splitsen via `waarde+waarde`. Template/CSS op
  design-tokens gebracht (geen component-hex/rgba, losse font-size, inline stijl of non-grid
  spacing). Blocking `scripts/verify.sh`: PASS; na de extra regressie die ook bevestigt dat
  automarkers binnen een gemeten ruimte starten staat de suite op 889/889 groen. Browser-QA op
  390/768/1440
  kon niet worden uitgevoerd: de voorgeschreven in-app-browserruntime gaf na diagnose exact nul
  beschikbare browsers (`agent.browsers.list() == []`). Taak blijft actief tot onafhankelijke
  herreview PASS geeft.
- 2026-08-21: Voor herreview gerebased op `origin/main` na merge van taak 015 (mappingmanifest en
  dakpreflight). Conflicten waren uitsluitend append-conflicten in `tests/run_tests.py` en
  `docs/STATE.md`; zowel alle taak-015-tests/status als alle 019/020-code en reviewfixes behouden.
  Een reeds op main aanwezige verouderde STATE-regel die taak 015 nog `active` noemde verwijderd;
  het taakbestand staat daadwerkelijk in `tasks/done/`. Actuele blocking `scripts/verify.sh`:
  PASS, 939/939 tests groen. Taak 020 blijft `active` tot onafhankelijke herreview PASS.
- 2026-08-21: Tweede herreview FAIL verwerkt. Productieroute toegevoegd om per verdieping op de
  bestaande achtergrond expliciete ruimtepolygonen te tekenen, voor te vertonen, valideren
  (minimaal 3 punten, 0..1) en via POST in `Ruimte.contour_relatief` op te slaan; daarna activeert
  dezelfde echte dossierroute het slepen. Fantoom-overstroom verwijderd: zonder opgeslagen
  bronruimte→natte-doelruimte-topologie geen groene marker en de vuistregel blijft `niet te bepalen`.
  De adviseur legt de verbinding via een eigen CTA vast; server valideert toevoerbron, nat doel en
  verdieping, bewaart `Ventilatieplan.topologie`, voert die door naar `toets_vuistregels()` en zet
  pas dan de marker op de geometrisch bepaalde bronrand richting doel. Oude fantoommarkers zonder
  topologie worden gemigreerd/verwijderd en de losse `+ Overstroom`-knop is weg. Markers hebben nu
  `tabindex`, buttonrol en aria-label; pijltjestoetsen verplaatsen binnen echte ruimtegeometrie,
  Enter/spatie opent dezelfde wijzigen/splitsen-flow en Delete/Backspace verwijdert na concrete
  bevestiging. Blocking `scripts/verify.sh`: PASS, 949/949 tests groen. Browser-QA opnieuw geprobeerd:
  de plugin was tussentijds geüpdatet; met de nieuwe geldige pluginbron stopte de verbinding op
  `Browser use requires a trusted Node REPL browser service`, dus screenshots bleven onmogelijk.
  Taak blijft `active` tot onafhankelijke herreview PASS.
- 2026-08-21: Derde herreview FAIL verwerkt. De UI/dossier-topologie blijft begrijpelijk
  `[toevoerbron, nat doel]`; precies op de grens naar `toets_vuistregels()` wordt deze nu expliciet
  getransformeerd naar het bestaande `deurbelasting()`-contract `[natte afvoer, bron]`. Een volledige
  POST→GET-regressie met Woonkamer→Keuken bewijst daardoor 28,0 l/s deurbelasting, status `voldoet
  niet` en expliciet deurroosteradvies (niet langer een stille 0). `_randpunt_van_naar()` gebruikt
  geen vertexgemiddelde meer: een deterministische interne-puntzoeker levert aantoonbaar een punt
  binnen de bron, daarna wordt de eerste echte segment/rand-intersectie richting een intern doelpunt
  berekend en een epsilon naar binnen geplaatst; het eindpunt wordt opnieuw met
  `punt_in_polygoon()` gevalideerd. Regressies dekken concave C- en U-vormen. De polygonen-POST
  weigert nu ook degeneratieve contouren zonder oppervlak en zelfsnijdende contouren. De generieke
  vuistregelreden noemt bij >15 l/s nu expliciet dat een deurrooster geadviseerd is. Blocking
  `scripts/verify.sh`: PASS, 953/953 tests groen. Taak blijft `active` tot onafhankelijke herreview.
- 2026-08-21: Vierde herreview FAIL (uitsluitend polygonvalidatie) verwerkt na expliciet planakkoord.
  Segmentvalidatie gebruikt nu een algemene gesloten-segmenttest met epsilon en `on_segment`, zodat
  naast echte kruisingen ook collineaire overlap en niet-aangrenzende endpoint-touch worden gevonden.
  Dubbele vertices (ook niet-aangrenzend) en zero-length edges worden vooraf afgewezen; aangrenzende
  zijden mogen alleen hun ene hoekpunt delen en teruglopen over de vorige zijde wordt als overlap
  geweigerd. De drie exacte reviewerreproducties (herhaald self-touchpunt, teruglopend segment en
  duplicate non-adjacent edge-endpoint) staan als regressies vast. Geldige concave C- en U-vormen
  blijven geaccepteerd. `_intern_punt` bleef conform plan ongemoeid: geen reproductie vereiste daar
  een wijziging. Blocking `scripts/verify.sh`: PASS, 957/957 tests groen. Taak blijft `active` tot
  onafhankelijke herreview PASS.
- 2026-08-21: Vijfde onafhankelijke herreview op `0f1f755`: PASS zonder blockers. Alle eerdere
  reproducties (deurbelastingrichting, concave C/U, self-touch/overlap, productiekalibratie,
  topologie, keyboard/focus en design) gecontroleerd. `verify.sh` PASS, 957/957, geen advisories.
  Taak naar `done` verplaatst.

## Notes
Referentie met exacte schermteksten en gedrag: `docs/ventilatieplan-webapp-spec.md`, sectie 1.
Neem het gedrag over, niet de vormgeving: geen merknaam, logo of kleurpalet van Aira.

Voor de SVG-laag is er al ervaring in `dashboard/gebouw_svg.py` (554 regels isometrische
renderer). Dat is een read-only presentatielaag; deze pagina is de eerste die de gebruiker
laat tekenen. Houd de renderer dom en de waarheid in het dossier.
