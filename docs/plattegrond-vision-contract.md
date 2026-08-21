# Plattegrond-vision: veilige contractgrens

Status: providerkeuze en productvalidatie geblokkeerd; het offline contract is gebouwd.

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

## Externe blockers

- De repository bevat geen gelabelde set van minimaal tien echte plattegronden. De vier
  aanwezige PNG-bestanden zijn dashboardiconen. De eis van minder dan 5% afwijking is dus
  niet getest en wordt niet geclaimd.
- Er bestaat een Anthropic-koppeling voor tekstredactie, maar er is geen vastgelegd
  visionmodel, versie, beeldgegevensbeleid of bewaartermijn. Dat is geen impliciete
  toestemming om woningplattegronden naar die provider te sturen.
- Voor providerimplementatie zijn nodig: expliciete keuze/autorisatie, gegevensbeleid en
  minimaal tien echte plattegronden met per ruimte een onafhankelijke referentieoppervlakte.
  Daarna moet elke modelversie opnieuw tegen die vaste set worden geëvalueerd.

Tot deze blockers zijn opgelost bestaat bewust geen upload- of analyseknop: die zou
functionaliteit suggereren die niet veilig of aantoonbaar beschikbaar is.
