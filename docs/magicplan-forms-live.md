# MagicPlan-forms — LIVE waarheidsbron (23-7-2026)

**Dit is de enige plek die beschrijft wat er ECHT in MagicPlan staat.** Live afgelezen via de
custom-fields/custom-forms-API op 23-7-2026 (workspace R.poortinga). Bij twijfel: dit document wint
van `additions.json`, `LIVE-WIJZIGINGEN.md` en oude how-to's — die zijn uit elkaar gelopen. Zie het
kader "Waarom dit document" onderaan.

Rolverdeling: **MagicPlan = de schil** (gevels, vloer, ramen, deuren + installaties + object-gegevens).
**De webapp = het dak** (dak + dakramen via de "Dak toevoegen"-wizard; besluit 15-7, uitgevoerd 23-7).

---

## 3 PROJECT-forms (custom-forms, gelden per project)

### Object
`Oriëntatie voorgevel` · `Qv10-waarde (dm3/s.m2)` · `Qv10 gemeten?` · `Bouwjaar` · `Renovatiejaar` ·
`Woningtype` · `Gevelhoogte (m)` (tot de goot) · **`Gebouwhoogte tot de nok (m)`** (nieuw 23-7, tot het
hoogste punt — handmatig, de tool berekent dit bewust niet) · `Ag-aftrek zolder (m2)` ·
`Foto: vooraanzicht woning (verplicht)` · `Foto: huisnummer (verplicht)`.

### Constructies
- **GEVEL**: `Gevel - invoer` (Kwaliteitsverklaring | Beslisschema) · `Gevel - thermische massa` ·
  `Gevel - begrenzing` · `Gevel - isolatie aan zijde` · `Kierdichting`.
- **VLOER**: `Vloer - invoer` · `Vloer - thermische massa` · `Vloer - begrenzing` ·
  `Bodemisolatie kruipruimte`.
- **DAK: VERWIJDERD op 23-7** (was 211 velden — type dak/Extra dak A/B, m²-per-oriëntatie, dakramen).
  Dak + dakramen doe je nu in de **webapp-wizard**. MagicPlan bevat geen dak-geometrie meer.

### Installaties
Secties: **VENTILATIE · VERWARMING · KOELING · TAPWATER · ZONNE-ENERGIE · FOTO'S**. Per sectie een
rekenzone-veld + de hoofdkeuzes (o.a. Ventilatiesysteem A-E, verwarming type opwekker/afgifte/
aanvoertemperatuur, koeling aanwezig?, tapwater toestel, PV aanwezig? + Meerdere PV-systemen?).

---

## 4 ELEMENT-field-groepen (custom-fields, per wand/vloer/raam/deur)

### Gevel per wand (context: All Walls)
`Gevelnaam` · `Gevel - oriëntatie (override)` · `Gevel - invoer (override)` ·
`Gevel - foto kwaliteitsverklaring` · `Gevel - isolatie aanwezig?` · `Gevel - isolatiedikte onbekend?` ·
`Gevel - bouwjaar` · `Gevel - isolatiedikte (mm)` · `Gevel - spouw aanwezig (indien <40mm)?` ·
`Gevel - spouw aanwezig?` · `Gevel - bouwjaar (onbekend)` · `Gevel - thermische massa` ·
`Gevel - begrenzing` · `Gevel - rekenzone` · `Deels binnen/deels buiten? (narekenen)` ·
`Grenst aan buiten (m)`.

### Vloer (context: All Rooms)
`Vloer - begrenzing` (per kamer, override op de project-vloer).

### Raam/paneel (context: Windows)
`Toevoerrooster aanwezig?` (hoofdraam) → `Toevoerrooster type` ·
`Bovenlicht in het kozijn?` → glas (oppervlak + type glas) | dicht paneel (oppervlak + isolatie
aanwezig? → **bouwjaarklasse** + dikte) + **`Bovenlicht kozijn - toevoerrooster aanwezig?`** (nieuw 23-7) ·
`Onderlicht in het kozijn?` (idem + **`Onderlicht kozijn - toevoerrooster aanwezig?`** nieuw 23-7) ·
`Type glas` · `Kozijnmateriaal` · `Begrenzing (anders dan buitenlucht)` · rekenzone/isolatiedikte-overrides.

### Deur (context: Doors)
`Bovenlicht boven de deur?` (glas | dicht paneel) · `Bovenlicht deur - type glas` ·
`Toevoerrooster deur aanwezig?` · `Type glas (indien glas in deur)` · `Kozijnmateriaal` ·
`Begrenzing (anders dan buitenlucht)`.

---

## Begrenzing-opties (alle 4 begrenzing-velden, na 23-7)
`Buitenlucht · Grond · Kruipruimte · AOR (onverwarmd) · AOS (serre) · AVR (aangrenzend verwarmd) ·`
**`ASGR (sterk geventileerd) · Water · Onverwarmde kelder`** (de laatste 3 toegevoegd 23-7; "Onverwarmde
kelder" alleen op gevel + vloer). De EPA-term is **ASGR** (Aangrenzend Sterk Geventileerde Ruimte, code 6);
"ASV" is geen officiële term maar wordt door de parser als tolerante alias herkend.

## Glas-opties (alle glasvelden)
`Enkel · Voorzetglas · Dubbel · HR (dubbel glas met coating) · HR+ · HR++ · TripleHR · Vacuümglas ·
Onbekend` — dekt de 7 forfaitaire klassen van NTA 8800 tabel I.8. HR+ zit in álle glasvelden.

## Kozijn-opties
`Hout of kunststof · Metaal (thermisch onderbroken) · Metaal (niet thermisch onderbroken)` = NTA
tabel 8.3 kozijntype A/B/C (forfaitaire U 2,4 / 3,8 / 7,0).

---

## Waarom dit document (het "overal wat staat"-probleem)
De MagicPlan-forms werden op vier plekken beschreven die uit elkaar liepen:
- `magicplan/forms/additions.json` — velden die de tool verwácht (form_push-bron), maar `push_forms.bat`
  kan NIET publiceren (editor-API weigert de app-key) → live-wijzigingen gaan handmatig via de
  browserconsole → additions.json en de live forms lopen uit elkaar (rooster/gebouwhoogte stonden er
  wél in, maar waren nooit live gezet; dak stond er niet meer maar was nog wél live).
- `magicplan/forms/LIVE-WIJZIGINGEN.md` — logboek van handmatige live-wijzigingen.
- `magicplan/statistics_csv.py` — wat de parser uit de CSV léést (de echte harde eis: veldnamen
  moeten hiermee matchen).
- oude how-to's (`magicplan-opname-howto.md`) — beschreven nog het verouderde "Schil & zone"-form.

**Werkwijze bij een form-wijziging:** wijzig live via de browserconsole-route (zie
`magicplan/forms/LIVE-WIJZIGINGEN.md` + memory `magicplan-form-api`), en **werk daarna dit document bij**.
De parser-veldnamen in `statistics_csv.py` zijn leidend voor de exacte naamgeving.
