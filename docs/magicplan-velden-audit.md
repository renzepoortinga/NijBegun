# MagicPlan-velden audit — live vs. parser vs. NTA 8800 / Nij Begun (27-7-2026)

Deep dive: komen de live MagicPlan-velden overeen met wat de tool leest, en dekken ze samen alles
wat NTA 8800 (basisopname) en Nij Begun / Maatregel 29 nodig hebben?

Bronnen: live uitgelezen via de custom-forms/-fields API (27-7-2026) · `magicplan/statistics_csv.py`
(de parser) · NTA 8800:2025+C1:2026 (H6/H8/H11 + bijlagen C/E/I/K) · `docs/nijbegun-kennisbank-eisen.md`.
Kolom-bewijs uit een echte export: `out/_uploads/opname_9501TP_32.csv` (Essenhage 32, 11-7).

---

## 1. Live inventaris — 174 velden

| Groep | Type | Aantal |
|---|---|---|
| **Object** | project-form | 11 |
| **Constructies** | project-form | 23 (GEVEL 13 + VLOER 10; dak verwijderd 23-7) |
| **Installaties** | project-form | 70 |
| **All Walls** | element-fields | 16 |
| **All Rooms** | element-fields | 11 |
| **Windows** | element-fields | 27 |
| **Doors** | element-fields | 16 |

---

## 2. Wat de parser écht leest

De parser kent twee routes:
- **`G("…")` = PLAN ATTRIBUTES** → de project-forms (Object/Constructies/Installaties). Deze worden
  **volledig gelezen** ✅
- **kolomkop-lookup in de rij** → element-velden (walls/windows/doors/rooms).

Voor de elementen leest de parser via kolomkop:
- **Windows** — via `_wn(...)`: alle raam-/paneel-/boven-/onderlicht-velden ✅
- **Doors** — via `_byname(...)`: alle deur-velden ✅
- **Walls** — slechts **4**: `Gevelnaam`, `Gevel - oriëntatie (override)`,
  `Deels binnen/deels buiten? (narekenen)`, `Grenst aan buiten (m)`
- **Rooms** — **0**: alleen kolom 0 (kamernaam) en kolom 1 (oppervlak)

### ⚠ Bevinding A — de per-wand overrides worden niet gelezen (12 velden)
`Gevel - isolatie aanwezig?/isolatiedikte onbekend?/bouwjaar/isolatiedikte (mm)/spouw ×2/
bouwjaar (onbekend)/thermische massa/begrenzing/rekenzone/invoer (override)/foto kwaliteitsverklaring`
staan wél live op de wand, maar de parser haalt die eigenschappen uit **naam-tokens** of uit de
**project-standaard** (`_isolatie_uit_naam`, `_rekenzone_uit_naam`, `_gevel_begr_default`).
→ Vul je ze per wand in, dan gebeurt er **niets**. Je moet terugvallen op tikken in de wandnaam —
precies wat we met de "geen namen meer typen"-slag wilden afschaffen.

### ⚠ Bevinding B — álle kamer-velden worden niet gelezen (11 velden)
`Vloer - invoer/isolatie/dikte/bouwjaar/thermische massa/begrenzing/rekenzone/telt mee voor Ag/foto KV`.
**Bewezen in de echte export:** `Vloer - telt mee voor gebruiksoppervlakte?` staat als kolom 11 in de
CSV — en wordt genegeerd. De vloerbegrenzing per kamer komt uit de **ruimtenaam**
(`_begrenzing_uit_naam`), niet uit het veld.

> Nuance: MagicPlan exporteert alleen kolommen voor velden die zijn ingevuld. De 11-juli-export bevat
> daarom niet alle wand-/kamervelden. Dat verandert de conclusie niet: de parser zóekt er niet naar.

---

## 3. Dekking NTA 8800 (basisopname)

| NTA-eis | Waar | Status |
|---|---|---|
| Ag / verliesopp. / geometrie (§6.6-6.9, bijl. K) | MagicPlan-geometrie + Ag-aftrek zolder | ✅ |
| Vloer-perimeter (randverlies, 13370) | auto uit gevelbreedtes (23-7) | ✅ |
| Rc dicht deel: isolatie/dikte/bouwjaarklasse/spouw (bijl. I.2.1) | Constructies (gevel/vloer) | ✅ project-breed |
| U ramen: glastype × kozijntype (tab. 8.3 / I.8) | Windows/Doors | ✅ |
| U deuren / panelen (I.10 / I.11) | Doors / paneel-velden | ✅ |
| Begrenzing incl. AOR/AOS/**ASGR**/water/kelder (§6.3, 6.7.3) | 4 begrenzing-velden (23-7 aangevuld) | ✅ |
| Thermische massa (§7.7) | Constructies gevel+vloer | ✅ (dak bestaat niet in EPA) |
| Oriëntatie (§8.2.1, TOjuli) | Oriëntatie voorgevel + per-wand override | ✅ |
| qv10 / infiltratie (§11.2.5) | Qv10-waarde + gemeten? + renovatiejaar | ✅ |
| Ventilatiesysteem A-E + subsysteem + WTW (H11) | Installaties | ✅ |
| Verwarming / tapwater / koeling / PV (H9/H10/H13/H16) | Installaties | ✅ |
| Bouwjaar / gebouwhoogte / woningtype | Object | ⚠ zie C |
| **Dak: isolatie/Rc** | webapp-wizard | ⚠ zie D |
| **DWTW douche-WTW (bijl. U)** | — | ❌ ontbreekt |
| **Zonwering/rolluik (§8.2.2.3.4)** | — | ❌ ontbreekt |
| **Rieten dak (bijl. I: d/0,105)** | alleen in de PDF-route | ❌ niet in de CSV-route |
| **Beschaduwing/belemmering PV (§17.3)** | — | ❌ ontbreekt |

### ⚠ Bevinding C — Woningtype dekt alleen grondgebonden
Live opties: `Vrijstaand · Twee-onder-een-kap · Tussenwoning · Hoekwoning`. Geen appartement/galerij/
portiek/maisonnette (de webapp kent die 10 wél). Dit raakt **twee** berekeningen:
- de **Standaard-eis** (§5.3.2) verschilt grondgebonden (43/60) vs. woongebouw (45/95);
- de **qv10 ftype** (tab. 11.14) heeft eigen rijen voor meerlaagse gebouwen.
`is_grondgebonden("")` geeft **True** → een appartement wordt stil als grondgebonden gerekend tenzij
je het woningtype in de webapp corrigeert.

### ⚠ Bevinding D — Dak-isolatie wordt niet uitgevraagd
De dak-wizard vraagt alleen geometrie en zet `isolatie_aanwezig="Onbekend"` hardcoded. De
element-editor kán Rc/isolatie/dikte/begrenzing achteraf zetten, maar de wizard **wijst er niet op**.
Bij "Onbekend" valt de generator terug op de **project-bouwjaarklasse** — conform NTA bijlage I.2.1.3,
dus niet fout, wél conservatief (en vaak onnodig ongunstig als je de dikte gewoon kunt meten).
Ontbreekt bovendien in de editor: **bouwjaarklasse per dakvlak** en **rc_bron (kwaliteitsverklaring)**.

---

## 4. Dekking Nij Begun / M29

| Eis (Beoordelingsformulier / handleidingen) | Status |
|---|---|
| Foto voorkant + huisnummer (adres-match) | ✅ Object, verplicht |
| Foto's per bouwdeel + ≥1 detailfoto per cat-2-prijs | ✅ Installaties-fotovelden + `foto/checklist.py` |
| Ventilatieberekening (0,7 dm³/s·m² per verblijfsgebied) | ✅ ruimtes + roosters (incl. boven-/onderlicht 23-7) |
| Kierdichting (V6) | ✅ Constructies |
| Bodemisolatie kruipruimte (V3) | ✅ Constructies |
| Isolatie aan zijde (V1/V4 huidige staat) | ⚠ gevel ✅, **dak-zijde weg** met het dak-blok |
| Technische haalbaarheid per maatregel | ✅ webapp (niet MagicPlan) |

---

## 5. Aanbevolen acties (op impact)

1. **Wand-overrides lezen** (bevinding A) — parser laten zoeken op de 12 wandkolommen, met de
   naam-tokens als fallback. Grootste winst: geen namen meer typen, per-wand afwijkingen werken echt.
2. **Kamer-overrides lezen** (bevinding B) — minimaal `Vloer - begrenzing`,
   `Vloer - telt mee voor gebruiksoppervlakte?` en `Vloer - rekenzone`. Nu stille invoer.
3. **Woningtype uitbreiden** (bevinding C) met de gestapelde types; anders is de Standaard-eis fout
   voor appartementen. Overweeg `is_grondgebonden` bij leeg woningtype te laten **flaggen** i.p.v. stil True.
4. **Dak-isolatie in de wizard** (bevinding D) — isolatie/dikte/bouwjaarklasse/rc_bron bij het
   toevoegen van een dakvlak uitvragen, plus "Dak - isolatie aan zijde" (V4) terug in de flow.
5. **Ontbrekende NTA-velden** toevoegen waar ze echt tellen: **DWTW** (grote invloed op tapwater),
   **zonwering/rolluik**, **riet**, **PV-belemmering**.

> Werkwijze bij wijzigingen: live via de browserconsole-route (zie `magicplan/forms/LIVE-WIJZIGINGEN.md`),
> en werk daarna `docs/magicplan-forms-live.md` bij. De parser-veldnamen in `statistics_csv.py` zijn
> leidend voor de exacte naamgeving.
