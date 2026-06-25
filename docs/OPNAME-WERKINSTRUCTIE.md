# Opname-werkinstructie — MagicPlan, kamer voor kamer 🏠

> Doel: **snel en zonder klungelen** een woning opnemen, zó dat de tool er thuis automatisch
> de VABI-invoer + het Nij Begun-isolatieplan van maakt. Print dit of zet het op je iPad.

## Het idee in 3 zinnen
1. **MagicPlan meet de wanden, vloeren en m² automatisch** als je scant — die hoef je NIET na te meten.
2. Jij doet per kamer maar 4 dingen: **scannen · ramen/deuren toevoegen · de kamer benoemen · de buitenmuren benoemen**.
3. De rest (oriëntaties, begrenzing, isolatie) regel je via **namen** en een paar **projectvelden** — geen kompas-gepriegel per muur.

---

## De opzet (net als VABI) — 3 project-forms + per-element Fields
- **Form "Object"** = geometrie/identificatie (bouwjaar, woningtype, gevelhoogte, **Oriëntatie voorgevel**, dak, Ag, qv10, begrenzing-vloer).
- **Form "Constructies"** = isolatie/constructie-defaults (geveltype, thermische massa, spouw-dak, **Rc-bron per bouwdeel**).
- **Form "Installaties"** = ventilatie · verwarming · tapwater · koeling · zonne-energie · foto's.
- **Fields per element** = OVERSCHRIJVEN waar het afwijkt: op een **muur** ("Gevel per wand"), **vloer** ("Vloer"), **raam/paneel** ("Raam/paneel"), **deur** ("Deur").

## STAP 0 — Vooraf op kantoor (5 min)
Vul in de **"Object"**-form wat je nú al weet (projectniveau):
- Adres · **BAG VBO-id** · bouwjaar(klasse) · **woningtype** (vrijstaand/2-onder-1-kap/hoek/tussen).
- **Oriëntatie voorgevel** (N/NO/O/ZO/Z/ZW/W/NW) — kijk op de kaart welke kant de vóórgevel op wijst. **Dit is de truc**: hieruit leidt de tool de andere 3 gevels af (zie STAP 2).
- Opnamedatum · type advies (Basis/Detail).

---

## STAP 1 — De gouden volgorde PER KAMER ⭐
Doe in **elke** ruimte exact dit, dan vergeet je niks:

| # | Actie | Toelichting |
|---|---|---|
| 1 | **Scan de ruimte** | MagicPlan tekent de wanden + meet ze. Loop rustig rond; controleer dat de plattegrond klopt. **Niet handmatig nameten.** |
| 2 | **Voeg ramen & deuren toe** | Tik op de wand → raam/deur → meet **breedte × hoogte**. Dit is het enige dat je écht zelf meet. (zie snelheidstips onder) |
| 3 | **Benoem de ruimte** | Woonkamer / Keuken / Slaapkamer 1 / Badkamer / Toilet / Bijkeuken. De tool leidt hieruit de **ventilatiebalans** af. |
| 4 | **Benoem de buitenmuren** | Geef elke buitenmuur de naam **Voorgevel / Achtergevel / Linkergevel / Rechtergevel**. Een muur naar de buren (woningscheidend) laat je leeg of noem je `buurwand` → die valt automatisch buiten de schil. |

> **Binnenmuren** hoef je niet te benoemen — alleen muren die aan buiten (of een afwijkende ruimte) grenzen.

---

## STAP 2 — Gevelnamen & kompas (de grote tijdwinst) 🧭
Je benoemt gevels met hun **plek** (voor/achter/links/rechts), niet met een kompasrichting. De tool rekent
de oriëntatie zelf uit, op basis van **"Oriëntatie voorgevel"** (die je in stap 0 invulde):

- **Linker- en rechtergevel = gezien vanaf de straat**, kijkend naar de voorgevel.
- Voorbeeld: voorgevel op het **Zuiden** → rechtergevel = **Oost**, linkergevel = **West**, achtergevel = **Noord**.
- Zie het plaatje: [`docs/gevel-kompas.svg`](gevel-kompas.svg).

**Afwijkend / schuin huis?** Zet de richting er gewoon achter in de naam, bv. `Rechtergevel ZW`. Die override
wint van de afgeleide richting. (De tool toont na afloop de 4 afgeleide oriëntaties zodat je ze even checkt.)

---

## STAP 3 — OVERSCHRIJVEN waar een vlak afwijkt ⭐ (per-element Fields)
Je vult de normale waarden één keer in (Constructies/Object-form). Wijkt één muur/vloer/raam af? **Tik op dat
element** en vul de bijbehorende **Field** in — alleen het afwijkende veld:

| Element | Field-groep | Wat je kunt overschrijven |
|---|---|---|
| een **muur** | "Gevel per wand" | Oriëntatie · Isolatie aanwezig (+spouw/bouwjaar) · **Begrenzing (anders dan buitenlucht)** · Spouwdikte · **Isolatiedikte (mm)** · **Rc-bron** · Bron · **Rekenzone** |
| een **vloer** | "Vloer" | **Begrenzing** (kruipruimte/grond/AOR/…) · Isolatie · Isolatiedikte · Rc-bron · **Telt mee voor Ag?** · **Rekenzone** |
| een **raam/paneel** | "Raam/paneel" | Raam/Paneel · kozijn · glas · Begrenzing · Oriëntatie · Isolatiedikte · Rc-bron · Rekenzone |
| een **deur** | "Deur" | idem raam/paneel |

> **Jouw AOR-vloer uit de vorige opname:** tik op die vloer (of de ruimte erboven) → "Vloer"-Field → **Begrenzing = AOR**.
> De rest van de begane grond houdt de project-default (`Begrenzing (vloer)` in de Object-form). Twee vloervlakken, klaar.

**Snelle alternatieven via de naam** (handig tijdens het scannen; de tool leest deze ook):
`Achtergevel AOR garage` · `Kelderwand grond` · `Zijgevel ongeisoleerd` · `Voorgevel narekenen` (deels buiten/binnen) ·
`buurwand`/`AVR` (telt niet mee). Voor de oriëntatie is de naam (voorgevel/achter/links/rechts) sowieso de makkelijkste route.

---

## STAP 4 — Na alle kamers: de project-forms afmaken (1× invullen)
- **Form "Object"** — type dak + dakmaten/oriëntaties (of hellingshoek) · plat dak · Ag-aftrek zolder · qv10 (gemeten?) · `Begrenzing (vloer)` (default) · renovatiejaar.
- **Form "Constructies"** — geveltype · thermische massa wanden/vloeren · spouwdikte dak · **Rc-bron gevel / vloer / dak** (Opgemeten / Dikte onbekend / **Kwaliteitsverklaring**).
- **Form "Installaties"** — ventilatie · verwarming · tapwater · koeling · zonne-energie · foto's.

> **Kwaliteitsverklaring?** Kies bij Rc-bron "Kwaliteitsverklaring". De tool kiest dan een forfaitaire constructie
> én **vlagt het**, zodat jij in VABI `Invoer = Kwaliteitsverklaring` + de Rc/U-waarde invult. (De tool gokt nooit een Rc/U.)

---

## STAP 5 — Meerdere installaties (bv. 2 soorten zonnepanelen)
Heb je **meer dan één** van iets? Vul dan het tweede exemplaar in de genummerde velden:
- **PV:** `PV - …` voor systeem 1, `PV-2 - …` voor systeem 2 (paneeltype/aantal/oriëntatie/hellingshoek). De tool zet **alle** PV-systemen door naar VABI.
- **Verwarming/Tapwater/Koeling:** `Verwarming 2 - …`, `Tapwater 2 - …`, `Koeling 2 - …` (bv. hybride warmtepomp + cv-ketel). De tool zet exemplaar 1 volledig door en **vlagt** de extra, die je in Vabi toevoegt.

---

## STAP 6 — Foto-checklist 📷 (sectie FOTO'S in de Installaties-form)
Maak een foto alleen waar het onderdeel er is. Maak in elk geval:

**Woning algemeen** — vooraanzicht · huisnummer · elke gevel (voor/achter/links/rechts).
**Schil-details** — kozijn/glas (typeplaatje of detail) · kruipruimte · dak-/zolderisolatie · **isolatiedikte met duimstok**.
**Installaties** — typeplaatje cv-ketel/warmtepomp/boiler · ventilatie-unit · meterkast · PV-omvormer.
**Bijzonderheden** — asbestverdacht materiaal · vochtplekken · slechte bereikbaarheid (steiger/hoogwerker).

> Datum van de foto ≤ opnamedatum; herleidbaar (welk onderdeel). Dit voedt de foto-checklist + het BRL-projectdossier.

---

## Snelheidstips — minder nameten
- **Identieke ramen?** Meet er één en **kopieer** 'm; pas alleen af waar het verschilt.
- Gebruik **MagicPlan-presets** voor standaard deur-/raamhoogtes; corrigeer alleen de afwijkende.
- Scan eerst de **hele verdieping**, voeg dáárna pas de ramen/deuren toe (minder wisselen tussen modi).
- Benoem muren meteen tijdens de scan (lang-indrukken → hernoemen), dan hoef je later niet terug.

---

## STAP 7 — Thuis: de tool draaien & de oriëntaties checken 💻
```
python magicplan/statistics_csv.py --csv "… Statistics.csv" --straat .. --huisnummer .. --postcode .. --plaats ..
python vabi/generate_all.py --dossier out/dossier_csv.json
```
Lees de **"LET OP / nameten"-lijst**. Eén regel toont de **afgeleide gevel-oriëntaties** — controleer of die kloppen
(klopt het niet → pas "Oriëntatie voorgevel" aan, of override een gevel in de naam zoals `Rechtergevel ZW`).
Daarna importeer je in VABI: **Constructies → Objecten → Installaties** en druk je op **Rekenen**.

> Volledige A-tot-Z: [`docs/WERKWIJZE-A-TOT-Z.md`](WERKWIJZE-A-TOT-Z.md). Veldnamen: [`docs/magicplan-form-spec.md`](magicplan-form-spec.md).
