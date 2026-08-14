---
id: 012
assigned: claude
branch: fix/magicplan-ssl-python314
depends_on: [007]
---

<!-- De map ís de status: backlog/ ready/ active/ done/. Geen status-veld hier. -->

# Task 012 — Live MagicPlan-API-calls faalden op Python 3.14 (SSL-profielcheck)

## Goal
Renze vroeg een echte MagicPlan-opname (Essenhage 32) opnieuw op te halen om de contour-fix
(taak 007) te beproeven. `python magicplan/extractor.py --project-id ...` faalde met
`ssl.SSLCertVerificationError: Basic Constraints of CA cert not marked critical`. Root cause
gevonden en veilig gefixt (geen certificaatverificatie uitgeschakeld).

## Root cause
Python 3.13+/OpenSSL 3.2+ zet `ssl.VERIFY_X509_STRICT` standaard aan in `create_default_context()`
— een strengere RFC 5280-profielcheck. `cloud.magicplan.app`'s certificaatketen heeft een
intermediate-CA waarvan het Basic-Constraints-veld niet als 'critical' is gemarkeerd: technisch
niet 100% profiel-conform, maar geen vervalst of onvertrouwd certificaat. Bevestigd geen MITM/
proxy-probleem op deze machine: `curl`/Windows Schannel accepteren dezelfde keten probleemloos, en
`https://www.google.com` werkte al de hele tijd via Python — alleen magicplan.app's specifieke
keten wordt door de nieuwe strikte OpenSSL-check afgewezen.

## Scope
`magicplan/extractor.py`: nieuwe `_ssl_context()` — een `ssl.create_default_context()` met
alléén `VERIFY_X509_STRICT` uitgeschakeld; CA-vertrouwen, hostnaam- en verloopcontrole blijven
volledig actief. Toegepast op de enige plek die live HTTP doet (`MagicPlanClient._get`).

## Out of scope
- Geen wijziging aan andere modules die netwerk doen (`magicplan/photos.py`,
  `dashboard/graph_mail.py`, `catalog/api_client.py`) — niet getest tegen deze fout, niet
  aangeraakt zonder bevestigd probleem daar.
- Geen `requirements.txt`-wijziging — dit is een stdlib-`ssl`-contextaanpassing, geen nieuwe
  dependency.

## Wat er tegelijk mee gedaan is (niet in deze commit-scope, wel dezelfde sessie)
Met de gefixte extractor is Essenhage 32 (project-id `efac3ec7-9e5c-44b8-81c4-e1d2cafd5051`)
opnieuw live opgehaald. De contour (taak 007) bleek daadwerkelijk te werken: het grondvlak is een
31-punts polygon (13 zichtbare gevelwanden i.p.v. de oude 2-4-wanden-doos), inclusief de "berging"
(MagicPlan noemt 'm "Laundry Room", 7.44 m², bevestigd via een screenshot van de plattegrond) als
onderdeel van dezelfde doorlopende vloerscan. De PRODUCTIE-dossier van dit project (VPS,
`out/projects/9501TP_32/dossier_9501TP_32.json`) is bijgewerkt met de 3 nieuwe contouren
(Ground/1st/2nd Floor), NA een backup (`dossier_9501TP_32.json.bak-voor-contour-14082026` naast
het origineel) en verificatie in de daadwerkelijk draaiende container (`data-footprint-bron=
"contour"`, 13 gevel-vlakken, geldige XML — bevestigd via `docker compose exec`). Overige
opnamevelden (isolatie/glastype/kierdichting etc., uit de eerdere CSV-route) zijn ONGEWIJZIGD
gelaten — alleen `contour_m` per vloer toegevoegd, niet de hele dossier vervangen (die had de
webapp's normale JSON-upload wél gedaan, vandaar de chirurgische aanpak i.p.v. de standaardroute).

## Acceptance criteria
- [x] `python magicplan/extractor.py --test` slaagt (was: SSL-fout).
- [x] `python magicplan/extractor.py --project-id <echt-id>` haalt een echte opname op.
- [x] `python tests/run_tests.py` blijft groen (789/789 — geen test raakt live netwerk).
- [x] `./scripts/verify.sh` slaagt.
- [ ] AI-review PASS door een andere agent dan de bouwer.

## Sessions
- 2026-08-15 (claude): SSL-fout eerst gekarakteriseerd vóór een fix te verzinnen — google.com
  werkte al (dus geen algemeen MITM/proxyprobleem), curl/Windows accepteerden dezelfde keten
  (dus geen vervalst certificaat). Dat wees direct naar Python 3.14's striktere standaard-
  `SSLContext` i.p.v. een netwerk- of magicplan-probleem. Gefixt door precies de ene strikte
  profielvlag uit te zetten, niets anders aan certificaatverificatie veranderd. Live beproefd op
  een echt project; productiedossier bijgewerkt met backup en verificatie in de draaiende
  container (zie hierboven) — nog niet gemerged/gedeployed als losse stap, dat gebeurt na review.
