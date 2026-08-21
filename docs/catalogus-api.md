# Nij Begun maatregelencatalogus-API

`catalog/catalog.json` wordt afgeleid van de publieke endpoint
`GET https://api.nij-begun.project.abl.nu/api/v1/measures`. Deze API heeft technische
specversie `1.0`, maar publiceert geen inhoudelijke catalogusversie of wijzigingsdatum. Daarom legt
de JSON drie afzonderlijke herkomstvelden vast:

- `api_specversie`: versie van het technische API-contract, niet van de catalogusinhoud;
- `opgehaald_op`: UTC-tijdstip waarop de response is opgehaald;
- `contentfingerprint`: SHA-256 van de gevalideerde, canoniek gesorteerde gemapte catalogusregels,
  onafhankelijk van de volgorde waarin de API maatregelen en kosten retourneert.

`versie` combineert de specversie met de eerste twaalf tekens van die fingerprint. Twee snapshots
met dezelfde volledige fingerprint hebben dezelfde inhoud, ook wanneer hun ophaaltijd verschilt.

## Handmatig verversen

Vanaf de repositoryroot:

```text
python catalog/api_client.py --refresh \
  --diff-report docs/catalogus-api-verschil-JJJJ-MM-DD.md
```

Het commando valideert eerst alle argumenten, de volledige mapping en het verschilrapport. Daarna
worden catalogus en rapport in hun doelmappen naar tijdelijke bestanden geschreven, geflusht en
met `os.replace` gepubliceerd. Mislukt schrijven of vervangen, dan blijven beide vorige bestanden
intact en worden tijdelijke bestanden opgeruimd.
Voor een expliciete andere oude snapshot kan `--previous PAD` worden gebruikt. Een opgeslagen
response kan zonder netwerk worden verwerkt met `--map-json PAD`; dit is de route voor tests en CI.

De classificatie volgt de `category`/`subcategory`-relaties in de API. Dat is noodzakelijk voor
kostcodes zoals `B5-*`, die bij categorie V5 (Ventilatie) horen. Een lege code, categorie of level,
een conflicterende dubbele code en een niet-eindige/niet-numerieke prijs blokkeren de import.
Volledig identieke dubbele codes worden expliciet gededupliceerd. Negatieve bedragen zijn toegestaan
omdat de API daarmee minderprijzen representeert.

De live response van 21 augustus 2026 bevat een bronconflict voor `V1-2-X3`: rolsteiger
(€ 250,43/st) onder V1-2 en hoogwerker (€ 569,25/wk) onder V2-3. De projecteigenaar heeft op
21 augustus 2026 expliciet besloten de rolsteiger te behouden en de hoogwerkervariant te negeren.
Dit is een gecontroleerde bronoverride: alleen de exact bekende hoogwerkeromschrijving, eenheid,
prijs en categorie worden genegeerd, de gekozen rolsteiger moet exact aanwezig zijn en
`catalog.json` vermeldt het besluit in `bronoverrides`. Elke afwijkende variant en ieder ander
duplicateconflict blokkeert de refresh nog steeds.

Het actuele verschilrapport staat in `docs/catalogus-api-verschil-2026-08-21.md`. Overige prijs-
en codeafwijkingen worden uitsluitend gerapporteerd; daarvoor bestaat geen lokale override.
