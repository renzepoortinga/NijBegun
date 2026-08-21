---
id: 025
assigned: Codex Builder
branch: fix/025-magicplan-ssl
depends_on: []
---

# Task 025 — Fix ontbrekende SSL-profielfix in `magicplan/form_push.py` + `magicplan/photos.py`

## Goal
Meerdere `magicplan/*.py`-modules doen eigen `urllib.request.urlopen()`-calls naar
`cloud.magicplan.app` zonder de Python 3.14/OpenSSL 3.2+-SSL-profielfix die
`magicplan/extractor.py` al heeft (taak 012, `f4e9c04`) — diezelfde machines zullen daar dus
dezelfde `SSLCertVerificationError` tegenkomen.

## Scope
- `magicplan/form_push.py:343` — `_http()` roept `urlopen(req, timeout=60)` aan zonder
  `_ssl_context()`, voor hetzelfde host (`BASE_URL` = `cloud.magicplan.app`, `form_push.py:33`).
- `magicplan/photos.py:118` (`_client_fetch`) + regel ~152 (CLI-fallback) — idem, voor
  MagicPlan-fotodownloads.
- Root cause identiek aan taak 012: Python 3.13+/OpenSSL 3.2+ zet `VERIFY_X509_STRICT` standaard
  aan, en cloud.magicplan.app's certificaatketen is niet 100% RFC-5280-profiel-conform (geen
  MITM/proxy — zie de uitleg in `extractor.py::_ssl_context`).
- Fix: `_ssl_context()` uit `extractor.py` DELEN (niet dupliceren) tussen alle drie modules —
  overweeg 'm te verplaatsen naar een klein gedeeld hulpmodule (bv. `magicplan/_http.py` of een
  functie in `magicplan/__init__.py`) zodat een volgend MagicPlan-callpad 'm niet weer vergeet.

## Out of scope
- Andere SSL/TLS-wijzigingen.
- Wijzigingen aan de form-merge- of foto-downloadlogica zelf.

## Acceptance criteria
- [x] `form_push.py` én `photos.py` gebruiken dezelfde SSL-profielfix als `extractor.py` voor
      calls naar `cloud.magicplan.app`.
- [x] Bij voorkeur: één gedeelde `_ssl_context()`-functie i.p.v. drie losse kopieën (voorkomt dat
      een vierde module het straks weer vergeet).
- [x] `./scripts/verify.sh` slaagt.
- [x] AI-review PASS door een andere agent dan de bouwer.

## Sessions

- 2026-08-21 Codex Builder: na onafhankelijke review PASS gerebased op de nieuwste `origin/main`.
  Blocking `scripts/verify.sh` slaagt na rebase met 970/970 tests. Alle acceptance criteria zijn
  voldaan. De live MagicPlan-handshake, form-push en fotodownload
  zijn niet uitgevoerd omdat daarvoor geen gebruikersautorisatie is gegeven. Daarom blijft de taak
  conform de Notes in `tasks/active/` en wordt de branch uitsluitend als draft aangeboden.
- 2026-08-21 Codex Builder: bestaande TLS-context naar `magicplan/ssl_context.py` gedeeld en alle
  `urlopen`-paden in extractor, form-push en photos aangesloten. Offline regressies bewijzen dat
  certificaat- en hostnaamverificatie actief blijven, alleen `VERIFY_X509_STRICT` uitstaat, en dat
  form-push en foto-download de context werkelijk doorgeven; bronchecks bewaken ook het CLI-pad.
  `scripts/verify.sh`: PASS, 852/852 tests. Geen live MagicPlan-call of `.env`-toegang uitgevoerd,
  conform gebruikersautorisatie; de operationele live check op Python 3.13+ blijft daarom open.
- 2026-08-21 Codex Manager: taak na hernummering geclaimd op een eigen worktree vanaf actuele
  `main`; live calls alleen als het taakbestand en de expliciete gebruikersautorisatie dit toelaten.

## Notes
Gevonden door twee onafhankelijke reviewrondes van taak 014/015 (15-8-2026, `/code-review high`)
— niet zelf live gereproduceerd deze sessie (geen `.env`/live MagicPlan-API-call uitgevoerd),
maar de code-asymmetrie met de al bevestigde taak-012-fix is in beide gevallen overtuigend.
Verifieer live vóór het sluiten van deze taak (`push_forms.bat` + een fotodownload draaien op
een Python 3.13+-machine).
