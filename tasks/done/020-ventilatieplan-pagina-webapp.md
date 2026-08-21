---
id: 020
assigned:
branch:
depends_on: [019]
---

# Task 020 — Ventilatieplan-pagina in de webapp (tekening met sleepbare pijlen)

## Goal
De adviseur ziet het ventilatieplan als tekening op de plattegrond, kan de pijlen verslepen
en de waarden aanpassen, en de wijzigingen blijven aan het dossier hangen.

## Scope
Nieuwe route in `dashboard/app.py`: `/project/<tag>/ventilatieplan` (GET) plus een
opslagroute voor de markers (POST, JSON). Leest `geometrie.ruimtes` en het resultaat van
`ventilatie.bereken()`; schrijft `ventilatieplan` in het dossier volgens het datamodel in
`docs/ventilatieplan-webapp-spec.md`.

**Schermindeling** (onze huisstijl, niet hun kleuren):
- Kop "Ventilatieplan" met daaronder een balans-pil: `Balans: toevoer X l/s = afvoer Y l/s`,
  groen bij sluitend, oranje met de reden bij niet sluitend, plus een knop "Herbereken balans".
- Links "Plan per verdieping": per verdieping een kaart met de plattegrond als achtergrond en
  daarover een SVG-laag met de markers.
- Rechts "Berekening": de twee tabellen uit taak 019 (`RUIMTE | M2 | MIN. L/S | ADVIES L/S`
  en `RUIMTE | MIN. L/S | ADVIES L/S | AFVOERPUNT`), daaronder de zeven vuistregels met hun
  status en de deurbelasting-adviezen.

**Markers**:
- Drie soorten: toevoer (blauwe pijl, in de gevel, wijst naar binnen), afvoer (rode ovaal op
  het afzuigpunt), overstroom (groene pijl door een binnendeur). Elk met de waarde in l/s.
- Bediening: slepen = verplaatsen, een klik = 90 graden draaien, dubbelklik = waarde wijzigen
  of splitsen. Per verdieping knoppen `+ Toevoer`, `+ Afvoer`, `+ Overstroom` en `Herstel`
  (terug naar de automatisch geplaatste set).
- Tijdens het slepen een lijn van de marker naar het label van de ruimte waar hij bij hoort,
  en die ruimte oplichten. Een marker hoort altijd bij een ruimte; loslaten buiten elke
  ruimte laat hem terugspringen.
- Autoplaatsing bij het eerste openen: toevoer in de buitengevel van elke verblijfsruimte,
  afvoer in elke natte ruimte, overstroom op de verbinding verblijfsruimte naar natte ruimte.
  De adviseur corrigeert; de tool verzint niets stil.

**Achtergrond van de tekening**: gebruik in deze volgorde de MagicPlan-plattegrondafbeelding
uit het dossier, anders de bestaande contour uit `VloerInfo.contour_m`, anders een lege
kaart met de melding dat er geen plattegrond is. Nooit een verzonnen vorm tekenen.

## Out of scope
- PDF- en PNG-export (taak 021).
- Plattegrond uit een foto lezen (taak 022).
- Een JavaScript-framework introduceren. De webapp is server-rendered Jinja met vanilla JS,
  dat blijft zo.
- De rekenregels wijzigen. Die komen uit taak 019.

## Acceptance criteria
- [ ] Markers verslepen, draaien, toevoegen, verwijderen en van waarde wijzigen werkt, en
      overleeft een herlaad van de pagina.
- [ ] Coordinaten worden relatief (0..1) opgeslagen; de tekening klopt op een ander
      schermformaat en in de export.
- [ ] Een marker zonder geldige `ruimte_id` wordt geweigerd, met een leesbare melding.
- [ ] "Herstel" zet de automatische plaatsing terug zonder de handmatige waarden van andere
      verdiepingen te raken.
- [ ] Balans-pil en tabellen werken bij: waarde wijzigen leidt tot een nieuwe balansstatus.
- [ ] Werkt zonder internet (VPS achter Caddy, geen CDN).
- [ ] `./scripts/verify.sh` slaagt.
- [ ] AI-review PASS door een andere agent dan de bouwer.

## Sessions
- 2026-08-21: Gebouwd op taak 019 (branch nog niet gemerged naar main — dependency, zie depends_on).
  Dossier minimaal uitgebreid (`core/dossier.py`): `Ruimte.verdieping` (al berekend in
  `statistics_csv.py` als `kamer_verdieping`, alleen nooit opgeslagen — nu wel), `VloerInfo.
  plattegrond_afbeelding` (forward-compat voor taak 022, nog door niets gevuld) en de nieuwe
  `Ventilatieplan`/`VentilatieplanVerdieping`/`VentilatieMarker`-dataclasses + Dossier-veld,
  geregistreerd in de (de)serialisatiemap. Nieuwe pure datalaag `dashboard/ventilatieplan.py`:
  groeperen per verdieping (met een expliciete 'niet gekoppeld'-groep i.p.v. stil verkeerd
  indelen), autoplaatsing (toevoer/afvoer uit de taak-019-rekenlaag; GEEN automatische
  overstroom-marker — er is geen adjacency-data in het dossier om te weten welke ruimtes een
  deur delen, dat verzinnen zou een stille aanname zijn), validatie (weigert de HELE batch bij de
  eerste fout, nooit een deel stil opslaan) en de marker-balans. 3 nieuwe routes in
  `dashboard/app.py` (GET pagina + POST markers + POST herstel) + `dashboard/static/
  ventilatieplan.js` (vanilla JS: pointer-events voor slepen/klikken=draaien/dubbelklik=waarde-
  wijzigen-of-verwijderen, geen framework). Bewust NIET gebouwd: 'splitsen' (marker in tweeën) —
  stond in de Scope-tekst maar niet in de Acceptance Criteria; dubbelklik met een lege waarde
  dekt 'verwijderen' al. Geen browser-visuele-QA — de Claude-in-Chrome-extensie verbindt niet
  vanuit deze sessie (zelfde blokkade als taak 010, zie STATE.md); wél volledig end-to-end getest
  via de Flask test-client (GET/POST, validatie, persistentie over een 'herlaad', 404/400-paden).
  874/874 tests groen (49 nieuw t.o.v. taak 019: 34 datalaag + 15 route).
- 2026-08-21: AI-review (`/code-review high`, andere agent, expliciet doel `feat/019...` zodat
  precies de taak-020-diff werd beoordeeld — een eerste poging keek per ongeluk naar losse,
  niet-gecommitte documentatiewijzigingen van een ander onderwerp in dezelfde werkmap). Vond 2
  restbevindingen in `ventilatie/ventilatie.py` (taak 019, gemist door de vorige review): de
  '0 m2'-waarschuwing toonde altijd '0 m2' i.p.v. het werkelijke (mogelijk negatieve) oppervlak,
  en `deurbelasting()` valideerde alleen het eerste ruimtenaam in een overstroomweg tegen
  `res['rows']`, niet de rest — een tikfout verderop gleed er stil doorheen, in tegenspraak met de
  eigen docstring. Beide gefixt + 2 regressietests. 876/876 groen, verify.sh PASS. Taak gereed voor
  tasks/done/.

## Notes
Referentie met exacte schermteksten en gedrag: `docs/ventilatieplan-webapp-spec.md`, sectie 1.
Neem het gedrag over, niet de vormgeving: geen merknaam, logo of kleurpalet van Aira.

Voor de SVG-laag is er al ervaring in `dashboard/gebouw_svg.py` (554 regels isometrische
renderer). Dat is een read-only presentatielaag; deze pagina is de eerste die de gebruiker
laat tekenen. Houd de renderer dom en de waarheid in het dossier.
