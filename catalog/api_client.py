"""
Nij Begun Maatregelencatalogus-API -> catalog.json (live actualiseren).

API: https://api.nij-begun.project.abl.nu  (Apipie/Rails; spec op /apipie.json?type=swagger,
docs op /api-docs).  LIVE GEVERIFIEERD (25-6-2026): GEEN auth-header nodig; JSON:API-formaat.
Endpoints:
    GET /api/v1/measures            -> {data:[{id, type:"measure", attributes:{...}}]}  (192 measures)
    GET /api/v1/measures/{id}       -> 1 measure
    GET /api/v1/categories , /subcategories
Per measure (attributes): name, unit, rcValue, uValue, thicknessInMm, isBiobased, isComplex,
    regularCosts[]   = de m2-brackets   (elk: id=catalogcode bv. V1-1-A1, contractorValuePerUnit
                       = prijs incl. btw, diyValuePerUnit, minUnits/maxUnits = m2-bracket, unit, notes)
    additionalCosts[]= de X-meerwerkposten (id bv. V1-1-X8; costableType "Subcategory" => GEDEELD
                       binnen de subcategorie => DEDUPE op code), contractorValuePerUnit incl. btw.

We FLATTEN dit naar de bestaande catalog.json-structuur (code/onderdeel/level/omschrijving/eenheid/
prijs_per_eenheid_excl/_incl_btw) zodat engine/measure_engine + price + validator ongewijzigd blijven.
Extra velden (rc_waarde/u_waarde/dikte_mm/biobased) worden TOEGEVOEGD (niet-brekend; bruikbaar door de
maatregel-selectie). De code ('V1-1-A1') is de join-key en komt 1-op-1 uit de API.

Richtingen:
  --refresh             LIVE ophalen -> catalog.json herschrijven (oude -> catalog.json.bak)
  --map-json <pad>      offline een opgeslagen API-response (out/catalog_api_raw.json) mappen
  --out <pad>           doelbestand (default catalog/catalog.json; gebruik bv. catalog_api.json om te vergelijken)

BTW: contractorValuePerUnit = incl. btw (live geverifieerd: V1-1-A1 -> 23.09 ~= catalog 23.0867).
excl. = incl / 1.21.  Versie wordt op de ophaaldatum gepind (de API geeft zelf geen versielabel).
"""
import os, sys, json, argparse, datetime, shutil, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# code-prefix -> onderdeel/level, consistent met de huidige catalog.json
ONDERDEEL_BY_PREFIX = {"V1": "A Gevel", "V2": "B Glas en kozijnen", "V3": "C Vloeren",
                       "V4": "D Daken", "V5": "E Ventilatie", "V6": "E Ventilatie"}
LEVEL_BY_PREFIX = {"V1": "Level 1 - GEVEL", "V2": "Level 2 - BEGLAZING EN  KOZIJNEN",
                   "V3": "Level 3 - VLOER", "V4": "Level 4 - DAK",
                   "V5": "Level 5 - VENTILATIE", "V6": "Level 6 - KIERDICHTING"}
BTW = 1.21


def load_env(path):
    env = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    for k in ("NIJBEGUN_API_KEY", "NIJBEGUN_API_BASE"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


def _to_float(v):
    if v is None:
        return None
    try:
        return float(str(v).replace(",", "."))
    except (ValueError, TypeError):
        return None


def _num(x):
    """3.0 -> '3', 3.5 -> '3.5' (voor de bracket-tekst)."""
    f = _to_float(x)
    if f is None:
        return ""
    return str(int(f)) if f == int(f) else ("%g" % f)


def _bracket_tekst(minU, maxU, unit):
    lo, hi = _num(minU), _num(maxU)
    u = unit or "m²"
    if hi:
        return "van %s %s tot %s %s" % (lo or "0", u, hi, u)
    if lo and lo != "0":
        return "vanaf %s %s" % (lo, u)
    return ""


def _schoon_notitie(s):
    s = (s or "").strip()
    for pre in ("Betreft:", "Opmerking:"):
        if s.startswith(pre):
            s = s[len(pre):].strip()
    return s


class NijBegunCatalogClient:
    def __init__(self, env):
        self.base = env.get("NIJBEGUN_API_BASE", "https://api.nij-begun.project.abl.nu").rstrip("/")
        self.key = env.get("NIJBEGUN_API_KEY", "")    # live niet nodig; meegestuurd indien aanwezig

    def _get(self, path):
        req = urllib.request.Request(self.base + path)
        req.add_header("Accept", "application/json")
        if self.key:
            req.add_header("Authorization", "Bearer " + self.key)
        with urllib.request.urlopen(req, timeout=45) as r:
            return json.loads(r.read().decode("utf-8"))

    def fetch_measures(self):
        return self._get("/api/v1/measures")


def _attr(node):
    """JSON:API-node -> (id, attributes)."""
    if not isinstance(node, dict):
        return None, {}
    return node.get("id"), (node.get("attributes") or {})


def map_measures_to_catalog(raw, versie=None):
    """LIVE API-response (JSON:API) -> catalog.json-structuur (gevlakt over brackets + X-codes)."""
    data = raw.get("data") if isinstance(raw, dict) else raw
    if not isinstance(data, list):
        data = []
    rows = []
    seen = set()                     # dedupe op code (X-codes zijn gedeeld binnen een subcategorie)

    def add(code, onderdeel, level, oms, eenheid, incl, extra=None):
        if not code or code in seen:
            return
        seen.add(code)
        incl = _to_float(incl)
        excl = round(incl / BTW, 4) if incl is not None else None
        row = {
            "code": code,
            "onderdeel": onderdeel,
            "level": level,
            "omschrijving": oms.strip(),
            "eenheid": eenheid or "m²",
            "prijs_per_eenheid_excl": excl,
            "prijs_per_eenheid_incl_btw": round(incl, 4) if incl is not None else None,
        }
        if extra:
            row.update({k: v for k, v in extra.items() if v not in (None, "")})
        rows.append(row)

    for node in data:
        mid, at = _attr(node)
        prefix = (mid or "")[:2]
        onderdeel = ONDERDEEL_BY_PREFIX.get(prefix, "")
        level = LEVEL_BY_PREFIX.get(prefix, "")
        naam = (at.get("name") or "").strip()
        extra = {
            "rc_waarde": _to_float(at.get("rcValue")),
            "u_waarde": _to_float(at.get("uValue")),
            "dikte_mm": _to_float(at.get("thicknessInMm")),
            "biobased": bool(at.get("isBiobased")) or None,
        }
        # 1) regular costs = de m2-brackets (elk een eigen catalogcode A1/A2/...)
        for c in (at.get("regularCosts") or []):
            cid, ca = _attr(c)
            prefix_c = (cid or "")[:2]
            br = _bracket_tekst(ca.get("minUnits"), ca.get("maxUnits"), ca.get("unit") or at.get("unit"))
            oms = (naam + (" " + br if br else "")).strip()
            add(cid or mid,
                ONDERDEEL_BY_PREFIX.get(prefix_c, onderdeel),
                LEVEL_BY_PREFIX.get(prefix_c, level),
                oms, ca.get("unit") or at.get("unit"),
                ca.get("contractorValuePerUnit"), extra)
        # 2) additional costs = de X-meerwerkposten (gedeeld -> dedupe op code)
        for c in (at.get("additionalCosts") or []):
            cid, ca = _attr(c)
            prefix_c = (cid or "")[:2]
            add(cid,
                ONDERDEEL_BY_PREFIX.get(prefix_c, onderdeel),
                LEVEL_BY_PREFIX.get(prefix_c, level),
                _schoon_notitie(ca.get("notes")) or naam, ca.get("unit"),
                ca.get("contractorValuePerUnit"))

    return {
        "bron": "Nij Begun catalogus-API (api.nij-begun.project.abl.nu)",
        "versie": versie or ("api-live_" + datetime.date.today().isoformat()),
        "gegenereerd_op": datetime.date.today().isoformat(),
        "aantal_maatregelen": len(rows),
        "maatregelen": rows,
    }


def write_catalog(catalog, out_path):
    if os.path.exists(out_path):                # back-up van de huidige catalogus
        shutil.copy2(out_path, out_path + ".bak")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(catalog, fh, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser(description="Nij Begun catalogus-API -> catalog.json")
    ap.add_argument("--refresh", action="store_true", help="live ophalen en catalog.json herschrijven")
    ap.add_argument("--map-json", help="offline: een opgeslagen API-response mappen")
    ap.add_argument("--env", default=os.path.join(ROOT, ".env"))
    ap.add_argument("--out", default=os.path.join(HERE, "catalog.json"))
    a = ap.parse_args()

    if a.map_json:
        raw = json.load(open(a.map_json, encoding="utf-8"))
    elif a.refresh:
        env = load_env(a.env)
        try:
            raw = NijBegunCatalogClient(env).fetch_measures()
        except urllib.error.URLError as e:
            print("FOUT: kon de API niet bereiken (%s). Internet nodig; vanaf de tool-sandbox lukt dit niet."
                  % getattr(e, "reason", e))
            sys.exit(2)
        os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
        json.dump(raw, open(os.path.join(ROOT, "out", "catalog_api_raw.json"), "w"), ensure_ascii=False, indent=1)
        print("  ruwe API-response -> out/catalog_api_raw.json")
    else:
        print("Geef --refresh (live) of --map-json <pad> (offline) op."); sys.exit(1)

    catalog = map_measures_to_catalog(raw)
    if not catalog["maatregelen"]:
        print("FOUT: 0 maatregelen gemapt. Check de JSON:API-structuur tegen out/catalog_api_raw.json.")
        sys.exit(1)
    write_catalog(catalog, a.out)
    print("OK: %s | %d catalogrijen | versie %s" % (a.out, catalog["aantal_maatregelen"], catalog["versie"]))


if __name__ == "__main__":
    main()
