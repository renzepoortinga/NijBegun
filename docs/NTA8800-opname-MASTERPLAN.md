# Masterplan — MagicPlan-opname → NTA8800/VABI + Nij Begun

*Synthese van twee multi-agent reviews (ISSO 82.1-norm + dekkingsmatrix tegen het officiële NTA8800 W-bouw
opnameformulier v2025), het officiële opnameformulier (`vabi/refs/opnameformulier_nta8800_v2025.txt`), en
eigen code-verificatie. Datum 22-6-2026. Toetsbron: `out/isso821_pages.json` (ISSO 82.1, 7e druk, 216 p.).*

> **Leeswijzer claims:** ✅ = door mij geverifieerd in code/ISSO/refs · 🔎 = aannemelijk, nog te verifiëren
> (echte MagicPlan-CSV of EPA-export) · 🔒 = vereist EPA-export-harvest vóór auto-schrijven (golden rule).

---

## 1. Conclusie vooraf
**De architectuur klopt en de gouden regel zit in code, niet in praatjes.** De schil-geometrie stroomt
end-to-end en importeert foutloos in EPA 12. Maar de keten dekt nú vooral de **schil-geometrie + een handvol
enums**; van de 205 velden op het officiële opnameformulier is grofweg **16 volledig / 65 deels / 124 niet**
gedekt. Het grootste gat zit in de **installaties** (verwarming-detail, koeling, tapwater, PV) en in de
**per-vlak-detaillering** van de schil (begrenzing/isolatie/spouw staan nog projectbreed of hardcoded).

**Twee vondsten die het belang van zelf-verifiëren onderstrepen** (een review-agent had het mís):
- De agent claimde dat de VABI-`Hellingshoek` "rauwe graden" is en dat élk hellend dak fout stond. **Onjuist** —
  het is in de objecten-route een **enum** (`3`=hellend, `6`=plat/gevel; ✅ geverifieerd in `vabi_enums.json`).
  Hellende daken stonden al correct; alleen **platte daken** kregen onterecht 3. **Nu gefixt + getest (141 groen).**
- De gevel-`Hellingshoek` 6 is dus géén "6 graden" maar de enum-code voor gevel/plat.

---

## 2. De keten in één plaat
```
MagicPlan-opname (plattegrond + forms + per-wand Fields)
   └─ Statistics-CSV ─► statistics_csv.py ─► dossier (core/dossier.py = single source of truth)
                                                 ├─► vabi/generate_all.py ─► 3 VABI-bibliotheken ─► EPA-W ─► label
                                                 └─► engine + isolatieplan + ventilatie + foto ─► Nij Begun (M29)
```
Eén opname voedt **beide** routes. Gouden regel: de tool rekent nooit NTA8800; VABI is de rekenkern; enums
worden alleen geschreven als ze bevestigd zijn.

---

## 3. Per NTA8800-output: hoe het is → hoe het moet → wat veranderen

### 3.1 Perimeter (vloer-randverlies) — ISSO §8.3 (p.74)
- **Nu:** `vloer.perimeter_m = MagicPlan "Exterior perimeter"`, 1-op-1 naar VABI `<Perimeter>` voor élke vloer met perimeter>0. ✅
- **Norm:** perimeter = binnenwerkse omtrek **alleen voor zover de vloer grenst aan grond/kruipruimte/onverwarmde kelder**; bij hoek/tussenwoning loopt de perimeter aan de buurzijde **door tot de hartmaat** (hoek +0,11 m, tussen +0,22 m op de vloerlengte); inpandige verwarmde kelder zonder buitenomtrek = **0,01 m**.
- **Veranderen:** (a) ✅ **guard** — perimeter alleen schrijven als vloer-begrenzing ∈ {grond, kruipruimte, kelder}; (b) 🔎 **hart-op-hart op de perimeter** (helper `perimeter_hart_op_hart(omtrek, woningtype)`, gespiegeld aan de gevel-toeslag); (c) 0,01 m-regel voor inpandige kelder.

### 3.2 Begrenzing per constructie — ISSO §8.4 (p.75-76), §6.3.4 (p.41)
- **Nu:** gevel/dak/raam/deur hard op `Buitenlucht`; vloer uit veld "Begrenzing (vloer)". GrenstAan-mapping ✅ `0=Buitenlucht, 2=Grond, 3=Kruipruimte, 4=AOR`. AOS/sterk-geventileerd/onverwarmde-kelder/water/AVR niet gemapt.
- **Norm:** 7 begrenzingen: Buitenlucht/Water · AOR · AOS · Aangrenzend sterk geventileerd · Grond · Kruipruimte · Onverwarmde kelder. **In de basisopname tellen AOR/AOS/sterk-geventileerd als buitenlucht** (p.41). Een constructie tegen een **verwarmde** buurruimte (AVR, bv. buurwoning) hoort **niet** in de schil.
- **Veranderen:** (a) **per-wand `Begrenzing`-Field** in MagicPlan (gevel = parent, zie §4.1); (b) `SchilDeel.begrenzing` → gecontroleerde enum; (c) AOS/sterk-geventileerd → code 0 (basis); (d) AVR → expliciet uitsluiten i.p.v. alleen "geen oriëntatie"; (e) 🔒 codes 5/6 (Water/Kelder/AOS) via probe verifiëren.

### 3.3 Thermische schil & zone — ISSO §6.3, §8.1 (p.33-42, 66)
- **Nu:** party-walls vallen weg doordat ze geen oriëntatie krijgen (impliciet). Geen expliciet thermische-zone-/AVR-model; AOR-schil zelf wordt niet opgenomen.
- **Norm:** schil scheidt de zone van buiten/grond/water/sterk-geventileerd/AOR/AOS/kruipruimte; constructie tussen twee verwarmde rekenzones of tegen AVR telt niet mee. Stappenplan grenzen → gebruiksfuncties → thermische zone → klimatiseringszone → rekenzone.
- **Veranderen:** expliciete **AVR-status** in het datamodel (§3.2d); flag als een buitenmuur noch oriëntatie noch begrenzing heeft.

### 3.4 Rekenzones — ISSO §6.4-6.5 (p.44-45)
- **Nu:** altijd `rekenzone=1`. ❌ geen splitsingslogica.
- **Norm:** splits in meerdere rekenzones als de **specifieke interne warmtecapaciteit > factor 3** verschilt tussen delen/verdiepingen (niet bij ≤ factor 3 of > 80% gelijk), of bij **fysiek gescheiden verwarmings-/koel-/ventilatiesysteem**.
- **Veranderen:** minimaal een **sanity-flag** wanneer thermische massa tussen verdiepingen > factor 3 verschilt (adviseur splitst handmatig); later automatische multi-rekenzone-generatie.

### 3.5 Gebruiksoppervlakte (Ag) — ISSO §7.2.1 (p.61-62, NEN 2580)
- **Nu:** Ag = "Total living area"/som ruimtes; gelijk verdeeld over verdiepingen. ✅ totaal klopt.
- **Norm:** meten tussen opgaande scheidingsconstructies, op 2 decimalen; **uitsluiten:** netto hoogte < 1,5 m onder schuin dak, trapgat/vide ≥ 4 m², lift-/leidingschacht ≥ 0,5 m², dragende binnenwand.
- **Veranderen:** roep `core.geometry.ag_onder_schuin_dak()` aan voor de zolder-rekenzone (bestaat, wordt niet gebruikt); trek vide/trapgat ≥ 4 m² af; **Ag per bouwlaag** lezen i.p.v. gelijk verdelen; rond op 2 decimalen.

### 3.6 m² per constructie — ISSO §8.2 (p.67-72), §8.5-8.6 (p.77-78)
- **Nu:** gevel binnenwerks "Surface zonder openingen" per oriëntatie + hart-op-hart-toeslag (gelijk verdeeld over alle oriëntaties); dak via footprint/cos(α) + kopgevel-driehoeken; raam/deur vlakvol incl. kozijn; oriëntatie 8 klassen ✅; **`<Hellingshoek>` nu correct (3 hellend / 6 plat) ✅.**
- **Norm:** binnenwerks tot **hartmaat** bij scheidingswand (+0,11/+0,22 breedte, +0,10/+0,20 vloerhoogte); samenvoegen **alleen** bij gelijk type/begrenzing/oriëntatie/Rc-U/helling/zonwering; gevel = helling 75-165°, dak ≤ 75° (hellend ≥15°, plat <15°); deur ≥ 65% glas telt als raam; plat dak = horizontaal.
- **Veranderen:** (a) hart-op-hart-toeslag **alleen op voor+achtergevel** (nu over alle oriëntaties — 🔎 systematische afwijking; vereist een "voorgevel"-indicator); (b) verticale +0,10/+0,20 scheidingsvloer-correctie + gevelhoogte = bk-vloer→ok-dak; (c) **samenvoeg-/splitsguard** op (oriëntatie, begrenzing, Rc, helling, zonwering); (d) dak-classificatie 75°/15° als validatie/fallback.

---

## 4. MagicPlan-opname herontwerp (invoer = VABI-gevoel)

### 4.1 Parent/child-gevelmodel — begrenzing + oriëntatie per buitengevel
**Probleem (jouw punt):** MagicPlan biedt geen los projectveld per buitengevel; begrenzing staat hard op
Buitenlucht. **Oplossing:** een **per-wand Field `Begrenzing (gevel)`** (List: Buitenlucht · AOR · AOS · Sterk
geventileerd · Grond · Kruipruimte · Onverwarmde kelder · **Aangrenzende woning/AVR = buiten schil**), net zoals
oriëntatie al op wandniveau zit (WALL-kolom). De **gevel wordt zo de parent**: ramen/deuren erven begrenzing +
oriëntatie. Parser leest de wand-begrenzing-kolom i.p.v. de hardcode; AVR-wand → uit de schil.
- **Fallback (editor wisselvallig):** naamconventie op de wand (`AOR garage Z`, `GROND`) → parser leest begrenzing+oriëntatie uit de wandnaam. Zelfde parent/child-logica.
- **If-then:** Begrenzing=Grond → toon `Diepte onder maaiveld (m)` (gevel-splitsing grond-deel/buitenlucht-deel, ISSO p.76); Begrenzing=Kruipruimte (vloer) → kruipruimte-subblok (detail).

### 4.2 Dak per-vlak / de 9 oriëntaties (moeilijke daken & dakkapellen)
- Behoud de bestaande 9 dak-velden voor het simpele zadeldak, maar maak dak **per-vlak invoerbaar** voor samengestelde daken: een herhaalbaar `Dakvlak`-blok (m² óf maten + hellingshoek + **oriëntatie N..NW + Horizontaal**). Parser → één `SchilDeel(type=dak)` per rij. ISSO verbiedt samenvoegen bij verschil in oriëntatie/helling (p.67).
- **Dakkapel:** invoerblok (breedte/hoogte/diepte + oriëntatie) → `core.geometry.dakkapel_vlakken` (bestaat al): voorgevel + 2 zijwangen = **gesloten gevel**, plat dakje = dak (ISSO §8.2.1 p.69).
- Lijn `Type dak` uit met het formulier: **Hellend/puntdak · Gedeeltelijk plat (≥50%, alleen vrijstaand) · Plat**.

### 4.3 Ventilatieplan & balans op de plattegrond — ISSO §11.1.4 + Kleintje Ventilatie
- **Per-ruimte ventilatie-symbolen** op de plattegrond: toevoer (gevel/raamrooster type ZR/niet-ZR + **lengte m**, of WTW-ventiel), afvoer (debiet dm³/s), **overstroompijl** onder deur (richting), mechanische unit/WTW-locatie, dak-/geveldoorvoer.
- `Ruimte` uitbreiden met ventilatievelden (functie verblijfsgebied/-ruimte/keuken/bad/toilet; vereist_debiet, toevoer/afvoer/overstroom).
- **Balans-rekenkern: HOU DE NIJ BEGUN-VUISTREGELS AAN** (`ventilatie/nijbegun_vuistregels.md`, BBL-gebaseerd, bindend — afwijken = afgekeurd). Rate = **0,7 dm³/s·m² per VERBLIJFSGEBIED** (NIET de NTA8800-nieuwbouw 0,9), **min 7 l/s per leefruimte**; afvoer keuken **21** / bad **14** / toilet **7**. Ons `ventilatie.py` gebruikt al 0,7 ("bestaand") — correct. Uitbreiden naar een echte balans-tabel met **overstroom** (max onder **2** deuren), de **≥50%-van-buiten-regel**, **géén afvoer in slaapkamer**, **>15 l/s onder deur → deurrooster**, afstand af/toevoer, afstand rookkanaal (~6-10 m / 2 m), en C4c CO₂-sturing op afvoer woonkamer+hoofdslaapkamer. *(De "0,9 verblijfsgebied" en "70%-installatie-eis" uit de review-agent waren onjuist voor Nij Begun — geschrapt.)*
- ⚠️ **Golden-rule-schending in eigen code:** `MAX_AFVOER_PER_VENTIEL_DM3S=14` in `ventilatie.py` ("Bevestig met ISSO") is een **verzonnen drempel** — staat NIET in de Nij Begun-vuistregels. Vervangen door een waarde uit ISSO-kleintje Ventilatie of flaggen. (De vuistregels geven wél de >15 l/s-onder-deur→deurrooster-regel; dat is overstroom, niet afvoer-per-ventiel.)
- **Deliverable:** een ventilatieplan-overlay (balans-tabel + ingetekende symbolen) — dubbel nut: onderbouwt de VABI-subsysteemkeuze én is een Nij Begun-deliverable (onderdeel E).

### 4.4 Derde form "Installaties (detail)"
Voor de dode takken (verwarming-detail/koeling/tapwater/PV): aparte form met **gate-velden** (Koeling aanwezig? PV/PVT/zonneboiler? Tapwater-systeemtype) die conditioneel subblokken openen. BCRG-/EN-meetgegevens **buiten** de form houden (zoekt de adviseur in Vabi) — consistent met de huidige ventilatie-aanpak.

---

## 5. Installaties (VABI-getrouw) — de grootste uitbreiding
- **Nu:** form dekt alleen ventilatie + verwarming-type-opwekker. Tapwater/koeling/zon **afwezig** in opname; parser/generator vullen ze niet → één opname kan het label **niet** volledig voeden.
- **PV-blokkade (label-kritiek):** `installatie_template.xml` heeft een **lege `<ZonneEnergieList>`** — geen sjabloonknoop om te klonen, dus zelfs een volledig PV-dossier levert **geen PV** in de import. → een echte EPA-export mét PV nodig om de sjabloonknoop te maken. 🔒
- **Veranderen:** form-blokken Verwarming(detail)/Tapwater/Koeling/Zon met VABI-getrouwe dropdowns + if-then (zie §7); parser+assemble mappen; generator schrijft **alleen bevestigde codes** (codebook-poort), rest geflagd; **installatie-dekkingsrapport** (zoals `sanity.py` voor geometrie) dat per installatiedeel meldt wat ontbreekt/nagevraagd moet worden.

---

## 6. VABI-import (enums): bevestigd vs te verifiëren
**✅ Bevestigd (auto-schrijven):** Orientatie (Z=0…ZO=7, horizontaal=-1) · GrenstAan (Buitenlucht=0/Grond=2/Kruipruimte=3/AOR=4) · **Hellingshoek (hellend=3, plat/gevel=6)** · ConstructieType (gevel=0/raam=2/deur=3/dak=4/vloer=7/paneel=1) · IsolatieAanwezig (opgemeten=0/geen=1/forfaitair=3) · Glas (voorzet=1/Dubbel=2/HR=3/HR+=4/HR++=5/Triple=6) · Kozijn (metaal-TO=3/metaal=4) · TypeBouwwijze Zwaar=1 · Ventilatie.Systeem (individueel=0/collectief=1).

**🔒 Te verifiëren in EPA (probe `out/probe_objecten.xml` staat klaar):** GrenstAan 5/6 + AVR · TypeBouwwijze 0/2 (Licht/Zeer zwaar) · Daktype (-1/0/2) · Glas D "dubbel met coating" · BodemisolatieKruipruimte "ongeïsoleerd".

**🔒 Nog te harvesten (gerichte EPA-exports):** verwarming (opwekker-subtype/WP-bron/aanvoertemp-klasse/afgifte/regeling) · koeling (vrijwel alle) · ventilatie (VentilatiesysteemType, ~30 subsystemen, TypeWTW, debiet/bypass/LUKA) · tapwater (Gaskeur/CW deels bevestigd; leidinglengte-8-klassen, DWTW) · ZonneEnergie (paneeltype, oriëntatie, bouwintegratie, fabricagejaar).

---

## 7. VABI-invoerlogica (if-this-then-that) om na te spelen
- Gebouwtype → sub-keuze (eengezins → woningtype; woongebouw → appartement-subtype zónder dak-keuze).
- `Gedeeltelijk plat dak` alleen geldig bij Vrijstaand.
- qv;10 gemeten? Nee → forfaitair (geen waarde); Ja → waarde verplicht. ✅ al correct in generator.
- Fossiele brandstof Ja → type {Aardgas/Propaan/Butaan/Stookolie}.
- Externe warmtelevering → toestel-sectie overslaan (rendement via afleverset).
- Warmtepomp → bron + temperatuurklasse + medium; WKK → vermogen + bouwjaar.
- WTW alleen bij ventilatiesysteem D/E; kanaal-velden alleen bij B-E.
- Gaskeur CW → CW-klasse verplicht; anders verbergen.
- (Zeer) zware vloer met lichter plafond Ja → afwijkende interne warmtecapaciteit.

---

## 8. Nij Begun-overlay
- **Gedeeld:** complete schil-geometrie, isolatie/begrenzing/oriëntatie, ventilatiesysteem/-balans, installatie-opwekkers.
- **Nij Begun-extra:** haalbaarheid per maatregel (asbest/lood/bereikbaarheid/vocht), spouwdikte (na-isolatie), foto-checklist + cat 2/3 meerwerk, maatregelen+prijsopbouw, **ventilatieplan-overlay met overstroom**.
- **Leeglaten bij alleen Nij Begun:** fijnmazige label-detailvelden (gemeten Rc/BCRG, kruipruimte-Rbf/ε, lineaire koudebruggen-tabel, ventilatiekanaal-LUKA, tapwater-meetgegevens, KWACO-verklaringen).
- **Form-implicatie:** stuur zichtbaarheid op `type_advies` (Basis/Uitgebreid/Label) + een Nij-Begun-vlag.

## 9. Wat de adviseur handmatig in Vabi blijft doen (golden rule)
BCRG-/kwaliteitsverklaring-opzoekingen (Rc/U/g, WTW-rendement, tapwater EN-meetgegevens, PV) — tool geeft vlag +
waarde als toelichting; exacte Rc/U/g (Vabi = rekenkern); geflagde enums tot bevestigd; lineaire koudebruggen
(Ψ kolom A/B); integrale Standaard-toets; detailopname-velden.

---

## 10. Geprioriteerd wijzigingsplan

> **STATUS 22-6-2026 — doorgevoerd (152 tests groen):** Wave 1 grotendeels, Wave 2 (naamconventie) en
> Wave 4 (ventilatie) zijn **af**. Nog open: enkele Wave-1-items (Ag-aftrek zolder, rekenzone-split-flag,
> per-wand isolatie), de MagicPlan-velden die login vereisen (Qv10 gemeten?), en de EPA-afhankelijke
> waves 3 + 5. Zie de ✅-markeringen hieronder.

### WAVE 1 — Geverifieerde quick-wins, GEEN EPA nodig
1. ✅ **Dak-`Hellingshoek` enum (3 hellend / 6 plat)** — **GEDAAN + getest (141 groen).**
2. ✅ **Perimeter-guard** — alleen bij vloer-begrenzing grond/kruipruimte/kelder (ISSO §8.3). GEDAAN.
3. ✅ **Gebouwhoogte** uit `opname.gevelhoogte_m` (vrije float; was sjabloon 7,60). GEDAAN.
4. ✅ **AOR/AOS/sterk-geventileerd basis = buitenlucht (0)** in `_grenst_aan_code` (basis-bewust). GEDAAN.
5. 🔜 **Per-vloer/per-wand `Isolatie aanwezig`** loskoppelen (parser leest nu nog projectbreed isol voor de gevels).
6. ✅ **`Qv10 gemeten?`** in de PARSER. 🔜 het MagicPlan-FORMveld toevoegen (vereist login; spec in form-spec).
7. ✅ **Kozijn A/B/C doorzetten** (`_norm_kozijn_mat`) i.p.v. hardcode. GEDAAN.
8. 🔜 **Ag-aftrek** zolder <1,5 m + Ag op 2 decimalen (zolder-/vide-opp nog onvoldoende uit MagicPlan).
9. 🔜 **Sanity-flag rekenzone-splitsing** (vereist thermische massa per verdieping; nu projectbreed).
10. ✅ **MAX_AFVOER_PER_VENTIEL verzonnen drempel** uit `ventilatie.py`. GEDAAN.

### WAVE 2 — Per-wand begrenzing-model (parent/child) ✅ GEDAAN (via naamconventie)
11. ✅ Wand-naamconventie (`AOR`/`GROND`/`KELDER`/`AVR`...) → parser zet gevel-begrenzing → raam/deur erven; AVR uit de schil. Getest. 🔜 nog: gevel-grond-splitsing (diepte onder maaiveld) bij souterrain.

### WAVE 3 — Probe-verificatie ✅ GEDAAN (22-6, EPA live)
12. ✅ `out/probe_objecten.xml` in EPA geïmporteerd + labels afgelezen → **TypeBouwwijze 0=Licht/1=Zwaar/2=Zeer zwaar**, **GrenstAan 0-9** (dropdown-index=code), **Daktype 0/1/2** — allemaal gewired (vabi/refs/grenstaan_mapping.md). Import-veiligheid bewezen.

### WAVE 4 — Ventilatie volgens de NIJ BEGUN-VUISTREGELS ✅ GEDAAN (rekenkern)
13. ✅ `ventilatie.py` herzien: **0,7 per verblijfsgebied** (min 7 l/s/leefruimte) + afvoer 21/14/7 + balans + **overstroom** + **geen-afvoer-in-slaapkamer**-waarschuwing + vuistregel-checklist; verzonnen drempel eruit. Getest. 🔜 nog: de plattegrond-**overlay** (toevoer/afvoer/overstroom-symbolen) + `Ruimte`/`Ventilatie`-velden voor de volledige balans-tabel.

### WAVE 5 — Installaties VABI-getrouw (HARVEST-gedreven)
14. Tapwater-blok (deels bevestigde codes) + form Verwarming-detail/Koeling/Zon; **PV-sjabloonknoop** uit een echte EPA-PV-export; gerichte harvests (WP/radiator-vloer/koeling/WTW/DWTW); installatie-dekkingsrapport.

### WAVE 6 — Schil-detail + samenvoegregel
15. Rieten dak, paneelconstructies, zonwering (A-I), overstek/belemmering, samenvoeg-/splitsguard, verticale hart-op-hart, hart-op-hart alleen voor+achtergevel.

**Aanbevolen eerste stap:** Wave 1 (allemaal bevestigde-code-fixes, geen EPA, raken geteste bestanden) in één
PR + testsuite, en parallel `probe_objecten.xml` aanleveren zodat Wave 3 direct kan. **OneDrive-valkuil:** `.py`
bewerken met sync gepauzeerd + `ast.parse`-check na elke save.
