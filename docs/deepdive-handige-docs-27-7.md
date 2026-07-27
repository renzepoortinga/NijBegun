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

## 6. Nog te doen (niet in deze ronde)
- **ISSO-Referentiedetails** — onderbouwen de forfaitaire ψ-waarden (NTA bijlage I); koppelen aan onze
  detailpositie-lookup (punt D uit de NTA-analyse).
- **Praktijkboek Bouwfysica** — achtergrond voor de advieslogica (vocht/condensatie na na-isoleren);
  kan `engine/advies_text.py` verrijken.
- **ISSO Praktijkboek Energieprestatie** — praktijkcontext.
- **Voorbeeldplannen-map** — output 1-op-1 matchen aan de gold standard (staat al op de roadmap).
