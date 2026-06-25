# Gap-analyse — onze tool naast ISSO 82.1 (7e druk) + BRL 9500-W

Bron: deep-dive (multi-agent) per hoofdstuk van **ISSO 82.1 Energieprestatie woningen en woongebouwen, 7e druk**
(publicatiedatum 12-01-2026, 216 p.) en **BRL 9500-W** (NL-EPBD®-procescertificaat, aangewezen door de minister
op 29-05-2026, 72 p.). Strikt alleen die twee documenten als kennisbron. Per eis/opname-item is bepaald of onze
tool het dekt. Legenda: ✅ gedekt · 🟡 deels · 🔴 ontbreekt · ⚪ n.v.t. (Vabi rekent — golden rule).

> **Lees dit goed:** veel 🔴 is *bewust* — de tool is een **opname-/invoerhulp**, niet de hele EPA. De adviseur
> vult installatie-detail + onderbouwing aan in Vabi (de geattesteerde rekenkern). 🔴 betekent dus 'doet de adviseur
> nu nog handmatig', niet per se 'tool-bug'. De échte tool-acties staan in de roadmap onderaan.

## Eindoordeel

De tool dekt de ISSO 82.1 + BRL 9500-W opname-eisen sterk waar het de geometrische en bouwfysische kern-invoer betreft die binnen de golden rule valt: schil-geometrie (oppervlaktes 2 decimalen, hart-op-hart-toeslag, dak via helling, perimeter/begrenzing), de begrenzing-naamconventie (AVR/AOR/AOS/grond/kruip/kelder live-bevestigd), bouwjaar/renovatie/thermische massa/qv10-forfait en de gehele VABI-invoer-keten (3 bibliotheken importeren foutloos). Voor de rekenkern (Rc/U/bruggen/EP/TOjuli/forfaits) leunt de tool correct op Vabi en gokt geen enum-waarden — de golden rule is consequent toegepast (warmtepomp/koeling/biomassa/WKK/ventilatie-subsystemen worden geflagd i.p.v. geraden). De échte gaten zitten in drie clusters: (1) installatie-opname is half af — koeling wordt nergens uit MagicPlan gelezen of naar VABI gewired, en warmtepomp/tapwater-detail/aanvoertemperatuur/afgifte-enums ontbreken nog (harvest nodig); (2) opname-niveau- en gebouwtype-onderscheid (basis vs detail, eengezins vs appartement/woongebouw, gebouwtype-enum) zijn niet expliciet vastgelegd; (3) de BRL-projectdossier-/bewijslast-laag (herkomst per gegeven, bewijsbijlagen gekoppeld, opdrachtgever, opname/registratie-adviseur gesplitst, software-versie EPA, reproduceerbaarheid) is grotendeels afwezig. Onbekend-gevallen worden conservatief verwerkt (goed), maar de tool dwingt de detailopname-bewijslast niet af. Veel BRL-h5/h6/h7-eisen zijn terecht organisatorisch (certificaathouder/CI/kwaliteitshandboek) en buiten toolscope. Samengevat: opname-INVOER is productie-gereed voor de bestaande-eengezins-Nij-Begun-route; de installatie-breedte (m.n. koeling+warmtepomp) en de BRL-dossier-/bewijslaag zijn de te dichten gaten voor een volwaardige BRL 9500-W energielabel-route.

### Sterke punten
- ✅ Golden rule consequent toegepast: tool rekent NTA 8800 nooit zelf, levert alleen invoer en flagt onbekende enums i.p.v. ze te raden (warmtepomp/koeling/biomassa/WKK/ventilatie-subsystemen geflagd, geen 'verzonnen' codes)
- ✅ Schil-geometrie ISSO 82.1-conform en live in EPA geverifieerd: oppervlaktes op 2 decimalen, hart-op-hart-toeslag per woningtype (8.2), dak via helling/Pythagoras, begrenzing 0-9 (AVR/AOR/AOS/grond/kruip/kelder), orientatie 8-klassen, daktype 0/1/2, thermische massa 0/1/2
- ✅ Conservatieve verwerking van 'onbekend': forfaitair op bouwjaar (Rc, qv10), isolatie default 'Onbekend' -> Vabi rekent veilig
- ✅ qv10 ISSO-correct: alleen indien gemeten naar VABI, anders forfaitair (7.1.5) — niet-gemeten waarde wordt genegeerd/geflagd
- ✅ Volledige VABI-invoerketen werkt: 3 bibliotheken (Constructies/Objecten/Installaties) importeren foutloos in EPA 12; PV end-to-end geverifieerd
- ✅ Bouwjaar/renovatie/thermische massa/begrenzing worden uit MagicPlan-CSV gelezen en doorgezet
- ✅ BouwZo-formulier terecht overgeslagen: directe VABI-import is ISSO-conform (5.4.1)
- ✅ Herleidbaarheid naar gebouw (BAG-adres + per-project-opslag out/projects/<postcode_huisnr>) is geborgd

### De drie gat-clusters
- 🔴 KOELING volledig ongedekt in de keten: statistics_csv leest geen enkel koelingveld, installatie_generate wired geen KoelingBron/Opwekking/Distributie/Afgifte, en het Koeling-datamodel mist ~12 velden (bron/aandrijving/expansie-LBK/vermogen/distributiemedium/ontwerptemp/regeling). Spec ligt klaar in docs/installaties-invoermodel-ISSO.md
- 🔴 WARMTEPOMP-opname ontbreekt terwijl het de kernmaatregel van Nij Begun is: geen wp_aandrijving/wp_bron/COP-toets/bijstook-als-2e-opwekker; verwarming-opwekker is een singleton (geen lijst), dus hybride WP+ketel niet vastlegbaar
- 🔴 Installatie-enums grotendeels ongeharvest: type opwekinstallatie collectief/extern, afgifte radiatoren/vloer, aanvoertemperatuur (4 i.p.v. 12 klassen), ventilatie-subsysteem A-E codes — allemaal nog te harvesten uit EPA-exports
- 🔴 Opname-NIVEAU niet expliciet: geen veld basisopname(EP-W/B) vs detailopname(EP-W/D); objecten_generate leidt is_basis af uit de string 'detail' in type_advies (fragiel). BRL dwingt detail af bij Bbl/oplevering — niet afgedwongen
- 🔴 GEBOUWTYPE-enum ontbreekt: alleen 4 eengezins-posities; appartement/woongebouw (8 posities) niet opneembaar; VABI Gebouwtype/Ligging-code wordt geflagd i.p.v. gezet
- 🔴 BRL-PROJECTDOSSIER/bewijslast-laag afwezig: geen herkomst per gegeven, geen koppeling van bewijsbijlagen (foto/factuur/tekening/kwaliteitsverklaring) aan de invoer, geen opdrachtgever-blok, geen reproduceerbaarheid-export (4.2.7)
- 🔴 Tapwater-opname niet uit MagicPlan gelezen en uittapleidinglengtes keuken/badkamer niet naar VABI weggeschreven (velden bestaan maar zijn dood); voorraadvat-/direct-vat-/indirect-vat-blokken ontbreken
- 🔴 PV/zonneboiler-opname niet uit MagicPlan: orientatie/hellingshoek/oppervlak/beschaduwing komen nooit automatisch binnen; oost-west wordt geflagd i.p.v. gesplitst; bouwintegratie 'onbekend' niet naar 'niet geventileerd' geforfaiteerd; PV-belemmering wordt nooit naar VABI weggeschreven
- 🔴 Fossiele brandstof op perceel + leidingdoorvoeren door thermische schil (7.1.7/7.2.4): geen veld, beinvloeden EP-uitkomst
- 🔴 Adviseur-rol niet gesplitst (opnemend vs registrerend, max 2) en vakbekwaamheidsniveau/vakbekwaamheidsnummer niet expliciet; EPA-softwareversie niet vastgelegd (tool_versie != rekenkernversie)
- 🔴 Beloopbare zolder / knieschot-velden ontbreken terwijl ze direct bepalen of dak/zolder in de schil valt (geometrie-impact)
- 🔴 Isolatiedikte wordt niet uit MagicPlan gevuld noch op 10 mm afgerond; spouw_aanwezig/deur-isolatie/g-waarde/zonwering/beschaduwing per raam worden niet ingelezen

## Dekkingsoverzicht per hoofdstuk

| Hoofdstuk | ✅ | 🟡 | 🔴 | ⚪ | Kernsamenvatting |
|---|--:|--:|--:|--:|---|
| **isso-1** Inleiding + leeswijzer + opnameprotocol-ba | 1 | 4 | 4 | 4 | Dit hoofdstuk is uitsluitend de Inleiding (p18-19): wettelijk kader (EPBD/NTA8800/Omgevingsregeling/BRL 9500-W), de vier momenten van vaststelling, en kwaliteitsborging/vakbekwa... |
| **isso-2-5** Energieprestatie + Standaard omstandighede | 4 | 11 | 8 | 6 | Dit is een PROCEDURE-/eisenhoofdstuk (hoe opnemen, registreren, bewijzen) — geen bouwdeel-protocol. Daardoor zijn de meeste items GEEN rekenregel maar wel administratieve opname... |
| **isso-6** Gebouwbegrenzing en indeling (rekenzones,  | 3 | 15 | 25 | 13 | De tool dekt de KERN van hoofdstuk 6 die nodig is voor de gangbare eengezins-/Nij Begun-opname: per-vlak BEGRENZING (AVR/AOR/AOS/sterk geventileerd) via de wandnaam-conventie en... |
| **isso-7** Algemene gegevens (bouwjaar, woningtype, A | 3 | 6 | 8 | 2 | De tool dekt de kern-opnamegegevens van H7 goed waar die al in de bestaande MagicPlan->dossier->VABI-keten zitten: daktype, gemeten qv;10 (correct: alleen doorzetten indien echt... |
| **isso-8a** Bouwkundige gegevens I: gevels/ramen/deure | 10 | 12 | 11 | 5 | De tool dekt de KERN-opname van de thermische schil goed: per SchilDeel worden type, begrenzing, oriëntatie, oppervlakte, Rc/U/g, perimeter, hellingshoek, glastype, kozijnmateri... |
| **isso-8b** Bouwkundige gegevens II: dak/vloer/Rc/U/g/ | 4 | 7 | 12 | 12 | De tool dekt de KERN-opname van dichte constructies goed: isolatie-aanwezig, bouwjaar/renovatiejaar (forfaitaire Rc-route), kozijnmateriaal (A/B/C), glastype-basis, begrenzing (... |
| **isso-9** Ruimteverwarming (opwekker/distributie/afg | 1 | 18 | 25 | 5 | Hoofdstuk 9 is een OPNAME-hoofdstuk (welke invoer vastleggen, geen NTA8800-rekenregels), dus bijna alle items vergen tool-actie. De tool levert opname-invoer voor de VABI Instal... |
| **isso-10** Ruimtekoeling | 1 | 10 | 29 | 11 | Kort: het koeling-blok is in de tool het ZWAKST uitgewerkte installatiedeel. Het dossier-datamodel (core/dossier.py, klasse Koeling) dekt slechts ~7 opnamevelden (aanwezig/syste... |
| **isso-11** Ventilatie (systeem A-E, subsystemen, WTW, | 1 | 8 | 20 | 7 | De tool legt het ventilatiesysteem op HOOFDNIVEAU vast (systeem A-E, subsysteem_code, individueel/collectief, merk/type/jaar) en heeft in core/dossier.py losse booleans voor zel... |
| **isso-13** Warmtapwater (+ bevochtiging/ontvochtiging | 1 | 8 | 29 | 11 | H12 (bevochtiging/ontvochtiging) is voor woonfuncties n.v.t. — terecht geen tool-actie. H13 Warmtapwater is een ZWAAR ONDERBELICHTE module in de tool. De `Tapwater`-dataclass (c... |
| **isso-14-15** Verlichting + Gebouwgebonden energieproduc | 1 | 11 | 15 | 5 | H14 Verlichting is correct afgedekt (n.v.t. voor woonfuncties — tool voert het niet in). H15 daarentegen is het zwakst gedekte installatie-onderdeel van de tool. De PV-tak is he... |
| **isso-16-17** Beschaduwing + Representatieve woningen | 0 | 4 | 18 | 4 | Twee onderwerpen, beide grotendeels NIET gedekt door de tool. H16 (beschaduwing): de tool legt geen enkel beschaduwings-opnamegegeven vast. Er bestaat alleen een kale boolean Zo... |
| **brl-2-3** Onderwerp/doel certificatie + EISEN aan he | 2 | 4 | 9 | 5 | Dit hoofdstuk regelt de SCOPE/opname-keuze (basis- vs detailopname, afbakeningstabel Bbl/oplevering/bestaand, splitsing woon-/utiliteits-/logiesfunctie, recreatiewoningen) en de... |
| **brl-4-opname** Eisen aan de werkzaamheden: OPNAME (4.2.2) | 4 | 7 | 17 | 5 | De tool is een OPNAME-/invoertool: ze legt opname-GEGEVENS vast in core/dossier.py (uit MagicPlan via statistics_csv.py) en genereert 3 VABI-bibliotheken die in de geattesteerde... |
| **brl-4-rest** Berekening + Registratie + Levering + PROJ | 1 | 14 | 16 | 19 | Dit BRL-hoofdstuk is proces-, dossier- en bewijslast-kader, geen NTA8800-rekenwerk — de golden rule (Vabi rekent) raakt het nauwelijks; vrijwel alles is OF een opname-/dossierge... |
| **brl-5-7** Certificaathouder + interne/externe kwalit | 1 | 11 | 41 | 1 | Dit hoofdstuk gaat vrijwel volledig over de kwaliteitsbewaking van de CERTIFICAATHOUDER/organisatie en het CI-controleregime - geen inhoudelijke opnameregels per bouwdeel. Het o... |
| **brl-bijlagen** Bijlagen (representativiteit/projectdossie | 3 | 19 | 26 | 11 | Dit hoofdstuk is overwegend een certificatie-/controle- en dossier-vastleggingsprotocol, geen bouwkundig opname-/rekenprotocol. De tool levert sterk op de OPNAME-GEGEVENS die in... |

**Totaal:** ✅ 41 gedekt · 🟡 169 deels · 🔴 313 ontbreekt · ⚪ 126 n.v.t.-Vabi (649 bevindingen).

## Roadmap — concrete tool-acties (geprioriteerd)

Alleen echte opname-/proces-/dossier-gaten; rekenregels (⚪) staan hier niet (dat is Vabi's werk).


### 🔴 HOOG (15)
- **Koeling end-to-end implementeren: Koeling-dataclass uitbreiden conform docs/installaties-invoermodel-ISSO.md (r63-90; bron/aandrijving/expansie-LBK/vermogen_kw/distributiemedium/ontwerptemp/regeling/fancoil_bevestiging/opstelplaats/fabricagejaar/merk/type), koelingvelden in MagicPlan-form + statistics_csv parser toevoegen, en _wire_koeling()-tak in installatie_generate (bevestigde velden schrijven, ongeharveste enums op -1 + FLAG). Zonder dit komt koeling nooit uit de opname.**
  <br/><sub>📁 core/dossier.py (Koeling), magicplan/statistics_csv.py, vabi/installatie_generate.py · 📖 ISSO 82.1 H10 (10.2-10.5) + docs/installaties-invoermodel-ISSO.md</sub>
- **Warmtepomp-opname toevoegen: WP-blok aan Verwarming (aandrijving elektrisch/gas, wp_bron buitenlucht/afvoerlucht/bodem/grondwater/etc. + terugvalregels individueel->bodem/onbekend->individueel, voldoet_cop bool, additioneel_geplaatst). Verwarming-opwekker tot LIJST maken (3 VABI-slots) zodat hybride WP+ketel/bijstook als aparte opwekkers vastlegbaar zijn. WP/bron-enumcodes harvesten uit EPA.**
  <br/><sub>📁 core/dossier.py (Verwarming opwekker-lijst + WP-blok), vabi/installatie_generate.py · 📖 ISSO 82.1 9.3 / 9.3.1.3 / 9.3.6</sub>
- **Expliciet opnameniveau-veld toevoegen: opname.opnameklasse = 'basis'(EP-W/B)|'detail'(EP-W/D), los van Nij Begun type_advies; laat objecten_generate daarop sturen i.p.v. de string 'detail'. Validator-blocker: bij bouwfase Bbl/oplevering -> detail verplicht en EP-W/D-adviseur vereist.**
  <br/><sub>📁 core/dossier.py (Opname), vabi/objecten_generate.py, validator/validate.py · 📖 ISSO 82.1 5.2 + BRL 9500-W 3.1/4.2.2 (afbakeningstabel)</sub>
- **Gebouwtype-enum toevoegen (eengezinswoning/woongebouw/woning in woongebouw/vakantiewoning/woonboot/woonwagen) + appartements-woningpositie (8 posities); VABI Gebouwtype/Ligging-enumcodes harvesten uit EPA-export en wiren in objecten_generate (nu geflagd). Zonder dit kan een appartement/woongebouw niet correct opgenomen worden.**
  <br/><sub>📁 core/dossier.py (Identificatie), MagicPlan-form, vabi/objecten_generate.py · 📖 ISSO 82.1 7.1.1.1-7.1.1.3</sub>
- **Projectdossier-/Uitgangspunten-blok toevoegen: per kritisch invoergegeven herkomst (opdrachtgever/aannemer/eigen waarneming + ter plaatse gecontroleerd ja/nee) en een verwijzing naar bewijsbijlage (foto/factuur/tekening/kwaliteitsverklaring/DoP); exporteer dit zodat invoer reproduceerbaar/toetsbaar is.**
  <br/><sub>📁 core/dossier.py (nieuw Projectdossier/bewijsmateriaal-register), output-generatie · 📖 ISSO 82.1 5.7 + BRL 9500-W 4.2.7</sub>
- **BAG pand-ID + verblijfsobject-ID vullen: bag_pandid toevoegen aan Identificatie en bag_vboid+bag_pandid uit MagicPlan/handmatig/BAGviewer vullen (statistics_csv vult ze nu niet); registreren voor projectdossier/herleidbaarheid.**
  <br/><sub>📁 core/dossier.py (Identificatie), magicplan/statistics_csv.py · 📖 ISSO 82.1 5.5 + BRL 9500-W</sub>
- **Beloopbare-zolder- en knieschot-opname toevoegen: zolder_beloopbaar, zolder_min_hoogte_m, vaste_trap (vlizotrap telt niet), knieschot_aanwezig/geisoleerd + Rc — bepaalt of dak/zolder-vloer/ruimte-achter-knieschot in de thermische schil valt (directe geometrie-impact).**
  <br/><sub>📁 core/dossier.py + MagicPlan-form · 📖 ISSO 82.1 H6 (beloopbare zolder/knieschot)</sub>
- **Fossiele brandstof op perceel (gebouwgebonden) ja/nee + leidingdoorvoeren door thermische schil (aantal verticale leidingen/bouwlagen/geisoleerd, of forfait tabel 7.7) als opnamevelden toevoegen en de bijbehorende VABI-vlaggen zetten (enumcodes harvesten). Beide beinvloeden de EP-uitkomst.**
  <br/><sub>📁 core/dossier.py, MagicPlan-form, vabi/objecten_generate.py · 📖 ISSO 82.1 7.1.7 + 7.2.4</sub>
- **Isolatiedikte per schildeel uit MagicPlan inlezen naar SchilDeel.isolatiedikte_mm en afronden op 10 mm (tenzij handelsdikte-vlag); nageisoleerde-spouw forfaitaire dikte tabel 8.26 toepassen (40/70/100 mm op bouwjaar) bij onbekende spouwdikte. Relevant voor Nij Begun na-isolatie.**
  <br/><sub>📁 magicplan/statistics_csv.py, vabi/constructie_generate.py, MagicPlan-form · 📖 ISSO 82.1 8.7.2 (tabel 8.26) + dikte-opnameregels</sub>
- **Tapwater-opname activeren: tapwater-velden in MagicPlan-form + statistics_csv parser (type_installatie/toestel/gaskeur/cw/dwtw/lengtes/voorraadvat), en de bestaande maar dode velden lengte_keuken/lengte_badkamer naar VABI wegschrijven (LeidinglengteNaarKeuken/Badkamer, codes 0..7 harvesten). Voorraadvat-blok (aantal/volume/opstelplaats per vat) toevoegen.**
  <br/><sub>📁 core/dossier.py (Tapwater), magicplan/statistics_csv.py, vabi/installatie_generate.py · 📖 ISSO 82.1 13.2/13.4.1/13.6</sub>
- **PV/zonne-energie uit MagicPlan inlezen (orientatie/hellingshoek/oppervlak/aantal/bouwintegratie/beschaduwing) in statistics_csv; oost-west auto-splitsen in twee systemen; bouwintegratie 'onbekend' -> 'niet geventileerd' (15.4.3); en de PV-belemmering daadwerkelijk naar een VABI-beschaduwingsveld wegschrijven (wordt nu nooit doorgegeven).**
  <br/><sub>📁 magicplan/statistics_csv.py, vabi/installatie_generate.py (_wire_pv), MagicPlan-form · 📖 ISSO 82.1 15.4 + 16.3 stap 4</sub>
- **Aanvoertemperatuur-klassen uitbreiden van 4 naar 12 ISSO-klassen + afleidregel uit afgifte+opwekker (tabel 9.9); afgifte-codes radiatoren(0)/vloerverwarming(2) wiren en ventilator-gedreven/overig harvesten; verwarming-afgifte+regeling+opstelplaats+installatiejaar uit MagicPlan lezen.**
  <br/><sub>📁 core/dossier.py (Verwarming), magicplan/statistics_csv.py, vabi/installatie_generate.py · 📖 ISSO 82.1 9.3.4 / 9.5.1 / 9.5.3</sub>
- **Beschaduwing-opnameblok per zonontvangend vlak (raam/PV/collector) toevoegen: type beschaduwing (belemmering/dakrand/overstek/zijbelemmering) + de relevante maten (h_b, b_b+zijde, h_o, h_dakrand/l_dakrand); vervang de kale boolean ZonneEnergieSysteem.belemmering. Minimaal 'beschaduwing aanwezig + situatie' zodat VABI de juiste tabel-16.1-situatie krijgt.**
  <br/><sub>📁 core/dossier.py (SchilDeel + ZonneEnergieSysteem), MagicPlan-form, magicplan/statistics_csv.py · 📖 ISSO 82.1 H16 (16.1-16.3)</sub>
- **Opdrachtgever-blok + adviseur-rollen splitsen: Opdrachtgever-dataclass (naam/rol/contact) en Adviseur splitsen in opnemend + registrerend (elk naam + expliciet vakbekwaamheidsnummer EP-W/B of EP-W/D, max 2); validator borgt aanwezigheid voor 'sluitend' dossier.**
  <br/><sub>📁 core/dossier.py (Opdrachtgever + Adviseur), validator/validate.py · 📖 BRL 9500-W 4.2.5 / 6.7.3</sub>
- **EPA-softwareversie vastleggen + EPA-computerdatabestand archiveren per project: veld vabi_epa_versie aan Meta (tool_versie is NIET de rekenkernversie) en de gegenereerde VABI-XML's/EPA-export samen met dossier bewaren in out/projects voor reproduceerbaarheid en 15-jaar-retentie.**
  <br/><sub>📁 core/dossier.py (Meta), dashboard/app.py / out/projects · 📖 BRL 9500-W 6.7.4 / 7.1.4 / 4.2.4</sub>

### 🟡 MIDDEL (21)
- **Foto-checklist uitbreiden van Nij-Begun-maatregelen (V1-V6) naar BRL-bewijsfoto's: per installatie (opwekker/typeplaatje/leidingisolatie/buiten-unit/afgifte) + overzicht+detail per schildeel + isolatiedikte-met-duimstok bij rc_bron=Opgemeten; en datum/herkomst aan Foto toevoegen + valideren fotodatum<=opnamedatum.**
  <br/><sub>📁 foto/checklist.py, core/dossier.py (Foto), validator/validate.py · 📖 ISSO 82.1 5.4/9.1.4/10.1.4/13.1.4/15.1.4 + BRL 4.2.7</sub>
- **Bewijslast per schildeel/installatie i.p.v. één woning-brede Opname.bewijslast: koppel kwaliteitsverklaring-vlag aan merk+type+bewijsbijlage (validator: kwaliteitsverklaring=True -> merk+type+bewijs verplicht) en voeg BCRG-verklaringnummer + geldigheidsstatus toe.**
  <br/><sub>📁 core/dossier.py (SchilDeel + installaties), validator/validate.py · 📖 ISSO 82.1 5.1.1/5.2.1 + BRL 9500-W 4.2.7</sub>
- **Onderbouwingsvelden toevoegen voor afwijkende/forfaitaire/inklap-keuzes: per afwijkende rekenwaarde (bron/analyse), AVR-begrenzing (waarom AOR als AVR, >=15C-onderbouwing), schematisering/rekenzone-keuze, en 'inklappen ja/nee + reden'; exporteer in een gebouwdossier-rapport.**
  <br/><sub>📁 core/dossier.py (SchilDeel.opmerkingen + nieuw onderbouwing-blok), output · 📖 ISSO 82.1 5.3/6.3.4/6.4 + BRL 9500-W 4.2.7</sub>
- **Zonwering + overstek/belemmering per raam als SchilDeel-velden toevoegen (vaste/beweegbare zonwering type+kleur+regeling; overstek/belemmering) + g-waarde glas en deur-isolatie uit MagicPlan inlezen; relevant voor koelbehoefte/oververhitting/beschaduwing.**
  <br/><sub>📁 core/dossier.py (SchilDeel), magicplan/statistics_csv.py, MagicPlan-form · 📖 ISSO 82.1 8.8/8.9 + Bouwkundige gegevens II (zonwering/g/deur)</sub>
- **Deur <65% glas splitsen in apart raam- (Araam=H*B) en deurdeel i.p.v. één deur; nu gaat het glasdeel van een deur <65% verloren als raam-oppervlak.**
  <br/><sub>📁 magicplan/statistics_csv.py · 📖 ISSO 82.1 8.2.2 / 8.7.2.4</sub>
- **Groeperingssleutel voor gevels/ramen uitbreiden: niet alleen (orientatie,begrenzing) maar ook Rc/hellingshoek/g/zonwering, zodat constructies met verschillende isolatie/g niet onterecht worden samengevoegd (8.2).**
  <br/><sub>📁 magicplan/statistics_csv.py (gevel_per) · 📖 ISSO 82.1 8.2</sub>
- **Perimeter-fallback 0,01 m implementeren voor vloeren aan grond/kruip/kelder zonder perimeter, en H1 (maaiveldhoogte) + gevel-splitsing grond/buitenlucht toevoegen voor souterrain/kelder/talud (nu volledig handmatig in Vabi).**
  <br/><sub>📁 vabi/objecten_generate.py, core/dossier.py (SchilDeel.h1_maaiveld_m) · 📖 ISSO 82.1 8.2.4 / 8.3 / 8.4</sub>
- **Klimatiseringszone-laag + per-rekenzone-koppeling van verwarming/koeling/ventilatie/tapwater (of expliciet documenteren dat de tool 1 klimatiseringszone aanneemt en multi-zone handmatig in Vabi); Ventilatie van singleton naar lijst bij verschillend WTW-rendement.**
  <br/><sub>📁 core/dossier.py (zone-model), vabi/installatie_generate.py · 📖 ISSO 82.1 6.5 / 9.2 / 11.1.1-11.2 / 13.2</sub>
- **Ag- en Als-plausibiliteitscheck toevoegen in sanity.py/validate.py: waarschuw bij Ag-afwijking >grootste van 3%/2 m2 (som ruimtes vs Total living area) en lever een Als-controlewaarde (som schiloppervlak) met flag; documenteer dat Vabi de norm bevestigt.**
  <br/><sub>📁 vabi/sanity.py, validator/validate.py · 📖 BRL 9500-W 4.2.2 (Ag/Als-marges)</sub>
- **Gebouwhoogte expliciteren als maaiveld->hoogste punt (i.p.v. 'gevelhoogte' met som-verdiepingshoogte-fallback) en bouwjaar uit BAG als exact jaar i.p.v. jaarklasse; renovatiejaar pas accepteren bij bewijslast!=Geen (beslisschema 7.3); qv10-meetrapport-metadata (datum/NEN 2686/uitvoerder) + check <=1 jaar.**
  <br/><sub>📁 core/dossier.py (Opname/Identificatie), magicplan/statistics_csv.py, validator/validate.py · 📖 ISSO 82.1 7.1.3/7.1.4/7.1.5/7.1.6</sub>
- **Garage/overige-ruimte-classificatie-invoer vastleggen (beslisschema afb. 6.1-6.3): garage-ventilatieopening_m2/deur_bxh/isolatie_pct/Rc, kelder h1/h2/maaiveld, opening>=0,2m2, open verbinding — als opname-checklist zodat de adviseur-keuze AOR/sterk-geventileerd/binnen-zone reproduceerbaar is (tool rekent niet, maar legt de invoer vast).**
  <br/><sub>📁 core/dossier.py + MagicPlan-form/opname-checklist · 📖 ISSO 82.1 H6 (garage/kelder/overige ruimten)</sub>
- **Registratiedatum + opname-context-velden toevoegen (aanleiding: Omgevingsvergunning|Melding Wkb|Oplevering|Verkoop/verhuur; bouwfase: Bbl-toets|Oplevering|Bestaand; bouwstatus nieuwbouw/bestaand) en bij preventieve Bbl-toets de regel opnamedatum=registratiedatum borgen; doel_rapport voor controle-regime.**
  <br/><sub>📁 core/dossier.py (Opname), run.py/dashboard · 📖 ISSO 82.1 inleiding/5.5 + BRL 9500-W 4.2.5/6.7.3</sub>
- **Ventilatie-detail uitbreiden + uit MagicPlan vullen: zelfregelend/tijdsturing/CO2-meting/CO2-sturing/zonering/WTW-type/recirculatie/bypass + geinstalleerd_debiet_m3h (let op: ventilatie.py-debiet 0,7 dm3/s.m2 is een Nij Begun-balanshulp, NIET de ISSO-opnamewaarde); ventilator-blok (Pnom/fabricagejaar) en LBK-blok voor D/E. Ventilatie-subsysteem-enums A-E harvesten uit EPA.**
  <br/><sub>📁 core/dossier.py (Ventilatie), magicplan/statistics_csv.py, vabi/installatie_generate.py · 📖 ISSO 82.1 11.3-11.7</sub>
- **Tapwater-detailblokken toevoegen: direct/indirect-vat-onderscheid + afleverset (aanvoertemp-klasse, onbekend=60C+ met validatie <60C niet voor tapwater), DWTW-detail (type/aantal douches/aansluitwijze), CW-klasse-codes + warmtepompboiler/elektro-subtypes harvesten; fallback 'geen tapwatersysteem -> elektrisch doorstroomtoestel'.**
  <br/><sub>📁 core/dossier.py (Tapwater), vabi/installatie_generate.py · 📖 ISSO 82.1 13.3 / 13.3.4 / 13.7</sub>
- **Distributie-detail verwarming/koeling vastleggen: distributiemedium wiren (Water=1, Geen-code harvesten), een-/tweepijps, waterzijdig inregelen (default onbekend->niet), leidingen door onverwarmde ruimte (lengte/omgeving/isolatie+isolatiejaar, default onbekend->bouwjaar), pompen forfaitair.**
  <br/><sub>📁 core/dossier.py (Verwarming/Koeling distributie), vabi/installatie_generate.py · 📖 ISSO 82.1 9.4 / 10.4</sub>
- **Zonneboiler/PVT- en thuisaccu-opname toevoegen (nu volledig afwezig): collectortype + voorraadvat (volume/back-up/aansluitverlies) + naverwarming + bediende_ag; elektrische/thermische opslagcapaciteit_kwh met voorwaarde 'alleen mee bij geldige PV + gebouwgebonden + fysieke verbinding'. PV/wind-toekenning aan woning (postcoderoos/off-grid afvangen). Zonneboiler-enums harvesten.**
  <br/><sub>📁 core/dossier.py (ZonneEnergie + Voorraadvat), vabi/installatie_generate.py · 📖 ISSO 82.1 15.2 / 15.3 / 15.5</sub>
- **BRL-projectdossier-compleetheidscheck (analoog aan validate.py KWACO) tegen Bijlage 3: opdrachtgever, tekeningen/plattegrond-verwijzing, productinfo, herkomst, overzicht+detail-foto's, uitvoerfile, software-versie; + exporteerbaar projectenregister (CSV met postcode/huisnr/opdrachtgever/subdeelgebied/doel/data/certificaatnummer) voor CI-inzage.**
  <br/><sub>📁 validator/validate.py (nieuwe BRL-check), dashboard/app.py · 📖 BRL 9500-W 4.2.7 / 6.7.3 / 7.2.2</sub>
- **Detailopname-bewijslast afdwingen: bij opnameklasse=detail rc_bron='Opgemeten dikte'/'Kwaliteitsverklaring'/DoP verplicht en forfaitaire Rc/U flaggen als niet-toegestaan; DoP-velden (identificatiecode/AVCP-klasse/hEN/lambda-U/fabrikant) per constructie waar relevant.**
  <br/><sub>📁 core/dossier.py (SchilDeel DoP), validator/validate.py, vabi/constructie_generate.py · 📖 ISSO 82.1 5.2.1/8.7.1 + BRL 9500-W 4.2.7</sub>
- **Validator uitbreiden zodat 'onbekend' bij goed-waarneembare gegevens (oppervlaktes/glas/kozijn/orientatie) blokkerend wordt voor de label-route (nu alleen WARN op isolatiestatus/begrenzing); en kennisgevingsbrief aan opdrachtgever (EP-Online/projectdossier-recht/CI-controle/klachtenprocedure) als optionele output genereren.**
  <br/><sub>📁 validator/validate.py, isolatieplan/output · 📖 BRL 9500-W 4.2.2 (kritieke afwijkingen) / 4.2.2 informeren opdrachtgever</sub>
- **Constructie-keuze het renovatiejaar laten respecteren per schildeel (nu alleen identificatie.bouwjaar) wanneer bewijs aanwezig is; renovatiejaar-onbekend -> eerste jaar hogere jaarklasse.**
  <br/><sub>📁 vabi/constructie_generate.py · 📖 ISSO 82.1 7.1.4 / 8.7.2.1</sub>
- **Productcode + fabricagejaar-fallback (fabricagejaar->installatiejaar->bouwjaar) per installatie toevoegen en in installatie_generate toepassen (bepaalt forfaitair rendement); merk/type/installatiejaar/opstelplaats uit MagicPlan lezen.**
  <br/><sub>📁 core/dossier.py (installaties), magicplan/statistics_csv.py, vabi/installatie_generate.py · 📖 ISSO 82.1 5.4 / 9.3.3 / 9.3.5</sub>

### ⚪ LAAG (5)
- **Lichte administratieve velden toevoegen: BRL 9500-W-certificaatnummer + onafhankelijkheid-vlag aan Adviseur, zelfstandige_wooneenheid + aantal_woonfuncties + energieprestatieplichtig_deel aan Opname/Identificatie, gebruiksfunctie-splitsing woon/utiliteit/logies-drempel (<=helft Ag EN <=50m2). Meeste eengezins-scope dus low-impact, maar leg de keuze vast.**
  <br/><sub>📁 core/dossier.py (Adviseur/Opname/Identificatie) · 📖 ISSO 82.1 inleiding/6.1 + BRL 9500-W 3.x</sub>
- **Kruipruimte/vloer-detailvelden: kruipruimtebodem geisoleerd ja/nee (tabel 8.13), thermokussens (Rc 1,95), afschotisolatie min-dikte, riet/dakkoepel/paneel-subtypes — als opnamevelden of expliciet als handmatige Vabi-invoer documenteren (lage frequentie).**
  <br/><sub>📁 core/dossier.py (SchilDeel-subtypes), MagicPlan-form · 📖 ISSO 82.1 8.2.2/8.2.4 + Bouwkundige gegevens II</sub>
- **Oververhitting-blok (actieve_koeling/factor_raamopeningen/zonwering_dekking/gto_uitkomst/koellastberekening) toevoegen voor de label/Bbl-route; voor bestaande Nij-Begun-woningen meestal n.v.t. maar de checks moeten in het projectdossier.**
  <br/><sub>📁 core/dossier.py (oververhitting), validator/validate.py · 📖 ISSO 82.1 6.6/6.7</sub>
- **Herlabel-/representativiteitsmodule bewust buiten scope markeren in CLAUDE.md (of later bouwen): 24-mnd-termijn/clusters, deelverzameling+steekproef (tabel 17.2, deterministisch implementeerbaar), gelijkheidsdrempels — nu volledig handmatig door de adviseur; documenteer de beperking.**
  <br/><sub>📁 CLAUDE.md / toekomstige module · 📖 ISSO 82.1 H17 + BRL 9500-W 4.3 / 5.6</sub>
- **Diverse lokale-installatie-detailvelden waar nu geen veld bestaat maar wel als 'onbekend' invoerbaar moet zijn (waakvlam-aantal, lokale-kachel-afvoer, gas/olie-keuze, WKK Pel/HRe, elektrische opwekkers-aantal, biomassa-kacheltype, externe warmtelevering aanvoertemp-klasse) toevoegen + bijbehorende enums harvesten; tot dan correct geflagd (golden rule).**
  <br/><sub>📁 core/dossier.py (Verwarming/Tapwater installatie-detail), vabi/installatie_generate.py · 📖 ISSO 82.1 9.3.1.1-9.3.1.7 / 13.3.x</sub>