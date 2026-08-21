# Plattegrond-vision: veilige contractgrens

Status: Anthropic-providerroute en verplichte controlestap gebouwd; praktijkvalidatie blijft beperkt.

## Wat nu bestaat

`dashboard/plattegrond_import.py` accepteert JSON met contractversie 1 en een expliciete
project-uploadroot. Het resultaat noemt
provider, modelnaam en exacte modelversie, en bevat verdiepingen in uploadvolgorde. Iedere
verdieping verwijst naar een projectrelatieve JPG/PNG. Ruimten bevatten naam, functie,
relatieve contour, vermoedelijke aangrenzendheid, onzekerheden en eventueel oppervlakte.

Een afbeeldingspad wordt platformonafhankelijk als relatief pad gevalideerd, onder die root
geresolved en op PNG- of JPEG-signature gecontroleerd. Een suffix alleen is geen bewijs.

Een schaal heet alleen betrouwbaar als het resultaat minimaal één zichtbare maatlijn met
concrete bron, tekst, `lengte_m` en `pixel_lengte` noemt én een positieve
`meter_per_pixel` levert. Iedere verhouding `lengte_m / pixel_lengte` moet binnen 2% van
die schaal liggen. Die 2% laat alleen OCR- en pixelafronding toe; een andere schaal wordt
niet geaccepteerd. Zonder consistent bewijs zet
de validator alle modeloppervlakten op `null` en maakt hij een aandachtspunt. De adviseur
moet dan zelf iedere oppervlakte invullen.

Geen concept muteert het dossier. De bevestigingsfunctie vereist een volledige payload met
`expliciet_bevestigd: true`; ontbrekende verdiepingen of ruimten falen atomisch. Daarna krijgt
ieder opgeslagen ruimteveld in `bron_per_waarde` de herkomst `afgelezen` of
`handmatig_gecorrigeerd`. Bestaande geometrie wordt nooit overschreven.
Vermoedelijke aangrenzendheid wordt symmetrisch gemaakt (A-B impliceert B-A); self-links en
onbekende ruimtenamen worden geweigerd. Het contract claimt geen geometrische aangrenzendheid
op basis van contourafstand, omdat beeldcoördinaten daarvoor geen betrouwbare bouwkundige
grens bewijzen.

## Provider en gegevensbeleid

De webroute gebruikt de al aanwezige Anthropic-koppeling en vereist een expliciete
`ai.vision_model` plus API-sleutel. Uploaden of bekijken verstuurt niets:
uitsluitend **Afbeeldingen analyseren** start de live call. De pagina waarschuwt vooraf dat namen en
persoonsgegevens uit de tekening moeten worden verwijderd. Provider, exacte modelnaam en versie staan
in ieder concept. Een andere provider of ander bewaarbeleid vereist een nieuw besluit.

## Benchmark en grens van de claim

`tests/fixtures/plattegrond_benchmark_manifest.json` beschrijft de drie werkelijk geparseerde bronnen.
`dashboard/plattegrond_dataset.py` laadt de MagicPlan-JSON, Statistics-CSV en Vabi-monitor via hun
echte parserpaden. Samen bevatten ze minder dan tien vloeren en geen gekoppelde rastergrondwaarheid.
Daarom blijft de <5%-AC open; er wordt geen synthetische nauwkeurigheidsclaim gemaakt.

Het bestaande echte `Bouwtekening.jpg` is als real-world smoke bekeken: zonder betrouwbare maatlijn
en onafhankelijke ruimtelabels moet de schaal terecht onbekend blijven. Tien echte, onafhankelijk
gelabelde scans ontbreken nog. Iedere modelversie moet later opnieuw tegen zo'n echte set worden
geëvalueerd voordat een praktijknauwkeurigheidsclaim is toegestaan.
