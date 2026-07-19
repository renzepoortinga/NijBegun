# Nij Begun & Energielabel — werkstroom met de tool

Twee paden, één opname. De tool levert VABI-invoer; **Vabi EPA-W blijft de geattesteerde rekenkern**
(gouden regel — wij rekenen NTA 8800 nooit zelf). De Standaard is géén vast getal: VABI rekent hem
per woning (geometrie/compactheid).

## Pad 1 — Energielabel (volledig)
> **BRL 9500-W-procesketen (buiten de tool, alleen dit pad).** Vóór de techniek: (0a) opdracht +
> **opname-soort** kiezen — *basis (EP-W/B)* óf *detail (EP-W/D)*; **toets Bbl/oplevering → detail
> verplicht**, bestaande woning → keuze (BRL §4.2.2). (0b) opdrachtgever schriftelijk informeren. Ná de
> berekening: **registreren in EP-Online binnen 3 mnd** na opnamedatum (juiste software-versie; opnemende +
> registrerende adviseur), **levering pas na registratie**, en het **projectdossier** (BRL Bijlage 3,
> **15 jaar** bewaren). Volledig: `docs/BRL-9500W-proceshandleiding.md` + `docs/projectdossier-checklist-bijlage3.md`.
> **Pad 2 (Nij Begun) heeft deze registratie-/dossierplicht NIET.**
>
> **Basis vs detail (gevolg voor invoer):** bij **detailopname** moeten Rc/U/g **onderbouwd** zijn met
> DoP/BCRG-kwaliteitsverklaring/opgemeten dikte — *niet* de forfaitaire bouwjaar-constructies die de tool
> standaard kiest; de adviseur vervangt + onderbouwt dit in Vabi + projectdossier.

1. MagicPlan-opname → export **Statistics-CSV** (+ Report-PDF).
2. `python magicplan/statistics_csv.py --csv "...Statistics.csv" --straat .. --huisnummer .. --postcode .. --plaats ..`
   → dossier; dan `python vabi/generate_all.py --dossier <dossier>` → 3 bibliotheken in `out/vabi_import/`.
3. EPA: **nieuw project → Algemeen: Objecttype=Woning, Bouwfase=Bestaande bouw, Opname=Basisopname
   EERST invullen** (anders weigert de objecten-import op metadata-mismatch). Dan importeren in de
   volgorde **Constructies → Objecten → Installaties**. Daarna **Rekenen**.
   > Geverifieerd 15-6 + **23-6-2026 (objecten-fix)**: alle 3 bibliotheken importeren foutloos in EPA 12.0.1
   > en de gevels staan correct per oriëntatie. De objecten-"Enum mismatch" is opgelost (Gebruiksoppervlakte-
   > enum + sjabloon-versie 12.0.1 + deterministische guids; zie `vabi/refs/grenstaan_mapping.md`). Gebruik de
   > verse bestanden in `out/vabi_import/` (niet oude exports).
4. Controleer/verfijn waar geflagd (gevel-volledigheid, dak-vlakken, installatie-enums); meld af.

## Pad 2 — Nij Begun isolatieplan (Maatregel 29)
Voor Nij Begun is de **volledige installatie niet nodig** — alleen **ventilatie** (+ de schil). De
keten:

```
opname ─► dossier ─► [HUIDIGE STAAT naar VABI] ─► VABI rekent ─► resultaat eruit
                                                                      │
                          ┌───────────────────────────────────────────┘
                          ▼
   engine kiest goedkoopste maatregelpakket  ─► [TOEKOMSTIGE STAAT naar nieuw VABI-bestand]
                          │                         (zelfde import, mét maatregelen verwerkt)
                          ▼
              VABI rekent ná maatregelen ─► Standaard gehaald?  ── nee ─► pakket uitbreiden
                          │ ja
                          ▼
        alles doorzetten in Nij Begun isolatieplan-template (Word) + ventilatieberekening + foto's
```

### Stap voor stap
1. **Huidige staat → VABI** (`generate_all`). VABI levert: huidige netto warmtebehoefte (kWh/m²·jr)
   + de **Standaard-eis** voor déze woning + maximaal warmteverlies. *Deze huidige staat hoort ook
   in het rapport (tool-eis 6b/c)* — de tool leest het VABI-resultaat terug (monitor/export) en zet
   het in V1–V6 + de warmteverlies-sectie.
2. **Maatregelen** (engine): kies het pakket met de **laagste investeringskosten** dat de Standaard
   haalt (tool-eis: 100% van de plannen halen de Standaard; 90% gelijk aan referentiepakket).
3. **Toekomstige staat → nieuw VABI-bestand**: genereer opnieuw de 3 bibliotheken, maar met de
   maatregelen verwerkt in de schil (hogere Rc, betere beglazing) + aangepaste ventilatie. Importeer
   in een **nieuw EPA-bestand** en reken na → bevestig dat de Standaard gehaald wordt.
4. **Indien gehaald** → vul de Nij Begun isolatieplan-template (Word) + ventilatieberekening + balans
   + bijlage "Waarom ventileren" + foto-checklist. Validator checkt compleetheid vóór indienen.

## Luchtdichtheid ná maatregelen — QV10 of renovatiejaar
Isoleren tot de Standaard **verhoogt de luchtdichtheid** → de infiltratie (qv;10) in de toekomstige
berekening moet kloppen, anders reken je de Standaard verkeerd. In NTA 8800/VABI zijn er twee routes:

**BEVESTIGD via ISSO 82.1, 7e druk §7.1.4–7.1.5 (Tabel 7.2 + Afb. 7.3 beslisschema):**
- **Er is GEEN vast qv;10-getal.** Twee routes:
  - **(a) Gemeten** met blowerdoortest → die qv;10-waarde [dm³/(s·m²)] handmatig invoeren.
  - **(b) Niet gemeten** → VABI berekent de infiltratie forfaitair op basis van **bouwjaar óf renovatiejaar**.
    Dus de "1.iets" is geen voorschrift; het is de forfaitaire uitkomst per jaarklasse (VABI rekent 'm).
- **Renovatiejaar mag je gebruiken** alleen bij aantoonbare **energiebesparende bouwkundige maatregelen**
  (met schriftelijk bewijs: facturen/tekeningen):
  - dak óf zoldervloer geïsoleerd;
  - kierdichting muur/kozijn met **flexibele, uitzettende afdichting** (bijv. uitzetband) — *alleen afkitten
    volstaat niet*;
  - gevel na-geïsoleerd via spouwmuurisolatie of geïsoleerde voorzetwand (dagkanten mee-geïsoleerd, naaddicht).
  - Meerdere onderdelen in verschillende jaren → **het jaar van het dak is leidend** (geen dak: gevel;
    kozijn+gevel verschillend: oudste jaar).
  - **Renovatiejaar onbekend** → eerste jaar van de volgende hogere jaarklasse t.o.v. het bouwjaar.
  - Jaarklassen: J<1970 · 1970–1980 · 1980–1990 · 1990–2000 · 2000–2010 · J≥2010.
- **Voor het Nij Begun-isolatieplan (toekomstige staat):** na de maatregelen (incl. kierdichting/na-isolatie)
  is de verdedigbare route **renovatiejaar = jaar van de maatregelen** → VABI rekent de forfaitaire qv;10.
  Een handmatige qv;10 alleen bij een blowerdoormeting.

De tool ondersteunt beide: `dossier.opname.qv10_waarde` (gemeten → Qv10Gemeten=1) óf `dossier.identificatie.renovatiejaar`.

## Woningscheidende wand / woningpositie (geverifieerd tegen ISSO 82.1, 7e druk)
De **woningpositie** heeft **twee losse effecten** — beide volgen uit één veld
`dossier.identificatie.woningtype`:

**(A) Infiltratie (ISSO §7.1.1 + §7.1.5).** De woningpositie bepaalt de forfaitaire infiltratie;
**VABI rekent dit zelf** uit het Subtype. Posities (ISSO §7.1.1.2): Vrijstaand · Twee-onder-één-kap ·
Tussenwoning (grenst aan ≥2 buren) · Hoekwoning (grenst aan 1 buur). → alleen het woningtype
opgeven, niets optellen.

**(B) Gevel-oppervlakte hart-op-hart (ISSO §8.2).** Horizontale gevelafmetingen meet je
binnenwerks, **maar tot de hartmaat van de gebouwscheidende wand**. Is de dikte niet meetbaar:
tel **+0,11 m per gebouwscheidende wand** bij de gevelbreedte (hoek +0,11; tussen +0,22 = 2×0,11;
uitgangspunt wand = 22 cm). Die breedte geldt voor de **voor- én achtergevel**, dus de totale
gevel-toeslag is **2 × n × 0,11 × gevelhoogte**:
- **Tussenwoning:** 0,44 × gevelhoogte · **Hoekwoning:** 0,22 × gevelhoogte · **Vrijstaand:** 0.

**De tool past (B) BEWUST NIET automatisch toe** (besluit Renze 19-7-2026): de verdeling van de
toeslag over de juiste gevels bleek te foutgevoelig om altijd goed te doen. In plaats daarvan geeft
de tool één **luide melding** met de geschatte m² — *"HART-OP-HART GEVEL-TOESLAG (ISSO 8.2) — ZELF
TOEVOEGEN IN VABI"* — in beide parser-paden (`magicplan/statistics_csv.py` + `magicplan/assemble.py`).
De adviseur zet de toeslag zelf op de voor- én achtergevel in VABI. `core/geometry.py:
woningscheidende_wand_toeslag_m2` bestaat nog, maar levert alleen de geschatte m² vóór die melding.
> Verticaal geldt analoog (ISSO §8.2): scheidingsvloer +0,10 m per laag (tussenlaag +0,20 = 2×0,10;
> uitgangspunt vloer = 20 cm) — relevant bij meerdere bouwlagen/rekenzones.
> NB: de gevel-basis is nu nog `omtrek × hoogte` (party-walls nog niet uitgefilterd) → adviseur
> verifieert de gevel-m² in Vabi; exacte per-wand-geometrie komt met de echte MagicPlan-export.

**Nog in MagicPlan toe te voegen (projectniveau):**
1. **Woningtype** (List): Vrijstaand · Twee-onder-één-kap · Tussenwoning · Hoekwoning.
2. **Gevelhoogte (m)** (Number) — anders pakt de tool de gebouwhoogte uit de plattegrond.
3. *(optioneel)* **Gevel al tot hartmaat gemeten? (Ja/Nee)** — Ja zet de hart-op-hart-toeslag uit.

> De **tool-kant leest deze velden al** (parser `magicplan/statistics_csv.py`): Woningtype,
> Gevelhoogte (m), Renovatiejaar én Thermische massa wanden/vloeren stromen automatisch in het
> dossier zodra ze in de form staan (CLI-arg `--woningtype/--gevelhoogte` overrulet het veld).
> De **exacte veldnamen + dak-velden + per-element-eisen** staan in
> [`docs/magicplan-form-spec.md`](magicplan-form-spec.md). Thermische massa: **Licht(0)/Zwaar(1)/Zeer
> zwaar(2) zijn nu alle drie LIVE in EPA bevestigd** → automatisch gezet (golden rule gehandhaafd; eerder
> alleen Zwaar bevestigd, nu alle drie via probe + objecten-import-bisectie).

> **Installaties-form (gepubliceerd):** naast "Schil & zone" is er nu een conditionele **"Installaties"**-form
> (ventilatie + verwarming + koeling + tapwater + uitgebreide PV/zonne-energie + accu) met **7 foto-velden**.
> De parser leest alle velden. Zie `docs/installaties-invoermodel-ISSO.md` voor het volledige veldmodel.

## Status van de bouwstenen
- ✅ Opname → dossier (MagicPlan hybride).
- ✅ Dossier → 3 VABI-bibliotheken, **importeren foutloos** (constructies/objecten/installaties).
- ✅ Isolatieplan-template-vulling, ventilatieberekening, foto-checklist, validator (bestonden al).
- 🔜 Teruglezen VABI-resultaat (huidige + na maatregelen) → rapport; toekomstige-staat-generatie met
  maatregelen verwerkt; qv;10-automatiek.
