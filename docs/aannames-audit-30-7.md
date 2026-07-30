# Aannames-audit 30-7-2026 — jacht op stille aannames

Aanleiding: de gevel-bug (Wall n en Wall n+2 beide op dezelfde gevel werden stil opgeteld) en de
glastype-bug (twee kolommen "Type glas …", de lege werd gepakt). Beide horen bij **één bugklasse**:

> **De tool neemt een beslissing die een getal verandert, zonder dat de adviseur het merkt.**

Deze audit zoekt die klasse systematisch: heuristieken, eerste-match-lookups, positionele fallbacks
en stille defaults. Leidend principe (zie memory `geen-aannames-beleid`): *conversie, geverifieerde
waarde, of 0/leeg + LUIDE flag — nooit stil gokken.*

---

## Bevindingen

### 1. 🔴 Kozijnmateriaal werd nooit echt gelezen — en viel terug op het gunstigste type
Het live veld heet **`Kozijnmateriaal afwijkend (anders dan hout/kunststof)?`** en is een **Ja/Nee-poort**.
Er is **geen vervolgveld** dat vraagt wélk materiaal.

Wat er gebeurde:
1. `_wn("kozijnmateriaal", exact=True)` matchte die kop niet (na het afknippen vóór `" ("` blijft
   *"kozijnmateriaal afwijkend"* over, niet *"kozijnmateriaal"*).
2. Daardoor viel de code terug op **positie `r[15]`** — en dat is in de huidige export **`Type glas`**.
3. `_norm_kozijn_mat("Dubbel")` herkent dat niet → **default "Hout of kunststof"**.

**Gevolg:** het kozijnmateriaal was *altijd* hout/kunststof = NTA **kozijntype A (Ufr 2,4)** — precies het
**gunstigste** type. Metaal met thermische onderbreking is **3,8**, zonder onderbreking **7,0 W/m²K**
(NTA 8800 tabel 8.3). Volledig stil.

**Fix:** op naam lezen (`Kozijnmateriaal` óf legacy `Kozijn`), positionele fallback geschrapt, en bij
*"afwijkend = Ja"* → **leeg laten + luide melding** (de tool weet het materiaal niet; hout/kunststof
aannemen zou de gunstigste uitkomst geven).

**Nog te doen (formulier):** MagicPlan mist een vervolgvraag *"welk materiaal?"* met de opties
`Metaal (thermisch onderbroken)` / `Metaal (niet thermisch onderbroken)`. Zonder dat veld kan de
informatie de tool niet bereiken.

### 2. 🔴 Dubbele kolomnamen in de export → de lege variant won
De export bevat **`Kozijnmateriaal afwijkend (…)` twee keer**: index **13** (deur) en **16** (raam).
MagicPlan zet de velden van álle element-groepen in dezelfde WALL-tabel. Een eerste-match-lookup pakt
altijd index 13 — op een raamrij is die leeg, en andersom.

**Fix:** zowel `_wn` (raam, al eerder) als `_byname` (deur, nu) nemen de **eerste kolom mét een waarde**.

### 3. 🔴 Positionele fallbacks wijzen naar verkeerde kolommen
De legacy-fallbacks op vaste kolomindexen zijn achterhaald doordat er velden zijn bijgekomen:

| Fallback | Bedoeld | Wijst nú naar | Status |
|---|---|---|---|
| `r[15]` kozijnmateriaal | materiaal | **`Type glas`** | ✅ verwijderd |
| `r[17]` oriëntatie (deur) | kompas | **`Toevoerrooster type`** | ✅ guard `_norm_kompas` toegevoegd |
| `r[16]` glas (deur) | glastype | `Kozijnmateriaal afwijkend` | ⚠️ vuurt alleen als de naam-lookup faalt |
| `r[11]` oriëntatie (wand) | kompas | `Bovenlicht-paneel - bouwjaarklasse` | ✅ al geguard met `_norm_kompas` |

De deur-oriëntatie was het gevaarlijkst: zonder guard werd *"Zelfregelend (ZR)"* de oriëntatie.

### 4. 🟠 Wall n / Wall n+2 op dezelfde gevel (opgelost 29-7)
MagicPlan nummert wanden rondom de kamer; `n` en `n+2` liggen tegenover elkaar. Stonden beide op
dezelfde gevel met **verschillende** breedtes, dan zag de breedte-dedup dat niet en telde de tool beide
mee. Nu een **luide melding** (niet stil corrigeren — bij een L-vormige kamer is het correct).

### 5. 🟠 Kwaliteitsverklaring werd als "niet geïsoleerd" gelezen (opgelost 27-7)
Bij *Invoer = Kwaliteitsverklaring* slaat MagicPlan de vraag *"isolatie aanwezig?"* over → het veld bleef
leeg → **Onbekend** → de engine adviseerde isolatie op een al geïsoleerd dak/vloer.

---

## Aannames die WÉL in orde zijn (gecontroleerd, bewust)

Deze zijn **geverifieerd** en hebben een flag of zijn aantoonbaar veilig:

- **`_ih` wandhoogte** gebruikt `startswith("height")` → matcht *niet* op `Ceiling Height`. ✅
- **`fls`-weging** (grond/kruipruimte ×0,7, AVR ×0) volgt NTA §6.7.3 exact. ✅
- **Vloerbegrenzing ontbreekt** → "Kruipruimte" aangenomen **mét** luide melding. ✅
- **Spouw "Onbekend"** → `None`, niet `False` (False = geverifieerd géén spouw). ✅
- **Gebouwhoogte ontbreekt** → 0 + luide flag, bewust géén berekende schatting. ✅
- **Breedte-dedup gelijke breedtes** → meldt elke keer dat hij dedupliceert. ✅
- **Woningtype leeg** → `standaard_eis()` geeft `None` i.p.v. grondgebonden aannemen. ✅
- **PV "Onbekend"** → code 7 (onbekend kristallijn), niet 0 (kwaliteitsverklaring). ✅

## Structurele les
Twee patronen veroorzaakten **alle** vier de fouten:
1. **Eerste-match op een kolomnaam-fragment** terwijl er meerdere kolommen matchen → neem de eerste
   **mét waarde**, of match exact.
2. **Positionele fallbacks** op een export waarvan de kolomvolgorde meebeweegt → alleen gebruiken met
   een inhoudelijke guard (zoals `_norm_kompas`), anders schrappen.

Regressietests staan in `tests/run_tests.py` (secties W, Y, Z). 698 tests groen.

---

# Deel 2 — Defaults: wanneer mag de tool iets aannemen? (30-7)

Aanleiding (Renze): *"Dat komt omdat je een standaard had bepaald toch?"* — klopt. De kolom-bug maakte
het veld leeg; de **default** vulde het daarna stil met de **gunstigste** waarde.

## De regel die de norm zelf stelt
NTA 8800, voorwoord:
> *"...forfaitaire waarden die bedoeld zijn als **vangnet** voor parameters waarvan aard en kwaliteit
> onbekend zijn. In die gevallen wordt een **veilige (lees: conservatieve) waarde** voorgeschreven...
> als de detailinfo onbekend is, dan moet de **energetisch slechtste waarde** gekozen worden"* —
> en bij gedeeltelijk bekende info een *"genuanceerde slechtste waarde"*.

## De toetsregel die daaruit volgt
ISSO 82.1 over het kozijn: *"Om het type kozijn te bepalen, kijk je alleen naar het materiaal van het
kozijnwerk."* Het is **waarneembaar** — er bestaat geen 'onbekend'-route voor. Daarmee:

| Soort gegeven | Voorbeeld | Correcte omgang |
|---|---|---|
| **Waarneembaar** ter plaatse | kozijnmateriaal, glastype, daktype, begrenzing, ventilatiesysteem | **Vragen.** Ontbreekt het → **flag**, geen stille default |
| **Niet waarneembaar** (dicht) | isolatiedikte in een spouw/kap | NTA-forfaitair: *Onbekend* + **conservatieve** waarde (bijlage I) |
| **Beleidswaarde** | qv10 per bouwjaar, fls-weging | Vaste normwaarde, geen keuze |

Een default op een **waarneembaar** gegeven is dus per definitie een stille aanname.

## Inventarisatie van de defaults

| Default | Waarde bij ontbreken | Oordeel |
|---|---|---|
| `_norm_kozijn_mat("")` | Hout of kunststof (Ufr **2,4** = beste) | ⚠️ **gunstig** — waarneembaar gegeven. Verdedigbaar omdat het live veld luidt *"afwijkend (anders dan hout/kunststof)?"* (leeg = niet afwijkend), maar bij **"Ja"** weet de tool het materiaal niet → nu **leeg + luide flag** i.p.v. het gunstigste type |
| `_begrenzing_uit_naam()` | Buitenlucht | ✅ **conservatief** (fls=1, volledige ΔT) |
| isolatie ontbreekt | "Onbekend" | ✅ correct — triggert de forfaitaire bouwjaartabel (bijlage I) |
| vloerbegrenzing ontbreekt | "Kruipruimte" **+ melding** | ✅ met flag |
| `type_dak` ontbreekt | "Zadeldak" **+ melding** | ✅ met flag |
| spouw "Onbekend" | `None` (niet `False`) | ✅ False zou 'geverifieerd geen spouw' betekenen |
| gebouwhoogte ontbreekt | 0 **+ luide flag** | ✅ bewust geen schatting |
| woningtype leeg | `standaard_eis()` → `None` | ✅ geen aanname |

## Bevinding 6 🔴 — Drie vocabulaires liepen uit elkaar (stille dataverlies)
MagicPlan, de parser en de webapp gebruikten elk een eigen schrijfwijze. Een `<select>` toont alleen
waarden uit zijn eigen lijst; staat de waarde er niet in, dan toont hij de **eerste optie** en
**overschrijft opslaan de echte waarde stil**.

| Bron | Waarde | Webapp-lijst | Gevolg |
|---|---|---|---|
| CSV | `HR dubbel glas met coating` | `HR (dubbel glas met coating)` | glastype **gewist** |
| MagicPlan | `AOR (onverwarmd)` / `ASGR (…)` / `AVR (…)` | `AOR` / `Sterk geventileerd` / `AVR` | begrenzing → **Buitenlucht** |
| MagicPlan | `Onverwarmde kelder` | *ontbrak* | begrenzing → **Buitenlucht** |

**Fix:** normalisatie **bij binnenkomst** (`_norm_begrenzing`, `_norm_glaslabel`) naar één canonieke
set, en `Onverwarmde kelder` toegevoegd aan de webapp. Een onbekende waarde blijft nu **staan**
(zichtbaar voor de adviseur) i.p.v. stil te verdwijnen.

**Structurele bewaking:** testsectie **AA** faalt zodra een canonieke waarde niet in de webapp-lijst
staat — dan lopen de vocabulaires weer uit elkaar en weet je het meteen.

## Alignment-status (30-7)
| Onderdeel | MagicPlan live | Webapp | Parser |
|---|---|---|---|
| Glastype (9 opties incl. HR+) | ✅ | ✅ | ✅ genormaliseerd |
| Begrenzing (9 incl. ASGR/Water/kelder) | ✅ | ✅ | ✅ genormaliseerd |
| Woningtype (10) | ✅ | ✅ | ✅ |
| **Kozijnmateriaal** | ⚠️ alleen **Ja/Nee**-poort | 3 materialen | leeg + flag bij "Ja" |

**Openstaand formuliergat:** MagicPlan mist de vervolgvraag *"welk kozijnmateriaal?"* met
`Metaal (thermisch onderbroken)` / `Metaal (niet thermisch onderbroken)`. Zonder dat veld kan het
verschil tussen Ufr 3,8 en 7,0 de tool niet bereiken.
