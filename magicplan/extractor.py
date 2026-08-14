"""
MagicPlan Project Plan API -> canoniek dossier.

Twee richtingen:
  --project-id <ID>   LIVE ophalen via GET {BASE}/projects/{id}/plan (door Renze, met .env)
  --plan-json <pad>   offline mappen van een al opgehaald/voorbeeld plan-JSON

Mapt de v0.3-opnametemplates (zie ../MagicPlan_Forms_Fields_schema_v0.3.json) naar het dossier:
identificatie, opname, geometrie (vloeren+ruimtes), schil (gevel/kozijn), ventilatie en
installaties (verwarming/tapwater/koeling/zonne-energie).

De VELD-keys (postcode, verw_type_opwekker, ...) zijn vast (uit ons schema). Wat we 1x tegen
een echt project moeten BEVESTIGEN is de CONTAINER-structuur: waar MagicPlan de form-antwoorden,
verdiepingen, wanden en objecten plaatst. Daarom leest _collect_answers() defensief meerdere
gangbare vormen, en logt onbekende sleutels. Draai live, bekijk out/plan_raw.json, stel zo nodig
de container-namen in EXPECTED_CONTAINERS bij.

Credentials uit .env (NIET in OneDrive bewaren): MAGICPLAN_API_KEY, MAGICPLAN_CUSTOMER_ID, MAGICPLAN_API_BASE
"""
import os, sys, json, math, argparse, ssl, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.dossier import (Dossier, Identificatie, Opname, Geometrie, VloerInfo, Ruimte,  # noqa
                          SchilDeel, Ventilatie, Installaties, Verwarming, Tapwater, Koeling,
                          ZonneEnergieSysteem, Foto, save_json)

# Containers die we 1x live verifieren (eerste alternatief dat bestaat wint).
EXPECTED_CONTAINERS = {
    "floors": ("floors", "stories", "levels", "verdiepingen"),
    "rooms": ("rooms", "spaces", "ruimtes"),
    "walls": ("walls", "wanden"),
    "objects": ("objects", "symbols", "openings", "items"),
    "photos": ("photos", "images", "fotos"),
    "answers": ("customFields", "fields", "answers", "formValues", "forms"),
}


def load_env(path):
    env = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    for k in ("MAGICPLAN_API_KEY", "MAGICPLAN_CUSTOMER_ID", "MAGICPLAN_API_BASE"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


def _ssl_context():
    """Python 3.13+/OpenSSL 3.2+ zet VERIFY_X509_STRICT standaard aan: een strengere RFC 5280-
    profielcheck die cloud.magicplan.app's certificaatketen afwijst ('Basic Constraints of CA cert
    not marked critical') - een reëel maar technisch niet-strikt-conform intermediate-CA-veld, geen
    vervalst certificaat (Windows/curl accepteren dezelfde keten probleemloos, en de rest van het
    internet werkt gewoon vanuit deze machine - dus geen MITM/proxy-probleem). We schakelen ALLEEN
    die ene profielcheck uit; CA-vertrouwen, hostnaam- en verloopcontrole blijven onverkort actief."""
    ctx = ssl.create_default_context()
    ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
    return ctx


class MagicPlanClient:
    def __init__(self, env):
        self.base = env.get("MAGICPLAN_API_BASE", "https://cloud.magicplan.app/api/v2").rstrip("/")
        self.key = env.get("MAGICPLAN_API_KEY", "")
        self.customer = env.get("MAGICPLAN_CUSTOMER_ID", "")

    def _get(self, path):
        req = urllib.request.Request(self.base + path)
        req.add_header("key", self.key)          # MagicPlan REST v2: headers 'key' + 'customer'
        req.add_header("customer", self.customer)
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=30, context=_ssl_context()) as r:
            return json.loads(r.read().decode("utf-8"))

    def get_workspace(self):
        return self._get("/workspace")           # auth-check: 200 = headers kloppen

    def list_projects(self):
        return self._get("/projects")

    def get_project_plan(self, project_id):
        # exacte plan-endpoint 1x bevestigen; probeer de gangbare patronen
        last = None
        for path in ("/projects/%s/plan" % project_id, "/projects/%s" % project_id):
            try:
                return self._get(path)
            except urllib.error.HTTPError as e:
                if e.code in (401, 403):
                    raise
                last = e
        raise RuntimeError("Geen werkend project-endpoint (%s); check Reference." % last)


# ---------- defensieve helpers ----------
def _first(node, names):
    for n in names:
        if isinstance(node, dict) and node.get(n) is not None:
            return node[n]
    return None


def _collect_answers(node):
    """Verzamel form-antwoorden uit een node -> {key_of_label_lower: value}."""
    out = {}
    if not isinstance(node, dict):
        return out
    raw = _first(node, EXPECTED_CONTAINERS["answers"]) or []
    # forms kan een lijst van forms met nested 'fields' zijn
    items = []
    if isinstance(raw, dict):
        for k, v in raw.items():
            out[str(k).lower()] = v
        return out
    for entry in raw:
        if isinstance(entry, dict) and "fields" in entry and isinstance(entry["fields"], list):
            items.extend(entry["fields"])
        else:
            items.append(entry)
    for fa in items:
        if not isinstance(fa, dict):
            continue
        key = fa.get("key") or fa.get("label") or fa.get("name")
        if key is None:
            continue
        out[str(key).lower()] = fa.get("value", fa.get("answer"))
    return out


def _g(ans, key, cast=None, default=None):
    v = ans.get(key.lower())
    if v in (None, ""):
        return default
    if cast is None:
        return v
    try:
        if cast is bool:
            return str(v).strip().lower() in ("true", "1", "ja", "yes", "waar", "y")
        return cast(v)
    except (ValueError, TypeError):
        return default


def _functie(naam):
    n = (naam or "").lower()
    if "keuken" in n: return "keuken"
    if "bad" in n: return "badkamer"
    if "toilet" in n or "wc" in n: return "toilet"
    if "was" in n: return "wasruimte"
    if any(w in n for w in ("hal", "gang", "overloop", "entree", "trap")): return "verkeer"
    if any(w in n for w in ("woon", "slaap", "kamer", "studeer", "zolder")): return "verblijfsruimte"
    return "overig"


# ---------- mapping ----------
def map_plan_to_dossier(plan):
    dos = Dossier()
    p = _collect_answers(plan)

    dos.identificatie = Identificatie(
        bag_vboid=_g(p, "bag_vboid", default="") or "",
        postcode=_g(p, "postcode", default="") or "",
        huisnummer=str(_g(p, "huisnummer", default="") or ""),
        bouwjaar=_g(p, "bouwjaar", int),
        renovatiejaar=_g(p, "renovatiejaar", int),
        woningtype=_g(p, "woningtype", default="") or "",
        aantal_bouwlagen=_g(p, "bouwlagen", int))
    dos.opname = Opname(
        opnamedatum=_g(p, "opnamedatum", default="") or "",
        type_advies=_g(p, "type_advies", default="Basis") or "Basis",
        qv10_gemeten=_g(p, "qv10_gemeten", bool, False),
        qv10_waarde=_g(p, "qv10_waarde", float),
        bewijslast=_g(p, "bewijslast", default="Geen") or "Geen")

    _map_geometrie_en_schil(plan, dos, p)
    _map_ventilatie(p, dos)
    _map_installaties(p, dos)
    _map_fotos(plan, dos)

    dos.meta.tool_versie = "extractor-0.2 (container 1x live verifieren)"
    return dos


def _map_geometrie_en_schil(plan, dos, p):
    """Bouwt schil uit de PROJECT-niveau 'algemeen'-tags (gevel/vloer/dak) + de geometrie uit de
    tekening. Gevels: per buitenwand een vlak met de algemene tags. Vloer/dak: 1 vlak uit footprint
    + tags (dak via helling of handmatig oppervlak). De exacte container-/oriëntatie-uitlezing
    verifieren we 1x op een echte test-opname (zie EXPECTED_CONTAINERS)."""
    geo = Geometrie(gebruiksoppervlakte_ag_m2=_g(p, "ag_m2", float, 0.0) or 0.0)
    floors = _first(plan, EXPECTED_CONTAINERS["floors"]) or []
    gevel_tags = {
        "subtype": _g(p, "geveltype", default="") or "",
        "begrenzing": _g(p, "gevel_begrenzing", default="Buitenlucht") or "Buitenlucht",
        "spouw_aanwezig": _g(p, "spouw_aanwezig", bool),
        "isolatie_aanwezig": _g(p, "isolatie_aanwezig", default="Onbekend") or "Onbekend",
        "rc_bron": _g(p, "rc_bron", default="") or "",
        "isolatie_mm": _g(p, "isolatie_mm", float),
        "rc_huidig": _g(p, "rc_huidig", float),
        "afwijking": _g(p, "gevel_afwijking", default="") or "",
    }
    schil, grond_footprint, top_footprint = [], 0.0, 0.0
    for fi, fl in enumerate(floors, 1):
        fa = _collect_answers(fl)
        naam = fl.get("name") or fa.get("naam") or "Bouwlaag %d" % fi
        opp = float(fl.get("area") or _g(fa, "oppervlakte_m2", float) or 0.0)
        hoogte = fl.get("height") or _g(fa, "plafondhoogte", float) or fl.get("ceilingHeight")
        geo.vloeren.append(VloerInfo(naam=naam, oppervlakte_m2=opp, hoogte_m=hoogte))
        if fi == 1:
            grond_footprint = opp
        top_footprint = opp
        for rm in (_first(fl, EXPECTED_CONTAINERS["rooms"]) or []):
            rnaam = rm.get("name") or "Ruimte"
            geo.ruimtes.append(Ruimte(naam=rnaam, functie=_functie(rnaam),
                                      oppervlakte_m2=float(rm.get("area") or 0)))
        for wi, w in enumerate(_first(fl, EXPECTED_CONTAINERS["walls"]) or [], 1):
            schil.extend(_map_wand(w, "%d-%d" % (fi, wi), gevel_tags))
    for wi, w in enumerate(_first(plan, EXPECTED_CONTAINERS["walls"]) or [], 1):
        schil.extend(_map_wand(w, "p-%d" % wi, gevel_tags))
    schil.append(_maak_vloer(p, grond_footprint))
    schil.append(_maak_dak(p, top_footprint))
    dos.geometrie = geo
    dos.schil = schil


def _map_wand(w, idbase, gevel_tags):
    """Buitenwand -> gevelvlak met de PROJECT-algemeen-tags; geometrie (opp/orientatie) uit de wand.
    Objecten op de wand -> kozijnen."""
    out = []
    exterior = w.get("exterior", w.get("isExterior", w.get("buitenwand")))
    area = float(w.get("area") or 0)
    orient = w.get("orientation") or w.get("orientatie") or ""
    if exterior is not False and area > 0:   # default: schil, tenzij expliciet als binnenwand gemarkeerd
        out.append(SchilDeel(
            id="gevel-%s" % idbase, type="gevel", subtype=gevel_tags["subtype"],
            begrenzing=gevel_tags["begrenzing"], orientatie=orient, oppervlakte_m2=area,
            isolatie_aanwezig=gevel_tags["isolatie_aanwezig"], rc_bron=gevel_tags["rc_bron"],
            spouw_aanwezig=gevel_tags["spouw_aanwezig"], isolatiedikte_mm=gevel_tags["isolatie_mm"],
            rc_huidig=gevel_tags["rc_huidig"], opmerkingen=gevel_tags["afwijking"]))
    for oi, o in enumerate(_first(w, EXPECTED_CONTAINERS["objects"]) or [], 1):
        oa = _collect_answers(o)
        elem = _g(oa, "element", default="")
        if not elem:
            continue
        opp = o.get("area")
        if not opp and o.get("width") and o.get("height"):
            opp = float(o["width"]) * float(o["height"])
        out.append(SchilDeel(
            id="kozijn-%s-%d" % (idbase, oi), type="kozijn", subtype=elem,
            begrenzing=_g(oa, "begrenzing", default="") or "Buitenlucht",
            orientatie=_g(oa, "orientatie", default="") or orient,
            oppervlakte_m2=float(opp or 0),
            glastype=_g(oa, "glastype", default="") or "",
            kozijnmateriaal=_g(oa, "kozijnmateriaal", default="") or "",
            u_huidig=_g(oa, "u_glas", float) or _g(oa, "u_kozijn", float)))
    return out


def _maak_vloer(p, footprint):
    return SchilDeel(
        id="vloer-bg", type="vloer",
        subtype=_g(p, "vloerconstructie", default="") or "",
        begrenzing=_g(p, "vloer_begrenzing", default="") or "",
        orientatie="horizontaal", oppervlakte_m2=round(footprint, 2),
        isolatie_aanwezig=_g(p, "vloer_iso", default="Onbekend") or "Onbekend",
        rc_bron=_g(p, "vloer_rc_bron", default="") or "",
        isolatiedikte_mm=_g(p, "vloer_isolatie_mm", float),
        rc_huidig=_g(p, "vloer_rc", float),
        opmerkingen=_g(p, "vlak_afwijking", default="") or "")


def _maak_dak(p, footprint):
    """Dakoppervlak: handmatig veld wint; anders footprint x hellingfactor (1/cos); anders footprint."""
    helling = _g(p, "dakhelling", float)
    handmatig = _g(p, "dak_oppervlak_m2", float)
    if handmatig:
        opp = handmatig
    elif helling and footprint:
        opp = footprint / max(math.cos(math.radians(helling)), 0.1)
    else:
        opp = footprint
    return SchilDeel(
        id="dak", type="dak",
        subtype=_g(p, "daktype", default="") or "",
        begrenzing="Buitenlucht", orientatie="horizontaal", oppervlakte_m2=round(opp, 2),
        isolatie_aanwezig=_g(p, "dak_iso", default="Onbekend") or "Onbekend",
        rc_bron=_g(p, "dak_rc_bron", default="") or "",
        isolatiedikte_mm=_g(p, "dak_isolatie_mm", float),
        rc_huidig=_g(p, "dak_rc", float),
        hellingshoek=helling, oppervlak_handmatig=handmatig)


def _map_ventilatie(p, dos):
    dos.ventilatie = Ventilatie(
        systeem=_g(p, "vent_systeem", default="") or "",
        systeem_soort=_g(p, "vent_systeem_soort", default="") or "",
        merk=_g(p, "vent_merk", default="") or "",
        wtw_rendement_pct=_g(p, "wtw_rendement", float),
        co2_sturing=_g(p, "vent_co2", bool),
        zelfregelend=_g(p, "vent_zelfregelend", bool),
        tijdsturing=_g(p, "vent_tijdsturing", bool),
        passieve_koeling=_g(p, "vent_passieve_koeling", bool),
        kwaliteitsverklaring=_g(p, "vent_kwaliteitsverklaring", bool),
        subsysteem_code=_g(p, "vent_subsysteem_code", default="") or "")


def _map_installaties(p, dos):
    inst = Installaties()
    inst.verwarming = Verwarming(
        systeem=_g(p, "verw_systeem", default="") or "",
        merk=_g(p, "verw_merk", default="") or "", type=_g(p, "verw_type", default="") or "",
        installatiejaar=_g(p, "verw_installatiejaar", int),
        type_opwekker=_g(p, "verw_type_opwekker", default="") or "",
        subtype=_g(p, "verw_subtype", default="") or "",
        opstelplaats=_g(p, "verw_opstelplaats", default="") or "",
        kwaliteitsverklaring=_g(p, "verw_kwaliteitsverklaring", bool),
        distributiemedium=_g(p, "verw_distributiemedium", default="") or "",
        aanvoertemperatuur=_g(p, "verw_aanvoertemp", default="") or "",
        type_distributie=_g(p, "verw_type_distributie", default="") or "",
        leidingen_onverwarmd=_g(p, "verw_leidingen_onverwarmd", bool),
        afgifte=_g(p, "verw_afgifte", default="") or "",
        regeling=_g(p, "verw_regeling", default="") or "")
    inst.tapwater = Tapwater(
        type_installatie=_g(p, "tap_type_installatie", default="") or "",
        aangesloten_op=_g(p, "tap_aangesloten_op", default="") or "",
        type_opwekker=_g(p, "tap_type_opwekker", default="") or "",
        type_toestel=_g(p, "tap_type_toestel", default="") or "",
        gaskeur=_g(p, "tap_gaskeur", default="") or "",
        cw_klasse=_g(p, "tap_cw_klasse", default="") or "",
        dwtw_aanwezig=_g(p, "tap_dwtw", bool),
        lengte_keuken=_g(p, "tap_lengte_keuken", default="") or "",
        lengte_badkamer=_g(p, "tap_lengte_badkamer", default="") or "",
        circulatieleiding=_g(p, "tap_circulatieleiding", bool))
    inst.koeling = Koeling(
        aanwezig=_g(p, "koeling_aanwezig", bool, False),
        type_opwekker=_g(p, "koeling_type_opwekker", default="") or "",
        splitsysteem=_g(p, "koeling_splitsysteem", default="") or "",
        afgifte=_g(p, "koeling_afgifte", default="") or "",
        aantal_toestellen=_g(p, "koeling_aantal_toestellen", int))
    if _g(p, "zon_systeem"):
        inst.zonne_energie.append(ZonneEnergieSysteem(
            systeem=_g(p, "zon_systeem", default="") or "",
            aantal=_g(p, "zon_aantal", int),
            oppervlak_per_paneel_m2=_g(p, "zon_oppervlak", float),
            orientatie=_g(p, "zon_orientatie", default="") or "",
            hellingshoek=_g(p, "zon_hellingshoek", float),
            pv_type=_g(p, "zon_pv_type", default="") or "",
            belemmering=_g(p, "zon_belemmering", bool)))
    dos.installaties = inst


def _map_fotos(plan, dos):
    for ph in (_first(plan, EXPECTED_CONTAINERS["photos"]) or []):
        if isinstance(ph, dict):
            dos.fotos.append(Foto(bestand=ph.get("file") or ph.get("url") or "",
                                  bouwdeel=ph.get("bouwdeel", "-"), type=ph.get("tag", "overzicht")))


def main():
    here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-id", help="MagicPlan project id (live ophalen)")
    ap.add_argument("--plan-json", help="lokaal opgeslagen plan-JSON (offline mappen)")
    ap.add_argument("--test", action="store_true", help="auth-check via /workspace")
    ap.add_argument("--probe", action="store_true", help="endpoints aftasten naar form-antwoorden")
    ap.add_argument("--needle", default="9503HN", help="een ingevuld form-antwoord om op te herkennen")
    ap.add_argument("--env", default=os.path.join(root, ".env"))
    ap.add_argument("--out", default=os.path.join(root, "out", "dossier_from_magicplan.json"))
    a = ap.parse_args()
    if a.test:
        env = load_env(a.env)
        try:
            ws = MagicPlanClient(env).get_workspace()
            print("AUTH OK - workspace:", json.dumps(ws)[:200])
        except Exception as e:
            print("AUTH-FOUT:", e); sys.exit(1)
        return
    if a.probe:
        env = load_env(a.env); c = MagicPlanClient(env); pid = a.project_id
        outdir = os.path.join(root, "out"); os.makedirs(outdir, exist_ok=True)
        plan_id, form_ids = None, []
        try:
            plan_id = (c._get("/projects/%s" % pid).get("data") or {}).get("plan_id")
        except Exception as e:
            print("plan_id ophalen mislukt:", e)
        try:
            for fm in (c._get("/forms?project_id=%s" % pid).get("data") or []):
                form_ids.append(fm.get("id"))
        except Exception as e:
            print("form-ids ophalen mislukt:", e)
        print("plan_id=%s | %d forms" % (plan_id, len(form_ids)))
        cands = []
        if plan_id:
            cands += ["/plans/%s/forms" % plan_id, "/plans/%s/form-values" % plan_id]
            for fid in form_ids:
                cands += ["/plans/%s/forms/%s" % (plan_id, fid),
                          "/plans/%s/forms/%s/values" % (plan_id, fid),
                          "/forms/%s?plan_id=%s" % (fid, plan_id),
                          "/forms/%s/values?plan_id=%s" % (fid, plan_id)]
        for fid in form_ids:
            cands += ["/forms/%s" % fid, "/forms/%s/values" % fid, "/forms/%s/responses" % fid]
        print("Probe v2 (needle=%s):" % a.needle)
        for path in cands:
            try:
                req = urllib.request.Request(c.base + path)
                req.add_header("key", c.key); req.add_header("customer", c.customer)
                req.add_header("Accept", "application/json")
                with urllib.request.urlopen(req, timeout=30) as r:
                    body = r.read().decode("utf-8", "replace")
                fn = os.path.join(outdir, "probe2_%s.json" % path.strip("/").replace("/", "_").replace("?", "_").replace("=", "_"))
                open(fn, "w", encoding="utf-8").write(body)
                hit = "  <<< FORM-ANTWOORDEN!" if a.needle in body else ""
                print("  200  %8d  %s%s" % (len(body), path, hit))
            except urllib.error.HTTPError as e:
                print("  %-4s           %s" % (e.code, path))
            except Exception as e:
                print("  ERR            %s  (%s)" % (path, str(e)[:30]))
        return
    if a.plan_json:
        plan = json.load(open(a.plan_json, encoding="utf-8"))
    elif a.project_id:
        env = load_env(a.env)
        if not env.get("MAGICPLAN_API_KEY"):
            print("FOUT: MAGICPLAN_API_KEY ontbreekt in .env"); sys.exit(1)
        plan = MagicPlanClient(env).get_project_plan(a.project_id)
        os.makedirs(os.path.join(root, "out"), exist_ok=True)
        json.dump(plan, open(os.path.join(root, "out", "plan_raw.json"), "w"), indent=2)
        print("  ruwe plan-JSON -> out/plan_raw.json (verifieer de container-sleutels!)")
    else:
        print("Geef --project-id (live) of --plan-json (offline) op."); sys.exit(1)
    dos = map_plan_to_dossier(plan)
    os.makedirs(os.path.dirname(a.out), exist_ok=True); save_json(dos, a.out)
    print("OK: %s" % a.out)
    print("  %s %s | %d schildelen | %d ruimtes | verwarming: %s %s" % (
        dos.identificatie.postcode, dos.identificatie.huisnummer, len(dos.schil),
        len(dos.geometrie.ruimtes), dos.installaties.verwarming.type_opwekker,
        dos.installaties.verwarming.subtype))


if __name__ == "__main__":
    main()
