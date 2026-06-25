# Nij Begun kennisbank — eisen voor het isolatieplan (compliance-spec voor de webapp)

Bron: **adviseurs-nijbegun.nl/support** (de officiële Nij Begun-kennisbank). Dit document vat de eisen samen
waaraan een isolatieplan moet voldoen, zodat de **webapp** ze afdekt vóór "exporteren/opleveren". Een plan dat
afwijkt wordt afgekeurd. Belangrijkste artikelen (URLs om bij te werken zodra Nij Begun ze wijzigt):
- Vuistregels voor ventilatie — `/solutions/articles/206000062898-vuistregels-voor-ventilatie`
- **Beoordelingsformulier Isolatieplan** — `/solutions/articles/206000045218-beoordelingsformulier-isolatieplan`
- Handleiding Fotowerkwijze Isolatieplan · Werkwijze isolatieplan en kwaliteit · Werkwijze endoscopisch onderzoek
- Handleiding woningopname tot isolatieplan · "Welke onderdelen hebben de meeste invloed voor het behalen van de standaard?"

## ⭐ Beoordelingsformulier — de webapp-checklist vóór indienen (mirror dit 1-op-1)
Nij Begun keurt op deze criteria. De webapp moet bij "Afronden" een **"klaar voor indienen"-check** tonen die
elk punt afvinkt (✔/✖ + reden), zodat Renze niet afgekeurd wordt.

**A. Compleetheid (alle vinkjes = volledig):**
- [ ] Adviseur staat in de open house
- [ ] Lay-out van Maatregel 29 is bewaard gebleven  → (fill_template mag de template-structuur niet breken)
- [ ] Geen hiaten in het formulier  → (alle placeholders/tabellen gevuld)
- [ ] **Adres én de foto op de voorkant komen overeen**  → (foto voorkant + huisnummer in de webapp; adres-match)
- [ ] Isolatieplanformulier staat op pagina 6
- [ ] **Huidige woningstaat volledig ingevuld**  → (V1–V6 + warmteverlies uit de VABI-export/result_reader)
- [ ] Samenvatting is helder voor SNN
- [ ] **Maatregelcodes correct**  → (uit de catalogus; measures.py)
- [ ] **Vaste bijlage "Waarom ventileren" toegevoegd**
- [ ] **Ventilatieberekening toegevoegd**  → (ventilatie.py + visueel ventilatieplan)
- [ ] **Fotoblad toegevoegd**  → (foto/checklist.py)

**Inhoud:**
- **A. Doeltreffendheid** — *Leidt de geadviseerde set tot de Standaard?* (BENG/Standaard/Streefwaarden). → de
  **VABI-rondtrip + Standaard-toets** (result_reader: energiebehoefte ≤ Standaard) is hét bewijs hiervoor.
- **B. Juiste set maatregelen** — technisch juist + logisch onderbouwd vanuit de opname (bv. géén binnenwand-
  isolatie als er spouw is). → measure_engine kiest passend per opname; webapp toont de onderbouwing.
- **C. Technische/praktische uitvoerbaarheid** — bereikbaarheid, ruimte, vocht (bv. kruipruimte diep/toegankelijk/
  droog genoeg?). → dossier.Haalbaarheid + foto-onderbouwing.
- **D. Toekomstbestendigheid** — bouwfysisch verantwoord; binnenklimaat/vocht-risico; materiaalkeuzes onderbouwd
  (dampremmende laag, ruimtefunctie onder koud dak, ventilatie). → advies_text + ventilatie-na-isoleren-regel.

**Eindbeoordeling:** Goedgekeurd / Afgekeurd.

## Ventilatie (Vuistregels voor ventilatie) — BEVESTIGD, klopt 1-op-1 met `ventilatie/nijbegun_vuistregels.md`
Stappenplan: opp → minimale **afvoer** (keuken 21 · bad 14 · toilet 7 l/s; elke leefruimte ≥7) → afvoerpunten
(natte ruimten) → **toevoer** → aan-/afvoer in **balans**. 10 aanvullende regels (overstroom max 2 deuren; ≥50%
van buiten; geen afvoer in slaapkamer; raambreedte bepaalt rooster-toevoer; >15 l/s onder deur → deurrooster;
geluid; af/toevoer niet te dicht bijeen; toevoer via roosters óf WTW; toevoer ~6–10 m / 2 m van rookkanaal;
onvoldoende roosters → ramen vervangen/doorvoer). C4c = CO₂-sturing op afvoer woonkamer + hoofdslaapkamer.

**Toevoer via roosters:** het artikel geeft GEEN l/s-per-rooster — bron is **ISSO-kleintje Ventilatie**
(raambreedte → roosterlengte; zelfregulerend?; evt. dakraam-toevoer). Het visuele ventilatieplan toont daarom de
benodigde toevoer per ruimte + "verdeel over roosters (raambreedte)"; de exacte rooster-l/s blijft adviseur/ISSO-
kleintje (niet gokken — golden rule). Geveldoorvoeren/deurroosters staan (nog) NIET in de catalogus M29.

Capaciteitstabel (ISSO-kleintje / BBL): verblijfsgebied 0,9 (min 7) · verblijfsruimte 0,7 (min 7) · verblijfs-
gebied met kooktoestel <15 kW 0,9 (min 21) · toilet 7 · bad 14 dm³/s. **Nij Begun (bestaande bouw) = 0,7 per
verblijfsgebied** (niet de nieuwbouw-0,9) — zo gewired in `ventilatie/ventilatie.py`.

## Fotowerkwijze (Handleiding Fotowerkwijze Isolatieplan) — voedt `foto/checklist.py` + de webapp-fotostap
Foto's zijn VERPLICHT (projectdossier compleet · maatregelen onderbouwen · uitvoerders informeren · kwaliteits-
commissie). Algemeen: overzichtsfoto per bouwdeel; **geen persoonlijke bezittingen/bewoners in beeld**; **min. 1
detailfoto per categorie-2-prijs**; scherp/recht/goed belicht (zaklamp/flits); systematisch (overzicht→detail);
alleen foto's die de geadviseerde maatregel onderbouwen. **Kwaliteit:** ≥8 MP · **SNN-upload max 5 MB** ·
duidelijke bestandsnamen · digitaal mee met het plan.
- **V1-1 spouwmuur:** overzicht per gevel · boorgat + binnenzijde spouw · voegwerk · bijzonderheden (betonlatei/
  overkapping) · (hoogwerker→staplaats).  **V1-2 buitengevel:** overzicht per gevel · aansluiting maaiveld + dakrand.
  **V1-3 binnengevel:** overzicht per ruimte · aansluitingen (gevel/plafond, /vloer, /kozijn) · cat-2 (WCD/leiding/radiator).
- **V2 glas/kozijn:** overzicht gevels met glas · glaslat.  **V3-1 begane grond:** foto ín de kruipruimte (niet betreden) ·
  diepte **met duimstok/rolmaat zichtbaar** · kruipluik + locatie.  **V3-2 zolder/vliering:** overzicht vloer · aansluiting dak/muur.
- **V4-1 schuin dak binnen:** overzicht · dakbeschot (materiaal/kieren/oude lekkage) · constructie (balken/spanten/gording-
  diepte) · uitbouw/dakkapel · aansluitingen (dak/muur, /nok, /dakkapel/dakraam) · doorvoeren · installaties.  **V5 ventilatie: n.v.t.**

## Werkwijze & kwaliteit (Werkwijze isolatieplan en kwaliteit) — proces + een KERNREGEL voor de maatregel-selectie
- Het isolatieplanformulier (basis van de subsidieaanvraag) moet **volledig**; n.v.t.-regels mag je weghalen. Handmatig
  óf **geautomatiseerd via de API** (link via leveranciers@nijbegun.nl). De **opmaak van het voorbeeld-isolatieplan is
  de norm** — afwijken → aanpassen.
- **Tweetraps kwaliteitscheck** (kwaliteitscommissie): (1) compleetheid, (2) inhoud. Begin: eerste **4 plannen** +
  100%-check + steekproef-huisbezoeken. Indienen via leveranciers@nijbegun.nl → akkoord → delen met bewoner.
- ⭐ **Standaard vs 30% ISDE (cruciaal voor de webapp-maatregel-selectie):** maatregelen die **nodig zijn om de
  Standaard te halen** gaan in de **M29-subsidietabel** (50/100% subsidiabel). Maatregelen die bouwfysisch **wenselijk**
  zijn maar NIET nodig voor de Standaard (bv. dakkapel-wangen isoleren tegen vocht, een deur vervangen) **adviseer je
  wél aan de bewoner**, maar die vallen onder **30% ISDE** en horen **NIET in de M29-tabel**. → De webapp moet twee
  buckets tonen: **"nodig voor de Standaard" (subsidietabel)** vs **"geadviseerd, 30% ISDE" (buiten de tabel)**.

## Voorbeeldplannen (de output-norm) — PDF-bijlagen, lezen bij het bouwen van de output
4 voorbeeld-isolatieplannen (PDF, ~1,5 MB): **bouwjaar 1930 · 1970 · 1993 · 2002** (folder 206000101610). Dit is de
gold-standard voor opmaak/inhoud van het isolatieplan + het ventilatieplan-beeld. Bij het bouwen van `fill_template`/de
webapp-output deze PDF's lezen en de output 1-op-1 matchen (lay-out M29 bewaren — Beoordelingsformulier-eis).

## Artikel-index (adviseurs-nijbegun.nl/support/solutions/articles/<id>)
**Werkwijze en handleidingen (folder 206000069621):** fotowerkwijze 206000045149 · werkwijze+kwaliteit 206000045180 ·
beoordelingsformulier 206000045218 · endoscopisch onderzoek 206000045781 · maatregelencatalogus 206000047484 (PDF
Handleiding-Maatregelencatalogus-04022026) · leerling-meester B→U 206000052392 / nvt→B 206000052393 · vuistregels
ventilatie 206000062898 · woningopname→isolatieplan 206000065616 · beslisschema garage (ISSO 82.1 7e druk) 206000076893.
**Voorbeeldplannen (206000101610):** 2002=206000065627 · 1993=206000065625 · 1970=206000065628 · 1930=(zie folder).
**FAQ — Algemene vragen (206000055941, 33 stuks; tool-relevant):** maatregelen niet vergoed 206000044949 · thermische
schil aanpassen 206000045103 · opnametools 206000045104 · isolatieplan verplicht 206000044944 · 30%-subsidieplafond
206000044942 · waar maatregelcatalogus 206000045071 · waarom foto's 206000045106 (+ Vabi/Uniec, ventilatieberekening-
verplicht, garagedeur-doelwaarden — te harvesten zodra relevant).
> Te harvesten bij de betreffende bouwstap: de voorbeeldplan-PDF's (output-match), woningopname-handleiding, endoscopie,
> garage-beslisschema, en de resterende FAQ's. URLs/ID's hierboven; haal ze gericht op wanneer die stap aan de beurt is.
