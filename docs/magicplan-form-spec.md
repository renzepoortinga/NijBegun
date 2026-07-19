# MagicPlan form-spec — exacte veldnamen die de tool leest

> **Belangrijk:** de Statistics-CSV-parser (`magicplan/statistics_csv.py`) zoekt op **exacte
> veldnaam**. Noem de MagicPlan-velden dus **precies** zoals hieronder (incl. hoofdletters,
> spaties, haakjes), anders komt de waarde niet door. Categorische waarden mag MagicPlan 'dotten'
> (spatie/`/` → `.`); de parser herstelt dat voor de bekende velden.

Status 2026-06-17: **DE FORM IS BIJGEWERKT ÉN GEPUBLICEERD.** Alle hieronder genoemde velden staan
nu live in "Schil & zone" (toegevoegd via de MagicPlan-API: `POST /api/custom-forms/save` +
`/api/custom-forms/publish/`, geverifieerd: 21 velden, gepubliceerd v=9_0 naar de eigen workgroup).
De grafische editor bevroor bij mijn geautomatiseerde screenshots van de Type-dropdown; de API-route
was betrouwbaar en deterministisch. Een backup van de oude form staat in de browser-localStorage
(`__schil_backup_2026-06-16`). Deze spec blijft de bron-van-waarheid voor de veldnamen.

## Form "Schil & zone" (Applied to: Project)

### Al aanwezig (geverifieerd 16-6-2026 in de live editor) ✅
| Veldnaam (exact) | Type | Opties / opmerking |
|---|---|---|
| `Thermische massa vloeren` | List | Licht · Zwaar · Zeer zwaar (GEEN "Half zwaar") |
| `Thermische massa wanden` | List | Licht · Zwaar · Zeer zwaar |
| `Qv10-waarde (dm3/s.m2)` | Number | **Leeg laten** tenzij blowerdoor-meting (ISSO 7.1.5) |
| `Renovatiejaar` | Number | alleen bij aantoonbare energiebesparende maatregel (ISSO 7.1.4) |
| `Type dak` | List | Zadeldak · Lessenaar · Plat ✅ |
| `Bouwjaar-klasse (vloer)` | List | Tot 1965 · 1965 t/m 1974 · 1975 t/m 1982 · 1983 t/m 1987 · 1988 t/m 1991 · 1992 t/m 2013 · 2014 · 2015 t/m 2017 · 2018 t/m 2020 (…) · Vanaf 2021 (…) ✅ |
| `Spouwdikte (dak, mm)` | Number | aanwezig ✅ |

### Toegevoegd + gepubliceerd 2026-06-17 (via API) ✅
| Veldnaam (exact) | Type | Opties / default |
|---|---|---|
| `Woningtype` | List | Vrijstaand · Twee-onder-een-kap · Tussenwoning · Hoekwoning |
| `Gevelhoogte (m)` | Number | gebouwhoogte gevel; stuurt hart-op-hart-toeslag (ISSO 8.2) |
| `Hellingshoek dak` | Number | graden — **óf** de 3 maatvelden hieronder |
| `Dak vloerbreedte` | Number | overspanning ⟂ nok (m) — alternatief voor hellingshoek |
| `Dak nokhoogte` | Number | m (vanaf vloer zolder) |
| `Dak knieschothoogte` | Number | m (0 als geen knieschot) |
| `Dak orientatie zijde 1` | List | oriëntaties (N/NO/O/ZO/Z/ZW/W/NW) — schuin dakvlak 1 |
| `Dak orientatie zijde 2` | List | schuin dakvlak 2 |
| `Kopgevel orientatie 1` | List | driehoekgevel boven muurplaat (telt als gevel) |
| `Kopgevel orientatie 2` | List | tweede kopgevel |
| `Plat dak m2` | Number | bv. erker/aanbouw — los plat dakvlak |
| `Plat dak orientatie` | List | meestal `horizontaal` |

> Dak: **óf** `Hellingshoek dak` invullen, **óf** `Dak vloerbreedte`+`Dak nokhoogte`
> (+`Dak knieschothoogte`) — de tool rekent de helling dan via tan(α)=h/b. Zonder een van beide
> valt de tool terug op footprint = dak-m² en **flagt** dat (nameten).

> ✅ **Opgelost (17-6-2026) via de API.** De velden zijn programmatisch toegevoegd
> (`POST /api/custom-forms/save`, CSRF-header `X-CSRF-Token` uit de `csrfToken`-cookie) en
> gepubliceerd (`POST /api/custom-forms/publish/<id>`). Vorm gekloond van bestaande vragen
> (Spouwdikte=number, Type dak=list) zodat het schema 1-op-1 klopt. Toekomstige veldwijzigingen
> kunnen dezelfde route gebruiken (zie sessie-transcript) of handmatig in de editor.

## Per-element (WALL ATTRIBUTES) — element-Fields, niet de project-form
Deze horen bij de **wand/raam/deur** (Fields → toegekend aan Wall/Window/Door), niet bij de
project-form. De parser leest ze positioneel uit de WALL-sectie.

| Onderwerp | Eis | Status / actie |
|---|---|---|
| **Oriëntatie per buitengevel** | élke buitenmuur een oriëntatie (N..NW). Wand zónder oriëntatie = binnenwand (telt niet mee in de schil). | Instructie: tag ALLE buitenmuren. Onvolledige gevel wordt geflagd door de parser (omtrek×hoogte-check). |
| **Isolatie op wand** | mag **leeg/Onbekend** — NIET verplicht stellen | ⚠️ Controleer dat "Mark as mandatory" UIT staat op het isolatie-veld (editor was bevroren, niet kunnen verifiëren). |
| **Deur — rekenzone** | default **1** | Zet default-waarde 1 op het deur-rekenzone-veld. Tool gebruikt sowieso rekenzone=1 als default. |
| **Raam/deur — glas + kozijn** | glastype + kozijnmateriaal per raam; deur met ≥65% glas → telt als raam | reeds in de parser; vul per raam/deur in. |

## ⭐ OPNAME-INSTRUCTIE: begrenzing per gevel via de WANDNAAM (parent/child)
Omdat MagicPlan geen los begrenzing-veld per buitengevel toelaat, geef je de begrenzing aan **in de
naam van de wand**. De gevel is dan de **parent**: alle ramen/deuren in die wand erven de begrenzing
(én de oriëntatie). De parser (`statistics_csv.py: _begrenzing_uit_naam`) leest het token uit de naam.

| Zet dit in de wandnaam | Begrenzing (dossier) | In VABI (basisopname) |
|---|---|---|
| *(niets / gewone naam)* | Buitenlucht | GrenstAan 0 |
| `... AOR ...` of `... garage ...` of `onverwarmd` | AOR | **0 (basis = buitenlucht)** |
| `... AOS ...` of `serre` | AOS | 0 (basis) |
| `... grond ...` / `souterrain` / `talud` | Grond | 2 |
| `... kruipruimte ...` | Kruipruimte | 3 |
| `... kelder ...` (onverwarmd) | Onverwarmde kelder | flag (code te verifiëren) |
| `... water ...` | Water | flag |
| `... AVR ...` / `buurwand` / `woningscheidend` / `buurwoning` | — | **WAND VALT UIT DE SCHIL** |

**Voorbeelden:** `Achtergevel AOR garage` · `Kelderwand grond` · `Zijwand buurwand AVR` · `Voorgevel`
(= Buitenlucht). Een **woningscheidende wand** geef je dus óf geen oriëntatie, óf de naam-tag `AVR` —
beide houden hem uit de thermische schil (ISSO §8.1). In de **basisopname** tellen AOR/AOS als
buitenlucht (officieel NTA8800-formulier p.4); in een detailopname krijgt AOR code 4.

## Qv10 gemeten? (project-veld)
Voeg `Qv10 gemeten?` (List: **Ja · Nee**) toe; de parser leest het → `qv10_gemeten`. Alleen bij **Ja**
(blowerdoormeting) neemt VABI de ingevulde `Qv10-waarde` mee; bij **Nee** rekent VABI forfaitair op
bouwjaar/renovatiejaar (ISSO 7.1.5). Zonder dit veld blijft de tool veilig op "niet gemeten".

## ⭐ Gevel-naamgeving i.p.v. kompas per wand (25-6-2026 — na de 1e echte veldopname)
Veel makkelijker in het veld: benoem buitenmuren met hun **plek** en geef de richting maar één keer op.

| Veldnaam (exact) | Type | Opties / werking |
|---|---|---|
| `Oriëntatie voorgevel` (project) | List | N · NO · O · ZO · Z · ZW · W · NW. De tool leidt de andere gevels af. |
| *wandnaam* `Voorgevel` / `Achtergevel` / `Linkergevel` / `Rechtergevel` | — | tool zet de oriëntatie: rechter = voorgevel −90°, links +90°, achter +180° (Oost-vanaf-straat). |
| *wandnaam* `Rechtergevel ZW` (kompastoken erbij) | — | **override**: expliciete richting wint van de afleiding (schuin/onregelmatig huis). |

De parser (`statistics_csv.py`: `_gevel_naam_uit_naam` / `_orient_afleiden` / `_orient_uit_naam`) verwerkt dit;
de run toont de 4 afgeleide oriëntaties ter controle. De oude per-wand kompaskolom blijft werken (wint als expliciet ingevuld).

## Rc-bron + kwaliteitsverklaring per bouwdeel
| Veldnaam (exact) | Type | Opties |
|---|---|---|
| `Rc-bron gevel` / `Rc-bron vloer` / `Rc-bron dak` | List | Opgemeten dikte · Dikte onbekend · **Kwaliteitsverklaring** |

Bij **Kwaliteitsverklaring** kiest de tool een forfaitaire constructie en **vlagt** het; de adviseur zet
`Invoer=Kwaliteitsverklaring` + de Rc/U in VABI (golden rule).

## ⭐ Huidige woningstaat — isolatieplan sectie 3 (V1/V3/V4/V6) — TOEGEVOEGD 19-7-2026
Het isolatieplan-template splitst de huidige staat op naar **zijde** en kent regels die niet uit de
geometrie volgen. Zonder deze velden blijven die template-regels **leeg**. Form **Constructies**:

| Veldnaam (exact) | Sectie | Type | Opties | Vult template-regel |
|---|---|---|---|---|
| `Gevel - isolatie aan zijde` | GEVEL | List | Spouw (na-isolatie) · Binnenzijde (voorzetwand) · Buitenzijde (buitengevelisolatie) · Geen · Onbekend | **V1**: Spouwmuur isolatie / Gevel isolatie binnenzijde / buitenzijde |
| `Kierdichting` | GEVEL | List | Onbekend · Slecht (veel kieren/tocht) · Redelijk · Goed (recent gekit / tochtstrips) | **V6** Kierdichting (een qv10-meting wint) |
| `Bodemisolatie kruipruimte` | VLOER | List | Nee · Ja - folie · Ja - chips/schelpen · Ja - anders · Onbekend · n.v.t. (geen kruipruimte) | **V3** Bodemisolatie |
| `Dak - isolatie aan zijde` | DAK | List | Binnenzijde · Buitenzijde · Onbekend | **V4**: binnen-/buitenzijde hellend én plat dak |

Leeg laten mag: dan valt de gevel terug op de **spouwmuur**-regel en het hellend dak op de
**binnenzijde**-regel. De tool meldt wat er ontbreekt via `isolatieplan.fill_template.huidige_staat_gaten()`.
**Nog te pushen** — staan in `magicplan/forms/additions.json`; draai `magicplan/push_forms.bat`.

> `Vierpansraam in dakvlak` is bewust **niet** geautomatiseerd: die vul je zelf in het plan in.

## Meerdere installaties (genummerde velden)
| Voor | Veldnamen (exact) |
|---|---|
| 2e PV-systeem | `PV-2 - paneeltype` · `PV-2 - fabricagejaar` · `PV-2 - orientatie` · `PV-2 - hellingshoek (graden)` · `PV-2 - aantal panelen` · `PV-2 - oppervlak per paneel (m2)` (idem `PV-3 - …`) |
| Hybride verwarming | `Verwarming 2 - type opwekker` · `Verwarming 2 - HR-klasse` · `Verwarming 2 - installatiejaar` |
| Extra tapwater/koeling | `Tapwater 2 - toestel` · `Koeling 2 - type opwekker` · `Koeling 2 - splitsysteem` |

De tool zet alle PV-systemen volledig door; extra verwarming/tapwater/koeling worden **geflagd** (exemplaar 1 gewired, rest in Vabi).

> **Deze velden uit code zetten:** `magicplan/push_forms.bat` (of `python magicplan/form_push.py --live --publish`)
> voegt de ontbrekende velden idempotent toe vanuit `magicplan/forms/additions.json`. Offline dry-run:
> `python magicplan/form_push.py --form-file <opgeslagen-form.json>`.

## Form "Installaties" (Applied to: Project) — reeds herbouwd
Ventilatie (`Systeem (ventilatie)`, `Ventilatiesysteem (A-E)`, `Subsysteem (zie type)`) +
`Verwarming – type opwekker`. Subsysteem-enums (HR107/WTW-type) worden in Vabi door de adviseur
bevestigd (VABI-codes niet automatisch gegokt — golden rule).
