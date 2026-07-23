# MagicPlan-opname — how-to voor de adviseur

Praktische handleiding om één woningopname in MagicPlan zó in te vullen dat de tool er
automatisch een VABI-import (3 bibliotheken) én een Nij Begun isolatieplan van maakt.
Geschreven voor wie de tool nog niet kent. Naslag op veld-niveau (exacte keuzelijsten):
`../../MagicPlan-VABI-veldenmapping.md`.

> **In één zin:** teken de woning, markeer de buitengevels met een oriëntatie, en vul daarna
> **alléén de afwijkingen** in. De rest vult de tool met slimme defaults.
>
> **Let op (23-7-2026):** MagicPlan = de **schil** (gevels/vloer/ramen/deuren/installaties/object).
> Het **dak doe je in de webapp** (Dak toevoegen-wizard). De exacte, actuele live veldenlijst staat
> in [`magicplan-forms-live.md`](magicplan-forms-live.md) — dát is de waarheidsbron, niet dit how-to
> (dit document noemt op sommige plekken nog het oude "Schil & zone"-form; dat heet nu Object /
> Constructies / Installaties).

---

## 0. Het gouden principe — "alleen afwijkingen invoeren"

Voor élk dicht deel (gevel, vloer, dak) geldt een **drielaagse overerving**:

```
per object (deze wand/vloer/ruimte)   →   projectwaarde (Form)   →   tool-default
        ingevuld wint                       als object leeg is        als alles leeg is
```

Je zet de **projectwaarde** één keer (in de Form / de project-veldgroep) en die geldt voor de
hele woning. Wijkt één gevel af (garage ernaast, andere isolatie, ander metselwerk)? Dan vul je
**alleen op die wand** het afwijkende veld in. Leeg laten = projectwaarde overnemen.

**Tool-defaults (hoef je dus nooit in te typen, alleen als het ánders is):**

| Onderdeel | Default als je niets invult |
|---|---|
| Gevel-begrenzing | Buitenlucht |
| Vloer-begrenzing | Kruipruimte / Grond |
| Kozijn (raam/deur) | Hout of kunststof |
| Rekenzone | 1 |
| Ruimte "telt mee voor Ag?" | Ja |

Dit scheelt ~90% van de kliks: een doorsnee tussenwoning vul je af met een handvol oriëntaties +
de installaties.

---

## 1. Voorbereiding (1 minuut)

1. Nieuw project in MagicPlan → vul het **adres** in.
2. Controleer dat de twee Forms aan het project hangen:
   - **Installaties** (ventilatie/verwarming/tapwater/koeling/PV)
   - **Schil & zone** (thermische massa, qv10/renovatiejaar, begrenzing vloer, type dak, bouwjaar-klasse)
3. Klaar — begin met tekenen.

---

## 2. De opname, stap voor stap

### Stap A — Teken de plattegrond (per verdieping)
Scan of teken elke verdieping. MagicPlan **meet automatisch**: wandlengtes, **wandoppervlak zonder
openingen**, plafondhoogte en vloeroppervlak. → **m² hoef je nooit in te typen.**

### Stap B — Markeer de buitengevels (Walls)
Loop de buitenmuren langs en geef elke **buitengevel een oriëntatie** (N · O · Z · W · NO · NW · ZO · ZW).

> ⚠️ **De oriëntatie doet dubbel werk:** een wand **mét** oriëntatie = buitengevel (telt mee in de
> m²). Een wand **zonder** oriëntatie = binnenwand (telt niet mee). Markeer dus precies de echte
> buitenwanden — dat is meteen je "welke muren zijn buitenmuren"-selectie.

Wijkt een gevel af van de standaard? Vul dan op díe wand de afwijkende velden in:
- **Begrenzing** ≠ buitenlucht: AOR (garage onverwarmd) · AOS (serre) · Aangrenzende woning (buur,
  verwarmd → adiabatisch, geen verlies) · Grond · Water · Kruipruimte · Kelder · ASGR.
- **Andere isolatie / spouw / bouwwijze** dan de rest: vul de betreffende velden.
- Alles wat je leeg laat = de projectwaarde.

### Stap C — Ramen, deuren, panelen (per stuk)
Plaats ze in de gevel. Per stuk:
- **Raam/paneel:** Kozijn (default Hout of kunststof) + **Glas** (enkel/dubbel/HR/HR+/HR++/triple).
  Oriëntatie **niet** nodig — het raam erft die van zijn gevel.
- **Deur:** Type (geïsoleerd / niet-geïsoleerd) + evt. "deur met raam ≥ 65% glas".

### Stap D — Vloer
Default-begrenzing is **Kruipruimte/Grond** (níet buitenlucht). Alleen afwijking invoeren.
Isolatie: **Ja → dikte (mm)** · **Onbekend → bouwjaar-klasse** · **Nee**. Een vloer heeft **nooit
spouwdikte**.

### Stap E — Dak: in de WEBAPP, niet in MagicPlan
Sinds **23-7-2026 doe je het dak (én de dakramen) in de webapp**, niet meer in MagicPlan — de
dak-velden zijn daar verwijderd (waren te omslachtig: 211 velden). In MagicPlan teken je alléén de
**schil** (gevels, vloer, ramen, deuren). Na de CSV-import kies je in de webapp-opname-editor
**"Dak toevoegen"**: plat / zadeldak (overspanning + noklengte + helling) / de overige types, met
**dakramen per dakvlak**. De tool rekent het schuine vlak = footprint / cos(helling) + kopgevel-driehoek.
- **Zolder (1,5 m-regel)** blijft wél in MagicPlan — dat gaat om het gebruiksoppervlak (Ag), niet om
  het dak. Alleen vloer met hoogte ≥ 1,5 m telt mee: teken de Ag-contour op de 1,5 m-lijn, óf vul
  `Ag-aftrek zolder (m²)` in het Object-form in.
- **Dakkapel** geef je bij het dakvlak in de webapp op (breedte × hoogte × diepte → extra gevel + plat dakje).

### Stap F — Ruimtes: gebruiksoppervlakte + rekenzone (Rooms)
Per ruimte: **"Telt mee voor gebruiksoppervlakte?"** (Ja default) + **Rekenzone** (default 1).
De tool sommeert het Ag per zone uit de ruimtes die op "Ja" staan. Bijkeuken/garage die niet
binnen de schil valt → op "Nee".

### Stap G — Installaties (Form "Installaties")
- **Ventilatie is verplicht** (zowel Nij Begun als energielabel): systeem **A–E** + subsysteem,
  merk/type/installatiejaar, en bij D/E de WTW.
- **Verwarming · tapwater · koeling · PV:** nodig voor het **energielabel**. Voor een **Nij Begun
  isolatieplan** is alleen ventilatie + de schil nodig — de rest mag je dan overslaan.

### Stap H — Zone & algemeen (Form "Schil & zone")
- **Thermische massa wanden** én **vloeren** (EPA-klassen: **Licht · Zwaar · Zeer zwaar**, elk met
  eigen omschrijving — zie `../vabi/refs/installaties_thermischemassa_EPA.md`) — per rekenzone
  (geldt voor zone 1; bij meerdere zones verifieer je de afwijkende zone in Vabi).
- **Qv10 / luchtdichtheid:** gemeten (blowerdoor) → vul de waarde in; niet gemeten → laat de tool
  het forfaitair rekenen via bouwjaar/**renovatiejaar**. Renovatiejaar mag alleen bij aantoonbare
  energiebesparende maatregelen (dak leidend). Zie `nijbegun_workflow.md`.
- **Perimeter**, **begrenzing vloer**, **bouwjaar-klasse**.

### Stap I — Foto's
Maak per bouwdeel/maatregel de vereiste foto's (de tool genereert een fotochecklist). Goede foto's
= sluitende KWACO-verantwoording.

---

## 3. Veelgemaakte fouten (let op)

- **Binnenwand een oriëntatie gegeven** → telt onterecht mee als buitengevel. Alleen buitenmuren
  een oriëntatie geven.
- **m² intypen** → niet doen; MagicPlan meet ze. Alleen bij een complex dak vul je m² handmatig.
- **Begrenzing standaard invullen** → onnodig. Leeg = buitenlucht (gevel) / kruipruimte (vloer).
- **Spouwdikte op de vloer** → bestaat niet; alleen gevel + dak.
- **Verwarmde buur als AOR** → een verwarmde buurwoning is **Aangrenzende woning** (adiabatisch),
  een onverwarmde garage is **AOR**. Verschil bepaalt het warmteverlies.

---

## 4. Exporteren → de tool neemt het over

1. Draai **`magicplan_export.bat`** (heeft de API-sleutel; haalt de opname op).
   → `out/plan_raw.json` + het project-report.
2. De tool maakt er automatisch van:
   - `python magicplan/assemble.py` → **dossier** (geometrie + form-antwoorden samengevoegd)
   - `python vabi/generate_all.py --dossier <dossier>` → **3 VABI-bibliotheken** + IMPORTEREN.txt
3. **Importeer in EPA-W:** Constructies → Objecten → Installaties → vul Algemeen → **Rekenen**.
4. De tool leest de **Standaard-toets** terug en vult (Nij Begun) het isolatieplan +
   ventilatieberekening + fotochecklist.

> **Gouden regel:** de tool rekent NTA 8800 nooit zelf — **Vabi EPA-W is de geattesteerde
> rekenkern**. Wij leveren de invoer en lezen de uitkomst. Daarmee blijf je in de toegestane
> handmatige adviseur-route.

---

## 5. Mini-naslag — welk veld waar

| Niveau (waar in MagicPlan) | Groep | Belangrijkste velden |
|---|---|---|
| **Project** | Form *Schil & zone* | thermische massa wanden/vloeren · qv10/renovatiejaar · perimeter · begrenzing vloer · type dak · bouwjaar-klasse |
| **Project** | Form *Installaties* | ventilatie (A–E) · verwarming · tapwater · koeling · PV |
| **Project** | veldgroep *Gevel – constructie* | default gevel-set (begrenzing/isolatie/spouw/bron) |
| **Walls** | veldgroep *Gevel – per wand* | oriëntatie · + afwijkingen t.o.v. de project-set |
| **Windows** | veldgroep *Raam/paneel* | kozijn · glas |
| **Doors** | veldgroep *Deur* | type deur · "raam ≥65% glas" |
| **Rooms** | veldgroep *Ag per vertrek* | telt mee? · rekenzone |

Exacte keuzelijsten per veld staan in **`../../MagicPlan-VABI-veldenmapping.md`** (leidend).
