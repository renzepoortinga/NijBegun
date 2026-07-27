# MagicPlan-inmeetgids — controlematen voor een 100% kloppende geometrie

> Veldgids: zó scan je een woning in MagicPlan én controleer je de maten, zodat de geometrie
> (m² per vlak, Ag, verliesoppervlak) klopt vóór de VABI-import. Aanvulling op
> docs/OPNAME-WERKINSTRUCTIE.md (per-kamer-werkwijze) — dit is de MEET-laag eronder.
> Vuistregel: **MagicPlan meet, jij controleert.** Elke verdieping 3 controlematen; wijkt er één
> >2% af → die kamer opnieuw scannen, niet "wegcorrigeren".

## 0. Vóór je begint (2 min)
- [ ] iPad/telefoon **opgeladen** + MagicPlan ingelogd in de juiste workspace (R.poortinga)
- [ ] **Laserafstandsmeter** mee (de controle), rolmaat (kruipruimte/diktes), zaklamp, endoscoop
- [ ] Nieuw project: adres als projectnaam · **eenheden = meters** · juiste template (Nij Begun)
- [ ] BAG-oppervlakte (Ag) van tevoren opgezocht (staat op de lead na de BAG-knop) → dit is straks je eindcontrole

## 1. Scannen per kamer (de basis)
1. Scan **kamer voor kamer**, houd het toestel op borsthoogte, beweeg rustig, sluit de polygon netjes.
2. Direct na elke scan: **1 controlemaat per kamer** — meet met de laser de **langste wand** en vergelijk
   met MagicPlan. Verschil >2% (bv. >8 cm op 4 m)? → kamer opnieuw (hoeken opnieuw aantikken).
3. **Benoem de kamer meteen** (Woonkamer/Keuken/Badkamer/Slaapkamer 1…): de namen sturen de
   ventilatieberekening (verblijfsgebied) én per-vloer-overrides (bv. "Slaapkamer AOR").
4. Buitenmuren meteen benoemen: **voorgevel / achtergevel / linkergevel / rechtergevel** (links/rechts
   gezien vanaf de straat). Afwijking in de naam: `Achtergevel AOR garage`, `buurwand AVR`, `… narekenen`.

## 2. De 7 controlematen (per woning)
| # | Wat | Hoe | Waarom |
|---|---|---|---|
| 1 | **Langste wand per kamer** | laser vs. MagicPlan, ±2% | scan-drift per kamer vangen |
| 2 | **Verdiepingshoogte** (vloer–plafond, per bouwlaag) | laser verticaal, invullen bij de verdieping | stuurt gevel-m² — fout hier = fout op ALLE gevels |
| 3 | **Gevelhoogte buiten** (maaiveld–goot; + nokhoogte bij schuin dak) | laser buiten, veld "Gevelhoogte (m)" (Object-form) | gebouwhoogte + dak-geometrie |
| 4 | **Footprint vs. BAG** | som kamers begane grond + muurwerk ≈ BAG-pand-oppervlak | systematische scan-fout zichtbaar |
| 5 | **Ag-controle** | MagicPlan totaal gebruiksoppervlak ≈ BAG-Ag (±5%) | Ag stuurt de Standaard-toets (kWh/m²!) |
| 6 | **Wanddikte** | meet in een deur- of raamnegge (kozijnsponning), noteer | binnen- vs. buitenmaat; spouwcheck |
| 7 | **Raam B×H per raam** | rolmaat/laser — dit is de enige maat die je écht per stuk zelf meet | glas-m² per oriëntatie |

**Sneltips ramen:** identieke ramen → meet er **één** en kopieer 'm in MagicPlan; gebruik presets voor
standaard deurmaten; kleine ruitjes <0,65 m² mag je gewoon invoeren (de tool rekent ze automatisch als
0,65 m², Nij Begun-regel).

## 3. Het dak (grootste foutenbron)
- **Standaard zadeldak:** vul in Constructies het geometrie-blok (vloerbreedte · nokhoogte · knieschothoogte ·
  kopgevel-oriëntaties) → de tool rekent de schuine m² + kopgevel-driehoeken vóór.
- **Alles wat afwijkt (SOBOLT-stijl, aanbevolen):** vul per **Dakvlak N** direct het **oppervlak (m²)** in —
  ingevulde m² **wint altijd** van de geometrie-berekening. Meet: schuine lengte (nok→goot, laser langs het
  dakbeschot op zolder) × breedte. Plat dak = footprint van dat deel.
- Per dakvlak: type · oriëntatie · hellingshoek · isolatie-boom · begrenzing (dak boven onverwarmde
  berging = AOR!). Tweede/derde dakvlak alleen aanvinken als het er echt is.
- **Controle:** som dakvlakken ≥ footprint bovenste verdieping (schuin dak is altijd groter dan plat).

## 4. Wat je verder invoert (waar → welk form)
- **Object** (projectniveau): bouwjaar · woningtype · **oriëntatie voorgevel** (de tool leidt de andere
  3 gevels af) · gevelhoogte · Ag-aftrek zolder · renovatiejaar · Qv10 (ALLEEN indien gemeten) · 2 foto's
  (vooraanzicht + huisnummer, verplicht).
- **Constructies** (projectniveau, per bouwdeel = de standaard): gevel/vloer/dak → VABI-beslisboom
  (invoer → isolatie Ja/Nee/Onbekend → dikte of bouwjaarklasse → spouw) + dak-geometrie/dakvlakken.
- **Installaties**: **ventilatie A–E + subsysteem** (de Nij Begun-kern; zie ventilatie-herkennen-gids).
  Verwarming/tapwater/PV = alleen voor het energielabel, mag je overslaan voor Nij Begun.
- **Per element** (tik op wand/vloer/raam/deur — alléén bij afwijking): begrenzing · isolatie ·
  isolatiedikte · Rc-bron · rekenzone. **Raam: alleen Type glas kiezen** — kozijn/rooster/paneel
  defaulten (hout-kunststof · geen rooster · raam). **Paneel:** zet Raam/paneel op "Paneel" → dichte
  constructie (de tool pakt het isolatie-beslisschema; verfijnen kan in de webapp-opname).
- **Foto's**: per bouwdeel overzicht + detail (boorgat/spouw, kruipruimte **met rolmaat in beeld**,
  dakisolatie met duimstok, typeplaatje ventilatie-unit).

## 5. Eindcheck vóór export (op de bank, 5 min)
- [ ] Elke buitenwand heeft een **gevelnaam** (voor/achter/links/rechts) — geen naamloze buitenmuren
- [ ] Oriëntatie voorgevel ingevuld (1 veld — stuurt alle 4 gevels)
- [ ] Elk raam heeft een **glastype** · panelen op "Paneel" gezet
- [ ] Dak: per vlak m² (of geometrie-blok volledig) + begrenzing
- [ ] Vloer: begrenzing klopt (kruipruimte/grond/AOR) + kruipruimte-foto met rolmaat
- [ ] Ag ≈ BAG (±5%) en verdiepingshoogtes ingevuld
- [ ] Ventilatie A–E + verplichte foto's aanwezig
- Dan: **exporteer de Statistics-CSV** → webapp → Opname-stap → daar zie je alles terug en draai je
  `vabi/sanity.py`-checks (outliers/ontbrekende oriëntaties) automatisch mee.

## 6. Isolatiedikte vaststellen — praktijktrucs (ISSO-Praktijkboek Energieprestatie, 2e druk)

De isolatiedikte stuurt de Rc (NTA bijlage I.2.1.4: `Rc = d/0,045 + Rad`). Kun je 'm meten, meet 'm —
dat scheelt een forfaitaire (conservatieve) waarde en dus een slechter label.

- **Prikpen** — hulpmiddel om de dikte van zachte isolatie te bepalen (glas-/steenwol, vlokken).
- **Boorgaten in de gevel**, vooral op de **kruisingen van de stootvoegen**, verraden **na-isolatie in
  de spouw**. Zie ze je: de spouw is (deels) gevuld — noteer + foto.
- **Meet de constructiedikte nabij een kozijn**: meet de totale dikte in de dagkant en trek de bekende
  lagen (binnen- en buitenspouwblad) eraf → wat overblijft is de spouw/isolatie.
- **Dak**: is er een **dakluik**, dan kun je daar de dikte van de dakconstructie bepalen. Bij
  **dakramen**: meet de dikte in de dagkant, maar **let op de opstaande randen** (die tellen niet mee).
- **Reflecterende folie**: telt alleen mee als de **spouw ≥ 20 mm** is (NTA tabel C.3) — bij een
  smallere spouw vervalt het effect.
- Lukt meten niet? Kies dan **"isolatiedikte onbekend"** + de **bouwjaarklasse**; nooit gokken. Bij een
  aantoonbare **kwaliteitsverklaring** zet je Invoer op *Kwaliteitsverklaring* en de **BCRG-code** in
  Vabi (let op: niet elke DoP staat in de BCRG-databank).

## Zakkaart
**Scan → laser-check per kamer (±2%) → benoem kamer + gevels → ramen B×H → verdiepingshoogte +
gevelhoogte → dak-m² per vlak → Ag ≈ BAG → forms (Object/Constructies/Ventilatie) → foto's → CSV.**
Twijfel = niet gokken: noteer + foto → verfijnen in de webapp of Vabi.
