"""
Maatregel-SELECTIE voor de webapp.

De auto-engine (engine/measure_engine) kiest per bouwdeel de goedkoopste maatregel. De webapp wil méér:
per bouwdeel een lijst KANDIDATEN tonen (goedkoopste voorgeselecteerd) zodat de adviseur zelf aanvinkt /
wisselt, plus de cat 2/3 meerwerk-subposten, en daarna de SELECTIE omzetten in dossier.maatregelen + totaal.

Dit bouwt bovenop measure_engine (zelfde catalogus = Nij Begun Maatregelencatalogus, lokaal catalog.json of
later live via catalog/api_client). Niets wordt zelf "gerekend": het zijn catalogus-maatregelen + prijzen.

    from dashboard.measures import laad_catalog, suggesties, bouw_maatregelen
    cat = laad_catalog()
    groepen = suggesties(dossier, cat)          # -> UI toont checkboxes per bouwdeel
    maatregelen, totaal = bouw_maatregelen(cat, keuze)   # keuze = aangevinkte codes + hoeveelheden
"""
import os, sys, json, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.dossier import Maatregel, Subpost                                   # noqa: E402
from engine.measure_engine import (element_spec, price_incl, is_delta, bracket_match,
                                    propose_subposten, ONDERDEEL, STREEF, EXCLUDE, CAT3_KW)  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(ROOT, "catalog", "catalog.json")


def laad_catalog(path=CATALOG_PATH):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _kandidaten(catalog, prefixes, keywords, m2):
    """Alle passende KERN-maatregelen (geen delta/meerwerk), gesorteerd: m²-bracket-match eerst, dan prijs."""
    def ok(m):
        o = (m.get("omschrijving") or "").lower()
        return (any(m["code"].startswith(p) for p in prefixes) and not is_delta(m)
                and (price_incl(m) or 0) > 0 and any(k in o for k in keywords)
                and not any(x in o for x in EXCLUDE))
    cand = [m for m in catalog["maatregelen"] if ok(m)]
    cand.sort(key=lambda m: (bracket_match(m["omschrijving"], m2) is not True, price_incl(m)))
    return cand


def suggesties(dossier, catalog):
    """-> lijst groepen per bouwdeel met kandidaten + meerwerk-subposten. De adviseur kiest in de UI.
    Aggregatie per element_spec-prefix (zoals measure_engine.run): één advies per gevel/vloer/dak/glas."""
    groups = {}
    for s in dossier.schil:
        spec = element_spec(s)
        if not spec:
            continue
        prefixes, keywords, note = spec
        key = tuple(prefixes)
        g = groups.setdefault(key, {"prefixes": prefixes, "keywords": keywords, "m2": 0.0,
                                    "type": s.type, "note": note})
        g["m2"] += s.oppervlakte_m2 or 0.0
    out = []
    for g in groups.values():
        m2 = round(g["m2"], 2)
        cand = _kandidaten(catalog, g["prefixes"], g["keywords"], m2)
        if not cand:
            continue
        kand = [{"code": m["code"], "omschrijving": (m.get("omschrijving") or "").rstrip(),
                 "prijs": round(price_incl(m), 2), "kosten": round(price_incl(m) * m2, 2),
                 "eenheid": m.get("eenheid", "m²") or "m²"} for m in cand]
        subs = propose_subposten(catalog, Maatregel(code=cand[0]["code"]))
        out.append({
            "onderdeel": ONDERDEEL.get(g["prefixes"][0][:2], ""), "type": g["type"], "m2": m2,
            "default_code": cand[0]["code"], "rc_u_doel": STREEF.get(g["type"], ""), "note": g["note"],
            "kandidaten": kand,
            "subposten": [{"code": s.code, "omschrijving": s.omschrijving, "categorie": s.categorie,
                           "prijs": s.prijs_per_eenheid, "eenheid": s.eenheid} for s in subs]})
    out.sort(key=lambda x: x["onderdeel"])
    return out


CAT_LABEL = {"V1": "Gevel", "V2": "Beglazing en kozijnen", "V3": "Vloer",
             "V4": "Dak", "V5": "Ventilatie", "V6": "Kierdichting"}


def _schoon_label(oms):
    """'Spouwmuurisolatie vlokken 60 mm van 0 m² tot 45 m²' -> 'Spouwmuurisolatie vlokken'."""
    s = re.sub(r"\s*van(af)?\s+[\d.,]+\s*m².*$", "", oms or "", flags=re.I)
    s = re.sub(r"\s*[\d.,]+\s*mm\s*$", "", s).strip(" -·")
    return s.strip()


def catalogus_boom(catalog):
    """Volledige Maatregelencatalogus als boom voor de 'zelf kiezen'-UI (zoals het Nij Begun-portal):
    categorieën (V1..V6) -> subcategorieën (V1-1..) -> kern-maatregelen + bijkomende kosten (X-codes)."""
    cats = {}
    for m in catalog.get("maatregelen", []):
        code = m.get("code") or ""
        parts = code.split("-")
        if len(parts) < 3 or parts[0] not in CAT_LABEL:
            continue
        sub = "-".join(parts[:2])
        c = cats.setdefault(parts[0], {"code": parts[0], "naam": CAT_LABEL[parts[0]], "subs": {}})
        s = c["subs"].setdefault(sub, {"code": sub, "naam": "", "kern": [], "meerwerk": []})
        rij = {"code": code, "omschrijving": (m.get("omschrijving") or "").strip(),
               "prijs": round(price_incl(m) or 0, 2), "eenheid": m.get("eenheid") or "m²",
               "biobased": bool(m.get("biobased"))}
        (s["meerwerk"] if parts[2].startswith("X") else s["kern"]).append(rij)
    out = []
    for cat in sorted(cats):
        c = cats[cat]
        subs = []
        for sc in sorted(c["subs"]):
            s = c["subs"][sc]
            basis = s["kern"] or s["meerwerk"]
            if not basis:
                continue
            s["naam"] = min((_schoon_label(r["omschrijving"]) for r in basis if r["omschrijving"]),
                            key=len, default=sc) or sc
            s["kern"].sort(key=lambda r: r["code"])
            s["meerwerk"].sort(key=lambda r: r["code"])
            subs.append(s)
        c["subs"] = subs
        out.append(c)
    return out


def zoek_maatregel(catalog, code):
    """-> catalogusrij of None (voor de vrije-keuze-flow)."""
    return next((m for m in catalog.get("maatregelen", []) if m.get("code") == code), None)


def bouw_maatregelen(catalog, keuze):
    """keuze = [{code, onderdeel, m2, rc_u_doel, subposten:[{code, hoeveelheid}]}] (alleen aangevinkte).
    -> (list[Maatregel] met kosten, totaal incl. btw). Voedt fill_template + de toekomstige-staat-export."""
    by_code = {m["code"]: m for m in catalog["maatregelen"]}
    maatregelen = []
    for k in keuze or []:
        m = by_code.get(k.get("code"))
        if not m:
            continue
        m2 = float(k.get("m2") or 0)
        prijs = round(price_incl(m) or 0, 2)
        maat = Maatregel(code=m["code"], onderdeel=k.get("onderdeel") or ONDERDEEL.get(m["code"][:2], ""),
                         omschrijving=(m.get("omschrijving") or "").rstrip(), rc_u_doel=k.get("rc_u_doel", ""),
                         oppervlakte_m2=m2, eenheid=m.get("eenheid", "m²") or "m²",
                         prijs_per_eenheid=prijs, kosten=round(prijs * m2, 2), categorie=1)
        for sp in k.get("subposten", []):
            sm = by_code.get(sp.get("code"))
            if not sm:
                continue
            hoev = float(sp.get("hoeveelheid") or 0)
            spr = round(price_incl(sm) or 0, 2)
            ol = (sm.get("omschrijving") or "").lower()
            maat.subposten.append(Subpost(
                categorie=(3 if any(x in ol for x in CAT3_KW) else 2), code=sp["code"],
                omschrijving=(sm.get("omschrijving") or "").rstrip(), prijs_per_eenheid=spr,
                eenheid=sm.get("eenheid", "m²") or "m²", hoeveelheid=hoev, kosten=round(spr * hoev, 2)))
        maatregelen.append(maat)
    maatregelen.sort(key=lambda x: x.onderdeel)
    totaal = round(sum((m.kosten or 0) + sum((s.kosten or 0) for s in m.subposten)
                       for m in maatregelen), 2)
    return maatregelen, totaal
