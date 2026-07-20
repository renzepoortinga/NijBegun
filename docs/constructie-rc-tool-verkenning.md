# Rc-calculator + constructiedoorsnede voor de aannemer — verkenning (20-7-2026)

**Vraag van Renze:** iets als [Ubakus](https://www.ubakus.de/nl/rc-waarde-calculator/) — de opbouw van
constructies toetsen, en die vervolgens visueel in het isolatieplan zetten voor de aannemer.

---

## 1. De normgrens — dit bepaalt wat je mag

Uit ISSO 82.1 §8.7 (zie `docs/ISSO-82.1-opnameguide.md`):

| route | hoe Rc bepaald wordt | van toepassing |
|---|---|---|
| **Basisopname (EP-W/B)** | 1) isolatiedikte meten → 2) bewijs/tekening → 3) bouwjaarklasse | **onze route** |
| **Detailopname (EP-W/D)** | lagenberekening volgens NTA 8800 hfst 8; λ uit DoP of forfaitair tabel E.10/E.11 | vereist tekeningen + productinfo + onderbouwing in het projectdossier |

Expliciet in §8.7.2: *"Op tekening/rekening vermelde Rc niet bruikbaar tenzij een gecontroleerde
verklaring dit bevestigt."*

**Conclusie:** een zelf berekende lagen-Rc is **GEEN geldige invoer voor het energielabel** in de
basisopname-route. Dat is geen probleem, want de behoefte ligt ergens anders:

1. **Toetsen** of een door een aannemer voorgestelde opbouw de vereiste Rc haalt → advies, geen labelinvoer
2. **Visualiseren** voor de aannemer → communicatie, geen labelinvoer

Beide vallen buiten NTA 8800 en raken de gouden regel niet. Het blijft wel belangrijk dat een
berekende Rc NOOIT stilzwijgend in het dossier of de VABI-invoer terechtkomt.

## 2. Wat de keten nu niet kan (feitelijk vastgesteld)

- **Vabi kent geen lagen.** In `vabi/refs/standaard_constructies_v120001001.xml`: 219 constructies,
  0 keer `<Laag>`, `<Materiaal>` of `<Lambda>`. Alleen `IsolatieAanwezig`, `Isolatiedikte`,
  `IsolatiedikteOnbekend`, `Bouwjaar`, `SpouwAanwezig`, `Rc`, kwaliteitsverklaring-velden.
  Vabi kán dit dus niet voor ons doen — het is het basisopname-model, precies zoals ISSO voorschrijft.
- **De catalogus geeft de doel-Rc al.** 65 van de 338 maatregelen noemen een expliciete Rc
  (bv. "Dakisolatie PIR-platen dik 80mm Rc 3.50 m².K/W"), samen 30 unieke opbouwen. Voor de
  geadviseerde maatregelen hoeft dus niets gerekend te worden — die Rc staat vast.
- **Het gat:** (a) een aannemer die afwijkt ("120 mm PIR i.p.v. 130 mm glaswol") kunnen we niet
  toetsen, en (b) het plan bevat geen doorsnede die laat zien hóé de opbouw eruit moet zien.

## 3. Marktverkenning

### Nederlandse tools (NEN 1068 / NTA 8800 — de juiste normen)

| tool | wat | norm | prijs | oordeel |
|---|---|---|---|---|
| **[FysicalC](https://www.fysicalc.nl/)** | Rc gevels/vloeren/plat+hellend dak incl. afschotisolatie, condensatierisico (ISO 13788), Qv10-luchtdichtheid, U-waarde kozijnen, equivalente Rc | NTA 8800 | **€145/jaar excl. btw**, alle modules | **beste NL-match**: dekt precies onze drie vragen (Rc, condens, Qv10) mét de juiste norm |
| **[DGMR Rc-waarde](https://dgmrsoftware.nl/producten/gebouw-en-installatie/gebouwprestatie/rc-waarde/)** | Rc enkelvoudig/samengesteld + Uw-waarde; materiaalbibliotheek uit NTA 8800 + NEN-EN-ISO 10456, inclusief historische materialen; rapport met grafische weergave, export Excel/PDF | NEN 1068 + NTA 8800 (+ Belgische EPB) | op aanvraag (geen publieke prijs) | **zwaarste papieren**; rapport expliciet geschikt als onderbouwing voor vergunning/BENG-dossier |
| **[Nieman rekentool](https://www.nieman.nl/nieuws/rc-waarde-calculator/)** | Rc vloeren/gevels/binnenwanden/daken; constructies gecontroleerd door Nieman | NEN 1068 + NTA 8800 | online, gratis/onbekend | snelle check; geen rapportage |
| **[ROCKWOOL Rekenhulp](https://www.rockwool.com/nl/downloads-tools-en-services/tools/rekenhulp-nen/)**, Knauf, Kingspan | fabrikant-rekenhulpen | NEN 1068 / NTA 8800 | gratis | prima voor één opbouw met dat merk; leveranciergebonden |
| **[HSB-rekentool Boorsma](https://boorsma.com/rekentool/)** | houtskeletbouw met houtpercentage | NTA 8800:2020+A1 | gratis | nichegeval (HSB) |

### Ubakus (Duits)

- Rc/U (DIN 6946), **Glaser-vochtberekening (DIN 4108-3)**, droogreserve (DIN 68800-2), zomerse
  warmtewering, faseverschuiving, milieubalans, 3.000+ materialen van fabrikanten, PDF-export.
- Prijzen incl. btw: Plus **€54,84/jr**, PDF **€101,82/jr**, Profi **€133,23/jr**. Zakelijk gebruik
  mag al vanaf Plus. Geen API.
- **Sterkte:** veruit het beste in vocht/condens en visuele weergave; ook Nederlandse interface en
  het toetst tegen Bouwbesluit/NTA 8800-eisen.
- **Zwakte voor ons:** rekent volgens DIN, niet NEN 1068/NTA 8800. Voor een *indicatie* prima, maar
  een Duitse berekening is geen sterke onderbouwing richting een Nederlandse aannemer of KWACO.

### Zwaardere/aangrenzende software (niet nodig)

- **WUFI** (Fraunhofer) — dynamische hygrothermische simulatie; gouden standaard voor vochtschade,
  fors geprijsd en zwaar. Alleen bij echte vochtproblematiek.
- **THERM** (LBNL, gratis) / **Flixo** / **Physibel** — 2D koudebruggen. Niet nodig voor M29.

## 4. Advies

**Voor het toetsen: [FysicalC](https://www.fysicalc.nl/) (€145/jr excl. btw), niet Ubakus.**
Reden: het rekent met **NTA 8800** — dezelfde norm als de rest van de keten — en dekt naast Rc ook
condensatierisico en Qv10, precies de drie dingen die bij dit werk terugkomen. Ubakus is goedkoper en
mooier, maar Duits genormeerd; dat is een zwakke plek zodra iemand doorvraagt.
Wil je maximale papieren (vergunning/BENG-onderbouwing) dan is DGMR de zwaarste optie — offerte opvragen.

**Voor het plan: zelf bouwen, want geen enkele tool kan dit.**
Geen van bovenstaande kent jouw dossier, jouw geadviseerde maatregelen of jouw Word-template. Wat de
aannemer nodig heeft is een **constructieblad per maatregel** in het plan zelf. Dat is precies waar
onze tool wél uniek in is.

## 5. Voorgestelde architectuur (als we bouwen)

```
constructie/materialen.json     λ-waarden MET BRON per regel (NTA 8800 tabel E.10/E.11 kolom
                                'Bestaande bouw', of DoP/kwaliteitsverklaring). Nooit gokken:
                                onbekend materiaal -> LUIDE flag, zoals bij de VABI-enums.
constructie/rc.py               Rc = Rsi + Σ(d/λ) + Rse volgens NEN 1068 / ISO 6946.
                                Puur, deterministisch, volledig testbaar (~200 regels).
                                Levert ALTIJD de gebruikte λ + bron mee terug.
constructie/doorsnede_svg.py    doorsnede-tekening in huisstijl: lagen met dikte, materiaalnaam,
                                arcering per materiaalsoort, buiten/binnen-aanduiding, Rc-uitkomst.
isolatieplan/fill_template.py   bijlage "Constructiebladen" achter de maatregelen A-E.
```

**Toets die het meteen nuttig maakt:** haalt de opbouw de Rc-eis van de catalogus-maatregel?
Zo nee → melding in het plan én in de webapp, met het verschil erbij.

**Harde regels bij de bouw (conform de gouden regel):**
- een berekende Rc gaat NOOIT automatisch het dossier of de VABI-invoer in — het is adviesmateriaal
- elk constructieblad vermeldt de bron van elke λ; ontbreekt die, dan wordt het blad niet gegenereerd
- geen Glaser/condensberekening zelf bouwen (aansprakelijkheid + normcomplexiteit) — dat blijft
  FysicalC/Ubakus

## 6. Voorgestelde eerste stap

Eén constructieblad voor de drie meest voorkomende maatregelen — **spouwmuurisolatie, dakisolatie
binnenzijde, vloerisolatie onderzijde** — met de λ-waarden die de catalogus-maatregelen impliceren,
en de doorsnede-SVG in het plan. Dan is bij het eerstvolgende plan meteen te zien of het werkt voor
de aannemer, vóórdat we een volledige materiaalbibliotheek opbouwen.
