# CLAUDE.md — Nij Begun & EPA isolatieplan-tool

## Wat dit is
Standalone tool die één woningopname omzet naar (A) energielabel-invoer (Vabi EPA-W) en
(B) een Nij Begun isolatieplan (Maatregel 29): ingevuld Word/PDF + JSON + ventilatieberekening
+ foto-checklist + KWACO-validatie. Eén commando; draait zelfstandig (Python of .exe), geen
Cowork/Claude Code nodig om te gebruiken.

## Gouden regel (architectuur)
Reken NTA 8800 NOOIT zelf. Vabi EPA-W (geattesteerd) is de rekenkern; deze tool levert invoer
aan en leest de uitkomsten (monitoringbestand). Zo blijft Renze in de toegestane handmatige
adviseur-route en buiten de tool-validatieplicht.

## Draaien
    pip install -r requirements.txt
    python run.py --from-monitor "monitor.xml" --straat ".." --plaats ".." --woningtype ".."
    # of sleep een monitor-XML op run.bat ; of bouw een .exe (zie README)
    python dashboard/app.py    # lokaal dashboard op http://127.0.0.1:5000 (of run_dashboard.bat)
    python vabi/monitor_generate.py --dossier dossier.json --out out/import_monitor.xml  # -> VABI-import
    python vabi/sanity.py --dossier dossier.json    # parameter-sanity-check (nameten/outliers)
    python magicplan/extractor.py --project-id <ID>   # MagicPlan-opname -> dossier (live, .env)
    magicplan/push_forms.bat                          # MagicPlan custom-forms bijwerken uit code (live, .env; idempotent)
    python magicplan/form_push.py --form-file <json>  # OFFLINE dry-run van de form-merge (geen internet nodig)
    python catalog/api_client.py --refresh            # Nij Begun catalogus-API -> catalog.json (live, .env)
Output in out/: isolatieplan_*.docx, dossier_*.json, rapport_*.txt,
ventilatieberekening_*.txt, fotochecklist_*.txt, run.log
Dashboard bewaart per project in out/projects/<postcode_huisnr>/ (incl. import_monitor_*.xml).

## Mappen / modules
- core/dossier.py        canoniek datamodel = single source of truth (incl. installaties-blok:
                         Verwarming/Tapwater/Koeling/ZonneEnergie, gespiegeld aan VABI EPA 12)
- catalog/               Maatregelencatalogus.xlsx -> catalog.json (+ price_dossier.py)
- catalog/api_client.py  Nij Begun catalogus-API -> catalog.json (versie gepind; .bak backup;
                         defensieve veldmapping, 1x live verifieren; offline --map-json)
- engine/measure_engine  kiest goedkoopste catalogus-maatregel per vlak (Rc/U-drempels)
- engine/advies_logic.py  beslislogica "welk advies wanneer" (offline regels per bouwdeel A-E +
                         ventilatie-na-isoleren + kierdichting); zie docs/maatregel-beslislogica.md
- engine/advies_text.py  begeleidende advies-tekst (SOBOLT-achtig, offline/deterministisch)
- magicplan/extractor.py  MagicPlan REST API v2 -> dossier-GEOMETRIE (base cloud.magicplan.app/api/v2,
                         headers key+customer; --test/--probe; geen internet in deze sandbox -> .bat draaien)
- magicplan/report_parser.py  MagicPlan project-report-PDF -> FORM-ANTWOORDEN (API geeft die niet!);
                         label/waarde-parse, 39 velden + per-raam kozijn. Zie memory magicplan-api-discovery
- magicplan/assemble.py   HYBRIDE: report-antwoorden + API-geometrie -> compleet dossier (build_dossier);
                         getest op echte Oosterkade-opname -> volledige isolatieplan-pijplijn. Gevel-m2 =
                         benadering (4*sqrt(footprint)*1.15 x hoogte - openingen); adviseur verifieert in Vabi
- magicplan/statistics_csv.py  GEVEL-NAAMGEVING (na 1e echte opname): benoem muren voorgevel/achter/links/
                         rechts; tool leidt oriëntatie af uit 'Oriëntatie voorgevel' (rechter -90/links +90/
                         achter +180, Oost-vanaf-straat). Naam-override 'Rechtergevel ZW' wint. Ook: meerdere
                         PV-systemen (PV-2 ...), extra verwarming/tapwater/koeling (Verwarming 2 ...), rc_bron
                         Kwaliteitsverklaring -> geflagd. Per-vloer begrenzing via ruimtenaam (bv. 'Slaapkamer AOR')
- magicplan/form_push.py + forms/additions.json + push_forms.bat  MagicPlan custom-forms bijwerken UIT CODE
                         (i.p.v. de wisselvallige editor): voegt ontbrekende velden NA de juiste sectie toe +
                         required-vlaggen, idempotent. Merge+validatie offline getest; live save/publish via .env
                         (context=['plan'], name_escaped strippen). Renze draait push_forms.bat (geen net in sandbox)
- vabi/codebook.py       'taal van VABI' afgeleid uit een echte export (Naam-decode); harde
                         validatie-poort assert_valid(veld,code). Bron: vabi/refs/standaard_constructies_*.xml
- vabi/harvest.py        leest willekeurig veel per-tegel exports -> vabi/refs/code_universe.json
                         (per veld de set geldige enum-codes + Naam-hints, gemerged over projecten/versies).
                         .epa zelf is VERSLEUTELD; voer = onversleutelde EPA-export per tegel (Constr/Inst/Obj)
- vabi/extract_strings.py  ript alle leesbare strings (UTF-16+ASCII) uit EPA_NTA8800.exe (native);
                         de C++-namen `Combo_Enum_Base@W4<Enum>@<Domein>` geven de COMPLETE dropdown-kaart
- vabi/build_enum_catalog.py  inventory + code_universe + monitor -> vabi/refs/vabi_enums.json
                         (per veld: codes+betekenis+verplicht; dekkingsrapport welke nog codes missen)
- vabi/harvest_monitor.py  leest NTA8800-monitoringbestanden -> refs/monitor_enum_universe.json
                         (enum-waarden + VERPLICHT-vlag: in alle N projecten = nodig voor resultaat)
- vabi/constructie_generate.py  dossier -> importeerbare Constructiebibliotheek (kloon 219-standaard;
                         resolve_constructies geeft per schildeel naam+guid, gedeeld met objecten)
- vabi/objecten_generate.py  dossier -> Objectenbibliotheek (geometrie: Hoofdvlak/Deelvlak; sjabloon
                         refs/objecten_template.xml; vlak-refs -> embedde constructies)
- vabi/installatie_generate.py  dossier -> Installatiebibliotheek (kloon sjabloon + ventilatie/vrije-tekst)
- vabi/generate_all.py   dossier -> alle 3 bibliotheken + IMPORTEREN.txt (1 commando)
- vabi/result_reader.py  VABI-export/monitor (Summary) -> kerngetallen + Standaard-toets
                         (energiebehoefte <= Standaard ?) voor het rapport
- vabi/monitor_xml.py    VABI NTA8800-monitoringbestand -> dossier (parser) [oude route]
- vabi/monitor_generate.py  dossier -> monitoring-XML [VERLATEN: enum-mismatch, zie memory; nu per-tegel bibliotheek]
- vabi/sanity.py         parameter-sanity-check vóór VABI-export (gebouwhoogte/plafond-outliers,
                         ontbrekende orientatie/begrenzing, dubbele ruimtenamen) -> "nameten"-lijst
- ventilatie/            ventilatieberekening + balans (0,7 dm3/s.m2; keuken21/bad14/toilet7)
- foto/checklist.py      foto-checklist per maatregel (Fotowerkwijze)
- isolatieplan/fill_template.py  vult officieel Word-template: gegevens, maatregelen A-E,
                         HUIDIGE STAAT V1-V6, warmteverlies
- validator/validate.py  KWACO "sluitend"-checklist
- dashboard/app.py       lokaal single-user Flask-dashboard (login): upload monitor/dossier ->
                         sanity + isolatieplan + VABI-import-XML; per project in out/projects/
- run.py                 orchestrator; config.json = per-adviseur instellingen
- MagicPlan-opnameschema + bouwgids: ../MagicPlan_Forms_Fields_schema_v0.3.json (+ -bouwgids.md)
  in de map "Nij Begun & EPA" (twee templates: Energielabel vs Nij Begun; VABI-getrouw)

## Status (juli 2026) — 299/299 groen. LIVE GEHOST op nijbegun.poortinga-energieadvies.nl (TransIP VPS 37.97.195.196,
Docker+Caddy, MFA). NIJ-BEGUN-FOCUS-SLAG (7-7): webapp volledig op Nij Begun (schil+ventilatie) gericht ná parallelle
audit (6 agents). (1) SCOPE gezuiverd: kennismakingsmail (dashboard/leads.py VOORBEREIDING) vraagt GEEN cv-ketel/
warmtepomp/PV meer (= energielabel, niet M29); opname 'Installaties'-kaart -> 'Ventilatie' prominent + verwarming/
tapwater dichtgevouwen 'alleen voor het energielabel' (velden blijven bestaan als sjabloon-fallback voor de VABI-
installatiebib — alleen ventilatie beïnvloedt de Standaard/warmtebehoefte). (2) FLOW herzien naar SOBOLT-model: leeg
project (geen upload) -> Opname (MagicPlan-CSV-import + editor + VABI-import) -> Huidige staat (VABI-export terug =
nulmeting) -> Maatregelen -> VABI-toets -> Afronden (foto's + PDF+JSON) -> Opleveren. Woningtype = dropdown. (3) LEADS
-> PROJECT: knop op de leadregel (vanaf 'afspraak gepland') maakt idempotent een project met adres/BAG/bouwjaar
(GEEN persoonsgegevens in dossier — AVG); lead krijgt project_tag + status 'opname gedaan' (routes leads_project/
_lead_naar_dossier; leads.set_project_tag). (4) MAGICPLAN-FOTO'S: magicplan/photos.py (photo_entries + download_photos
met injecteerbare fetch, offline getest; live fetch_project_photos via v2-API key+customer -> out/projects/<tag>/fotos/;
golden rule: alleen directe foto-URL's, id-zonder-URL wordt geflagd; CLI --project-id/--tag; fotos/ mee in export-zip).
(5) APPLE HIG: dashboard/static/app.css volledig herschreven (design-tokens, prefers-color-scheme DARK MODE + data-theme,
env(safe-area-inset), 44/46px touch-targets, :focus-visible, breakpoints 700/480px, stepper-inklap, tabellen in
.table-wrap); viewport-fit=cover; class="muted small" gequote. (6) docs/spouwinspectie-gids.md (endoscopie-werkwijze.md
opgegaan -> pointer). Bouwjaar-hint per tijdvak was al compleet (7 ERAS matchen de gids-headers). Zie ook 'Fix 403
achter Caddy' (origin-check host-only + ProxyFix bij NIJBEGUN_HTTPS). Deploy-update: git push -> op VPS `cd /opt/nijbegun
&& git pull && sudo docker compose -f deploy/docker-compose.yml up -d --build`.
## Status (juni 2026) — 230/230 groen. PRODUCTIE-GEREED. Zie docs/PRODUCTIE-GEREED.md + docs/NTA8800-opname-MASTERPLAN.md.
ISOLATIEPLAN-WEBAPP v2 (6-7, SOBOLT-achtig, lokaal Flask): `python dashboard/app.py` -> 6-stappen-flow:
Inladen (CSV/dossier/VABI-export + foto's) -> OPNAME-EDITOR (volledige gebouw-boom per rekenzone bewerkbaar:
dak/gevel/vloer/kozijn m2/Rc/U/orientatie/begrenzing/rekenzone + dupliceren/toevoegen/verwijderen; Algemeen
BAG-id/Ag/qv10/orientatie-voorgevel; Installaties; verliesopp+Ag+compactheid; export HUIDIGE staat -> VABI-zip
0-meting) -> Maatregelen (suggesties Standaard/30%-ISDE ÉN zelf kiezen uit volledige catalogus-boom
measures.catalogus_boom: kern + bijkomende X-kosten + biobased-badge + eigen hoeveelheid; technische-
haalbaarheid-veld per maatregel = M29 Bijlage 1 punt 13) -> VABI-toets (berekening-blok standaard/warmte-
behoefte/kosten/verliesopp/compactheid; Qv10-na-maatregelen via RENOVATIEJAAR-variant zoals het portal;
toekomstige-staat-libs + upload-terug -> verdict) -> Afronden (persoonlijke toelichting -> haalbaarheid_
toelichting-bijlage; Word + ventilatieplan-SVG + Beoordelingsformulier-check) -> Export-zip. GUIDE bijgewerkt.
M29-TOOL-EISEN: Downloads/"Bijlage 1 eisen aan de isolatieplantool.pdf" gelezen (26-6) — webapp voldoet aan
vrijwel alle functionaliteiten; validatie-route (10 ref-woningen) alleen nodig bij distributie/zelf rekenen;
Vabi-route = "bij voorkeur geaccrediteerde RVO-software" (punt 7c). Licentiemodel: max EUR 50/plan, EUR 15k
eenmalige ontwikkelvergoeding mogelijk. End-to-end getest (test-client).
LEADS-MODULE (26-6, /leads): Nij Begun-portal-mail ("AdviseurToegekend", JSON-blok van smarttwin.nl) plakken ->
lead geparsed (dedupe op BAG-id) -> statusflow (nieuw..afgerond) -> concept-kennismakingsmail (adviseur verstuurt
ZELF; vraagt bewoner ISSO-bewijslast klaar te leggen) -> CSV-export. Data lokaal in out/leads (AVG). BAG-KNOP:
dashboard/bag.py verrijkt met straat/woonplaats/bouwjaar/m2 via PDOK (GEEN sleutel; live geverifieerd): Locatie-
server (nummeraanduiding_id = BagAdresId uit de mail!) + kadaster/bag/wfs/v2_0 (LET OP: CQL_FILTER genegeerd ->
bbox om centroide + client-side match op verblijfsobject-id). Internet nodig -> draait op adviseur-machine.
Nij Begun-eisen verwerkt uit de kennisbank (docs/nijbegun-kennisbank-eisen.md): vuistregels ventilatie,
Beoordelingsformulier (= indien-check), fotowerkwijze, Standaard-vs-30%-ISDE-regel.
CATALOGUS-API LIVE (25-6, geverifieerd): catalog/api_client.py --refresh haalt nu de ECHTE Nij Begun-API op
(api.nij-begun.project.abl.nu, GEEN auth; JSON:API GET /api/v1/measures; spec /apipie.json?type=swagger). 192
measures -> 287 catalogrijen (regularCosts=m²-brackets, contractorValuePerUnit=incl btw; additionalCosts=X-codes,
gededupe). Prijzen matchen catalog.json (V1-1-A1 23.09≈23.0867). catalog.json blijft fallback; --refresh draait
LOKAAL (sandbox=geen internet). Offline mapping-test in de suite. BOUWJAARKLASSE-OPNAMEGIDS (workflow):
docs/bouwjaarklasse-opnamegids.md = bouwfysica per tijdvak (constructie/installaties/risico's/let-op/maatregelen).
GITHUB: repo is git-init + .gitignore (geheimen/config.json/out/.epa uitgesloten) + commit op 'main'; pushen doet
Renze lokaal (gh niet geinstalleerd; sandbox=geen net). MAGICPLAN (25-6 live geverifieerd): Object/Constructies/
Installaties gepubliceerd + compleet (oriëntatie voorgevel, Schilddak+Lessenaarsdak, rekenzone per installatie,
7 foto's, PV-detail, element-overrides Rekenzone/Rc-bron/Isolatiedikte). 2 gaten in form-als-code (additions.json),
nog te pushen via push_forms.bat: 'Meerdere PV-systemen?' + 'Tweede opwekker (hybride)?'.
Roadmap (nog open): ventilatieplan op echte MagicPlan-plattegrond · output 1-op-1 matchen aan de voorbeeldplan-
PDF's (1930/70/93/2002; folder 206000101610) · 30%-ISDE-bucket apart in de plan-output.
DAKTYPES + REKENZONE (25-6): core/geometry.py + parser kennen nu naast zadeldak ook LESSENAARSDAK (1 schuin
vlak=footprint/cos) en SCHILDDAK/hip (alle zijden dak, GEEN verticale kopgevel; totaal=footprint/cos verdeeld
over de zijden, geflagd voor Vabi-verfijning). Type dak-form heeft Zadeldak/Lessenaarsdak/Schilddak/Plat dak.
REKENZONE komt mee: per vlak via naam-token ('... zone2'/'rekenzone 3'/'rz2'), per installatie via Installaties-
form-velden ('Ventilatie - rekenzone' etc.); SchilDeel.rekenzone + rekenzone op alle installatie-dataclasses.
Multi-zone wordt GEFLAGD — multi-zone VABI-geometrie (meerdere Rekenzone-knopen) nog niet geautomatiseerd:
vereist één multi-zone VABI-export om de XML-structuur te leren (golden rule, zoals single-zone destijds).
OBJECTEN-IMPORT VOLLEDIG WERKEND (23-6, LIVE BEWEZEN): de Constructie- ÉN volledige Objectenbibliotheek importeren
nu FOUTLOOS in EPA 12.0.1. "Enum mismatch" bij objecten was de laatste blocker; root-cause via bisectie (clean
template importeert → transformaties één voor één toegevoegd): (1) Rekenzone>Algemeen-`<Gebruiksoppervlakte>` is
een ENUM/vlag (export="1"), GEEN m²-veld → de gemeten m² erin schrijven gaf "Enum mismatch" → FIX: niet zetten,
Ag dragen via Verdiepingen-som + vloer-hoofdvlakken; (2) objecten-sjabloon was 12.0.0 (120000061) ↔ constructies
12.0.1 → vervangen door verse 12.0.1-export (objecten_template.xml = 120001001; bron _v1201_source.xml, oude
_v1200.xml.bak); (3) constructie-GUIDs deterministisch (uuid5) zodat objecten↔constructiebib identiek verwijzen.
Details + bewijs: vabi/refs/grenstaan_mapping.md (sectie "Objecten-import valkuilen"). Regressietests bewaken dit
(XmlVersie==120001001, Gebruiksoppervlakte≠m², guid-determinisme, refs-bestaan). TypeBouwwijzeVloeren=0 (Licht)
nu OOK direct bevestigd. MAGICPLAN "Installaties"-form HERBOUWD+GEPUBLICEERD (conditioneel, VABI-getrouw): ventilatie
+ verwarming(opwekker→HR-klasse/WP/afgifte/aanvoertemp/jaar) + koeling + tapwater + ZONNE-ENERGIE (PV uitgebreid:
mono/poly/paneeltype + fabricagejaar + bouwintegratie + oriëntatie + hellingshoek + aantal + Wp; zonneboiler; accu)
+ 7 FOTO-velden (dataType image; vooraanzicht+huisnummer verplicht). Parser leest alle nieuwe velden (statistics_csv).
OPNAME-WORKFLOW VERSIMPELD (25-6, na Renze' 1e echte veldopname — "klungelen met nameten" eruit): (a) GEVEL-
NAAMGEVING i.p.v. kompas per wand — benoem muren voorgevel/achter/links/rechts, geef alleen 'Oriëntatie voorgevel'
op, tool leidt de 3 andere af (rechter -90/links +90/achter +180, Oost-vanaf-straat-conventie; naam-override
'Rechtergevel ZW' wint; run toont de afgeleide oriëntaties ter controle); (b) MEERDERE PV-systemen (PV-2/PV-3...)
+ extra verwarming/tapwater/koeling (Verwarming 2...); (c) KWALITEITSVERKLARING per bouwdeel (rc_bron) -> geflagd
voor VABI; (d) per-vloer begrenzing via ruimtenaam (bv. 'Slaapkamer AOR'). Nieuw: docs/OPNAME-WERKINSTRUCTIE.md
(per-kamer-checklist) + docs/gevel-kompas.svg; magicplan/form_push.py (+forms/additions.json+push_forms.bat) zet de
benodigde formvelden uit code in MagicPlan (idempotent; merge offline getest). 207/207 tests groen.
MAGICPLAN FORMS HERSTRUCTUREERD NAAR VABI-MODEL (25-6, LIVE via Brave-sessie + form-API): "Schil & zone" gesplitst
in 3 project-forms — **Object** (geometrie/identificatie + Oriëntatie voorgevel) · **Constructies** (geveltype/
thermische massa/spouw-dak/Rc-bron per bouwdeel) · **Installaties** (ongewijzigd). De element-Fields (overrides op
wall/vloer/raam/deur) bestonden al (oriëntatie/isolatie/begrenzing-anders/spouw/bron/**rekenzone**) en zijn op
wall/vloer/raam aangevuld met **Isolatiedikte (mm) + Rc-bron** (per-vlak override van de isolatiewaarde). Alle 3 forms
+ 5 field-groepen gepubliceerd naar workspace R.poortinga. Backups: browser-download magicplan_{forms,fields}_backup.json.
Exacte API-endpoints (create/save/publish + cookie-CSRF + publish-body=rauwe array) in memory magicplan-form-api.
LET OP-vervolg: project-velden (Oriëntatie voorgevel, Rc-bron) komen naam-gebaseerd via PLAN ATTRIBUTES (al gewired);
de element-overrides komen via WALL ATTRIBUTES die de parser POSITIONEEL leest → na de eerstvolgende echte CSV-export
de kolomposities verifiëren (de extra override-kolommen kunnen schuiven).
INSTALLATIES (22-6, W5 deels): zelf alle installaties in EPA aangemaakt, flow+if-this-then-that geobserveerd,
Installatiebibliotheek geëxporteerd → codes geharvest (vabi/refs/installatie_enums_EPA.md). PV VOLLEDIG gewired +
END-TO-END GEVERIFIEERD (genereren→import EPA: 12×1,70=20,40 m² PV/Zuid/35° foutloos doorgekomen): ZonneEnergie-
sjabloonknoop in installatie_template.xml geïnjecteerd (was leeg), generator zet systeem/paneeltype/fabricagejaar/
bouwintegratie/oriëntatie(PV-enum N=0..NW=7, ≠ geometrie)/hellingshoek/aantal/oppervlak; geen-PV→knoop weg.
Verwarming gasketel TypeOpwekker=4/SubType HR107=4/afgifte-lucht=3 + tapwater individueel/combi=10/Gaskeur-CW=3
(anker-codes); warmtepomp/koeling/biomassa/ventilatie-subsystemen NIET gegokt → sjabloon+flag (golden rule).
Volledig invoer-model (5 installaties/177 velden, ISSO+opnameformulier) = docs/installaties-invoermodel-ISSO.md.
Volledige review tegen het officiële NTA8800 W-opnameformulier (vabi/refs/opnameformulier_nta8800_v2025.txt) +
ISSO 82.1 -> masterplan. Doorgevoerd: dak-Hellingshoek-enum (3 hellend/6 plat), perimeter-guard (grond/kruip/kelder),
Gebouwhoogte uit opname, kozijn A/B/C, Qv10-gemeten, per-wand begrenzing via WAND-NAAMCONVENTIE (gevel=parent;
AVR/buurwand uit de schil), ventilatie.py = Nij Begun-vuistregels (0,7/verblijfsgebied + balans + overstroom), en
MagicPlan 'Qv10 gemeten?'-veld. EPA-PROBE LIVE GEVERIFIEERD (zie vabi/refs/grenstaan_mapping.md): thermische massa
0=Licht/1=Zwaar/2=Zeer zwaar, GrenstAan 0-9 (dropdown-index=code; basis AOR/AOS/ASGR->0), Daktype 0/1/2 — allemaal
gewired. Open: Gebouwtype/Ligging-enum (woningpositie) + installatie-enums (verwarming/koeling/tapwater/PV) +
PV-sjabloonknoop (lege ZonneEnergieList) -> aparte EPA-export-harvest; installatie-form-blokken.
MagicPlan-form "Schil & zone" uitgebreid + GEPUBLICEERD via de API (21 velden, VABI-getrouw:
Woningtype/Gevelhoogte/dak-velden toegevoegd). Objecten-generator nu volledig dossier-gestuurd:
Bouwjaar (bug gefixt: schreef de PROJECT- i.p.v. REKENZONE-Algemeen → Bouwjaar/Renovatie/Qv10 kwamen
nooit door), Gebruiksoppervlakte (Ag)+Verdiepingen+AantalBouwlagen, vloer-Perimeter, qv10 ISSO-correct
(alleen indien gemeten), en BEGRENZING per vlak (GrenstAan 0=Buitenlucht/2=Grond/3=Kruipruimte/4=AOR,
afgeleid uit echt sjabloon — zie vabi/refs/grenstaan_mapping.md). End-to-end bewezen op demo-
tussenwoning (out/demo_*). Nog 1 EPA-export nodig (computertoegang door Renze): GrenstAan 5/6 +
TypeBouwwijze 0/2 (Licht/Zeer zwaar); tot dan bevestigde codes auto, rest geflagd (golden rule).
CSV-parser leest nu ook Woningtype/Gevelhoogte/Renovatiejaar/Thermische massa uit de MagicPlan-
Statistics-CSV (CLI-arg overrulet); exacte MagicPlan-veldnamen in `docs/magicplan-form-spec.md`.
Thermische massa -> VABI: alleen Zwaar=1 live bevestigd, Licht/Zeer zwaar worden GEFLAGD (niet
gegokt — golden rule; codes 0/2 nog te verifiëren in EPA). MagicPlan-form-editor bevriest op de
Type-dropdown → resterende formvelden (Woningtype/Gevelhoogte/dak) handmatig toevoegen.
DOORBRAAK: alle 3 VABI-bibliotheken (Constructies/Objecten/Installaties) genereren uit het dossier
en IMPORTEREN FOUTLOOS in EPA 12.0.1 (live getest). Eén commando: `python vabi/generate_all.py
--dossier <dossier>`. Aanpak: kloon een echte VABI-export als sjabloon + harde validatie-poort
(codebook) -> nooit 'enum mismatch'. VABI's taal ontcijferd: 237 dropdowns/22 domeinen uit de
binary (vabi/extract_strings.py), codes uit echte exports (vabi/build_enum_catalog.py -> vabi_enums.json,
142/237 velden met codes). result_reader leest de Standaard-toets terug (energiebehoefte vs Standaard).
HYBRIDE MAGICPLAN-KETEN: opname -> API-geometrie + report-PDF -> dossier -> isolatieplan + ventilatie
+ foto + validatie + 3 VABI-bibliotheken. Zie docs/nijbegun_workflow.md + ../MagicPlan-VABI-veldenmapping.md.
Resterend: installatie-enums verder vullen (diverse exports harvesten); toekomstige-staat-generatie
(maatregelen in schil verwerken -> herrekenen Standaard); qv;10-na-maatregelen exacte waarde bevestigen;
gevel-m2 per orientatie verfijnen; MagicPlan forms/fields aanmaken (spec ligt klaar).

## (oude status) Essenhage-monitorketen — 52/52
monitor -> dossier -> engine -> isolatieplan + huidige staat + ventilatie + foto + validatie: OK.
GEBOUWD: installaties-blok (VABI-getrouw); VABI-generator (dossier->monitoring-XML, round-trip
getest incl. 25-delen monitor); parameter-sanity-check; lokaal dashboard (Flask); MagicPlan-
extractor (plan->dossier); prijsopbouw T7-T9 (blok per maatregel, cat 1/2/3 via subposten);
catalogus-API-client; meerwerk-subposten cat 2/3 automatisch voorgesteld uit catalogus (X-codes,
prijs ingevuld, hoeveelheid door adviseur).
GESYNCED met finale MagicPlan-form (juni 2026): gevel/vloer/dak als 'algemeen'-tags op projectniveau,
isolatie Ja/Nee/Onbekend (engine/fill accepteren beide vocab), nieuwe begrenzingen, dak-m2 via helling
(1/cos) of handmatig veld; extractor maakt nu ook vloer+dak-schildelen. LET OP: de losse schema-JSON
(../MagicPlan_Forms_Fields_schema_v0.3.json) is hierop NOG niet bijgewerkt - ../MagicPlan-Cloud-
invulinstructie.md is de actuele veldbron. Draai na elke wijziging: python tests/run_tests.py (52/52).

## TODO (prioriteit) — hier verdergaan
1. [JIJ] MagicPlan-form "Schil & zone": velden Woningtype + Gevelhoogte (m) + dak-velden handmatig
   toevoegen (zie `docs/magicplan-form-spec.md` voor EXACTE veldnamen). De web-editor bevriest op de
   Type-dropdown → automatisch toevoegen lukt niet; doe handmatig (evt. browser herstart). Type dak,
   Bouwjaar-klasse en Thermische massa staan al in de form. Tool-kant leest deze velden al.
2. [JIJ] VABI-generator: import 1x TESTEN in echte EPA-W; bij afwijzing veldnamen/namespaces bijstellen.
3. Catalogus: GEEN API nodig. catalog.json (333 maatregelen, V3_Q2_03062026) zit al in de tool en
   werkt. Nieuwe versie? -> xlsx opnieuw parsen: python catalog/parse_maatregelencatalogus.py "..xlsx".
   api_client.py = OPTIONEEL (alleen voor auto-refresh als Nij Begun ooit een sleutel geeft).
4. [WIJ] Meerwerk-hoeveelheden koppelen aan technische-haalbaarheid (nu prijs voorgesteld, hoeveelheid handmatig).
5. [WIJ] Monitor-parser installaties laten teruglezen (Samenvatting). Dashboard ook plan-JSON laten uploaden.
6. [LATER] Dashboard fase 2: multi-user/hosted -> Nij Begun tool-validatie (zie Constraints).

## Constraints / valkuilen
- Goedkeuringspoort: handmatig opstellen met Vabi + officieel template MAG; pas een
  gedistribueerde/zelfrekenende tool vereist Nij Begun-validatie (10 referentiewoningen).
- AVG: EU-opslag (OneDrive EU Data Boundary = ok), MFA, geen deling zonder toestemming.
- !! OneDrive corrumpeert .py-bestanden bij Write/Edit (afkapping/null-bytes door sync/linter).
  Werk in Claude Code in een NIET-gesynchroniseerde map (bv C:\dev\nijbegun-tool) of pauzeer
  OneDrive-sync tijdens bewerken. Verifieer na elke save:
    python -c "import ast,glob;[ast.parse(open(f,encoding='utf-8').read()) for f in glob.glob('**/*.py',recursive=True)]"
- De engine berekent de integrale Standaard niet; Vabi EPA-W bevestigt of het pakket de norm haalt.

## BRL 9500-W & ISSO 82.1 — proces buiten reken-scope (23-6-2026)
Volledige hoofdstuk-voor-hoofdstuk deep-dive tegen **ISSO 82.1 (7e druk, 12-01-2026)** + **BRL 9500-W
(aangewezen 29-05-2026)** — uitsluitend die twee als bron. Resultaat: docs/ISSO-82.1-opnameguide.md
(wat opnemen/voldoen/wanneer per hfdst), docs/BRL-9500W-proceshandleiding.md, docs/projectdossier-
checklist-bijlage3.md, docs/ISSO-BRL-gap-analyse.md (649 bevindingen: 41 gedekt/169 deels/313 ontbreekt/
126 nvt-Vabi), flowchart docs/proces-flowchart-a-tot-z.svg (route-split A/B). Eindoordeel: schil-opname
is sterk + golden-rule-conform; 3 gat-clusters = (1) installatie-breedte (koeling/warmtepomp/tapwater+PV-
uit-MagicPlan + enums harvesten), (2) opnameklasse basis(EP-W/B)/detail(EP-W/D) + gebouwtype expliciet,
(3) BRL-projectdossier/bewijslast-laag. BELANGRIJK voor toekomstige sessies: veel "ontbreekt" is BEWUST —
de tool is opname-/invoerhulp, niet de hele EPA; registratie EP-Online (3 mnd), projectdossier (Bijlage 3,
15 jaar), certificering/audits en representativiteit liggen bij de adviseur/het bedrijf (NIET tool-bugs).
Roadmap (geprioriteerd) staat in de gap-analyse. **Twee routes**: A energielabel (BRL 9500-W) vs B Nij Begun.

## Schaalbaar / multi-user
config.json bevat per-adviseur instellingen (naam/bedrijf/telefoon + woning/ventilatie-defaults +
paden). Meerdere gebruikers: ieder een eigen config.json; catalog.json centraal (later via API).
De tool is stateless per run -> eenvoudig te verpakken (.exe) of later achter een web-UI te zetten.
