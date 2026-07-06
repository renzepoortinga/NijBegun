"""
AI-assistentie voor de webapp (zoals SOBOLT's "AI spelling"/"AI assistentie"), twee smaken:

1. OFFLINE tekstvoorstel — engine/advies_text.genereer_advies: deterministisch, gratis, geen internet.
2. "AI verbeteren" — Claude API (Anthropic): verbetert spelling/toon van de door de adviseur geschreven
   toelichting. Vereist een API-sleutel + internet (draait op de adviseur-machine).

Sleutel: env ANTHROPIC_API_KEY of config.json  "ai": {"api_key": "...", "model": "..."}.
AVG: de toelichting gaat naar de Anthropic-API — zet er GEEN persoonsgegevens in (geen naam/adres van
de bewoner; het adres staat toch al elders in het plan). De UI waarschuwt hiervoor.
"""
import json, os, urllib.request, urllib.error

API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-5"

PROMPT = (
    "Je bent redacteur voor een Nederlandse EPA-isolatieadviseur. Verbeter de spelling, grammatica en "
    "leesbaarheid van de onderstaande 'persoonlijke toelichting' voor een Nij Begun-isolatieplan. "
    "Behoud de inhoud en alle technische feiten exact; voeg NIETS toe dat er niet staat; professionele, "
    "vriendelijke toon richting de bewoner. Geef ALLEEN de verbeterde tekst terug, zonder inleiding.\n\n"
    "TEKST:\n%s"
)


def _sleutel(cfg):
    return os.environ.get("ANTHROPIC_API_KEY") or (cfg.get("ai") or {}).get("api_key", "")


def verbeter_tekst(tekst, cfg=None):
    """-> (verbeterde_tekst, None) of (None, foutmelding)."""
    cfg = cfg or {}
    tekst = (tekst or "").strip()
    if not tekst:
        return None, "Schrijf eerst een toelichting; daarna kan de AI 'm verbeteren."
    key = _sleutel(cfg)
    if not key:
        return None, ("Geen Anthropic API-sleutel gevonden. Zet ANTHROPIC_API_KEY (omgevingsvariabele) of "
                      '"ai": {"api_key": "..."} in config.json. Sleutel maken: console.anthropic.com.')
    body = json.dumps({
        "model": (cfg.get("ai") or {}).get("model", DEFAULT_MODEL),
        "max_tokens": 1500,
        "messages": [{"role": "user", "content": PROMPT % tekst}],
    }).encode("utf-8")
    req = urllib.request.Request(API_URL, data=body, method="POST", headers={
        "Content-Type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            j = json.loads(r.read().decode("utf-8"))
        uit = "".join(b.get("text", "") for b in j.get("content", []) if b.get("type") == "text").strip()
        return (uit, None) if uit else (None, "Leeg antwoord van de API — probeer opnieuw.")
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = json.loads(e.read().decode("utf-8")).get("error", {}).get("message", "")[:120]
        except Exception:
            pass
        return None, "AI-verzoek mislukt (HTTP %s). %s" % (e.code, detail)
    except Exception as e:
        return None, "AI-verzoek mislukt (%s). Internet nodig; werkt op je eigen machine." % str(e)[:80]
