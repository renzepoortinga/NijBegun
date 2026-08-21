# Plattegrond-vision: veilige contractgrens

Status: providerkeuze en productvalidatie geblokkeerd; het offline contract is gebouwd.

## Wat nu bestaat

`dashboard/plattegrond_import.py` accepteert JSON met contractversie 1. Het resultaat noemt
provider, modelnaam en exacte modelversie, en bevat verdiepingen in uploadvolgorde. Iedere
verdieping verwijst naar een projectrelatieve JPG/PNG. Ruimten bevatten naam, functie,
relatieve contour, vermoedelijke aangrenzendheid, onzekerheden en eventueel oppervlakte.

Een schaal heet alleen betrouwbaar als het resultaat minimaal één zichtbare maatlijn met
tekst en pixellengte noemt én een positieve `meter_per_pixel` levert. Zonder dat bewijs zet
de validator alle modeloppervlakten op `null` en maakt hij een aandachtspunt. De adviseur
moet dan zelf iedere oppervlakte invullen.

Geen concept muteert het dossier. De bevestigingsfunctie vereist een volledige payload met
`expliciet_bevestigd: true`; ontbrekende verdiepingen of ruimten falen atomisch. Daarna krijgt
ieder opgeslagen ruimteveld in `bron_per_waarde` de herkomst `afgelezen` of
`handmatig_gecorrigeerd`. Bestaande geometrie wordt nooit overschreven.

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
