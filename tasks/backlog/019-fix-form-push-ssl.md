---
id: 019
assigned:
branch:
depends_on: []
---

# Task 019 — Fix ontbrekende SSL-profielfix in `magicplan/form_push.py`

## Goal
`push_forms.bat`/`form_push.py` faalt op dezelfde Python 3.14/OpenSSL 3.2+-machines waar
`magicplan/extractor.py` al eerder faalde (taak 012, `f4e9c04`), omdat de SSL-profielfix daar
nooit is doorgevoerd.

## Scope
- `magicplan/form_push.py:343` — `_http()` roept `urllib.request.urlopen(req, timeout=60)` aan
  ZONDER de `_ssl_context()`-fix die `magicplan/extractor.py` (`_ssl_context()`, sinds taak 012)
  al heeft voor exact hetzelfde host (`cloud.magicplan.app`, zie `BASE_URL` in `form_push.py:33`).
- Root cause identiek aan taak 012: Python 3.13+/OpenSSL 3.2+ zet `VERIFY_X509_STRICT` standaard
  aan, en cloud.magicplan.app's certificaatketen is niet 100% RFC-5280-profiel-conform (geen
  MITM/proxy — zie de uitleg in `extractor.py::_ssl_context`).
- Fix: dezelfde `_ssl_context()`-aanpak toepassen op de `urlopen()`-call in `form_push.py`
  (bij voorkeur de bestaande helper hergebruiken/delen i.p.v. dupliceren).

## Out of scope
- Andere SSL/TLS-wijzigingen.
- Wijzigingen aan de form-merge-logica zelf.

## Acceptance criteria
- [ ] `form_push.py` gebruikt dezelfde SSL-profielfix als `extractor.py` voor calls naar
      `cloud.magicplan.app`.
- [ ] `./scripts/verify.sh` slaagt.
- [ ] AI-review PASS door een andere agent dan de bouwer.

## Sessions

## Notes
Gevonden door de onafhankelijke reviewer van taak 014/015 (15-8-2026, `/code-review high`) —
niet zelf live gereproduceerd deze sessie (geen `.env`/live MagicPlan-formulierwijziging
uitgevoerd), maar de code-asymmetrie met de al bevestigde taak-012-fix is overtuigend. Verifieer
live vóór het sluiten van deze taak (`push_forms.bat` draaien op een Python 3.13+-machine).
