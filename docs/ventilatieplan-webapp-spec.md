# Ventilatieplan in de webapp — specificatie

Status: ontwerp. Hoort bij `tasks/backlog/019`, `020` en `021`.
Rekenhart: `ventilatie/ventilatie.py` (bestaat al). Webapp: `dashboard/app.py`.

## Waarom
Wij rekenen de ventilatie al correct door, maar leveren alleen een tekstrapport. Een
ventilatieplan dat de bewoner en de installateur begrijpen is een **tekening**: pijlen met
l/s-waarden op de plattegrond, plus de onderbouwende tabel. Dat is precies het gat.

## 1. Referentie: wat Aira doet (waargenomen, niet aangenomen)

Bron: `C:\Users\Renze Poortinga\Downloads\aira.mp4` — 39 s, 1920x1080, schermopname van
aira-ventilatie.nl ("gemaakt voor energie-adviseurs"). Alles hieronder is van de beelden
afgelezen. Frames zelf terughalen:

```
ffmpeg -i aira.mp4 -vf "fps=1,mpdecimate=hi=64*40:lo=64*10:frac=0.2,scale=1280:-1" -fps_mode vfr -q:v 4 f_%03d.jpg
```

Hun claim in de openingstitel: "Van plattegrond naar BBL-ventilatieplan. In minuten. Zonder
tekenwerk, zonder gedoe."

### Stap 1 — Upload (t is ongeveer 2-7 s)
- Stepper bovenaan: `1 Upload — 2 Validatie — 3 Resultaat`. Rechtsboven een groene badge
  `Opgeslagen in woning`. Linksboven `Terug naar woning`.
- Kop: "Plattegrond uploaden". Sub: "Upload een scan of foto van de plattegrond (JPG of PNG).
  Geen voorbewerking nodig."
- Dropzone: "Nog een verdieping toevoegen — PNG of JPG, een afbeelding per verdieping
  (meerdere mogelijk). Of een FML-bestand (Floorplanner-export, bevat alle verdiepingen),
  voeg er ook foto's aan toe voor een getekend plan met pijlen."
- Rechts een strook thumbnails per verdieping met titel ("Begane grond", "1e verdieping"),
  een kruisje per tegel en pijltjes om te herordenen. Boven de strook: "2 VERDIEPINGEN ·
  SLEEP OF GEBRUIK PIJLEN OM TE ORDENEN (EERSTE = BEGANE GROND)".
- Velden: `ADRES (OPTIONEEL)` (waarde "Demo") en `VENTILATIESYSTEEM` (dropdown, waarde "C").
- Knop: "Analyseer 2 plattegronden". Tijdens verwerken: voortgangsbalk "Plattegrond aflezen…
  10%" met "2 verdiepingen worden tegelijk verwerkt, dit duurt ongeveer een minuut", knop
  wordt "Analyseren…" en is uitgeschakeld.

### Stap 2 — Validatie (t is ongeveer 8-11 s)
- Kop: "Gegevens controleren". Sub: "De ruimtes zijn automatisch afgelezen. Controleer en pas
  aan waar nodig." Overlay-tekst in de video: "STAP 2 — CONTROLE / Jij houdt de regie."
- Oranje paneel "3 aandachtspunten — even nakijken" met exact deze drie regels:
  - "MK (meterkast) zichtbaar in Entree op begane grond: controleer of deze een gasmeter of CV-ketel bevat."
  - "Bijkeuken op begane grond is gemarkeerd als alternatieve afvoerlocatie; controleer of hier een afzuigpunt gewenst is."
  - "Geen CV-ketel- of gasmetersymbool zichtbaar op de 1e verdieping; controleer of de CV-ketel zich in de bijkeuken of meterkast op de begane grond bevindt."
- Per verdieping een tabel: `RUIMTE | FUNCTIE (dropdown) | OPPERVLAKTE (bewerkbaar, m2) | splits | verwijderen`.
- Waargenomen functiewaarden: `verblijfsgebied`, `verblijfsruimte`, `keuken`, `badruimte`,
  `toiletruimte`, `verkeersruimte`, `overig`.
- Waargenomen demo-woning (hun voorbeeld, overnemen als testfixture):
  - Begane grond: Woonkamer 38,7 (verblijfsgebied) · Slaapkamer 4 18,2 (verblijfsruimte) ·
    Bijkeuken 9,7 (overig) · Entree 8,2 (verkeersruimte) · Toilet 1,2 (toiletruimte) ·
    Keuken 18,5 (keuken)
  - 1e verdieping: Slaapkamer 1 12,2 · Slaapkamer 3 6,9 · Slaapkamer 2 9,3 (alle
    verblijfsruimte) · Overloop 3,8 (verkeersruimte) · Badkamer 6,9 (badruimte)
- Onderaan een inklapbare rij: "Topologie aanpassen · geavanceerd" met rechts
  "automatisch gedetecteerd". Knoppen: "Terug" en "Berekening starten".

### Stap 3 — Resultaat (t is ongeveer 12-26 s)
- Kop: "Ventilatieplan". Sub: "Het berekende plan op basis van de afgelezen plattegrond.
  Uitleg opnieuw tonen". Rechtsboven: `Download ventilatieplan (PDF)`.
- Balans-pil: `Balans: toevoer 76.0 l/s = afvoer 76.0 l/s` met daarnaast de knop
  "Herbereken balans".
- "Plan per verdieping": per verdieping een kaart met de **originele plattegrond als
  achtergrond** en daaroverheen de markers. Boven de kaarten: `Download plan (PNG)`.
- Onder elke kaart de bedieningshint: "Sleep = verplaatsen · 1x klik = draaien · dubbelklik =
  getal wijzigen / splitsen" en de knoppen `+ Toevoer` (blauw), `+ Afvoer` (rood),
  `+ Overstroom` (groen) en `Herstel`. Legenda: Toevoer / Afvoer / Overstroom.
- Markervormen: **toevoer** = blauwe pijltag met getal, staat in de buitengevel en wijst naar
  binnen. **afvoer** = rode ovaal met getal op het afzuigpunt. **overstroom** = groene
  pijltag met getal door een binnendeur of opening.
- Bij het slepen van een marker verschijnt een **blauwe verbindingslijn naar het ruimtelabel**
  van de ruimte waar hij bij hoort, en dat label krijgt een rode cirkel. De marker is dus aan
  een ruimte gebonden, niet los op het plaatje. Dit gedrag overnemen.
- Rechterkolom "Berekening" met knoppen "Tabel bewerken" en `PNG`:
  - "Toevoer per verblijfsruimte": `RUIMTE | M2 | MIN. L/S | ADVIES L/S`
    Woonkamer 38,7 / 40,0 / **40,0** · Slaapkamer 4 18,2 / 13,0 / **13,0** ·
    Slaapkamer 1 12,2 / 9,0 / **9,0** · Slaapkamer 3 6,9 / 7,0 / **7,0** ·
    Slaapkamer 2 9,3 / 7,0 / **7,0**
  - "Afvoer per natte ruimte": `RUIMTE | MIN. L/S | ADVIES L/S | AFVOERPUNT`
    Bijkeuken 0,0 / **13,0** / Ja · Toilet 7,0 / **10,0** / Ja · Keuken 21,0 / **30,0** / Ja ·
    Badkamer 14,0 / **23,0** / Ja
  - "Advies": onder meer "Deurbelasting Badkamer-Overloop: 23.0 l/s (>15 l/s), deurrooster geadviseerd."

### Het eindrapport (t is ongeveer 27-36 s)
PDF van **4 paginas**, bestandsnaam is de adres-slug (`wilde-zwaan-6.pdf`).
- p1: samenvatting/voorblad. p2: "Begane grond" met plan. p3: "1e verdieping" met plan.
  p4: "BEREKENING (BBL TABEL 3.1)" met beide tabellen, daaronder in groen
  "Balans: toevoer 76.0 l/s / afvoer 76.0 l/s — in balans" en een kopje "AANDACHTSPUNTEN"
  met de deurbelasting-bullet.
- Voettekst op **elke** pagina: "Indicatief ventilatieplan volgens BBL Tabel 3.1 - hieraan
  kunnen geen rechten worden ontleend." plus "Pagina X / 4".
- Onder elke plattegrond: "Deze plattegronden zijn opgemaakt voor indicatieve doeleinden,
  hieraan kunnen geen rechten worden ontleend."
- In de tekening blijven de maatlijnen (2,86 m / 9,40 m / 6,36 m en verder) en de noordpijl
  van de bronplattegrond staan; slaapkamers krijgen een genummerde cirkel (1, 2, 3, 4).

### Nagerekend: hun norm is onze norm
- Woonkamer 38,7 m2 krijgt 40,0 l/s. Dat is niet 0,7 x 38,7 (= 27,1) maar
  **0,7 x (38,7 + 18,5 keuken) = 40,04**. Zij tellen woonkamer en keuken als een
  verblijfsgebied, precies zoals `TOEVOER_FUNCTIES` in `ventilatie/ventilatie.py`.
- Slaapkamer 18,2 wordt 13,0 (0,7 x). Slaapkamer 6,9 en 9,3 worden beide 7,0, dus hetzelfde
  **minimum van 7 l/s per leefruimte** dat wij hanteren.
- Hun minima natte ruimten: keuken 21,0 · badkamer 14,0 · toilet 7,0, identiek aan onze
  `AFVOER`-tabel. Bijkeuken staat bij hen op min 0,0 (bij ons: wasruimte 14,0).
- Hun advies-afvoer (13/10/30/23 = 76,0) ligt boven de som van de minima (42,0): zij
  **verdelen het balansverschil automatisch over de natte ruimten**. Wij geven daar nu alleen
  een waarschuwing. Dat is het enige rekenkundige dat zij meer doen dan wij.
- **Afronding**: zij ronden af op hele l/s, naar het dichtstbijzijnde getal. 12,74 wordt 13,0;
  8,54 wordt 9,0; 40,04 wordt 40,0. Wij ronden nu op 0,1 l/s. Zie de beslissing in taak 019.

Conclusie: hun rekenhart is het onze. Het verschil zit in de tekening, de PDF en de invoerroute.

## 2. Wat wij bouwen

### Wat wij anders doen dan Aira
| | Aira | Wij |
|---|---|---|
| Geometrie | AI leest een plattegrondfoto | **MagicPlan-opname** (gemeten). Beeldherkenning is optioneel en pas taak 021 |
| Norm | BBL Tabel 3.1 | Nij Begun-vuistregels (BBL-gebaseerd, bindend), zie `ventilatie/nijbegun_vuistregels.md` |
| Toetsing | 1 regel (deurbelasting) | **alle 7 vuistregels** als pass/fail-check |
| Context | losse tool | onderdeel van het dossier: isolatieplan, M29-maatregelen, KWACO-validator |

### Waar wij het beter doen (dit is de opdracht, niet alleen nabouwen)
1. **Alle 7 vuistregels toetsen** en per regel tonen of het plan slaagt: overstroom via
   maximaal 2 deuren, minstens 50% lucht direct van buiten, geen afvoerpunt in een
   slaapkamer, meer dan 15 l/s onder een deur betekent een deurrooster, af- en toevoer niet
   te dicht bij elkaar, toevoer niet bij een rookkanaal, C4c CO2-sturing op woonkamer en
   hoofdslaapkamer.
2. **Balansverdeling automatisch** (wat Aira doet) en zichtbaar: toon per natte ruimte het
   minimum, het verdeelde advies en waar de opgehoogde lucht vandaan komt.
3. **Herleidbaarheid**: elke waarde in de tabel toont zijn herkomst (0,7 x opp, of het
   minimum, of een balansophoging). Past bij het geen-aannames-beleid.
4. **Geen los eiland**: het plan hangt aan het dossier (`out/<tag>/`), gaat mee in het
   isolatieplan en de fotochecklist, en de validator kan erop toetsen.

### Datamodel (uitbreiding dossier-JSON, geen database)
```
ventilatieplan: {
  systeem: "C",                          # bestaand veld ventilatie_default.systeem
  verdiepingen: [
    { naam: "Begane grond",
      achtergrond: "plattegrond_bg.png", # pad relatief aan de dossiermap
      breedte_px: 1600, hoogte_px: 1200,
      markers: [
        { id: "m1", type: "toevoer|afvoer|overstroom", ruimte_id: "r3",
          waarde_ls: 30.0, x: 0.42, y: 0.66, rotatie: 90, bron: "auto|handmatig" }
      ] } ] }
```
`x` en `y` zijn relatief (0..1) zodat de tekening schaalt. `ruimte_id` verwijst naar
`geometrie.ruimtes`; een marker zonder geldige `ruimte_id` mag niet opgeslagen worden.

### Niet overnemen
Merknaam, logo, kleurpalet en teksten van Aira zijn van hen. Wij bouwen de functionaliteit en
de normbasis (BBL en Nij Begun, publiek), in onze eigen huisstijl en met onze eigen teksten.
