# Deep dive "Handige docs Nij Begun" — bevindingen 27-7-2026

Bronnen (bureaublad `Handige docs Nij Begun`): Maatregelencatalogus Q3-2026 · ISSO 82.1 (7e druk) ·
Startpakket Isolatieadviseur maart 2026 · Proces isolatieplannen · Opdrachtbrief 2026 ·
ISSO Praktijkboek Energieprestatie · Praktijkboek Bouwfysica · ISSO-Referentiedetails · Voorbeeldplannen.

---

## 1. 🔴 FACTURATIE-BUG (geld) — opgelost
**Startpakket, "Woningtypen en tarieven":**
> Basis = voor woningen gebouwd **vanaf 1 januari 1945** · Uitgebreid = voor woningen gebouwd
> **vóór 1 januari 1945**. *"Let op: Het bouwjaar bepaalt of het B of U tarief van toepassing is en
> niet de kwalificatie van de adviseur!"*

De webapp leidde `uitgebreid` af uit **`opname.type_advies`** (Basis/Uitgebreid/Label = de
kwalificatie). Een tussenwoning van vóór 1945 met een "Basis"-opname werd dus op **€350** gezet
i.p.v. **€425** — €75 mis per plan, structureel.
**Fix:** `voorschot.uitgebreid_uit_bouwjaar()` (<1945 → U). Onbekend bouwjaar → `None` + vlag
`bouwjaar_onbekend` i.p.v. gokken. Tests toegevoegd.

**Tarieven (excl. btw), B / U:**
| Woningtype | Basis (≥1945) | Uitgebreid (<1945) |
|---|---|---|
| Vrijstaand > 300 m² | 750 | 825 |
| Vrijstaand ≤ 300 m² | 625 | 700 |
| 2-onder-1-kap / hoekwoning | 500 | 575 |
| Tussenwoning | 350 | 425 |
| Meergezinswoning | 325 | 400 |
| Repeterende woning | 250 | 325 |

## 2. 🔴 INDIENROUTE klopte niet — opgelost
De Guide zei "dien in via **leveranciers@nijbegun.nl**". Volgens **Proces isolatieplannen** gaat het via
**Teams**: upload in je **eigen kanaal → tabblad Bestanden**. Vooraf vul je het **Excel-overzicht** op je
kanaal aan (postcode · huisnummer · datum woningopname · woningtype) — *"op basis van deze informatie
kan de officiële opdracht worden verstrekt"*. Guide-tekst herschreven.

**KWACO-statussen (5, wij kenden er 2):**
| Status | Actie adviseur |
|---|---|
| Beoordeling | geen actie |
| **Retour** | aanpassen + uploaden met **zelfde bestandsnaam + "V2"** |
| **Herbeoordeling** | die status zet je **zelf** na het uploaden |
| **Akkoord na opmerkingen** | aanpassen, **niet** terug naar kwaco, direct naar bewoner — én het aangepaste plan in Teams **én in de woningdatabase** |
| Akkoord | plan zelf downloaden en naar de bewoner sturen |

Verder: **reageer binnen 3 werkdagen** op verzoeken; controle is een **tweetrapscontrole**, eerst 100%,
daarna steekproef (en terug naar 100% bij kwaliteitsverlies); bewoner heeft recht op **één gratis
opname + plan** per woning.

## 3. 🟠 Catalogus Q3-2026 — bijgewerkt
Onze `catalog.json` stond op **Q2 (3-6-2026)**, bureaublad had **Q3 (21-7-2026)**. Verschil: **geen**
maatregelen toegevoegd/vervallen, **6 prijswijzigingen**:
- **V1-1-X12 "Natuurvrij maken bij spouwisolatie" is VERVALLEN** (prijs → 0; catalogus verwijst naar
  X13/X14). Geen risico: `measure_engine.EXCLUDE` bevat `"natuurvrij"`, dus deze codes worden nooit
  automatisch voorgesteld (besluit: alleen melden via `core/gedoogbeleid.py`).
- **V1-1-X13..X17 geïndexeerd +3,1 %** (gedoogbeleid/eDNA).
Parser-regex snapte het nieuwe bestandsnaamformaat niet → gaf `versie: onbekend`; gefixt.

## 4. 🟡 ISSO 82.1 — zolder & Ag (raakt de MagicPlan-werkwijze)

**Zolder (§6.3.3):** een **beloopbare zolder ≥ 1,5 m die met een vaste trap bereikbaar is, behoort
per definitie tot de thermische zone.** Een **vlizotrap telt niet** als vaste trap. Zonder vaste trap:
via de beslisschema's 6.3a–c bepalen.

**Knieschot-regel (belangrijke nuance die wij nog niet expliciet hadden):**
- Zijn de **knieschotten én de vloer erachter geïsoleerd** én is hun Rc **groter** dan die van het
  achterliggende dak/de gevel → de ruimte achter het knieschot valt **buiten** de thermische zone (AOR).
- **In alle andere gevallen** hoort **de hele zolder inclusief de ruimte achter de knieschotten** bij
  de thermische zone → de **thermische schil is dan het DAK tot de dakvoet**, niet het knieschot.

> Praktisch: de **1,5 m-lijn** bepaalt alleen de **Ag** (§7.2.1). De **schil** (welk vlak je als dak
> opgeeft) is een aparte vraag en volgt de knieschot-regel. Onze dak-berekening gebruikt de footprint
> van de verdieping **eronder** → dat is het volledige dakvlak tot de dakvoet, dus consistent met de
> hoofdregel. ✅

**Ag-regels (§7.2.1) die de adviseur moet kennen** — meet tussen de opgaande scheidingsconstructies;
niet meetellen: vloerdelen met netto hoogte **< 1,5 m**; **trapgat/vide ≥ 4 m²**; liftschacht;
**dragende binnenwand**; vrijstaande constructie ≥ 0,5 m²; leidingschacht ≥ 0,5 m². Wél meetellen:
vloer **onder** de trap, open haard, keukenkastjes/aanrecht.
**Bouwlaag** = hoogte op **enig punt** ≥ 1,5 m.

**Werkwijze zolder in MagicPlan (advies):** teken de zolder als eigen verdieping en trek de wanden
**op de 1,5 m-lijn** (dupliceer de verdieping eronder en schuif de wanden naar binnen). Dan klopt Ag
automatisch én bestaat de ruimte als **kamer** → hij verschijnt in het **ventilatieplan**. Geef die
zolderwanden **géén gevelnaam/oriëntatie** (ze zitten onder het dak; anders dubbeltelling met het
dakvlak uit de webapp-wizard).

---

## 5. 🟠 Voorbeeldplannen: goedgekeurde plannen hebben 7 bijlagen, ons template 3

**Gold standard** (`Voorbeeldplannen/Voorbeeld isolatieplan bouwjaar 1970.pdf`, 22 p.):
1. Een isolatieplan speciaal voor jouw huis
2. Isolatieplanformulier (1 Gegevens · 2 Subsidiabele maatregelen · 3 Huidige woningstaat ·
   4 Prijsopbouw per maatregel)
3. Inhoud maatregelen en technische haalbaarheid toegelicht
**Bijlage 1** Waarom ventileren? · **2** Vergunningen · **3** Foto's van opname ·
**4** Informatie over dit isolatieplan · **5** Voorgestelde maatregelen in beeld ·
**6** Ventilatieplan · **7** Detailtekeningen

**Ons template** (`templates/isolatieplan_template.docx`, officieel 23-04-2026) bevat **alleen
bijlage 1–3**. Bijlage 6 (ventilatieplan-SVG) en de haalbaarheidsbijlage maken wij wél, maar als
**losse bestanden** — in de goedgekeurde plannen zitten ze **ín het document**.

**Wat bijlage 4–7 bevatten (uit het voorbeeldplan):**
- **4 — Informatie over dit isolatieplan**: standaardtekst. Berekend met standaard energieverbruik en
  bewonersgedrag; investeringskosten uit de **Groninger Maatregelen Catalogus**, ontbrekende bedragen
  via **kostenkengetallen.rvo.nl**; energietarieven van **Milieu Centraal** (per kwartaal bijgewerkt);
  alles **incl. 21 % btw**. Plus een uitleg over **koudebruggen** (condensatie/schimmel na isoleren).
- **5 — Voorgestelde maatregelen in beeld**: schets van de woning met daarop de maatregelen én de
  potentiële koudebruggen; te vervangen ramen **blauw gearceerd**.
- **6 — Ventilatieplan**: hebben wij al (SVG).
- **7 — Detailtekeningen**: genummerde constructiedetails ("Detailtekening 1", …) — dit is precies het
  **constructieblad** uit `docs/constructie-rc-tool-verkenning.md`, en sluit aan op de
  ISSO-Referentiedetails (zelfde detailnummering als NTA bijlage K).

**Actie:** vraag bij Nij Begun na of er een **nieuwer officieel template** is (met bijlage 4–7), of
voeg de bijlagen bij het indienen samen tot één document. Toegevoegd aan de **indien-check** in de
webapp zodat het niet vergeten wordt. *Niet zelf de M29-lay-out aanpassen — dat is een
Beoordelingsformulier-eis.*

## 6. 🟢 Praktijkboek Bouwfysica → advieslogica verrijkt

Onze begeleidende tekst noemde vocht/schimmel alléén bij ventilatie. De Nij Begun-eis "technische
haalbaarheid" vraagt expliciet om **dampremmende laag · ruimtefunctie onder een koud dak · ventilatie**.
Toegevoegd in `engine/advies_text.py` (`_BOUWFYSICA`, per bouwdeel A–E):

**Kernregel uit het Praktijkboek:** een **dampremmende laag hoort altijd aan de WARME (binnen)zijde**
van de isolatie — ligt hij aan de koude zijde, dan ontstaat **inwendige condensatie** in de constructie.

- **A gevel** — binnenisolatie: dampremmer aan de binnenzijde; let op **balkkoppen** (houten vloerbalken
  die in de gevel liggen kunnen gaan rotten als ze in de koude zone belanden). Spouwisolatie: eerst
  vochtdoorslag + open stootvoegen beoordelen.
- **B glas/kozijn** — kierdichting verlaagt de natuurlijke toevoer → ventilatie borgen.
- **C vloer** — vochtige kruipruimtelucht geeft inwendige condensatie; goed geventileerde kruipruimte +
  dampremmer aan de warme zijde.
- **D dak** — binnenzijde isoleren: dampremmer aan de warme zijde, **ventilatiespouw boven de isolatie
  openhouden**, let op de ruimtefunctie onder een koud dak (slaapkamer = meer vochtproductie).
- **E ventilatie** — toe- en afvoer in balans + overstroom; afzuiging zonder toevoer trekt vocht/koude
  via kieren naar binnen.

**ISSO-Referentiedetails** (studenteneditie): gebruikt dezelfde detailnummering als NTA bijlage K
(`101.0.1.01` enz.) en levert per detail de **ψ-waarde en f-factor**. Dit is de onderbouwing onder de
forfaitaire ψ-tabel (NTA bijlage I) én de bron voor **Bijlage 7 Detailtekeningen**. Nog niet gewired —
zie punt D van `nta8800-analyse-vs-tool.md` (ψ-lookup) en de constructieblad-verkenning.

## 7. 🟢 ψ-lookup gebouwd → voedt Bijlage 7 (afgerond)

`engine/psi_lookup.py` bevat nu de forfaitaire ψ-waarden uit **NTA 8800 bijlage I**: tabel **I.1**
(laagbouw, detailpositie 1–24) en **I.2** (gestapeld, 50–74), met **kolom A** (aanvullende voorwaarden
gehaald) en **kolom B** (niet), plus de **0,50-default** voor een ontbrekende detailpositie.
`relevante_details(dos)` leidt uit de opname af welke details voorkomen (gevel · kozijn · hellend dak ·
dakraam · dakkapel · woningscheidende wand, of de gestapelde tegenhangers).

Dit is een **lookup van normwaarden** — de tool rekent nog steeds geen transmissie. Belangrijk: de norm
koppelt deze waarden aan **nieuwbouw-Rc**, dus ze horen bij de **toekomstige staat** (na de maatregelen)
— precies waar bijlage 7 over gaat. De nummering komt overeen met de **ISSO-Referentiedetails**.

## 8. 🟢 Bijlage 4–7 in de plan-output (afgerond)
`fill_template` zet bijlage 4 t/m 7 nu **achter** de bestaande inhoud, zodat het plan de structuur van
de goedgekeurde voorbeeldplannen volgt. **Puur additief** — de M29-lay-out van het template zelf blijft
ongemoeid (Beoordelingsformulier-eis). Bijlage 5 en 7 laten ruimte voor de schets resp. de
detailtekeningen; bijlage 7 vermeldt per detail de ψ-waarde (A/B) en de voorwaarde.

## 9. 🟢 ISSO-Praktijkboek Energieprestatie → inmeetgids aangevuld
Praktijktrucs voor het vaststellen van de **isolatiedikte** (die stuurt de Rc, dus het label):
**prikpen** voor zachte isolatie · **boorgaten op de kruisingen van de stootvoegen** = na-isolatie in
de spouw · **dikte meten in de dagkant nabij een kozijn** en de bekende lagen eraf trekken ·
**dakluik** voor de dakdikte · bij **dakramen letten op de opstaande randen** · **reflecterende folie
telt alleen bij spouw ≥ 20 mm** · niet meetbaar → *dikte onbekend* + bouwjaarklasse, nooit gokken ·
kwaliteitsverklaring → **BCRG-code** (niet elke DoP staat in de BCRG-databank).
Toegevoegd als §6 in `docs/magicplan-inmeetgids.md`.

## 10. Nog te doen
- Bijlage 5: de **schets** van de woning met maatregelen + koudebruggen automatisch genereren
  (nu een tekstplaceholder).
- Bijlage 7: de **detailtekeningen** zelf (nu alleen de detaillijst met ψ) — sluit aan op de
  constructieblad-verkenning.
