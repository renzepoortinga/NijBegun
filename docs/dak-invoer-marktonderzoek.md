# Dak-invoer in NL energielabel- en isolatieadviessoftware — vergelijkend onderzoek + UX-aanbevelingen

*Product-research, 11-7-2026. Bronnen: publiek web (inbrix.nl, sobolt.com, support.vabi.nl, label-wise.nl, waarderingskamer.nl) + eigen kennis van de Sobolt-tool en Vabi EPA 12. Waar publieke info dun is staat dat expliciet.*

---

## 1. INBRIX (inbrix.nl) — parametrische dak-generator

**Wat het is.** Opname-app voor EP-adviseurs (iOS/Android, gelanceerd ±2025): meetdata, foto's, constructies en installaties op locatie vastleggen; claim "tot 80% minder uitwerktijd"; **met één klik exporteren naar Vabi, zonder dubbel invoeren** (alleen Vabi wordt genoemd, geen Uniec).

**Hoe zij daken oplossen — de kern:**

> "Kies een **standaard dakconstructie**, voer de variabelen in, en de **dakvlakken, gevels en gebruiksoppervlakte** worden automatisch berekend en aangemaakt."

Dus: daktype kiezen → een handvol maten invoeren → de app genereert *tegelijk* (a) de hellende/platte dakvlakken, (b) de bijbehorende gevels (dus ook **kopgevels/topgevels** bij een zadeldak), én (c) de **gebruiksoppervlakte** (Ag-bijdrage van de kap, dus inclusief de 1,5-m-aftrek). "De meest voorkomende daken zitten al in het systeem, en dit wordt uitgebreid." Verdiepingen werken hetzelfde: lengte × breedte × hoogte invoeren, "Inbrix doet de rest".

**Dakkapellen/erkers:** kant-en-klare **standaardmodules** ("handige standaardmodules, zoals erker en dakkapel") — je voert de module-maten in en de set vlakken wordt gegenereerd i.p.v. dat je voorvlak/wangen/plat dak los intypt.

**Eerlijkheid over de bronnen:** dit is zo'n beetje alles wat publiek vindbaar is. De handleidingen-pagina (inbrix.nl/handleidingen) toont alleen videotitels — relevant: *"Standaard dakconstructies en verdiepingen toevoegen"*, *"Tekenen op plattegronden"*, *"Constructie aanmaken"*, *"Standaard gebouwonderdeel aanmaken"*, *"Glas in deur verrekenen"* — maar de video's zelf zijn niet openbaar geïndexeerd (geen YouTube-kanaal gevonden). **Welke variabelen** per daktype gevraagd worden (nokhoogte? goothoogte? helling? overstek?) en hoe de Ag-aftrek precies wordt getoond, is publiek niet gedocumenteerd. Wil je dat weten: demo aanvragen (ze bieden die actief aan) of de app installeren.

**Les voor ons:** het bestaans­bewijs dat *parametrische dak-generatie + Ag-koppeling* commercieel de onderscheidende feature is. Inbrix verkoopt precies de stap die bij ons `core/geometry.py` al half doet (footprint + daktype → vlakken) — maar zij koppelen er de gebruiksoppervlakte en de kopgevels expliciet aan vast, en houden alles daarna handmatig overschrijfbaar via "standaard gebouwonderdeel".

---

## 2. SOBOLT (nijbegun.sobolt.com) — géén geometrie-automatisering, platte lijst

**Wat het is.** De goedgekeurde M29-isolatieplantool (live in Groningen sinds nov 2025, goedgekeurd door de provincie). Workflow in 5 stappen: *"Woningdata invoeren en ophalen"* → *"Berekenen volgens NTA 8800"* (realtime tijdens invoer, eigen rekenkern) → *"Slim maatregelenpakket samenstellen"* (ingebouwde M29-catalogus) → *"Isolatieplan genereren"* (PDF, één klik) → uitvoeren met checklists. Data centraal opgeslagen binnen de EU.

**Hoe zij daken oplossen:** *niet* — bewust. Bekend uit eigen gebruik (en consistent met wat publiek zichtbaar is): een **platte lijst dakelementen** waarin de adviseur per element **direct m² en Rc** invoert, per rekenzone. Geen daktype-keuze, geen hellingshoek-afleiding, geen kopgevel-generatie, geen Ag-koppeling vanuit het dak. Dakkapellen: geen module — je voegt gewoon extra elementen toe (of neemt ze op in het dakvlak-m²; de tool dwingt niets af). De publieke pagina's en webinars ("van de rekensoftware en eerste ervaringen van adviseurs tot updates en rapportages") adverteren rekensnelheid en catalogus-integratie, nooit geometriehulp.

**Waarom dat werkt voor hen:** hun rekenkern vraagt alleen verliesoppervlakken × U/Rc; voor een *isolatieplan* (geen geregistreerd label) is de bewijslast op de m² lichter. De prijs is dat de adviseur zelf buiten de tool moet rekenen (schuine m² = footprint/cos, kopgevel-driehoeken, Ag-aftrek) — precies het "klungelen met nameten" dat Renze bij de eerste veldopname wilde elimineren.

**Les voor ons:** Sobolt bewijst dat een platte lijst *volstaat* voor M29-goedkeuring — de generator is dus UX-luxe, geen compliance-eis. Maar het is óók de zwakke plek waarop wij ons kunnen onderscheiden.

---

## 3. Vabi EPA (Assets Energie) — het referentiemodel dat onze export moet voeden

Uit de online help (support.vabi.nl, Rekenzone – Geometrie):

- **Ordening:** tabbladen *Voorgevel / Achtergevel / Linkergevel / Rechtergevel / Daken / Vloeren*. Cruciaal citaat: **"Invoer op de verschillende tabbladen (locatie) is optioneel"** — het is puur ordening, geen semantiek. En: *"Voor hellende daken kan je het bouwdeel eerst op de betreffende ligging invoeren en daarna, desgewenst, verplaatsen naar het tabblad daken."*
- **Per dakvlak:** oppervlak (of l×b), **constructie** (Rc, met keuze constructie 'hellend dak', 'plat dak' of gecombineerd 'hellend/plat dak'), **begrenzing** (buitenlucht/AOR/…), **oriëntatie** en **hellingshoek** (0° = horizontaal, 90° = verticaal).
- **Oriëntatie-afleiding:** geef je de oriëntatie voorgevel op, dan worden voor/achter/links/rechts automatisch gevuld (exact ons gevelnaam-model); je voert de *dichtstbijzijnde* hoofdrichting in want **NTA 8800 rekent op 4 oriëntaties, niet 8**. Dakvlakken zonder logische gevelkoppeling: oriëntatie handmatig.
- **Dakramen** = deelvlakken ín het dakvlak; ze **erven de hellingshoek van het moedervlak**, plus oppervlak/afmetingen, beschaduwing/overstek, zonwering.
- **Dakkapellen/kopgevels:** géén module. Standaard bouwdeel-logica: elk vlak los. Een kopgevel is gewoon een gevel-bouwdeel (driehoek meetellen in het gevel-m²), een dakkapel wordt voorvlak (gevel/kozijn) + wangen + plat dakje, elk als eigen bouwdeel, en het gat in het dakvlak moet je zelf van het dakvlak-m² aftrekken.

De Label-wise-kennisbank (rekensoftware-concurrent) bevestigt het pijnpunt onafhankelijk: *"NTA 8800 rekent met alle vlakken van de thermische schil; dakkapellen voegen extra gevels, daken en aansluitingen toe waardoor het aantal vlakken snel oploopt… complexe vormen maken de invoer foutgevoelig… de kunst is deze gestructureerd vast te leggen zodat je niet verdwaalt in tientallen losse vlakken en later kunt herleiden hoe je aan elk oppervlak komt."* Hun remedie is proces-discipline (naamconventies, sjablonen/bibliotheken voor terugkerende details bij seriematige bouw) — geen generator.

---

## 4. Dakkapellen — drie strategieën naast elkaar

| Strategie | Wie | Hoe |
|---|---|---|
| **Module/generator** | Inbrix | Standaardmodule "dakkapel": maten invoeren → voorvlak + wangen + plat dak + (vermoedelijk) dakvlak-aftrek gegenereerd |
| **Losse vlakken, discipline** | Vabi, Label-wise | Elk vlak apart bouwdeel; naamconventie + herleidbaarheid is het houvast; dakvlak-m² zelf corrigeren |
| **Niet afgedwongen / opgaan in het dakvlak** | Sobolt | Platte lijst; adviseur beslist zelf of de dakkapel apart element wordt of in het dak-m² verdwijnt |

**Forfaitair bestaat nergens** — er is in NTA 8800/ISSO 82.1 geen forfaitaire dakkapel; klein oppervlak mag hooguit praktisch worden meegenomen in het omliggende vlak als de constructie-eigenschappen niet wezenlijk verschillen (maar het voorvlak bevat vrijwel altijd een raam, dus dat kán zelden). De vlakken-set van een standaard dakkapel: **voorvlak** (grotendeels kozijn + borstwering, verticaal, oriëntatie = dakvlak-oriëntatie), **2 wangen** (verticaal, oriëntatie ±90°, vaak licht/ongeïsoleerd → apart Rc!), **plat dak** (hellingshoek 0°), en **aftrek van het gat** in het hellende dakvlak.

## 5. De 1,5-meter-lijn en Ag — de asymmetrie die de UX moet uitleggen

- **Ag (gebruiksoppervlakte thermische zone)** volgt NEN 2580/meetinstructie: vloeroppervlak met **vrije hoogte < 1,5 m telt niet mee**. Het Waarderingskamer-document bevestigt: de Ag van de thermische zone wordt *altijd door de EP-adviseur* bepaald (bewust buiten de meetinstructie gehouden), is een deelverzameling van de BAG-GO, en van 'overige inpandige ruimten' (vliering, zolder-als-berging, kelder, bijkeuken…) moet per ruimte beoordeeld worden of ze binnen de thermische schil vallen. Het spiegelonderzoek van RVO noemt de 1,5-m-grens onder (2-zijdig) hellende daken expliciet als veelgemaakte fout.
- **Verliesoppervlak ≠ Ag**: het dakvlak telt als schil-verlies **volledig** mee, tot aan de goot — óók het stuk onder de 1,5-m-lijn — zolang de isolatielijn het dakvlak volgt. De 1,5-m-lijn knipt alleen de *vloer*-m² (Ag), nooit het *dak*-m².
- **Knieschot-varianten** (bepaalt de schil-lijn, dus wélke vlakken meedoen):
  1. *Isolatie volgt het hele dakvlak* → dakvlak nok-tot-goot in de schil; ruimte achter het knieschot binnen de zone (maar <1,5 m-vloer telt niet in Ag).
  2. *Isolatie over knieschot + dakvlak boven knieschot* → dakvlak-onder-knieschot vervalt uit de schil; knieschot = wand grenzend aan **AOR**; dakvlak boven knieschot blijft buitenlucht.
  3. *Onbeloopbare/onverwarmde zolder, geïsoleerde zoldervloer* → dakvlakken helemaal niet in de schil; zoldervloer = plafond hoogste woonlaag, begrenzing **AOR** (vliering = klassiek voorbeeld van 'overige inpandige ruimte' buiten de zone).
- **Geen van de drie pakketten automatiseert dit zichtbaar goed.** Inbrix rekent de Ag mee bij de dak-generator (hoe transparant is onbekend); Vabi en Sobolt leggen het volledig bij de adviseur.

## 6. Vergelijkingstabel

| Aspect | Inbrix | Sobolt (M29) | Vabi EPA |
|---|---|---|---|
| Dak-invoermodel | Parametrisch: daktype + variabelen → vlakken | Platte lijst: m² + Rc per element | Per vlak: m²/l×b + helling + oriëntatie + begrenzing |
| Kopgevels | Automatisch mee-gegenereerd | Zelf als wand-m² invoeren | Zelf als gevel-bouwdeel |
| Ag-koppeling dak | Automatisch berekend | Los veld, zelf bepalen | Los veld, zelf bepalen |
| Dakkapel | Standaardmodule | Vrij (geen structuur) | Losse bouwdelen |
| Dakramen | Onbekend (publiek) | Element in lijst | Deelvlak, erft dakhelling |
| Oriëntatie | Onbekend | Per element | Voorgevel → rest afgeleid; 4 windrichtingen |
| Doelgroep-route | Label (BRL 9500-W) → Vabi-export | M29-plan, eigen rekenkern | Rekenkern zelf |
| Publieke documentatie | Dun (videotitels, marketingclaims) | Dun (workflow-marketing) | Goed (online help) |

## 7. Aanbevelingen voor onze invoer-UX

**Grondprincipe (gevalideerd door alle drie):** *parametrisch genereren, transparant tonen, altijd overschrijfbaar.* Inbrix bewijst de waarde van de generator; Vabi bewijst dat de export uiteindelijk losse vlakken met m²/helling/oriëntatie/begrenzing moet opleveren; Label-wise bewijst dat herleidbaarheid ("hoe kom ik aan dit m²?") de audit-eis is. Toon dus bij elk gegenereerd vlak de formule ("2 × 8,4 m × 5,1 m/cos 40° = 55,9 m²") en een potloodje.

**Minimale vragenset per daktype** (sluit aan op bestaand `core/geometry.py` + MagicPlan-footprint):

| Daktype | Minimale vragen | Automatisch afgeleid | Flag/controle |
|---|---|---|---|
| **Plat** | Rc(-bron); overstek j/n | m² = footprint; helling 0°; geen oriëntatie nodig | — |
| **Zadel** | Nokrichting (evenwijdig aan voorgevel j/n); helling °(of goot- + nokhoogte); Rc | 2 dakvlakken = ½footprint/cos elk; oriëntaties uit 'oriëntatie voorgevel' (ons gevelnaam-model = exact Vabi's model); **2 kopgevels** (driehoek: ½·breedte·(nok−goot)) bij de juiste gevels opgeteld; Ag-zolderbijdrage met 1,5-m-aftrek uit breedte+helling | Toon afgeleide oriëntaties ter controle (doen we al) |
| **Lessenaar** | Richting laagste zijde; helling; Rc | 1 vlak = footprint/cos; 1 hoge kopwand-strook | Oriëntatie dakvlak expliciet bevestigen |
| **Schild** | Helling (evt. per vlakpaar); Rc | 4 vlakken, totaal = footprint/cos, verdeeld; **géén kopgevels** | Flag "verdeling per vlak verfijnen in Vabi" (doen we al) |
| **Samengesteld / mansarde / afwijkend** | — | **Niets genereren** | Route 'zelf invoeren': lijst-editor per vlak (m², helling, oriëntatie, begrenzing) — het Sobolt-model als vangnet |

**Dakkapel als module (Inbrix-model), niet als losse vlakken:** vraag breedte, hoogte voorvlak, diepte, raam-m² (of kozijnmaat), wangen geïsoleerd j/n → genereer voorvlak (borstwering + kozijn), 2 wangen, plat dakje, én trek het gat automatisch van het moederdakvlak af. Naamconventie automatisch ("Dakkapel achter — wang links") zodat de Vabi-export herleidbaar blijft. Zelfde patroon herbruikbaar voor erker.

**1,5-m-lijn expliciet in de UI, per zolder-scenario één vraag:** "Is de zolder binnen de thermische schil?" → (a) *ja, isolatie volgt dak*: dakvlakken vol meetellen, Ag-bijdrage = alleen vloer >1,5 m (berekenen uit breedte+helling, tonen als "waarvan X m² telt voor Ag"); (b) *ja, tot knieschot*: dakvlak splitsen boven/onder knieschot, knieschot-wand → AOR; (c) *nee, zoldervloer geïsoleerd*: dakvlakken uit de schil, zoldervloer als plafond → AOR. Nooit stil corrigeren — de asymmetrie (dak-m² wél vol, vloer-Ag niet) is dé bekende foutbron (RVO-spiegelonderzoek) en juist een vertrouwenwekkend uitleg-moment.

**Wanneer 'zelf invoeren' de enige juiste route is:** samengestelde/mansarde/L-vormige daken; verschillende hellingen of Rc per vlak; gedeeltelijke isolatie (knieschot-lijn die per vlak verschilt); dakkapel over meerdere vlakken; alles waar de adviseur de generator-uitkomst niet met een controlemaat kan bevestigen. Golden rule blijft: wij benaderen, Vabi rekent, de adviseur verifieert — dus elke gegenereerde waarde krijgt de status "berekend — pas aan indien nagemeten" en gaat geflagd de sanity-check (`vabi/sanity.py`) in.

**Wat we NIET moeten doen:** een tekenmodule bouwen (Inbrix' "tekenen op plattegronden" is hun grootste investering en voor ons overbodig — MagicPlan ís onze tekenlaag); forfaitaire dakkapellen verzinnen (bestaat in geen enkel pakket noch in de norm); de Sobolt-platte-lijst als hoofdroute nemen (het is het juiste vangnet, maar de generator is precies waar wij en Inbrix tijd winnen).

---
*Kanttekening bronnen: over Inbrix is publiek weinig hards — de claims hierboven komen uit hun eigen marketing (homepage, app-store-teksten, handleiding-titels); onafhankelijke reviews of screenshots van de dak-dialoog zijn niet gevonden. Een demo aanvragen (of de gratis app installeren) is de enige manier om hun exacte variabelen-set per daktype te zien. Sobolt-details komen deels uit eigen gebruik van de tool; publieke pagina's bevestigen alleen de workflow op hoofdlijnen. Vabi-gedrag is uit de officiële online help en strookt met wat we live in EPA 12 hebben gezien.*