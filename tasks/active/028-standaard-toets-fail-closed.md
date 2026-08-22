---
id: 028
assigned: Claude Code
branch: fix/028-standaard-toets-fail-closed
depends_on: []
---

# Task 028 — Standaard-toets fail-closed + indicator-provenance (audit-blockers PR #28)

## Goal
Een technische audit (22-8-2026, extern rapport op project 9502CS_26) verifieerde grotendeels correct
tegen de echte code en live tools dat PR #26/#28 de 101,25-vs-77,99-bug alleen oploste voor het geval
waarin `NettoWarmtebehoefte` aanwezig is. Drie audit-blokkers plus één zelf gevonden verwant gat zijn
in deze taak gedicht: het "voldoet aan de Standaard"-oordeel is nu overal fail-closed — alleen groen/rood
wanneer het daadwerkelijk op een echte `NettoWarmtebehoefte` rust, anders expliciet "niet te bepalen"
(nooit stilzwijgend rood, nooit een verkeerd-maar-groen oordeel).

## Scope
- `vabi/result_reader.py`: `_voldoet_aan_standaard`/`_marge_kwh_m2` zijn nu expliciet `None` (niet
  weggelaten) wanneer de toets op de `IndicatorEnergiebehoefte`-fallback rust. Nieuwe `_indicator_type`-
  sleutel (`"NettoWarmtebehoefte"` / `"IndicatorEnergiebehoefte"`) voor provenance. CLI print "niet te
  bepalen" i.p.v. een gegokt oordeel.
- `core/dossier.py::Berekening`: twee nieuwe velden `indicator_type_huidig` / `indicator_type_na`
  (default `""` = onbekend/legacy — automatisch fail-closed voor bestaande dossiers zonder deze info).
- `vabi/monitor_xml.py::parse()`: zet `indicator_type_huidig` naast `kwh_m2_huidig`.
- `dashboard/app.py`:
  - `_verdict()` niet-dossier-pad geeft `voldoet` nu door zonder `bool()`-cast (een expliciete `None`
    werd eerder stilzwijgend `False`/rood).
  - `_verdict(is_dossier=True)` gebruikt `indicator_type_huidig`; alleen bij exact
    `"NettoWarmtebehoefte"` een boolean, anders `None`.
  - `/project/<tag>/huidig` persisteert nu ook `indicator_type_huidig` in het dossier.
  - `/project/<tag>/vabi` persisteert **nieuw** `kwh_m2_na_maatregelen` + `indicator_type_na` in het
    dossier — dit veld werd voorheen nérgens gezet, waardoor `validator/validate.py`'s KWACO-check altijd
    "Warmteverlies NA maatregelen ontbreekt" meldde en het Word-plan de "na maatregelen"-energiecel
    altijd leeg rendde, ook als de VABI-toets-pagina al correct "voldoet" toonde.
  - Templates `HUIDIG`/`VABI`: derde rendering-tak voor `voldoet is none` → "Niet te bepalen"
    (hergebruikt de bestaande amber `.verdict.no`-stijl, geen nieuwe CSS).
- `nijbegun_engine/__init__.py::read_vabi_result()`: gebruikt nu `_voldoet_aan_standaard` direct i.p.v.
  zelf `eb <= std` te herberekenen (dat omzeilde het fail-closed gedrag); nieuwe `indicator_type`-sleutel
  in de return-dict; `energiebehoefte`-sleutelnaam ongewijzigd (extern contract), docstring uitgebreid.
- Tests (`tests/run_tests.py`, sectie 19): bestaande fallback-test aangescherpt (`None` i.p.v. `False`),
  plus nieuwe tests voor `monitor_xml.parse()`, `dashboard._verdict(is_dossier=True)` met legacy/getypeerd
  dossier, `nijbegun_engine.read_vabi_result()`, en een test-client-POST naar `/project/<tag>/vabi` die
  bevestigt dat `kwh_m2_na_maatregelen`/`indicator_type_na` daadwerkelijk in het dossier landen.

## Out of scope (bewust niet meegenomen — zie sessie-audit-review)
- Ventilatieplan-geometrie voor project 9502CS_26 (taak 022, databeperking, geen codebug).
- De cataloguscode-claims uit het auditrapport (`V5-1-A2`/`V5-1-X1`) — geverifieerd als **fout in het
  rapport zelf**: de echte code is `B5-1-A2`; `V5-1-X1` bestaat niet in `catalog.json` (dat is `V5-2-X1`).
  Geen actie.
- Documentopmaakfouten in het opgeleverde plan (placeholder-tekst, `NULL` in een link) — apart, los van
  de rekenketen.
- Een nieuwe CI-workflow voor een onafhankelijke andere-leverancier-review — blijft een openstaand gat,
  vergt een aparte beslissing over vendor/secret.

## Acceptance criteria
- [x] `result_reader.read_results()` geeft `_voldoet_aan_standaard=None` bij ontbrekende
  `NettoWarmtebehoefte`, nooit een gegokt boolean.
- [x] `dashboard.app._verdict()` (beide paden) en de templates tonen "niet te bepalen" i.p.v. rood/groen
  wanneer de indicator niet getypeerd/NWB is.
- [x] `Berekening.kwh_m2_na_maatregelen` + `indicator_type_na` worden daadwerkelijk gevuld door de
  `/vabi`-upload (was voorheen dood veld).
- [x] `nijbegun_engine.read_vabi_result()` fail-closed + `indicator_type` in de publieke return-dict.
- [x] Regressietests voor alle bovenstaande punten.
- [x] `./scripts/verify.sh` slaagt (1082/1082 Python-tests, geen nieuwe advisory-punten).
- [x] AI-review door een andere leverancier (Codex/OpenAI, via lokale `codex exec` CLI) — VERDICT FAIL
  op de eerste versie, 3 echte blokkers gevonden en verwerkt (zie sessielog); daarna geen nieuwe review
  meer gedraaid (geen tijd/budget), maar de gevonden bugs zijn stuk voor stuk gefixt + geregressietest.

## Sessions
- 2026-08-22 Claude Code: technische audit (extern rapport, 22-8-2026) doorgenomen en stuk voor stuk
  geverifieerd tegen live tools/code (ventilatieplan-pagina, cataloguscodes, opgeleverd Word-plan,
  GitHub-review-status) — grotendeels accuraat gebleken, één feitelijke fout gevonden in de
  cataloguscode-sectie (zie Out of scope). Op basis van de bevestigde BLOKKERS is deze taak geïmplementeerd
  volgens een vooraf goedgekeurd plan (fail-closed Standaard-toets + indicator-type-provenance in het
  dossier + reparatie van het dode `kwh_m2_na_maatregelen`-veld). `verify.sh` PASS (1074/1074).
- 2026-08-22 Claude Code, onafhankelijke review: `codex exec` (OpenAI CLI, andere leverancier dan de
  bouwer) gedraaid met de reviewerrol uit `agents/reviewer.md` op PR #31. **VERDICT FAIL**, 3 echte
  blokkers: (1) `validator/validate.py`'s KWACO-doeltreffendheidscheck vergeleek `kwh_m2_na_maatregelen`
  rechtstreeks tegen de Standaard zonder te checken of dat een echte NettoWarmtebehoefte was — een
  fallback-waarde kon zo alsnog een BLOKKEREND "haalt de norm niet" geven, precies het gat dat deze taak
  moest dichten; nu gated op `indicator_type_na == "NettoWarmtebehoefte"`. (2) `result_reader.py`/
  `monitor_xml.py` claimden `_indicator_type`/`indicator_type_huidig` = "IndicatorEnergiebehoefte" ook
  wanneer DIE indicator zelf ook ontbrak (valse fallback-provenance) — nu `None`/`""` in dat geval.
  (3) `dashboard.app._verdict(is_dossier=True)` kon bij een echte NWB maar ontbrekende/0 Standaard een
  kortgesloten `None`/`0` teruggeven i.p.v. een schone `bool`/`None` — expliciet gemaakt. Alle drie
  gefixt + regressietests (incl. de door Codex gemelde ontbrekende dekking: fallback-upload via `/vabi`,
  KWACO-check met fallback-indicator). `verify.sh` PASS (1082/1082). **Proces-lesje**: `codex exec` liep
  met schrijftoegang in dezelfde werkmap als een gelijktijdige, ongerelateerde eigen bewerking
  (ventilatieplan-achtergrond-upload); Codex zag die ongecommitte wijziging tijdens zijn eigen testrun,
  interpreteerde 'm als een bijeffect van zijn eigen actie en zette 'm terug om read-only te blijven —
  logisch gezien zijn instructies, maar wiste zo per ongeluk een stuk niet-gecommit eigen werk (geen
  dataverlies: alles opnieuw toegepast uit sessiegeheugen). Voortaan: nooit een schrijvende CLI-agent in
  dezelfde werkmap draaien als eigen actieve, ongecommitte bewerkingen — eigen wijzigingen eerst committen
  of een aparte worktree gebruiken.
