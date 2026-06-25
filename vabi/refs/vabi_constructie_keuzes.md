# VABI EPA — constructie-invoer: ALLE keuzemogelijkheden

Live afgelezen uit het constructie-invoerscherm van VABI EPA **12.0.1** (Constructies > Toevoegen).
Dit is de volledige keuzeruimte — méér dan de 219 standaard-constructies (die zijn alleen de
Beslisschema-presets). Gebruik dit om de MagicPlan-velden 1-op-1 op VABI af te stemmen.

## Type constructie (8)
Gevel · Paneel in kozijn · Raam · Deur · Dak hellend/plat · Dak hellend · Dak plat · Vloer
> Let op: dak heeft 3 varianten (hellend/plat = gecombineerd code 4, hellend = 5, plat = 6) — allemaal geldig.

## Invoer (methode)
- **Beslisschema** (forfaitair via isolatie/bouwjaar — de 219 presets gebruiken dit)
- **Kwaliteitsverklaring** (BCRG-gecontroleerde verklaring)
- Ramen/deuren bovendien: eigen **U-/g-waarde** invoeren (+ checkbox "Productinformatie g-waarde")

## Dichte delen (Gevel / Dak / Vloer / Paneel) — bij Beslisschema
**Isolatie aanwezig**: Ja · Nee · Onbekend
- **Ja** → checkbox "Isolatiedikte onbekend" (aan/uit) + isolatiedikte [mm]
- **Onbekend** → kies **Bouwjaar-klasse** (forfaitaire Rc volgt automatisch)
- (Luchtspouw aanwezig = aparte vlag; alleen relevant als geen isolatie / dikte < 4 cm / onbekend)

### Bouwjaar-klasse (12)
Tot 1965 · 1965 t/m 1974 · 1975 t/m 1982 · 1983 t/m 1987 · 1988 t/m 1991 ·
1992 t/m 2013 · 2014 · 2015 t/m 2017 · 2018 t/m 2020 (1 jan in gebruik) ·
2018 t/m 2020 (Overig) · Vanaf 2021 (1 jan in gebruik) · Vanaf 2021 (Overig)

## Raam — bij Beslisschema
**Kozijn (5)**: Hout of kunststof · Hout · Kunststof · Metaal (thermisch onderbroken) · Metaal (niet thermisch onderbroken)
**Glas (7)**: Enkel · Voorzetglas · Dubbel · HR (dubbel glas met coating) · HR+ · HR++ · TripleHR
- Checkbox "Oppervlakte per constructie"
- Forfaitaire U/g volgen automatisch (bv. Dubbel glas + hout/kunststof → U=2.90 buiten / 2.30 niet-buiten, g=0.75)

## Deur
- Checkbox "Deur met een raam ≥ 65% glas"
- Beslisschema: geïsoleerd / niet-geïsoleerd (niet-geïsoleerd → U = 3.40)

## Bron (verantwoording, alle types, 5)
Geen verantwoording in software · Waarneming in het gebouw · Van bestek of tekening ·
Volgens mededeling van opdrachtgever · Aangenomen
> Voor een MagicPlan-opname is "Waarneming in het gebouw" logisch.

---
## NB: Begrenzing & oriëntatie staan NIET hier
Die horen bij het **vlak/object** (Objectenbibliotheek), niet bij het constructie-type.
Begrenzing-keuzes (uit Opnameformulier/monitor): Buitenlucht · Water · Kruipruimte · Kelder ·
Grond · AOR (aangrenzende onverwarmde ruimte) · AOS (aangrenzende onverwarmde serre) ·
ASGR/SterkGeventileerdeRuimte. Oriëntatie: N/O/Z/W + NO/NW/ZO/ZW (+ horizontaal).
