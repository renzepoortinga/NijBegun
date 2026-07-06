# Ventilatiesystemen & roosters HERKENNEN in de woning (veldgids)

> Voor de opname: welk systeem (A–E) + welk subsysteem vul je in MagicPlan in, en hoe zie je dat ter
> plekke? Subsysteem-lijsten = exact de VABI/ISSO-keuzes (vabi/refs/installaties_thermischemassa_EPA.md).
> Vuistregels/debieten: ventilatie/nijbegun_vuistregels.md. Twijfel = niet gokken → noteer + foto.

## Stap 1 — Het hoofdtype bepalen (A–E): stel 2 vragen
1. **Zit er een ventilatie-UNIT in de woning?** (zolder/berging/badkamer: witte doos met slangen/kanalen)
2. **Hoe komt verse lucht binnen, en hoe gaat lucht eruit?**

| Wat je ziet | Systeem |
|---|---|
| Alleen roosters/klepraampjes; géén unit, géén afzuigventielen | **A — natuurlijk** |
| Unit die lucht INBLAAST (toevoerkanalen naar woonkamer/slaapkamers), afvoer via roosters/schacht | **B — mech. toevoer** (zeldzaam) |
| Roosters in de kozijnen + **afzuigventielen** in keuken/bad/toilet + één afvoer-unit ("C-box", vaak zolder/keukenkast) | **C — mech. afvoer** (meest voorkomend na ±1975) |
| **Géén roosters in kozijnen**, wél ventielen voor toevoer ÉN afvoer + unit met **2 dikke buizen naar buiten/dak** | **D — balans/WTW** (nieuwbouw/renovatie na ±2000) |
| Mix van systeemdelen (bv. WTW in aanbouw + C in hoofdhuis) | **E — gecombineerd** |

**Herkenning C-box vs WTW-unit:** C-box = klein (≈30×30 cm), 1 afvoerkanaal naar dak, alleen afzuiging.
WTW = groter (≈60×60+), 4 kanaalaansluitingen (toevoer/afvoer × binnen/buiten), vaak filters-klepje +
merkplaatje (Zehnder/Brink/Itho). **Foto typeplaatje maken!**

## Stap 2 — Roosters herkennen (bepaalt het subsysteem!)
- **Zelfregelend (ZR)**: rooster met kunststof klep/membraan binnenin die bij winddruk dichtknijpt; vaak
  merk + type op de zijkant (Buva TopStream, Duco, Itho, Alusta). Type-opdruk = noteren + foto.
  → subsysteem "type onbekend, **zelfregelende klep aanwezig**" (bouwjaar rekenzone / geplaatst > 2003).
- **Niet-zelfregelend**: simpele klep/schuif zonder mechaniek (ouder werk, klepraampjes, klassieke
  schuifroosters) → A1/C1 "Standaard".
- **Drukgestuurd (Δp-klasse)**: alleen invullen bij documentatie/kwaliteitsverklaring van het rooster
  (A2a/C2a ≤1 Pa etc.) — anders niet claimen.
- In MagicPlan: per raam "Toevoerrooster aanwezig?" + type (ZR / niet-ZR / onbekend).

## Stap 3 — Sturing herkennen (de a/b/c-subcodes)
- **Standenschakelaar** (3 standen, keuken/bad) zonder sensoren → C1/tijdsturing-varianten.
- **Vochtsensor/badkamerboost** → nog steeds C1/C3 (tijd), géén CO₂.
- **CO₂-sturing**: sensor(tje) met LED in **woonkamer én hoofdslaapkamer** (of in de unit met
  ruimtesensoren) → C4/C5-varianten (c4c = de Nij Begun-upgrade-referentie); bij D: D3/D5.
  Zonering = per zone kleppen/meerdere boxen.
- Geen sturing zichtbaar + geen documentatie → "Standaard"-subsysteem kiezen (niet gokken).

## Stap 4 — Wat noteer je (MagicPlan Installaties-form)
Ventilatiesysteem A–E · subsysteem (conditionele lijst) · systeem individueel/collectief ·
Type WTW bij D/E (kruisstroom/tegenstroom/warmtewiel/enthalpie — staat op typeplaatje/documentatie) ·
foto ventilatie-unit + roosters (verplicht veld) · schimmel/vochtklachten (→ toelichting) ·
afzuigpunten keuken/bad/toilet aanwezig? · mogelijkheden kanalen/koofwerk (meters = cat-2!).

## Stap 5 — Ventilatie NA het isoleren (het advies)
Isoleren+kierdichten = minder infiltratie → ventilatie MOET kloppen (vuistregels: toevoer 0,7 dm³/s·m²
per verblijfsgebied, min 7 l/s per leefruimte; afvoer keuken 21 / bad 14 / toilet 7; balans; ≥50% van
buiten; geen afvoer in slaapkamers; >15 l/s onder deur → deurrooster). De tool rekent dit
(ventilatie/ventilatie.py) en tekent het ventilatieplan; rooster-l/s per raambreedte = ISSO-kleintje
(nog niet in de kennisbank — flag). Bestaand systeem A + isoleren → advies meestal ZR-roosters +
(indien nodig) mechanische afvoer C4c (catalogus V5).

## Snel-determinatie (zakkaart)
1. Unit? nee → **A**. 2. Unit alleen afzuiging (klein, 1 kanaal)? → **C**. 3. Unit met 4 kanalen,
geen kozijnroosters? → **D (WTW)**. 4. Inblaas zonder afzuig-unit? → **B**. 5. Mix? → **E**.
Daarna: roosters ZR? · sturing (standen/CO₂)? · typeplaatje-foto. Klaar.
