---
id: 003
assigned: Codex (OpenAI), Builder
branch: fix/kwaliteitsverklaring-blokkeert-vabi-export
depends_on: []
---

# Task 003 — Kwaliteitsverklaring mag geen rekenbare fallback worden

## Goal
Voorkomen dat een in MagicPlan gekozen kwaliteitsverklaring stil wordt
geexporteerd als een rekenbare forfaitaire constructie met onbekende isolatie.

## Scope
- Voeg een harde preflight-gate toe aan de Vabi-export voor schildelen waarvan
  `rc_bron` na MagicPlan-import exact (witruimte/case-insensitief)
  `Kwaliteitsverklaring` is.
- Stop vóór het schrijven van Constructie-, Objecten- en
  Installatiebibliotheken, zodat geen gedeeltelijke of rekenbare exportset
  achterblijft.
- Toon in CLI en dashboard een concrete fout met de betrokken schildeel-id's en
  de instructie dat de kwaliteitsverklaring eerst correct in Vabi moet worden
  verwerkt.
- Verwijder voor deze route de huidige forfaitaire/best-passende fallback.
- Voeg regressietests toe voor directe generatoraanroepen, de volledige
  `generate_all`-keten en de dashboardroute die de exports maakt.

## Out of scope
- De bestaande verwerking van MagicPlan `Onbekend`, `Dikte onbekend`, lege
  `rc_bron` of de normale beslisschema-/bouwjaarroute wijzigen. Deze blijven
  exporteerbaar zoals nu.
- BCRG zoeken, valideren of NTA 8800 zelf rekenen.
- Zelf een Vabi-XML-structuur voor een onvolledige kwaliteitsverklaring gokken.
- Installatiekwaliteitsverklaringen wijzigen; deze taak betreft uitsluitend
  `SchilDeel.rc_bron`.
- MagicPlan-formulieren of het canonieke datamodel uitbreiden.

## Acceptance criteria
- [ ] Exact `rc_bron = Kwaliteitsverklaring` veroorzaakt een harde fout vóór
      enig Vabi-exportbestand wordt geschreven.
- [ ] De fout noemt ieder betrokken schildeel en legt uit waarom de export is
      geblokkeerd.
- [ ] `isolatie_aanwezig = Onbekend` zonder kwaliteitsverklaring blijft via de
      bestaande beslisschema-/forfaitaire route exporteerbaar.
- [ ] `rc_bron = Dikte onbekend`, leeg en overige bestaande waarden blijven
      ongewijzigd werken.
- [ ] Er blijft na een geblokkeerde `generate_all`-run geen gedeeltelijke nieuwe
      exportset achter.
- [ ] Bestaande tests plus nieuwe regressietests slagen via
      `./scripts/verify.sh`.
- [ ] AI-review PASS door een andere leverancier dan de bouwer.

## Sessions
- 2026-08-13 Codex (OpenAI), Manager: oorzaak vastgesteld in
  `vabi/constructie_generate.py`; taak afgebakend. Besluit gebruiker: alleen de
  expliciete MagicPlan-keuze `Kwaliteitsverklaring` blokkeren, nooit de gewone
  keuze `Onbekend`.
- 2026-08-13 Codex (OpenAI), Builder: centrale Vabi-preflight toegevoegd en
  aangeroepen vóór alle drie directe writers en vóór `generate_all` de
  uitvoermap aanmaakt. Oude forfaitaire kwaliteitsverklaring-fallback
  verwijderd; fout noemt alle schildeel-id's en dashboard toont die via de
  bestaande flash-route. Regressietests toegevoegd voor directe writers,
  volledige keten, toegestane onbekend-varianten en dashboard. Gerichte
  dependencyvrije regressie PASS; `py_compile` en `git diff --check` PASS.
  `./scripts/verify.sh` geeft PASS met de bestaande advisory uit taak 002:
  systeem-Python mist `lxml`; installeren lukte niet omdat ook `pip` ontbreekt.
  Onafhankelijke leveranciersreview en volledige suite in een ingerichte
  omgeving blijven vereist.

## Notes
De huidige code kiest bij een kwaliteitsverklaring eerst een standaardtemplate
en voegt daarna alleen een issue toe. Daardoor is de Vabi-invoer toch compleet
en kan een inhoudelijk onjuiste berekening worden gemaakt.

Een latere verbetering kan een importeerbare maar bewust onvolledige
kwaliteitsverklaring exporteren. Daarvoor is eerst een echte, door dezelfde
Vabi-versie gemaakte referentie-export nodig; zonder die referentie geldt de
gouden regel dat veldnamen en enumcodes niet worden gegokt.
