---
id: 023
assigned: Codex Builder
branch: fix/023-dakkapel-preflight
depends_on: []
---

# Task 023 — Dakkapel-op-legacy-placeholder mist het `id=="dak"`-signaal + 5x dubbele preflight-scan

## Goal
Twee kleine, niet aan elkaar gerelateerde bevindingen uit de `/code-review high`-ronde van taak 015
(21-8-2026), die buiten die taak vallen (ze raken taak-014-code, al afgerond/`tasks/done/`) en dus
hier apart vastgelegd worden i.p.v. in 015 meegefixt — zelfde patroon als taak 025.

## Scope
1. **`dashboard/app.py::opname_dakkapel()` (rond regel 1851)** — reclassificeert het moederdak alleen
   weg van de weggooibare placeholder-status voor het EXPLICIET getagde geval
   (`moeder.bron == "magicplan-dak-fallback"`), maar mist het LEGACY-signaal dat
   `vabi/preflight.py::dak_fallback_schildelen()` ook als placeholder herkent
   (`bron == "" and id == "dak"` — precies het live Essenhage-patroon dat taak 014 aanleiding gaf).
   Gevolg: bij een dakkapel op een ONGETAGD legacy-dossier blijft het (na de dakkapel-correctie
   legitiem verkleinde) dakvlak toch als placeholder herkenbaar → een latere dak-wizard-route kan het
   alsnog stilletjes weggooien (`_dak_fallback_opschonen`), of de preflight-poort blokkeert/laat toe
   op basis van de verkeerde classificatie. Fix: dezelfde herclassificatie ook toepassen wanneer het
   legacy-signaal (`id=="dak"`, lege `bron`) van toepassing was, niet alleen de expliciete tag.
2. **`vabi/generate_all.py`** — `assert_no_dubbel_dak_fallback(dos)` wordt tot 5x per
   `generate_all()`-run aangeroepen (rechtstreeks + binnenin de `resolve_constructies`-aanroepen van
   `constructie_generate.write`/`objecten_generate.write` + nogmaals rechtstreeks in
   `objecten_generate.write` + in `installatie_generate.write`), en scant elke keer opnieuw de volledige
   `dos.schil`-lijst. Geen correctheidsprobleem, wel overbodig werk dat groeit naarmate er meer
   preflight-checks bijkomen volgens hetzelfde patroon — eenmalig aanroepen (bv. bovenaan
   `generate_all()`) en doorgeven, of de individuele generators laten vertrouwen op de ene
   bovenliggende aanroep.

## Out of scope
- De rest van taak 014/015 (al afgerond).
- Nieuwe dakrekenformules of preflight-regels.

## Acceptance criteria
- [ ] Dakkapel op een ongetagd legacy-dossier (bron=="" , id=="dak") herclassificeert het
      moederdak net als het expliciet-getagde geval; regressietest toegevoegd.
- [ ] `assert_no_dubbel_dak_fallback` wordt maximaal 1x per `generate_all()`-run uitgevoerd (of de
      herhaalde aanroepen zijn aantoonbaar goedkoop/no-op gemaakt); bestaande AC-tests blijven groen.
- [ ] `./scripts/verify.sh` slaagt.
- [ ] AI-review PASS door een andere agent dan de bouwer.

## Sessions

- 2026-08-21 Codex Manager: hernummerde reviewvervolgtaak geclaimd op een eigen worktree vanaf
  actuele `main`; scope blijft beperkt tot legacy-dakkapelclassificatie en preflightdeduplicatie.
- 2026-08-21 Codex Builder: `opname_dakkapel` legt via de gedeelde
  `dak_fallback_schildelen`-herkenner vóór mutatie vast of het moederdak een expliciete of
  ongetagde legacy-placeholder was en herclassificeert beide daarna als `magicplan-import`.
  `generate_all` voert de dubbel-dakpreflight eenmaal uit en geeft dit expliciet door aan de drie
  writers en hun gedeelde constructieresolver; rechtstreeks aangeroepen writers blijven zelf
  fail-closed controleren. Regressies bewijzen het legacy-dakkapelpad, exact één preflight per
  samengestelde export en behoud van de drie directe-writerpoorten. `python tests/run_tests.py`:
  849/849 groen; blocking `scripts/verify.sh`: PASS. Geen dependencies of dakformules gewijzigd.
- 2026-08-21 Codex Builder (reviewfix): review-FAIL was terecht: de eerste implementatie bood
  externe callers een forgeable publieke `dak_preflight_done=True`-bypass. Die parameter is uit
  alle publieke writer/resolver/build-tree-signatures verwijderd. Publieke paden voeren de poort
  altijd uit; alleen private underscore-helpers delen binnen `generate_all` het al gevalideerde
  dossier. Taak-017-foutinjectie wijst nu naar die interne writerfasen. Nieuwe regressies bewijzen
  dat de publieke signatures geen bypass meer aanbieden, de oude keyword-aanroep `TypeError` geeft,
  directe writers blijven blokkeren en `generate_all` nog steeds exact eenmaal scant. 851/851 groen;
  blocking `scripts/verify.sh`: PASS.

## Notes
Gevonden tijdens `/code-review high` op taak 015 (21-8-2026, mappingmanifest-sessie). Zie die
review-ronde voor de volledige bevindingsomschrijving; hier alleen samengevat/vastgelegd.
