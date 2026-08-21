# Nij Begun maatregelencatalogus-API

`catalog/catalog.json` wordt afgeleid van de publieke endpoint
`GET https://api.nij-begun.project.abl.nu/api/v1/measures`. Deze API heeft technische
specversie `1.0`, maar publiceert geen inhoudelijke catalogusversie of wijzigingsdatum. Daarom legt
de JSON drie afzonderlijke herkomstvelden vast:

- `api_specversie`: versie van het technische API-contract, niet van de catalogusinhoud;
- `opgehaald_op`: UTC-tijdstip waarop de response is opgehaald;
- `contentfingerprint`: SHA-256 van canoniek gesorteerde response-inhoud, onafhankelijk van
  object- en lijstvolgorde.

`versie` combineert de specversie met de eerste twaalf tekens van die fingerprint. Twee snapshots
met dezelfde volledige fingerprint hebben dezelfde inhoud, ook wanneer hun ophaaltijd verschilt.

## Handmatig verversen

Vanaf de repositoryroot:

```text
python catalog/api_client.py --refresh \
  --diff-report docs/catalogus-api-verschil-JJJJ-MM-DD.md
```

Het commando bewaart het bestaande doel als `catalog/catalog.json.bak`, haalt de publieke response
op, valideert iedere gemapte regel en schrijft daarna de nieuwe catalogus en het verschilrapport.
Voor een expliciete andere oude snapshot kan `--previous PAD` worden gebruikt. Een opgeslagen
response kan zonder netwerk worden verwerkt met `--map-json PAD`; dit is de route voor tests en CI.

De classificatie volgt de `category`/`subcategory`-relaties in de API. Dat is noodzakelijk voor
kostcodes zoals `B5-*`, die bij categorie V5 (Ventilatie) horen. Een lege code, categorie of level,
een dubbele code en een niet-eindige/niet-numerieke prijs blokkeren de import. Negatieve bedragen
zijn toegestaan omdat de API daarmee minderprijzen representeert.

De actuele migratievergelijking staat in
`docs/catalogus-api-verschil-2026-08-21.md`. Prijs- en codeafwijkingen worden gerapporteerd en niet
lokaal gerepareerd: de API blijft de bron.
