---
id: 014
assigned:
branch:
depends_on: [015]
---

# Task 014 — Dakmigratie zonder dubbele legacyvlakken

## Goal
Zorgen dat de dakwizard een oud/importdak aantoonbaar vervangt of bewust aanvult, zonder dubbele Vabi-oppervlakte.

## Scope
- Reproduceer het Essenhage-patroon: generiek legacydak plus wizardvlakken.
- Gebruik bron-id/fingerprint en geometriegroep om correspondentie te bepalen; verwijder nooit op alleen naam of oppervlak.
- Ontwerp een expliciete vervang-/behoudkeuze met preview van oud en nieuw oppervlak.
- Maak vervanging atomisch en voeg regressietests toe voor toevoegen, wijzigen, annuleren en herimport.
- Migreer niet automatisch bij ambigu samengestelde/aanbouwgeometrie; toon dan een blokkade.

## Out of scope
- Nieuwe dakrekenformules.
- Zelf NTA 8800 rekenen.
- Productiedossiers zonder backup batchgewijs wijzigen.

## Acceptance criteria
- [x] Een wizarddak kan niet ongemerkt naast zijn legacyvoorganger worden geëxporteerd. Twee lagen:
      (1) de webapp verwijdert de parser-placeholder (`SchilDeel.bron == "magicplan-dak-fallback"`)
      automatisch zodra je via de dak-wizard een écht dakvlak toevoegt (`dashboard.app.
      _dak_fallback_opschonen`, aangeroepen in `opname_dak_plat/driehoek/negen`); (2) een harde
      VABI-preflight-poort (`vabi.preflight.assert_no_dubbel_dak_fallback`, gewired in alle vier
      export-entrypoints net als de bestaande kwaliteitsverklaring-poort) blokkeert de export als
      die placeholder toch ooit naast een ander dakvlak staat — dus ook via CLI/JSON-upload/tests,
      niet alleen de webapp-UI.
- [x] Aanbouw-/extra daken blijven afzonderlijk mogelijk. Ongewijzigd: de wizard blijft
      `dak1`/`dak2`/`dak3`... auto-nummeren; de bestaande "MOGELIJK DAK ONTBREEKT"-heuristiek
      (aanbouw/uitbouw-detectie op footprint-verschil) is niet aangeraakt.
- [x] Voor/na-oppervlak en verwijderde ids zijn controleerbaar. De flash-melding bij elke
      dak-wizard-route noemt nu zowel het/de verwijderde id('s) als de verwijderde m².
- [~] Vervanging vereist een aantoonbare bron-/vlakrelatie; ambiguïteit blokkeert automatische
      migratie. **Deels**: de automatische verwijdering raakt UITSLUITEND de ondubbelzinnig getagde
      parser-placeholder (nooit legacy-CSV-dakvlakken of eerder handmatig werk). Wat NIET is
      opgelost: als een dossier zowel legacy-CSV-dakvlakken (oude "Dakvlak 1/2/3"-route, vóór 23-7)
      ALS nieuwe wizard-dakvlakken bevat, wordt dat niet gedetecteerd/geblokkeerd als mogelijke
      dubbeling — dat is inherent ambigu (kunnen ook allebei legitiem aanbouw-daken zijn) en vereist
      een echte "dakwerkbank"-UI (voor/na-vergelijking, expliciete keuze) om goed op te lossen; hier
      bewust niet aan begonnen (te groot voor deze sessie, en niet de bug die live is aangetroffen).
- [x] Re-import overschrijft handmatig dakwerk niet stil — **voor dakvlakken**: een CSV-herimport
      (`opname_magicplan`) draagt nu alle `bron == "webapp-wizard"` schildelen over naar het nieuw
      geïmporteerde dossier vóórdat het wordt opgeslagen (CSV kan sowieso nooit dakdata leveren
      sinds de dak-velden op 23-7 uit MagicPlan zijn gehaald, dus dit kan nooit een echte
      MagicPlan-dakwaarde overschrijven). Andere handmatige gebouwboom-edits (bv. een Rc-override op
      een gevel) blijven bij een CSV-herimport wél volledig vervangen, zoals voorheen — dat is
      ongewijzigd gedrag, niet nieuw kapotgemaakt, maar ook niet opgelost door deze taak.
- [x] `./scripts/verify.sh` slaagt (797/799 Python-tests; de 2 restfalen zijn de bekende
      buiten-de-repo-omgevingsafhankelijkheden uit taak 002, niet aan dit werk gerelateerd).
- [x] AI-review PASS door een andere agent dan de bouwer. Twee rondes `/code-review high`; ronde 1
      vond 1 kritiek + 1 ongerelateerd punt (zie hieronder), ronde 2 (na fixes) vond nog eens 3
      echte punten — allemaal verwerkt (zie Sessions). Geen blockers meer over.

## Sessions
- 2026-08-15 (los gesprek van taak 013's ketenaudit) — user vroeg expliciet: "wat er met het
  Essenhage-dak moet gebeuren" volgens 5 stappen (identificeer legacyvlak, registreer
  wizardvlakken als vervanging, check aanbouw, verwijder pas dan het oude vlak, herexporteer en
  controleer). Root cause gevonden: het "legacydak" ís het footprint-fallback-dak dat
  `statistics_csv.build_dossier()` zelf aanmaakt zodra een CSV geen dakvelden heeft (normaal sinds
  dak op 23-7 uit MagicPlan is gehaald) — de dak-wizard-routes in `dashboard/app.py` controleerden
  nooit of zo'n placeholder al bestond voor ze een nieuw dakvlak toevoegden.
  Geïmplementeerd: `SchilDeel.bron`-veld (taak 015, scoped) + `_dak_fallback_opschonen()`-helper
  (webapp, automatische opschoning bij het toevoegen van een dakvlak) + harde VABI-preflight-poort
  `assert_no_dubbel_dak_fallback` (vangnet op elk exportpad) + CSV-herimport behoudt
  wizard-dakvlakken. 14 nieuwe regressietests (sectie "AC" in `tests/run_tests.py`), waaronder een
  bestaande test die (na de fix, terecht) een niet-opgeschoonde testopstelling bleek te hebben —
  gecorrigeerd. 797/799 groen (2 bekende omgevingsfalen).
- 2026-08-15 (zelfde gesprek, review-ronde 1) — `/code-review high` vond: (1) **kritiek**:
  `magicplan/extractor.py::_maak_dak()` (de hybride API+report-PDF-route, gebruikt door
  `magicplan/assemble.py`) zette de nieuwe `bron`-tag nooit → dossiers via dát pad omzeilden de
  hele fix. Gefixt: zelfde tag, 2 nieuwe tests. (2) een ongerelateerde bevinding
  (`form_push.py` mist de taak-012-SSL-fix) vastgelegd als taak 025 i.p.v. hier meegefixt.
  799/801 groen.
- 2026-08-15 (zelfde gesprek, review-ronde 2) — nieuwe `/code-review high` op de gefixte stand
  vond 3 verdere echte punten (van de 8 gemelde; de overige 5 zijn ofwel al expliciet
  gedocumenteerde bewuste scope-grenzen, ofwel pre-existente/losstaande efficiëntiepunten buiten
  scope): (1) **kritiek** — de hele bron-tag-aanpak is opt-in en dus blind voor dossiers die al
  op schijf stonden vóórdat dit veld bestond, WAARONDER het echte, live Essenhage-dossier dat
  deze taak veroorzaakte (bron=="" op zowel het oude als het nieuwe dakvlak). Gefixt: gedeelde
  `vabi.preflight.dak_fallback_schildelen()`-herkenning matcht nu ook op het legacy-signaal
  `id == "dak"` (uniek voor de twee footprint-fallback-paden; wizard/legacy-CSV-routes gebruiken
  nooit die kale id) — 3 nieuwe tests (AC7) bewijzen dit óók voor een volledig ongetagd dossier.
  (2) de JSON-dossier-upload-tak van `opname_magicplan` kreeg de wizard-dak-behoud-fix niet, alleen
  de CSV-tak — nu gedeeld over beide met id-gebaseerde dedup (2 nieuwe tests, AC8). (3) DRY:
  `_dak_fallback_opschonen` en `assert_no_dubbel_dak_fallback` herimplementeerden dezelfde
  herkenningslogica apart → nu één gedeelde `dak_fallback_schildelen()`-functie; de 3
  dak-wizard-routes herhaalden ook dezelfde flash-tekst-opbouw → nu `_dak_toegevoegd_melding()`.
  804/806 groen (2 bekende omgevingsfalen, ongewijzigd). `./scripts/verify.sh`: PASS.
- 2026-08-15 (zelfde gesprek, review-ronde 3) — nog een `/code-review high` op de ronde-2-fixes
  vond 3 punten: (1) **echt, mijn eigen over-correctie** — `_maak_dak()` tagde na ronde-1-fix ELK
  dakvlak als fallback, ook een écht handmatig ingevoerd `dak_oppervlak_m2`; gefixt door alleen de
  schatting (geen `handmatig`-veld) als fallback te taggen, net als de CSV-route al deed voor haar
  eigen 'direct ingevoerde m²'-pad. (2) `opname_dakkapel` voegt ook een `type="dak"`-vlak toe maar
  riep nooit de opschoning aan — bleek bij nader inzien GEEN kwestie van "ook opschonen": als het
  gekozen moederdak toevallig de placeholder was, is die na de dakkapel-correctie een bewust
  behouden, verkleind maar nog écht dakvlak — opschonen zou het gewoon weggooien. Fix: de moeder
  wordt in dat geval herclassificeerd (`bron` -> "magicplan-import") i.p.v. verwijderd. Dat botste
  eerst met het id=="dak"-legacy-signaal uit ronde 2 (die negeerde de herclassificatie) — opgelost
  door `dak_fallback_schildelen()` een expliciet gezette, niet-lege `bron` te laten winnen van het
  id-signaal. 3 nieuwe tests (AC9) dekken dit specifieke conflict. (3) een derde ongerelateerde
  SSL-bevinding (`magicplan/photos.py`, zelfde patroon) toegevoegd aan taak 025 i.p.v. hier
  meegefixt. 808/810 groen (2 bekende omgevingsfalen). `./scripts/verify.sh`: PASS. Geen verdere
  blockers gevonden in deze ronde — drie reviewrondes totaal, elke ronde kleiner en dichter bij
  alleen out-of-scope/pre-existente punten.

## Notes
Live audit 15-8-2026: Essenhage bevat 55,56 m² legacydak plus 2 × 28,71 m² schuine wizardvlakken.
Root cause (bevestigd deze sessie): het legacydak = `statistics_csv.py`'s eigen
footprint-fallback (`id="dak"`, ontstaat zodra een CSV geen dakvelden bevat — de norm sinds
23-7). Geen apart "legacy import"-pad nodig om te herkennen: de parser tagt 'm nu zelf.
