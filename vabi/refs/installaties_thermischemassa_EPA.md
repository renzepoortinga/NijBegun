# EPA-W (12.0.1) — exacte keuzelijsten, live afgelezen

Bron: live afgelezen in EPA-W 12.0.1 (voorbeeldproject "Energielabel Woning bestaande bouw
basisopname"), 14-6-2026. Dit is de **autoritatieve** lijst — MagicPlan moet deze 1-op-1 volgen.
NB: eerder stond "Half zwaar" bij thermische massa; dat is **fout** — bestaat niet in EPA.

---

## 1. Thermische massa (Rekenzone → Algemeen)
Twee aparte dropdowns, elk **3 klassen** (Licht / Zwaar / Zeer zwaar) mét omschrijving.

### Type bouwwijze WANDEN
1. **Licht:** Hout (hsb), staal (sfb), binnenzijde isolatie
2. **Zwaar:** Dragend metselwerk, betonnen kolom-ligger skeletbouw
3. **Zeer zwaar:** Betonnen wand-vloer skeletbouw

### Type bouwwijze VLOEREN
1. **Licht:** Hout (hsb), staal (sfb), schuimbetonvloer, binnenzijde isolatie
2. **Zwaar:** Staal/Hout-beton, niet-massieve beton (kanaalplaat- en cassettevloeren), licht met dekvloer
3. **Zeer zwaar:** Massieve beton

Naast deze twee staan op hetzelfde Rekenzone-Algemeen-scherm: **Bouwjaar**, **Renovatiejaar**,
**Qv10 gemeten** (checkbox), "Zware vloer met licht plafond", Specifieke interne warmtecapaciteit,
Gebruiksoppervlak per verdieping. → bevestigt dat deze in de Form "Schil & zone" (zone-niveau) horen.

---

## 2. Woningtype (Object → Algemeen → Subtype)
Eén dropdown "Subtype" bij Gebouwtype=Eengezinswoning. **4 opties:**
1. Vrijstaand
2. Kop-, eind- of hoekligging
3. Tussenligging
4. Twee onder een kap

Dit is hét veld voor de woningscheidende-wand-situatie (buren). VABI gebruikt Subtype +
`AantalNaastgelegenAangrenzendeGebouwen`. → woningtype hoort als projectveld in MagicPlan.

---

## 3. Ventilatie (Installatie → Ventilatie)
Volgorde in EPA: **Systeem → Ventilatiesysteem (A–E) → Subsysteem (met ⓘ-uitleg) → Merk/Type/
Installatiejaar → [systeem-specifieke velden] → Bron**.

- **Systeem:** Individueel · Collectief
- **Ventilatiesysteem (A–E):**
  - A Natuurlijke ventilatie
  - B Mechanische toevoer
  - C Mechanische afvoer
  - D Mechanische balansventilatie
  - E Gecombineerd systeem

### Subsystemen per systeem (exact)

**A — Natuurlijke ventilatie**
- A1 Standaard (toevoer niet luchtdruk gestuurd)
- A2a Luchtdrukgestuurde toevoer Δp ≤ 1 Pa
- A2b Luchtdrukgestuurde toevoer 1 Pa < Δp ≤ 5 Pa
- A2c Luchtdrukgestuurde toevoer 5 Pa < Δp ≤ 10 Pa
- Type onbekend, zelfregelende klep aanwezig, bouwjaar rekenzone
- Type onbekend, zelfregelende klep aanwezig, geplaatst > 2003
- (extra veld: **Lintverwarming aanwezig** (natuurlijke ventilatie))

**B — Mechanische toevoer**
- B1 Standaard
- B2 Tijdsturing op toevoer, zonder zonering
- B3 CO₂-meting per verblijfsruimte, CO₂-sturing op toevoer, met zonering
- (extra: passieve koeling · debiet bekend · LBK ≥1000 m³/h · luchtdichtheidsklasse · ventilatoren)

**C — Mechanische afvoer**
- C1 Standaard
- C2a Luchtdrukgestuurde toevoer Δp ≤ 1 Pa
- C2b Luchtdrukgestuurde toevoer 1 Pa < Δp ≤ 5 Pa
- C2c Luchtdrukgestuurde toevoer 5 Pa < Δp ≤ 10 Pa
- Type onbekend, zelfregelende klep aanwezig, bouwjaar rekenzone
- Type onbekend, zelfregelende klep aanwezig, geplaatst > 2003
- C3a Tijdsturing afvoer, zonder zonering
- C3b Luchtdrukgestuurde toevoer Δp ≤ 1 Pa, tijdsturing afvoer, zonder zonering
- C3c Tijdsturing toevoer, afvoer zonder zonering
- C4a Luchtdrukgestuurde toevoer Δp ≤ 1 Pa, sturing op afvoer door CO₂-metingen in de woonkamer en ten minste de hoofdslaapkamer, zonder zonering
- C4b CO₂-sturing op de toevoer in ten minste de woonkamer en de hoofdslaapkamer, zonder zonering
- C4c Luchtdrukgestuurde toevoer Δp ≤ 1 Pa, sturing op afvoer door CO₂-metingen in de woonkamer en ten minste de hoofdslaapkamer, zonder zonering
- C5a Luchtdrukgestuurde toevoer Δp ≤ 1 Pa, sturing op afvoer door CO₂-metingen in de woonkamer en ten minste de hoofdslaapkamer, met zonering
- C5b Luchtdrukgestuurde toevoer Δp ≤ 1 Pa, sturing op afvoer door CO₂-metingen in de woonkamer en ten minste de hoofdslaapkamer, met zonering en afzonderlijke afvoerpunten per verblijfsruimte

**D — Mechanische balansventilatie**
- D1 Standaard
- D2 Centrale WTW-installatie zonder zoneringen en zonder sturing
- D3 Cent. WTW, sturing toe- of afvoer CO₂-meting in de wk, geen zonering
- D4a Tijdsturing zonder zonering
- D4b Tijdsturing met zonering
- D5a Centrale WTW. CO₂-metingen in ten minste de woonkamer en de hoofdslaapkamer, sturing op toe- of afvoer, met zonering
- D5b Decentrale WTW. CO₂-metingen in ten minste de woonkamer en de hoofdslaapkamer, sturing op toe- of afvoer, met zonering
- D5c Centrale WTW. CO₂-metingen in ten minste de woonkamer en de hoofdslaapkamer, sturing op toe- of afvoer, zonder zonering
- (extra: **Type WTW** — zie onder)

**E — Gecombineerd systeem**
- E1 Systeemdeel D: decentrale WTW (Systeem D.5b); Systeemdeel met een ander ventilatiesysteem
- (extra: Verblijfsgebied systeem [m²]; twee systeemdelen)

### Type WTW (bij D/E)
- Kruisstroomwarmtewisselaar
- Tegenstroomwarmtewisselaar, aluminium
- Tegenstroomwarmtewisselaar, kunststof
- Tegenstroomwarmtewisselaar, onbekend
- Langzaam roterende of intermitterende warmtewisselaar (warmtewiel)
- Enthalpiewisselaar
- Warmtebuisapparaat (heatpipe)

### Bron (alle installatiedelen)
Geen verantwoording · Waarneming in het gebouw · Van bestek of tekening · Mededeling · Aangenomen · Onbekend

---

## 4. Installatie-secties (volgorde in EPA)
**Ventilatie · Verwarming · Tapwater · Koeling · Zonne-energie** — Zonne-energie hoort er dus
expliciet bij (PV/PVT/zonneboiler). De MagicPlan-form moet deze vijf secties in deze volgorde volgen.
