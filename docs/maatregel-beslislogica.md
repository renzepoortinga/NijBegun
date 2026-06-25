# Maatregel-beslislogica — welk advies in welke situatie

Onze eigen, **offline** adviesmotor (geen AI/tokens, geen externe tool nagebouwd). Pure logica,
afgeleid uit de **Maatregelencatalogus** (families per onderdeel) + RVO-streefwaarden en
NTA 8800-principes. Geimplementeerd in `engine/advies_logic.py`; doel = de **Standaard** (Vabi
rekent die exact). Dit document is de leesbare matrix achter die regels.

## Volgorde-principes (hoe een adviseur redeneert)
1. **Grootste, slechtste vlak eerst** — meeste besparing per euro (gevel/dak vaak eerst).
2. **Goedkoopste effectieve maatregel** binnen een bouwdeel kiezen (engine doet de kostenpick).
3. **Isoleren maakt luchtdichter** → altijd ventilatie + kierdichting meenemen.
4. **Doel is de Standaard**, niet "alles maximaal" — streefwaarden zijn richtinggevend.
5. Reeds **op niveau** geisoleerd → geen advies (voorkom over-advisering).

## Streefwaarden (richtinggevend doel per bouwdeel)
| Bouwdeel | Streef | "Op niveau" als (geen advies meer) |
|---|---|---|
| Gevel | Rc 5,0 | isolatie Ja én Rc ≥ 5,0 of dikte ≥ 80 mm |
| Dak | Rc 6,5 | isolatie Ja én Rc ≥ 6,5 of dikte ≥ 120 mm |
| Vloer | Rc 3,7 | isolatie Ja én Rc ≥ 3,7 of dikte ≥ 80 mm |
| Raam | U 1,6 | HR++/triple/vacuüm aanwezig |
| Deur | U 2,0 | geïsoleerde deur |

## A — Gevel
| Situatie | Advies | Materialen (catalogus) | Prio |
|---|---|---|---|
| **Spouw aanwezig**, niet/licht geïsoleerd | **Spouwmuurisolatie** | minerale wol vlokken · EPS parels · PUR-schuim | 1 |
| Geen (bruikbare) spouw / massieve gevel | **Binnenisolatie (voorzetwand)** of **buitengevelisolatie** | voorzetwand glas-/hout-/hennep-/vlas-/grasvezel of PIR · buitengevel ETICS | 2 |
| Al op niveau | — geen advies | | — |

*Rationale:* spouwvulling is de goedkoopste effectieve eerste stap; zonder spouw is binnen- of
buitenzijde nodig (buiten = thermisch best, geen koudebruggen; binnen = behoud aanzicht).
**Spouw vervalt bij dikte ≥ 40 mm** (dan niet relevant).

## B — Glas & kozijnen
| Situatie | Advies | Materialen | Prio |
|---|---|---|---|
| Enkel/dubbel glas (geen HR) | **HR++/triple** vervangen, of **voorzetbeglazing** bij behoud kozijn | HR++ · triple · voorzetraam | 2 |
| Slecht/rot kozijn | kozijn vervangen (met HR++/triple) | | 2 |
| Ongeïsoleerde buitendeur | geïsoleerde deur | | 3 |

*Rationale:* HR++/triple halveert glasverlies en stopt koudeval/tocht; voorzetbeglazing bij
monument/behoud. Deur meestal klein oppervlak → lagere prioriteit.

## C — Vloeren
| Situatie | Advies | Materialen | Prio |
|---|---|---|---|
| Niet/onvoldoende geïsoleerd, **kruipruimte toegankelijk** | **Bodemisolatie** en/of **vloerisolatie (onderzijde)** | EPS-korrels (bodem) · isolatiefolie · PUR-schuim · EPS-platen | 2 |
| Geen kruipruimte / op grond | beperkte opties (per situatie) | | 3 |

*Rationale:* goedkoop en direct comfort (minder koude voeten); combineer met kierdichting vloerranden
en bodemisolatie waar de kruipruimte dat toelaat.

## D — Daken
| Situatie | Advies | Materialen | Prio |
|---|---|---|---|
| Hellend dak niet/onvoldoende geïsoleerd | **Dakisolatie (hellend)** binnenzijde, of buitenzijde bij dakvervanging | glaswol · PIR-platen · biobased (vlas/gras/hennep/houtvezel) · gespoten schuim | 1 |
| Plat dak niet/onvoldoende geïsoleerd | **Dakisolatie (plat)** | idem | 1 |

*Rationale:* warmte stijgt → ongeïsoleerd dak is groot lek met hoog rendement; meestal goed uitvoerbaar.

## E — Ventilatie (dossier-breed, na isoleren)
| Situatie | Advies | Prio |
|---|---|---|
| Schil wordt luchtdichter + **alleen natuurlijke ventilatie (A)** | **Upgrade**: mechanische afvoer met CO₂-sturing **of balans-WTW (D)** | 1 |
| Schil luchtdichter, mechanische ventilatie aanwezig | Capaciteit/sturing controleren; evt. CO₂-sturing/WTW | 2 |

*Rationale:* isoleren verhoogt luchtdichtheid → zonder gebalanceerde ventilatie vocht-/schimmelrisico;
WTW bespaart energie. Vaste bijlage "Waarom ventileren".

## Algemeen — luchtdichtheid
| Situatie | Advies | Prio |
|---|---|---|
| Na isolatie | **Kierdichting** (kozijnen, vloerranden, muurplaten, draaiende delen) | 2 |
| qv;10 aantonen | **Blowerdoortest** (m.n. recentere bouw/renovatie) | 3 |

*Rationale:* kierdichting verlaagt qv;10 (infiltratie), is goedkoop en vaak nodig om de Standaard te
halen. Zie ook `docs/nijbegun_workflow.md` (qv;10 vs renovatiejaar na maatregelen).

---
**Pipeline:** `advies_logic` (welke maatregel wanneer) → `measure_engine` (goedkoopste pakket dat de
Standaard haalt) → `advies_text` (begeleidende tekst) → isolatieplan-template. Vabi EPA-W bevestigt
of het pakket de Standaard haalt. Alles offline en reproduceerbaar.
