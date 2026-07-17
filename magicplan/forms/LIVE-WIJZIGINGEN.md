# MagicPlan live forms — stand 25-6-2026 (via custom-forms/-fields API, geverifieerd)

Forms: **Object · Constructies · Installaties** + element-field-groepen **Gevel per wand · Vloer · Raam/paneel · Deur**
(workspace R.poortinga). Save/publish-roundtrip live bewezen. Backup: `magicplan_*_backup.json` (eerdere sessie) +
in-sessie `window.__BK_FORMS__/__BK_FIELDS__`. Geldige dataTypes: **list/number/image/bool** (GEEN vrije tekst →
Bron/Opmerkingen niet mogelijk in een custom-form). Section-node = minimaal `{id,name,type:'section',children,comparisonValue}`.

## Constructies = VABI-beslisboom (FORM = standaard, ELEMENT = override) — KERN
Per bouwdeel (GEVEL / VLOER / DAK) identiek opgebouwd, 1-op-1 als VABI EPA:
```
Invoer:  ① Kwaliteitsverklaring → 📷 Foto factuur (verplicht op form-niveau)
         ② Beslisschema → Isolatie aanwezig?
              ├ Ja      → Isolatiedikte onbekend?  ├ Ja → Bouwjaar (12 VABI-klassen)
              │                                     └ Nee → Isolatiedikte (mm) [+ Spouw? bij <40mm, alleen GEVEL]
              ├ Nee     → Spouw aanwezig? (alleen GEVEL)
              └ Onbekend→ Bouwjaar
+ Thermische massa (Licht/Zwaar/Zeer zwaar) + Begrenzing (Buitenlucht/Grond/Kruipruimte/AOR/AOS/AVR)
```
- **GEVEL** = met spouw-tak. **VLOER** = zonder spouw. **DAK** = per dakvlak (Dakvlak 1 + "Tweede/Derde dakvlak aanwezig?")
  elk met daktype·oriëntatie·m²·hellingshoek + dezelfde isolatie-boom + begrenzing; + **9 m²-vakjes** (N..NW + Horizontaal)
  als fallback bij type "Anders".
- **Element-override**: "Gevel per wand" (All Walls) + "Vloer" (**All Rooms = PER KAMER**, context 'room') dragen **exact dezelfde
  boom** (+ wand: oriëntatie-override; +rekenzone; +vloer: telt-mee-voor-Ag). Leeg = neem form-standaard; invullen = overrule per stuk.
  Vloer-override hangt nu per KAMER (living room→kelder, bedroom→AOS), niet meer op verdieping-niveau.
- **Rekenzone overal default 1**: MagicPlan kent geen veld-default → parser `_rz()` vult leeg → 1 (alleen invoeren bij overrulen).
- **2e ventilatie + 2e tapwater**: conditionele blokken ("Tweede ventilatiesysteem?" / "Tweede tapwaterinstallatie?") naast 2e verwarming.
  Parser leest 2e tapwater (tapwater_extra) + flagt 2e ventilatie (golden rule). Tests #37–#39, 246/246 groen.
- **Raam/paneel + Deur opgeschoond** (26-6): waren vol cruft (dubbele Type glas/Toevoerrooster + leftover wand-velden). Nu schoon:
  Raam = Type glas (Enkel/Voorzetglas/Dubbel/HR/HR+/HR++/TripleHR/Vacuümglas/Onbekend) · Kozijnmateriaal (hout-kunststof / metaal TO / metaal niet-TO) ·
  Toevoerrooster aanwezig?→type · Begrenzing-override · Raam/paneel-toggle. Deur = Type constructie · Type glas · Oppervlakte raam-in-deur · Kozijnmateriaal · Begrenzing.
  **Verwijderd** (hoorde niet bij glas): isolatiedikte, Rc-bron, oriëntatie, bron, spouw. Oriëntatie + begrenzing erft een raam/deur van de moederwand (parser parent/child).
  ~~TODO generator-check: glas-enum-mapping HR+/HR++/TripleHR/Vacuümglas verifiëren~~ **AFGEHANDELD (audit 15-7)**:
  Enkel/Dubbel/HR/HR+/HR++/TripleHR mappen correct; Vacuümglas -> HR++ mét flag (bewust). De ECHTE gaten zaten
  elders en zijn nu gefixt: **Voorzetglas** matchte de codebook-sleutel 'voorzetraam' niet (viel stil op Dubbel),
  en glas **'Onbekend'** viel stil op de eerste raam-template -> nu geflagd.
- "Gevel - project" (oude plan-groep) **leeggemaakt** (overbodig; Constructies-form dekt gevel-standaard).
- Bouwjaar-klassen exact: Tot 1965 · 1965–74 · 1975–82 · 1983–87 · 1988–91 · 1992–2013 · 2014 · 2015–17 ·
  2018–20 (1 jan/Overig) · 2021 (1 jan/Overig).

## Object / Installaties
Aanvoertemp 80/60+90/70; foto vooraanzicht+huisnummer → Object; spouwdikte-dak weg; PV-kwaliteitsverklaring; multi-PV (PV-2).
**Installaties VABI-getrouw (laatste ronde):**
- **Ventilatie-subsysteem conditioneel per type A–E** (VABI-labels uit refs: A1/A2a-c+onbekend, B1-3, C1..C5b, D1..D5c, E1;
  Type WTW conditioneel bij D/E). Oude platte "Subsysteem (zie type)" verwijderd.
- **Rekenzone inline** bij elke installatie (ventilatie/verwarming/koeling/tapwater/PV); losse REKENZONE-sectie weg; leeg = zone 1.
- **"Tweede verwarmingsinstallatie? (2e ketel / hybride)"** (hernoemd van hybride) → 2e volledige verwarming (2 CV-ketels of WP+ketel).

## Dak geconsolideerd naar Constructies (Optie A)
Alle dak-velden uit **Object** verwijderd (Object houdt: oriëntatie voorgevel, Qv10, renovatiejaar, woningtype,
gevelhoogte, Ag-aftrek zolder, 2 foto's). **Constructies → DAK** heeft nu bovenin een geometrie-blok
(Dak - vloerbreedte / nokhoogte / knieschothoogte / kopgevel oriëntatie 1+2) → standaard daktype = tool rekent
m² + kopgevel-driehoek vóór; type "Anders" = de 9 m²-vakjes. Per dakvlak: type/oriëntatie/m²/hellingshoek + isolatie-boom + begrenzing.

## Parser-stand (magicplan/statistics_csv.py) — GEWIRED + getest (243/243)
- Leest per bouwdeel de **VABI-beslisboom**: `<Gevel|Vloer|Dakvlak 1> - invoer` (KV→flag / Beslisschema) → isolatie
  aanwezig (Ja/Nee/Onbekend) → isolatiedikte onbekend?/bouwjaar/dikte (mm)/spouw → begrenzing → rc_bron/isolatie/dikte op SchilDeel.
- **DAK** uit Constructies: `Dakvlak 1 - daktype/hellingshoek/oriëntatie` + `Dak - vloerbreedte/kopgevel oriëntatie 1/2`
  → zadeldak/lessenaar/schild (auto-m² + kopgevel-driehoek); type Anders → `Dak m² <N..NW/Horizontaal>` (9 vakjes); plat → dakvlak.
- **Ventilatie subsysteem** conditioneel: leest `Subsysteem (A..E)` (whichever gevuld). **Rekenzone inline** per installatie.
- Alles met **fallback naar de oude platte velden** (oudere CSV's blijven werken). Tests #37/#38.

## RESTERENDE kalibratie — alleen op de eerste ECHTE Statistics-CSV
De **element-overrides** (per-wand/vloer invoer-boom: `Gevel/Vloer - invoer/isolatie aanwezig?/...`) exporteren als
WALL/FLOOR-attribuutkolommen; die kolomnamen/-posities ken ik pas uit een echte export. De parser leest de per-wand
override nu nog via de naamconventie + positionele kolommen — dat verfijn ik 1-op-1 zodra Renze één CSV exporteert,
plus de exacte project-veld-kolomnamen (MagicPlan kan ze net iets anders schrijven dan de form-labels).

## 8-7-2026 — Raam/paneel + Installaties LIVE bijgewerkt (browserconsole-route, geverifieerd + gepubliceerd)
- **Raam/paneel-veldgroep** (custom-fields, rec da2af963): "Toevoerrooster aanwezig?" opties nu **Nee|Ja**
  (default Nee vooraan); onder de toggle "Raam = Ja | Paneel = Nee" hangen nu 3 conditionele velden bij
  keuze **"Nee (dicht paneel)"**: `Paneel - isolatie aanwezig?` (Ja/Nee/Onbekend) · `Paneel - isolatiedikte
  (mm)` · `Paneel - Rc-bron`. Alle raam-velden waren al niet-verplicht + Hout of kunststof stond al vooraan.
- **Installaties-form** (custom-forms, rec 0c386069): `Meerdere PV-systemen?` (bool → 6 PV-2-velden) na
  sectie Zonne-energie + `Tweede opwekker (hybride)?` (bool → 3 Verwarming 2-velden) na sectie Verwarming.
  Form telt nu 31 top-level velden. → additions.json "NOG TE PUSHEN" is hiermee AFGEHANDELD.
- Werkwijze: in-page fetch + X-CSRF-Token; backups in localStorage `__fields_backup_2026-07-08` +
  `__forms_backup_2026-07-08`; save→verify (verse GET)→publish (rauwe workgroup-array, 200 success).
- **BEVESTIGD**: de .env-app-sleutel werkt NIET op /api/custom-forms|fields (login-HTML terug) — de
  browserconsole blijft dé route; form_push.py geeft daar nu een nette melding over.
- Parser-let-op: de CSV-kolom heet "Raam = Ja | Paneel = Nee" → matcher in statistics_csv aangepast
  (herkent raam+paneel in de kolomnaam); waarde "Nee (dicht paneel)" → paneel-SchilDeel. De nieuwe
  `Paneel - *`-detailkolommen kalibreren we bij de eerstvolgende echte Statistics-CSV (posities kunnen schuiven).

## 8-7-2026 (2) — Deur-groep VABI-conditioneel (LIVE gepubliceerd)
"Type constructie (deur)" opties versimpeld naar **Dichte deur | Deur met glas | Onbekend** (openslaand=
geometrie; bovenlicht=deur met glas + klein oppervlak; bovenpaneel=dichte deur). Glas-velden zijn nu
CONDITIONELE kinderen @ "Deur met glas": `Type glas (indien glas in deur)` + `Oppervlakte raam in deur (m²)`
+ NIEUW `Glas ≥ 65% van de deur?` (Nee|Ja = de VABI deur-met-raam≥65%-vlag). Dichte deur = geen extra
velden. Ids van bestaande velden behouden. Parser: deur-kolommen nu op NAAM (type constructie / type glas
(indien / oppervlakte raam in deur / 65%) met positioneel fallback; glas65-vlag uit de nieuwe vraag.

## 8-7-2026 (3) — Deur uitgebreid + kozijn-default-logic (LIVE gepubliceerd)
Deur: opties nu **Dichte deur | Deur met raam | Deur met 65% glas | Onbekend**; glas-velden conditioneel
per optie (raam: Type glas + Oppervlakte raam in deur; 65%: Type glas (65%-glasdeur) + Oppervlakte glas
65%-glasdeur). NIEUW **"Bovenlicht boven de deur?"** (Nee | Ja, met glas | Ja, met dicht paneel) bij ELKE
deur: glas-bovenlicht -> oppervlak (m²) [parser telt op bij glas-in-deur]; paneel-bovenlicht -> oppervlak +
isolatie aanwezig (Ja/Nee/Onbekend) + isolatiedikte [parser -> paneel-SchilDeel]. KOZIJN: "Kozijnmateriaal
afwijkend (anders dan hout/kunststof)?" (Nee|Ja -> dan pas de materiaalkeuze) in Deur ÉN Raam/paneel —
default = hout/kunststof, alleen afwijking invoeren. VABI-65%-vlag alleen bij de 65%-optie ('Deur met raam'
zet 'm NIET). Parser: naam-gebaseerde kolommen + legacy positioneel fallback; kalibratie op eerstvolgende echte CSV.

## 8-7-2026 (4) — VABI-boom afgemaakt: bouwjaarklasse bij paneel-Onbekend; 'Onbekend' weg bij deur (LIVE)
Deur: optie "Onbekend" VERWIJDERD (glas in een deur is altijd zichtbaar). Paneel-isolatie "Onbekend" ->
nieuwe conditionele vraag "Paneel - bouwjaarklasse" (raam-groep) resp. "Bovenlicht-paneel - bouwjaarklasse"
(deur-groep), met de 12 officiële klassen GEKLOOND uit de Constructies-form (Tot 1965 ... Vanaf 2021
(Overig)) — zelfde logic als VABI. Parser leest paneel-isolatie/dikte/bouwjaarklasse nu op naam; afwijkende
bouwjaarklasse wordt geflagd in opmerkingen (tool rekent forfaitair op projectbouwjaar; adviseur zet de
afwijking in Vabi). LET OP default-values: lijstvelden starten leeg in de app; 'default' = optie bovenaan.
Een échte voorgeselecteerde waarde (bv. raam-toggle op 'Ja (raam)') kan alleen via de editor-UI ("Add a
default value") — JSON-sleutel nog onbekend; 1x handmatig zetten en dan de JSON harvesten.

## 9-7-2026 (nacht) — TIKBAAR Gevelnaam-veld + kalibratie op echte Essenhage-export (LIVE)
NIEUW veld bovenaan "Gevel per wand": **"Gevelnaam (leeg = binnenwand)"** — lijst Voorgevel/Achtergevel/
Linkergevel/Rechtergevel/Buurwand (AVR). GEEN wandnamen meer typen: tik de keuze, de tool leidt de
oriëntatie af uit 'Oriëntatie voorgevel' en filtert Buurwand (AVR) uit de schil. Parser plakt de
kolomwaarde bij de wandnaam zodat alle bestaande token-logica werkt (test #52). E2E bewezen op de
gesimuleerde 'getikte' Essenhage-CSV: 3 gevels + 13 ramen + 2 deuren + 1 paneel(bovenlicht) + 2 dak-
vlakken + vloer -> 3 VABI-bibliotheken door de codebook-poort + webapp-flow (CSV-import/zip) groen.
LET OP: python-API vanaf deze machine faalt op TLS-interceptie (certificaat) -> foto's/plan-fetch via
script is follow-up; browser-route werkt.

## 11-7-2026 (deep dive dak+bouwjaar) — LIVE + EPA-import bewezen
- **EPA-IMPORT GEVERIFIEERD** (computer-use, EPA 12.0.1): Constructiebibliotheek (6 constructies) + Objecten-
  bibliotheek (1 object, Eengezinswoning/Hellend dak) uit de Essenhage-tap-CSV importeren BEIDE foutloos
  ("Import succesvol"). De nieuwe dak-geometrie geeft geen enum-mismatch.
- **DAK-HERONTWERP**: Constructies-form DAK-sectie = per dak (1..3) type-master (Plat/Zadel/Schild/Lessenaar/
  Afwijkend) met alleen de type-eigen velden conditioneel. Parser rekent per type (core/geometry): zadel 2
  vlakken + kopgevels auto op +/-90; schild 4 vlakken; lessenaar 1 vlak + hoge-zijde-note; plat=top-floor
  footprint of override; afwijkend=9 vakjes. Isolatieboom+begrenzing per Dakvlak 1/2/3.
- **Object-form**: Bouwjaar (verplicht) toegevoegd (ontbrak). **Gevel per wand**: 'Grenst aan buiten (m)'
  onder het narekenen-vinkje -> parser splitst zelf (meters x wandhoogte = gevel, rest buiten schil).
- **DEFAULT-VALUES**: fields.defaultValue geprobeerd (save 400 -> door node-property, ook 400). Opgelost via
  ZELFDOCUMENTERENDE veldnamen: "(leeg = raam/geen/hout-kunststof/1/buitenlucht)" suffixen live gezet.
- **GIDSEN** (webonderzoek + ISSO + bouwfysica): docs/bouwjaarklasse-eisen-gids.md (Rc-historie per klasse
  + aansluitdetails), spouwmuur-herkennen-gids.md (4 inline SVG's, metselverband/muurdikte), rekenwijze-gids.md
  (hoe de tool elk oppervlak berekent), dak-rekenmodel.md (formules per type), dak-invoer-marktonderzoek.md
  (INBRIX/SOBOLT/Vabi). Alle in de webapp-Guide (/gids/<slug>); md_naar_html laat nu inline SVG verbatim door.

## 15-7-2026 — DAK-redesign (webapp-wizard) + kopgevel-basis-fix + veld-relevantie-check
- **KOPGEVEL-BASIS-FIX (parser, GEEN form-push nodig).** De kopgevel-driehoek staat HAAKS op de nok; z'n basis is
  de OVERSPANNING (= footprint / noklengte), NIET de 'vloerbreedte tussen de kopgevels' (= de noklengte zelf).
  De oude code gaf de noklengte als basis door -> te kleine/grote kopgevel bij hoek-/vrijstaande woningen (bij een
  tussenwoning viel het niet op: kopgevels = buurwand, weggelaten). Nu: basis = footprint/noklengte, of de
  expliciete overspanning als die is ingevuld. Geldt voor de per-dak- én de legacy-zadeldak-route. Test #66.
- **NIEUW MAGICPLAN-VELD (te pushen in Constructies → DAK → zadel-geometrieblok):**
  `Dak zadel - overspanning (m, leeg = auto)` (number, niet verplicht).
  Help: "De diepte waarover het dak schuin loopt (= de basis van de kopgevel-driehoek). Samen met
  'vloerbreedte tussen de kopgevels' (= noklengte) is het dak volledig expliciet: hellend vlak = schuine zijde x
  noklengte; kopgevel = driehoek met basis = overspanning. Leeg = de tool leidt de overspanning af (footprint/noklengte)."
  Parser leest 'm al; zolang het veld nog niet gepusht is, rekent de tool via footprint/noklengte (de fix).
- **WEBAPP 'Dak toevoegen'-wizard** (opname-editor): plat / zadeldak-via-driehoek (overspanning c + noklengte +
  hellingshoek + kopgevel-buiten-toggles, live voorbeeld) / 9 geometrieën; herhaalbaar tot 20, auto-genummerd;
  + dakraam per dakvlak (deelvlak op het DAK-hoofdvlak). Dit is dé plek voor complexe daken.
- **VELD-RELEVANTIE-CHECK (zadeldak) — alles nog nodig, maar 2 routes naar hetzelfde:**
  - HELLING: `hellingshoek` (DIRECT meten = aanbevolen) OF `nokhoogte boven zoldervloer` + `knieschothoogte`
    (afgeleid; alleen als je de hoek niet direct kunt meten).
  - FOOTPRINT/OVERSPANNING: `overspanning` x `vloerbreedte tussen de kopgevels(noklengte)` (expliciet, aanbevolen)
    OF `grondoppervlak dat het dak overspant` (footprint direct) OF auto (verdieping onder de zolder).
  - ALTIJD nodig: `Type dak`, `oriëntatie dakvlak 1`. OPTIONEEL: `hellingshoek vlak 2` (asymmetrisch).
  - Aanbeveling: zet in MagicPlan de PRIMAIRE route bovenaan (oriëntatie + hellingshoek + overspanning +
    noklengte), en label nokhoogte/knieschot/grondoppervlak als "alleen als je niet direct kunt meten".
