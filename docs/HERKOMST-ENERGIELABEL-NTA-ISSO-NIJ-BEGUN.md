# Hoe hangen energielabel, NTA 8800, ISSO, VABI en Nij Begun samen?

## Doel en status van dit document

Dit document legt in gewone taal uit waar de eisen in deze tool vandaan komen. Het is bedoeld als achtergrond voor ontwikkelaars, energieadviseurs en reviewers. Het vervangt **niet** de actuele wet- en regelgeving, de officiële NTA 8800, het toepasselijke ISSO-publicatieblad, de BRL 9500-W of de actuele documenten van Nij Begun.

Gebruik bij een inhoudelijk geschil altijd de officiële bron met het juiste versienummer en de juiste peildatum. Noteer die versies ook in het projectdossier.

## De keten in één oogopslag

```text
Klimaat- en energiebeleid
        ↓
Wet- en regelgeving voor energieprestatie en energielabel
        ↓
NTA 8800: landelijke bepalingsmethode
        ↓
ISSO-opnameprotocol + BRL 9500-W: opnemen, bewijs en kwaliteitsborging
        ↓
Geattesteerde rekensoftware, zoals VABI EPA-W: uitvoering van de berekening
        ↓
Energielabel / energieprestatie-indicatoren

Nij Begun gebruikt delen van deze bestaande keten
om een controleerbaar isolatieplan en toets aan de Isolatiestandaard te krijgen.
```

De belangrijkste scheiding is:

- **NTA 8800** bepaalt *hoe er wordt gerekend*;
- **ISSO** beschrijft voor de adviseur *hoe gegevens worden opgenomen en geïnterpreteerd*;
- **BRL 9500-W** borgt *wie het werk uitvoert en hoe het proces en dossier worden gecontroleerd*;
- **VABI EPA-W** is software die de methode uitvoert; VABI is zelf geen wettelijke norm;
- **Nij Begun** is het programma/de subsidieregeling met eigen proces-, plan- en subsidiabiliteitseisen.

## 1. Hoe is het energielabel ontstaan?

Het energielabel is ontstaan vanuit Europees en Nederlands beleid om de energieprestatie van gebouwen zichtbaar en vergelijkbaar te maken. Een label geeft bewoners, kopers, verhuurders, financiers en overheden een gestandaardiseerd beeld van de energieprestatie van een woning.

Nederland heeft de methodiek in de loop der jaren gewijzigd. Oudere labels en Energie-Index-berekeningen gebruikten eerdere methoden. Sinds 2021 wordt voor woningen de energieprestatie bepaald met de NTA 8800-systematiek. Daardoor zijn oude en nieuwe labeluitkomsten niet zonder meer één-op-één vergelijkbaar.

Een energielabel is meer dan een los getal. Het resultaat ontstaat uit:

1. een opname van gebouw, thermische schil en installaties;
2. regels voor bewijs en standaard-/forfaitaire waarden;
3. een gestandaardiseerde berekening;
4. kwaliteitsborging en registratie door bevoegde partijen.

## 2. Waarom is NTA 8800 tot stand gekomen?

De NTA 8800 is ontwikkeld als één samenhangende Nederlandse bepalingsmethode voor de energieprestatie van gebouwen. De methode brengt woningbouw en utiliteitsbouw en verschillende energieprestatievraagstukken onder één rekenkader. Zij ondersteunt onder meer de energieprestatie-eisen voor nieuwbouw en de bepaling van energielabels voor bestaande gebouwen.

De NTA 8800 beschrijft onder andere hoe moet worden gerekend met:

- geometrie en verliesoppervlakken;
- isolatiewaarden van gevels, vloeren, daken, ramen en deuren;
- ventilatie en infiltratie;
- verwarming, koeling en warmtapwater;
- zonne-energie en andere gebouwgebonden installaties;
- standaardgebruik, klimaatdata en omrekenfactoren.

De methode is bewust gestandaardiseerd: twee bevoegde adviseurs moeten bij dezelfde woning, dezelfde bewijsstukken en dezelfde opnamekeuzes tot reproduceerbare invoer en uitkomsten kunnen komen.

## 3. Wat is ISSO?

ISSO is een kennisinstituut voor de bouw- en installatiesector en publiceert vakkennis en opnameprotocollen. Voor woninglabels is het toepasselijke ISSO-publicatieblad de praktische brug tussen de abstracte bepalingsmethode en de opname in een echte woning.

Het protocol geeft bijvoorbeeld regels voor:

- afbakening van de thermische zone en rekenzones;
- meten en indelen van gevels, daken, vloeren en openingen;
- herkennen en onderbouwen van isolatie en installaties;
- gebruik van bewijsstukken, kwaliteitsverklaringen en forfaitaire waarden;
- basis- en detailopname;
- omgaan met onbekende of niet waarneembare situaties.

ISSO “rekent” dus niet in plaats van de NTA 8800. Het vertelt de adviseur vooral hoe betrouwbare invoer voor die berekening tot stand komt.

## 4. Wat is BRL 9500-W?

De BRL 9500-W is de kwaliteitsrichtlijn rond energieprestatieadvisering voor woningen. De BRL bevat eisen aan het gecertificeerde proces, de organisatie, de adviseur, controles en dossiervorming. Samen met het opnameprotocol voorkomt dit dat een technisch correct rekenmodel wordt gevoed met niet-herleidbare of onvoldoende onderbouwde invoer.

Voor deze tool betekent dit: automatisering mag gegevens structureren, controles uitvoeren en invoerbestanden voorbereiden, maar mag de professionele verantwoordelijkheid en verplichte controles van de bevoegde adviseur niet verhullen.

## 5. Wat is VABI EPA-W?

VABI EPA-W is geattesteerde rekensoftware voor de energieprestatie van woningen. De software implementeert de voorgeschreven rekenmethode en levert de energieprestatie-indicatoren waarmee onder andere het label en relevante toetsen worden onderbouwd.

Voor bediening en actuele software-uitleg gebruikt de kennisbank de officiële, doorlopend bijgewerkte
[VABI EPA Online Help](https://support.vabi.nl/support/epa/online-help/). Dit is geen vervanging van NTA 8800,
ISSO 82.1 of de vastlegging van de werkelijk gebruikte VABI-versie in het projectdossier.

Daarom hanteert deze tool de volgende gouden regel:

> De tool bereidt gegevens voor, controleert ze en leest resultaten terug; VABI EPA-W blijft de formele rekenkern voor de NTA 8800-berekening.

Een “VABI-eis” is meestal één van drie dingen:

1. een inhoudelijke NTA- of ISSO-eis die in VABI moet worden ingevoerd;
2. een softwaretechnische formaat- of enum-eis van het VABI-importbestand;
3. een beperking van wat veilig automatisch kan worden gemapt.

Die drie moeten in code en documentatie uit elkaar blijven. Een XML-code van VABI is bijvoorbeeld geen landelijke normregel.

## 6. Wat is Nij Begun?

Nij Begun is de langjarige aanpak voor Groningen en Noord-Drenthe die is ontstaan als reactie op de gevolgen van de gaswinning en de bredere sociaal-economische en verduurzamingsopgave in het gebied. Binnen die aanpak bestaan regelingen en uitvoeringsprocessen voor woningisolatie.

Voor een isolatieplan wil Nij Begun een controleerbare verbinding tussen:

- de bestaande toestand van de woning;
- de maatregelen die technisch nodig en uitvoerbaar zijn;
- de toets aan de geldende Isolatiestandaard;
- de actuele maatregelencatalogus en subsidiabele kosten;
- ventilatie, vocht, bouwfysica en andere randvoorwaarden;
- bewijsstukken, foto's, hoeveelheden en dossieropbouw.

Nij Begun heeft de NTA 8800 niet zelf gemaakt. De regeling gebruikt een bestaande, landelijk herkenbare energieprestatiemethodiek om plannen vergelijkbaar en toetsbaar te maken. Daarbovenop gelden eigen regelingseisen, formats, cataloguscodes, prijsregels en indieningscriteria.

## 7. Waarom gebruikt de tool NTA 8800 én VABI?

Omdat zij verschillende rollen hebben:

| Onderdeel | Rol | Wat de tool ermee doet |
|---|---|---|
| NTA 8800 | Bepalingsmethode | Legt rekenbegrippen en formules ten grondslag aan invoer en controles |
| ISSO-opnameprotocol | Praktische opnameregels | Stuurt MagicPlan-velden, geometrie, bewijs en waarschuwingen |
| BRL 9500-W | Kwaliteitsproces | Stuurt herleidbaarheid, dossiervorming en adviseurscontrole |
| VABI EPA-W | Geattesteerde rekensoftware | Ontvangt de invoer en levert de formele rekenresultaten terug |
| Nij Begun-documenten | Regeling en uitvoering | Bepalen planformat, catalogus, subsidiabiliteit en compleetheid |

De tool mag enkele controleberekeningen of verwachtingen tonen, bijvoorbeeld om een invoerfout te signaleren. Zo'n kruiscontrole is niet automatisch de formele uitkomst. Bij afwijking is de VABI-uitkomst leidend voor het dossier, nadat de adviseur invoer en softwareversie heeft gecontroleerd.

## 8. Hoe is deze tool hieruit ontstaan?

De tool is opgebouwd om één woningopname gecontroleerd door meerdere stappen te laten stromen:

```text
MagicPlan / handmatige opname
        ↓
canoniek dossier (één interne waarheid)
        ├── controles en actiepunten voor de adviseur
        ├── VABI-bibliotheken voor huidige/toekomstige toestand
        ├── maatregelkeuze en catalogusprijzen
        ├── ventilatie- en bouwfysische aandachtspunten
        └── isolatieplan, bijlagen en dossierexport
```

De ontwerpkeuze voor een **canoniek dossier** voorkomt dat MagicPlan-termen, webappvelden, VABI-codes en Word-velden ieder een eigen betekenis krijgen. Onzekere of niet-bevestigde invoer hoort leeg te blijven en als actiepunt zichtbaar te worden; de tool mag geen gunstige waarde gokken.

De repository verdeelt deze verantwoordelijkheden als volgt:

- `core/`: canoniek gegevensmodel en gedeelde geometrie;
- `magicplan/`: opname-import en vertaling naar het canonieke dossier;
- `vabi/`: import-/exportvertaling en resultaatlezing;
- `engine/`: advies- en maatregellogica;
- `catalog/`: Nij Begun-maatregelencatalogus en prijzen;
- `validator/`: compleetheids- en plausibiliteitscontroles;
- `isolatieplan/` en `ventilatie/`: leverdocumenten;
- `dashboard/`: begeleide gebruikersworkflow;
- `nijbegun_engine/`: publieke package-interface en package-data.

## 9. Welke bron wint bij tegenspraak?

Hanteer voor inhoudelijke besluiten deze volgorde, met steeds de actuele toepasselijke versie:

1. wet- en regelgeving en officiële aanwijzing van de bepalingsmethode;
2. NTA 8800 voor de berekeningsmethode;
3. toepasselijk ISSO-opnameprotocol en BRL 9500-W voor opname en proces;
4. officiële Nij Begun-regeling, kennisbank, maatregelencatalogus en formats;
5. documentatie van de gebruikte geattesteerde software voor softwarebediening en bestandsformaat;
6. interne tooldocumentatie en code.

Bij een conflict mag de interne toolregel nooit stilzwijgend winnen. Leg het conflict vast, corrigeer de mapping en voeg een regressietest toe.

## 10. Bronregister dat nog projectspecifiek moet worden ingevuld

Vul vóór formeel gebruik de exacte titels, versies en peildata in van de lokaal beschikbare documenten:

| Bron | Versie/datum | Bestandslocatie | Waarvoor gebruikt |
|---|---|---|---|
| NTA 8800 | 2025+C1:2026 | gelicentieerd lokaal exemplaar | bepalingsmethode |
| ISSO-publicatie woningbouw | ISSO 82.1, 7e druk, 12-01-2026 | gelicentieerd lokaal exemplaar | opnameprotocol |
| BRL 9500-W | BRL 9500-W:2026, aangewezen 29-05-2026 | lokaal exemplaar | proces en kwaliteitsborging |
| Nij Begun regeling/kennisbank | **in te vullen** | **in te vullen** | programma- en planeisen |
| Nij Begun maatregelencatalogus | Q3_2026_21072026 | lokaal bronbestand + afgeleide `catalog/catalog.json` | maatregelen, codes en prijzen |
| VABI EPA-W documentatie | online, doorlopend | officiële VABI Online Help | softwarebediening; versie per project apart vastleggen |

Bewaar auteursrechtelijk beschermde normdocumenten niet automatisch in Git. Een intern bronregister met gecontroleerde locatie, versie, geldigheid en verantwoordelijke is meestal geschikter.
