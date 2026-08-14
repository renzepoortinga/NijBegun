---
id: 008
assigned: claude
branch: fix/dak-wizard-erft-standaard
depends_on: []
---

<!-- De map ís de status: backlog/ ready/ active/ done/. Geen status-veld hier. -->

# Task 008 — Alle dak-wizards erven de Constructies-DAK-standaard + bouwjaarklasse/rc_bron in de editor

## Goal
`docs/magicplan-velden-audit.md` bevinding D constateerde op 27-7 dat de dak-wizard alleen
geometrie uitvraagt en `isolatie_aanwezig="Onbekend"` hardcodeert, en dat bouwjaarklasse/rc_bron
per dakvlak ontbraken in de editor. Bij het narechecken bleek de helft al gefixt: het PLATTE
dak (`opname_dak_plat`) erft `dos.opname.dak_standaard` (de MagicPlan Constructies-DAK-form) al
sinds die datum. De zadeldak- (`opname_dak_driehoek`) en freeform-wizard (`opname_dak_negen`)
deden dat niet — die hardcodeerden nog steeds `isolatie_aanwezig="Onbekend"` zonder de standaard
te raadplegen, en droegen ook geen bouwjaarklasse/rc_bron. En de generieke "gebouwboom"-editor
(voor élk vlak, niet alleen dak) had geen velden om bouwjaarklasse/rc_bron per vlak te zetten of
te corrigeren. Dit rondt bevinding D volledig af.

(Bevinding C uit hetzelfde document — woningtype dekt alleen grondgebonden — bleek bij het
narechecken AL volledig opgelost: `WONINGTYPE_OPTS` in `dashboard/app.py` heeft alle 10 opties
incl. gestapelde bouw, en `engine/standaard.py` retourneert `None` i.p.v. stil grondgebonden aan
te nemen bij een leeg woningtype. Geen actie nodig.)

## Scope
- `dashboard/app.py`:
  - `opname_dak_driehoek` en `opname_dak_negen`: dezelfde `_ds = getattr(dos.opname,
    "dak_standaard", None)`-overerving als `opname_dak_plat` al had (isolatie_aanwezig,
    isolatiedikte_mm, bouwjaarklasse, spouw_aanwezig, rc_bron, begrenzing). De kopgevel-driehoek
    (gevel-typed, ontstaat als bijproduct van het zadeldak) blijft bewust buiten deze overerving —
    die hoort bij de gevel-standaard, niet de dak-standaard.
  - Nieuwe constanten `BOUWJAARKLASSE_OPTS` (7 klassen, zelfde grenzen als
    `dashboard/bouwjaar.py:ERAS`, gefraseerd zoals `vabi/constructie_generate.py:
    _jaar_uit_klassetekst()` al herkent) en `RC_BRON_OPTS`.
  - Generieke element-editor (`opname_el` + het bijbehorende formulier): twee nieuwe velden
    "Bouwjaarklasse (dit vlak)" en "Rc-bron" naast de bestaande Rc/isolatie/dikte-velden, voor elk
    niet-kozijn vlak (geldt dus ook voor gevel/vloer, niet alleen dak — `SchilDeel.bouwjaarklasse`/
    `rc_bron` waren al generieke velden op het datamodel).

## Out of scope
- Geen wijziging aan `core/dossier.py`, `engine/standaard.py` of de VABI-generators — alle
  gebruikte velden bestonden al.
- Dakkapel-isolatie blijft zoals het was (eigen `wangen_geisoleerd`-checkbox, geen deel van de
  dak-standaard-overerving) — dat is een bewuste, aparte invoer, geen gat.
- Geen visuele stijl-wijzigingen aan de gebouwboom-editor.

## Acceptance criteria
- [x] Zadeldak- en freeform-dakwizard erven `dak_standaard` net als het platte dak.
- [x] Bouwjaarklasse en Rc-bron zijn per vlak zichtbaar en opslaanbaar in de gebouwboom-editor.
- [x] `python tests/run_tests.py` groen (772/772, incl. nieuwe tests voor beide wizards + de
      handmatige override in de editor).
- [x] `./scripts/verify.sh` slaagt.
- [ ] AI-review PASS door een andere agent dan de bouwer.

## Sessions
- 2026-08-14 (claude): Bevinding C nagelopen -> bleek al opgelost, geen wijziging nodig.
  Bevinding D: `opname_dak_driehoek`/`opname_dak_negen` uitgebreid met dezelfde
  `dak_standaard`-overerving als `opname_dak_plat`; `BOUWJAARKLASSE_OPTS`/`RC_BRON_OPTS` +
  velden in de generieke element-editor. Tests toegevoegd op de bestaande webapp-testflow
  (dezelfde `_ptag`-project als de overige dak-wizard-tests): dak-nummering bleek 3 platte-dak-
  aanroepen verder te staan dan verwacht (dakkapel-ids matchen de `dak(\d+)`-telling niet mee,
  maar het platte dak van een eerdere test in dezelfde flow wel) — eerste testpoging faalde op een
  StopIteration door een verkeerd aangenomen dak-nummer, opgelost door de daadwerkelijke
  `_volgend_dak_nr`-telling na te rekenen i.p.v. te gokken. 772/772 groen.

## Notes
- `BOUWJAARKLASSE_OPTS`-fraseringen ("Tot 1946", "Van X t/m Y", "Vanaf 2006") zijn bewust gelijk
  aan wat `vabi/constructie_generate.py:_jaar_uit_klassetekst()` al parseert (afkomstig uit hoe
  MagicPlan dit soort velden aanlevert) — geen nieuwe, ongeteste tekstconventie verzonnen.
