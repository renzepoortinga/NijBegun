# Opname-werkinstructie — MagicPlan, kamer voor kamer 🏠

## HET STAPPENPLAN (definitief — 11-7-2026, gelijk aan de live MagicPlan-forms)

### Vooraf op kantoor (5 min)
1. Webapp: lead -> **[+ Project]** (adres/BAG/bouwjaar komen mee). Noteer de **BAG-Ag** (eindcheck straks).
2. MagicPlan: nieuw project (adres als naam, meters als eenheid).

### In de woning — de 3 project-forms (1x invullen, ~5 min)
3. **Object**: Bouwjaar (verplicht) · Woningtype · **Orientatie voorgevel** · Gevelhoogte (laser buiten) ·
   Renovatiejaar (alleen bij ingrijpende renovatie) · Qv10 (ALLEEN indien gemeten) · Ag-aftrek zolder (mag later) ·
   **foto vooraanzicht + huisnummer** (verplicht).
4. **Constructies**: GEVEL-beslisboom (invoer -> isolatie Ja/Nee/Onbekend -> dikte of bouwjaarklasse -> spouw) +
   thermische massa + begrenzing-default · VLOER-boom · **DAK: per dak het type tikken** — een zadeldak is
   **1 dak** (de tool maakt beide vlakken + kopgevels zelf); Dak 2/3 alleen voor een écht extra dak
   (aanbouw/berging). Per dak: maten van dat type + evt. dakkapel (aantal/B/H/D) + evt. dakramen
   (aantal/m2/glas) + de dak-isolatieboom ("Dak N - invoer"). **Knieschot? Altijd de knieschothoogte invullen** bij de nok-methode (Essenhage: zonder knieschot 45° i.p.v. de echte 30°) — of meet de helling direct met een hellingsmeter-app. Kwaliteitsverklaring alléén kiezen als je
   een factuur/verklaring hebt (anders Beslisschema!).
5. **Installaties**: Ventilatie A-E + subsysteem (zakkaart in de ventilatie-gids). Verwarming/tapwater/PV =
   energielabel, mag je overslaan voor Nij Begun.

### Per kamer (de scan-loop, herhaal per ruimte)
6. **Scan** de kamer -> **laser-check** de langste wand (verschil >2% = opnieuw scannen).
7. **Benoem de kamer** (Woonkamer/Keuken/Badkamer/... — stuurt de ventilatieberekening).
8. Tik de **buitenwand(en)** aan -> **Gevelnaam** kiezen: Voorgevel / Achtergevel / Linkergevel /
   Rechtergevel / Buurwand (AVR). Leeg = binnenwand. GEEN namen typen.

   **⭐⭐ DE ZEKERSTE WEG — meet de gevelbreedte (nieuw 14-7):** vul in het Object-form per gevel
   **"Voorgevel/Achtergevel/Linkergevel/Rechtergevel - breedte (m)"** in (net als de dak-vloerbreedte).
   Dan rekent de tool **breedte × verdiepingshoogte per bouwlaag** en negeert de (foutgevoelige) wandsom
   volledig — geen dubbeltelling mogelijk. Eén meting per gevel = rock-solid. Tik je geen breedte, dan
   valt de tool terug op de som van je getikte wanden (zie de tik-regels hieronder).

   **⭐ DE GOUDEN TIK-REGELS (voor de wandsom-fallback; Essenhage-les 14-7 — gevel was +26% door deze fouten):**
   - **Meerdere gevels per kamer mag gewoon** (hoekwoning: achtergevel + rechtergevel; doorlopende
     woonkamer-keuken: drie; vrijstaand: vier) — dat zijn verschillende oriëntaties en prima.
     Wat NIET kan: twee **tegenover elkaar liggende** wanden (Wall 1 én Wall 3, zelfde breedte)
     allebei als dezélfde gevel tikken — een kamer raakt één gevel maar aan één kant. De tool
     waarschuwt hierop ("TIKFOUT? evenwijdige wanden"), maar voorkomen is beter.
   - **Zolderwanden onder het schuine dak NIET tikken.** Op zolder zit de thermische schil in het
     DAK (dat rekent de tool al uit footprint + helling). Alleen échte verticale kopgevels tikken
     (de driehoek-zijden, haaks op de nok). *Vangnet:* tik je per ongeluk tóch de voor/achtergevel
     op de zolder, dan **haalt de tool die verdieping automatisch uit de gevel** (want die oriëntatie
     is een schuin dakvlak) en meldt dat in een note — dubbeltelling met het dak kan dus niet meer.
   - **Wél elke verdieping.** Op BG én verdieping(en) de gevelwanden tikken — een gemiste kamer =
     een gat in de gevel (de tool checkt de volledigheid tegen omtrek x gevelhoogte).
   - **Ramen/deuren gewoon per kamer intikken zoals je meet** — die kloppen bewezen op de
     centimeter (Essenhage: 12,26 vs 12,26 m² op NW). De gevel-m² is de enige plek waar
     tik-discipline telt.
9. **Ramen/deuren plaatsen** + B x H meten (identiek raam: kopieer). Per raam: **alleen Type glas** — de
   rest is default (hout/kunststof · geen rooster · raam); alleen afwijkingen aanraken (paneel! metaal! rooster!).
   Per deur: Type constructie (dicht / met raam / 65% glas) + evt. **bovenlicht** (glas of dicht paneel).
10. **Afwijkingen** per element: begrenzing (AOR/kruipruimte/...), isolatie-override, rekenzone, of
    **narekenen-vinkje + "Grenst aan buiten (m)"** (meet de buitenlengte — de tool splitst zelf).

### Bewijslast (tijdens de ronde)
11. **Spouwinspectie** per te isoleren gevel (boorgat in de voeg + endoscoop; zie spouwinspectie-gids) ·
    **kruipruimte-foto met rolmaat** (hoogte!) · dak-isolatie met duimstok · ventilatie-unit + typeplaatje ·
    overzichtsfoto per bouwdeel.

### Eindcheck op de bank (5 min — zie inmeetgids)
12. Elke buitenwand een gevelnaam? · elk raam een glastype? · **1 zadeldak = 1 dak** (geen dubbel!) ·
    verdiepingshoogtes reëel (geen 0,46 m-kamers) · Ag ≈ BAG (±5%) · foto's compleet.

### Thuis (10 min)
13. Exporteer de **Statistics-CSV** (NIET de PDF — daar zitten de form-antwoorden niet in!).
14. Webapp: project -> Opname -> CSV inladen -> **actiekaart "Zelf doen in Vabi" afwerken** -> gegevens
    nalopen -> VABI-import downloaden -> EPA: 3 tegels importeren -> rekenen -> export terug (nulmeting) ->
    maatregelen -> VABI-toets -> afronden (PDF+JSON) -> indienen.

> Doel: **snel en zonder klungelen** een woning opnemen, zó dat de tool er thuis automatisch
> de VABI-invoer + het Nij Begun-isolatieplan van maakt. Print dit of zet het op je iPad.

## Het idee in 3 zinnen
1. **MagicPlan meet de wanden, vloeren en m² automatisch** als je scant — die hoef je NIET na te meten.
2. Jij doet per kamer maar 4 dingen: **scannen · ramen/deuren toevoegen · de kamer benoemen · de buitenmuren benoemen**.
3. De rest (oriëntaties, begrenzing, isolatie) regel je via **namen** en een paar **projectvelden** — geen kompas-gepriegel per muur.

---

## De opzet (net als VABI) — 3 project-forms + per-element Fields
- **Form "Object"** = geometrie/identificatie (bouwjaar, woningtype, gevelhoogte, **Oriëntatie voorgevel**, dak, Ag, qv10, begrenzing-vloer).
- **Form "Constructies"** = isolatie/constructie-defaults (geveltype, thermische massa, spouw-dak, **Rc-bron per bouwdeel**).
- **Form "Installaties"** = ventilatie · verwarming · tapwater · koeling · zonne-energie · foto's.
- **Fields per element** = OVERSCHRIJVEN waar het afwijkt: op een **muur** ("Gevel per wand"), **vloer** ("Vloer"), **raam/paneel** ("Raam/paneel"), **deur** ("Deur").

## STAP 0 — Vooraf op kantoor (5 min)
Vul in de **"Object"**-form wat je nú al weet (projectniveau):
- Adres · **BAG VBO-id** · bouwjaar(klasse) · **woningtype** (vrijstaand/2-onder-1-kap/hoek/tussen).
- **Oriëntatie voorgevel** (N/NO/O/ZO/Z/ZW/W/NW) — kijk op de kaart welke kant de vóórgevel op wijst. **Dit is de truc**: hieruit leidt de tool de andere 3 gevels af (zie STAP 2).
- Opnamedatum · type advies (Basis/Detail).

---

## STAP 1 — De gouden volgorde PER KAMER ⭐
Doe in **elke** ruimte exact dit, dan vergeet je niks:

| # | Actie | Toelichting |
|---|---|---|
| 1 | **Scan de ruimte** | MagicPlan tekent de wanden + meet ze. Loop rustig rond; controleer dat de plattegrond klopt. **Niet handmatig nameten.** |
| 2 | **Voeg ramen & deuren toe** | Tik op de wand → raam/deur → meet **breedte × hoogte**. Dit is het enige dat je écht zelf meet. (zie snelheidstips onder) |
| 3 | **Benoem de ruimte** | Woonkamer / Keuken / Slaapkamer 1 / Badkamer / Toilet / Bijkeuken. De tool leidt hieruit de **ventilatiebalans** af. |
| 4 | **Benoem de buitenmuren** | Geef elke buitenmuur de naam **Voorgevel / Achtergevel / Linkergevel / Rechtergevel**. Een muur naar de buren (woningscheidend) laat je leeg of noem je `buurwand` → die valt automatisch buiten de schil. |

> **Binnenmuren** hoef je niet te benoemen — alleen muren die aan buiten (of een afwijkende ruimte) grenzen.

---

## STAP 2 — Gevelnamen & kompas (de grote tijdwinst) 🧭
Je benoemt gevels met hun **plek** (voor/achter/links/rechts), niet met een kompasrichting. De tool rekent
de oriëntatie zelf uit, op basis van **"Oriëntatie voorgevel"** (die je in stap 0 invulde):

- **Linker- en rechtergevel = gezien vanaf de straat**, kijkend naar de voorgevel.
- Voorbeeld: voorgevel op het **Zuiden** → rechtergevel = **Oost**, linkergevel = **West**, achtergevel = **Noord**.
- Zie het plaatje: [`docs/gevel-kompas.svg`](gevel-kompas.svg).

**Afwijkend / schuin huis?** Zet de richting er gewoon achter in de naam, bv. `Rechtergevel ZW`. Die override
wint van de afgeleide richting. (De tool toont na afloop de 4 afgeleide oriëntaties zodat je ze even checkt.)

---

## STAP 3 — OVERSCHRIJVEN waar een vlak afwijkt ⭐ (per-element Fields)
Je vult de normale waarden één keer in (Constructies/Object-form). Wijkt één muur/vloer/raam af? **Tik op dat
element** en vul de bijbehorende **Field** in — alleen het afwijkende veld:

| Element | Field-groep | Wat je kunt overschrijven |
|---|---|---|
| een **muur** | "Gevel per wand" | Oriëntatie · Isolatie aanwezig (+spouw/bouwjaar) · **Begrenzing (anders dan buitenlucht)** · Spouwdikte · **Isolatiedikte (mm)** · **Rc-bron** · Bron · **Rekenzone** |
| een **vloer** | "Vloer" | **Begrenzing** (kruipruimte/grond/AOR/…) · Isolatie · Isolatiedikte · Rc-bron · **Telt mee voor Ag?** · **Rekenzone** |
| een **raam/paneel** | "Raam/paneel" | **Alleen Type glas** hoef je te kiezen. Kozijnmateriaal · Toevoerrooster · Raam/paneel laat je leeg → de tool neemt de default: **hout/kunststof · geen toevoerrooster · raam**. Alleen invullen als het afwijkt (bv. metalen kozijn, wél een rooster, of een dicht paneel). Oriëntatie + begrenzing erft het raam van de moederwand. |
| een **deur** | "Deur" | Type constructie · glas · oppervlakte raam-in-deur; kozijn default hout/kunststof (begrenzing/oriëntatie erft van de wand) |

> **Jouw AOR-vloer uit de vorige opname:** tik op die vloer (of de ruimte erboven) → "Vloer"-Field → **Begrenzing = AOR**.
> De rest van de begane grond houdt de project-default (`Begrenzing (vloer)` in de Object-form). Twee vloervlakken, klaar.

**Snelle alternatieven via de naam** (handig tijdens het scannen; de tool leest deze ook):
`Achtergevel AOR garage` · `Kelderwand grond` · `Zijgevel ongeisoleerd` · `Voorgevel narekenen` (deels buiten/binnen) ·
`buurwand`/`AVR` (telt niet mee). Voor de oriëntatie is de naam (voorgevel/achter/links/rechts) sowieso de makkelijkste route.

---

## STAP 4 — Na alle kamers: de project-forms afmaken (1× invullen)
- **Form "Object"** — type dak + dakmaten/oriëntaties (of hellingshoek) · plat dak · Ag-aftrek zolder · qv10 (gemeten?) · `Begrenzing (vloer)` (default) · renovatiejaar.
- **Form "Constructies"** — geveltype · thermische massa wanden/vloeren · spouwdikte dak · **Rc-bron gevel / vloer / dak** (Opgemeten / Dikte onbekend / **Kwaliteitsverklaring**).
- **Form "Installaties"** — ventilatie · verwarming · tapwater · koeling · zonne-energie · foto's.

> **Kwaliteitsverklaring?** Kies bij Rc-bron "Kwaliteitsverklaring". De tool kiest dan een forfaitaire constructie
> én **vlagt het**, zodat jij in VABI `Invoer = Kwaliteitsverklaring` + de Rc/U-waarde invult. (De tool gokt nooit een Rc/U.)

### ⭐ Vier velden voor de HUIDIGE STAAT in het isolatieplan (sectie 3) — vergeet ze niet
Deze bepalen op welke regel van het plan de staat terechtkomt. Laat je ze leeg, dan blijven die
regels **leeg** in het plan (form **Constructies**):

| Veld | Waarom |
|---|---|
| `Gevel - isolatie aan zijde` | Spouw / binnenzijde (voorzetwand) / buitenzijde → **V1** |
| `Dak - isolatie aan zijde` | Binnen- of buitenzijde, hellend én plat → **V4** |
| `Bodemisolatie kruipruimte` | Bodem van de kruipruimte (niet de vloer) → **V3** |
| `Kierdichting` | Alleen nodig als er géén qv10-meting is → **V6** |

> **Spouwmuurisolatie in provincie Groningen?** Dan moeten sinds 1-7-2026 ook **eDNA-onderzoek,
> natuurvrij maken en een alternatieve verblijfplaats** in het plan (V1-1-X13 t/m X17). De tool
> herinnert je eraan in de stap Maatregelen — zie de gids *Gedoogbeleid vleermuizen & eDNA*.

---

## STAP 5 — Meerdere installaties (bv. 2 soorten zonnepanelen)
Heb je **meer dan één** van iets? Vul dan het tweede exemplaar in de genummerde velden:
- **PV:** `PV - …` voor systeem 1, `PV-2 - …` voor systeem 2 (paneeltype/aantal/oriëntatie/hellingshoek). De tool zet **alle** PV-systemen door naar VABI.
- **Verwarming/Tapwater/Koeling:** `Verwarming 2 - …`, `Tapwater 2 - …`, `Koeling 2 - …` (bv. hybride warmtepomp + cv-ketel). De tool zet exemplaar 1 volledig door en **vlagt** de extra, die je in Vabi toevoegt.

---

## STAP 6 — Foto-checklist 📷 (sectie FOTO'S in de Installaties-form)
Maak een foto alleen waar het onderdeel er is. Maak in elk geval:

**Woning algemeen** — vooraanzicht · huisnummer · elke gevel (voor/achter/links/rechts).
**Schil-details** — kozijn/glas (typeplaatje of detail) · kruipruimte · dak-/zolderisolatie · **isolatiedikte met duimstok**.
**Installaties** — typeplaatje cv-ketel/warmtepomp/boiler · ventilatie-unit · meterkast · PV-omvormer.
**Bijzonderheden** — asbestverdacht materiaal · vochtplekken · slechte bereikbaarheid (steiger/hoogwerker).

> Datum van de foto ≤ opnamedatum; herleidbaar (welk onderdeel). Dit voedt de foto-checklist + het BRL-projectdossier.

---

## Snelheidstips — minder nameten
- **Identieke ramen?** Meet er één en **kopieer** 'm; pas alleen af waar het verschilt.
- Gebruik **MagicPlan-presets** voor standaard deur-/raamhoogtes; corrigeer alleen de afwijkende.
- Scan eerst de **hele verdieping**, voeg dáárna pas de ramen/deuren toe (minder wisselen tussen modi).
- Benoem muren meteen tijdens de scan (lang-indrukken → hernoemen), dan hoef je later niet terug.

---

## STAP 7 — Thuis: de tool draaien & de oriëntaties checken 💻
```
python magicplan/statistics_csv.py --csv "… Statistics.csv" --straat .. --huisnummer .. --postcode .. --plaats ..
python vabi/generate_all.py --dossier out/dossier_csv.json
```
Lees de **"LET OP / nameten"-lijst**. Eén regel toont de **afgeleide gevel-oriëntaties** — controleer of die kloppen
(klopt het niet → pas "Oriëntatie voorgevel" aan, of override een gevel in de naam zoals `Rechtergevel ZW`).
Daarna importeer je in VABI: **Constructies → Objecten → Installaties** en druk je op **Rekenen**.

> Volledige A-tot-Z: [`docs/WERKWIJZE-A-TOT-Z.md`](WERKWIJZE-A-TOT-Z.md). Veldnamen: [`docs/magicplan-form-spec.md`](magicplan-form-spec.md).
