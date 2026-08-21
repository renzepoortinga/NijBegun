# Stresstest MagicPlan ↔ tool ↔ VABI — 15-8-2026

> **Let op:** dezelfde dag liep parallel al een bredere, formele ketenaudit (taak 013,
> `docs/ketenaudit-magicplan-tool-vabi-2026-08-15.md`, met eigen review en backlog-taken
> 014-017) — die is architectonisch grondiger (dakmigratie/dubbele vlakken, atomische export,
> mappingmanifest, voorbeeldplan-structuurvergelijking). Dit document is een **losse, kortere
> stresstest** uit een ander gesprek die zich vooral onderscheidt door één concrete,
> reproduceerbare **code-bug** die de andere audit niet noemt (bevinding 1) — zie
> `tasks/backlog/018-fix-aanvoertemperatuur-undot.md` voor de bugfix-taak. Lees dit document
> als aanvulling op taak 013, niet als vervanging.

Doel: live doorlopen of een goed ingevulde MagicPlan-opname écht bijna niets meer aan
handwerk overlaat (behalve het dak, per besluit 15-7), of de dropdowns/vocabulaire tussen
MagicPlan, de parser en VABI kloppen, en of import/export soepel loopt. Uitgevoerd met
Chrome (MagicPlan live, workspace R.poortinga) + de tool lokaal, op het testproject
**"Essenhage 32, 9501TP (Copy)"** (aangemaakt 13-8 door Renze, forms al ingevuld).

## Aanpak
1. Kennisbank gelezen: `STATE.md`, `magicplan-velden-audit.md`, `magicplan-forms-live.md`,
   `WERKWIJZE-A-TOT-Z.md`, `OVERDRACHT-NIEUWE-STRUCTUUR-2026-08-12.md`.
2. Live in MagicPlan: de 3 project-forms (Object/Constructies/Installaties) van het
   testproject uitgelezen en de dropdown-waarden vergeleken met wat de parser
   (`magicplan/statistics_csv.py`) en de VABI-generators verwachten.
3. Verse Statistics-CSV gedownload uit het originele Essenhage-project (na expliciete
   toestemming) en door de **hele keten** gehaald: `statistics_csv.py` → dossier-JSON →
   `vabi/generate_all.py` (Constructie-/Objecten-/Installatiebibliotheek) → `run.py`
   (isolatieplan/rapport/ventilatie/foto-checklist/validatie).
4. Voorbeeldplannen (1970/1993/2002) gelokaliseerd in OneDrive; visuele 1-op-1-vergelijking
   met de gegenereerde docx kon dit keer niet (poppler/pdftoppm ontbreekt op deze machine
   voor het renderen van PDF-pagina's) — zie "Niet gedaan" onderaan.

---

## Bevinding 1 (bug, hoge impact) — aanvoertemperatuur wordt STRUCTUREEL fout genormaliseerd

**Live bevestigd + herleid tot de exacte regel.** MagicPlan exporteert de dropdown-waarde
`90/70` in de Statistics-CSV als `90.70` (punt i.p.v. schuine streep — een MagicPlan-
exportquirk voor élke "X/Y"-achtige dropdown-waarde). `installatie_generate.py` weet dit al
en herstelt bewust `.` → `/` vóór de vergelijking met de codetabel:

```python
# vabi/installatie_generate.py:237
_at = _at_raw.replace(".", "/").replace("-", "/").replace(" ", "")
```

Het probleem: de waarde is dan al kapot. `statistics_csv.py` leest élk Installaties-veld via
`G2()`, en `G2()` haalt alles door `_undot()`:

```python
# magicplan/statistics_csv.py:31-37
def _undot(v):
    """Herstel een ge-'dot' categorische waarde: 't.m' -> 't/m', overige '.' -> spatie."""
    s.replace("t.m", "t/m")
    return s.replace(".", " ").strip()   # ELKE andere punt -> SPATIE
```

`_undot()` is geschreven voor bouwjaarklasse-achtige strings (`1975.t.m.1982` → `1975 t/m
1982`) maar wordt via `G2()` blind toegepast op **alle** Installaties-velden, dus ook
`aanvoertemperatuur`. `90.70` wordt daardoor al in de parser `90 70` (spatie) — en de latere
`.replace(".", "/")` in `installatie_generate.py` heeft niets meer om te herstellen, want de
punt is al weg. **Live gereproduceerd**: dossier-JSON van het testproject bevat
`"aanvoertemperatuur": "90 70"`, en `vabi/generate_all.py` gooit vervolgens de flag
`aanvoertemperatuur '90 70': onbekende klasse` — terwijl de live MagicPlan-waarde gewoon de
bekende, ondersteunde `90/70` was. Bevestigd in isolatie:
```python
>>> statistics_csv._undot("90.70")
'90 70'
```

**Impact:** dit raakt *elk* project met een aanvoertemperatuur-dropdownwaarde (alle 12 codes
30/27 t/m 90/70) — de auto-codering naar `WaterAanvoertemperatuur` in VABI **werkt dus nooit**,
ook al is dat precies het veld waarvan de code-comments zeggen dat het "belangrijk is voor
oude woningen met 90/70-radiatoren" (eerder al eens gefixt voor een ander mapping-gat, 18-7).
Elke adviseur moet dit nu altijd handmatig in Vabi zetten — terwijl de tool het kán automatiseren.

**Fix (niet doorgevoerd, awaiting akkoord):** in `installatie_generate.py` vóór de
`_AANVOERTEMP`-lookup ook spaties tussen twee 2-cijferige getallen als scheiding accepteren
(`re.sub(r"(\d{2})\D+(\d{2})", r"\1/\2", _at_raw)`), of specifieker: `G2()` voor het
`aanvoertemperatuur`-veld niet door `_undot()` halen (het is geen categorische t/m-waarde).
De tweede optie is zuiverder — `_undot()` hoort niet blind op elk Installaties-veld te draaien.

---

## Bevinding 2 — `WERKWIJZE-A-TOT-Z.md` is verouderd (documentatie, geen code)

Beschrijft nog het form **"Schil & zone"** en dak-projectvelden (`Type dak`, `Dak orientatie
zijde 1/2`, …) in MagicPlan. Die zijn op 23-7 vervangen door **Object + Constructies +
Installaties**, en het dak is diezelfde dag **uit MagicPlan verwijderd** (nu alleen nog
isolatie-only in Constructies; geometrie via de webapp-wizard) — bevestigd live: het
testproject heeft precies 3 forms, geen dak-geometrievelden. Een adviseur die deze how-to
volgt zoekt naar velden die niet meer bestaan. `docs/magicplan-forms-live.md` is wél actueel
en zou de bron moeten zijn waarnaar STAP 2f/2f-bis van de A-tot-Z-gids verwijst.

## Bevinding 3 — kleine UX-inconsistentie: Engelse "No" tussen Nederlandse velden

`Tweede opwekker (hybride)?` en `Meerdere PV-systemen?` zijn losse boolean-velden (gate voor
resp. 3 en 6 vervolgvelden) die **"No"/"Yes"** tonen i.p.v. de **"Ja"/"Nee"**-dropdownstijl van
de rest van het formulier — functioneel geen probleem (de parser leest sowieso rechtstreeks
`Verwarming 2 - type opwekker` / `PV-2 - ...`, ongeacht deze gate-waarde), maar oogt slordig
naast 174 verder consequent Nederlandse velden. Makkelijk op te lossen door deze twee velden
ook als de standaard Ja/Nee-dropdown te definiëren i.p.v. het native boolean-widget-type.

## Bevinding 4 — freshness-check gebruikt het verkeerde tijdstempel

De parser waarschuwt: *"Deze opname komt uit een MagicPlan-export met projectdatum
2026-07-08. Klopt dit niet met je laatste wijzigingen? Exporteer dan een verse CSV."* — dit
komt uit het **projectaanmaakmoment**, niet de exportdatum van de CSV zelf. Bij dit
testproject (aangemaakt 8-7, laatst gewijzigd/geëxporteerd 13-8) vuurt de melding dus ook op
een **kersverse** export. Nuttige controle in intentie, maar het signaal is niet betrouwbaar —
overweeg de CSV-bestandsdatum (of een 'laatst gewijzigd'-veld uit MagicPlan zelf, indien
geëxporteerd) te gebruiken in plaats van de projectdatum.

---

## Wat goed werkt (bevestigd, positief)

- **Conditionele form-logica live correct**: "isolatiedikte onbekend? = Ja" verbergt
  terecht het dikte-veld; Ventilatiesysteem A → toont automatisch Subsysteem (A)-opties; PV/
  hybride-gates tonen/verbergen hun vervolgvelden.
- **`Gevel/Dak - isolatie aan zijde`-vocabulaire** ("Spouw (na-isolatie)", "Binnenzijde
  (voorzetwand)") matcht de substring-matching in `isolatieplan/fill_template.py` correct —
  geverifieerd met de live waarden van het testproject.
- **KV-preflight-gate bijt echt**: het testproject had `Vloer - invoer = Kwaliteitsverklaring`
  zonder correct verwerkte foto/waarde → `vabi/generate_all.py` weigerde terecht te exporteren
  (`VabiExportBlocked`) in plaats van stilzwijgend een forfaitaire waarde te verzinnen — precies
  de gouden regel in actie.
- **Slimme geometrie-heuristieken vuurden correct** op de echte data: gesplitste
  woningscheidende wand via 'Grenst aan buiten (m)' herkend op twee wanden, hart-op-hart-
  gevel-toeslag correct berekend en geflagd (niet automatisch toegepast, zoals bedoeld),
  vloerbegrenzing per ruimte correct gesplitst (Grond vs. Kruipruimte), **en een ontbrekend
  dakvlak (aanbouw/bijkeuken) correct gedetecteerd** op basis van het oppervlakteverschil
  tussen begane grond en hoofddak-footprint — dat is precies het soort controle die een
  adviseur anders zelf moet opmerken.
- **Volledige keten liep foutloos door**: CSV → dossier (12 ruimtes, 4 gevels, 13 kozijnen) →
  3 VABI-bibliotheken (8 constructietypes, 4 gevels/14 deelvlakken, installaties) → isolatieplan
  (3 maatregelen, €13.070,42 incl. btw) + ventilatieberekening + fotochecklist + validator, met
  heldere "LET OP"-meldingen op elke stap.

---

## Niet gedaan deze sessie (scope/tijd)

- **Live import in VABI EPA-W** van de 3 gegenereerde bibliotheken (zou de eindcontrole zijn
  op echte "Enum mismatch"-fouten) — niet uitgevoerd; EPA-W is niet geopend deze sessie.
- **Webapp-dashboard (dak-wizard, maatregelen-stap)** — vereist inloggen (e-mail/wachtwoord/
  MFA); dat mag ik niet voor je invullen. Log zelf in op de "Nij Begun · isolatieplan"-tab en
  ik pak de rest van de flow op.
- **1-op-1 visuele vergelijking met de 3 voorbeeldplan-PDF's** (1970/1993/2002, gevonden in
  OneDrive) — deze machine mist `poppler`/`pdftoppm` om PDF-pagina's te renderen. Met een
  losse PDF-viewer kun je dit zelf snel doen, of installeer poppler en ik doe het alsnog.
- **Volledige dropdown-voor-dropdown audit** van alle 174 velden — met de conditionele
  steekproef + de end-to-end-run is het hoogste-impact-gebied (installaties/aanvoertemp)
  gevonden; een uitputtende veld-voor-veld pass is een aparte, geduldige taak.

## Aanbevelingen (op impact)

1. **Fix bevinding 1 (aanvoertemperatuur)** — kleine, veilige wijziging, hoge impact (raakt
   elk project). Wil je dat ik dit oppak op een nieuwe branch (`fix/aanvoertemperatuur-undot`)?
2. Update `WERKWIJZE-A-TOT-Z.md` STAP 2f/2f-bis + verwijs naar `magicplan-forms-live.md` als
   bron (bevinding 2) — klein, laag risico.
3. Zet de twee Engelse boolean-gates om naar Ja/Nee-dropdowns voor consistentie (bevinding 3).
4. Freshness-check op CSV-bestandsdatum i.p.v. projectdatum (bevinding 4) — lage prioriteit.
5. Plan een sessie met EPA-W open om de 3 gegenereerde bibliotheken van dit testproject
   daadwerkelijk te importeren — dat is de enige controle die deze sessie niet kon doen.
