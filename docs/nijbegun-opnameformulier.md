# Nij Begun opnameformulier — alles wat een M29-project nodig heeft

> Hét formulier per project: alle gegevens die je moet vastleggen voor een goedkeurbaar Nij Begun-
> isolatieplan (Maatregel 29). Volgorde = de webapp-flow. Vink af tijdens/na de opname.
> Scope-bewaking: **schil + ventilatie**. Cv-ketel/warmtepomp/PV = energielabel, NIET dit formulier.

## A · Project & identificatie
- [ ] Straat + huisnummer(+toevoeging): ______  Postcode: ______  Plaats: ______
- [ ] BAG nummeraanduiding-ID (= BagAdresId uit de portal-mail): ______
- [ ] Bouwjaar: ______   Renovatiejaar (indien ingrijpend gerenoveerd): ______
- [ ] Woningtype (dropdown): vrijstaand / 2-onder-1-kap / hoek / tussen / appartement…: ______
- [ ] Oriëntatie voorgevel (N/NO/O/ZO/Z/ZW/W/NW, gezien vanaf de straat): ______
- [ ] Lead gekoppeld aan project in de webapp (➕ Project-knop; AVG: geen persoonsgegevens in dossier)

## B · Geometrie (zie magicplan-inmeetgids voor de controlematen)
- [ ] Ag (gebruiksoppervlak) MagicPlan ≈ BAG (±5%): ______ m²
- [ ] Aantal bouwlagen: ___  Verdiepingshoogte(s): ______  Gevelhoogte buiten: ______ m
- [ ] Gevels benoemd (voor/achter/links/rechts) + m² per oriëntatie compleet
- [ ] Dak per vlak: type · m² · helling · oriëntatie
- [ ] Ramen per stuk B×H + deuren + panelen (Raam/paneel-toggle)

## C · Schil — huidige staat (per bouwdeel; isolatie alleen indien waarneembaar/aantoonbaar — ISSO 82.1 §8.7)
**Gevel** (per gevel/afwijkend deel)
- [ ] Spouw aanwezig? ja/nee/onbekend · spouwbreedte ___ mm (spouwinspectie-gids!)
- [ ] Isolatie: Ja (dikte ___ mm) / Nee / Onbekend (→ bouwjaarklasse) · Rc-bron: gemeten / dikte onbekend / kwaliteitsverklaring
- [ ] Begrenzing per vlak: buitenlucht / AOR / AVR (buurwand telt niet mee) · afwijkende delen gesplitst
**Vloer**
- [ ] Type (hout/beton) · begrenzing (kruipruimte/grond/AOR) · isolatie + dikte/onbekend
- [ ] Kruipruimte: toegang · **hoogte ___ cm** (≥35 cm nodig voor vloerisolatie) · droog/vochtig/water · foto met rolmaat
**Dak** (per dakvlak)
- [ ] Isolatie + dikte/onbekend · dakbeschot-staat · begrenzing (buitenlucht/AOR-berging)
**Glas** (per raam)
- [ ] Type glas (enkel/dubbel/HR/HR+/HR++/triple) — kozijn/rooster alleen bij afwijking
**Panelen/deuren**
- [ ] Panelen als dichte constructie (isolatie ja/nee/onbekend) · deuren + raam-in-deur

## D · Ventilatie (verplicht Nij Begun-onderdeel!)
- [ ] Systeem A–E + subsysteem (zakkaart ventilatie-herkennen-gids) · foto unit + typeplaatje
- [ ] Toevoerroosters per verblijfsruimte (ZR ja/nee) · afzuigpunten keuken/bad/toilet
- [ ] Qv10 alléén invullen indien gemeten · schimmel/vochtklachten genoteerd: ______
- [ ] Ventilatie ná isoleren doorgedacht (0,7 dm³/s·m²; keuken 21 / bad 14 / toilet 7; balans) — de webapp rekent + tekent het ventilatieplan

## E · Technische haalbaarheid per maatregel (M29 Bijlage 1 punt 13 — per maatregel invullen in de webapp)
- [ ] Spouw: breed/schoon/droog genoeg? boorgat-bevindingen: ______
- [ ] Vloer: kruiphoogte + vocht → methode (vloer- of bodemisolatie): ______
- [ ] Dak: binnen- of buitenzijde bereikbaar · gording-diepte = max dikte: ______
- [ ] Bijzonderheden: asbestverdacht / lood / monument / vocht eerst oplossen: ______

## F · Foto's (bewijslast — kwaliteitscommissie)
- [ ] Vooraanzicht + huisnummer (verplicht, adres herkenbaar, ≥8 MP, max 5 MB)
- [ ] Per bouwdeel: overzicht + detail (V1 spouw: boorgat+endoscoop+voegwerk · V2 glas · V3 vloer/kruipruimte
      mét rolmaat · V4 dak binnen+buiten · ventilatie-unit + roosters)
- [ ] ≥1 detailfoto per cat-2-meerwerkpost · geen bewoners/persoonlijke spullen in beeld

## G · Afronding (webapp-stappen)
- [ ] MagicPlan-CSV ingeladen → opname nagelopen → VABI-import gedownload → Vabi doorgerekend
- [ ] VABI-export terug (huidige staat = nulmeting: label + afstand tot Standaard)
- [ ] Maatregelen gekozen (subsidietabel = Standaard; extra's = 30% ISDE) + haalbaarheid per maatregel
- [ ] VABI-toets ná maatregelen: **Standaard gehaald?** (nee → pakket uitbreiden)
- [ ] Toelichting geschreven · foto's geüpload · indien-check volledig groen (Beoordelingsformulier)
- [ ] Export-zip: isolatieplan **PDF + JSON** · ventilatieplan + -berekening · haalbaarheids-bijlage ·
      fotoblad · dossier.json → indienen via leveranciers@nijbegun.nl

> Alles hierboven bestaat al in de tool: de webapp-stappen dekken G, de MagicPlan-forms dekken A–D,
> de haalbaarheids-velden dekken E. Dit formulier is je papieren/mentale checklist dat NIETS ontbreekt.
