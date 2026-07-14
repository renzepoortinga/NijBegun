"""
Nij Begun isolatieplan-webapp (lokaal, single-user) — Apple-HIG begeleide stappen-flow.

De export-kant van de tool: laad een (kloppende) VABI-export of dossier in, vink de maatregelen aan
(Nij Begun-catalogus), genereer de VABI-import mét maatregelen, toets de Standaard, en rond af volgens de
Nij Begun-eisen (isolatieplan-Word + visueel ventilatieplan + Beoordelingsformulier-check + fotoblad), dan
exporteer de bundel. Een ingebouwde GUIDE legt per stap uit hoe en wat (kennisbank-eisen).

Draaien:
    pip install -r requirements.txt
    python dashboard/app.py            # -> http://127.0.0.1:5000

Gouden regel: de tool rekent NTA 8800 nooit zelf — Vabi EPA-W bevestigt de Standaard. De webapp blijft
lokaal (AVG) en is de handmatige adviseur-route.
"""
import os, sys, json, glob, io, zipfile, datetime, functools, secrets, copy, re
TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL_DIR)
from flask import (Flask, request, session, redirect, url_for, send_from_directory,  # noqa: E402
                   render_template_string, abort, flash, Response)
from core.dossier import load_json, save_json                                         # noqa: E402
from vabi.monitor_xml import parse as parse_monitor                                   # noqa: E402
from vabi.result_reader import read_results                                           # noqa: E402
from vabi.sanity import check as sanity_check                                         # noqa: E402
from vabi import generate_all                                                         # noqa: E402
from dashboard.measures import (laad_catalog, suggesties, bouw_maatregelen,           # noqa: E402
                                catalogus_boom, zoek_maatregel)
from dashboard import leads as leads_mod                                              # noqa: E402
from dashboard import bag as bag_mod                                                  # noqa: E402
from dashboard import security as sec                                                 # noqa: E402
from dashboard import ai as ai_mod                                                    # noqa: E402
from dashboard import bouwjaar as bouwjaar_mod                                        # noqa: E402
from engine.advies_text import genereer_advies                                        # noqa: E402
from ventilatie.ventilatie import bereken as vent_bereken, rapport as vent_rapport    # noqa: E402
from ventilatie.ventilatieplan_svg import ventilatieplan_svg                          # noqa: E402
from isolatieplan import fill_template                                                # noqa: E402
from foto import checklist as foto_checklist                                          # noqa: E402
from validator import validate as validator_mod                                       # noqa: E402

PROJECTS_DIR = os.path.join(TOOL_DIR, "out", "projects")
UPLOAD_DIR = os.path.join(TOOL_DIR, "out", "_uploads")
CONFIG = os.path.join(TOOL_DIR, "config.json")
TEMPLATE_DOCX = os.path.join(TOOL_DIR, "templates", "isolatieplan_template.docx")
DEFAULT_PW = "nijbegun"
# Flow (SOBOLT-achtig): leeg project -> Opname (MagicPlan-import + bewerken + VABI-import downloaden) ->
# Huidige staat (VABI-export terug -> Standaard-nulmeting) -> Maatregelen -> VABI-toets (import mét
# maatregelen -> Standaard gehaald?) -> Afronden (ventilatieplan + foto's) -> Opleveren (PDF+JSON+zip).
STAPPEN = [("opname", "Opname"), ("huidig", "Huidige staat"), ("maatregelen", "Maatregelen"),
           ("vabi", "VABI-toets"), ("afronden", "Afronden"), ("klaar", "Opleveren")]
# Woningtype-keuzes (NTA 8800 / ISSO 82.1-conventie) — dropdown i.p.v. vrije tekst.
WONINGTYPE_OPTS = ["Vrijstaand", "Twee-onder-een-kap", "Hoekwoning", "Tussenwoning",
                   "Galerijwoning", "Portiekwoning", "Maisonnette (bovenwoning)",
                   "Appartement (tussen)", "Appartement (hoek)", "Woning boven bedrijfsruimte"]

app = Flask(__name__)


def _cfg():
    try:
        with open(CONFIG, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _password():
    return (os.environ.get("NIJBEGUN_DASHBOARD_PW")
            or _cfg().get("dashboard", {}).get("wachtwoord") or DEFAULT_PW)


def _dash_cfg():
    """Dashboard-beveiligingsconfig: env-vars (PaaS zoals Render/Railway) > config.json (eigen server/lokaal)."""
    d = dict(_cfg().get("dashboard", {}))
    for env, key in (("NIJBEGUN_PW_HASH", "pw_hash"), ("NIJBEGUN_TOTP_SECRET", "totp_secret"),
                     ("NIJBEGUN_SECRET", "secret")):
        if os.environ.get(env):
            d[key] = os.environ[env]
    return d


def _secret_key():
    """Vaste secret key (sessies overleven een herstart): env/config > persistent bestand > nieuw."""
    s = _dash_cfg().get("secret")
    if s:
        return s
    pad = os.path.join(TOOL_DIR, "out", ".secret_key")
    try:
        if os.path.isfile(pad):
            return open(pad, encoding="ascii").read().strip()
        os.makedirs(os.path.dirname(pad), exist_ok=True)
        s = secrets.token_hex(32)
        with open(pad, "w", encoding="ascii") as fh:
            fh.write(s)
        return s
    except OSError:
        return secrets.token_hex(32)


app.secret_key = _secret_key()
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  SESSION_COOKIE_SECURE=bool(os.environ.get("NIJBEGUN_HTTPS")),
                  MAX_CONTENT_LENGTH=50 * 1024 * 1024)


@app.after_request
def _security_headers(resp):
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
    return resp


if os.environ.get("NIJBEGUN_HTTPS"):
    # achter Caddy (reverse proxy): X-Forwarded-Proto/Host respecteren zodat Flask weet dat het https is
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)


@app.before_request
def _origin_check():
    """CSRF-bescherming: POST's moeten van onze eigen HOST komen (scheme-onafhankelijk — achter een
    reverse proxy ziet Flask http terwijl de browser https meldt; vergelijk daarom alleen de host)."""
    if request.method == "POST":
        from urllib.parse import urlsplit
        bron = request.headers.get("Origin") or request.headers.get("Referer") or ""
        if bron and urlsplit(bron).netloc and urlsplit(bron).netloc != request.host:
            abort(403)


def login_required(fn):
    @functools.wraps(fn)
    def wrap(*a, **kw):
        if not session.get("ingelogd"):
            return redirect(url_for("login"))
        return fn(*a, **kw)
    return wrap


# ---------------- project-state ----------------
def _pdir(tag):
    return os.path.join(PROJECTS_DIR, tag)


def _tag(dos):
    return ("%s_%s" % (dos.identificatie.postcode or "woning",
                       dos.identificatie.huisnummer or "")).strip("_").replace(" ", "") or "woning"


def _load_state(tag):
    p = os.path.join(_pdir(tag), "project.json")
    if os.path.isfile(p):
        with open(p, encoding="utf-8") as fh:
            st = json.load(fh)
        st["tag"] = tag                 # borg de tag (klikbare stepper werkt ook bij oude projecten)
        return st
    return None


def _save_state(tag, st):
    os.makedirs(_pdir(tag), exist_ok=True)
    with open(os.path.join(_pdir(tag), "project.json"), "w", encoding="utf-8") as fh:
        json.dump(st, fh, ensure_ascii=False, indent=2)


def _dossier(tag):
    st = _load_state(tag)
    dj = os.path.join(_pdir(tag), st["dossier_file"]) if st else None
    if dj and os.path.isfile(dj):
        return load_json(dj)
    g = glob.glob(os.path.join(_pdir(tag), "dossier_*.json"))
    return load_json(g[0]) if g else None


def _verdict(res_or_dos, is_dossier=False):
    """Maak een huidig/na-toets-dict uit een result_reader-dict of dossier.berekening."""
    if is_dossier:
        b = res_or_dos.berekening
        eb, std = b.kwh_m2_huidig, b.standaard_eis_kwh_m2
        v = (eb is not None and std and eb <= std)
        return {"label": b.label_huidig or "—", "behoefte": eb, "standaard": std,
                "voldoet": bool(v), "marge": (round(std - eb, 1) if (eb is not None and std) else None)}
    r = res_or_dos
    eb = float(r["IndicatorEnergiebehoefte"]) if r.get("IndicatorEnergiebehoefte") else None
    std = float(r["Standaard"]) if r.get("Standaard") else None
    return {"label": r.get("Labelklasse", "—"), "behoefte": eb, "standaard": std,
            "voldoet": bool(r.get("_voldoet_aan_standaard")), "marge": r.get("_marge_kwh_m2")}


# ---------------- toekomstige staat (maatregelen toepassen op de schil) ----------------
def _doel_waarde(rc_u_doel):
    m = re.search(r"([\d.,]+)", rc_u_doel or "")
    return float(m.group(1).replace(",", ".")) if m else None


def _toekomstige_staat(dossier, maatregelen):
    """Pas de gekozen Standaard-maatregelen toe op een KOPIE van het dossier (Rc/U + isolatie bijwerken),
    zodat de VABI-import de toekomstige staat representeert. Benadering — Vabi blijft de rekenkern."""
    dos = copy.deepcopy(dossier)
    by_onderdeel = {m.onderdeel[:1].upper(): m for m in maatregelen}
    for s in dos.schil:
        t = (s.type or "").lower()
        key = {"gevel": "A", "kozijn": "B", "vloer": "C", "dak": "D"}.get(t)
        m = by_onderdeel.get(key)
        if not m:
            continue
        doel = _doel_waarde(m.rc_u_doel)
        s.isolatie_aanwezig = "Ja"
        if t == "kozijn":
            if doel:
                s.u_huidig = doel
            s.glastype = s.glastype or "HR++"
        elif doel:
            s.rc_huidig = doel
    dos.maatregelen = maatregelen
    return dos


# ---------------- Beoordelingsformulier-check (kennisbank) ----------------
def _beoordeling(tag, st, dossier):
    """Spiegelt het Nij Begun-Beoordelingsformulier (compleetheidscriteria) -> [(ok, tekst)]."""
    pdir = _pdir(tag)
    files = set(os.path.basename(p).lower() for p in glob.glob(os.path.join(pdir, "*")))
    has = lambda pat: any(pat in f for f in files)
    na = st.get("na") or {}
    out = [
        (bool(st.get("foto_voorkant")) and bool(st.get("foto_huisnummer")),
         "Foto voorkant + huisnummer aanwezig (komen overeen met het adres)"),
        (bool(dossier and dossier.maatregelen), "Maatregelcodes (catalogus) ingevuld"),
        (bool(na.get("voldoet")), "Doeltreffend: de maatregelenset haalt de Standaard (VABI-toets)"),
        (has("isolatieplan") and has(".docx"), "Isolatieplan (Word) gegenereerd — lay-out M29 bewaard"),
        (has("ventilatieplan"), "Ventilatieberekening + visueel ventilatieplan toegevoegd"),
        (has("fotochecklist") or has("foto"), "Fotoblad / foto-checklist toegevoegd"),
        (bool(dossier and dossier.berekening.kwh_m2_huidig is not None),
         "Huidige woningstaat (V1–V6 + warmteverlies) ingevuld"),
        (has("ventilatieberekening"), "Ventilatieberekening (tabel) toegevoegd"),
        (any(f.startswith("isolatieplan") and f.endswith(".pdf") for f in files)
         and any(f.startswith("isolatieplan") and f.endswith(".json") for f in files),
         "Leverformaat PDF + JSON gegenereerd (M29-tooleis punt 10a)"),
        (not st.get("kwaco"), "KWACO-validatie zonder bevindingen"
         + ((" — " + " · ".join(st["kwaco"][:3])) if st.get("kwaco") else "")),
    ]
    return out


# ---------------- HTML ----------------
BASE = """<!doctype html><html lang=nl><head><meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Nij Begun · isolatieplan</title>
<link rel="stylesheet" href="{{url_for('static', filename='app.css')}}"></head><body>
<div class=topbar><span class=brand>🏠 Nij Begun · isolatieplan</span>
<nav>{% if session.ingelogd %}<a href="{{url_for('leads_pagina')}}">Leads</a><a href="{{url_for('home')}}">Projecten</a><a href="{{url_for('guide')}}">Guide</a>
<a href="{{url_for('logout')}}">Uitloggen</a>{% endif %}</nav></div>
<div class="wrap {{wrapclass or ''}}">
{% with msgs = get_flashed_messages() %}{% for m in msgs %}<div class=warn>{{m}}</div>{% endfor %}{% endwith %}
{{ body|safe }}</div></body></html>"""


def stepper(active, st):
    done = set()
    order = [s for s, _ in STAPPEN]
    if st:
        huidige = st.get("stap", "opname")
        if huidige not in order:            # legacy-stap (bv. oud 'inladen') -> begin
            huidige = "opname"
        idx = order.index(huidige)
        for s in order:
            if order.index(s) < idx:
                done.add(s)
    tag = st.get("tag") if st else None
    endpoint = {"klaar": "afronden"}    # 'Opleveren' heeft geen eigen route -> de Afronden-pagina
    parts = ['<div class=stepper>']
    for s, lbl in STAPPEN:
        cls = "active" if s == active else ("done" if s in done else "")
        ep = endpoint.get(s, s)
        # elke stap is klikbaar -> je kunt vrij navigeren (bv. direct naar Afronden), niet gedwongen
        # de VABI-toets-heenweg doorlopen. De opname-editor/afronden werkt met wat er is.
        href = None
        if tag and ep in app.view_functions:
            try:
                href = url_for(ep, tag=tag)
            except Exception:
                href = None
        if href:
            parts.append('<a class="step %s" href="%s"><div class=bar></div>%s</a>' % (cls, href, lbl))
        else:
            parts.append('<div class="step %s"><div class=bar></div>%s</div>' % (cls, lbl))
    parts.append('</div>')
    return "".join(parts)


def page(body_tmpl, wrapclass="", **ctx):
    body = render_template_string(body_tmpl, **ctx)
    return render_template_string(BASE, body=body, wrapclass=wrapclass)


LOGIN = """<div class=card style="max-width:400px;margin:10vh auto">
<h1>Inloggen</h1><p class=lead>Je persoonlijke isolatieplan-werkplek.</p>
<form method=post><label>Wachtwoord</label><input type=password name=wachtwoord autofocus>
{% if mfa %}<label>Code uit je authenticator-app (MFA)</label><input name=code inputmode=numeric autocomplete=one-time-code placeholder="123 456">{% endif %}
<div class=btn-row><button class="btn lg">Inloggen</button></div></form></div>"""

HOME = """<h1>Projecten</h1><p class=lead>Van kloppende VABI-export naar een ingediend Nij Begun-isolatieplan — stap voor stap.</p>
<div class=card><h2>Nieuw project</h2>
<p class=muted>Vul het adres in en start — de <b>MagicPlan-opname laad je in de volgende stap in</b>. Je hoeft hier nog geen bestand te kiezen.</p>
<form method=post action="{{url_for('nieuw')}}">
<div class=grid2>
<div><label>Straat + huisnummer</label><input name=straat placeholder="bv. Oosterkade 23" autofocus></div>
<div><label>Postcode</label><input name=postcode placeholder="bv. 9711RS"></div>
<div><label>Plaats</label><input name=plaats></div>
<div><label>Woningtype</label><select name=woningtype>{% for w in woningtypes %}<option {{'selected' if w=='Tussenwoning'}}>{{w}}</option>{% endfor %}</select></div></div>
<div class=btn-row><button class="btn lg">Project starten →</button>
<a class="btn ghost" href="{{url_for('guide')}}">Eerst de guide lezen</a></div></form></div>
{% if projects %}<div class=card><h2>Lopende projecten</h2><div class="table-wrap"><table>
<tr><th>Adres</th><th>Stap</th><th>Standaard</th><th>Maatregelen</th><th></th></tr>
{% for p in projects %}<tr><td>{{p.adres}}</td>
<td><span class="pill gray">{{p.stap}}</span></td>
<td>{% if p.voldoet is none %}<span class=muted>—</span>{% elif p.voldoet %}<span class="pill green">voldoet</span>{% else %}<span class="pill amber">nog niet</span>{% endif %}</td>
<td>{{p.n}}{% if p.totaal %} · &euro;{{'%.0f'|format(p.totaal)}}{% endif %}</td>
<td><a class="btn sec" href="{{url_for('project', tag=p.tag)}}">openen →</a></td></tr>{% endfor %}</table></div></div>
{% endif %}"""

HUIDIG = """{{stepper|safe}}<h1>Huidige staat — nulmeting</h1>
<p class=lead>Je hebt de opname in Vabi ingelezen en doorgerekend. <b>Exporteer de woning uit Vabi</b> en laad die
hier terug — de webapp leest het huidige energielabel en of de woning de Standaard al haalt.</p>
{% if h and h.behoefte is not none %}
<div class="verdict {{ 'ok' if h.voldoet else 'no' }}"><span class=ico>{{ '✅' if h.voldoet else '🎯' }}</span>
<div><b>Huidige staat — label {{h.label}}</b><br>
<span class=muted>energiebehoefte {{h.behoefte}} vs Standaard {{h.standaard if h.standaard is not none else '—'}} kWh/m²·jr
{% if h.voldoet %}→ voldoet al{% elif h.marge is not none %}→ {{h.marge}} kWh/m²·jr te overbruggen met maatregelen{% endif %}</span></div></div>
{% else %}
<div class=hint>Nog geen VABI-export ingeladen. Upload hieronder de export van de <b>huidige</b> woning uit Vabi (het monitoring-/resultatenbestand). <b>Vabi blijft de rekenkern.</b></div>
{% endif %}
<form method=post enctype=multipart/form-data><div class=card><h2>VABI-export inladen (huidige woning)</h2>
<div class=file-drop>Sleep hier de VABI-export (.xml) of kies 'm<br><input type=file name=export accept=".xml"></div>
<p class="muted small">Dit is de <b>0-meting</b>: het label en de Standaard-afstand vóór maatregelen. Klopt er iets niet? Pas het in Vabi aan en upload opnieuw.</p>
<div class=btn-row><button class=btn>Inladen &amp; toetsen</button>
<span class=spacer></span>
<a class="btn lg {{ '' if h and h.behoefte is not none else 'ghost' }}" href="{{url_for('naar_maatregelen', tag=tag)}}">Door naar maatregelen →</a></div></div></form>"""

# --------- opname-editor (SOBOLT-achtig: alle gegevens zichtbaar + bewerkbaar) ---------
BEGR_OPTS = ["Buitenlucht", "Grond", "Kruipruimte", "AOR", "AOS", "AVR", "Sterk geventileerd", "Water"]
ORI_OPTS = ["", "N", "NO", "O", "ZO", "Z", "ZW", "W", "NW"]
GLAS_OPTS = ["", "Enkel", "Voorzetglas", "Dubbel", "HR (dubbel glas met coating)", "HR+", "HR++",
             "TripleHR", "Vacuümglas", "Onbekend"]
KOZ_OPTS = ["", "Hout of kunststof", "Metaal (thermisch onderbroken)", "Metaal (niet thermisch onderbroken)"]
TYPE_ICO = {"dak": "⛰", "gevel": "🧱", "vloer": "▬", "kozijn": "🪟", "paneel": "⬜"}

OPNAME_TMPL = """{{stepper|safe}}<h1>Opname — {{st.adres}}</h1>
<p class=lead>Alle opnamegegevens, bewerkbaar. Laad je MagicPlan-opname in of vul handmatig aan — <b>Vabi blijft de rekenkern</b>.</p>
<div class=card><h2>① MagicPlan-opname inladen</h2>
<p class=muted>Upload de MagicPlan <b>Statistics-CSV</b> (of een eerder dossier .json). De gebouwboom, installaties en gegevens hieronder worden gevuld; je kunt daarna alles nalopen.</p>
<form method=post action="{{url_for('opname_magicplan', tag=tag)}}" enctype=multipart/form-data>
<div class=file-drop>Sleep hier de MagicPlan-CSV of dossier (.csv / .json)<br><input type=file name=bestand accept=".csv,.json"></div>
<div class=btn-row><button class=btn>Inladen in de opname</button>
<span class="muted small">Al ingeladen? Loop de gegevens hieronder na en pas aan waar nodig.</span></div></form></div>
{% if st.vabi_acties %}<div class=card style="border:2px solid var(--warn-line);background:var(--warn-bg)">
<h2>📋 Zelf doen in Vabi — {{st.vabi_acties|length}} actiepunt(en)</h2>
<ul class=check>{% for a in st.vabi_acties %}<li><span class="mk no2">→</span>{{a}}</li>{% endfor %}</ul>
<p class="muted small">Automatisch verzameld bij je MagicPlan-upload: narekenen-wanden, kwaliteitsverklaringen
(zet in Vabi Invoer=Kwaliteitsverklaring + vul zelf de BCRG-code), multi-zone en ontbrekende gegevens.
Deze lijst blijft staan tot de volgende upload en gaat mee in IMPORTEREN.txt bij de VABI-export.</p></div>{% endif %}
<div class=card><h2>② Algemeen</h2><form method=post action="{{url_for('opname_algemeen', tag=tag)}}"><div class=grid2>
<div><label>BAG nummeraanduiding-ID</label><input name=bag_vboid value="{{d.identificatie.bag_vboid}}"></div>
<div><label>Woningtype</label><select name=woningtype>{% for w in woningtypes %}<option {{'selected' if w==d.identificatie.woningtype}}>{{w}}</option>{% endfor %}{% if d.identificatie.woningtype and d.identificatie.woningtype not in woningtypes %}<option selected>{{d.identificatie.woningtype}}</option>{% endif %}</select></div>
<div><label>Bouwjaar</label><input name=bouwjaar value="{{d.identificatie.bouwjaar or ''}}"></div>
<div><label>Renovatiejaar (huidig)</label><input name=renovatiejaar value="{{d.identificatie.renovatiejaar or ''}}"></div>
<div><label>Gevelhoogte (m)</label><input name=gevelhoogte value="{{d.opname.gevelhoogte_m or ''}}"></div>
<div><label>Gebruiksoppervlakte Ag (m²)</label><input name=ag value="{{d.geometrie.gebruiksoppervlakte_ag_m2 or ''}}"></div>
<div><label>Qv10 (dm³/s·m²) — alleen indien gemeten</label><input name=qv10 value="{{d.opname.qv10_waarde or ''}}"></div>
<div><label>Oriëntatie voorgevel</label><select name=ori_voor>{% for o in ori_opts %}<option {{'selected' if o==d.identificatie.orientatie_voorgevel}}>{{o}}</option>{% endfor %}</select></div>
</div><div class=btn-row><button class=btn>Algemeen opslaan</button></div></form></div>

{% if bj_titel %}<details class=acc><summary>💡 Wat je waarschijnlijk aantreft — {{bj_titel}} (o.b.v. bouwjaar {{d.identificatie.bouwjaar}})</summary>
<div class=acc-body>{{bj_html|safe}}<p class="muted small">Bron: bouwjaarklasse-opnamegids (algemene NL-bouwpraktijk) — de opname blijft leidend.</p></div></details>{% endif %}

<div class=card><h2>Gebouw <span class="pill gray">{{elementen|length}} vlakken</span></h2>
{% for rz, els in zones %}<h3 style="margin-top:14px">Rekenzone {{rz}}</h3>
{% for i, s in els %}<details class=acc><summary>{{ico.get(s.type,'▫')}} <b>{{s.id}}</b>
<span class="pill gray">{{s.type}}{{' · '+s.subtype if s.subtype}}</span>
{% if s.orientatie %}<span class="pill blue">{{s.orientatie}}</span>{% endif %}
<span class="pill gray">{{'%.2f'|format(s.oppervlakte_m2 or 0)}} m²</span>
{% if s.rc_huidig %}<span class="pill green">Rc={{s.rc_huidig}}</span>{% elif s.u_huidig %}<span class="pill green">U={{s.u_huidig}}</span>{% endif %}
{% if s.begrenzing and s.begrenzing != 'Buitenlucht' %}<span class="pill amber">{{s.begrenzing}}</span>{% endif %}</summary>
<div class=acc-body><form method=post action="{{url_for('opname_el', tag=tag, i=i)}}"><div class=grid2>
<div><label>Naam</label><input name=id value="{{s.id}}"></div>
<div><label>Subtype</label><input name=subtype value="{{s.subtype}}"></div>
<div><label>Oppervlakte (m²)</label><input name=m2 value="{{s.oppervlakte_m2 or ''}}"></div>
<div><label>Oriëntatie</label><select name=orientatie>{% for o in ori_opts %}<option {{'selected' if o==s.orientatie}}>{{o}}</option>{% endfor %}</select></div>
<div><label>Begrenzing</label><select name=begrenzing>{% for b in begr_opts %}<option {{'selected' if b==s.begrenzing}}>{{b}}</option>{% endfor %}</select></div>
<div><label>Rekenzone</label><select name=rekenzone>{% for z in (1,2,3) %}<option {{'selected' if z==s.rekenzone}}>{{z}}</option>{% endfor %}</select></div>
{% if s.type == 'kozijn' %}
<div><label>Type glas</label><select name=glastype>{% for g in glas_opts %}<option {{'selected' if g==s.glastype}}>{{g}}</option>{% endfor %}</select></div>
<div><label>Kozijnmateriaal</label><select name=kozijnmateriaal>{% for k in koz_opts %}<option {{'selected' if k==s.kozijnmateriaal}}>{{k}}</option>{% endfor %}</select></div>
<div><label>U-waarde (huidig)</label><input name=u value="{{s.u_huidig or ''}}"></div>
{% else %}
<div><label>Rc-waarde (huidig, m²K/W)</label><input name=rc value="{{s.rc_huidig or ''}}"></div>
<div><label>Isolatie aanwezig</label><select name=isolatie>{% for x in ('Ja','Nee','Onbekend') %}<option {{'selected' if x==s.isolatie_aanwezig}}>{{x}}</option>{% endfor %}</select></div>
<div><label>Isolatiedikte (mm)</label><input name=dikte value="{{s.isolatiedikte_mm or ''}}"></div>
{% endif %}
{% if s.type == 'dak' %}<div><label>Hellingshoek (°)</label><input name=helling value="{{s.hellingshoek or ''}}"></div>{% endif %}
<div><label>Opmerkingen</label><input name=opmerkingen value="{{s.opmerkingen}}"></div>
</div><div class=btn-row><button class=btn>Opslaan</button>
<button class="btn sec" formaction="{{url_for('opname_el_kopie', tag=tag, i=i)}}">⧉ Dupliceer</button>
<button class="btn sec" formaction="{{url_for('opname_el_weg', tag=tag, i=i)}}" onclick="return confirm('{{s.id}} verwijderen?')">🗑 Verwijder</button>
</div></form></div></details>{% endfor %}{% endfor %}
<form method=post action="{{url_for('opname_el_nieuw', tag=tag)}}" class=btn-row style="margin-top:14px">
<select name=type style="max-width:180px"><option value=gevel>Gevel</option><option value=dak>Dak</option>
<option value=vloer>Vloer</option><option value=kozijn>Raam/deur</option><option value=paneel>Paneel (dicht)</option></select>
<button class="btn sec">+ Vlak toevoegen</button></form></div>

<div class=card><h2>Ventilatie</h2>
<p class=muted>Nij Begun rekent met vuistregels: toevoer 0,7 dm³/s·m² per verblijfsgebied (min 7 l/s), afvoer keuken 21 / bad 14 / toilet 7, in balans. Ventilatie is een <b>verplicht</b> onderdeel van het isolatieplan.</p>
<form method=post action="{{url_for('opname_installaties', tag=tag)}}"><div class=grid2>
<div><label>Ventilatie (A-E)</label><input name=vent_systeem value="{{d.ventilatie.systeem}}" placeholder="A/B/C/D/E"></div>
<div><label>Ventilatie subsysteem</label><input name=vent_sub value="{{d.ventilatie.subsysteem_code}}" placeholder="bv. C1"></div>
</div>
<details class=acc style="margin-top:14px"><summary>Verwarming &amp; tapwater — <span class=muted>alleen voor het energielabel (optioneel)</span></summary>
<div class=acc-body><p class="muted small">Deze installaties bepalen het <b>energielabel</b>, niet de Nij Begun-Standaard (netto warmtebehoefte).
Je vult ze in Vabi in; hier invullen is optioneel en wordt alleen als sjabloon-hint meegegeven aan de VABI-import.</p>
<div class=grid2>
<div><label>Verwarming — type opwekker</label><input name=vw_opwekker value="{{d.installaties.verwarming.type_opwekker}}"></div>
<div><label>Verwarming — subtype (HR-klasse/WP)</label><input name=vw_subtype value="{{d.installaties.verwarming.subtype}}"></div>
<div><label>Verwarming — afgifte</label><input name=vw_afgifte value="{{d.installaties.verwarming.afgifte}}"></div>
<div><label>Verwarming — aanvoertemperatuur</label><input name=vw_temp value="{{d.installaties.verwarming.aanvoertemperatuur}}"></div>
<div><label>Tapwater — toestel</label><input name=tw_toestel value="{{d.installaties.tapwater.type_toestel}}"></div>
<div><label>Tapwater — installatiejaar</label><input name=tw_jaar value="{{d.installaties.tapwater.installatiejaar or ''}}"></div>
</div></div></details>
<div class=btn-row><button class=btn>Ventilatie opslaan</button></div></form></div>

<div class=card><div class=kv>
<dt>Totaal verliesoppervlak</dt><dd>{{'%.2f'|format(verlies)}} m²</dd>
<dt>Gebruiksoppervlak (Ag)</dt><dd>{{'%.2f'|format(ag) if ag else '—'}} m²</dd>
<dt>Compactheid (verlies/Ag)</dt><dd>{{'%.2f'|format(verlies/ag) if ag else '—'}}</dd></div>
<p class="muted small">AVR-vlakken tellen niet mee in het verliesoppervlak (adiabatisch).</p></div>

<div class=card><h2>③ Exporteer naar Vabi</h2>
<p class=muted>Genereer de VABI-import (3 bibliotheken) van de <b>huidige</b> woning, importeer die in EPA-W en reken door.
Exporteer de woning daarna uit Vabi — die laad je in de volgende stap terug als nulmeting.</p>
<div class=btn-row><a class="btn sec" href="{{url_for('opname_vabi_huidig', tag=tag)}}">⬇ VABI-import (huidige staat)</a>
<div class=spacer></div><a class="btn lg" href="{{url_for('huidig', tag=tag)}}">Door naar huidige staat →</a></div></div>"""

MAATREGELEN = """{{stepper|safe}}<h1>Maatregelen kiezen</h1>
<p class=lead>Vink aan wat je toepast. De goedkoopste passende maatregel is voorgeselecteerd; je kunt per bouwdeel wisselen.</p>
<div class=hint><b>Nij Begun-regel:</b> maatregelen die nódig zijn voor de <b>Standaard</b> staan in de <b>subsidietabel</b> (50/100%).
Bouwfysisch wenselijke extra's (bv. dakkapel-wangen, deur) adviseer je wél, maar die vallen onder <b>30% ISDE</b> — zet die op “advies”.</div>
<form method=post id=mf>
{% for g in groepen %}
<div class="card meas-group" data-m2="{{g.m2}}">
<div style="display:flex;justify-content:space-between;align-items:center">
<h2 style="margin:0">{{g.onderdeel}} <span class="pill blue">{{'%.1f'|format(g.m2)}} m²</span></h2>
<select name="bucket_{{loop.index0}}" class=bk style="max-width:230px">
<option value=standaard>In subsidietabel (Standaard)</option>
<option value=isde>Advies (30% ISDE) — buiten tabel</option>
<option value=geen>Niet opnemen</option></select></div>
{% if g.note %}<p class="muted small">{{g.note}}</p>{% endif %}
<input type=hidden name="onderdeel_{{loop.index0}}" value="{{g.onderdeel}}">
<input type=hidden name="m2_{{loop.index0}}" value="{{g.m2}}">
<input type=hidden name="doel_{{loop.index0}}" value="{{g.rc_u_doel}}">
<label>Maatregel (catalogus)</label>
<select name="code_{{loop.index0}}" class=cm data-grp="{{loop.index0}}">
{% for k in g.kandidaten %}<option value="{{k.code}}" data-prijs="{{k.prijs}}" {{'selected' if k.code==g.default_code else ''}}>{{k.code}} · {{k.omschrijving[:70]}} — €{{'%.2f'|format(k.prijs)}}/{{k.eenheid}}</option>{% endfor %}</select>
<p class="muted small">doelwaarde {{g.rc_u_doel}} · regel-subtotaal <b class=sub data-grp="{{loop.index0}}">€{{'%.0f'|format(g.kandidaten[0].kosten)}}</b></p>
<label>Technische haalbaarheid (per maatregel — komt in de losse bijlage)</label>
<input name="haal_{{loop.index0}}" placeholder="bv. kruipruimte 60 cm en droog · bereikbaar via luik hal · geen asbest gezien" value="{{(st.haal or {}).get(loop.index0|string, '')}}">
</div>{% endfor %}</form>

<div class=card><h2>Zelf kiezen uit de catalogus</h2>
<p class=muted>De volledige Nij Begun-catalogus (zoals het portal): categorie → subcategorie → maatregel of bijkomende kosten. Voeg toe met eigen hoeveelheid.</p>
{% if vrij %}<div class="table-wrap"><table><tr><th>Code</th><th>Omschrijving</th><th>Hoeveelheid</th><th>Kosten</th><th>Bucket</th><th></th></tr>
{% for v in vrij %}<tr><td class=small>{{v.code}}</td><td>{{v.omschrijving[:58]}}</td>
<td>{{v.hoeveelheid}} {{v.eenheid}}</td><td>€{{'%.0f'|format(v.kosten)}}</td>
<td><span class="pill {{'green' if v.bucket=='standaard' else 'amber'}}">{{'Standaard' if v.bucket=='standaard' else '30% ISDE'}}</span></td>
<td><form method=post action="{{url_for('maatregel_del', tag=tag, idx=loop.index0)}}"><button class="btn sec">✕</button></form></td></tr>{% endfor %}</table></div>
<p class="muted small">Subtotaal catalogus-keuze (Standaard-bucket): <b>€{{'%.0f'|format(vrij_tot)}}</b></p>{% endif %}
{% for c in boom %}<details class=acc><summary><b>{{c.naam}}</b> <span class="pill gray">{{c.code}}</span></summary><div class=acc-body>
{% for s in c.subs %}<details class=acc><summary>{{s.naam[:60]}} <span class="pill gray">{{s.code}}</span></summary><div class=acc-body>
{% for m in s.kern %}<form method=post action="{{url_for('maatregel_add', tag=tag)}}" style="display:flex;gap:8px;align-items:center;padding:4px 0">
<input type=hidden name=code value="{{m.code}}"><span style="flex:1" class=small>{{m.code}} · {{m.omschrijving[:64]}} — €{{'%.2f'|format(m.prijs)}}/{{m.eenheid}}{% if m.biobased %} <span class="pill green">bio</span>{% endif %}</span>
<input name=hoeveelheid placeholder="{{m.eenheid}}" style="max-width:90px"><select name=bucket style="max-width:130px"><option value=standaard>Standaard</option><option value=isde>30% ISDE</option></select>
<button class="btn sec">＋</button></form>{% endfor %}
{% if s.meerwerk %}<p class="muted small" style="margin:8px 0 2px"><b>Bijkomende kosten</b></p>
{% for m in s.meerwerk %}<form method=post action="{{url_for('maatregel_add', tag=tag)}}" style="display:flex;gap:8px;align-items:center;padding:4px 0">
<input type=hidden name=code value="{{m.code}}"><span style="flex:1" class=small>{{m.code}} · {{m.omschrijving[:64]}} — €{{'%.2f'|format(m.prijs)}}/{{m.eenheid}}</span>
<input name=hoeveelheid placeholder="{{m.eenheid}}" style="max-width:90px"><select name=bucket style="max-width:130px"><option value=standaard>Standaard</option><option value=isde>30% ISDE</option></select>
<button class="btn sec">＋</button></form>{% endfor %}{% endif %}
</div></details>{% endfor %}</div></details>{% endfor %}</div>

<div class=totalbar><span class=t>Subsidietabel (Standaard)</span><span class=v id=tot>€0</span>
<div class=spacer></div><button class="btn lg" form=mf>Door naar VABI-toets →</button></div>
<script>
var VRIJ={{vrij_tot|int}};
function recalc(){var tot=VRIJ;document.querySelectorAll('.meas-group').forEach(function(g,i){
var m2=parseFloat(g.dataset.m2)||0;var sel=g.querySelector('.cm');var pr=parseFloat(sel.selectedOptions[0].dataset.prijs)||0;
var sub=Math.round(pr*m2);g.querySelector('.sub').textContent='€'+sub.toLocaleString('nl-NL');
var bk=g.querySelector('.bk').value;if(bk==='standaard')tot+=sub;});
document.getElementById('tot').textContent='€'+tot.toLocaleString('nl-NL');}
document.getElementById('mf').addEventListener('change',recalc);recalc();
</script>"""

VABI = """{{stepper|safe}}<h1>VABI-toets met maatregelen</h1>
<p class=lead>Genereer de VABI-import mét de gekozen maatregelen, reken in Vabi, en upload de nieuwe export terug.</p>
<div class=card><h2>1 · Importeer in Vabi EPA-W</h2>
<form method=get style="margin-bottom:12px"><label>Rekenwaarde Qv10 na maatregelen — renovatiejaar variant (zet de tool op de toekomstige staat; Vabi rekent de infiltratie forfaitair op dit jaar)</label>
<div class=btn-row><input name=renojaar value="{{renojaar}}" style="max-width:120px"><button class="btn sec">Opnieuw genereren met dit renovatiejaar</button></div></form>
<p class=muted>De toekomstige staat (maatregelen verwerkt) als 3 bibliotheken. Importeer in EPA-W → <b>Constructies → Objecten → Installaties</b> → Rekenen.</p>
<ul class=files>{% for f in vabi_files %}<li>{{f}} <a class="btn sec" href="{{url_for('download', tag=tag, filename='vabi_na/'+f)}}">download</a></li>{% endfor %}</ul></div>
<div class=card><h2>Berekening</h2><div class=kv>
<dt>Isolatiestandaard (eis)</dt><dd>{{h.standaard if h.standaard is not none else '—'}} kWh/m²·jr</dd>
<dt>Netto warmtebehoefte (huidig)</dt><dd>{{h.behoefte if h.behoefte is not none else '—'}} kWh/m²·jr</dd>
<dt>Netto warmtebehoefte (met maatregelen)</dt><dd>{{na.behoefte if na and na.behoefte is not none else '— (upload de export)'}} kWh/m²·jr</dd>
<dt>Totale kosten (subsidietabel)</dt><dd>€{{'%.2f'|format(st.totaal or 0)}}</dd>
<dt>Totaal verliesoppervlak</dt><dd>{{'%.2f'|format(verlies)}} m²</dd>
<dt>Totaal gebruiksoppervlak</dt><dd>{{'%.2f'|format(ag) if ag else '—'}} m²</dd>
<dt>Compactheid</dt><dd>{{'%.2f'|format(verlies/ag) if ag else '—'}}</dd></div>
<p class="muted small">Warmtebehoefte-getallen komen uit Vabi (de rekenkern) — de tool rekent ze nooit zelf.</p></div>
<div class=card><h2>2 · Upload de nieuwe VABI-export</h2>
<form method=post enctype=multipart/form-data>
<div class=file-drop>VABI-export ná maatregelen (.xml)<br><input type=file name=export accept=".xml" required></div>
<div class=btn-row><button class=btn>Standaard toetsen →</button></div></form>
{% if na %}<div class="verdict {{ 'ok' if na.voldoet else 'no' }}" style="margin-top:16px"><span class=ico>{{ '✅' if na.voldoet else '⚠️' }}</span>
<div><b>{{ 'Voldoet aan de Standaard!' if na.voldoet else 'Voldoet nog niet' }}</b><br>
<span class=muted>energiebehoefte {{na.behoefte}} vs Standaard {{na.standaard}} kWh/m²·jr{% if na.marge is not none %} · marge {{na.marge}}{% endif %}</span></div></div>
{% if na.voldoet %}<div class=btn-row><a class="btn lg green" href="{{url_for('afronden', tag=tag)}}">Afronden →</a></div>
{% else %}<div class=btn-row><a class="btn sec" href="{{url_for('maatregelen', tag=tag)}}">← pakket uitbreiden</a></div>{% endif %}{% endif %}</div>"""

AFRONDEN = """{{stepper|safe}}<h1>Afronden volgens Nij Begun</h1>
<p class=lead>Foto's, het isolatieplan, het visuele ventilatieplan en de indien-check — klaar voor oplevering.</p>
<div class=card><h2>Verplichte foto's</h2>
<p class=muted>Kwaliteitscommissie-eis: het adres én de foto van de voorkant komen overeen. ≥8 MP · max 5 MB (SNN).</p>
<form method=post action="{{url_for('fotos', tag=tag)}}" enctype=multipart/form-data><div class=grid2>
<div><label>Foto voorkant woning{% if st.foto_voorkant %} <span class="pill green">✓ toegevoegd</span>{% endif %}</label><input type=file name=foto_voorkant accept="image/*"></div>
<div><label>Foto huisnummer{% if st.foto_huisnummer %} <span class="pill green">✓ toegevoegd</span>{% endif %}</label><input type=file name=foto_huisnummer accept="image/*"></div></div>
<div class=btn-row><button class=btn>Foto's opslaan</button></div></form></div>
<div class=card><h2>Eigen ventilatieplan &amp; bijlagen uploaden</h2>
<p class=muted>Heb je een eigen ventilatieplan (op de echte MagicPlan-plattegrond) of andere bijlagen (facturen,
plattegrond, extra foto's, offertes)? Upload ze hier — ze gaan mee in de export-bundel.</p>
<form method=post action="{{url_for('bijlagen', tag=tag)}}" enctype=multipart/form-data>
<div class=grid2>
<div><label>Eigen ventilatieplan (PDF / afbeelding){% if st.ventilatieplan_eigen %} <span class="pill green">✓ {{st.ventilatieplan_eigen}}</span>{% endif %}</label>
<input type=file name=ventilatieplan_eigen accept="image/*,.pdf,.svg"></div>
<div><label>Extra bijlagen (meerdere tegelijk){% if st.bijlagen %} <span class="pill green">✓ {{st.bijlagen|length}} bestand(en)</span>{% endif %}</label>
<input type=file name=bijlagen multiple></div></div>
<div class=btn-row><button class=btn>Uploaden</button></div>
{% if st.bijlagen %}<ul class=files>{% for b in st.bijlagen %}<li>{{b}} <a class="btn sec" href="{{url_for('download', tag=tag, filename=b)}}">download</a>
<a class="btn sec" href="{{url_for('bijlage_weg', tag=tag, naam=b)}}" onclick="return confirm('Verwijderen?')">✕</a></li>{% endfor %}</ul>{% endif %}
</form></div>
<div class=card><h2>Toelichting op advies</h2>
<p class=muted>Deze persoonlijke toelichting komt in de bijlage bij het plan (met de technische haalbaarheid per maatregel).</p>
<form method=post action="{{url_for('toelichting', tag=tag)}}">
<textarea name=toelichting rows=6 placeholder="bv. bewoner wil eerst het dak; spouw is in 2005 al deels gevuld — zie foto's">{{st.toelichting or ''}}</textarea>
<div class=btn-row><button class=btn>Toelichting opslaan</button>
<button class="btn sec" formaction="{{url_for('toelichting_assist', tag=tag)}}" name=actie value=voorstel>✨ Tekstvoorstel (offline)</button>
<button class="btn sec" formaction="{{url_for('toelichting_assist', tag=tag)}}" name=actie value=verbeter>🤖 AI verbeteren</button></div>
<p class="muted small">Tekstvoorstel = uit je eigen opname/maatregelen (offline). AI verbeteren = Claude-API
(sleutel in config.json; zet geen naam/adres van de bewoner in de tekst — AVG).</p></form></div>
<div class=card><h2>Klaar voor indienen? (Beoordelingsformulier)</h2><ul class=check>
{% for ok, txt in beoord %}<li><span class="mk {{'ok2' if ok else 'no2'}}">{{ '✓' if ok else '○' }}</span>{{txt}}</li>{% endfor %}</ul>
<p class="muted small">Spiegelt de compleetheidscriteria van de Nij Begun-kwaliteitscommissie.</p></div>
<div class=card><h2>Ventilatieplan (automatisch)</h2>
{% if st.ventilatieplan_eigen %}<p class=muted>Je hebt een <b>eigen ventilatieplan</b> geüpload ({{st.ventilatieplan_eigen}}) — dat zit in de export. Dit auto-plan is de onderbouwing/berekening.</p>{% endif %}
<div class=svgbox>{{vent_svg|safe}}</div></div>
<div class=card><h2>Gegenereerde bestanden</h2><ul class=files>
{% for f in files %}<li>{{f}} <a class="btn sec" href="{{url_for('download', tag=tag, filename=f)}}">download</a></li>{% endfor %}</ul></div>
<div class=btn-row><a class="btn sec" href="{{url_for('afronden', tag=tag)}}?regen=1">Opnieuw genereren</a><div class=spacer></div>
<a class="btn lg green" href="{{url_for('export', tag=tag)}}">⬇ Exporteer de bundel (.zip)</a></div>"""

GUIDE = """<h1>Guide — zo maak je een Nij Begun-isolatieplan</h1>
<p class=lead>De volledige werkwijze, met de eisen van de Nij Begun-kennisbank erin verwerkt.</p>
<div class=card><h2>Veldgidsen (open ze op je telefoon bij de opname)</h2><ul class=files>
{% for slug, (titel, _b) in gidsen.items() %}<li>{{titel}} <a class="btn sec" href="{{url_for('gids', slug=slug)}}">openen</a></li>{% endfor %}
</ul></div>
<div class=card><h2>De flow in 6 stappen</h2>
<div class=stepper>{% for s,l in stappen %}<div class="step done"><div class=bar></div>{{l}}</div>{% endfor %}</div>
<dl class=kv><dt>1 · Opname</dt><dd>Start een <b>leeg project</b> (alleen adres) en laad in deze stap de <b>MagicPlan Statistics-CSV</b> in. Alle opnamegegevens worden <b>zichtbaar en bewerkbaar</b>: de gebouw-boom per rekenzone (dak/gevels/ramen/vloer met m², Rc/U, begrenzing), installaties en algemene gegevens. Onderaan exporteer je de woning naar <b>Vabi</b> (3 bibliotheken), reken je door in EPA-W en exporteer je 'm weer uit Vabi.</dd>
<dt>2 · Huidige staat</dt><dd>Laad de <b>VABI-export</b> van de huidige woning terug: de webapp leest het <b>label</b> en of de Standaard al gehaald wordt (de 0-meting).</dd>
<dt>3 · Maatregelen</dt><dd>Suggesties per bouwdeel (goedkoopste eerst) óf <b>zelf kiezen uit de volledige catalogus</b> incl. bijkomende kosten. Noteer per maatregel de <b>technische haalbaarheid</b>. Standaard → subsidietabel; extra's → 30% ISDE.</dd>
<dt>4 · VABI-toets</dt><dd>Genereer de toekomstige staat (met <b>renovatiejaar-variant</b> voor de Qv10), importeer in Vabi, reken, upload de export terug. <b>Voldoet de set aan de Standaard?</b> Zo niet → pakket uitbreiden.</dd>
<dt>5 · Afronden</dt><dd>Verplichte <b>foto's</b> (voorkant + huisnummer) + persoonlijke toelichting + isolatieplan (<b>PDF + JSON</b> leverformaat) + <b>visueel ventilatieplan</b> + haalbaarheids-bijlage + foto-checklist. De <b>indien-check</b> spiegelt het Beoordelingsformulier.</dd>
<dt>6 · Opleveren</dt><dd>Exporteer de bundel en dien in via leveranciers@nijbegun.nl. De eerste 4 plannen worden 100% gecontroleerd.</dd></dl></div>
<details class=acc open><summary>Ventilatie — de Nij Begun-vuistregels (bindend)</summary><div class=acc-body>
Toevoer <b>0,7 dm³/s·m² per verblijfsgebied</b> (min 7 l/s/leefruimte) via roosters/WTW. Afvoer <b>keuken 21 · bad 14 · toilet 7</b>. Aan-/afvoer in <b>balans</b>.
Regels o.a.: overstroom max 2 deuren · ≥50% van buiten · géén afvoer in slaapkamer · >15 l/s onder deur → deurrooster · C4c CO₂-sturing woonkamer+hoofdslaapkamer.
Rooster-l/s: raambreedte-afhankelijk (ISSO-kleintje). Geveldoorvoeren/deurroosters staan (nog) niet in M29.</div></details>
<details class=acc><summary>Foto's — wat is verplicht</summary><div class=acc-body>
Overzicht per bouwdeel + ≥1 detailfoto per cat-2-prijs. Geen persoonlijke spullen/bewoners in beeld. ≥8 MP, SNN-upload max 5 MB.
Per maatregel specifiek (bv. spouw: boorgat+spouw, voegwerk; kruipruimte: diepte met duimstok zichtbaar + kruipluik).</div></details>
<details class=acc><summary>Goedkeuring — het Beoordelingsformulier</summary><div class=acc-body>
Compleetheid: adviseur in open house · lay-out M29 bewaard · geen hiaten · adres+foto kloppen · plan op pagina 6 · huidige staat volledig · samenvatting voor SNN · maatregelcodes correct · bijlage “Waarom ventileren” · ventilatieberekening · fotoblad.
Inhoud: doeltreffend (haalt de Standaard) · juiste set (uit de opname) · uitvoerbaar (vocht/bereikbaarheid) · toekomstbestendig (bouwfysica).</div></details>
<p class="muted small">Bron: adviseurs-nijbegun.nl/support. Details in docs/nijbegun-kennisbank-eisen.md.</p>
<div class=btn-row><a class="btn" href="{{url_for('home')}}">← naar projecten</a></div>"""


# ---------------- routes ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    dash = _dash_cfg()
    if request.method == "POST":
        ok, fout = sec.login_check(dash, request.form.get("wachtwoord"), request.form.get("code"),
                                   request.remote_addr or "?", fallback_pw=_password())
        if ok:
            session["ingelogd"] = True
            return redirect(url_for("home"))
        flash(fout)
    return page(LOGIN, wrapclass="narrow", mfa=bool(dash.get("totp_secret")))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def home():
    rows = []
    if os.path.isdir(PROJECTS_DIR):
        for tag in sorted(os.listdir(PROJECTS_DIR)):
            st = _load_state(tag)
            if not st:
                continue
            na = st.get("na") or {}
            rows.append({"tag": tag, "adres": st.get("adres", tag), "stap": st.get("stap", "opname"),
                         "voldoet": na.get("voldoet"), "n": len(st.get("keuze", [])),
                         "totaal": st.get("totaal", 0)})
    return page(HOME, projects=rows, woningtypes=WONINGTYPE_OPTS)


# Veldgidsen — markdown uit docs/ gerenderd in de webapp (mobiel bij de opname te gebruiken)
GIDSEN = {
    "opnameformulier": ("📋 Nij Begun opnameformulier (alles per project)", "nijbegun-opnameformulier.md"),
    "inmeten": ("📐 MagicPlan-inmeetgids (controlematen geometrie)", "magicplan-inmeetgids.md"),
    "dak": ("⛰ Dak invoeren — types, geometrie & rekenmodel", "dak-rekenmodel.md"),
    "rekenwijze": ("🧮 Rekenwijze — hoe de tool alles berekent", "rekenwijze-gids.md"),
    "bouwjaar-eisen": ("📜 Eisen & herkenning per bouwjaarklasse (Rc-historie)", "bouwjaarklasse-eisen-gids.md"),
    "spouwmuur": ("🧱 Spouwmuur herkennen (visueel, met tekeningen)", "spouwmuur-herkennen-gids.md"),
    "spouwinspectie": ("🔎 Spouwinspectie / endoscopie", "spouwinspectie-gids.md"),
    "ventilatie": ("💨 Ventilatiesystemen & roosters herkennen", "ventilatie-herkennen-gids.md"),
    "bouwjaar": ("🏗 Bouwjaarklasse-opnamegids (bouwfysica per tijdvak)", "bouwjaarklasse-opnamegids.md"),
    "werkinstructie": ("✅ Opname-werkinstructie per kamer", "OPNAME-WERKINSTRUCTIE.md"),
}

GIDS_TMPL = """<p><a class="btn ghost" href="{{url_for('guide')}}">← alle gidsen</a></p>
<div class=card><h1 style="font-size:24px">{{titel}}</h1>{{inhoud|safe}}</div>
<p class="muted small">Bron: docs/{{bestand}} — ook offline in de repo beschikbaar.</p>"""


@app.route("/gids/<slug>")
@login_required
def gids(slug):
    if slug not in GIDSEN:
        abort(404)
    titel, bestand = GIDSEN[slug]
    pad = os.path.join(TOOL_DIR, "docs", bestand)
    if not os.path.isfile(pad):
        abort(404)
    md = open(pad, encoding="utf-8").read()
    return page(GIDS_TMPL, titel=titel, bestand=bestand, inhoud=bouwjaar_mod.md_naar_html(md))


@app.route("/guide")
@login_required
def guide():
    return page(GUIDE, stappen=STAPPEN, gidsen=GIDSEN)


def _split_adres(straat_veld, dos):
    """'Oosterkade 23' -> straat + huisnummer op het dossier."""
    a = (straat_veld or "").strip()
    if not a:
        return
    parts = a.rsplit(" ", 1)
    dos.identificatie.straat = parts[0]
    if len(parts) > 1:
        dos.identificatie.huisnummer = parts[1]


@app.route("/nieuw", methods=["POST"])
@login_required
def nieuw():
    """Maak een LEEG project (geen upload nodig) — de MagicPlan-opname komt in de Opname-stap.
    Blijft een geüpload bestand (dossier/VABI/CSV) accepteren als iemand dat toch meestuurt."""
    from core.dossier import Dossier
    dos, huidig = None, None
    f = request.files.get("bestand")
    if f and f.filename:                       # optioneel: direct een bestand meesturen
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in (".xml", ".json", ".csv"):
            flash("Alleen .xml (VABI), .json (dossier) of .csv (MagicPlan)."); return redirect(url_for("home"))
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        up = os.path.join(UPLOAD_DIR, "upload" + ext)
        f.save(up)
        try:
            if ext == ".xml":
                dos = parse_monitor(up)[0]
                try:
                    huidig = _verdict(read_results(up))
                except Exception:
                    huidig = None
            elif ext == ".json":
                dos = load_json(up)
            else:
                from magicplan.statistics_csv import build_dossier
                dos, _ = build_dossier(up, straat=request.form.get("straat", ""),
                                       postcode=request.form.get("postcode", ""),
                                       plaats=request.form.get("plaats", ""),
                                       woningtype=request.form.get("woningtype", ""))
        except Exception as e:
            flash("Kon bestand niet lezen: %s" % e); return redirect(url_for("home"))
    if dos is None:                            # normaal pad: leeg project
        dos = Dossier()
    # adres/type uit het formulier
    _split_adres(request.form.get("straat"), dos)
    if request.form.get("postcode"):
        dos.identificatie.postcode = request.form["postcode"].strip().upper().replace(" ", "")
    if request.form.get("plaats"):
        dos.identificatie.plaats = request.form["plaats"].strip()
    if request.form.get("woningtype"):
        dos.identificatie.woningtype = request.form["woningtype"].strip()
    tag = _tag(dos)
    os.makedirs(_pdir(tag), exist_ok=True)
    dfile = "dossier_%s.json" % tag
    save_json(dos, os.path.join(_pdir(tag), dfile))
    if huidig is None:
        huidig = _verdict(dos, is_dossier=True)
    st = {"tag": tag, "adres": "%s %s, %s" % (dos.identificatie.straat or "", dos.identificatie.huisnummer or "",
          dos.identificatie.plaats or ""), "stap": "opname", "dossier_file": dfile, "huidig": huidig,
          "na": None, "foto_voorkant": "", "foto_huisnummer": "", "keuze": [], "totaal": 0}
    _save_state(tag, st)
    return redirect(url_for("opname", tag=tag))


@app.route("/project/<tag>")
@login_required
def project(tag):
    st = _load_state(tag)
    if not st:
        abort(404)
    stap = st.get("stap", "opname")
    doelen = {"opname", "huidig", "maatregelen", "vabi", "afronden"}
    doel = "afronden" if stap == "klaar" else (stap if stap in doelen else "opname")
    return redirect(url_for(doel, tag=tag))


@app.route("/project/<tag>/huidig", methods=["GET", "POST"])
@login_required
def huidig(tag):
    """Huidige staat: laad de VABI-export van de HUIDIGE woning terug -> label + Standaard-nulmeting."""
    st = _load_state(tag)
    dos = _dossier(tag)
    if not st or not dos:
        abort(404)
    if st.get("stap") == "opname":            # binnengekomen vanuit de opname -> stap bijwerken
        st["stap"] = "huidig"
        _save_state(tag, st)
    if request.method == "POST":
        ex = request.files.get("export")
        if ex and ex.filename:
            p = os.path.join(_pdir(tag), "vabi_export_huidig_%s.xml" % tag)
            ex.save(p)
            try:
                st["huidig"] = _verdict(read_results(p))
                # het huidige label/energiebehoefte ook in het dossier (voor het isolatieplan V1-V6)
                try:
                    b = dos.berekening
                    b.label_huidig = st["huidig"].get("label") or b.label_huidig
                    b.kwh_m2_huidig = st["huidig"].get("behoefte")
                    b.standaard_eis_kwh_m2 = st["huidig"].get("standaard")
                    save_json(dos, os.path.join(_pdir(tag), st["dossier_file"]))
                except Exception:
                    pass
                flash("Huidige staat ingeladen: label %s." % st["huidig"].get("label", "—"))
            except Exception as e:
                flash("Kon de VABI-export niet lezen: %s" % e)
            _save_state(tag, st)
        else:
            flash("Geen VABI-export gekozen.")
        return redirect(url_for("huidig", tag=tag))
    return page(HUIDIG, stepper=stepper("huidig", st), tag=tag, st=st, d=dos, h=st.get("huidig") or {})


# ---------------- opname-editor ----------------
def _f2(v):
    try:
        return float(str(v).replace(",", ".")) if str(v).strip() else None
    except (ValueError, TypeError):
        return None


def _dos_save(tag, st, dos):
    save_json(dos, os.path.join(_pdir(tag), st["dossier_file"]))


def _docx_naar_pdf(docx_pad, pdf_pad):
    """MS Word (COM, via PowerShell) zet de gevulde template om naar PDF — lay-out blijft 1-op-1."""
    import subprocess
    ps = ('$ErrorActionPreference="Stop";$w=New-Object -ComObject Word.Application;$w.Visible=$false;'
          '$d=$w.Documents.Open("%s");$d.SaveAs("%s",17);$d.Close();$w.Quit()'
          % (docx_pad.replace('"', ""), pdf_pad.replace('"', "")))
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, timeout=120, capture_output=True)


def _plan_json(tag, st, dos, vres):
    """Gestructureerd isolatieplan-JSON (M29 Bijlage 1 punt 10a: JSON + PDF als leverformaat)."""
    import dataclasses
    plan = {
        "formaat": "nijbegun-isolatieplan", "versie": 1,
        "gegenereerd_op": datetime.date.today().isoformat(),
        "tool": {"naam": "Poortinga EPA-tool", "rekenkern": "Vabi EPA-W (geattesteerd, NTA 8800)"},
        "adviseur": dataclasses.asdict(dos.adviseur),
        "identificatie": dataclasses.asdict(dos.identificatie),
        "berekening": {"huidig": st.get("huidig"), "na_maatregelen": st.get("na"),
                       "totaal_subsidietabel_incl_btw": st.get("totaal")},
        "maatregelen_subsidietabel": [dataclasses.asdict(m) for m in dos.maatregelen],
        "advies_30pct_isde": st.get("isde") or [],
        "toelichting": st.get("toelichting", ""),
        "haalbaarheid": {k.get("code", ""): k.get("haalbaarheid", "") for k in (st.get("keuze") or [])},
    }
    try:
        plan["ventilatie"] = json.loads(json.dumps(vres, default=str))
    except Exception:
        pass
    with open(os.path.join(_pdir(tag), "isolatieplan_%s.json" % tag), "w", encoding="utf-8") as fh:
        json.dump(plan, fh, ensure_ascii=False, indent=1, default=str)


@app.route("/project/<tag>/opname")
@login_required
def opname(tag):
    st = _load_state(tag)
    dos = _dossier(tag)
    if not st or not dos:
        abort(404)
    orde = {"dak": 0, "gevel": 1, "paneel": 2, "kozijn": 3, "vloer": 4}
    elementen = list(enumerate(dos.schil))
    per_zone = {}
    for i, s in elementen:
        per_zone.setdefault(s.rekenzone or 1, []).append((i, s))
    zones = []
    for rz in sorted(per_zone):
        rows = sorted(per_zone[rz], key=lambda t: (orde.get((t[1].type or "").lower(), 9), t[1].id))
        zones.append((rz, rows))
    verlies = sum((s.oppervlakte_m2 or 0) for s in dos.schil
                  if (s.begrenzing or "") != "AVR" and s.type not in ("kozijn", "paneel"))
    # gevels zijn BRUTO (b x h; ramen/deuren zitten erin) -> kozijnen niet dubbel tellen
    ag = dos.geometrie.gebruiksoppervlakte_ag_m2 or 0
    bj_titel, bj_html = bouwjaar_mod.hint(dos.identificatie.bouwjaar)
    return page(OPNAME_TMPL, stepper=stepper("opname", st), tag=tag, st=st, d=dos,
                elementen=elementen, zones=zones, verlies=verlies, ag=ag,
                bj_titel=bj_titel, bj_html=bj_html, woningtypes=WONINGTYPE_OPTS,
                begr_opts=BEGR_OPTS, ori_opts=ORI_OPTS, glas_opts=GLAS_OPTS, koz_opts=KOZ_OPTS, ico=TYPE_ICO)


@app.route("/project/<tag>/opname/magicplan", methods=["POST"])
@login_required
def opname_magicplan(tag):
    """Laad een MagicPlan Statistics-CSV (of dossier .json) in het bestaande project — vult de gebouwboom
    en gegevens, met behoud van het reeds ingevulde adres/woningtype waar het CSV die niet levert."""
    st, dos = _load_state(tag), _dossier(tag)
    if not st or not dos:
        abort(404)
    f = request.files.get("bestand")
    if not f or not f.filename:
        flash("Geen bestand gekozen."); return redirect(url_for("opname", tag=tag))
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in (".csv", ".json"):
        flash("Alleen een MagicPlan Statistics-CSV of dossier .json."); return redirect(url_for("opname", tag=tag))
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    up = os.path.join(UPLOAD_DIR, "opname_%s%s" % (tag, ext))
    f.save(up)
    oud = dos.identificatie
    notes = []
    try:
        if ext == ".json":
            nieuw = load_json(up)
        else:
            from magicplan.statistics_csv import build_dossier
            nieuw, notes = build_dossier(up, straat=oud.straat, postcode=oud.postcode,
                                         plaats=oud.plaats, woningtype=oud.woningtype)
    except Exception as e:
        flash("Kon de opname niet lezen: %s" % e); return redirect(url_for("opname", tag=tag))
    # "ZELF DOEN IN VABI"-lijst: parser-notes (narekenen/KV/multi-zone/ontbrekend) + generator-flags
    # (kwaliteitsverklaring -> Invoer+BCRG-code handmatig; onbekende types) direct bij de upload tonen.
    acties = ["VÓÓR het importeren in Vabi: Algemeen invullen met Objecttype=Woning, "
              "Bouwfase=Bestaande bouw, Opname=Basisopname. Laat je die leeg, dan weigert "
              "EPA de Objecten-import ('komen niet overeen')."]
    acties += [str(n) for n in (notes or [])]
    try:
        from vabi.constructie_generate import resolve_constructies
        _, _, _issues = resolve_constructies(nieuw)
        acties += [str(i) for i in _issues if str(i) not in acties]
    except Exception as e:
        acties.append("VABI-voorcontrole kon niet draaien: %s" % str(e)[:90])
    st["vabi_acties"] = acties
    # behoud eerder ingevulde identificatie waar de import leeg is (bouwjaar: BAG/lead-waarde
    # mag niet weggevaagd worden door een CSV zonder Bouwjaar-veld)
    for attr in ("straat", "huisnummer", "postcode", "plaats", "woningtype", "bouwjaar", "bag_vboid"):
        if not getattr(nieuw.identificatie, attr, "") and getattr(oud, attr, ""):
            setattr(nieuw.identificatie, attr, getattr(oud, attr))
    save_json(nieuw, os.path.join(_pdir(tag), st["dossier_file"]))
    st["adres"] = "%s %s, %s" % (nieuw.identificatie.straat or "", nieuw.identificatie.huisnummer or "",
                                 nieuw.identificatie.plaats or "")
    _save_state(tag, st)
    flash("MagicPlan-opname ingeladen (%d vlakken)%s — loop de gegevens na." % (len(nieuw.schil),
          (" · %d actiepunt(en) voor Vabi — zie de gele kaart" % len(acties)) if acties else ""))
    return redirect(url_for("opname", tag=tag))


@app.route("/project/<tag>/opname/algemeen", methods=["POST"])
@login_required
def opname_algemeen(tag):
    st, dos = _load_state(tag), _dossier(tag)
    if not st or not dos:
        abort(404)
    f = request.form
    dos.identificatie.bag_vboid = f.get("bag_vboid", "").strip()
    dos.identificatie.woningtype = f.get("woningtype", dos.identificatie.woningtype).strip()
    dos.identificatie.orientatie_voorgevel = f.get("ori_voor", "").strip()
    for veld, attr in (("bouwjaar", "bouwjaar"), ("renovatiejaar", "renovatiejaar")):
        v = f.get(veld, "").strip()
        if v.isdigit():
            setattr(dos.identificatie, attr, int(v))
        elif not v:
            setattr(dos.identificatie, attr, None)
    dos.opname.gevelhoogte_m = _f2(f.get("gevelhoogte")) or dos.opname.gevelhoogte_m
    dos.opname.qv10_waarde = _f2(f.get("qv10"))
    ag = _f2(f.get("ag"))
    if ag:
        dos.geometrie.gebruiksoppervlakte_ag_m2 = ag
    _dos_save(tag, st, dos)
    flash("Algemeen opgeslagen.")
    return redirect(url_for("opname", tag=tag))


@app.route("/project/<tag>/opname/el/<int:i>", methods=["POST"])
@login_required
def opname_el(tag, i):
    st, dos = _load_state(tag), _dossier(tag)
    if not st or not dos or i >= len(dos.schil):
        abort(404)
    s, f = dos.schil[i], request.form
    s.id = f.get("id", s.id).strip() or s.id
    s.subtype = f.get("subtype", s.subtype).strip()
    s.oppervlakte_m2 = _f2(f.get("m2")) or 0.0
    s.orientatie = f.get("orientatie", "").strip()
    s.begrenzing = f.get("begrenzing", s.begrenzing)
    s.rekenzone = int(f.get("rekenzone") or 1)
    s.opmerkingen = f.get("opmerkingen", s.opmerkingen)
    if (s.type or "").lower() == "kozijn":
        s.glastype = f.get("glastype", "").strip()
        s.kozijnmateriaal = f.get("kozijnmateriaal", "").strip()
        s.u_huidig = _f2(f.get("u"))
    else:
        s.rc_huidig = _f2(f.get("rc"))
        s.isolatie_aanwezig = f.get("isolatie", s.isolatie_aanwezig)
        s.isolatiedikte_mm = _f2(f.get("dikte"))
    if (s.type or "").lower() == "dak":
        s.hellingshoek = _f2(f.get("helling"))
    _dos_save(tag, st, dos)
    return redirect(url_for("opname", tag=tag))


@app.route("/project/<tag>/opname/el/<int:i>/kopie", methods=["POST"])
@login_required
def opname_el_kopie(tag, i):
    st, dos = _load_state(tag), _dossier(tag)
    if not st or not dos or i >= len(dos.schil):
        abort(404)
    kop = copy.deepcopy(dos.schil[i])
    kop.id = kop.id + "-kopie"
    dos.schil.insert(i + 1, kop)
    _dos_save(tag, st, dos)
    return redirect(url_for("opname", tag=tag))


@app.route("/project/<tag>/opname/el/<int:i>/weg", methods=["POST"])
@login_required
def opname_el_weg(tag, i):
    st, dos = _load_state(tag), _dossier(tag)
    if not st or not dos or i >= len(dos.schil):
        abort(404)
    dos.schil.pop(i)
    _dos_save(tag, st, dos)
    return redirect(url_for("opname", tag=tag))


@app.route("/project/<tag>/opname/el/nieuw", methods=["POST"])
@login_required
def opname_el_nieuw(tag):
    st, dos = _load_state(tag), _dossier(tag)
    if not st or not dos:
        abort(404)
    from core.dossier import SchilDeel
    t = request.form.get("type", "gevel")
    n = sum(1 for s in dos.schil if s.type == t) + 1
    _sub = {"kozijn": "Raam", "paneel": "Paneel"}.get(t, "")
    dos.schil.append(SchilDeel(id="%s-nieuw-%d" % (t, n), type=t, subtype=_sub, begrenzing="Buitenlucht"))
    _dos_save(tag, st, dos)
    flash("Vlak toegevoegd — vul de gegevens in.")
    return redirect(url_for("opname", tag=tag))


@app.route("/project/<tag>/opname/installaties", methods=["POST"])
@login_required
def opname_installaties(tag):
    st, dos = _load_state(tag), _dossier(tag)
    if not st or not dos:
        abort(404)
    f = request.form
    dos.ventilatie.systeem = f.get("vent_systeem", dos.ventilatie.systeem).strip()
    dos.ventilatie.subsysteem_code = f.get("vent_sub", dos.ventilatie.subsysteem_code).strip()
    vw = dos.installaties.verwarming
    vw.type_opwekker = f.get("vw_opwekker", vw.type_opwekker).strip()
    vw.subtype = f.get("vw_subtype", vw.subtype).strip()
    vw.afgifte = f.get("vw_afgifte", vw.afgifte).strip()
    vw.aanvoertemperatuur = f.get("vw_temp", vw.aanvoertemperatuur).strip()
    tw = dos.installaties.tapwater
    tw.type_toestel = f.get("tw_toestel", tw.type_toestel).strip()
    j = f.get("tw_jaar", "").strip()
    tw.installatiejaar = int(j) if j.isdigit() else tw.installatiejaar
    _dos_save(tag, st, dos)
    flash("Installaties opgeslagen.")
    return redirect(url_for("opname", tag=tag))


@app.route("/project/<tag>/opname/vabi_huidig")
@login_required
def opname_vabi_huidig(tag):
    """De HUIDIGE staat als 3 VABI-bibliotheken (zip) — voor de 0-meting in Vabi."""
    st, dos = _load_state(tag), _dossier(tag)
    if not st or not dos:
        abort(404)
    outdir = os.path.join(_pdir(tag), "vabi_huidig")
    try:
        generate_all.generate_all(dos, outdir, prefix="huidig")
    except Exception as e:
        flash("VABI-export genereren mislukte: %s" % e)
        return redirect(url_for("opname", tag=tag))
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
        for p in glob.glob(os.path.join(outdir, "*")):
            z.write(p, os.path.basename(p))
    mem.seek(0)
    return Response(mem.read(), mimetype="application/zip",
                    headers={"Content-Disposition": "attachment; filename=vabi_huidig_%s.zip" % tag})


@app.route("/project/<tag>/naar_maatregelen")
@login_required
def naar_maatregelen(tag):
    st = _load_state(tag)
    if not st:
        abort(404)
    st["stap"] = "maatregelen"
    _save_state(tag, st)
    return redirect(url_for("maatregelen", tag=tag))


@app.route("/project/<tag>/maatregelen", methods=["GET", "POST"])
@login_required
def maatregelen(tag):
    st = _load_state(tag)
    dos = _dossier(tag)
    if not st or not dos:
        abort(404)
    catalog = laad_catalog()
    if request.method == "POST":
        groepen = suggesties(dos, catalog)
        keuze_std, keuze_isde, haal = [], [], {}
        for i in range(len(groepen)):
            bucket = request.form.get("bucket_%d" % i, "standaard")
            h = request.form.get("haal_%d" % i, "").strip()
            if h:
                haal[str(i)] = h
            if bucket == "geen":
                continue
            item = {"code": request.form.get("code_%d" % i), "onderdeel": request.form.get("onderdeel_%d" % i),
                    "m2": float(request.form.get("m2_%d" % i) or 0), "rc_u_doel": request.form.get("doel_%d" % i, ""),
                    "haalbaarheid": h, "subposten": []}
            (keuze_std if bucket == "standaard" else keuze_isde).append(item)
        # vrije catalogus-keuze (zelf toegevoegd) meenemen
        for v in st.get("vrij") or []:
            item = {"code": v["code"], "onderdeel": "", "m2": float(v.get("hoeveelheid") or 0),
                    "rc_u_doel": "", "haalbaarheid": v.get("haalbaarheid", ""), "subposten": []}
            (keuze_std if v.get("bucket") == "standaard" else keuze_isde).append(item)
        maatregelen_std, totaal = bouw_maatregelen(catalog, keuze_std)
        maatregelen_isde, _ = bouw_maatregelen(catalog, keuze_isde)
        dos.maatregelen = maatregelen_std
        save_json(dos, os.path.join(_pdir(tag), st["dossier_file"]))
        st["keuze"] = keuze_std
        st["haal"] = haal
        st["isde"] = [{"code": m.code, "onderdeel": m.onderdeel, "omschrijving": m.omschrijving} for m in maatregelen_isde]
        st["totaal"] = totaal
        st["stap"] = "vabi"
        _save_state(tag, st)
        return redirect(url_for("vabi", tag=tag))
    vrij = st.get("vrij") or []
    vrij_tot = round(sum(v.get("kosten", 0) for v in vrij if v.get("bucket") == "standaard"), 2)
    return page(MAATREGELEN, stepper=stepper("maatregelen", st), groepen=suggesties(dos, catalog),
                boom=catalogus_boom(catalog), vrij=vrij, vrij_tot=vrij_tot, tag=tag, st=st)


@app.route("/project/<tag>/maatregelen/add", methods=["POST"])
@login_required
def maatregel_add(tag):
    st = _load_state(tag)
    if not st:
        abort(404)
    m = zoek_maatregel(laad_catalog(), request.form.get("code", ""))
    if not m:
        flash("Maatregel niet gevonden in de catalogus.")
        return redirect(url_for("maatregelen", tag=tag))
    hoev = _f2(request.form.get("hoeveelheid")) or 1.0
    prijs = round(m.get("prijs_per_eenheid_incl_btw") or 0, 2)
    st.setdefault("vrij", []).append({
        "code": m["code"], "omschrijving": (m.get("omschrijving") or "").strip(),
        "eenheid": m.get("eenheid") or "m²", "prijs": prijs, "hoeveelheid": hoev,
        "kosten": round(prijs * hoev, 2), "bucket": request.form.get("bucket", "standaard"),
        "haalbaarheid": ""})
    _save_state(tag, st)
    return redirect(url_for("maatregelen", tag=tag))


@app.route("/project/<tag>/maatregelen/del/<int:idx>", methods=["POST"])
@login_required
def maatregel_del(tag, idx):
    st = _load_state(tag)
    if not st:
        abort(404)
    vrij = st.get("vrij") or []
    if 0 <= idx < len(vrij):
        vrij.pop(idx)
        st["vrij"] = vrij
        _save_state(tag, st)
    return redirect(url_for("maatregelen", tag=tag))


@app.route("/project/<tag>/vabi", methods=["GET", "POST"])
@login_required
def vabi(tag):
    st = _load_state(tag)
    dos = _dossier(tag)
    if not st or not dos:
        abort(404)
    outdir = os.path.join(_pdir(tag), "vabi_na")
    if request.method == "POST":
        ex = request.files.get("export")
        if ex and ex.filename:
            p = os.path.join(_pdir(tag), "vabi_export_na_%s.xml" % tag)
            ex.save(p)
            try:
                st["na"] = _verdict(read_results(p))
            except Exception as e:
                flash("Kon de VABI-export niet lezen: %s" % e)
            if st.get("na", {}).get("voldoet"):
                st["stap"] = "afronden"
            _save_state(tag, st)
        return redirect(url_for("vabi", tag=tag))
    # genereer toekomstige-staat-bibliotheken (Qv10 na maatregelen: renovatiejaar-variant, zoals het portal)
    renojaar = request.args.get("renojaar", "").strip() or str(st.get("reno_variant") or datetime.date.today().year)
    if renojaar.isdigit():
        st["reno_variant"] = int(renojaar)
        _save_state(tag, st)
    try:
        toekomst = _toekomstige_staat(dos, dos.maatregelen)
        if st.get("reno_variant"):
            toekomst.identificatie.renovatiejaar = st["reno_variant"]
            toekomst.identificatie.renovatiejaar_toelichting = "Nij Begun-maatregelenvariant (Qv10 forfaitair op renovatiejaar)"
        generate_all.generate_all(toekomst, outdir, prefix="na")
    except Exception as e:
        flash("VABI-import genereren mislukte: %s" % e)
    vabi_files = sorted(os.path.basename(p) for p in glob.glob(os.path.join(outdir, "*.xml")))
    verlies = sum((s.oppervlakte_m2 or 0) for s in dos.schil
                  if (s.begrenzing or "") != "AVR" and s.type not in ("kozijn", "paneel"))
    # gevels zijn BRUTO (b x h; ramen/deuren zitten erin) -> kozijnen niet dubbel tellen
    ag = dos.geometrie.gebruiksoppervlakte_ag_m2 or 0
    return page(VABI, stepper=stepper("vabi", st), tag=tag, vabi_files=vabi_files, na=st.get("na"),
                h=st.get("huidig") or {}, st=st, verlies=verlies, ag=ag, renojaar=renojaar)


@app.route("/project/<tag>/afronden")
@login_required
def afronden(tag):
    st = _load_state(tag)
    dos = _dossier(tag)
    if not st or not dos:
        abort(404)
    pdir = _pdir(tag)
    # adviseur-defaults uit config mergen
    adv = _cfg().get("adviseur", {})
    if not dos.adviseur.naam and adv.get("naam"):
        dos.adviseur.naam = adv["naam"]
        dos.adviseur.bedrijf = adv.get("bedrijf", ""); dos.adviseur.telefoon = adv.get("telefoon", "")
    if request.args.get("regen") or not glob.glob(os.path.join(pdir, "isolatieplan_*.docx")):
        try:
            docx_pad = os.path.join(pdir, "isolatieplan_%s.docx" % tag)
            fill_template.fill(dos, TEMPLATE_DOCX, docx_pad)
            # LEVERFORMAAT = PDF (M29 Bijlage 1 punt 10a: JSON en PDF). Word = alleen de vul-motor
            # (M29-lay-out 1-op-1); MS Word zet 'm om naar PDF (COM). Niet in tests (opent Word).
            if not app.config.get("TESTING"):
                try:
                    _docx_naar_pdf(docx_pad, os.path.join(pdir, "isolatieplan_%s.pdf" % tag))
                except Exception as e:
                    flash("PDF maken lukte niet (MS Word vereist op deze machine): %s" % str(e)[:90])
        except Exception as e:
            flash("Isolatieplan genereren mislukte: %s" % e)
        try:
            with open(os.path.join(pdir, "fotochecklist_%s.txt" % tag), "w", encoding="utf-8") as fh:
                fh.write(foto_checklist.generate(dos))
        except Exception:
            pass
    # ventilatieplan (altijd vers) + de VENTILATIEBEREKENING-tabel (Beoordelingsformulier vraagt de berekening).
    # Robuust: een (nog) leeg dossier mag de Afronden-pagina NOOIT laten crashen.
    vres, svg = None, "<p class=muted>Nog geen ruimtes in de opname — ventilatieplan verschijnt zodra die er zijn.</p>"
    try:
        vres = vent_bereken(dos.geometrie.ruimtes)
        svg = ventilatieplan_svg(vres, adres=st.get("adres", ""))
        with open(os.path.join(pdir, "ventilatieplan_%s.svg" % tag), "w", encoding="utf-8") as fh:
            fh.write(svg)
        with open(os.path.join(pdir, "ventilatieberekening_%s.txt" % tag), "w", encoding="utf-8") as fh:
            fh.write(vent_rapport(vres))
    except Exception as e:
        flash("Ventilatieplan (auto) kon niet gemaakt worden: %s — je kunt een eigen plan uploaden." % str(e)[:90])
    # leverformaat JSON (M29 punt 10a) — altijd vers
    try:
        _plan_json(tag, st, dos, vres)
    except Exception as e:
        flash("Isolatieplan-JSON genereren mislukte: %s" % str(e)[:90])
    # KWACO-validator (maatregelcodes/kruipruimte/Standaard-blockers) -> in de indien-check
    try:
        codes = validator_mod.load_catalog_codes(os.path.join(TOOL_DIR, "catalog", "catalog.json"))
        st["kwaco"] = [str(x) for x in (validator_mod.validate(dos, codes) or [])]
    except Exception:
        st["kwaco"] = []
    # losse bijlage: toelichting + technische haalbaarheid per maatregel (M29-eis Bijlage 1 punt 13)
    regels = ["TOELICHTING OP ADVIES + TECHNISCHE HAALBAARHEID — %s" % st.get("adres", ""), "=" * 60, ""]
    if st.get("toelichting"):
        regels += ["Persoonlijke toelichting:", st["toelichting"], ""]
    regels.append("Technische haalbaarheid per maatregel (vastgesteld in de woning):")
    for k in (st.get("keuze") or []):
        regels.append("  %s — %s" % (k.get("code", ""), (k.get("haalbaarheid") or "geen bijzonderheden genoteerd")))
    for v in (st.get("vrij") or []):
        regels.append("  %s — %s (zelf gekozen, %s %s)" % (v.get("code", ""),
                      v.get("haalbaarheid") or "geen bijzonderheden genoteerd",
                      v.get("hoeveelheid", ""), v.get("eenheid", "")))
    if st.get("isde"):
        regels += ["", "Geadviseerd BUITEN de subsidietabel (30% ISDE — bouwfysisch wenselijk, "
                   "niet nodig voor de Standaard):"]
        for m in st["isde"]:
            regels.append("  %s — %s (%s)" % (m.get("code", ""), m.get("omschrijving", ""), m.get("onderdeel", "")))
    with open(os.path.join(pdir, "haalbaarheid_toelichting_%s.txt" % tag), "w", encoding="utf-8") as fh:
        fh.write("\n".join(regels) + "\n")
    st["stap"] = "klaar"
    _save_state(tag, st)
    files = sorted(os.path.basename(p) for p in glob.glob(os.path.join(pdir, "*"))
                   if os.path.isfile(p) and not p.endswith("project.json"))
    return page(AFRONDEN, stepper=stepper("afronden", st), tag=tag, vent_svg=svg, st=st,
                beoord=_beoordeling(tag, st, dos), files=files)


@app.route("/project/<tag>/fotos", methods=["POST"])
@login_required
def fotos(tag):
    st = _load_state(tag)
    if not st:
        abort(404)
    n = 0
    for veld in ("foto_voorkant", "foto_huisnummer"):
        fp = request.files.get(veld)
        if fp and fp.filename:
            ext = os.path.splitext(fp.filename)[1].lower() or ".jpg"
            naam = "%s_%s%s" % (veld, tag, ext)
            fp.save(os.path.join(_pdir(tag), naam))
            st[veld] = naam
            n += 1
    _save_state(tag, st)
    flash("%d foto('s) opgeslagen." % n if n else "Geen foto gekozen.")
    return redirect(url_for("afronden", tag=tag) + "?regen=1")


def _veilige_naam(naam):
    """Bestandsnaam ontdoen van pad-/rare tekens (upload-veiligheid)."""
    naam = os.path.basename(naam or "").replace("\\", "_")
    naam = re.sub(r"[^A-Za-z0-9._ +()\-]", "_", naam).strip() or "bestand"
    return naam[:120]


@app.route("/project/<tag>/bijlagen", methods=["POST"])
@login_required
def bijlagen(tag):
    """Eigen ventilatieplan + vrije bijlagen (facturen/plattegrond/foto's) — gaan mee in de export."""
    st = _load_state(tag)
    if not st:
        abort(404)
    pdir = _pdir(tag)
    n = 0
    vp = request.files.get("ventilatieplan_eigen")
    if vp and vp.filename:
        ext = os.path.splitext(vp.filename)[1].lower() or ".pdf"
        naam = "ventilatieplan_eigen_%s%s" % (tag, ext)
        vp.save(os.path.join(pdir, naam))
        st["ventilatieplan_eigen"] = naam
        n += 1
    bdir = os.path.join(pdir, "bijlagen")
    os.makedirs(bdir, exist_ok=True)
    huidig = list(st.get("bijlagen") or [])
    for f in request.files.getlist("bijlagen"):
        if f and f.filename:
            naam = _veilige_naam(f.filename)
            f.save(os.path.join(bdir, naam))
            if naam not in huidig:
                huidig.append(naam)
            n += 1
    st["bijlagen"] = huidig
    _save_state(tag, st)
    flash("%d bestand(en) geüpload — ze zitten in de export-bundel." % n if n else "Geen bestand gekozen.")
    return redirect(url_for("afronden", tag=tag))


@app.route("/project/<tag>/bijlage/<path:naam>/weg")
@login_required
def bijlage_weg(tag, naam):
    st = _load_state(tag)
    if not st:
        abort(404)
    naam = os.path.basename(naam)
    p = os.path.join(_pdir(tag), "bijlagen", naam)
    if os.path.isfile(p):
        os.remove(p)
    st["bijlagen"] = [b for b in (st.get("bijlagen") or []) if b != naam]
    _save_state(tag, st)
    flash("Bijlage verwijderd.")
    return redirect(url_for("afronden", tag=tag))


@app.route("/project/<tag>/toelichting", methods=["POST"])
@login_required
def toelichting(tag):
    st = _load_state(tag)
    if not st:
        abort(404)
    st["toelichting"] = request.form.get("toelichting", "").strip()
    _save_state(tag, st)
    flash("Toelichting opgeslagen — wordt in de bijlage meegenomen.")
    return redirect(url_for("afronden", tag=tag) + "?regen=1")


@app.route("/project/<tag>/toelichting/assist", methods=["POST"])
@login_required
def toelichting_assist(tag):
    """SOBOLT-achtige assistentie: 'voorstel' = offline adviestekst uit het dossier; 'verbeter' = Claude-API."""
    st, dos = _load_state(tag), _dossier(tag)
    if not st or not dos:
        abort(404)
    tekst = request.form.get("toelichting", "").strip()
    if request.form.get("actie") == "voorstel":
        try:
            st["toelichting"] = (tekst + "\n\n" if tekst else "") + genereer_advies(dos, dos.maatregelen)
            flash("Tekstvoorstel gegenereerd (offline, uit je opname + maatregelen) — lees na en pas aan.")
        except Exception as e:
            flash("Tekstvoorstel mislukte: %s" % str(e)[:80])
    else:
        uit, fout = ai_mod.verbeter_tekst(tekst, _cfg())
        if fout:
            st["toelichting"] = tekst
            flash(fout)
        else:
            st["toelichting"] = uit
            flash("Toelichting verbeterd door Claude — lees na voordat je opslaat.")
    _save_state(tag, st)
    return redirect(url_for("afronden", tag=tag))


@app.route("/project/<tag>/export")
@login_required
def export(tag):
    pdir = _pdir(tag)
    if not os.path.isdir(pdir):
        abort(404)
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
        for p in glob.glob(os.path.join(pdir, "*")):
            if os.path.isfile(p) and not p.endswith("project.json"):
                z.write(p, os.path.basename(p))
        for p in glob.glob(os.path.join(pdir, "vabi_na", "*")):
            z.write(p, os.path.join("vabi_na", os.path.basename(p)))
        for p in glob.glob(os.path.join(pdir, "fotos", "*")):    # MagicPlan-foto's (fotoblad)
            if os.path.isfile(p):
                z.write(p, os.path.join("fotos", os.path.basename(p)))
        for p in glob.glob(os.path.join(pdir, "bijlagen", "*")):  # eigen bijlagen (facturen/plattegrond/...)
            if os.path.isfile(p):
                z.write(p, os.path.join("bijlagen", os.path.basename(p)))
    mem.seek(0)
    return Response(mem.read(), mimetype="application/zip",
                    headers={"Content-Disposition": "attachment; filename=isolatieplan_%s.zip" % tag})


@app.route("/download/<tag>/<path:filename>")
@login_required
def download(tag, filename):
    pdir = _pdir(tag)
    if ".." in filename or not os.path.isdir(pdir):
        abort(404)
    # bijlagen staan in de submap bijlagen/ — daar ook zoeken als het bestand niet in de root staat
    if not os.path.isfile(os.path.join(pdir, filename)) and os.path.isfile(os.path.join(pdir, "bijlagen", filename)):
        return send_from_directory(os.path.join(pdir, "bijlagen"), filename, as_attachment=True)
    return send_from_directory(pdir, filename, as_attachment=True)


# ---------------- leads (Nij Begun-portal-toewijzingen) ----------------
LEADS = """<h1>Leads</h1>
<p class=lead>Toegewezen bewoners uit het Nij Begun-portal — plak de mail, volg de status, genereer de kennismakingsmail.</p>
<div class=card><h2>Nieuwe lead toevoegen</h2>
<p class=muted>Plak de <b>portal-mail(s)</b> in het vak, óf <b>selecteer de mails in Outlook en sleep ze naar een map</b>
(worden .eml-bestanden) en kies ze hieronder — mag met 60 tegelijk. Het JSON-blok wordt eruit gehaald;
de gegevens blijven <b>lokaal</b> op deze computer (AVG).</p>
<form method=post action="{{url_for('leads_add')}}" enctype="multipart/form-data">
<textarea name=mailtekst rows=4 placeholder='{"BagAdresId":"...","Email":"...","Naam":"..."}'></textarea>
<label class="muted small" style="display:block;margin-top:8px">Of upload gesleepte Outlook-mails (.eml, meerdere tegelijk):
<input type=file name=emls multiple accept=".eml,.txt" style="margin-top:4px"></label>
<div class=btn-row><button class=btn>Lead(s) toevoegen</button>
<span class="muted small">Plakken en uploaden mag door elkaar — elk {...}-blok wordt een lead, dubbelen worden overgeslagen.</span>
<span class=spacer></span>
<a class="btn sec" href="{{url_for('leads_ontvangst')}}">✉ Ontvangstmail (alle nieuwe, BCC)</a>
<a class="btn sec" href="{{url_for('leads_csv')}}">⬇ CSV</a></div></form></div>
{% if leads %}<div class=card><h2>{{leads|length}} lead(s)</h2><div class="table-wrap"><table>
<tr><th>Ontvangen</th><th>Naam</th><th>Adres</th><th>Contact</th><th>Status</th><th></th></tr>
{% for l in leads %}<tr>
<td class=small>{{l.ontvangen}}</td>
<td><b>{{l.naam}}</b></td>
<td>{{l.adres}}{% if l.bouwjaar %}<br><span class="pill blue">{{l.bouwjaar}}</span> <span class="pill gray">{{l.oppervlakte_m2}} m²</span>{% endif %}</td>
<td class=small>{{l.telefoon}}<br>{{l.email}}</td>
<td><form method=post action="{{url_for('leads_status', lid=l.id)}}">
<select name=status onchange="this.form.submit()">
{% for s in statussen %}<option value="{{s}}" {{'selected' if s==l.status else ''}}>{{s}}</option>{% endfor %}
</select></form>
<form method=post action="{{url_for('leads_afspraak', lid=l.id)}}" style="display:flex;gap:4px;margin-top:6px">
<input type=datetime-local name=wanneer value="{{l.afspraak or ''}}" style="min-height:38px;font-size:13px">
<button class="btn sec" title="Afspraak opslaan (+ project aanmaken)">📅</button></form></td>
<td style="white-space:nowrap">{% if not l.bouwjaar %}<form method=post style="display:inline" action="{{url_for('leads_bag', lid=l.id)}}"><button class="btn sec" title="Straat + bouwjaar + m² uit de BAG halen">🏛 BAG</button></form> {% endif %}<a class="btn sec" href="{{url_for('leads_mail', lid=l.id)}}">✉ mail</a>
{% if l.afspraak %} <a class="btn sec" href="{{url_for('leads_mail', lid=l.id)}}?soort=bevestiging" title="Afspraak-bevestigingsmail (voorbereiding + verwachtingen)">✉ bevestiging</a>{% endif %}
{% if l.project_tag %} <a class="btn green" href="{{url_for('project', tag=l.project_tag)}}" title="Open het gekoppelde project">📂 Project</a>
{% elif l.status in ('afspraak gepland','opname gedaan','plan ingediend','afgerond') %} <form method=post style="display:inline" action="{{url_for('leads_project', lid=l.id)}}"><button class="btn" title="Maak een project met dit adres en ga naar de opname">➕ Project</button></form>{% endif %}
</td></tr>{% endfor %}</table></div>
<p class="muted small">Status wisselen slaat direct op. Volgorde: nieuw → mail gestuurd → gebeld → afspraak gepland → opname gedaan → plan ingediend → afgerond.</p></div>
{% else %}<div class=hint>Nog geen leads. Plak je eerste portal-mail hierboven.</div>{% endif %}"""

LEADS_ONTVANGST = """<h1>Ontvangstbevestiging — bulk</h1>
<p class=lead>{{n}} lead(s) met status <b>nieuw</b>. Maak in je mailprogramma één mail: plak de adressen in het
<b>BCC</b>-veld (nooit Aan/CC — AVG!), jezelf in Aan, en plak onderwerp + tekst. Verstuur zelf.</p>
<div class=card><h2>BCC-adressen ({{n}})</h2><textarea rows=4 id=bcc readonly>{{bcc}}</textarea>
<div class=btn-row><button class="btn sec" type=button onclick="navigator.clipboard.writeText(document.getElementById('bcc').value);this.textContent='✓ Gekopieerd'">Kopieer adressen</button></div></div>
<div class=card><h2>Onderwerp</h2><input readonly value="{{onderwerp}}">
<h2 style="margin-top:14px">Tekst</h2><textarea rows=14 id=body readonly>{{tekst}}</textarea>
<div class=btn-row><button class="btn sec" type=button onclick="navigator.clipboard.writeText(document.getElementById('body').value);this.textContent='✓ Gekopieerd'">Kopieer tekst</button>
<span class=spacer></span>
<form method=post action="{{url_for('leads_ontvangst_verstuurd')}}" onsubmit="return confirm('Alle {{n}} nieuwe leads markeren als mail gestuurd?')">
<button class="btn green">✓ Verstuurd — markeer allen</button></form>
<a class="btn ghost" href="{{url_for('leads_pagina')}}">← terug</a></div></div>"""

LEAD_MAIL = """<h1>Kennismakingsmail — {{l.naam}}</h1>
<p class=lead>Concept. Kopieer of open 'm in je mailprogramma, lees 'm even na en <b>verstuur zelf</b>.</p>
<div class=card><div class=kv><dt>Aan</dt><dd>{{l.email or '—'}}</dd>
<dt>Onderwerp</dt><dd>{{onderwerp}}</dd><dt>Telefoon</dt><dd>{{l.telefoon or '—'}}</dd></div></div>
<div class=card><textarea id=mailbody rows=22 style="font-family:inherit">{{tekst}}</textarea>
<div class=btn-row>
<a class="btn lg" href="mailto:{{l.email}}?subject={{onderwerp|urlencode}}&body={{tekst|urlencode}}">✉ Open in mailprogramma</a>
<button class="btn sec" type=button onclick="navigator.clipboard.writeText(document.getElementById('mailbody').value);this.textContent='✓ Gekopieerd'">Kopieer tekst</button>
<span class=spacer></span>
<form method=post action="{{url_for('leads_status', lid=l.id)}}"><input type=hidden name=status value="mail gestuurd">
<button class="btn green">Markeer 'mail gestuurd'</button></form>
<a class="btn ghost" href="{{url_for('leads_pagina')}}">← terug</a></div></div>
<div class=hint>De mail vraagt de bewoner alvast klaar te leggen: facturen/tekeningen van eerder <b>isolatiewerk</b>
en toegang tot kruipruimte en zolder — de bewijslast voor de <b>isolatie-opname</b> (isolatie telt alleen mee
indien waarneembaar of met factuur/tekening aantoonbaar). Installaties (cv-ketel/warmtepomp/PV) horen bij het
energielabel, niet bij het Nij Begun-isolatieplan — daar vragen we bewust niet naar.</div>"""


@app.route("/leads")
@login_required
def leads_pagina():
    rows = leads_mod.load_leads()
    for r in rows:
        r["adres"] = leads_mod.adres(r)
    rows.sort(key=lambda r: (r.get("status") in ("afgerond", "vervallen"), -r.get("id", 0)))
    return page(LEADS, leads=rows, statussen=leads_mod.STATUSSEN)


@app.route("/leads/add", methods=["POST"])
@login_required
def leads_add():
    tekst = request.form.get("mailtekst", "")
    n_msg = 0
    for f in request.files.getlist("emls"):       # gesleepte Outlook-mails (.eml) — mag met 60 tegelijk
        naam = (f.filename or "").lower()
        if naam.endswith(".msg"):
            n_msg += 1                            # klassiek-Outlook-formaat (OLE-binair) — kunnen we niet lezen
            continue
        if naam.endswith(".eml"):
            tekst += "\n" + leads_mod.tekst_uit_eml(f.read())
        elif naam.endswith(".txt"):
            tekst += "\n" + f.read().decode("utf-8", errors="replace")
    if n_msg:
        flash("%d .msg-bestand(en) overgeslagen — dat is het klassieke Outlook-formaat. Sleep de mails "
              "vanuit de NIEUWE Outlook (geeft .eml), of plak de tekst." % n_msg)
    gevonden = leads_mod.parse_leads_bulk(tekst)
    if not gevonden:
        flash("Kon geen lead-gegevens vinden — plak de portal-mail(s) of sleep .eml-bestanden (met {...}-blok).")
        return redirect(url_for("leads_pagina"))
    rows = leads_mod.load_leads()
    n_nieuw = n_dubbel = 0
    for lead in gevonden:                    # BULK: plak gerust 60 mails in één keer
        rows, nieuw = leads_mod.add_lead(lead, rows)
        n_nieuw += 1 if nieuw else 0
        n_dubbel += 0 if nieuw else 1
    leads_mod.save_leads(rows)
    flash("%d lead(s) toegevoegd%s." % (n_nieuw, (" · %d dubbel overgeslagen" % n_dubbel) if n_dubbel else ""))
    return redirect(url_for("leads_pagina"))


@app.route("/leads/<int:lid>/status", methods=["POST"])
@login_required
def leads_status(lid):
    rows = leads_mod.load_leads()
    st = request.form.get("status", "")
    for r in rows:
        if r.get("id") == lid and st in leads_mod.STATUSSEN:
            r["status"] = st
    leads_mod.save_leads(rows)
    # AUTOMATISCH project aanmaken zodra de afspraak gepland is (idempotent)
    if st == "afspraak gepland":
        tag, bestond = _project_uit_lead(lid, rows, status_door=False)
        if tag and not bestond:
            flash("Afspraak gepland → project %s automatisch aangemaakt. Zet ook de afspraakdatum (📅) "
                  "en verstuur de bevestigingsmail." % tag)
    return redirect(url_for("leads_pagina"))


@app.route("/leads/<int:lid>/bag", methods=["POST"])
@login_required
def leads_bag(lid):
    """Verrijk de lead met openbare BAG-gegevens (straat/woonplaats/bouwjaar/m²) — internet nodig."""
    rows = leads_mod.load_leads()
    r = next((x for x in rows if x.get("id") == lid), None)
    if not r:
        abort(404)
    info, fout = bag_mod.bag_info(r.get("postcode", ""), r.get("huisnummer", ""), r.get("toevoeging", ""))
    if fout:
        flash(fout)
    else:
        for k in ("straat", "woonplaats", "bouwjaar", "oppervlakte_m2", "gebruiksdoel", "verblijfsobject_id"):
            if info.get(k) not in (None, ""):
                r[k] = info[k]
        leads_mod.save_leads(rows)
    return redirect(url_for("leads_pagina"))


def _lead_naar_dossier(lead):
    """Bouw een LEEG dossier uit de lead-identificatie. Draagt alleen adres/BAG-gegevens over;
    naam/telefoon/e-mail blijven in out/leads (AVG — die horen niet in het projectdossier)."""
    from core.dossier import Dossier
    dos = Dossier()
    i = dos.identificatie
    hn = str(lead.get("huisnummer", "")).strip()
    toev = str(lead.get("toevoeging", "")).strip()
    i.huisnummer = (hn + toev) if toev else hn          # 106B -> unieke tag bij appartementen
    i.postcode = str(lead.get("postcode", "")).strip().upper().replace(" ", "")
    if lead.get("straat"):
        i.straat = lead["straat"]
    if lead.get("woonplaats"):
        i.plaats = lead["woonplaats"]
    if lead.get("bouwjaar"):
        try:
            i.bouwjaar = int(lead["bouwjaar"])
        except (TypeError, ValueError):
            pass
    if lead.get("verblijfsobject_id"):
        i.bag_vboid = str(lead["verblijfsobject_id"])
    if lead.get("woningtype"):
        i.woningtype = lead["woningtype"]
    return dos


def _project_uit_lead(lid, rows, status_door=True):
    """Maak (idempotent) een project uit een lead. -> (tag, bestond_al). Persoonsgegevens blijven
    in out/leads (AVG); alleen adres/BAG gaat het dossier in."""
    lead = next((x for x in rows if x.get("id") == lid), None)
    if not lead:
        return None, False
    dos = _lead_naar_dossier(lead)
    tag = _tag(dos)
    if lead.get("project_tag") == tag or _load_state(tag) is not None:
        if lead.get("project_tag") != tag:
            leads_mod.set_project_tag(lid, tag, rows)
        return tag, True
    os.makedirs(_pdir(tag), exist_ok=True)
    dfile = "dossier_%s.json" % tag
    save_json(dos, os.path.join(_pdir(tag), dfile))
    st = {"tag": tag, "adres": "%s %s, %s" % (dos.identificatie.straat or "", dos.identificatie.huisnummer or "",
          dos.identificatie.plaats or ""), "stap": "opname", "dossier_file": dfile,
          "huidig": _verdict(dos, is_dossier=True), "na": None, "foto_voorkant": "", "foto_huisnummer": "",
          "keuze": [], "totaal": 0, "lead_id": lid}
    _save_state(tag, st)
    leads_mod.set_project_tag(lid, tag, rows)
    if status_door:                     # handmatige 📂-knop = opname (bijna) gedaan; auto-routes laten
        for r in rows:                  # de status op 'afspraak gepland' staan (status_door=False)
            if r.get("id") == lid and r.get("status") in ("nieuw", "mail gestuurd", "gebeld", "afspraak gepland"):
                r["status"] = "opname gedaan"
    leads_mod.save_leads(rows)
    return tag, False


@app.route("/leads/<int:lid>/project", methods=["POST"])
@login_required
def leads_project(lid):
    """Handmatig: lead -> project + naar de Opname-stap (idempotent)."""
    rows = leads_mod.load_leads()
    tag, bestond = _project_uit_lead(lid, rows)
    if not tag:
        abort(404)
    flash("Project bestond al — geopend (niets overschreven)." if bestond
          else "Project aangemaakt vanuit de lead — vul de opname in.")
    return redirect(url_for("opname", tag=tag))


@app.route("/leads/<int:lid>/afspraak", methods=["POST"])
@login_required
def leads_afspraak(lid):
    """Afspraakdatum/-tijd op de lead + status 'afspraak gepland' + AUTOMATISCH project aanmaken."""
    rows = leads_mod.load_leads()
    lead = next((x for x in rows if x.get("id") == lid), None)
    if not lead:
        abort(404)
    wanneer = request.form.get("wanneer", "").strip()
    leads_mod.set_afspraak(lid, wanneer, rows)
    if wanneer:
        for r in rows:
            if r.get("id") == lid and r.get("status") in ("nieuw", "mail gestuurd", "gebeld"):
                r["status"] = "afspraak gepland"
        leads_mod.save_leads(rows)
        tag, bestond = _project_uit_lead(lid, rows, status_door=False)
        flash("Afspraak opgeslagen%s — verstuur nu de bevestigingsmail (✉ bevestiging)."
              % ("" if bestond else " + project %s aangemaakt" % tag))
    else:
        flash("Afspraak leeggemaakt.")
    return redirect(url_for("leads_pagina"))


@app.route("/leads/ontvangst")
@login_required
def leads_ontvangst():
    """Bulk-ontvangstbevestiging: BCC-lijst van alle 'nieuw'-leads + concepttekst (drukte/wachtlijst)."""
    rows = [r for r in leads_mod.load_leads() if r.get("status") == "nieuw" and r.get("email")]
    onderwerp, tekst = leads_mod.ontvangst_mail(_cfg().get("adviseur", {}))
    bcc = "; ".join(r["email"] for r in rows)
    return page(LEADS_ONTVANGST, n=len(rows), bcc=bcc, onderwerp=onderwerp, tekst=tekst)


@app.route("/leads/ontvangst/verstuurd", methods=["POST"])
@login_required
def leads_ontvangst_verstuurd():
    rows = leads_mod.load_leads()
    n = 0
    for r in rows:
        if r.get("status") == "nieuw":
            r["status"] = "mail gestuurd"; n += 1
    leads_mod.save_leads(rows)
    flash("%d lead(s) gemarkeerd als 'mail gestuurd'." % n)
    return redirect(url_for("leads_pagina"))


@app.route("/leads/<int:lid>/mail")
@login_required
def leads_mail(lid):
    r = next((x for x in leads_mod.load_leads() if x.get("id") == lid), None)
    if not r:
        abort(404)
    if request.args.get("soort") == "bevestiging":
        onderwerp, tekst = leads_mod.bevestiging_mail(r, _cfg().get("adviseur", {}))
    else:
        onderwerp, tekst = leads_mod.concept_mail(r, _cfg().get("adviseur", {}))
    return page(LEAD_MAIL, l=r, onderwerp=onderwerp, tekst=tekst)


@app.route("/leads/export.csv")
@login_required
def leads_csv():
    csv = leads_mod.to_csv(leads_mod.load_leads())
    return Response(csv, mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=nijbegun_leads.csv"})


if __name__ == "__main__":
    prod = bool(os.environ.get("NIJBEGUN_PROD")) or "--serve" in sys.argv
    if prod:
        dash = _dash_cfg()
        if not dash.get("pw_hash") or not dash.get("totp_secret"):
            print("GEWEIGERD: productie-modus vereist pw_hash + totp_secret (MFA, M29-eis punt 27).")
            print("Draai eerst:  python dashboard/security.py --setup")
            sys.exit(1)
        from waitress import serve
        print("Nij Begun isolatieplan-webapp (PRODUCTIE, waitress) -> poort 8000; zet HTTPS via Caddy ervoor.")
        serve(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), threads=8)
    else:
        print("Nij Begun isolatieplan-webapp -> http://127.0.0.1:5000  (Ctrl+C om te stoppen)")
        if _password() == DEFAULT_PW:
            print("  LET OP: default-wachtwoord 'nijbegun' actief. Stel er een in via config.json.")
        app.run(host="127.0.0.1", port=5000, debug=False)
