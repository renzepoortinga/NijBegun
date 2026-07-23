# NTA 8800:2025+C1:2026 gelezen — analyse tegen onze tool

Datum: 23-7-2026. Bron: `NTA 8800_2025+C1_2026 nl.pdf` (1163 pagina's, geconsolideerde versie,
aangewezen per 29-5-2026). Gelezen: H5 (energieprestatie-indicatoren + Standaard), H6
(gebouwbegrenzing/thermische zone/verliesoppervlak/dakoppervlak), H7 (warmte-/koudebehoefte,
structuur), H8 (transmissie: U-, raam-, deur-, thermische-brug-bepaling), H11 (ventilatie:
infiltratie qv10), H17 (klimaat), en bijlagen C (Rc), E (materialen/λ), I (forfaitaire Rc/U/ψ),
K (meetregels AT/Acon).

---

## 0. Conclusie in één alinea

**Onze architectuur klopt en wordt door de norm bevestigd.** De NTA 8800 is de bepalingsmethode;
de eigenlijke rekenkern (maandelijkse warmtebalans, grondtransmissie via NEN-EN-ISO 13370,
benuttingsfactoren, primaire-energie-sommatie) is precies het stuk dat wij bewust bij Vabi EPA-W
laten — en dat is een verstandige keuze, want dat deel is enorm (honderden formules over 17
hoofdstukken + 28 bijlagen) én valt onder de tool-validatieplicht van Nij Begun. Wat de norm ons
wél oplevert zijn **concrete, verifieerbare invoer- en controleregels** die we nu deels missen of
impliciet aan Vabi overlaten. Hieronder 7 verbeterpunten (A–G), oplopend van "quick win" naar
"nieuw gereedschap", plus een eerlijke afweging over zelf rekenen.

---

## 1. Wat de norm precies is (en waarom onze gouden regel juist is)

- De NTA bevat **geen eisen** — alleen de bepalingsmethode. De eisen (BENG-grenswaarden,
  labelklassen, Standaard) staan in het Bbl / de labelsystematiek. NTA §5 neemt die eisen wél op
  "uit oogpunt van bruikbaarheid", maar ze zijn beleidsmatig.
- Drie hoofdindicatoren (§5.3.1): **Ewe;H+C;nd;ventsys=C1** (energiebehoefte), **Ewe;PTot** (primair
  fossiel → bepaalt de labelklasse), **RER;PrenTot** (aandeel hernieuwbaar). Vanaf 29-5-2026 komen
  daar per EPBD IV twee indicatoren bij die óók op het label moeten: **het finale energiegebruik**
  (§5.3.5) en **de operationele broeikasgasemissies** (§5.5.6). → zie punt F.
- De methode is expliciet "inklapbaar": 80 % van de dagelijkse praktijk zit in 20 % van de tekst,
  met overal forfaitaire waarden als de detailinfo ontbreekt. **Dat 20 %-deel is precies wat wij
  automatiseren.** De norm bevestigt onze basisopname-route: forfaitaire Rc/U bij onbekende
  isolatie (bijlage I), forfaitaire ψ voor thermische bruggen (bijlage I.1), forfaitaire qv10 uit
  bouwjaar/gebouwtype (§11.2.5).
- Bevestiging van de goedkeuringspoort: de norm zelf zegt (bijlage I.2.1.3) dat gebruik van de
  forfaitaire "slechtste waarde" bij ontbrekende gegevens "nader moet worden vastgelegd in
  procedurevoorschriften (bijvoorbeeld een BRL)". Ons opnameproces valt onder ISSO 82.1 / BRL
  9500-W; zolang wij invoer leveren en Vabi rekent, blijven we in de handmatige adviseur-route.

---

## 2. Verbeterpunten in onze tool (geprioriteerd)

### A. `Als`-weging (`fls`) ontbreekt in de webapp-compactheid — NTA §6.7.3  ⭐ quick win

NTA §6.7.2/6.7.3: de verliesoppervlakte is **gewogen**:
`Als = Σ fls;i × AT;i`, met
- `fls = 0` voor inwendige scheiding / naar een AVR of andere rekenzone (adiabatisch);
- `fls = 1` voor buitenlucht, water, AOR, AOS, sterk geventileerd;
- **`fls = 0,7` voor grond of kruipruimte.**

Onze webapp (`dashboard/app.py`, rond regel 1099 en 1603) rekent:
```python
verlies = sum((s.oppervlakte_m2 or 0) for s in dos.schil
              if (s.begrenzing or "") != "AVR" and s.type not in ("kozijn", "paneel"))
```
Dit past AVR=0 correct toe, maar **telt vloeren op grond/kruipruimte voor 100 % mee** i.p.v. 70 %.
Daardoor overschat de getoonde **compactheid (Als/Ag)** de echte `Als`. Cosmetisch nu geen ramp — de
échte toets komt uit Vabi (`result_reader` leest `Verliesoppervlakte`/`Standaard` uit de export) —
maar het is een echte afwijking die verwarrend is als adviseur en gebruiker de webapp-waarde
vergelijken met de Vabi-waarde.

**Fix (klein):** voeg een `fls`-map toe en weeg. Grond/kruipruimte × 0,7, AVR/inter-zone × 0,
overige × 1. Meteen goed voor punt B.

### B. Standaard-eis zelf voorrekenen als sanity-check — NTA §5.3.2  ⭐ quick win

De Standaard voor woningisolatie is een **exacte formule** (NTA §5.3.2), alleen afhankelijk van
`Als/Ag` en twee vlaggen (grondgebonden vs. woongebouw, bouwjaar ≤ of > 1945):

| Type | Als/Ag < 1,0 | Als/Ag ≥ 1,0 |
|---|---|---|
| Grondgebonden, ≤ 1945 | 60 | 60 + 105 × (Als/Ag − 1) |
| Grondgebonden, > 1945 | 43 | 43 + 40 × (Als/Ag − 1) |
| Woongebouw, ≤ 1945 | 95 | 95 + 70 × (Als/Ag − 1) |
| Woongebouw, > 1945 | 45 | 45 + 45 × (Als/Ag − 1) |

Nu staat in `core/dossier.py` een **hardcoded demo-default** `standaard_eis_kwh_m2 = 70.0` en lezen
we de echte waarde pas terug uit Vabi. Met de gewogen `Als` uit punt A kunnen we de Standaard
**zelf voorrekenen** en tonen zodra de opname klaar is — nog vóór de Vabi-run. Dat geeft:
1. een 0-meting-verwachting ("deze woning moet onder ~55 kWh/m²"), en
2. een **kruiscontrole**: wijkt onze voorgerekende Standaard >1–2 af van wat Vabi teruggeeft, dan
   klopt de geometrie (Als/Ag) of het woningtype niet — precies het soort tikfout dat sanity.py nu
   nog niet vangt. Dit rekent geen NTA (blijft binnen de gouden regel: het is een beleidsformule,
   geen warmtebalans), maar het maakt de tool slimmer en foutbestendiger.

### C. Forfaitaire Rc uit isolatiedikte tonen als advies/controle — bijlage I.2.1.4

Bijlage I.2.1.4 geeft de forfaitaire Rc bij **bekende isolatiedikte** met één simpele formule:
```
Rc = d_iso / λ_equi;ntr + R_ad        (dikte afgerond op 10 mm)
λ_equi;ntr = 0,045 W/m·K  (tenzij bekend hoger)
R_ad = 0,36 (gevel) | 0,15 (vloer) | 0,22 (dak)   [+ luchtspouwtoeslag bij ≤30 mm]
```
Wij vángen de isolatiedikte al op in de opname (`isolatiedikte_mm` op elk `SchilDeel`) en
`constructie_generate.pick_dicht()` gebruikt 'm om het dichtstbijzijnde Vabi-sjabloon te kiezen —
maar we **tonen de eruit volgende Rc nergens**. `engine/advies_logic.py` triggert advies puur op
een dikte-drempel (`_DIKTE_OK = {gevel:80, dak:120, vloer:80}`), niet op de echte forfaitaire Rc.

**Kans:** reken de forfaitaire Rc uit dikte (formule hierboven — geen NTA-warmtebalans, gewoon een
bijlage-I-tabelformule) en gebruik 'm om:
- het advies te triggeren op **Rc t.o.v. STREEF** (gevel 5,0 / dak 6,5 / vloer 3,7) i.p.v. een ruwe
  dikte-drempel — nauwkeuriger, want 80 mm minerale wol ≠ 80 mm PIR;
- in het isolatieplan een **onderbouwde huidige Rc** te tonen ("gevel 90 mm → Rc ≈ 2,4") i.p.v.
  alleen "geïsoleerd, dikte 90 mm".

Dit is de eerste bouwsteen van de "constructieblad/Rc-calculator"-verkenning die al in
`docs/constructie-rc-tool-verkenning.md` ligt — en het is bijlage-I-forfaitair, dus toegestaan
zonder eigen NTA-rekenkern.

### D. Forfaitaire ψ thermische bruggen — bijlage I.1 (+ ΔUfor §8.2)

De thermische bruggen laten we nu volledig aan Vabi (terecht — de exacte ψ vergt 2D-detailmodellen).
Maar bijlage I.1 geeft **forfaitaire ψ-waarden per aansluitdetail** (tabel I.1 laagbouw, I.2
gestapeld; 24 resp. 25 detailposities, kolom A "voldoet aan aanvullende voorwaarden" vs. kolom B).
En §8.2 geeft de **forfaitaire ΔUfor-toeslag** die de hele bruggenpost in één opslag vangt
(tabel 8.1: gemiddelde U 0,8→0 · 0,6→0,05 · 0,4→0,10 W/m²K — hoe beter geïsoleerd, hoe hoger de
toeslag). Relevant voor ons omdat de tool nu de "hart-op-hart gevel-toeslag" bewust als losse
melding geeft (besluit 19-7); die melding kunnen we koppelen aan de juiste bijlage-I-detailpositie
zodat de adviseur weet wélke ψ hij in Vabi moet zetten. Geen nieuwe rekenkern nodig — een
**lookup-tabel + koppeling aan het opgenomen detail**.

### E. Meetregels AT/Acon — bijlage K vs. onze gevel-benadering

Bijlage K is de norm voor hoe je oppervlakten opmeet: `AT` (geprojecteerd, tot de adiabatische
afsnijvlakken) vs. `Acon` (voor de U-waarde). Kernpunten die onze parser raken:
- Ramen/deuren: `AT` = **binnenwerks kozijn** (dagmaat), niet het glas. Wij nemen raam-m² als
  totaal kozijnvlak — consistent, maar leg in de rekenwijze-gids expliciet de K.2-definitie vast.
- Gevel-`AT` loopt tot het **vloerpeil** (het deel onder vloerpeil telt niet mee, dat is ψ).
- Ons `assemble.py`/`statistics_csv.py` benadert de gevel-m² bij de MagicPlan-route met
  `4·√(footprint)·1,15 × hoogte − openingen` — een schatting die de adviseur in Vabi verifieert
  (staat zo in CLAUDE.md). Dat is een pragmatische keuze, maar bijlage K + de Essenhage-ijking
  laten zien dat de exacte regel "breedte × verdiepingshoogte per bouwlaag, bruto" is. **Advies:**
  benoem in de rekenwijze-gids per bouwdeel de K-afsnijregel die we benaderen, zodat de
  hart-op-hart/vloerpeil-afwijking traceerbaar is (we hebben Essenhage al als ijkpunt).

### F. Nieuwe EPBD IV-indicatoren op het label — §5.3.5 + §5.5.6  ⚠ deadline 29-5-2026

Vanaf 29-5-2026 staan er twee extra indicatoren op het energielabel:
- **Finaal energiegebruik** `EweFinal` (§5.3.5.1) en de EED-variant (§5.3.5.2);
- **Operationele broeikasgasemissies** (scope 1+2, §5.5.6.1).

`vabi/result_reader.py` leest nu `Labelklasse, IndicatorEnergiebehoefte, Standaard,
IndicatorPrimaireFossieleEnergie, TOjuliNTA8800, NettoWarmtevraagTbvEPV, Compactheid,
Gebruiksoppervlakte`. Als Vabi in de 2025-versie deze twee nieuwe velden in het monitorbestand
gaat schrijven (waarschijnlijk `EweFinal` / een broeikasgasveld), moeten we `KERN` in result_reader
uitbreiden zodat we ze in het rapport kunnen tonen. **Actie:** na de eerste Vabi-export met de
2025-methode het monitorbestand harvesten (zoals we altijd doen) en de nieuwe veldnamen toevoegen.
Voor Nij Begun (schil-focus, Standaard) verandert er niets aan de kern, maar voor het energielabel-
spoor (BRL 9500-W) is dit een must vóór 29 mei.

### G. Ventilatie/infiltratie — §11.2.5 (we doen het goed, kans op zelf-controle)

NTA §11.2.5 (infiltratie): `qv10;lea;ref = ftype × fy × qv10;spec;reken`, met de bouwjaar/renovatie-
correctie `fj` (tabel 11.13: <1970 → 3,0 … ≥2010 → 0,7) en gebouwtype-correctie `ftype`
(tabel 11.14). Belangrijk: **het renovatiejaar mag alléén als er (nagenoeg) volledige renovatie is
— alleen kierdichting van kozijnen telt niet.** Onze webapp gebruikt exact de renovatiejaar-variant
voor de Qv10 na maatregelen (`app.py` `_toekomstige_staat` → `renojaar`), wat klopt met §11.2.5 en
met hoe het portaal het doet. Alleen tekstueel scherpstellen dat de renovatiejaar-variant niet mag
bij een pakket dat alleen kierdicht. Onze ventilatie-vuistregel (0,7 dm³/s·m²) is Nij Begun/
Bouwbesluit-normstelling voor het **ventilatieplan**, los van de NTA-energieberekening — correct
gescheiden gehouden.

**Los, klein:** tabel I.5 (forfaitaire Rc per bouwjaarklasse: gevel 1965-75 → 0,43 · 1992-2014 →
2,5 · vanaf 2021 → 4,7, enz.) is de autoritatieve bron achter onze bouwjaarklasse-gids. Onze
klasse-grenzen komen uit de echte Vabi-export (golden-rule-conform), dus die kloppen — maar leg in
de gids een verwijzing naar NTA tabel I.5 zodat de Rc-getallen in de gids traceerbaar zijn.

---

## 3. Zelf rekensoftware maken — eerlijke afweging

**Kan het? Technisch grotendeels ja. Verstandig? Alleen gefaseerd, en niet als vervanging van Vabi.**

Wat "de NTA zelf rekenen" concreet betekent, is de volledige keten uit H7–H16 bouwen:
maandelijkse warmtebalans per rekenzone (H7), grondtransmissie via NEN-EN-ISO 13370 met periodieke
penetratiediepte en faseverschuiving (bijlage D — de formules D.4 t/m D.16 zijn fors), benuttings-
factoren en tijdconstante (§7.8), zontoetreding per oriëntatie/helling met beschaduwing (§7.6 +
bijlage A), en dan alle installatierendementen (H9–H13 + bijlagen M–W) en de primaire-energie- en
hernieuwbaar-sommatie (§5.5/5.6). Dat is honderden formules, tientallen forfaitaire tabellen, en
het verwijst door naar ~20 losse NEN-EN-ISO-normen die je óók moet implementeren. Realistisch:
**vele mensmaanden werk, plus permanent onderhoud** (de NTA wordt herzien; 2025 verving 2024
verving 2023).

Drie harde blokkers los van de bouwtijd:
1. **Validatieplicht.** Een gedistribueerde/zelfrekenende tool voor energielabels/Nij Begun moet
   worden gevalideerd tegen de 10 referentiewoningen (BCRG/Nij Begun-eis; staat al in onze
   constraints). Zodra we zelf rekenen, verliezen we de "handmatige adviseur + geattesteerde
   software"-route en komen we in het certificeringsregime.
2. **Aansprakelijkheid.** Bij zelf rekenen ligt de rekenfout bij ons; bij Vabi ligt die bij de
   geattesteerde leverancier. Voor een eenmanszaak is dat een groot verschil.
3. **Onderhoudslast.** Elke NTA-herziening en elke wijziging in een onderliggende EN-ISO-norm moet
   je narekenen en hervalideren.

**Wel zinvol — en dat is de kern van dit advies — zijn de "halve" rekenstappen die géén NTA-
warmtebalans zijn maar wel echt rekenwerk toevoegen, allemaal bijlage-forfaitair en dus binnen de
gouden regel:**

- **Rc uit isolatiedikte** (bijlage I.2.1.4, punt C) — één formule, direct nut.
- **Standaard-eis** (§5.3.2, punt B) — vier lineaire formules, sanity-check op de geometrie.
- **Forfaitaire ψ-lookup** (bijlage I.1, punt D) — een tabel, koppelt opname aan Vabi-invoer.
- **Lagen-Rc-calculator** (bijlage C.1 + E: `Rc = Σ d/λcalc`, met de λ-tabellen E.10–E.17) — dit is
  de constructieblad-tool uit de verkenning. Het is geen labelinvoer (basisopname gebruikt
  forfaitair), maar wél waardevol als advies/tekening voor de aannemer, en het is puur
  materiaal-Rc, geen energiebalans.

Die vier samen geven 80 % van de "voelt als eigen rekensoftware"-waarde tegen ~5 % van de bouw- en
juridische kosten van een echte NTA-kern. Een volledige eigen EPA-motor bouwen zou ik **niet**
aanraden zolang Vabi de geattesteerde kern levert en Nij Begun bij voorkeur RVO-geaccrediteerde
software wil (punt 7c uit de tool-eisen).

---

## 4. Voorgestelde volgorde

1. **A + B samen** (fls-weging + Standaard-formule): kleine PR in `dashboard/app.py` +
   `core/dossier.py`, meteen betere 0-meting en een geometrie-sanity-check. Laagste risico, direct
   nut. Uitbreiden in `vabi/sanity.py`: waarschuw als eigen Standaard ≠ Vabi-Standaard.
2. **C** (Rc uit dikte): nieuwe helper (bijv. `engine/rc_forfaitair.py`), advies-triggering in
   `advies_logic.py` op Rc i.p.v. dikte, en Rc tonen in het isolatieplan. Eerste blok van de
   constructieblad-tool.
3. **F** (nieuwe label-indicatoren): zodra een Vabi-2025-export beschikbaar is, monitorbestand
   harvesten en `result_reader.KERN` uitbreiden. Deadline-gedreven (29-5-2026) voor het
   energielabel-spoor.
4. **D + E** (ψ-lookup + K-meetregels documenteren): tabel I.1/I.2 als lookup, en de rekenwijze-gids
   aanvullen met de bijlage-K-afsnijregels per bouwdeel.
5. **Lagen-Rc-calculator** (constructieblad): grotere klus, verkenning ligt klaar, bouw pas na 1–4.

Geen van deze stappen doorbreekt de gouden regel: het blijven forfaitaire bijlage-formules en
beleidsformules, geen eigen NTA-warmtebalans. Vabi blijft de geattesteerde rekenkern.
