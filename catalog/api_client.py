"""
Nij Begun Maatregelencatalogus-API -> catalog.json (live actualiseren).

API-docs: https://api.nij-begun.project.abl.nu/api-docs (Swagger; Rails/ABL).
Toegang (API-sleutel) opvragen via leveranciers@nijbegun.nl. Credentials uit .env:
    NIJBEGUN_API_KEY, NIJBEGUN_API_BASE (default https://api.nij-begun.project.abl.nu)

Twee richtingen:
  --refresh             LIVE ophalen -> catalog.json herschrijven (oude -> catalog.json.bak)
  --map-json <pad>      offline een al opgeslagen API-response mappen (zonder netwerk)

De catalog.json-STRUCTUUR is leidend (code/onderdeel/level/omschrijving/eenheid/
prijs_per_eenheid_excl/_incl_btw) zodat engine + price + validator ongewijzigd blijven werken.
De API-VELDNAMEN zijn defensief (meerdere kandidaten); bevestig ze 1x op een echte response
(zie out/catalog_api_raw.json) en stel zo nodig FIELD_CANDIDATES bij. Versie wordt vastgepind
(auditeerbaar; de catalogus wijzigt, bv. V3 Q2 03-06-2026 met overgangsdatum 13 mei 2026).
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

# kandidaat-veldnamen in de API-response (1e die bestaat wint) — 1x live verifieren
FIELD_CANDIDATES = {
    "code": ("code", "measureCode", "maatregelcode", "id"),
    "omschrijving": ("description", "omschrijving", "name", "title"),
    "eenheid": ("unit", "eenheid", "uom"),
    "excl": ("priceExclVat", "prijs_excl", "priceExcl", "prijsExclBtw", "price_excl_vat"),
    "incl": ("priceInclVat", "prijs_incl", "priceIncl", "prijsInclBtw", "price_incl_vat"),
    "onderdeel": ("part", "onderdeel", "category", "categorie", "level"),
    "versie": ("version", "versie", "catalogVersion"),
}
LIST_CONTAINERS = ("measures", "maatregelen", "items", "data", "results")


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


def _pick(d, key):
    for name in FIELD_CANDIDATES[key]:
        if isinstance(d, dict) and d.get(name) not in (None, ""):
            return d[name]
    return None


def _to_float(v):
    if v is None:
        return None
    try:
        return float(str(v).replace(",", "."))
    except (ValueError, TypeError):
        return None


class NijBegunCatalogClient:
    def __init__(self, env):
        self.base = env.get("NIJBEGUN_API_BASE", "https://api.nij-begun.project.abl.nu").rstrip("/")
        self.key = env.get("NIJBEGUN_API_KEY", "")

    def _get(self, path):
        req = urllib.request.Request(self.base + path)
        # TODO(verify): exacte auth-header (Bearer vs X-API-Key) bij 1e live test
        req.add_header("Authorization", "Bearer " + self.key)
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))

    def fetch_measures(self):
        # TODO(verify): exact endpoint uit Swagger (bv. /measures, /v1/measures, /catalog)
        for path in ("/measures", "/v1/measures", "/catalog/measures", "/maatregelen"):
            try:
                return self._get(path)
            except urllib.error.HTTPError as e:
                if e.code in (401, 403):
                    raise
                continue
        raise RuntimeError("Geen werkend measures-endpoint gevonden; check Swagger + auth.")


def _raw_list(raw):
    if isinstance(raw, list):
        return raw
    for c in LIST_CONTAINERS:
        if isinstance(raw, dict) and isinstance(raw.get(c), list):
            return raw[c]
    return []


def map_measures_to_catalog(raw, versie=None):
    """API-response -> catalog.json-structuur."""
    items = _raw_list(raw)
    maatregelen = []
    for it in items:
        code = _pick(it, "code")
        if not code:
            continue
        code = str(code)
        prefix = code[:2]
        incl = _to_float(_pick(it, "incl"))
        excl = _to_float(_pick(it, "excl"))
        if incl is None and excl is not None:
            incl = round(excl * 1.21, 4)        # 21% btw als incl ontbreekt
        maatregelen.append({
            "code": code,
            "onderdeel": ONDERDEEL_BY_PREFIX.get(prefix, _pick(it, "onderdeel") or ""),
            "level": LEVEL_BY_PREFIX.get(prefix, ""),
            "omschrijving": _pick(it, "omschrijving") or "",
            "eenheid": _pick(it, "eenheid") or "m²",
            "prijs_per_eenheid_excl": excl,
            "prijs_per_eenheid_incl_btw": incl,
        })
    if versie is None and isinstance(raw, dict):
        versie = _pick(raw, "versie")
    return {
        "bron": "Nij Begun catalogus-API",
        "versie": versie or ("api_" + datetime.date.today().isoformat()),
        "gegenereerd_op": datetime.date.today().isoformat(),
        "aantal_maatregelen": len(maatregelen),
        "maatregelen": maatregelen,
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
        if not env.get("NIJBEGUN_API_KEY"):
            print("FOUT: NIJBEGUN_API_KEY ontbreekt in .env (opvragen: leveranciers@nijbegun.nl)")
            sys.exit(1)
        raw = NijBegunCatalogClient(env).fetch_measures()
        os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
        json.dump(raw, open(os.path.join(ROOT, "out", "catalog_api_raw.json"), "w"), indent=2)
        print("  ruwe API-response -> out/catalog_api_raw.json (verifieer de veldnamen!)")
    else:
        print("Geef --refresh (live) of --map-json <pad> (offline) op."); sys.exit(1)

    catalog = map_measures_to_catalog(raw)
    if not catalog["maatregelen"]:
        print("FOUT: 0 maatregelen gemapt. Check FIELD_CANDIDATES/containers tegen de response.")
        sys.exit(1)
    write_catalog(catalog, a.out)
    print("OK: %s | %d maatregelen | versie %s" % (a.out, catalog["aantal_maatregelen"], catalog["versie"]))


if __name__ == "__main__":
    main()
