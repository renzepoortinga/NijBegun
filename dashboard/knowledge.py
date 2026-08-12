"""Lokale kennisbank + brongebonden AI-vraagbaak.

De lokale zoeker blijft werken zonder API-sleutel. Alleen de best passende passages
worden naar de bestaande Anthropic-koppeling gestuurd; persoonsgegevens horen niet
in de kennisbank of in vragen.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from functools import lru_cache
from hashlib import sha256


ROOT = Path(__file__).resolve().parent.parent
REGISTER = ROOT / "knowledge" / "sources.json"


def laad_register(path=REGISTER):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    bronnen = data.get("bronnen", [])
    bekende_paden = set()
    hashes = {}
    for bron in bronnen:
        rel = bron.get("pad", "")
        p = ROOT / rel if rel else None
        bron["aanwezig"] = bool((p and p.is_file()) or bron.get("url"))
        if rel:
            bekende_paden.add(rel.replace("\\", "/").lower())
    # Maploos beheer: elk ondersteund bestand onder knowledge/ verschijnt automatisch.
    for p in sorted((ROOT / "knowledge").rglob("*")):
        if not p.is_file() or p.suffix.lower() not in (".pdf", ".md", ".txt", ".docx", ".xlsx"):
            continue
        rel = p.relative_to(ROOT).as_posix()
        if rel.lower() in bekende_paden or p.name in ("README.md",):
            continue
        digest = sha256(p.read_bytes()).hexdigest()
        duplicate = hashes.get(digest)
        hashes[digest] = duplicate or rel
        naam = p.stem
        low = (rel + " " + naam).lower()
        categorie = ("Voorbeeld" if "voorbeeld" in low else
                     "Contractueel" if "opdrachtbrief" in low or "aanbesteding" in low else
                     "Nij Begun uitvoering" if "nij begun" in low else "Aanvullende vakkennis")
        toegang = "licentiebeperkt" if any(x in low for x in
                    ("isso", "nta 8800", "handboek", "praktijkboek", "aanvullende relevante kennis", "biobased bouwen")) else "intern"
        bronnen.append({"id": "auto-" + digest[:12], "titel": naam, "categorie": categorie,
                        "status": "duplicaat" if duplicate else "aanvullend",
                        "versie": "automatisch ontdekt — controleren", "peildatum": "",
                        "pad": rel, "eigenaar": "nog classificeren", "aanwezig": True,
                        "toegang": toegang, "duplicaat_van": duplicate or ""})
    return data


@lru_cache(maxsize=64)
def _tekst_uit_pdf(path):
    try:
        from pypdf import PdfReader
        pages = []
        for nr, page in enumerate(PdfReader(str(path)).pages, 1):
            txt = page.extract_text() or ""
            if txt.strip():
                pages.append("[pagina %d]\n%s" % (nr, txt))
        return "\n\n".join(pages)
    except Exception:
        return ""


@lru_cache(maxsize=16)
def _url_tekst(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "NijBegun-kennisbank/1.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            html = response.read().decode("utf-8", errors="replace")
        html = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
        return re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", html)).strip()
    except Exception:
        return ""


@lru_cache(maxsize=128)
def _lees_pad(rel):
    path = ROOT / rel
    if not path.is_file():
        return ""
    if path.suffix.lower() == ".pdf":
        return _tekst_uit_pdf(path)
    if path.suffix.lower() == ".docx":
        try:
            from docx import Document
            return "\n".join(p.text for p in Document(str(path)).paragraphs if p.text.strip())
        except Exception:
            return ""
    if path.suffix.lower() == ".xlsx" and path.name.startswith("Maatregelencatalogus"):
        try:
            data = json.loads((ROOT / "catalog" / "catalog.json").read_text(encoding="utf-8"))
            return json.dumps(data, ensure_ascii=False)
        except Exception:
            return ""
    if path.suffix.lower() in (".md", ".txt"):
        return path.read_text(encoding="utf-8", errors="replace")
    return ""


def lees_bron(bron):
    if bron.get("url"):
        return _url_tekst(bron["url"])
    path = ROOT / bron.get("pad", "")
    return _lees_pad(bron.get("pad", "")) if path else ""


def _secties(tekst, max_chars=2600):
    delen, kop, buf = [], "", []
    for regel in tekst.splitlines():
        if regel.startswith("#") and buf:
            delen.append((kop, "\n".join(buf).strip()))
            buf = []
        if regel.startswith("#"):
            kop = regel.lstrip("# ").strip()
        else:
            buf.append(regel)
        if sum(map(len, buf)) >= max_chars:
            delen.append((kop, "\n".join(buf).strip()))
            buf = []
    if buf:
        delen.append((kop, "\n".join(buf).strip()))
    return [(k, t) for k, t in delen if t]


def zoek(vraag, register=None, limiet=8, licentiebronnen=False):
    register = register or laad_register()
    woorden = set(re.findall(r"[a-z0-9à-ÿ]{3,}", (vraag or "").lower()))
    stop = {"wat", "hoe", "waarom", "welke", "zijn", "voor", "van", "een", "het", "deze", "met"}
    woorden -= stop
    hits = []
    for bron in register.get("bronnen", []):
        if not bron.get("aanwezig"):
            continue
        if bron.get("status") in ("historisch", "duplicaat", "status-onzeker"):
            continue
        if bron.get("toegang") == "licentiebeperkt" and not licentiebronnen:
            continue
        for kop, tekst in _secties(lees_bron(bron)):
            hay = (kop + " " + tekst).lower()
            score = sum(3 if w in kop.lower() else min(hay.count(w), 3) for w in woorden)
            if score:
                hits.append({"score": score, "id": bron["id"], "titel": bron["titel"],
                             "versie": bron.get("versie", ""), "pad": bron.get("pad") or bron.get("url", ""),
                             "categorie": bron.get("categorie", ""),
                             "kop": kop, "tekst": tekst[:2600]})
    return sorted(hits, key=lambda x: (-x["score"], x["titel"]))[:limiet]


def beantwoord(vraag, hits, cfg=None):
    """Geeft (antwoord, fout). Zonder sleutel blijft de lokale bronnenlijst bruikbaar."""
    cfg = cfg or {}
    if not hits:
        return None, "Niet vastgesteld in de beschikbare bronnen. Voeg een geldige bron toe of stel de vraag specifieker."
    ai = cfg.get("ai") or {}
    key = os.environ.get("ANTHROPIC_API_KEY") or ai.get("api_key", "")
    if not key:
        return None, "AI-sleutel ontbreekt; hieronder staan wel de lokaal gevonden bronpassages."
    context = []
    for i, h in enumerate(hits, 1):
        context.append("[BRON %d: %s | categorie %s | versie %s | %s | %s]\n%s" %
                       (i, h["titel"], h.get("categorie", ""), h["versie"] or "niet vastgelegd", h["pad"],
                        h["kop"] or "zonder kop", h["tekst"]))
    prompt = """Je bent de interne brongebonden vraagbaak voor Nederlandse energieprestatie en Nij Begun.
Beantwoord UITSLUITEND met de aangeleverde passages. Maak duidelijk onderscheid tussen NTA 8800
(rekenmethode), ISSO (opnameprotocol), BRL (kwaliteit/proces), VABI (software) en Nij Begun
(regeling/uitvoering). Een normatieve/actieve bron wint altijd van achtergrond, voorbeeld of interne uitleg.
Verzin niets. Als de passages onvoldoende bewijs geven, antwoord exact:
'Niet vastgesteld in de beschikbare bronnen.' Sluit inhoudelijke beweringen af met [BRON n].
Noem bij versiegevoelige informatie de versie. Geef geen juridisch bindend oordeel.

VRAAG:\n%s\n\nPASSAGES:\n%s""" % (vraag.strip(), "\n\n".join(context))
    body = json.dumps({"model": ai.get("model", "claude-sonnet-5"), "max_tokens": 1800,
                       "messages": [{"role": "user", "content": prompt}]}).encode("utf-8")
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, method="POST",
                                 headers={"Content-Type": "application/json", "x-api-key": key,
                                          "anthropic-version": "2023-06-01"})
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
        answer = "".join(x.get("text", "") for x in result.get("content", [])
                         if x.get("type") == "text").strip()
        return (answer, None) if answer else (None, "Leeg antwoord van de AI-provider.")
    except urllib.error.HTTPError as exc:
        return None, "AI-vraag mislukt (HTTP %s); lokale bronresultaten blijven beschikbaar." % exc.code
    except Exception as exc:
        return None, "AI-vraag mislukt (%s); lokale bronresultaten blijven beschikbaar." % str(exc)[:80]
