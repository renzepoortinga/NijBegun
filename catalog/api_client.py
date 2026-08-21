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
excl. = incl / 1.21. De API geeft geen inhoudelijk versielabel; fingerprint + UTC-ophaaltijd pinnen de stand.
"""
import os, sys, json, argparse, datetime, hashlib, math, tempfile, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# code-prefix -> onderdeel/level, consistent met de huidige catalog.json
ONDERDEEL_BY_PREFIX = {"V1": "A Gevel", "V2": "B Glas en kozijnen", "V3": "C Vloeren",
                       "V4": "D Daken", "V5": "E Ventilatie", "V6": "E Ventilatie"}
LEVEL_BY_PREFIX = {"V1": "Level 1 - GEVEL", "V2": "Level 2 - BEGLAZING EN  KOZIJNEN",
                   "V3": "Level 3 - VLOER", "V4": "Level 4 - DAK",
                   "V5": "Level 5 - VENTILATIE", "V6": "Level 6 - KIERDICHTING"}
BTW = 1.21
API_SPEC_VERSION = "1.0"
API_SOURCE = "https://api.nij-begun.project.abl.nu/api/v1/measures"


def load_env(path):
    env = {}
    if path and os.path.exists(path):
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


def _canonical(value):
    """Normaliseer JSON zodat API-volgorde de inhoudsfingerprint niet beinvloedt."""
    if isinstance(value, dict):
        return {key: _canonical(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        normalized = [_canonical(item) for item in value]
        return sorted(normalized, key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False,
                                                               separators=(",", ":")))
    return value


def content_fingerprint(mapped_rows):
    """Fingerprint exact de gevalideerde, gemapte catalogusinhoud (zonder vluchtige metadata)."""
    payload = json.dumps(_canonical(mapped_rows), sort_keys=True, ensure_ascii=False,
                         separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _category(at, measure_id):
    """Haal de categorie uit de API-relaties; codes zoals B5 erven dus correct V5."""
    category = at.get("category") or {}
    category_id, category_at = _attr(category)
    subcategory = at.get("subcategory") or {}
    _, subcategory_at = _attr(subcategory)
    category_id = category_id or subcategory_at.get("categoryCode")
    if not category_id and (measure_id or "").startswith("V"):
        category_id = (measure_id or "").split("-", 1)[0]
    name = (category_at.get("name") or "").strip()
    onderdeel = ONDERDEEL_BY_PREFIX.get(category_id, "")
    level = LEVEL_BY_PREFIX.get(category_id, "")
    if category_id and name:
        onderdeel = onderdeel or "%s %s" % (chr(64 + int(category_id[1:])), name)
        level = level or "Level %s - %s" % (category_id[1:], name.upper())
    return category_id, onderdeel, level


def validate_catalog(catalog):
    errors = []
    seen = set()
    for index, row in enumerate(catalog.get("maatregelen") or []):
        code = row.get("code")
        for field in ("code", "onderdeel", "level"):
            if not str(row.get(field) or "").strip():
                errors.append("rij %d: leeg %s" % (index + 1, field))
        price = row.get("prijs_per_eenheid_incl_btw")
        # Negatieve bedragen zijn geldige minderprijzen; niet-numeriek/NaN/Infinity nooit.
        if (not isinstance(price, (int, float)) or isinstance(price, bool)
                or not math.isfinite(price)):
            errors.append("%s: ongeldige prijs %r" % (code or "rij %d" % (index + 1), price))
        if code in seen:
            errors.append("dubbele code %s" % code)
        seen.add(code)
    if errors:
        raise ValueError("Ongeldige catalogus:\n- " + "\n- ".join(errors))
    return True


def map_measures_to_catalog(raw, versie=None, opgehaald_op=None):
    """LIVE API-response (JSON:API) -> catalog.json-structuur (gevlakt over brackets + X-codes)."""
    data = raw.get("data") if isinstance(raw, dict) else raw
    if not isinstance(data, list):
        data = []
    by_code = {}                     # X-codes zijn soms identiek gedeeld binnen een subcategorie

    def add(code, onderdeel, level, oms, eenheid, incl, extra=None):
        if not code:
            return
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
        existing = by_code.get(code)
        if existing is not None and existing != row:
            raise ValueError("Conflicterende dubbele cataloguscode %s" % code)
        by_code[code] = row           # identieke duplicaten expliciet en deterministisch dedupliceren

    for node in data:
        mid, at = _attr(node)
        _, onderdeel, level = _category(at, mid)
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
            br = _bracket_tekst(ca.get("minUnits"), ca.get("maxUnits"), ca.get("unit") or at.get("unit"))
            oms = (naam + (" " + br if br else "")).strip()
            add(cid or mid,
                onderdeel, level,
                oms, ca.get("unit") or at.get("unit"),
                ca.get("contractorValuePerUnit"), extra)
        # 2) additional costs = de X-meerwerkposten (gedeeld -> dedupe op code)
        for c in (at.get("additionalCosts") or []):
            cid, ca = _attr(c)
            add(cid,
                onderdeel, level,
                _schoon_notitie(ca.get("notes")) or naam, ca.get("unit"),
                ca.get("contractorValuePerUnit"))

    rows = [by_code[code] for code in sorted(by_code)]
    fingerprint = content_fingerprint(rows)
    fetched = opgehaald_op or datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    catalog = {
        "bron": API_SOURCE,
        "api_specversie": API_SPEC_VERSION,
        "versie": versie or "api-spec-1.0+" + fingerprint.split(":", 1)[1][:12],
        "opgehaald_op": fetched,
        "contentfingerprint": fingerprint,
        "gegenereerd_op": fetched[:10],
        "aantal_maatregelen": len(rows),
        "maatregelen": rows,
    }
    validate_catalog(catalog)
    return catalog


def compare_catalogs(previous, current):
    old = {row["code"]: row for row in previous.get("maatregelen", [])}
    new = {row["code"]: row for row in current.get("maatregelen", [])}
    fields = ("onderdeel", "level", "omschrijving", "eenheid", "prijs_per_eenheid_excl",
              "prijs_per_eenheid_incl_btw", "rc_waarde", "u_waarde", "dikte_mm", "biobased")
    changed = []
    for code in sorted(old.keys() & new.keys()):
        differences = {field: {"was": old[code].get(field), "wordt": new[code].get(field)}
                       for field in fields if old[code].get(field) != new[code].get(field)}
        if differences:
            changed.append({"code": code, "verschillen": differences})
    return {"toegevoegd": sorted(new.keys() - old.keys()), "verwijderd": sorted(old.keys() - new.keys()),
            "gewijzigd": changed}


def render_diff_report(diff, previous, current):
    lines = ["# Verschilrapport maatregelencatalogus", "",
             "Vergelijking van `%s` met API-fingerprint `%s`." %
             (previous.get("versie", "onbekend"), current["contentfingerprint"]), "",
             "- Toegevoegd: %d" % len(diff["toegevoegd"]),
             "- Verwijderd: %d" % len(diff["verwijderd"]),
             "- Inhoudelijk gewijzigd: %d" % len(diff["gewijzigd"]), "",
             "## Toegevoegde codes", "", ", ".join(diff["toegevoegd"]) or "Geen.", "",
             "## Verwijderde codes", "", ", ".join(diff["verwijderd"]) or "Geen.", "",
             "## Gewijzigde codes", ""]
    for item in diff["gewijzigd"]:
        details = []
        for field, values in item["verschillen"].items():
            details.append("%s: `%s` -> `%s`" % (field, values["was"], values["wordt"]))
        lines.append("- **%s** — %s" % (item["code"], "; ".join(details)))
    return "\n".join(lines) + "\n"


def _stage_bytes(path, payload):
    directory = os.path.dirname(os.path.abspath(path))
    fd, temp_path = tempfile.mkstemp(prefix=".catalog-stage-", dir=directory)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        return temp_path
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def publish_outputs(catalog, out_path, report_path=None, report_text=None,
                    stage_func=_stage_bytes, replace_func=os.replace):
    """Publiceer catalogus + optioneel rapport als transactie, met rollback bij replace-fout."""
    targets = [(os.path.abspath(out_path),
                (json.dumps(catalog, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))]
    if report_path is not None:
        if report_text is None:
            raise ValueError("report_text ontbreekt")
        targets.append((os.path.abspath(report_path), report_text.encode("utf-8")))
    paths = [path for path, _ in targets]
    if len(set(os.path.normcase(path) for path in paths)) != len(paths):
        raise ValueError("Catalogus en verschilrapport mogen niet hetzelfde pad zijn")
    for path in paths:
        directory = os.path.dirname(path)
        if not os.path.isdir(directory):
            raise ValueError("Doelmap bestaat niet: %s" % directory)

    staged, rollback, published = {}, {}, []
    try:
        # Eerst alle nieuwe én oude inhoud duurzaam stagen; tot hier blijft zichtbare staat intact.
        for path, payload in targets:
            staged[path] = stage_func(path, payload)
            rollback[path] = stage_func(path, open(path, "rb").read()) if os.path.exists(path) else None
        for path, _ in targets:
            replace_func(staged[path], path)
            staged[path] = None
            published.append(path)
    except Exception:
        for path in reversed(published):
            old = rollback.get(path)
            if old is None:
                try:
                    os.unlink(path)
                except FileNotFoundError:
                    pass
            else:
                os.replace(old, path)
                rollback[path] = None
        raise
    finally:
        for temp_path in list(staged.values()) + list(rollback.values()):
            if temp_path:
                try:
                    os.unlink(temp_path)
                except FileNotFoundError:
                    pass


def main(argv=None):
    ap = argparse.ArgumentParser(description="Nij Begun catalogus-API -> catalog.json")
    source = ap.add_mutually_exclusive_group(required=True)
    source.add_argument("--refresh", action="store_true", help="live ophalen en catalog.json herschrijven")
    source.add_argument("--map-json", help="offline: een opgeslagen API-response mappen")
    ap.add_argument("--env", help="optioneel env-bestand; publieke API vereist dit niet")
    ap.add_argument("--out", default=os.path.join(HERE, "catalog.json"))
    ap.add_argument("--previous", help="vorige catalogus voor verschilrapport (default: bestaand --out)")
    ap.add_argument("--diff-report", help="schrijf controleerbaar Markdown-verschilrapport")
    a = ap.parse_args(argv)

    previous_path = a.previous or a.out
    if a.diff_report and not os.path.isfile(previous_path):
        print("FOUT: --diff-report vereist een bestaande vorige catalogus")
        return 1
    if os.path.abspath(a.out) == os.path.abspath(a.diff_report or ""):
        print("FOUT: catalogus en verschilrapport mogen niet hetzelfde pad zijn")
        return 1
    for target in (a.out, a.diff_report):
        if target and not os.path.isdir(os.path.dirname(os.path.abspath(target))):
            print("FOUT: doelmap bestaat niet: %s" % os.path.dirname(os.path.abspath(target)))
            return 1

    if a.map_json:
        raw = json.load(open(a.map_json, encoding="utf-8"))
    elif a.refresh:
        env = load_env(a.env)
        try:
            raw = NijBegunCatalogClient(env).fetch_measures()
        except urllib.error.URLError as e:
            print("FOUT: kon de API niet bereiken (%s). Internet nodig; vanaf de tool-sandbox lukt dit niet."
                  % getattr(e, "reason", e))
            return 2
    if os.path.exists(previous_path):
        with open(previous_path, encoding="utf-8") as fh:
            previous = json.load(fh)
    else:
        previous = None
    try:
        catalog = map_measures_to_catalog(raw)
    except ValueError as exc:
        print("FOUT: %s" % exc)
        return 1
    if not catalog["maatregelen"]:
        print("FOUT: 0 maatregelen gemapt. Check de JSON:API-structuur tegen out/catalog_api_raw.json.")
        return 1
    report_text = None
    if a.diff_report:
        report_text = render_diff_report(compare_catalogs(previous, catalog), previous, catalog)
    publish_outputs(catalog, a.out, a.diff_report, report_text)
    print("OK: %s | %d catalogrijen | versie %s" % (a.out, catalog["aantal_maatregelen"], catalog["versie"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
