# Productie-gereed — status & werkwijze (bijgewerkt 23-6-2026)

Doel: **een MagicPlan-opname invullen voelt als VABI invullen, en daarna staat (bijna) alles klaar.**
Dit document zegt precies wat automatisch gaat en wat je nog in Vabi doet.

## ⭐ EINDOORDEEL (23-6-2026) — objecten-import nu óók foutloos, alle drie bibliotheken bewezen
**PRODUCTIE-GEREED voor de Nij Begun-route (schil + ventilatie) én de schil-invoer van het energielabel.**
Bewezen op een realistische tussenwoning: MagicPlan-CSV → dossier → **3 VABI-bibliotheken** (importeren
foutloos) → **Nij Begun isolatieplan** (Word) + ventilatieberekening + foto-checklist + validator + rapport.
**183/183 tests groen.** Alle schil-enums zijn **LIVE in EPA geverifieerd** (thermische massa 0/1/2,
begrenzing GrenstAan 0-9, Daktype 0/1/2) — niets meer gegokt.

**🔓 OBJECTEN-IMPORT VOLLEDIG WERKEND (23-6, live in EPA 12.0.1):** de "Enum mismatch" bij objecten-import
(de laatste blocker) is via bisectie tot de bron herleid en gefixt. Drie oorzaken, één voor één empirisch
geïsoleerd: (1) het Rekenzone>Algemeen-veld `<Gebruiksoppervlakte>` is een **enum/vlag** (export="1"), GEEN
m²-veld — de gemeten m² erin schrijven gaf de fout → nu niet meer gezet (Ag komt via de Verdiepingen-som +
vloer-hoofdvlakken); (2) het objecten-sjabloon was **12.0.0** terwijl de constructies 12.0.1 zijn → vervangen
door een verse **12.0.1-export**; (3) constructie-GUIDs **deterministisch** (uuid5) zodat objecten en
constructiebibliotheek naar identieke guids verwijzen. Constructie- én volledige Objectenbibliotheek
importeren nu foutloos; regressietests bewaken het. Detail: `vabi/refs/grenstaan_mapping.md`.

**PV nu VOLLEDIG ✅ (22-6):** zelf alle installaties in EPA aangemaakt + de flow geobserveerd +
Installatiebibliotheek geëxporteerd → codes geharvest (`vabi/refs/installatie_enums_EPA.md`). De
PV-sjabloonknoop (eerder lege `ZonneEnergieList`) is geïnjecteerd; de generator zet PV volledig
(systeem/paneeltype/fabricagejaar/bouwintegratie/oriëntatie N=0..NW=7/hellingshoek/aantal/oppervlak) en
**dit is end-to-end in EPA geverifieerd** (genereren → import: 12 × 1,70 = 20,40 m² PV, Zuid, 35° kwamen
foutloos door). Verwarming gasketel + tapwater individueel/combi/Gaskeur-CW zijn met anker-codes gewired.

**Nog NIET volledig (voor een compleet ENERGIELABEL, niet nodig voor Nij Begun):** de overige installatie-
detailcodes — **warmtepomp-bron/temperatuurklasse, koeling, biomassa, WKK, ventilatie-subsystemen + WTW,
tapwater-warmtepompboiler, distributie-temperatuurklassen** — vereisen elk nog 1 EPA-export om te harvesten
(golden rule: niet gokken → sjabloon-default + flag). Het volledige invoer-model (5 installaties, 177 velden,
ISSO + opnameformulier) staat klaar als spec in `docs/installaties-invoermodel-ISSO.md`. Tot dan: PV +
ventilatie + verwarming-opwekker(gasketel) + tapwater komen door, de rest vult de adviseur in Vabi. **Projectdossier (BRL 9500)**: de tool levert invoer + isolatieplan + foto-checklist;
de adviseur archiveert het volledige dossier (foto's/BAG/plattegrond/registratie EP-Online) — buiten
de tool. De integrale **Standaard/EP** blijft Vabi EPA-W (gouden regel).

## Proces-scope vs tool-scope — BRL 9500-W + ISSO 82.1 (deep-dive 23-6-2026)
Hoofdstuk-voor-hoofdstuk getoetst aan **ISSO 82.1 (7e druk)** + **BRL 9500-W (aangewezen 29-05-2026)** —
uitsluitend die twee als bron (zie `docs/ISSO-82.1-opnameguide.md`, `docs/BRL-9500W-proceshandleiding.md`,
`docs/projectdossier-checklist-bijlage3.md`, `docs/ISSO-BRL-gap-analyse.md`). Eerlijke afbakening:

| Wat de TOOL levert (opname-invoer) | Wat de ADVISEUR doet (proces/Vabi, buiten de tool) |
|---|---|
| ISSO-conforme schil-geometrie + begrenzing + oriëntatie + dak/vloer + Ag | opname-soort **basis (EP-W/B)** vs **detail (EP-W/D)** kiezen + adviseurniveau |
| 3 VABI-bibliotheken (importeren foutloos) incl. PV; ventilatie-balans; isolatieplan; foto-checklist; KWACO | **opdrachtgever schriftelijk informeren** (EP-Online/projectdossier-recht/CI-controle/klachten) |
| forfaitaire Rc/U/g op bouwjaar (Vabi rekent de norm) | bij **detailopname**: Rc/U/g onderbouwen (DoP/BCRG/opgemeten dikte) i.p.v. forfait |
| per-project-opslag (`out/projects/<postcode_huisnr>/`) | **registreren in EP-Online** (binnen 3 mnd) + juiste software-versie |
| flags voor alles wat niet zeker is (golden rule) | **projectdossier** (BRL Bijlage 3) compleet maken + **15 jaar** bewaren |
| | **representativiteit/herlabelen** (seriematig) — handmatig, buiten toolscope |

**Gap-analyse-cijfers:** 649 bevindingen — 41 gedekt / 169 deels / 313 ontbreekt / 126 n.v.t.-Vabi. Veel
"ontbreekt" is **bewust** (opname-/invoerhulp, niet de hele EPA). De 3 echte gat-clusters voor verdere
groei: (1) installatie-breedte (koeling/warmtepomp/tapwater+PV uit MagicPlan + enums harvesten), (2)
opnameklasse + gebouwtype expliciet, (3) BRL-projectdossier/bewijslast-laag. Roadmap: `docs/ISSO-BRL-gap-analyse.md`.

## In één oogopslag
- ✅ MagicPlan-form **"Schil & zone"** = uitgebreid + gepubliceerd (21 velden, VABI-getrouw).
- ✅ MagicPlan-form **"Installaties"** = herbouwd + gepubliceerd (conditioneel, VABI-getrouw): ventilatie +
  verwarming + koeling + tapwater + **zonne-energie (PV uitgebreid: mono/poly + fabricagejaar + bouwintegratie
  + oriëntatie + hellingshoek + aantal + Wp; zonneboiler; accu)** + **7 foto-velden** (vooraanzicht/huisnummer
  verplicht). De parser leest alle nieuwe velden.
- ✅ Opname (Statistics-CSV) → dossier → **3 VABI-bibliotheken** in één commando, **alle drie importeren foutloos**
  in EPA 12.0.1 (constructies + objecten + installaties — live bewezen 23-6).
- ✅ **183/183 tests groen**, alle Python parse-clean.
- ✅ End-to-end bewezen op een demo-tussenwoning (`out/demo_*`): gevels per oriëntatie, dak-per-vlak,
  Ag, perimeter, begrenzing, hart-op-hart-toeslag, ventilatie — allemaal correct in de objecten-XML.

## Werkwijze per opname (Energielabel én Nij Begun)
1. **MagicPlan-opname** met de form "Schil & zone" (élke buitenmuur een oriëntatie; woningscheidende
   wand géén oriëntatie; vul Woningtype, Gevelhoogte, dak-velden, Begrenzing vloer in).
2. Exporteer de **Statistics-CSV** (+ Report-PDF).
3. `python magicplan/statistics_csv.py --csv "...Statistics.csv" --straat .. --huisnummer .. --postcode .. --plaats ..`
   → `python vabi/generate_all.py --dossier out/dossier_csv.json`
4. EPA: nieuw project → Algemeen **Objecttype=Woning, Bouwfase=Bestaande bouw, Opname=Basisopname**,
   dan importeren **Constructies → Objecten → Installaties** → **Rekenen**.
5. Controleer de geflagde punten (zie hieronder) en meld af.

## Wat MagicPlan nu automatisch levert voor VABI ✅
| VABI-veld | Bron |
|---|---|
| Gevels per oriëntatie (m²) + begrenzing Buitenlucht | wand + oriëntatie |
| Ramen/deuren (m², glas, oriëntatie) | wand-subvlakken |
| **Dak per vlak** (schuine vlakken + kopgevel) | Hellingshoek dak / vloerbreedte+nok+knieschot |
| Plat dak | Plat dak m2 + oriëntatie |
| **Gebruiksoppervlakte Ag** + Verdiepingen + bouwlagen | Total living area + floors |
| **Vloer-perimeter** (randverlies) | Exterior perimeter |
| **Begrenzing vloer** (Kruipruimte/Grond/AOR → GrenstAan) | Begrenzing (vloer) |
| **Bouwjaar** + (renovatiejaar) | Bouwjaar-klasse |
| **qv10** (ISSO-correct: alleen als gemeten; anders forfaitair) | — |
| **Hart-op-hart toeslag** (tussen 0,44·h / hoek 0,22·h) | Woningtype + Gevelhoogte |
| Rc/U per vlak (forfaitair op bouwjaar/isolatie) | Bouwjaar + Isolatie |
| Ventilatie A–E + subsysteem | Ventilatie-velden |
| Thermische massa **Licht / Zwaar / Zeer zwaar** (alle drie LIVE bevestigd) | Thermische massa wanden/vloeren |
| **Installaties**: ventilatie + verwarming-opwekker + tapwater + **PV (uitgebreid)** + zonneboiler/accu | MagicPlan-form "Installaties" |
| **Foto's** (vooraanzicht, huisnummer, gevels, meterkast, installaties, detail) | 7 foto-velden in MagicPlan |

## Wat je nog in Vabi controleert/aanvult (bewust geflagd — golden rule: nooit gokken)
1. **Begrenzing 5/6** (AOS/ASGR) in een **detailopname** — in de basisopname tellen AOR/AOS/ASGR als
   buitenlucht (0, ISSO §6.3.4); 0/2/3/4 + kelder(7) + ander gebouw(9) gaan auto.
2. **Woningpositie/infiltratie** in VABI — woningtype stuurt de gevel-toeslag; de infiltratie-positie
   (Gebouwtype/Ligging-enum nog niet bevestigd) bevestig je in Vabi (party-walls modelleren we door ze
   uit de schil te laten).
3. **Installatie-detailcodes** (warmtepomp-bron/temperatuurklasse, koeling, biomassa, WKK, ventilatie-
   subsystemen+WTW, tapwater-warmtepompboiler) — voor het *energielabel* aanvullen; voor *Nij Begun*
   volstaat ventilatie + schil. PV + verwarming-opwekker(gasketel) + tapwater(combi) komen wél door.
4. **Gevel-volledigheid** — de tool flagt als getagde gevel < omtrek×hoogte (bij tussen/hoek is dat
   normaal: party-walls tellen niet mee). Controleer dat élke buitenmuur een oriëntatie heeft.

## Opgeloste enum-/import-blockers (23-6-2026, niets meer geblokkeerd op de schil)
- ✅ **Thermische massa 0/1/2** (Licht/Zwaar/Zeer zwaar) — alle drie LIVE bevestigd; auto.
- ✅ **GrenstAan 0–9** — probe geïmporteerd, dropdown-index = code; auto.
- ✅ **Objecten "Enum mismatch"** — root-cause gevonden + gefixt (Gebruiksoppervlakte-enum, sjabloon-versie
  12.0.1, deterministische guids). Alle drie de bibliotheken importeren foutloos. Zie het eindoordeel boven
  en `vabi/refs/grenstaan_mapping.md` (sectie "Objecten-import valkuilen").
- 🔒 Resterend (niet schil-blokkerend): Gebouwtype/Ligging-enum + de installatie-detailcodes (elk 1 EPA-export).

## Veiligheid / herstel
- MagicPlan-form-backup: browser-localStorage `__schil_backup_2026-06-16` (volledige oude definitie).
- VABI-import kan niet struikelen op onbekende enums (sjabloon-kloon + harde validatiepoort).
- Gouden regel bewaakt: tool rekent nooit NTA8800; Vabi blijft de geattesteerde rekenkern.
