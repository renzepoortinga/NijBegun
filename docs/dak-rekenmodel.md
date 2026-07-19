# Definitief rekenmodel dak per daktype — Nij Begun/EPA-tool

**Status:** veldklaar referentiedocument. Conventies: `B` = overspanning loodrecht op de nok (m), `L` = maat evenwijdig aan de nok (m), `a` = hellingshoek t.o.v. horizontaal (graden), `F` = horizontale footprint die het dak OVERSPANT (m²). **Let op (gecorrigeerd 15-7):** dat is NIET automatisch de bovenste verdieping — die is vaak een **zolder binnen de kap** (Essenhage: zolder 22 m² terwijl het dak 44 m² overspande → dak kwam 63% te laag uit). De tool neemt daarom de verdieping **onder de zolder** zodra de bovenste duidelijk kleiner is (<70%), of het expliciet ingevulde `overspanning × noklengte` / `grondoppervlak dat het dak overspant`. Een **plat** dak blijft wél de bovenste verdieping, `h` = nokhoogte boven muurplaat/knieschot (m). Alle maten **binnenwerks** (ISSO 82.1 §8.2), oppervlakten op 2 decimalen.

**ISSO-anker (uit `docs/ISSO-82.1-opnameguide.md`):** hellingshoek ≤75° = dak, >75° = gevel; hellend dak ≥15°, plat dak <15° (§8.2.3). Dakoppervlak = meten, óf `fdak × vloeroppervlak onder dakvlak` (tabel 8.2: 0°=1,00 · 15°=1,04 · 30°=1,15 · 40°=1,31 · 45°=1,41 · 50°=1,56 · … · 75°=3,86; tussenwaarden interpoleren). **`fdak ≡ 1/cos(a)` exact** — ons `footprint/cos(a)`-model (`core/geometry.py: schuin_dakvlak_m2`) is dus 1-op-1 de ISSO-methode, geen benadering.

---

## (a) Rekenmodel per daktype

### 1. PLAT DAK (a < 15°)
```
A_dak = F_top  (+ hartmaat-opslag)
```
- **CSV-bron:** `Ground surface without walls` van de **bovenste niet-kelder-verdieping** — dit is wat de parser al doet (`magicplan/statistics_csv.py` r296: kolom `Ground surface without walls…`; r609–610: `top_fp` = laatste niet-kelder-vloer). **NIET** `Ground surface with all walls`: ISSO meet binnenwerks; "with all walls" ≈ buitenwerks en overschat het dak met de eigen-muurdikte-rand.
- **Hartmaat-correctie (ISSO §8.2, opslag +11 cm):** bij hoek-/tussenwoning de footprint-maat **loodrecht op elke gebouwscheidende wand** met +0,11 m verlengen: `ΔA = n_buurwanden × 0,11 × (lengte langs de buurwand)`. Vrijstaand: 0. **De tool past deze correctie NERGENS automatisch toe** (besluit 19-7-2026) — niet op de gevel én niet op de dak-footprint. Hij geeft er een luide *"ZELF TOEVOEGEN IN VABI"*-melding voor; de adviseur verwerkt de opslag zelf in VABI.
- Oriëntatie = **Horizontaal**; VABI Objecten-`Hellingshoek`-enum = **6** ("Dak plat"); begrenzing Buitenlucht (`vabi/objecten_generate.py` r153–156, r241–248).

### 2. ZADELDAK (symmetrisch, nok in het midden)
```
Per schuin vlak:   A_vlak = (B/2)/cos(a) × L          (2 vlakken; samen F/cos(a))
Nokhoogte:         h = (B/2) × tan(a)                  (boven muurplaat)
Kopgevel-driehoek: A_kop = 0,5 × B × h = 0,25 × B² × tan(a)   (per kopgevel; ×2)
Helling uit nok:   tan(a) = (nokhoogte − knieschothoogte) / (B_meet/2)
                   B_meet = breedte tussen de knieschotten (geen knieschot: volle vloerbreedte)
```
- **Kopgevel-driehoeken zijn GEVEL** (kind="gevel" in `dak_vlakken_zadeldak`), hellingshoek 90° (>75° = gevel per ISSO §8.2.3). Bij een knieschot is de kopgevel een **trapezium**: rechthoek `B × k` (knieschothoogte, meestal al in de MagicPlan-zolderwanden gemeten) + driehoek `0,5 × B_meet × h` erbovenop. **Dubbeltel-waarschuwing:** als MagicPlan de zolder-kopgevel al als wand meet, de auto-driehoek niet nogmaals optellen (flag, zie checks).
- **Oriëntaties:** dakvlak 2 = dakvlak 1 + 180° (`_opp8`); kopgevels = dakvlak 1 ± 90° (`_zij8`, statistics_csv r602–608). Rijwoning met nok evenwijdig aan de straat: dakvlakken = voor/achter, kopgevels = linker-/rechtergevel (bij tussenwoning zijn dat buurwanden → géén kopgevel-driehoek in de schil!). Dat volgt automatisch: buurwand-kopgevels niet als schildeel opnemen.
- Tussenwoning: vóór de cos-deling `L` met +0,11 m per buurwand verlengen (hartmaat).

### 3. LESSENAARSDAK (1 schuin vlak)
```
Dakvlak:            A_dak = F/cos(a)        oriëntatie = afwaterende richting
Hoogteverschil:     dh = B × tan(a)
Hoge-zijde-gevel:   A_hoog = L × dh          (rechthoek, oriëntatie = tegenover afwatering)
Zijgevel-driehoek:  A_zij = 0,5 × B × dh     (per zijgevel; ×2, oriëntaties ±90°)
Totaal extra gevel: dh × (L + B)
Helling uit meting: tan(a) = dh / B   (dh = hoog-laag muurplaathoogteverschil)
```
- Huidige code (`dak_vlakken_lessenaar`) levert alleen het dakvlak en zet een **note** dat de hoge-zijde-opstand bij de gevel hoort (statistics_csv r659). Bovenstaande formules maken dat automatiseerbaar: rechthoek + 2 driehoeken als gevel-vlakken toevoegen, met flag "verifieer in Vabi" (vaak zit de hoge gevel al deels in de MagicPlan-wanden).

### 4. SCHILDDAK / TENTDAK (4 vlakken, GEEN kopgevels)
**Gelijke helling a op alle zijden** (nok in het midden, noklengte `L_nok = L − B`):
```
Schuine hoogte:     s = (B/2)/cos(a)
Lang vlak (trapezium, ×2):  A_lang = ((L + L_nok)/2) × s = (L − B/2) × (B/2)/cos(a)
Kopschild (driehoek, ×2):   A_kop  = 0,5 × B × s = 0,25 × B²/cos(a)
Controle (exact):   2·A_lang + 2·A_kop = B×L/cos(a) = F/cos(a)
```
De huidige implementatie (`dak_vlakken_schilddak`: F/cos(a) **gelijk verdeeld** over de 4 oriëntaties, flag "verfijn in Vabi") is qua **totaal** exact; de trapezium/driehoek-formules hierboven geven de juiste **verdeling per oriëntatie** — aanbevolen upgrade, want oriëntatie stuurt de zonwinst.

**Afwijkende kophelling a_k ≠ a_l** (nu terecht geflagd, statistics_csv r647):
```
Nokhoogte:      H = (B/2) × tan(a_l)
Kop-inloop:     r = H / tan(a_k) = (B/2) × tan(a_l)/tan(a_k)
Noklengte:      L_nok = L − 2r     (moet ≥ 0; anders geometrie onmogelijk → fout)
A_lang (×2) = ((L + L_nok)/2) × (B/2)/cos(a_l)
A_kop  (×2) = 0,5 × B × r/cos(a_k)
```
Tentdak = schilddak met `L = B` → `L_nok = 0`, 4 driehoeken. **Geen verticale kopgevel-driehoeken** — dat is hét verschil met het zadeldak.

### 5. AFWIJKEND / SAMENGESTELD
Geen geometrie-magie: **9 directe m²-vakjes** `Dak m² N · NO · O · ZO · Z · ZW · W · NW · Horizontaal` (statistics_csv r733–742), elk → één `SchilDeel(type=dak)` met eigen oriëntatie; Horizontaal = plat (helling 0). ISSO §8.2 verbiedt samenvoegen bij verschil in oriëntatie/helling/Rc — dus per vlak apart. **SOBOLT-regel blijft leidend:** een direct ingevoerd `Dakvlak N - oppervlak (m²)` **wint altijd** van elke auto-berekening (r679–699).

---

## (b) Minimale conditionele veldenlijst per type (MagicPlan-form "Dak N", N=1..3)

| Veld | Plat | Zadel | Schild | Lessenaar | Afwijkend |
|---|---|---|---|---|---|
| `Dak N - type (leeg = geen dak N)` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `… plat - oppervlak (m², leeg = footprint bovenste verdieping)` | optioneel | — | — | — | — |
| `… zadel - oriëntatie dakvlak 1` *(vlak 2 en kopgevels auto ±90/180)* | — | **✓** | — | — | — |
| `… zadel - hellingshoek (°, leeg = berekend uit nok/breedte)` | — | ✓¹ | — | — | — |
| `… zadel - vloerbreedte / nokhoogte / knieschothoogte (m)` | — | ✓¹ | — | — | — |
| `… schild - hellingshoek lange vlakken (°)` | — | — | **✓** | — | — |
| `… schild - hellingshoek kopschilden (°, leeg = zelfde)` | — | — | optioneel | — | — |
| `… schild - oriëntatie lang dakvlak 1` *(rest auto)* | — | — | **✓** | — | — |
| `… lessenaar - oriëntatie dakvlak (afwaterend naar)` | — | — | — | **✓** | — |
| `… lessenaar - hellingshoek (°, leeg = berekend)` + hoog/laag-maten | — | — | — | ✓¹ | — |
| 9× `Dak m² <oriëntatie>` | — | — | — | — | **✓** |
| `Dakvlak N - oppervlak (m²)` *(directe m², wint altijd)* | overal optioneel als override | | | | |
| `Dakvlak N`-blok: isolatie Ja/Nee/Onbekend · dikte (mm) · Rc-bron · begrenzing | ✓ (alle typen, per dak N) | | | | |

¹ = óf de hellingshoek direct, óf de nok-meetset — één van beide verplicht, anders wordt het dak overgeslagen met note (huidig parser-gedrag, r637/650/663). Minimum per type: **Plat = 0 extra velden** (footprint-fallback) · **Zadel = 2** (oriëntatie + helling-of-nokset) · **Schild = 2** · **Lessenaar = 2** · **Afwijkend = ≥1 m²-vakje**.

---

## (c) Dakkapel — wat de bronnen ECHT zeggen

**In de repo gevonden ISSO-regels:**
1. **§7.1.2** (opnameguide r209/238): dakkapellen en uitbouwen tellen **niet mee voor het daktype** van het hoofdgebouw (hellend/deels plat/plat).
2. **§8.2.1** (opnameguide r273): "**Zijwangen dakkapel zonder kozijn = gesloten gevel**; met [kozijn → paneel-in-kozijn — de brontekst is in de guide afgekapt, verifieer de rest in ISSO 82.1 zelf]".
3. **§8.2** (r267/319): vlakken met verschillende oriëntatie/helling/Rc **mogen niet worden samengevoegd** → dakkapelvlakken zijn per definitie aparte vlakken.
4. `docs/NTA8800-opname-MASTERPLAN.md` §4.2 bevestigt: voorgevel + 2 zijwangen = **gesloten gevel**, plat dakje = **dak** (verwijst naar ISSO §8.2.1 p.69).

**Een "<2%-verwaarloosbaarheidsregel" voor dakkapels staat NERGENS in de repo-docs** (gegrept op 2%/verwaarloos/samenvoegen in alle docs). Die regel dus **niet toepassen en niet claimen** — golden rule: niet verzinnen. Conservatieve werkwijze (deels al in `core/geometry.py: dakkapel_vlakken`):

```
Invoer: breedte B_k × hoogte H_k × diepte D_k + oriëntatie (erft van dakvlak)
Voorvlak:   kozijnwerk (raam) apart opmeten; rest = gesloten gevel op dakkapel-oriëntatie
Zijwangen:  2 × D_k × H_k = gesloten gevel (zonder kozijn), oriëntaties ±90°
Dakje:      B_k × D_k = plat dak (helling <15° → Horizontaal)
Gat in schuin dakvlak: A_gat = (B_k × D_k)/cos(a)   ← AFTREKKEN van het schuine vlak
```
De huidige code **verwaarloost het gat bewust** (geometry.py r95–96: "adviseur verifieert in Vabi") — dat overschat het schuine dak met `B_k·D_k/cos(a)` én telt het kapel-oppervlak dubbel. Advies: gat-aftrek toevoegen zodra de kapelmaten bekend zijn, en **altijd flaggen** ("dakkapel verwerkt: voorvlak/wangen=gevel, dakje=plat dak, gat afgetrokken — verifieer in Vabi"). Meerdere identieke kapellen op hetzelfde dakvlak mogen als n× dezelfde set (zelfde oriëntatie/Rc), anders apart.

---

## (d) Validatiechecks (voor `vabi/sanity.py` / parser-notes)

1. **Projectie-sluitcheck (som dakvlakken vs footprint):** `Σ A_i × cos(a_i)` (plat: `A_i × 1`) moet de top-footprint dekken. Flag als `< 0,95 × F_top` ("dak dekt de plattegrond niet — vlak vergeten?") of `> 1,10 × F_top` ("dak groter dan plattegrond — dubbeltelling/overstek? ISSO meet binnenwerks, oversteken tellen niet"). Kopgevel-driehoeken (kind=gevel) buiten deze som houden.
2. **Hellingsgrenzen (ISSO §8.2.3 — LET OP, niet 10–75°):** hellend dak geldig bij **15° ≤ a ≤ 75°**. `a < 15°` → volgens ISSO een **plat dak**: automatisch als plat behandelen + note (10–14° komt voor bij flauwe lessenaren). `a > 75°` → dit vlak is een **gevel**: blokkeren als dakvlak, herclassificeren + flag. Praktische plausibiliteitsband voor woningkappen: 15–65°; daarbuiten extra "nameten"-flag.
3. **fdak-kruischeck:** `1/cos(a)` moet binnen 1% op de geïnterpoleerde tabel-8.2-waarde liggen (15°=1,04 · 30°=1,15 · 45°=1,41) — regressietest op het rekenmodel zelf.
4. **Nok-consistentie:** als én de directe hellingshoek én de nokset zijn ingevuld: `|a_direct − atan((nok−knie)/(B_meet/2))| ≤ 5°` (ISSO-controletolerantie, opnameguide r361), anders flag "helling en nokmaten spreken elkaar tegen".
5. **Kopgevel-dubbeltelling (zadeldak):** als MagicPlan op de zolderverdieping wanden op de kopgevel-oriëntatie meet én de tool een kopgevel-driehoek toevoegt → flag "controleer dubbeltelling zolderkopgevel". Tussenwoning: kopgevels aan buurwand → géén driehoek toevoegen.
6. **Schilddak-geometrie:** `L_nok = L − 2r ≥ 0` vereist (afwijkende kophelling), anders fout "kophelling te flauw voor deze plattegrond"; kophelling ≠ langshelling blijft geflagd tot de trapezium/driehoek-verdeling is geïmplementeerd.
7. **Oriëntatie-plicht (ISSO §8.5):** elk hellend dakvlak grenzend aan buitenlucht heeft een oriëntatie N..NW; plat = Horizontaal (VABI-enum 6, hellend = 3 — `objecten_generate.py` r153). Ontbreekt → dak overslaan + note (huidig gedrag, correct).
8. **Samenvoegverbod (ISSO §8.2):** nooit dakvlakken mergen bij verschil in oriëntatie, helling, begrenzing of Rc/isolatie — geldt ook voor dakkapeldakjes en de 9 Afwijkend-vakjes.
9. **Plat-dak-bron:** als `Dak N plat`-oppervlak leeg is en de footprint-fallback wordt gebruikt bij N>1 → note "klopt de footprint voor dit dakdeel?" (bestaat al, r624–626); nieuw: note als hartmaat-opslag bij hoek-/tussenwoning nog niet op het dak is toegepast.

**Relevante bestanden:** `core/geometry.py` (rekenfuncties) · `magicplan/statistics_csv.py` r582–749 (dak-parsing, Dak N-model) · `vabi/objecten_generate.py` (Hellingshoek-enum 3/6, Daktype 0/1/2) · `docs/ISSO-82.1-opnameguide.md` r282/273/209 · `docs/NTA8800-opname-MASTERPLAN.md` §4.2 · `docs/magicplan-opname-howto.md` stap E.