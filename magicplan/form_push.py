"""
MagicPlan custom-forms bijwerken vanuit code (i.p.v. de wisselvallige web-editor).

Voegt de velden uit `magicplan/forms/additions.json` toe aan de bestaande forms (NA de juiste sectie),
zet required-vlaggen, en publiceert. IDEMPOTENT: een veld dat al bestaat (zelfde naam) wordt overgeslagen,
dus je kunt dit veilig opnieuw draaien.

De merge + validatie zijn PURE functies en worden offline getest (tests/run_tests.py + dit bestand met
--form-file). De LIVE stappen (fetch/save/publish) draai je zelf met internet + .env:

    python magicplan/form_push.py --form-file out/probe2_forms_338499d4-...json   # OFFLINE dry-run (toont diff)
    python magicplan/form_push.py --live                                          # fetch + merge + valideer (geen push)
    python magicplan/form_push.py --live --publish                                # daadwerkelijk opslaan + publiceren

Auth: .env in de repo-root met MAGICPLAN_API_KEY + MAGICPLAN_CUSTOMER_ID (zoals magicplan/extractor.py).
Save-valkuilen die dit script afhandelt (eerder live geleerd): context = string-array ["plan"];
ALLE `name_escaped`-velden strippen; anders weigert de API met "Form is invalid".
"""
import os, sys, json, argparse, copy
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ADDITIONS = os.path.join(HERE, "forms", "additions.json")
# LIVE-GEVERIFIEERD 25-6-2026 (zie memory magicplan-form-api): base = /api (NIET /api/v2). Project-forms via
# /custom-forms/{list,create,save,publish}, element-fields via /custom-fields/*. Publish-body = RAUWE ARRAY van
# workgroup-id-strings. De BEWEZEN live-route is de browserconsole (cookie + X-CSRF-Token); de hele VABI-
# herstructurering (Object/Constructies/Installaties + override-fields) is zo doorgevoerd. Dit script (offline
# merge + validatie) blijft de back-up/CI-route; de .env-key-auth voor save/publish is niet apart geverifieerd.
BASE_URL = "https://cloud.magicplan.app/api"


# ---------------- pure helpers (offline testbaar) ----------------
def load_additions(path=ADDITIONS):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _form_of(record):
    """Haal de form-definitie (met children) uit een API-record of een ruwe form-dict."""
    if isinstance(record, dict) and "form" in record and isinstance(record["form"], dict):
        return record["form"]
    if isinstance(record, dict) and "data" in record:        # API-dump: {"data": {...}}
        return _form_of(record["data"])
    return record


def _children(form):
    return form.setdefault("children", [])


def _existing_names(form):
    """Alle reeds aanwezige vraag-/sectienamen (lowercased) — recursief (incl. conditionele kinderen)."""
    out = set()

    def rec(nodes):
        for n in nodes or []:
            if isinstance(n, dict):
                if n.get("name"):
                    out.add(n["name"].strip().lower())
                rec(n.get("children"))
    rec(_children(form))
    return out


def _gen_id(used, prefix="addq"):
    i = 1
    while True:
        cid = "%s%04d" % (prefix, i)
        if cid not in used:
            used.add(cid)
            return cid
        i += 1


def _make_node(spec, used, comparison=None):
    """Bouw één question-node (list/number/bool/text/image) + eventuele conditionele kinderen."""
    node = {"id": _gen_id(used), "name": spec["name"], "type": "question",
            "dataType": spec.get("dataType", "text"),
            "comparisonValue": comparison, "required": bool(spec.get("required", False))}
    if spec.get("options"):
        node["fields"] = {"options": list(spec["options"])}
    kids = spec.get("children")
    if kids:   # conditioneel: kinderen tonen wanneer deze (bool) vraag waar is (comparisonValue=1)
        node["children"] = [_make_node(k, used, comparison=1) for k in kids]
    return node


def _all_ids(form):
    used = set()

    def rec(nodes):
        for n in nodes or []:
            if isinstance(n, dict):
                if n.get("id"):
                    used.add(n["id"])
                rec(n.get("children"))
    rec(_children(form))
    return used


def _section_indices(form):
    """{sectienaam_lower: index} van de section-markers in de platte children-lijst."""
    idx = {}
    for i, n in enumerate(_children(form)):
        if isinstance(n, dict) and n.get("type") == "section" and n.get("name"):
            idx[n["name"].strip().lower()] = i
    return idx


def apply_additions(form, form_add):
    """Voeg ontbrekende velden toe NA de genoemde sectie. Geeft (form, toegevoegde_namen)."""
    have = _existing_names(form)
    used = _all_ids(form)
    added = []
    kids = _children(form)
    for sectie, velden in (form_add.get("add_after_section") or {}).items():
        sidx = _section_indices(form).get(sectie.strip().lower())
        # bepaal invoegpositie: net na de laatste vraag van deze sectie (vóór de volgende section/eind)
        if sidx is None:
            insert_at = len(kids)        # sectie niet gevonden -> achteraan
        else:
            insert_at = sidx + 1
            while insert_at < len(kids) and kids[insert_at].get("type") != "section":
                insert_at += 1
        for spec in velden:
            if spec["name"].strip().lower() in have:
                continue                 # bestaat al -> idempotent overslaan
            node = _make_node(spec, used)
            kids.insert(insert_at, node)
            insert_at += 1
            have.add(spec["name"].strip().lower())
            added.append(spec["name"])
    return form, added


def apply_required(form, names):
    """Zet required=True op vragen met een naam uit `names`. Geeft de lijst gezette namen."""
    want = {n.strip().lower() for n in names}
    done = []

    def rec(nodes):
        for n in nodes or []:
            if isinstance(n, dict):
                if n.get("type") == "question" and (n.get("name", "").strip().lower() in want) and not n.get("required"):
                    n["required"] = True
                    done.append(n["name"])
                rec(n.get("children"))
    rec(_children(form))
    return done


def apply_optional(form, names):
    """Zet required=False op vragen met een naam uit `names` (spiegelbeeld van apply_required).
    Zo hoeft de adviseur die velden niet meer in te vullen — de tool defaultt ze (bv. raam: alleen
    Type glas verplicht; Kozijnmateriaal/Toevoerrooster/Raam-paneel optioneel)."""
    want = {n.strip().lower() for n in names}
    done = []

    def rec(nodes):
        for n in nodes or []:
            if isinstance(n, dict):
                if n.get("type") == "question" and (n.get("name", "").strip().lower() in want) and n.get("required"):
                    n["required"] = False
                    done.append(n["name"])
                rec(n.get("children"))
    rec(_children(form))
    return done


def apply_default_first(form, name_to_default):
    """Zet de default-optie VOORAAN in de options-lijst van een list-vraag (MagicPlan toont de eerste
    bovenaan). Veilig: geen onbekende JSON-sleutels — alleen de bestaande options herordenen."""
    want = {k.strip().lower(): v for k, v in (name_to_default or {}).items()}
    done = []

    def rec(nodes):
        for n in nodes or []:
            if isinstance(n, dict):
                nm = n.get("name", "").strip().lower()
                opts = (n.get("fields") or {}).get("options")
                if n.get("type") == "question" and nm in want and isinstance(opts, list):
                    dv = want[nm]
                    hit = next((o for o in opts if str(o).strip().lower() == str(dv).strip().lower()), None)
                    if hit is not None and opts and opts[0] != hit:
                        opts.remove(hit)
                        opts.insert(0, hit)
                        done.append(n["name"])
                rec(n.get("children"))
    rec(_children(form))
    return done


def strip_name_escaped(obj):
    """Verwijder ALLE name_escaped-velden recursief (anders weigert de save-API)."""
    if isinstance(obj, dict):
        obj.pop("name_escaped", None)
        for v in obj.values():
            strip_name_escaped(v)
    elif isinstance(obj, list):
        for v in obj:
            strip_name_escaped(v)
    return obj


def normalize_context(form):
    """context moet een string-array zijn (bv. ['plan']), niet de objecten uit de list-API."""
    ctx = form.get("context")
    if isinstance(ctx, list):
        form["context"] = [c.get("type", c) if isinstance(c, dict) else c for c in ctx] or ["plan"]
    elif not ctx:
        form["context"] = ["plan"]
    return form


_VALID_DT = {"list", "number", "text", "bool", "image", "datetime"}


def validate(form):
    """Structurele check vóór save. Geeft een lijst problemen (leeg = ok)."""
    problems = []
    if not isinstance(form.get("context"), list) or not all(isinstance(c, str) for c in form["context"]):
        problems.append("context moet een string-array zijn (bv. ['plan'])")

    def rec(nodes, path="children"):
        for i, n in enumerate(nodes or []):
            p = "%s[%d]" % (path, i)
            if not isinstance(n, dict):
                problems.append("%s: geen object" % p); continue
            if "name_escaped" in n:
                problems.append("%s: name_escaped niet gestript" % p)
            if not n.get("id"):
                problems.append("%s: id ontbreekt" % p)
            if not n.get("name"):
                problems.append("%s: name ontbreekt" % p)
            t = n.get("type")
            if t not in ("section", "question"):
                problems.append("%s: type %r ongeldig" % (p, t))
            if t == "question" and n.get("dataType") not in _VALID_DT:
                problems.append("%s: dataType %r ongeldig" % (p, n.get("dataType")))
            rec(n.get("children"), p + "/children")
    rec(_children(form))
    # dubbele ids
    ids = [x for x in _all_ids(form)]
    if len(ids) != len(set(ids)):
        problems.append("dubbele veld-ids")
    return problems


def merge_record(record, additions, verbose=True):
    """Pas additions + required toe op één form-record. Geeft (record, added, required_done, problems)."""
    form = _form_of(record)
    name = (form.get("name") or "").strip()
    form_add = next((f for f in additions.get("forms", []) if f.get("form_match", "").lower() in name.lower()), None)
    added, req_done = [], []
    if form_add:
        _, added = apply_additions(form, form_add)
    req_names = [r["name"] for r in additions.get("set_required", [])
                 if r.get("form_match", "").lower() in name.lower()]
    if req_names:
        req_done = apply_required(form, req_names)
    opt_names = [r["name"] for r in additions.get("set_optional", [])
                 if r.get("form_match", "").lower() in name.lower()]
    opt_done = apply_optional(form, opt_names) if opt_names else []
    defaults = {r["name"]: r["default"] for r in additions.get("set_default", [])
                if r.get("form_match", "").lower() in name.lower() and r.get("default") is not None}
    def_done = apply_default_first(form, defaults) if defaults else []
    strip_name_escaped(record)
    normalize_context(form)
    problems = validate(form)
    if verbose:
        print("  form %-16s | +%d veld(en) %s | required: %s | optioneel: %s | default-eerst: %s%s" % (
            name, len(added), added or "", req_done or "-", opt_done or "-", def_done or "-",
            "" if not problems else " | PROBLEMEN: %d" % len(problems)))
    return record, added, req_done, problems


# ---------------- live HTTP (zelf draaien met internet + .env) ----------------
def _load_env():
    env = {}
    p = os.path.join(ROOT, ".env")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _headers(env):
    return {"key": env.get("MAGICPLAN_API_KEY", ""), "customer": env.get("MAGICPLAN_CUSTOMER_ID", ""),
            "Content-Type": "application/json", "Accept": "application/json"}


def _http(method, url, headers, body=None):
    import urllib.request
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8") or "{}")


def fetch_forms(env):
    return _http("GET", BASE_URL + "/custom-forms/list/", _headers(env)).get("data", [])


def save_and_publish(env, record):
    rec_id = record.get("id") or _form_of(record).get("id")
    _http("POST", BASE_URL + "/custom-forms/save", _headers(env),
          {"id": rec_id, "form": _form_of(record)})
    _http("POST", BASE_URL + "/custom-forms/publish/%s" % rec_id, _headers(env))
    return rec_id


def main():
    ap = argparse.ArgumentParser(description="MagicPlan custom-forms bijwerken (additions.json)")
    ap.add_argument("--form-file", help="OFFLINE: één opgeslagen form-dump (JSON) i.p.v. de live API")
    ap.add_argument("--live", action="store_true", help="forms via de MagicPlan-API ophalen (.env nodig)")
    ap.add_argument("--publish", action="store_true", help="daadwerkelijk opslaan + publiceren (impliceert --live)")
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "forms_merged"), help="map voor de gemergede JSON's")
    a = ap.parse_args()
    additions = load_additions()

    if a.form_file:
        rec = json.load(open(a.form_file, encoding="utf-8"))
        records = [rec]
    elif a.live or a.publish:
        env = _load_env()
        if not env.get("MAGICPLAN_API_KEY"):
            print("Geen MAGICPLAN_API_KEY in .env — kan niet live ophalen."); sys.exit(2)
        records = fetch_forms(env)
    else:
        print("Geef --form-file <json> (offline) of --live (API). Zie --help."); sys.exit(2)

    os.makedirs(a.out, exist_ok=True)
    any_problem = False
    for rec in records:
        rec, added, req_done, problems = merge_record(rec, additions)
        form = _form_of(rec)
        name = (form.get("name") or "form").strip().replace(" ", "_")
        json.dump(rec, open(os.path.join(a.out, "%s.json" % name), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        if problems:
            any_problem = True
            for pr in problems:
                print("     ! " + pr)
        if a.publish and not problems:
            rid = save_and_publish(_load_env(), rec)
            print("     -> gepubliceerd: %s (%s)" % (name, rid))
    print("\nGemergede JSON's in: %s" % a.out)
    if any_problem:
        print("LET OP: er zijn validatieproblemen — NIET publiceren tot ze opgelost zijn.")
        sys.exit(1)
    if not a.publish:
        print("Dry-run klaar. Controleer de JSON's; draai met --live --publish om door te voeren.")


if __name__ == "__main__":
    main()
