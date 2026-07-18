# Installatie-enumcodes — LIVE GEHARVEST uit EPA 12.0.1 (22-6-2026)

Bron: in EPA installaties aangemaakt (verwarming HR107, tapwater combitoestel, PV monokristallijn),
de Installatiebibliotheek geëxporteerd (`out/installatie_harvest.xml`) en de integercodes afgelezen.
De flow + if-this-then-that is live geobserveerd (screenshots). Golden rule: alleen bevestigde codes.

## Zonne-energie (PV) — node `ZonneEnergie` (sjabloon: vabi/refs/zonne_energie_node.xml)
De `ZonneEnergieList` is in EPA EÉN gedeelde node voor PV/PVT/zonneboiler/opslag (veel velden -1/0 als ongebruikt).
| Veld | Betekenis | Codes (LIVE) |
|---|---|---|
| `ZonneEnergiesysteem` | systeemtype | **0=PV-panelen · 1=PVT-panelen · 2=Zonneboiler · 3=Opslag** |
| `PiekvermogenPVPanelen` | PV-paneeltype | **0=Kwaliteitsverklaring · 1=Monokristallijn · 2=Multikristallijn · 3=Amorf-enkelvoudig · 4=Multi-junctie-amorf · 5=CIGS · 6=CdTe · 7=Onbekend kristallijn · 8=Onbekend amorf** |
| `FabricagejaarPVPanelen` | fabricagejaar | **0=Voor2001 · 1=2001-2010 · 2=2011-2014 · 3=2015-2017 · 4=Vanaf2018 · 5=Onbekend** |
| `Bouwintegratie` | ventilatie achter paneel | **0=Niet geventileerd · 1=Matig · 2=Sterk geventileerd · 3=Onbekend** |
| `Orientatie` | **PV-oriëntatie (klokrichting vanaf Noord — ANDERS dan de geometrie-oriëntatie!)** | **0=N · 1=NO · 2=O · 3=ZO · 4=Z · 5=ZW · 6=W · 7=NW** |
| `Hellingshoek` | **rauwe graden** (35 → 35; GEEN enum, anders dan de dak-Hellingshoek!) | graden |
| `AantalPanelen` / `OppervlakPaneel` | aantal / m² per paneel | getal |
| `OphalenBcrg` | kwaliteitsverklaring via BCRG | 0/1 |

**Conditionele logica (live):** ZonneEnergiesysteem=PV → toont BCRG-checkbox + PV-subsectie (paneeltype + bouwintegratie);
paneeltype=kristallijn/amorf → toont Fabricagejaar; AantalPanelen>0 → toont Oriëntatie.

## Verwarming — node `VerwarmingOpwekker` / `VerwarmingDistributie` / `VerwarmingAfgifte`
LIVE GEHARVEST 23-6-2026 (dropdowns afgelezen + export `out/installatie_harvest2.xml` bevestigd).
| Veld | Betekenis | Codes |
|---|---|---|
| `Systeem` | systeem | **0=Individueel · 1=Gemeenschappelijk/collectief · 2=Warmtelevering derden individueel · 3=Warmtelevering derden gemeenschappelijk** (live) |
| `TypeOpwekker` | opwekkertype (VOLLEDIG, index=code, export 9=WP-el bevestigd) | **0=Lokaal gaskachel · 1=Lokaal oliekachel · 2=Elektrische verwarming · 3=Moederhaard · 4=Gasgestookte ketel · 5=Oliegestookte ketel · 6=WKK · 7=Warmtepomp gasabsorptie · 8=Warmtepomp gasmotor · 9=Warmtepomp elektrisch · 10=Biomassakachel · 11=Biomassaketel centraal opgesteld** |
| `SubType` | ketel-subtype (bij gas/olieketel) | **4=HR107** (0=CR/1=VR/2=HR100/3=HR104/4=HR107 — anker HR107=4) |
| `TypeWarmtepomp` | WP-medium (bij TypeOpwekker 7/8/9, export 1 bevestigd) | **0=Water/water · 1=Lucht/water · 2=Lucht/lucht** |
| `BronWarmtepomp` | WP-bron (⚠️ GLOBALE codes, NIET dropdown-index!) | **Buitenlucht=1** (export-bevestigd). Dropdown lucht/water toont Buitenlucht/Retour-afvoerlucht/Buitenlucht+retourlucht; water/water toont bodem/grondwater/… → de overige bron-codes per stuk TE BEVESTIGEN via export (niet gokken). |
| `VoldoetAanMinCOP` | tabel 9.28 | 0/1 (bool) |
| `OpstelplaatsOpwekker` | plaats | **0=Binnen thermische zone** (1=Buiten) |
| `Afgiftesysteem` (VerwarmingAfgifte) | afgifte (VOLLEDIG, index=code, export 3=lucht bevestigd) | **0=Radiatoren/convectoren · 1=Ventilator-gedreven radiatoren/convectoren · 2=Vloerverwarming · 3=Luchtverwarming · 4=Overig of onbekend** |
| `Regeling` (afgifte) | regeling | **0=Hoofdvertrek (kamerthermostaat) · 1=Centraal met naregeling per ruimte · 2=Individueel per ruimte · 3=Overig/onbekend** |
| `Distributiemedium` (VerwarmingDistributie) | medium | **0=Water · 1=Geen (lokaal)** |
| `WaterAanvoertemperatuur` | temperatuurklasse | **0=30/27 · 1=35/30 · 2=40/35 · 3=45/40 · 4=50/42 · 5=55/47 · 6=60/50 · 7=65/55 · 8=70/60 °C** (mogelijk nog hoger 90/70 — TE BEVESTIGEN) |
| `TypeDistributie` | pijpsysteem | **0=Tweepijpssysteem · 1=Eenpijpssysteem** |
| Flow | conditioneel | TypeOpwekker → SubType (ketel) / TypeWarmtepomp+Bron (WP); Distributiemedium=Water → aanvoertemp+pijpsysteem |

## Koeling — node `KoelingOpwekker`
LIVE GEHARVEST 23-6-2026 (dropdowns + export bevestigd: TypeOpwekker 0/Expansie 0/Split 0).
| Veld | Betekenis | Codes |
|---|---|---|
| `Koelsysteem` | systeem | **0=Individueel · 1=Gemeenschappelijk/collectief · 2=Koudelevering derden individueel · 3=Koudelevering derden gemeenschappelijk** |
| `TypeOpwekker` | opwekker | **0=Compressiekoeling · 1=Absorptiekoeling · 2=Passieve of vrije koeling** |
| `Expansie` | expansie (bij compressie) | **0=Directe expansie in de ruimte (airco) · 1=Directe expansie in LBK (DX) · 2=Met indirecte verdamping** |
| `Splitsysteem` | split (bij directe expansie ruimte) | **0=Single split · 1=Multi split** |
| `Distributiemedium` | medium | **0=Water · 1=Geen (Lokaal)** |
| Aantal opwekkers | — | Eén/Twee/Drie (0/1/2) |

## Tapwater — node `Tapwater`/`TapwaterOpwekker` (LIVE 23-6-2026)
| Veld | Betekenis | Codes |
|---|---|---|
| `TypeInstallatie` | systeem | **0=Individueel** (collectief/extern = parallel aan verwarming) |
| `TypeOpwekker` (top) | categorie | **0=Compleet toestel · 1=Direct verwarmd vat · 2=Indirect verwarmd vat** |
| `TypeToestel` (bij Compleet) — ⚠️ GLOBALE codes, NIET dropdown-index! | toestel | dropdown-VOLGORDE: Keukengeiser · Gasgestookt warmwatertoestel (Badgeiser) · Gasgestookt combitoestel · (micro)WKK · Elektrische warmtepomp · Boosterwarmtepomp · Elektrische doorstromer · Elektrische boiler · Heet/kokend waterkraan. **Bevestigde codes: Gasgestookt combitoestel=10 · Elektrische warmtepomp (warmtepompboiler)=4.** Rest per stuk via export. |
| `Gaskeur` | gaskeur | **3** (Gaskeur CW) |
| `CwKlasse` | CW-klasse | **3** |
| `AangeslotenOp` | aansluiting | **0** (hele woning) |
| sub-secties | — | Aantal warmtapwatersystemen (Eén/Twee) · DWTW (`DwtwAanwezig`) · Afgiftesysteem · Distributie (`Circulatieleiding aanwezig`) |

## Zonne-energie — node `ZonneEnergie` (unified; zie ook regel 7 boven)
`ZonneEnergiesysteem`: **0=PV-panelen · 1=PVT-panelen · 2=Zonneboiler · 3=Opslag** (LIVE). De ene unified node bevat ook
opslag-velden (`TypeOpslag`/`TotaalOpslagCapaciteit`/`BackupVolume`) en zonneboiler/collector-velden (`TypeCollector`/
`VolumeVoorraadvat`/`Zonbijdrage`/`N0`/`A1`/`A2`). PV = volledig gewired+geverifieerd. Opslag(accu)/zonneboiler sub-enums
(`TypeOpslag`, `TypeCollector`) nog per stuk via export te bevestigen.

## Ventilatie — node `Ventilatie` / `Ventilatiesysteem` (LIVE GEHARVEST 18-7-2026)
Bron: voorbeeldproject 'hoekwoning' (Detailopname, systeem D) — dropdowns afgelezen + Installatie-export
`hoekwoning_installatie.xml` bevestigd de integercodes.
| Veld | Betekenis | Codes |
|---|---|---|
| `Systeem` | systeem | **0=Individueel** (export-bevestigd; collectief/warmtelevering = parallel aan verwarming) |
| `Ventilatiesysteem` (= VentilatiesysteemType A-E, top-level, index=code) | systeemtype | **0=A Natuurlijke ventilatie · 1=B Mechanische toevoer · 2=C Mechanische afvoer · 3=D Mechanische balansventilatie · 4=E Gecombineerd systeem** (D=3 export-bevestigd) |
| `Subsysteem` | subsysteem (ISSO 11.3) | **⚠️ GLOBALE codes, NIET per-systeem dropdown-index.** Bevestigd: **D5a=33** (export). D-lijst (8, matcht de bekende telling A:6/B:3/C:14/D:8/E:1): D1·D2·D3·D4a·D4b·D5a·D5b·D5c. Overige subsysteem-codes per stuk via export (golden rule). |
| `TypeWtw` | WTW-type | **3=Platen- of buizenwarmtewisselaar** (export-bevestigd) |
Conditioneel (D/E): LBK-velden + Type WTW + Volumeregeling. **Golden rule:** het ventilatie-subsysteem
stuurt de Standaard → blijft een bewuste adviseurskeuze; de tool flagt het (geen stille gok van code 33 e.d.).

## Herbevestigd 18-7-2026 (hoekwoning-export, WP + vloerverwarming + warmtepompboiler)
Verwarming `TypeOpwekker`=9 (WP-el) · `TypeWarmtepomp`=1 (Lucht/water) · `BronWarmtepomp`=1 (Buitenlucht) ·
`Afgiftesysteem`=2 (Vloerverwarming) · `Regeling`=2 · `DistributieMedium`=0 (Water) ·
`WaterAanvoertemperatuur`=1 (35/30) · `OpstelplaatsOpwekker`=0 (binnen). Tapwater `TypeInstallatie`=0 ·
`AangeslotenOp`=0 · `TypeOpwekker`=0 (Compleet toestel) · `TypeToestel`=4 (Elektrische warmtepomp/boiler).
PV `ZonneEnergiesysteem`=0 · `PiekvermogenPVPanelen`=0 (Kwaliteitsverklaring) · `Orientatie`=4 (Zuid, PV-enum!)
· `Hellingshoek`=45 (rauw). Alles conform de eerdere harvest → de installatie-mapping is stabiel.

## Nog te harvesten (per stuk via export — NIET gokken)
- **BronWarmtepomp** overige codes (bodem/grondwater/retourlucht/…): globale codes, alleen Buitenlucht=1 bevestigd.
- **Tapwater-detail**: warmtepompboiler/elektrische boiler/zonneboiler-toestelcodes, voorraadvat, DWTW, CW-klasse-codes.
- **Ventilatie**: VentilatiesysteemType (A-E) + Systeem + TypeWtw=3 nu BEVESTIGD (18-7, zie boven). Resterend: de GLOBALE subsysteem-codes per stuk (alleen D5a=33 bevestigd) — via export bij de gekozen subsysteem; blijft adviseurskeuze.
- **Biomassa** (kachel/ketel subtypes) · **WKK** (HRe-label/vermogen/bouwjaar) · hogere aanvoertemp-klassen (90/70).
- **LES (23-6):** top-level dropdowns = index=code (TypeOpwekker/Afgifte/Koeling bevestigd), maar CONDITIONELE sub-lijsten
  (zoals BronWarmtepomp) gebruiken GLOBALE codes ≠ dropdown-index → altijd via export bevestigen (golden rule).
