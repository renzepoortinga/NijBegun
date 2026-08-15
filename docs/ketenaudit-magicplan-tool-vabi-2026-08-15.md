# Ketenaudit MagicPlan → Nij Begun-tool → Vabi EPA-W

**Peildatum:** 15 augustus 2026  
**Rol:** IT-manager / ketenauditor  
**Gouden regel:** Vabi EPA-W blijft de geattesteerde NTA 8800-rekenkern. Deze audit beoordeelt opname, gegevensoverdracht, workflow en controleerbaarheid; de tool rekent het label niet zelf.

## Managementsamenvatting

De technische basis is sterk, maar de huidige keten is nog niet geschikt voor het doelbeeld “goed ingevuld MagicPlan-project inladen en alleen het dak nog beoordelen”. De parser, het canonieke dossier en de drie Vabi-bibliotheken zijn breed getest (790/790 checks groen), maar de echte adviseursroute heeft nog vier systeemproblemen:

1. **Dakmigratie kan dubbele vlakken achterlaten.** Het live Essenhage-dossier toont één oud generiek dak van 55,56 m² én twee nieuw aangemaakte schuine dakvlakken van elk 28,71 m². De webapp meldt tegelijk “TYPE DAK ontbreekt”. Zonder expliciete vervang-/migratiestap kan dit tot dubbele dakoppervlakte leiden.
2. **Kwaliteitsverklaring is een harde ketenstop.** Eén vloer met `Rc-bron = Kwaliteitsverklaring` blokkeert alle drie Vabi-exportbibliotheken. Dat is veilig, maar niet gebruiksvriendelijk: de adviseur krijgt geen begeleide BCRG-afhandeling en kan de rest van de overdracht niet alvast uitvoeren.
3. **De “één vocabulaire”-poort is nog gedeeltelijk.** Glas, begrenzing en woningtype zijn afgedekt. Veel conditionele installatie-dropdowns hebben volgens de eigen kennisbank nog niet-geharveste Vabi-codes. Daar mag de tool terecht niet gokken, maar de resterende handmatige invoer is daardoor groter dan het doelbeeld.
4. **Documentatie en live waarheid lopen opnieuw uiteen.** `magicplan-forms-live.md` noemt zichzelf de enige waarheid, maar draagt nog de datum 23-7 en beschrijft “DAK verwijderd”; `magicplan-velden-audit.md` meldt dat op 27-7 een dak-isolatiesectie terug live is gezet. Ook `additions.json` bevat oudere defaultaannames. De kennisbank is inhoudelijk rijk, maar mist één gegenereerde veldmatrix die live formulier, parser, canoniek veld, webappkeuze en Vabi-bestemming tegelijk bewaakt.

Advies: maak eerst dakvervanging en bron-/versiebeheer sluitend. Bouw daarna de “one-click intake”: MagicPlan-project selecteren, importeren in een nieuw/gekoppeld dossier, afwijkingen tonen en alleen de echt noodzakelijke Vabi-handacties overhouden. Volledig “alleen het dak” is niet voor elk labeldossier haalbaar; installaties, BCRG-bewijs, zonegrenzen en uitzonderlijke geometrie moeten aantoonbaar blijven.

## Onderzoeksopzet en bewijs

- Projectcontract, `docs/STATE.md`, operationeel geheugen, actieve/afgeronde taken en rolcontracten gelezen.
- Alle documenten in `docs/` op functie en onderlinge verwijzingen geïnventariseerd; normatieve kern en bestaande audits inhoudelijk vergeleken.
- Drie lokale voorbeeldplannen tekstueel en op paginastructuur onderzocht:
  - bouwjaar 1970: 22 pagina’s, bijlage 1 t/m 7;
  - bouwjaar 1993: 26 pagina’s, hoofdplan met vier bijlagen plus een afzonderlijk adviesdeel met eigen bijlage 1 t/m 3;
  - bouwjaar 2002: 20 pagina’s, bijlage 1 t/m 6 en geen detailtekeningen.
- In de ingelogde Chrome-sessie live gekeken naar MagicPlan, de bestaande Essenhage-kopie en de productie-webapp.
- `python tests/run_tests.py`: **790 geslaagd, 0 gefaald**.
- Offline Vabi-export gegenereerd uit `tests/fixtures/monitor_voorbeeld.xml`: drie XML-bibliotheken plus `IMPORTEREN.txt` ontstaan. De export geeft terecht luide waarschuwingen bij ontbrekende perimeter, gebouwhoogte, woningtype, thermische massa en installaties.
- Een daadwerkelijke import in de Windows-desktopapp Vabi kon in deze sessie niet bestuurbaar worden uitgevoerd: de beschikbare browserbesturing bedient Chrome, niet native Windows-vensters. Eerdere projectstatus meldt wel foutloze import in EPA 12.0.1; dat is geen vervanging voor een nieuwe live herhaling van deze audit.

## Kenniskaart

| Laag | Leidende bronnen | Beoordeling |
|---|---|---|
| Architectuur en status | `AGENTS.md`, `CLAUDE.md`, `docs/STATE.md`, `docs/architecture.md` | Gouden regel en modulegrenzen duidelijk. `CLAUDE.md` bevat veel historische status en is deels dubbel met actuele docs. |
| Norm en proces | NTA 8800:2025+C1:2026, ISSO 82.1 7e druk, BRL 9500-W:2026, proceshandleidingen | Versies zijn op 12-8 geaudit. Gelicentieerde bronnen mogen niet ongemerkt als algemene AI-bron worden gedeeld. |
| Opname | `OPNAME-WERKINSTRUCTIE.md`, `ISSO-82.1-opnameguide.md`, MagicPlan how-to/inmeetgids/forms | Inhoud is volwassen, maar de adviseur moet tussen meerdere documenten springen. Formulierversie is niet machineleesbaar aan een dossier gekoppeld. |
| Mapping | `magicplan-velden-audit.md`, `aannames-audit*.md`, `installaties-invoermodel-ISSO.md`, Vabi refs | Sterke inhoudelijke audits. Geen compleet, automatisch vergelijkbaar veldregister over alle vijf lagen. |
| Uitvoer en kwaliteit | Nij Begun-eisen, voorbeeldplannen, validator, beslislogica, foto/ventilatie | Outputinhoud is sterk uitgebreid. Voorbeeldplannen blijken verschillende generaties/sjablonen te zijn; “gold standard” moet versiegebonden worden. |
| Historie | build logs, statusnacht, overdrachtdocumenten | Waardevol als bewijs, maar niet leidend. Zoekresultaten kunnen oude conclusies naast nieuwe tonen. |

### Documentatierisico’s

- De live-formwaarheid van 23-7 is door wijzigingen van 27-7 achterhaald zonder dat titel/datum en inventaris volledig zijn bijgewerkt.
- Het aantal velden (174) en de groepsinhoud uit de audit zijn momentopnamen. Zonder live fingerprint weet een dossier niet met welke formulierversie het is opgenomen.
- In `installaties-invoermodel-ISSO.md` staan nog expliciete “TE HARVESTEN”-codes. Dit zijn geen bugs zolang de generator ze niet gokt, maar wel grenzen aan automatisering.
- Oude lokale Essenhage-uitvoer en het lokale dossier zijn veel leger/ouder dan het live productieproject. `out/` is dossieropslag, geen betrouwbare centrale waarheid tussen machines/omgevingen.

## Dropdown- en veldbeoordeling

### Wat aantoonbaar klopt

- Woningtype: tien opties in MagicPlan/webapp; leeg wordt niet stil als grondgebonden behandeld.
- Oriëntatie: acht windrichtingen plus leeg; gevelrichtingen worden afgeleid en als controlepunt getoond.
- Begrenzing: Buitenlucht, Grond, Kruipruimte, AOR, AOS, AVR, ASGR/sterk geventileerd, Water en onverwarmde kelder worden genormaliseerd.
- Glas: negen canonieke keuzes inclusief HR, HR+, HR++, TripleHR en vacuümglas; onbekende waarden verdwijnen niet meer stil.
- Kozijnmateriaal: de webapp kent drie NTA-klassen. De parser flagt “afwijkend = ja” zonder materiaal in plaats van gunstig hout/kunststof te kiezen.
- Per-wand- en per-ruimteoverrides winnen van naamtoken en projectstandaard.
- Kwaliteitsverklaring wordt niet als forfaitaire constructie geëxporteerd; de preflight blokkeert vóórdat gedeeltelijke bestanden worden geschreven.

### Wat beter kan

| Bevinding | Impact | Verbetering |
|---|---|---|
| MagicPlan-vraag “kozijn afwijkend?” kan het werkelijke metaaltype niet altijd leveren | Ufr 3,8 versus 7,0 blijft handmatig | Maak materiaal een directe dropdown op elk relevant raam/deur, met “Onbekend” als fout-/controlewaarde. |
| Installatiekeuzes zijn omvangrijk en conditioneel; diverse Vabi-codes zijn niet exportbevestigd | Adviseur moet meer in Vabi nalopen; verkeerd sjabloon kan blijven staan | Harvest per conditionele tak uit een echte Vabi-export; alleen bevestigde codes automatisch schrijven. |
| Eerste/defaultoptie in MagicPlan kan als betekenisvolle invoer eindigen | Stille “default = waarneming” | Gebruik expliciet “Niet opgenomen” als eerste keuze voor waarneembare gegevens; maak kritieke vragen conditioneel verplicht. |
| Eén statische woordenlijsttest dekt vooral glas en begrenzing | Nieuwe dropdowndrift kan buiten tests blijven | Genereer één mappingmanifest met live label/opties, parsernormalisatie, canonieke enum, webappopties en Vabi-code/bewijsstatus. |
| Formulierversie ontbreekt in dossiermetadata | Oude en nieuwe exports zijn niet betrouwbaar te migreren | Sla form fingerprint, exportdatum en MagicPlan-project-id op; toon migratiewaarschuwing bij mismatch. |

## Import/export en stressresultaten

### MagicPlan → tool

- De live webapp registreert importhistorie met bestand, tijd en aantal vlakken; Essenhage toont 21 geïmporteerde vlakken.
- Het bewerkte dossier toont daarna 23 vlakken door webapp-daktoevoegingen. De oude generieke dakregel bleef aanwezig. De UI maakt niet duidelijk dat de nieuwe dakwizard het oude dak moet **vervangen** in plaats van aanvullen.
- De tool detecteert wel dat het hoofddak niet de volledige begane-grondfootprint overspant en vermoedt terecht een eigen aanbouwdak. Dat is goede expertcontrole, maar er is nog geen begeleide oplossing.
- Re-import moet expliciet getest worden op behoud van handmatige dakcorrecties, foto’s, maatregelen en Vabi-resultaten. De huidige tests bewijzen parsing, niet de volledige merge-semantiek van een reeds bewerkt productiedossier.

### Tool → Vabi

- De kwaliteitsverklaring-preflight draait vóór schrijven en laat bij die blokkade geen gedeeltelijke set achter. De algemene generatie is echter **niet atomisch**: de drie writers schrijven sequentieel rechtstreeks naar eindpaden. Een fout in een latere writer kan dus een gedeeltelijke of met oude bestanden gemengde set achterlaten.
- De Objectenexport kan geometrische conflicten luid melden, bijvoorbeeld deelvlakken groter dan het hoofdvlak; dat is beter dan stil corrigeren.
- De adviseur moet vóór import Vabi-Algemeen correct instellen (woning, bestaande bouw, basisopname). Dit blijft een foutgevoelige handmatige preconditie.
- Hart-op-harttoeslag, onzekere gevelplaatsing, ontbrekende perimeter/hoogte/massa en sjablooninstallaties blijven controlepunten. Een waarschuwing is geen automatisering.
- Kwaliteitsverklaring blokkeert de hele export. Functioneel veilig, operationeel stroef.

### Vabi → tool

- Monitoring-/resultaatimport en Standaard-toets hebben fixtures en ketentests.
- De UI vraagt een XML-export van huidige en toekomstige situatie. Bestandsidentiteit, Vabi-versie en match met het dossier moeten als harde provenance-controle worden opgeslagen en getoond; nu is “verkeerd bestand bij verkeerd adres” vooral een procesrisico.

## Voorbeeldplannen versus onze werkwijze

Er is niet één uniforme voorbeeldstructuur:

| Plan | Structuur | Les voor de tool |
|---|---|---|
| 1970, 22 p. | Bijlage 1-7, inclusief maatregelenbeeld, ventilatieplan en detailtekeningen | Beste inhoudelijke referentie voor een uitgebreid plan. |
| 1993, 26 p. | Vier bijlagen in hoofdplan plus apart adviesdeel met eigen disclaimer/Standaard/begrippenlijst | Waarschijnlijk andere generatie of samengevoegde rapportage; niet blind als layoutsjabloon gebruiken. |
| 2002, 20 p. | Bijlage 1-6, geen detailtekeningen | Detailbijlage is kennelijk situatie-/maatregelafhankelijk, niet altijd verplicht als lege sectie. |

De huidige generator kan bijlage 4-7 additief toevoegen, maar oudere bestanden in `out/` tonen nog alleen bijlage 1-3. Productie-uitvoer moet bij regeneratie versie, gebruikte template en conditioneel opgenomen bijlagen vastleggen. Bijlage 5 (woningbeeld met maatregelen/koudebruggen) en de echte detailtekeningen blijven de grootste kwaliteitsverschillen met het 1970-voorbeeld; tekstplaceholders en alleen psi-lijsten bereiken hetzelfde communicatieniveau niet.

## Doelarchitectuur: minimale adviseurshandelingen

1. **Selecteer MagicPlan-project**, niet eerst adres en daarna handmatig CSV zoeken. De tool haalt of ontvangt Statistics-CSV, rapport en geometrie als één importpakket.
2. **Bind identiteit:** BAG/adres + MagicPlan project-id + form fingerprint + exporttijd. Geen stille import in een dossier met afwijkende identiteit.
3. **Normaliseer en valideer:** één mappingmanifest; kritieke ontbrekende waarneembare gegevens terug als korte taaklijst.
4. **Dakwerkbank:** toont footprint, ontbrekende aanbouwdaken en bestaande legacyvlakken. “Vervang oud dak” is een expliciete, atomische actie.
5. **Uitzonderingenwerkbank:** BCRG/kwaliteitsverklaring, multi-zone, thermische massa, afwijkende kozijnen en onmogelijke geometrie; geen generieke lijst van 22 losse teksten.
6. **Vabi-pakket:** controleer Algemeen-profiel, schrijf alleen bewezen enums en lever een korte importvolgorde met rood/oranje/groen status.
7. **Resultaatretour:** accepteer alleen een Vabi-export die bij adres/dossier/versie past; toon verschillen huidige/na zonder NTA zelf te rekenen.
8. **Planopbouw:** kies templateprofiel, neem bijlagen conditioneel op, render en voer visuele QA uit vóór opleveren.

## Prioriteiten

### P0 — vóór verder opschalen

- Voorkom dubbele legacy- en wizarddakvlakken; voeg migratie- en regressietest toe.
- Registreer form-/bronversies en dossieridentiteit bij import/export.
- Maak de live-formdocumentatie weer werkelijk leidend of genereer haar uit het mappingmanifest.
- Publiceer Vabi-exportsets atomisch via een tijdelijke map en vervang de eindset pas nadat alle writers en validaties slagen.

### P1 — grootste tijdwinst

- Projectselectie/éénknopsimport met veilige merge en duidelijke diff.
- Begeleide kwaliteitsverklaring/BCRG-route vóór Vabi-export.
- Structurele foutlijst groeperen tot vijf adviseurstaken: identiteit, schil, dak, installaties, bewijs.
- Harvest de veelgebruikte installatiepaden (HR-ketel, warmtepomp, ventilatie A-E, tapwater, PV) volledig en exportbevestigd.

### P2 — plan- en kwaliteitsniveau

- Bijlage 5 automatisch uit het gebouwoverzicht met gekozen maatregelen en koudebrugmarkeringen.
- Echte detailtekeningen conditioneel opnemen; geen lege bijlage 7.
- Template-/voorbeeldversie expliciet beheren en output visueel regressietesten.

## Restrisico’s en beslispunten

- “Alleen het dak nog bekijken” kan als standaardroute voor eenvoudige, volledig ingevulde eengezinswoningen. Het mag geen belofte worden voor kwaliteitsverklaringen, appartementen/multi-zone, samengestelde geometrie of onbekende installaties.
- Een Vabi-desktopimport blijft nodig als onafhankelijke acceptatietest per ondersteunde EPA-versie. XML-validatie en fixtures alleen zijn onvoldoende.
- De gebruiker heeft live MagicPlan-wijzigingen toegestaan op een duplicaat; deze audit heeft geen formulier gepubliceerd en geen productiedossier overschreven.
