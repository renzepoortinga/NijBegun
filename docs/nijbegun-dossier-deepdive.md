# DEEP-DIVE: het complete Nij Begun-dossier (7-7-2026)

Bronnen: volledige kennisbank-harvest (fotowerkwijze 206000045149 + woningopname-handleiding 206000065616,
beide integraal gelezen), Beoordelingsformulier, M29 "Bijlage 1 eisen isolatieplantool", repo-audit
(agent, alle generatoren/validators), SOBOLT-walkthrough (Essenhage 32) + Sobolt-flyer maart 2026.

## 1. WAT MOET ER IN HET DOSSIER (de indien-set)
Per plan naar de kwaliteitscommissie (Teams, status 'beoordelen' → akkoord → bewoner + woningdatabase):
1. **Isolatieplan-Word** (M29-lay-out bewaard): gegevens+datums · **huidige staat V1–V6 VOLLEDIG**
   (n.v.t.-regels weghalen, niet leeg laten!) · plan op pagina 6 · samenvatting (SNN) · maatregelcodes ·
   toelichting/haalbaarheid (sectie 3) · **foto voorkant op het voorblad = adres**
2. **Ventilatieberekening** (tabel!) + visueel ventilatieplan + vaste bijlage "Waarom ventileren" (zit in template)
3. **Fotoblad** (Bijlage 3 in het Word) — echte foto's, niet alleen een checklist
4. **Plattegrond met aanduiding van de isolatiemaatregelen** (opname-handleiding §6!)
5. Foto's conform Fotowerkwijze (zie §3)

## 2. TOOL-STATUS (repo-audit): top-gaten op afkeurrisico
| # | Gat | Status |
|---|---|---|
| 1 | Foto voorkant niet ín het Word-voorblad (fill_template heeft geen image-insertie) | OPEN (bouwen) |
| 2 | Fotoblad/Bijlage 3 blijft leeg (alleen tekst-checklist) | OPEN (bouwen) |
| 3 | Huidige staat V1–V6: ±16 rijen leeg, V6 kierdichting nooit gevuld | OPEN (bouwen) |
| 4 | KWACO-validator draaide niet in de webapp | ✅ GEFIXT 7-7 (in afronden + indien-check) |
| 5 | Ventilatieberekening-tabel ontbrak in webapp-export | ✅ GEFIXT 7-7 (ventilatieberekening_*.txt) |
| 6 | Opname-/rapportagedatum/type advies niet invulbaar in webapp → hiaat in "1. Gegevens" | OPEN (klein) |
| 7 | Indien-check dekt 9/11 compleetheidscriteria (mist pagina-6/samenvatting/hiaten-scan) | DEELS (2 erbij 7-7) |
| 8 | 30%-ISDE-adviezen verdwenen uit de output | ✅ GEFIXT 7-7 (in haalbaarheid-bijlage) |
| 9 | Fotokwaliteit onbewaakt (8MP/5MB, duimstok-bij-opgemeten-dikte, typeplaatjes) | OPEN |
| 10 | Plattegrond-met-maatregelen ontbreekt (§6-eis) | OPEN (roadmap: MagicPlan-plattegrond) |

## 3. FOTOWERKWIJZE (volledig, kennisbank 206000045149)
Algemeen: overzichtsfoto per bouwdeel · ≥1 detailfoto per **cat-2-prijs** · geen bewoners/persoonlijke
spullen · scherp/recht/belicht · alleen onderbouwende foto's · ≥8 MP · SNN-upload max 5 MB.
- **V1-1 spouw**: overzicht per gevel · **boorgat + binnenzijde spouw** · voegwerk · bijzonderheden
  (betonlatei/overkapping) · staplaats hoogwerker indien nodig
- **V1-2 buiten**: aansluiting maaiveld + dakrand · **V1-3 binnen**: per ruimte + aansluitingen + cat-2 (WCD/leidingen/radiatoren)
- **V2 glas**: gevels met glas + **foto van de glaslat**
- **V3-1 vloer**: foto ín kruipruimte (niet betreden) · **diepte met duimstok/rolmaat ZICHTBAAR** · kruipluik + locatie
- **V3-2 zolder-/vlieringvloer**: overzicht + aansluitingen dak/muur
- **V4-1 dak binnen**: overzicht · dakbeschot (materiaal/kieren/lekkages) · constructie (gording-diepte!) ·
  dakkapellen · aansluitingen (muur/nok/dakraam) · doorvoeren · installaties
- V5: n.v.t. — MagicPlan-fotovelden dekken de kern (7 velden); per-maatregel-details via foto/checklist.py.

## 4. OPNAME-HANDLEIDING — regels die de TOOL nu afdwingt/kent
- **Kleine ruiten < 0,65 m² → rekenen als 0,65 m²** → ✅ parser 7-7 (raam-minimum + note)
- **Kruipruimte < 35 cm → vloerisolatie meestal niet mogelijk** → KWACO-check (draait nu in webapp)
- **Perimeter: woningscheidende wand telt NIET mee** → ✅ parser-note bij tussen/hoekwoning 7-7
- Gording-dikte = max isolatiedikte dak · glaslat-code/aansteker-test · koofwerk-meters = cat-2 ·
  spouw: boorgat kruising lint-/stootvoeg + endoscoop + netjes afvullen, 2e gevel herhalen
- Materialen: afstandsmeter, iPad, zaklamp, rolmaat, fietsspaak, boormachine, aansteker, endoscoop

## 5. DAK — "net als Sobolt" → ✅ GEBOUWD 7-7
SOBOLT: platte lijst dak-elementen per rekenzone met **directe m² + Rc per vlak** ("Dak 1" 33,92 m² ·
"Dak plat aanbouw 2" 5,53 m²) — geen geometrie-magie. Onze parser doet nu hetzelfde: **"Dakvlak N -
oppervlak (m²)" ingevuld → dat vlak 1-op-1 overgenomen (eigen type/oriëntatie/helling/begrenzing/isolatie),
auto-berekening overgeslagen** (alleen nog fallback). Plus webapp-opname-editor: dakvlakken bewerken/toevoegen.

## 6. GEVEL DEELS BINNEN / DEELS BUITEN — de werkwijze
MagicPlan kan wanden niet splitsen. SOBOLT lost het op met **losse gevel-elementen met handmatige m²**
("Gevel aanbouw 4" = 6,05 m²). Onze route (vandaag al werkend):
1. In MagicPlan: tag de wand **'narekenen'** in de naam (bv. `Achtergevel narekenen`) → tool flagt hem.
2. In de **webapp-opname-editor**: dupliceer de gevel → deel 1 = buitenlucht-m² (zelf gemeten/berekend),
   deel 2 = rest-m² met begrenzing AVR/AOR. Exact het SOBOLT-patroon, met VABI-export erachter.
(Toekomst: 2 override-velden op het wand-element "Deel buitenlucht (m²)" + "Begrenzing restdeel" —
na CSV-kolomkalibratie op de eerste echte export.)

## 7. SOBOLT-CONTEXT (flyer maart 2026 + walkthrough)
Sobolt NTA-rekensoftware = eigen rekenkern ("NTA 8800-gebaseerd", BRL 9501-marketinggraphic, geen
attestnummer genoemd), door Provincie Groningen goedgekeurd voor M29; **vanaf €5.000 per 100 adressen**
(≈ €50+/woning). Gebruikt door Gezond Verduurzamen. Onze route (Vabi = geattesteerd) is per M29-Bijlage-1
punt 7c de vóórkeursroute. UI-lessen overgenomen: gebouw-boom, directe m² per vlak, catalogus-kiezer met
bijkomende kosten, Qv10-na-maatregelen via renovatiejaar, berekening-blok, toelichting-op-advies.
LET OP automatisering: de SOBOLT-app heeft een closed shadow-DOM (niet scriptbaar); walkthrough = visueel.

## 8. VOLGENDE BOUWSTAPPEN (geprioriteerd)
1. Word-integratie: foto voorblad + fotoblad Bijlage 3 + V1–V6 volledig + datums-invoer (gat 1/2/3/6)
2. Foto-upload per checklist-item in de webapp (met 8MP/5MB-check) → fotoblad
3. Plattegrond-met-maatregelen (MagicPlan-plangeometrie) — dekt ook ventilatieplan-op-plattegrond
4. Wand-splitsing-velden in MagicPlan + parser (na eerste echte CSV)
5. Officieel niet-ingevuld-voorbeeld-PDF naast ons template leggen (PDF's lokaal aanleveren in out/)
