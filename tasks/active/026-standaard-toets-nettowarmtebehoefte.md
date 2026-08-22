---
id: 026
assigned: Claude Code
branch: fix/026-standaard-toets-nettowarmtebehoefte
depends_on: []
---

# Task 026 — Standaard-toets vergelijkt de verkeerde VABI-indicator

## Goal
De Nij Begun-Standaardtoets (VABI-toets-pagina + KWACO-validator + advies-tekst) moet de netto
warmtebehoefte van de schil tegen de Standaard toetsen — niet de bredere energiebehoefte-indicator
die ook installaties meeweegt — zodat "voldoet aan de Standaard" klopt met wat Vabi/EPA-W écht
teruggeeft.

## Scope
- Gevonden op project 9502CS_26 (Meester Neuteboomstraat 26, Stadskanaal): de VABI-toets-pagina
  toonde "energiebehoefte 101,25 vs Standaard 84,0 -> voldoet niet", terwijl de eigen VABI-export
  van de gebruiker `<NettoWarmtebehoefte>77,99</NettoWarmtebehoefte>` bevat (77,99 <= 84 = voldoet).
  Bevestigd door SOBOLT ernaast te leggen (zelfde project): SOBOLT toetst "Isolatiestandaard 84" tegen
  "Netto warmtebehoefte incl. maatregelen 75,44" -> groen vinkje.
- `vabi/result_reader.py`: `NettoWarmtebehoefte` toegevoegd aan `KERN`; `_voldoet_aan_standaard`/
  `_marge_kwh_m2` gebruiken nu `NettoWarmtebehoefte` met fallback op `IndicatorEnergiebehoefte` voor
  oudere exports zonder dat veld; nieuwe sleutels `_toetswaarde`/`_toetswaarde_bron`.
- `vabi/monitor_xml.py`: `Berekening.kwh_m2_huidig` leest nu `NettoWarmtebehoefte` (met dezelfde
  fallback) i.p.v. altijd `IndicatorEnergiebehoefte` — dit voedt de KWACO-validator en fill_template.
- `dashboard/app.py`: `_verdict()` gebruikt `_toetswaarde`; UI-labels "energiebehoefte ... vs Standaard"
  hernoemd naar "netto warmtebehoefte ... vs Standaard" (Huidige staat + VABI-toets-pagina).
- `engine/advies_text.py` + `nijbegun_engine/__init__.py` (publieke SaaS-contract): zelfde
  voorkeursvolgorde NettoWarmtebehoefte > IndicatorEnergiebehoefte.
- Regressietest in `tests/run_tests.py` (test 19) met een fixture die exact de 9502CS_26-situatie
  nabootst (101,25 vs 77,99 vs Standaard 84).

## Out of scope
- Andere VABI-Summary-velden of indicatoren (label, primair fossiel, TOjuli) — ongewijzigd.
- Herberekening van bestaande dossiers/projecten op de VPS (dat is een aparte heruploadstap per
  project, geen code-taak).

## Acceptance criteria
- [x] `result_reader.read_results()` toetst tegen `NettoWarmtebehoefte` wanneer aanwezig.
- [x] Fallback op `IndicatorEnergiebehoefte` blijft werken voor exports zonder `NettoWarmtebehoefte`.
- [x] Dashboard, advies-tekst en het publieke `nijbegun_engine`-contract gebruiken dezelfde waarde.
- [x] Regressietest met de echte 9502CS_26-cijfers (101,25 / 77,99 / 84).
- [ ] `./scripts/verify.sh` slaagt.
- [ ] AI-review PASS door een andere leverancier dan de bouwer.

## Status voor de volgende sessie (22-8-2026)
**Nog open, niet gemerged, niet gedeployed.** PR #28 (https://github.com/renzepoortinga/NijBegun/pull/28)
staat OPEN, de `verify`-Actions-check is groen, maar de `ai-review`-Actions-check is GEEN echte review
— de workflowlog toont letterlijk `ANTHROPIC_API_KEY ontbreekt — AI-review overgeslagen`. Er is dus nog
GEEN onafhankelijke review geweest (mijn eigen `/code-review high` in-sessie hieronder is dezelfde
leverancier en telt niet als de vereiste onafhankelijke review).

Live op de VPS (production) draait nog de OUDE code: bevestigd 22-8-2026 op project 9502CS_26 — de
VABI-toets-pagina toont "Netto warmtebehoefte (met maatregelen) 101,25". Het label zelf was al goed
(stond al zo in de bestaande template, dat verwarde me eerst), maar het GETAL erachter is nog fout —
moet 77,99 zijn (uit `NettoWarmtebehoefte` in de eigen VABI-export van de gebruiker). Bevestigt dat de
bug reëel en nog live/ongefixt is voor de gebruiker.

**Volgende stappen voor wie dit oppakt:**
1. Onafhankelijke review regelen op PR #28 (andere leverancier dan Claude/Anthropic — Codex/OpenAI is
   in dit project de gangbare route, zie eerdere taken se `agents/reviewer.md`).
2. Na PASS: mergen naar `main` (niet zelf `--admin` forceren).
3. VPS deployen: `ssh renzepoortinga@37.97.195.196 "cd /opt/nijbegun && git pull && sudo docker compose -f deploy/docker-compose.yml up -d --build"`.
4. Live op project 9502CS_26 verifiëren (https://nijbegun.poortinga-energieadvies.nl/project/9502CS_26/vabi):
   moet 77,99 vs 84,0 tonen -> "voldoet".
5. Taak naar `tasks/done/` verplaatsen + `docs/STATE.md` bijwerken.

## Sessions
- 2026-08-21 Claude Code: bug gevonden tijdens live vergelijking van project 9502CS_26 in de webapp
  vs SOBOLT (browser-automatisering), bevestigd met de ruwe VABI-XML van de gebruiker. Fix
  doorgevoerd in result_reader/monitor_xml/dashboard/advies_text/nijbegun_engine + regressietest.
  `./scripts/verify.sh` PASS (1067/1067). PR #28 geopend.
- 2026-08-21 Claude Code, zelf-review (`/code-review high`, zelfde leverancier — geen vervanging
  voor de vereiste onafhankelijke review): 4 bevindingen verwerkt — (1) advies-tekst claimde altijd
  "netto warmtebehoefte" ook bij de IndicatorEnergiebehoefte-fallback, nu conditioneel op
  `_toetswaarde_bron`; (2) CLI-prints in `monitor_xml.py`/`run.py` hernoemd naar neutraal
  "warmtebehoefte (schil)"; (3) `nijbegun_engine` hergebruikt nu `_toetswaarde` i.p.v. de
  fallback-regel te dupliceren; (4) dubbele XML-lookup in `monitor_xml.py` opgelost. Dashboard-
  labels (Huidige staat + VABI-toets) tonen nu ook conditioneel "netto warmtebehoefte" vs
  "energiebehoefte" via nieuwe `behoefte_label`-sleutel in `_verdict()`. `verify.sh` opnieuw PASS.
  Nog open: onafhankelijke review (andere leverancier) + live her-upload op de webapp.

## Notes
De publieke `nijbegun_engine`-package documenteert zich als "stable contract the SaaS builds
against" — de sleutelnaam `"energiebehoefte"` in de return-dict is bewust ongewijzigd gelaten, alleen
de onderliggende waarde is gefixt, om het externe contract niet te breken.
