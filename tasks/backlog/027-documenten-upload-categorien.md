---
id: 027
assigned:
branch:
depends_on: []
---

# Task 027 — Documenten/foto-upload per categorie (SOBOLT-vergelijking)

## Goal
De "Afronden"-pagina van de webapp moet uploads per categorie tonen (plattegrond, ventilatieplan,
foto's, foto voorpagina, foto huisnummer, aantekeningen) met thumbnails en per-bestand verwijderen —
zoals SOBOLT dat al doet — in plaats van één ongesorteerde "Extra bijlagen"-bucket.

## Waarom (context uit sessie 21/22-8-2026)
Renze gebruikt zowel onze webapp als SOBOLT voor hetzelfde soort werk en vroeg om een vergelijking.
Via browser-automatisering (SOBOLT is canvas-gerenderd, DOM-tools werken er niet op — zie Notes) is de
"Documenten"-sectie in SOBOLT's Opname-pagina bekeken (project Meester Neuteboomstraat 26):

- 5 losse upload-knoppen naast elkaar: **Ventilatieplan · Plattegrond · Foto's · Foto voorpagina ·
  Aantekeningen**.
- Geüploade bestanden verschijnen gegroepeerd per categorie (bv. "Foto voorpagina ①"), inklapbaar,
  met thumbnail-grid en een prullenbak-icoon per foto (hover) om 'm te verwijderen.
- Een "Selecteren"-knop voor bulkacties.

Onze webapp (`dashboard/app.py`, Afronden-pagina) heeft nu: "Foto voorkant" + "Foto huisnummer" als
losse velden, één generiek "Eigen ventilatieplan"-upload, en één ongesorteerde "Extra bijlagen"-bucket
(facturen/plattegrond/foto's/offertes door elkaar, geen thumbnails, geen per-bestand verwijderen
zichtbaar in wat bekeken is). Concreet gemis: **plattegrond heeft geen eigen slot** — verdwijnt nu in
de ongesorteerde bijlagen, terwijl SOBOLT 'm als eigen categorie behandelt (hoort logisch bij het
ventilatieplan-hoofdstuk van het isolatieplan).

## Scope
- Nieuwe/aangepaste upload-routes in `dashboard/app.py` per categorie (plattegrond, ventilatieplan,
  foto's, foto voorpagina, foto huisnummer, aantekeningen), opgeslagen onder `out/projects/<tag>/`
  met een duidelijke per-categorie submap of naamconventie.
- Galerij-rendering met thumbnails per categorie op de Afronden-pagina (of een nieuwe "Documenten"-
  substap), met een verwijderknop per bestand.
- Bestaande "Foto voorkant"/"Foto huisnummer"-verplichtingen (KWACO-eis) blijven intact — dit is een
  UI/structuurverbetering, geen wijziging van de Beoordelingsformulier-eisen.

## Out of scope
- SOBOLT nabouwen 1-op-1 (andere backend/stack); alleen het UX-patroon (categorieën + thumbnails +
  per-bestand verwijderen) overnemen.
- Wijzigingen aan wat er wél/niet verplicht is voor "klaar voor indienen" (Beoordelingsformulier).
- Bulk-select/bulk-acties (SOBOLT's "Selecteren"-knop) — nice-to-have, niet vereist voor v1.

## Acceptance criteria
- [ ] Plattegrond, ventilatieplan, foto's, foto voorpagina, foto huisnummer en aantekeningen hebben elk
      een eigen, herkenbare upload-plek op de Afronden-pagina.
- [ ] Geüploade bestanden zijn zichtbaar als thumbnail (afbeeldingen) of bestandsregel (overig), per
      categorie gegroepeerd.
- [ ] Een geüpload bestand is per stuk te verwijderen zonder de rest van de categorie te raken.
- [ ] Bestaande KWACO-eisen (voorbladfoto/huisnummerfoto) blijven functioneel ongewijzigd werken.
- [ ] `./scripts/verify.sh` slaagt.
- [ ] AI-review PASS door een andere leverancier dan de bouwer.

## Sessions
- 2026-08-22 Claude Code: taak aangemaakt op verzoek van Renze na live SOBOLT-vergelijking. Nog niet
  gestart — staat in `backlog/`, niet `ready/`, want scope (submap-structuur, of dit een aparte
  substap of een sectie op Afronden wordt) is nog niet met Renze doorgesproken.

## Notes
SOBOLT (`nijbegun.sobolt.com`) is een **canvas-gerenderde app** — `get_page_text`/`find`/de
accessibility-tree zien er vrijwel niets van, en de linker-sidebar is een fixed-position overlay die
klikken op x<250px onderschept (leidde meermaals tot per ongeluk naar "Hulp"/"Profiel" navigeren i.p.v.
een sectie uitklappen). Werkende aanpak: klik ver rechts van een sectiekop (bv. x≈395) i.p.v. op het
chevron-icoon zelf. Bruikbaar voor een volgende sessie die verder wil kijken in SOBOLT (bv. de
"Gebouw"-sectie is nog niet bekeken).
