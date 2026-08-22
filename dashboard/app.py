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
import os, sys, json, glob, io, zipfile, datetime, functools, secrets, copy, re, math, threading, shutil, contextlib
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
from dashboard import mailbox as mailbox_mod                                          # noqa: E402
from dashboard import graph_mail as graph_mod                                         # noqa: E402
from dashboard import security as sec                                                 # noqa: E402
from dashboard import ai as ai_mod                                                    # noqa: E402
from dashboard import knowledge as knowledge_mod                                      # noqa: E402
from dashboard import bouwjaar as bouwjaar_mod                                        # noqa: E402
from dashboard import plattegrond_import as pi_mod                                   # noqa: E402
from engine.advies_text import genereer_advies                                        # noqa: E402
from engine.standaard import verliesoppervlak, standaard_eis                          # noqa: E402
from ventilatie.ventilatie import (bereken as vent_bereken, rapport as vent_rapport,  # noqa: E402
                                   verdeel_balans as vent_verdeel_balans,
                                   toets_vuistregels as vent_toets_vuistregels)
from ventilatie.ventilatieplan_svg import ventilatieplan_svg                          # noqa: E402
from dashboard.gebouw_svg import gebouw_svg                                            # noqa: E402
from dashboard import ventilatieplan as vp_mod                                         # noqa: E402
from dashboard import ventilatieplan_export as vp_export                              # noqa: E402
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
        # migratie: vabi_acties was een lijst STRINGS, is nu [{tekst, prio}] (prioriteit vs controle).
        # Oude projecten zonder herimport blijven zo gewoon werken.
        acts = st.get("vabi_acties")
        if acts and isinstance(acts[0], str):
            st["vabi_acties"] = [{"tekst": a, "prio": _is_prio_actie(a)} for a in acts]
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
        # Fail-closed: alleen een groen/rood oordeel wanneer het dossier zelf vastlegt dat kwh_m2_huidig
        # de echte NettoWarmtebehoefte was. Legacy dossiers (indicator_type_huidig == "") of dossiers
        # die op de fallback-indicator rusten geven "niet te bepalen" (None), nooit een gegokt oordeel.
        is_nwb = b.indicator_type_huidig == "NettoWarmtebehoefte"
        v = (eb is not None and std and eb <= std) if is_nwb else None
        return {"label": b.label_huidig or "—", "behoefte": eb, "standaard": std,
                "behoefte_label": "netto warmtebehoefte" if is_nwb else "warmtebehoefte",
                "indicator_type": b.indicator_type_huidig,
                "voldoet": v, "marge": (round(std - eb, 1) if (is_nwb and eb is not None and std) else None)}
    r = res_or_dos
    eb = r.get("_toetswaarde")   # netto warmtebehoefte (schil); fallback: IndicatorEnergiebehoefte
    std = float(r["Standaard"]) if r.get("Standaard") else None
    behoefte_label = "energiebehoefte" if "fallback" in (r.get("_toetswaarde_bron") or "") else "netto warmtebehoefte"
    return {"label": r.get("Labelklasse", "—"), "behoefte": eb, "standaard": std,
            "behoefte_label": behoefte_label,
            "indicator_type": r.get("_indicator_type"),
            # geen bool()! een expliciete None ("niet te bepalen") mag niet stilzwijgend rood worden.
            "voldoet": r.get("_voldoet_aan_standaard"), "marge": r.get("_marge_kwh_m2")}


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
        # De goedgekeurde voorbeeldplannen hebben BIJLAGE 1 t/m 7; ons officiële template (23-04-2026)
        # bevat er 3. Bijlage 4-7 lever je nu als losse bestanden mee -> voeg ze samen tot één plan.
        (False, "Bijlagen 4–7 samenvoegen tot één document vóór indienen: 4 Informatie over dit "
                "isolatieplan · 5 Voorgestelde maatregelen in beeld (schets + koudebruggen) · "
                "6 Ventilatieplan · 7 Detailtekeningen. Zie docs/deepdive-handige-docs-27-7.md"),
    ]
    return out


# ---------------- HTML ----------------
BASE = """<!doctype html><html lang=nl><head><meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Nij Begun · isolatieplan</title>
<link rel="stylesheet" href="{{url_for('static', filename='app.css')}}">
<link rel="icon" type="image/svg+xml" href="{{url_for('static', filename='mark.svg')}}">
<link rel="icon" type="image/png" sizes="32x32" href="{{url_for('static', filename='favicon-32.png')}}">
<link rel="apple-touch-icon" href="{{url_for('static', filename='apple-touch-icon.png')}}">
<link rel="manifest" href="{{url_for('manifest')}}">
<meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#000000" media="(prefers-color-scheme: dark)">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Nij Begun">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
</head><body>
<div class=topbar><a class=brand href="{{url_for('home') if session.ingelogd else url_for('login')}}"><img class=brand-mark src="{{url_for('static', filename='mark.svg')}}" alt="" width=24 height=24>Nij Begun<span class=brand-sub> · isolatieplan</span></a>
<nav>{% if session.ingelogd %}<a href="{{url_for('leads_pagina')}}">Leads</a><a href="{{url_for('home')}}">Projecten</a><a href="{{url_for('voorschot_pagina')}}">Voorschot</a><a href="{{url_for('knowledge_page')}}">Kennisbank</a><a href="{{url_for('guide')}}">Guide</a>
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


LOGIN = """<div class=login>
<img class=login-logo src="{{url_for('static', filename='logo.svg')}}" alt="Poortinga Energieadvies" width=270 height=63>
<div class=card>
<h1>Inloggen</h1><p class=lead>Je persoonlijke isolatieplan-werkplek.</p>
<form method=post>
{% if vraag_email %}<label>E-mailadres</label>
<input type=email name=email autocomplete=username inputmode=email autocapitalize=off autocorrect=off spellcheck=false autofocus placeholder="naam@bedrijf.nl">{% endif %}
<label>Wachtwoord</label>
<input type=password name=wachtwoord autocomplete=current-password {{'' if vraag_email else 'autofocus'}}>
{% if mfa %}<label>Code uit je authenticator-app (MFA)</label><input name=code inputmode=numeric autocomplete=one-time-code placeholder="123 456">{% endif %}
<div class=btn-row><button class="btn lg">Inloggen</button></div></form></div>
<p class="login-voet muted small">Nij Begun · isolatieplan — werkomgeving van Poortinga Energieadvies</p></div>"""

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
{% if projects %}<div class=card><h2>Lopende projecten</h2><div class="table-wrap card-table"><table>
<tr><th>Adres</th><th>Stap</th><th>Standaard</th><th>Maatregelen</th><th>Actie</th></tr>
{% for p in projects %}<tr><td data-label="Adres"><b>{{p.adres}}</b></td>
<td data-label="Stap"><span class="pill gray">{{p.stap}}</span></td>
<td data-label="Standaard">{% if p.voldoet is none %}<span class=muted>—</span>{% elif p.voldoet %}<span class="pill green">voldoet</span>{% else %}<span class="pill amber">nog niet</span>{% endif %}</td>
<td data-label="Maatregelen">{{p.n}}{% if p.totaal %} · &euro;{{'%.0f'|format(p.totaal)}}{% endif %}</td>
<td data-label="Actie" style="white-space:nowrap"><a class="btn sec" href="{{url_for('project', tag=p.tag)}}">openen →</a>
<form method=post action="{{url_for('project_verwijder', tag=p.tag)}}" style="display:inline"
  onsubmit="return confirm('Project {{p.adres}} DEFINITIEF verwijderen? Alle bestanden (dossier, VABI-export, isolatieplan, foto\'s) gaan weg. Dit kan niet ongedaan worden gemaakt.')">
<button class="btn sec" title="Project definitief verwijderen">🗑</button></form></td></tr>{% endfor %}</table></div>
<p class="muted small">Verwijderen wist de hele projectmap uit out/projects/. Wil je de bestanden bewaren, exporteer dan eerst de projectmap-zip (op de afrond-pagina).</p></div>
{% endif %}"""

HUIDIG = """{{stepper|safe}}<h1>Huidige staat — nulmeting</h1>
<p class=lead>Je hebt de opname in Vabi ingelezen en doorgerekend. <b>Exporteer de woning uit Vabi</b> en laad die
hier terug — de webapp leest het huidige energielabel en of de woning de Standaard al haalt.</p>
{% if h and h.behoefte is not none %}
<div class="verdict {{ 'ok' if h.voldoet else 'no' }}"><span class=ico>{{ '✅' if h.voldoet else ('❓' if h.voldoet is none else '🎯') }}</span>
<div><b>Huidige staat — label {{h.label}}</b><br>
<span class=muted>{{h.behoefte_label}} {{h.behoefte}} vs Standaard {{h.standaard if h.standaard is not none else '—'}} kWh/m²·jr
{% if h.voldoet %}→ voldoet al{% elif h.voldoet is none %}→ niet te bepalen (geen NettoWarmtebehoefte vastgelegd — herbereken in Vabi){% elif h.marge is not none %}→ {{h.marge}} kWh/m²·jr te overbruggen met maatregelen{% endif %}</span></div></div>
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
# Canonieke begrenzingen — MOET gelijk blijven aan _BEGR_CANON in magicplan/statistics_csv.py.
# Staat een waarde niet in deze lijst, dan toont het <select> de eerste optie en overschrijft het
# opslaan de echte waarde stil (aannames-audit 30-7).
BEGR_OPTS = ["Buitenlucht", "Grond", "Kruipruimte", "AOR", "AOS", "AVR", "Sterk geventileerd",
             "Onverwarmde kelder", "Water"]
ORI_OPTS = ["", "N", "NO", "O", "ZO", "Z", "ZW", "W", "NW"]
GLAS_OPTS = ["", "Enkel", "Voorzetglas", "Dubbel", "HR (dubbel glas met coating)", "HR+", "HR++",
             "TripleHR", "Vacuümglas", "Onbekend"]
KOZ_OPTS = ["", "Hout of kunststof", "Metaal (thermisch onderbroken)", "Metaal (niet thermisch onderbroken)"]
# Zelfde klasse-grenzen als dashboard/bouwjaar.py:ERAS; fraseringen ('Tot'/'Van .. t/m'/'Vanaf') zijn
# wat vabi/constructie_generate.py:_jaar_uit_klassetekst() al herkent (afkomstig uit het MagicPlan-form).
BOUWJAARKLASSE_OPTS = ["", "Tot 1946", "Van 1946 t/m 1964", "Van 1965 t/m 1974", "Van 1975 t/m 1982",
                       "Van 1983 t/m 1991", "Van 1992 t/m 2005", "Vanaf 2006"]
RC_BRON_OPTS = ["", "Opgemeten dikte", "Dikte onbekend", "Kwaliteitsverklaring",
               "Forfaitair (bouwjaar/renovatiejaar)"]
TYPE_ICO = {"dak": "⛰", "gevel": "🧱", "vloer": "▬", "kozijn": "🪟", "paneel": "⬜"}

OPNAME_TMPL = """{{stepper|safe}}<h1>Opname — {{st.adres}}</h1>
<p class=lead>Alle opnamegegevens, bewerkbaar. Laad je MagicPlan-opname in of vul handmatig aan — <b>Vabi blijft de rekenkern</b>.</p>
<div class=card><h2>① MagicPlan-opname inladen — pakket controleren</h2>
<p class=muted>Upload één pakket met projectidentiteit, Statistics, rapport en geometrie. Er verandert niets voordat je de preview bevestigt.</p>
<form method=post action="{{url_for('opname_intake_preview', tag=tag)}}" enctype=multipart/form-data>
<div class=file-drop>MagicPlan-importpakket (.zip)<br><input type=file name=pakket accept=".zip" required></div>
<div class=btn-row><button class=btn>Preview en verschillen tonen</button></div></form>
<details class=acc><summary>Losse legacy-import</summary><div class=acc-body>
<p class=muted>Alleen voor bestaande exports zonder importpakket. Deze route heeft geen pakketbrede identiteitscontrole.</p>
<form method=post action="{{url_for('opname_magicplan', tag=tag)}}" enctype=multipart/form-data>
<div class=file-drop>Sleep hier de MagicPlan-CSV of dossier (.csv / .json)<br><input type=file name=bestand accept=".csv,.json"></div>
<div class=btn-row><button class=btn>Inladen in de opname</button>
<span class="muted small">Loop de gegevens daarna volledig na.</span></div></form></div></details></div>
<div class=card><h2>Geen MagicPlan-opname?</h2><p class=muted>Lees één of meer bestaande
plattegrondafbeeldingen uit met verplichte adviseurscontrole.</p>
<a class="btn sec" href="{{url_for('plattegrond_import_pagina', tag=tag)}}">Plattegronden uploaden en controleren</a></div>
{% if st.import_historie %}<div class=card><h2>🕓 Import-historie</h2>
<p class="muted small">Elke MagicPlan-import met datum/tijd — zo zie je (ook vanaf een ander device) of dit de meest recente opname is.</p>
<div class=table-wrap><table><thead><tr><th>Wanneer</th><th>Bestand</th><th>Vlakken</th></tr></thead><tbody>
{% for h in st.import_historie|reverse %}<tr><td>{{h.tijd}}{% if loop.first %} <span class="pill green">meest recent</span>{% endif %}</td><td data-label="Bestand">{{h.bestand}}</td><td data-label="Vlakken">{{h.vlakken}}</td></tr>{% endfor %}
</tbody></table></div></div>{% endif %}
{% if st.vabi_acties %}<div class=card style="border:2px solid var(--warn-line);background:var(--warn-bg)">
<h2>📋 Zelf doen in Vabi — {{st.vabi_acties|length}} punt(en)</h2>
{% set prio = st.vabi_acties|selectattr('prio')|list %}{% set ctrl = st.vabi_acties|rejectattr('prio')|list %}
{% if prio %}<h3 style="margin:6px 0 4px">🔴 Actie vereist ({{prio|length}}) — hier gaat de berekening fout zonder ingrijpen</h3>
<ul class=check>{% for a in prio %}<li><span class="mk no2">→</span>{{a.tekst}}</li>{% endfor %}</ul>{% endif %}
{% if ctrl %}<details{% if not prio %} open{% endif %}><summary><b>🔍 Ter controle ({{ctrl|length}})</b> — nalopen, meestal akkoord</summary>
<ul class=check>{% for a in ctrl %}<li><span class="mk">✓</span>{{a.tekst}}</li>{% endfor %}</ul></details>{% endif %}
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
{% if gebouw_svg %}<div class=svgbox>{{gebouw_svg|safe}}</div>{% endif %}
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
<div><label>Bouwjaarklasse (dit vlak, leeg = projectbouwjaar)</label><select name=bouwjaarklasse>{% for bj in bouwjaarklasse_opts %}<option {{'selected' if bj==s.bouwjaarklasse}}>{{bj}}</option>{% endfor %}</select></div>
<div><label>Rc-bron</label><select name=rc_bron>{% for r in rc_bron_opts %}<option {{'selected' if r==s.rc_bron}}>{{r}}</option>{% endfor %}</select></div>
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

<div class=card id=dak-toevoegen><h2>⛰ Dak toevoegen</h2>
<p class=muted>Voeg zoveel daken toe als nodig (tot 20) — elk dak wordt automatisch genummerd. Kies per dak de invoerwijze. De toegevoegde dakvlakken verschijnen in de gebouwboom hierboven.</p>
<details class=acc><summary><b>1 · Plat dak</b></summary><div class=acc-body>
<div class=dakwire><svg id="platSvg" class=isometrie-canvas viewBox="0 0 320 220" role=img aria-label="Isometrische voorbeeldtekening van het platte dak"></svg></div>
<form method=post action="{{url_for('opname_dak_plat', tag=tag)}}" oninput="platDakPrev(this)"><div class=grid2>
<div><label>Breedte (m)</label><input name=breedte placeholder="bv. 5" required></div>
<div><label>Diepte (m)</label><input name=diepte placeholder="bv. 4.9" required></div>
<div><label>Rekenzone</label><select name=rekenzone>{% for z in (1,2,3) %}<option>{{z}}</option>{% endfor %}</select></div>
</div><div class=btn-row><button class=btn>+ Plat dak toevoegen</button></div></form></div></details>

<details class=acc><summary><b>2 · Zadeldak — via driehoek berekenen</b></summary><div class=acc-body>
<p class="muted small">De <b>hellende vlakken</b> zitten aan de gekozen oriëntatie én de tegenoverliggende. De <b>lange zijde (basis c)</b> is de breedte van de kopgevel (de zijde waarover het dak schuin loopt); de <b>breedte/noklengte</b> is de lengte waarmee elk hellend vlak vermenigvuldigd wordt. De <b>kopgevels</b> (driehoeken) tellen alleen mee als ze aan buiten grenzen (bij een tussenwoning meestal buurwand → uit laten).</p>
<div class=dakwire><svg id="zadelSvg" class=isometrie-canvas viewBox="0 0 320 220" role=img aria-label="Isometrische voorbeeldtekening van het zadeldak"></svg></div>
<form method=post action="{{url_for('opname_dak_driehoek', tag=tag)}}" oninput="dakPrev(this)"><div class=grid2>
<div><label>Oriëntatie hellende vlakken</label><select name=orient_hellend>{% for o in ori_opts %}{% if o %}<option>{{o}}</option>{% endif %}{% endfor %}</select></div>
<div><label>Hellingshoek (°)</label><input name=helling1 value="45"></div>
<div><label>Lange zijde / basis c (m)</label><input name=lange_zijde placeholder="bv. 7"></div>
<div><label>Breedte / noklengte (m)</label><input name=breedte placeholder="bv. 5"></div>
<div><label>Hellingshoek vlak 2 (° — leeg = zelfde)</label><input name=helling2 placeholder="alleen bij asymmetrisch"></div>
<div><label>Rekenzone</label><select name=rekenzone>{% for z in (1,2,3) %}<option>{{z}}</option>{% endfor %}</select></div>
<div><label class=chk><input type=checkbox name=kopgevel1_buiten> Kopgevel 1 grenst aan buiten</label></div>
<div><label class=chk><input type=checkbox name=kopgevel2_buiten> Kopgevel 2 grenst aan buiten</label></div>
</div>
<p class="muted small" id=dakprev>Vul lange zijde, breedte en hellingshoek in voor een voorbeeld.</p>
<div class=btn-row><button class=btn>+ Zadeldak toevoegen</button></div></form></div></details>

<details class=acc><summary><b>3 · Zelf de m² invoeren (9 geometrieën)</b></summary><div class=acc-body>
<p class="muted small">Voor een lastig dak: vul per oriëntatie het (schuine) dakoppervlak in. Laat leeg wat er niet is.</p>
<div class=dakwire><svg id="compasSvg" viewBox="0 0 300 300" width="260" height="260">
<circle cx="150" cy="150" r="36" fill="var(--tint)" stroke="var(--sub)" stroke-width="1.5"/>
<text id="compasHorizVal" x="150" y="155" font-size="var(--svg-fs-3)" text-anchor="middle" fill="var(--sub)">plat —</text>
{% for o in ['N','NO','O','ZO','Z','ZW','W','NW'] %}
<g id="compasSeg{{o}}" transform="rotate({{loop.index0 * 45}} 150 150)">
<path d="M150 150 L150 40 A110 110 0 0 1 {{(150+110*0.3826834324)|round(1)}} {{(150-110*0.9238795325)|round(1)}} Z" fill="var(--tint)" stroke="var(--card)" stroke-width="2"/>
<text x="150" y="66" font-size="var(--svg-fs-2)" font-weight="650" text-anchor="middle" fill="var(--ink)" transform="rotate({{-(loop.index0 * 45)}} 150 66)">{{o}}</text>
<text id="compasVal{{o}}" x="150" y="82" font-size="var(--svg-fs-1)" text-anchor="middle" fill="var(--sub)" transform="rotate({{-(loop.index0 * 45)}} 150 82)">—</text>
</g>
{% endfor %}
</svg></div>
<form method=post action="{{url_for('opname_dak_negen', tag=tag)}}" oninput="compasPrev(this)"><div class=grid2>
{% for o in ['N','NO','O','ZO','Z','ZW','W','NW','Horizontaal'] %}<div><label>{{o}} (m²)</label><input name="m2_{{o}}"></div>{% endfor %}
<div><label>Hellingshoek schuine vlakken (° — optioneel)</label><input name=helling9></div>
<div><label>Rekenzone</label><select name=rekenzone>{% for z in (1,2,3) %}<option>{{z}}</option>{% endfor %}</select></div>
</div><div class=btn-row><button class=btn>+ Dak toevoegen</button></div></form></div></details>

<details class=acc><summary><b>4 · Dakraam toevoegen{% if n_dakraam %} <span class="pill gray">{{n_dakraam}} nu</span>{% endif %}</b></summary><div class=acc-body>
{% if dak_vlakken %}<p class="muted small">Voeg een dakraam toe aan een bestaand dakvlak (zelfde logica als een raam in een gevel). Het dakraam komt als deelvlak op dát dakvlak in Vabi; het glas wordt van het dakvlak afgetrokken. Herhaal voor meer dakramen.</p>
<form method=post action="{{url_for('opname_dakraam', tag=tag)}}"><div class=grid2>
<div><label>In dakvlak</label><select name=dak_orient>{% for lbl, ov in dak_vlakken %}<option value="{{ov}}">{{lbl}}</option>{% endfor %}</select></div>
<div><label>Type glas</label><select name=glas>{% for g in glas_opts %}{% if g %}<option>{{g}}</option>{% endif %}{% endfor %}</select></div>
<div><label>Breedte (m)</label><input name=breedte placeholder="bv. 0.8"></div>
<div><label>Hoogte (m)</label><input name=hoogte placeholder="bv. 1.2"></div>
<div><label>of direct oppervlak (m²)</label><input name=m2 placeholder="leeg = breedte x hoogte"></div>
<div><label>Toevoerrooster</label><select name=rooster><option value="">Geen</option><option>Zelfregelend (ZR)</option><option>Niet-zelfregelend</option><option>Onbekend</option></select></div>
<div><label>Zonwering/luik</label><select name=zonwering><option value="">Geen</option><option>Rolluik of luik (bedienbaar)</option><option>Buitenzonwering</option><option>Binnenzonwering</option></select></div>
</div><div class=btn-row><button class=btn>+ Dakraam toevoegen</button></div></form>
{% else %}<p class=muted>Voeg eerst een dakvlak toe (optie 1/2/3 hierboven), dan kun je er dakramen aan hangen.</p>{% endif %}
</div></details>

<details class=acc><summary><b>5 · Dakkapel toevoegen{% if n_dakkapel %} <span class="pill gray">{{n_dakkapel}} nu</span>{% endif %}</b></summary><div class=acc-body>
{% if dakkapel_moeder_opts %}<p class="muted small">ISSO 82.1 §8.2.1: een dakkapel voegt een <b>voorvlak</b> (gevel) + <b>2 wangen</b> (gevel) + een <b>plat dakje</b> toe, en maakt een <b>gat</b> in het schuine moederdakvlak — dat gat wordt automatisch van het gekozen dakvlak afgetrokken (past het niet, dan wordt de dakkapel geweigerd — controleer dan het moederdak/de maten). Alleen <b>hellende</b> dakvlakken zijn kiesbaar (een dakkapel breekt door een schuin vlak heen; een plat dak of het dakje van een andere dakkapel niet).</p>
<div class=dakwire><svg id="kapelSvg" class=isometrie-canvas viewBox="0 0 320 220" role=img aria-label="Isometrische voorbeeldtekening van de dakkapel"></svg></div>
<p class="muted small" id=kapelprev aria-live=polite>Vul breedte, hoogte en diepte in.</p>
<form method=post action="{{url_for('opname_dakkapel', tag=tag)}}" oninput="kapelPrev(this)"><div class=grid2>
<div><label>In dakvlak (moederdak)</label><select name=moederdak_i>{% for lbl, di in dakkapel_moeder_opts %}<option value="{{di}}" data-helling="{{d.schil[di].hellingshoek or 0}}">{{lbl}}</option>{% endfor %}</select></div>
<div><label>Breedte voorvlak (m)</label><input name=breedte placeholder="bv. 2.5"></div>
<div><label>Hoogte voorvlak (m)</label><input name=hoogte placeholder="bv. 1.5"></div>
<div><label>Diepte (m)</label><input name=diepte placeholder="bv. 1.0"></div>
<div><label>Rekenzone</label><select name=rekenzone>{% for z in (1,2,3) %}<option>{{z}}</option>{% endfor %}</select></div>
<div><label class=chk><input type=checkbox name=wangen_geisoleerd checked> Wangen geïsoleerd</label></div>
</div><div class=btn-row><button class=btn>+ Dakkapel toevoegen</button></div></form>
{% else %}<p class=muted>Voeg eerst een hellend dakvlak toe (optie 2 of 3 hierboven, met een hellingshoek &gt; 0°), dan kun je er een dakkapel in zetten.</p>{% endif %}
</div></details>
<script src="{{url_for('static', filename='isometrie.js')}}"></script>
<script>
function compasPrev(f){
  var os=['N','NO','O','ZO','Z','ZW','W','NW'];
  os.forEach(function(o){
    var inp=f['m2_'+o],val=inp?parseFloat((inp.value||'').replace(',','.')):NaN,
        seg=document.getElementById('compasSeg'+o),lbl=document.getElementById('compasVal'+o);
    if(!lbl)return;
    if(val>0){lbl.textContent=val.toFixed(1)+' m²';seg.querySelector('path').setAttribute('fill','var(--info-bg)');}
    else{lbl.textContent='—';seg.querySelector('path').setAttribute('fill','var(--tint)');}
  });
  var hz=f['m2_Horizontaal'],hv=hz?parseFloat((hz.value||'').replace(',','.')):NaN,ht=document.getElementById('compasHorizVal');
  if(ht)ht.textContent='plat '+(hv>0?hv.toFixed(1)+' m²':'—');
}
</script></div>

<div class=card><h2>Ventilatie</h2>
<p class=muted>Nij Begun rekent met vuistregels: toevoer 0,7 dm³/s·m² per verblijfsgebied (min 7 l/s), afvoer keuken 21 / bad 14 / toilet 7, in balans. Ventilatie is een <b>verplicht</b> onderdeel van het isolatieplan.</p>
{% if d.geometrie.ruimtes %}<a class="btn sec" href="{{url_for('ventilatieplan_pagina', tag=tag)}}">📐 Ventilatieplan tekenen</a>{% endif %}
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
<dt>Totaal verliesoppervlak (Als)</dt><dd>{{'%.2f'|format(verlies)}} m²</dd>
<dt>Gebruiksoppervlak (Ag)</dt><dd>{{'%.2f'|format(ag) if ag else '—'}} m²</dd>
<dt>Compactheid (Als/Ag)</dt><dd>{{'%.2f'|format(verlies/ag) if ag else '—'}}</dd>
<dt>Standaard-eis (verwachting)</dt><dd>{{std_eigen ~ ' kWh/m²·jr' if std_eigen is not none else '— (bouwjaar/Ag nodig)'}}</dd></div>
<p class="muted small">Weging NTA 8800 §6.7.3: grond/kruipruimte ×0,7, AVR/woningscheidend ×0 (adiabatisch), overige ×1.
De Standaard-eis is <b>zelf voorgerekend</b> (§5.3.2) als 0-meting-verwachting; Vabi geeft de definitieve waarde.</p></div>

<div class=card><h2>③ Exporteer naar Vabi</h2>
<p class=muted>Genereer de VABI-import (3 bibliotheken) van de <b>huidige</b> woning, importeer die in EPA-W en reken door.
Exporteer de woning daarna uit Vabi — die laad je in de volgende stap terug als nulmeting.</p>
<div class=btn-row><a class="btn sec" href="{{url_for('opname_vabi_huidig', tag=tag)}}">⬇ VABI-import (huidige staat)</a>
<div class=spacer></div><a class="btn lg" href="{{url_for('huidig', tag=tag)}}">Door naar huidige staat →</a></div></div>"""

MAATREGELEN = """{{stepper|safe}}<h1>Maatregelen kiezen</h1>
<p class=lead>Vink aan wat je toepast. De goedkoopste passende maatregel is voorgeselecteerd; je kunt per bouwdeel wisselen.</p>
{% if gedoog %}<div class=warn style="border:2px solid var(--warn-line)"><b>🦇 Gedoogbeleid vleermuizen / eDNA (per 1-7-2026):</b>
{% for g in gedoog %}<div style="margin-top:6px">{{g}}</div>{% endfor %}
<div class="muted small" style="margin-top:6px">Zoek de codes op via “Zelf kiezen uit de catalogus” hieronder (hoofdcategorie 1 Gevel).</div></div>{% endif %}
<div class=hint><b>Nij Begun-regel:</b> maatregelen die nódig zijn voor de <b>Standaard</b> staan in de <b>subsidietabel</b> (50/100%).
Bouwfysisch wenselijke extra's (bv. dakkapel-wangen, deur) adviseer je wél, maar die vallen onder <b>30% ISDE</b> — zet die op “advies”.</div>
<form method=post id=mf>
{% for g in groepen %}
<div class="card meas-group" data-m2="{{g.m2}}">
<div class=grp-head>
<h2 style="margin:0">{{g.onderdeel}} <span class="pill blue">{{'%.1f'|format(g.m2)}} m²</span></h2>
<select name="bucket_{{loop.index0}}" class=bk>
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
{% if vrij %}<div class="table-wrap card-table"><table><tr><th>Code</th><th>Omschrijving</th><th>Hoeveelheid</th><th>Kosten</th><th>Bucket</th><th>Actie</th></tr>
{% for v in vrij %}<tr><td class=small data-label="Code">{{v.code}}</td><td data-label="Omschrijving">{{v.omschrijving[:58]}}</td>
<td data-label="Hoeveelheid">{{v.hoeveelheid}} {{v.eenheid}}</td><td data-label="Kosten">€{{'%.0f'|format(v.kosten)}}</td>
<td data-label="Bucket"><span class="pill {{'green' if v.bucket=='standaard' else 'amber'}}">{{'Standaard' if v.bucket=='standaard' else '30% ISDE'}}</span></td>
<td data-label="Actie"><form method=post action="{{url_for('maatregel_del', tag=tag, idx=loop.index0)}}"><button class="btn sec">✕ verwijderen</button></form></td></tr>{% endfor %}</table></div>
<p class="muted small">Subtotaal catalogus-keuze (Standaard-bucket): <b>€{{'%.0f'|format(vrij_tot)}}</b></p>{% endif %}
{% for c in boom %}<details class=acc><summary><b>{{c.naam}}</b> <span class="pill gray">{{c.code}}</span></summary><div class=acc-body>
{% for s in c.subs %}<details class=acc><summary>{{s.naam[:60]}} <span class="pill gray">{{s.code}}</span></summary><div class=acc-body>
{% for m in s.kern %}<form method=post action="{{url_for('maatregel_add', tag=tag)}}" class=add-row>
<input type=hidden name=code value="{{m.code}}"><span class="desc small">{{m.code}} · {{m.omschrijving[:64]}} — €{{'%.2f'|format(m.prijs)}}/{{m.eenheid}}{% if m.biobased %} <span class="pill green">bio</span>{% endif %}</span>
<input name=hoeveelheid placeholder="{{m.eenheid}}" style="max-width:90px"><select name=bucket style="max-width:130px"><option value=standaard>Standaard</option><option value=isde>30% ISDE</option></select>
<button class="btn sec">＋</button></form>{% endfor %}
{% if s.meerwerk %}<p class="muted small" style="margin:8px 0 2px"><b>Bijkomende kosten</b></p>
{% for m in s.meerwerk %}<form method=post action="{{url_for('maatregel_add', tag=tag)}}" class=add-row>
<input type=hidden name=code value="{{m.code}}"><span class="desc small">{{m.code}} · {{m.omschrijving[:64]}} — €{{'%.2f'|format(m.prijs)}}/{{m.eenheid}}</span>
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
<dt>Isolatiestandaard (eis, uit Vabi)</dt><dd>{{h.standaard if h.standaard is not none else '—'}} kWh/m²·jr{% if std_eigen is not none %} <span class="muted small">(zelf voorgerekend: {{std_eigen}}{% if std_afwijking is not none and std_afwijking > 2 %} — <b>afwijking {{std_afwijking}}, loop geometrie/woningtype na</b>{% endif %})</span>{% endif %}</dd>
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
{% if na %}<div class="verdict {{ 'ok' if na.voldoet else 'no' }}" style="margin-top:16px"><span class=ico>{{ '✅' if na.voldoet else ('❓' if na.voldoet is none else '⚠️') }}</span>
<div><b>{{ 'Voldoet aan de Standaard!' if na.voldoet else ('Niet te bepalen' if na.voldoet is none else 'Voldoet nog niet') }}</b><br>
<span class=muted>{{na.behoefte_label}} {{na.behoefte}} vs Standaard {{na.standaard}} kWh/m²·jr{% if na.marge is not none %} · marge {{na.marge}}{% endif %}{% if na.voldoet is none %} — geen NettoWarmtebehoefte vastgelegd in deze export, herbereken in Vabi{% endif %}</span></div></div>
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
<div class=card><h2>Projectmap voor OneDrive</h2>
<p class=muted>Je krijgt een <b>complete projectmap</b> als zip: pak 'm uit in OneDrive en alles staat
al gesorteerd (opname · VABI · isolatieplan · foto's), met lege mappen voor <b>correspondentie</b> en
<b>facturen</b> die je zelf vult. Een LEESMIJ legt de indeling en de bewaartermijn uit.</p>
<p class="muted small">Let op: een nieuwe export is een <b>verse</b> map — wat jij zelf hebt toegevoegd
zit er niet in. Voeg nieuwe bestanden dus toe aan je bestaande map in plaats van 'm te vervangen.</p>
<div class=btn-row><a class="btn sec" href="{{url_for('afronden', tag=tag)}}?regen=1">Opnieuw genereren</a><div class=spacer></div>
<a class="btn lg green" href="{{url_for('export', tag=tag)}}">⬇ Projectmap downloaden (.zip)</a></div></div>"""

GUIDE = """<h1>Guide — zo maak je een Nij Begun-isolatieplan</h1>
<p class=lead>De volledige werkwijze, met de eisen van de Nij Begun-kennisbank erin verwerkt.</p>
<div class=card><h2>Veldgidsen (open ze op je telefoon bij de opname)</h2><ul class=files>
<li>✉ De drie bewonersmails (ontvangst · kennismaking · afspraakbevestiging) <a class="btn sec" href="{{url_for('mails')}}">openen</a></li>
{% for slug, (titel, _b) in gidsen.items() %}<li>{{titel}} <a class="btn sec" href="{{url_for('gids', slug=slug)}}">openen</a></li>{% endfor %}
</ul></div>
<div class=card><h2>De flow in 6 stappen</h2>
<div class=stepper>{% for s,l in stappen %}<div class="step done"><div class=bar></div>{{l}}</div>{% endfor %}</div>
<dl class=kv><dt>1 · Opname</dt><dd>Start een <b>leeg project</b> (alleen adres) en laad in deze stap de <b>MagicPlan Statistics-CSV</b> in. Alle opnamegegevens worden <b>zichtbaar en bewerkbaar</b>: de gebouw-boom per rekenzone (dak/gevels/ramen/vloer met m², Rc/U, begrenzing), installaties en algemene gegevens. Onderaan exporteer je de woning naar <b>Vabi</b> (3 bibliotheken), reken je door in EPA-W en exporteer je 'm weer uit Vabi.</dd>
<dt>2 · Huidige staat</dt><dd>Laad de <b>VABI-export</b> van de huidige woning terug: de webapp leest het <b>label</b> en of de Standaard al gehaald wordt (de 0-meting).</dd>
<dt>3 · Maatregelen</dt><dd>Suggesties per bouwdeel (goedkoopste eerst) óf <b>zelf kiezen uit de volledige catalogus</b> incl. bijkomende kosten. Noteer per maatregel de <b>technische haalbaarheid</b>. Standaard → subsidietabel; extra's → 30% ISDE.</dd>
<dt>4 · VABI-toets</dt><dd>Genereer de toekomstige staat (met <b>renovatiejaar-variant</b> voor de Qv10), importeer in Vabi, reken, upload de export terug. <b>Voldoet de set aan de Standaard?</b> Zo niet → pakket uitbreiden.</dd>
<dt>5 · Afronden</dt><dd>Verplichte <b>foto's</b> (voorkant + huisnummer) + persoonlijke toelichting + isolatieplan (<b>PDF + JSON</b> leverformaat) + <b>visueel ventilatieplan</b> + haalbaarheids-bijlage + foto-checklist. De <b>indien-check</b> spiegelt het Beoordelingsformulier.</dd>
<dt>6 · Opleveren</dt><dd>Exporteer de bundel en upload het plan in <b>Teams</b> → je eigen kanaal → tabblad <b>Bestanden</b> (zo schrijft "Proces isolatieplannen" het voor; niet per mail). Vul vooraf het <b>Excel-overzicht</b> op je Teams-kanaal aan met postcode · huisnummer · datum woningopname · woningtype — pas dán wordt de officiële opdracht verstrekt. <b>KWACO</b> zet het plan daarna op <b>akkoord</b> (je krijgt een mail; download het plan zelf uit Teams en stuur het naar de bewoner) of op <b>retour adviseur</b> (aanpassen en opnieuw indienen).</dd></dl></div>
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
@app.route("/manifest.webmanifest")
def manifest():
    """PWA-manifest: op het iPad-beginscherm start de app dan zonder browserbalk (standalone),
    met het huisstijl-icoon. Geen login vereist — het bevat geen gegevens."""
    return app.response_class(json.dumps({
        "name": "Nij Begun · isolatieplan", "short_name": "Nij Begun",
        "description": "Werkomgeving voor Nij Begun-isolatieplannen (Poortinga Energieadvies)",
        "start_url": "/", "scope": "/", "display": "standalone",
        "background_color": "#0b3c49", "theme_color": "#0b3c49", "lang": "nl",
        "icons": [
            {"src": url_for("static", filename="icon-192.png"), "sizes": "192x192", "type": "image/png"},
            {"src": url_for("static", filename="icon-512.png"), "sizes": "512x512", "type": "image/png"},
            {"src": url_for("static", filename="icon-512.png"), "sizes": "512x512",
             "type": "image/png", "purpose": "maskable"},
        ],
        # DELEN VANAF DE TELEFOON: hiermee verschijnt 'Nij Begun' in het deelmenu van iOS/Android.
        # Je deelt de MagicPlan-CSV of een foto rechtstreeks naar de app — geen omweg via OneDrive.
        "share_target": {
            "action": "/deel", "method": "POST", "enctype": "multipart/form-data",
            "params": {"title": "title", "text": "text", "url": "url",
                       "files": [{"name": "bestand",
                                  "accept": ["text/csv", ".csv", "application/json", ".json",
                                             "image/*", "application/xml", "text/xml", ".xml"]}]},
        },
    }, ensure_ascii=False), mimetype="application/manifest+json")


DEEL_TMPL = """<h1>Gedeeld bestand</h1>
<p class=lead><b>{{naam}}</b> is vanaf je telefoon gedeeld met de app. Kies het project waar het bij hoort.</p>
{% if projecten %}<div class=card><h2>Kies het project</h2>
<form method=post action="{{url_for('deel_plaats')}}"><input type=hidden name=token value="{{token}}">
<div><label>Project</label><select name=tag>{% for t, a in projecten %}<option value="{{t}}">{{a or t}}</option>{% endfor %}</select></div>
<div style="margin-top:10px"><label>Wat is dit?</label><select name=soort>
<option value="opname">MagicPlan-opname (.csv) of dossier (.json) — inladen in de opname</option>
<option value="foto">Foto — bij de projectfoto's</option>
<option value="bijlage">Overige bijlage — bewaren bij het project</option>
</select></div>
<div class=btn-row style="margin-top:12px"><button class=btn>Plaatsen in het project</button></div></form></div>
{% else %}<div class=hint>Je hebt nog geen projecten. Maak er eerst één aan op de startpagina.</div>{% endif %}
<div class=btn-row><a class="btn sec" href="{{url_for('home')}}">← Naar de projecten</a></div>"""


@app.route("/deel", methods=["POST", "GET"])
@login_required
def deel():
    """PWA share target: ontvangt een bestand uit het deelmenu van iOS/Android en laat je kiezen
    bij welk project het hoort. Zo hoef je niet eerst in OneDrive op te slaan."""
    f = request.files.get("bestand")
    if not f or not f.filename:
        flash("Geen bestand ontvangen uit het deelmenu.")
        return redirect(url_for("home"))
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    token = secrets.token_hex(8)
    veilig = os.path.basename(f.filename).replace("/", "_").replace("\\", "_")
    f.save(os.path.join(UPLOAD_DIR, "deel_%s_%s" % (token, veilig)))
    projecten = []
    if os.path.isdir(PROJECTS_DIR):
        for tag in sorted(os.listdir(PROJECTS_DIR)):
            s = _load_state(tag)
            if s:
                projecten.append((tag, s.get("adres")))
    return page(DEEL_TMPL, naam=veilig, token=token, projecten=projecten)


@app.route("/deel/plaats", methods=["POST"])
@login_required
def deel_plaats():
    """Zet het gedeelde bestand in het gekozen project (opname / foto / bijlage)."""
    token, tag = request.form.get("token", ""), request.form.get("tag", "")
    soort = request.form.get("soort", "bijlage")
    st = _load_state(tag)
    if not st or not re.fullmatch(r"[0-9a-f]{16}", token or ""):
        abort(404)
    treffers = glob.glob(os.path.join(UPLOAD_DIR, "deel_%s_*" % token))
    if not treffers:
        flash("Het gedeelde bestand is niet meer gevonden — deel het opnieuw.")
        return redirect(url_for("home"))
    bron = treffers[0]
    naam = os.path.basename(bron).split("_", 2)[-1]
    ext = os.path.splitext(naam)[1].lower()
    if soort == "opname" and ext in (".csv", ".json"):
        doel = os.path.join(UPLOAD_DIR, "opname_%s%s" % (tag, ext))
        shutil.move(bron, doel)
        flash("'%s' staat klaar — kies in de Opname-stap 'Inladen' om 'm te verwerken." % naam)
        return redirect(url_for("opname", tag=tag))
    submap = "fotos" if soort == "foto" else "bijlagen"
    doelmap = os.path.join(_pdir(tag), submap)
    os.makedirs(doelmap, exist_ok=True)
    shutil.move(bron, os.path.join(doelmap, naam))
    flash("'%s' opgeslagen bij het project (%s)." % (naam, submap))
    return redirect(url_for("opname", tag=tag))


@app.route("/login", methods=["GET", "POST"])
def login():
    dash = _dash_cfg()
    # inloggen met e-mailadres + wachtwoord: 'dashboard.email' wint, anders het adviseur-adres uit
    # config.json. Geen adres geconfigureerd -> geen e-mailveld (lokale modus blijft werken).
    verwacht_email = (dash.get("email") or _cfg().get("adviseur", {}).get("email") or "").strip()
    if request.method == "POST":
        ok, fout = sec.login_check(dash, request.form.get("wachtwoord"), request.form.get("code"),
                                   request.remote_addr or "?", fallback_pw=_password(),
                                   email=request.form.get("email"), verwacht_email=verwacht_email)
        if ok:
            session["ingelogd"] = True
            return redirect(url_for("home"))
        flash(fout)
    return page(LOGIN, wrapclass="narrow", mfa=bool(dash.get("totp_secret")),
                vraag_email=bool(verwacht_email))


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


VOORSCHOT = """<h1>Voorschot-factuur — specificatie</h1>
<p class=lead>Specificatie op adresniveau voor een voorschot bij de Provincie Groningen (75% van het
adviestarief). Neem deze regels 1-op-1 over op je factuur; postcode/huisnummer moeten <b>gelijk</b> zijn
aan het isolatieplan.</p>
<div class=card><h2>Verplichte factuurgegevens</h2>
<div class=table-wrap><table><tr><td class=muted>Aan</td><td>{{spec.header.aan}}</td></tr>
<tr><td class=muted>T.a.v.</td><td>{{spec.header.tav}}</td></tr>
<tr><td class=muted>VPL-nummer</td><td><b>{{spec.header.vpl_nummer}}</b></td></tr>
<tr><td class=muted>Documentnr. opdracht</td><td><b>{{spec.header.documentnummer_opdracht}}</b></td></tr>
<tr><td class=muted>Kenmerk</td><td>{{spec.header.kenmerk}}</td></tr>
<tr><td class=muted>Indienen bij</td><td>{{spec.header.email}} (XML + kopie PDF)</td></tr></table></div></div>
<div class=card><div class=grp-head><h2>Specificatie ({{spec.regels|length}} plan(nen))</h2>
<a class="btn sec" href="{{url_for('voorschot_csv')}}">⬇ CSV</a></div>
<div class="table-wrap card-table"><table>
<tr><th>Postcode + huisnr</th><th>Woningtype</th><th>Advies</th><th>Tarief excl. btw</th></tr>
{% for r in spec.regels %}<tr><td data-label="Adres"><b>{{r.adres}}</b></td>
<td data-label="Woningtype">{{r.woningtype}}</td>
<td data-label="Advies">{{'Uitgebreid' if r.uitgebreid else 'Basis'}}</td>
<td data-label="Tarief">&euro;{{'%.2f'|format(r.tarief_excl)}}</td></tr>{% endfor %}</table></div>
<div class=table-wrap style="margin-top:14px;max-width:420px"><table>
<tr><td>Subtotaal (excl. btw)</td><td style="text-align:right">&euro;{{'%.2f'|format(spec.subtotaal_excl)}}</td></tr>
<tr><td><b>Voorschot 75% (excl. btw)</b></td><td style="text-align:right"><b>&euro;{{'%.2f'|format(spec.voorschot_excl)}}</b></td></tr>
<tr><td>21% btw</td><td style="text-align:right">&euro;{{'%.2f'|format(spec.btw)}}</td></tr>
<tr><td><b>Totaal (incl. btw)</b></td><td style="text-align:right"><b>&euro;{{'%.2f'|format(spec.totaal_incl)}}</b></td></tr></table></div></div>
{% if spec.onbekend %}<div class=warn><b>Woningtype niet herkend — zelf tarief bepalen ({{spec.onbekend|length}}):</b>
{% for o in spec.onbekend %}<div>{{o.adres}} — {{o.woningtype or '(leeg)'}}</div>{% endfor %}</div>{% endif %}
<p class="muted small">Tarieven excl. btw uit de opdrachtbrief 2026: Vrijstaand &gt;300 m² €750/€825 · Vrijstaand
&lt;300 m² €625/€700 · 2-onder-1-kap/hoek €500/€575 · tussen €350/€425 · meergezins €325/€400 ·
repeterend €250/€325 (Basis/Uitgebreid). Advies volgt uit het type advies in de opname.</p>"""


# Woorden die een actiepunt tot ECHTE ACTIE maken: zonder ingrijpen rekent Vabi met verkeerde of
# ontbrekende invoer. De rest is 'ter controle' (de tool heeft een keuze gemaakt, jij bevestigt 'm).
_PRIO_WOORDEN = ("fout", "ontbreekt", "onvolledig", "handmatig narekenen", "niet meegeteld",
                 "let op wand", "tikfout", "dubbeltel", "onmogelijke hoek", "zelf toevoegen",
                 "kwaliteitsverklaring", "multi-zone", "meerdere rekenzones", "vul ", "corrigeer",
                 "verplicht", "gebouwhoogte", "weigert")


def _is_prio_actie(tekst):
    """True = 'actie vereist' (rode lijst), False = 'ter controle' (inklapbaar)."""
    t = (tekst or "").lower()
    return any(w in t for w in _PRIO_WOORDEN)


def _voorschot_plannen():
    """Alle projecten -> plan-dicts voor de voorschot-specificatie (postcode/huisnr/woningtype/Ag/advies)."""
    plannen = []
    if os.path.isdir(PROJECTS_DIR):
        for tag in sorted(os.listdir(PROJECTS_DIR)):
            dos = _dossier(tag)
            if not dos:
                continue
            idc = getattr(dos, "identificatie", None)
            # B/U-tarief volgt uit het BOUWJAAR (vóór 1945 = Uitgebreid), NIET uit het opnametype /
            # de kwalificatie van de adviseur — zie Startpakket Isolatieadviseur maart 2026.
            from dashboard.voorschot import uitgebreid_uit_bouwjaar
            _uit = uitgebreid_uit_bouwjaar(getattr(idc, "bouwjaar", None))
            plannen.append({
                "tag": tag,
                "postcode": getattr(idc, "postcode", "") or "",
                "huisnummer": getattr(idc, "huisnummer", "") or "",
                "woningtype": getattr(idc, "woningtype", "") or "",
                "ag_m2": getattr(getattr(dos, "geometrie", None), "gebruiksoppervlakte_ag_m2", 0) or 0,
                "uitgebreid": bool(_uit),
                "bouwjaar_onbekend": _uit is None,   # -> als B gefactureerd; controleer het bouwjaar
            })
    return plannen


@app.route("/voorschot")
@login_required
def voorschot_pagina():
    from dashboard.voorschot import build_specificatie
    return page(VOORSCHOT, spec=build_specificatie(_voorschot_plannen()))


@app.route("/voorschot/csv")
@login_required
def voorschot_csv():
    import io, csv as _csv
    from flask import Response
    from dashboard.voorschot import build_specificatie
    spec = build_specificatie(_voorschot_plannen())
    buf = io.StringIO()
    w = _csv.writer(buf, delimiter=";")
    w.writerow(["Postcode+huisnummer", "Woningtype", "Advies", "Tarief excl btw"])
    for r in spec["regels"]:
        w.writerow([r["adres"], r["woningtype"], "Uitgebreid" if r["uitgebreid"] else "Basis",
                    "%.2f" % r["tarief_excl"]])
    w.writerow([])
    w.writerow(["Subtotaal excl", "", "", "%.2f" % spec["subtotaal_excl"]])
    w.writerow(["Voorschot 75% excl", "", "", "%.2f" % spec["voorschot_excl"]])
    w.writerow(["21% btw", "", "", "%.2f" % spec["btw"]])
    w.writerow(["Totaal incl", "", "", "%.2f" % spec["totaal_incl"]])
    w.writerow([])
    w.writerow(["VPL", spec["header"]["vpl_nummer"], "Documentnr", spec["header"]["documentnummer_opdracht"]])
    return Response("﻿" + buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=voorschot_specificatie.csv"})


# Veldgidsen — markdown uit docs/ gerenderd in de webapp (mobiel bij de opname te gebruiken)
GIDSEN = {
    "herkomst": ("🧭 Ontstaansgeschiedenis: energielabel, NTA, ISSO, VABI en Nij Begun", "HERKOMST-ENERGIELABEL-NTA-ISSO-NIJ-BEGUN.md"),
    "collega-start": ("👋 Start hier — introductie voor nieuwe collega's", "COLLEGA-INTRO.md"),
    "bronnen-audit": ("🔍 Actualiteit en aandachtspunten van de kennisbank", "KENNISBANK-BRONNEN-AUDIT-2026-08-12.md"),
    "opnameformulier": ("📋 Nij Begun opnameformulier (alles per project)", "nijbegun-opnameformulier.md"),
    "gedoogbeleid": ("🦇 Gedoogbeleid vleermuizen & eDNA (spouwisolatie, Groningen)", "gedoogbeleid-edna-gids.md"),
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
<div class="card gids-inhoud"><h1 style="font-size:24px">{{titel}}</h1>{{inhoud|safe}}</div>
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


KNOWLEDGE = """<h1>Kennisbank & vraagbaak</h1>
<p class=lead>Waarom het systeem werkt zoals het werkt, welke bronnen leidend zijn en wat je moet lezen
voordat je inhoudelijke keuzes maakt.</p>
<div class=hint><b>Brongebonden:</b> de vraagbaak zoekt alleen in toegestane, aanwezige documenten.
Een AI-antwoord vervangt nooit de controle door de bevoegde adviseur.</div>
<p><a class="btn sec" href="{{url_for('gids', slug='collega-start')}}">Nieuw hier? Start met de collega-intro</a></p>

<div class=card><h2>Het pad naar de huidige tool</h2>
<ol><li><b>Energielabel en energieprestatie</b> maken gebouwen vergelijkbaar.</li>
<li><b>NTA 8800</b> bepaalt de landelijke rekenmethode.</li>
<li><b>ISSO</b> vertaalt dit naar praktische opname- en bewijsregels.</li>
<li><b>BRL 9500-W</b> borgt vakbekwaamheid, proces en dossier.</li>
<li><b>VABI EPA-W</b> voert als geattesteerde software de formele berekening uit.</li>
<li><b>Nij Begun</b> gebruikt deze basis en voegt regeling-, plan-, catalogus- en indieningseisen toe.</li>
<li><b>Deze tool</b> bewaart één canoniek dossier en verbindt opname, controle, VABI en isolatieplan.</li></ol>
<a class="btn sec" href="{{url_for('gids', slug='herkomst')}}">Lees de volledige ontstaansgeschiedenis</a></div>

<div class=card><h2>Stel een inhoudelijke vraag</h2>
<form method=post><label for=vraag>Vraag over ISSO, NTA 8800, BRL, VABI of Nij Begun</label>
<textarea id=vraag name=vraag rows=4 required placeholder="Bijvoorbeeld: hoe bepaal ik volgens ISSO of een zolder tot de thermische zone behoort?">{{vraag}}</textarea>
<div class=btn-row><button class=btn type=submit>Zoek en beantwoord</button></div></form>
{% if fout %}<div class=warn>{{fout}}</div>{% endif %}
{% if antwoord %}<div class=card style="margin-top:16px"><h3>Brongebonden antwoord</h3><div class=gids-inhoud>{{antwoord_html|safe}}</div></div>{% endif %}
{% if hits %}<h3>Gebruikte bronpassages</h3>{% for h in hits %}<details class=acc><summary>[BRON {{loop.index}}] {{h.titel}}{% if h.kop %} — {{h.kop}}{% endif %}</summary>
<div class=acc-body><p class="muted small">Versie: {{h.versie or 'niet vastgelegd'}} · {{h.pad}}</p><pre style="white-space:pre-wrap;font-family:inherit">{{h.tekst}}</pre></div></details>{% endfor %}{% endif %}</div>

<div class=card><h2>Bronregister</h2><p class=muted>Een verplichte bron die ontbreekt of nog “IN TE VULLEN” is, blokkeert formeel vertrouwen in de vraagbaak voor dat onderwerp.</p>
<div class=table-wrap><table><thead><tr><th>Status</th><th>Bron</th><th>Categorie</th><th>Versie</th><th>Bestand</th></tr></thead><tbody>
{% for b in register.bronnen %}<tr><td>{% if b.aanwezig %}✅ Aanwezig{% else %}⚠️ Ontbreekt{% endif %}<br><span class="muted small">{{b.status}}</span></td>
<td><b>{{b.titel}}</b><br><span class="muted small">Eigenaar: {{b.eigenaar}}{% if b.toegang %} · Toegang: {{b.toegang}}{% endif %}{% if b.duplicaat_van %} · Dubbel van {{b.duplicaat_van}}{% endif %}</span></td><td>{{b.categorie}}</td><td>{{b.versie}}</td><td><code>{{b.pad or b.url}}</code></td></tr>{% endfor %}
</tbody></table></div><p class="muted small">Beheerinstructie: knowledge/README.md · Register: knowledge/sources.json</p></div>"""


@app.route("/kennisbank", methods=["GET", "POST"])
@login_required
def knowledge_page():
    register = knowledge_mod.laad_register()
    vraag = (request.form.get("vraag") or "").strip() if request.method == "POST" else ""
    hits, antwoord, fout = [], None, None
    if vraag:
        licensed = os.environ.get("NIJBEGUN_KENNISBANK_LICENTIE", "").lower() in ("1", "ja", "true")
        hits = knowledge_mod.zoek(vraag, register, licentiebronnen=licensed)
        antwoord, fout = knowledge_mod.beantwoord(vraag, hits, _cfg())
    antwoord_html = bouwjaar_mod.md_naar_html(antwoord) if antwoord else ""
    return page(KNOWLEDGE, register=register, vraag=vraag, hits=hits, antwoord=antwoord,
                antwoord_html=antwoord_html, fout=fout)


MAILS = """<h1>Bewonersmails</h1>
<p class=lead>De drie mails die de tool voor je opstelt, met voorbeeldgegevens ingevuld. Je verstuurt ze
altijd <b>zelf</b> vanuit je eigen mailprogramma — de tool mailt nooit namens jou.</p>
{% for m in mails %}
<div class=card>
  <h2>{{loop.index}}. {{m.titel}}</h2>
  <p class=muted>{{m.wanneer}}</p>
  <div class=kv><dt>Onderwerp</dt><dd>{{m.onderwerp}}</dd>
  <dt>Aan</dt><dd>{{m.aan}}</dd></div>
  <textarea rows=16 readonly id="m{{loop.index}}" style="font-family:inherit;margin-top:12px">{{m.tekst}}</textarea>
  <div class=btn-row><button class="btn sec" type=button
    onclick="navigator.clipboard.writeText(document.getElementById('m{{loop.index}}').value);this.textContent='✓ Gekopieerd'">Kopieer tekst</button>
  {% if m.route %}<a class="btn ghost" href="{{m.route}}">→ naar de leads-pagina</a>{% endif %}</div>
</div>
{% endfor %}
<div class=hint>De teksten staan in <b>dashboard/leads.py</b>. Wil je er iets structureel in wijzigen
(andere voorbereiding, andere verwachtingen), zeg het dan — dan passen we de bron aan in plaats van
elke mail met de hand.</div>"""


@app.route("/mails")
@login_required
def mails():
    """De drie bewonersmails naast elkaar, met voorbeeldgegevens — zodat je ze kunt nalezen
    zonder eerst een lead te moeten openen."""
    adv = _cfg().get("adviseur", {})
    voorbeeld = {"naam": "Jan de Boer", "straat": "Munsterheerd", "huisnummer": "106",
                 "woonplaats": "Groningen", "postcode": "9736GL", "toevoeging": "",
                 "email": "j.deboer@voorbeeld.nl", "afspraak": "2026-07-23T14:30"}
    ontv_o, ontv_t = leads_mod.ontvangst_mail(adv)
    ken_o, ken_t = leads_mod.concept_mail(voorbeeld, adv)
    bev_o, bev_t = leads_mod.bevestiging_mail(voorbeeld, adv)
    mails_ = [
        {"titel": "Ontvangstbevestiging", "onderwerp": ontv_o, "tekst": ontv_t,
         "aan": "alle nieuwe leads tegelijk, in BCC (nooit in Aan/CC — AVG)",
         "wanneer": "Direct nadat de leads uit het portaal binnenkomen. Eén mail voor de hele batch; "
                    "alleen de bewoners die je daadwerkelijk mailt gaan op 'mail gestuurd'.",
         "route": url_for("leads_ontvangst")},
        {"titel": "Kennismakingsmail", "onderwerp": ken_o, "tekst": ken_t,
         "aan": "één bewoner (naam en adres worden ingevuld)",
         "wanneer": "Als je de bewoner persoonlijk gaat benaderen om een afspraak te maken. Vraagt de "
                    "bewijslast voor de isolatie-opname alvast klaar te leggen.",
         "route": url_for("leads_pagina")},
        {"titel": "Afspraakbevestiging", "onderwerp": bev_o, "tekst": bev_t,
         "aan": "één bewoner, zodra er een datum staat",
         "wanneer": "Zodra je de afspraak hebt ingepland (📅 op de leadkaart). Bevat de voorbereiding "
                    "en het verwachtingsmanagement over wat de regeling wel en niet vergoedt.",
         "route": url_for("leads_pagina")},
    ]
    return page(MAILS, mails=mails_)


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


@app.route("/project/<tag>/verwijder", methods=["POST"])
@login_required
def project_verwijder(tag):
    """Verwijder een heel project (de map out/projects/<tag> met alles erin). Onomkeerbaar —
    het formulier vraagt om bevestiging. Een eventuele lead-koppeling wordt netjes losgemaakt
    zodat er geen dode 'Project'-knop achterblijft; de lead zelf blijft staan."""
    pdir = _pdir(tag)
    # pad-veiligheid: tag mag niet uit de projects-map wijzen (../ e.d.)
    if ".." in tag or "/" in tag or "\\" in tag or not os.path.isdir(pdir):
        abort(404)
    adres = (_load_state(tag) or {}).get("adres", tag)
    shutil.rmtree(pdir, ignore_errors=True)
    losgemaakt = leads_mod.wis_project_tag(tag)
    flash("Project '%s' definitief verwijderd (alle bestanden weg%s)."
          % (adres, ", lead-koppeling losgemaakt" if losgemaakt else ""))
    return redirect(url_for("home"))


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
                    b.indicator_type_huidig = st["huidig"].get("indicator_type") or ""
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
    # gewogen verliesoppervlakte Als (NTA 8800 §6.7.3: grond/kruipruimte x0,7, AVR/woningscheidend x0)
    verlies = verliesoppervlak(dos)
    # gevels zijn BRUTO (b x h; ramen/deuren zitten erin) -> kozijnen niet dubbel tellen
    ag = dos.geometrie.gebruiksoppervlakte_ag_m2 or 0
    std_eigen = standaard_eis(dos)          # Standaard-eis zelf voorgerekend (§5.3.2) als 0-meting-verwachting
    bj_titel, bj_html = bouwjaar_mod.hint(dos.identificatie.bouwjaar)
    # dakvlakken (voor de 'dakraam toevoegen'-keuze): label + oriëntatie-waarde
    dak_vlakken = [("%s · %s · %.1f m²" % (s.id, s.orientatie or "Horizontaal", s.oppervlakte_m2 or 0),
                    s.orientatie or "") for s in dos.schil if (s.type or "") == "dak"]
    dak_vlakken_idx = [("%s · %s · %.1f m²" % (s.id, s.orientatie or "Horizontaal", s.oppervlakte_m2 or 0), i)
                       for i, s in enumerate(dos.schil) if (s.type or "") == "dak"]
    # dakkapel (ISSO 82.1 §8.2.1) breekt door een HELLEND vlak heen -> platte daken en het
    # dakje van een andere dakkapel zijn geen geldig moederdak (ook server-side afgedwongen
    # in opname_dakkapel, dit is alleen de klikbare keuzelijst).
    dakkapel_moeder_opts = [(lbl, i) for lbl, i in dak_vlakken_idx
                            if (dos.schil[i].hellingshoek or 0) > 0
                            and "dakkapel" not in (dos.schil[i].id or "").lower()]
    n_dakraam = sum(1 for s in dos.schil if "dakraam" in (s.subtype or "").lower())
    n_dakkapel = sum(1 for s in dos.schil if "dakkapel" in (s.id or "").lower() and "voorvlak" in (s.id or "").lower())
    gebouw_overzicht_svg = gebouw_svg(dos) if dos.schil else ""
    return page(OPNAME_TMPL, stepper=stepper("opname", st), tag=tag, st=st, d=dos,
                elementen=elementen, zones=zones, verlies=verlies, ag=ag, std_eigen=std_eigen,
                bj_titel=bj_titel, bj_html=bj_html, woningtypes=WONINGTYPE_OPTS, dak_vlakken=dak_vlakken,
                dak_vlakken_idx=dak_vlakken_idx, dakkapel_moeder_opts=dakkapel_moeder_opts,
                n_dakraam=n_dakraam, n_dakkapel=n_dakkapel,
                begr_opts=BEGR_OPTS, ori_opts=ORI_OPTS, glas_opts=GLAS_OPTS,
                koz_opts=KOZ_OPTS, bouwjaarklasse_opts=BOUWJAARKLASSE_OPTS, rc_bron_opts=RC_BRON_OPTS,
                ico=TYPE_ICO, gebouw_svg=gebouw_overzicht_svg)


INTAKE_PREVIEW = """{{stepper|safe}}<h1>MagicPlan-intake controleren</h1>
<p class=lead>Controleer de projectkoppeling en de gevolgen. Het dossier is nog niet gewijzigd.</p>
<div class=card><h2>Projectidentiteit</h2>
<dl class=kv><dt>MagicPlan-project</dt><dd>{{p.manifest.project_id}}</dd>
<dt>Woning</dt><dd>{{p.manifest.identity.postcode}} {{p.manifest.identity.huisnummer}} · {{p.manifest.identity.straat}}</dd>
<dt>Formulierfingerprint</dt><dd><code>{{p.manifest.form_fingerprint}}</code></dd></dl></div>
<div class=card><h2>Verschillen</h2>
<dl class=kv><dt>Schildelen</dt><dd>{{p.diff.schil.voor}} → {{p.diff.schil.na}} (import: {{p.diff.schil.import}}, wizard: {{p.diff.schil.wizard_voor}} → {{p.diff.schil.wizard_na}})</dd>
<dt>Toegevoegd</dt><dd>{{p.diff.schil.toegevoegd|join(', ') or 'geen'}}</dd>
<dt>Vervallen uit import</dt><dd>{{p.diff.schil.verwijderd|join(', ') or 'geen'}}</dd>
<dt>Installaties</dt><dd>{{p.diff.installaties.voor}} → {{p.diff.installaties.na}} · {{p.diff.installaties.beleid}}</dd>
<dt>Foto's</dt><dd>{{p.diff.fotos.voor}} → {{p.diff.fotos.na}} · {{p.diff.fotos.beleid}}</dd>
<dt>Maatregelen</dt><dd>{{p.diff.maatregelen.voor}} → {{p.diff.maatregelen.na}} · {{p.diff.maatregelen.beleid}}</dd>
<dt>Vabi-resultaten</dt><dd>{{p.diff.vabi_resultaten.beleid}}</dd></dl></div>
<div class=card><h2>Actiepunten na import</h2>
{% for groep, items in p.acties.items() %}<h3>{{groep|capitalize}} <span class="pill gray">{{items|length}}</span></h3>
{% if items %}<ul class=check>{% for item in items %}<li>{{item}}</li>{% endfor %}</ul>{% else %}<p class=muted>Geen open punten.</p>{% endif %}{% endfor %}</div>
<div class=btn-row><form method=post action="{{url_for('opname_intake_bevestig', tag=tag)}}">
<input type=hidden name=token value="{{token}}"><button class="btn lg">Import expliciet bevestigen</button></form>
<form method=post action="{{url_for('opname_intake_annuleer', tag=tag)}}"><input type=hidden name=token value="{{token}}">
<button class="btn sec">Annuleren en preview verwijderen</button></form></div>"""


def _intake_stage_dir(tag, token):
    if not re.fullmatch(r"[A-Za-z0-9_-]{20,100}", token or ""):
        return None
    return os.path.join(_pdir(tag), ".intake", token)


def _bestand_sha256(pad):
    import hashlib
    with open(pad, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _intake_cleanup(stage):
    if stage:
        shutil.rmtree(stage, ignore_errors=True)


_INTAKE_LOCKS = {}
_INTAKE_LOCKS_GUARD = threading.Lock()
_INTAKE_BEFORE_LOCK_HOOK = None                 # uitsluitend injectiepunt voor deterministische tests
_INTAKE_REPLACE = os.replace                    # idem: fout op tweede atomische publicatie injecteren


@contextlib.contextmanager
def _intake_project_lock(tag):
    """Serializeer confirm binnen dit proces én tussen dashboardprocessen per project."""
    lockpad = os.path.join(_pdir(tag), ".intake-confirm.lock")
    sleutel = os.path.abspath(lockpad)
    with _INTAKE_LOCKS_GUARD:
        thread_lock = _INTAKE_LOCKS.setdefault(sleutel, threading.Lock())
    with thread_lock:
        os.makedirs(os.path.dirname(lockpad), exist_ok=True)
        with open(lockpad, "a+b") as fh:
            if os.path.getsize(lockpad) == 0:
                fh.write(b"0"); fh.flush()
            fh.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
                try: yield
                finally:
                    fh.seek(0); msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
                try: yield
                finally: fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


class _IntakeRevisionError(RuntimeError):
    pass


def _schrijf_json_fsync(pad, data):
    with open(pad, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.flush(); os.fsync(fh.fileno())


def _intake_atomic_pair(dossier_pad, dossier, state_pad, state, stage):
    """Publiceer dossier+state als paar; herstel het dossier als state-publicatie faalt."""
    dossier_next, state_next = os.path.join(stage, "dossier.next"), os.path.join(stage, "state.next")
    dossier_backup = os.path.join(stage, "dossier.before")
    with open(dossier_pad, "rb") as bron, open(dossier_backup, "wb") as doel:
        doel.write(bron.read()); doel.flush(); os.fsync(doel.fileno())
    _schrijf_json_fsync(dossier_next, dossier.to_dict())
    _schrijf_json_fsync(state_next, state)
    dossier_gepubliceerd = False
    try:
        _INTAKE_REPLACE(dossier_next, dossier_pad); dossier_gepubliceerd = True
        _INTAKE_REPLACE(state_next, state_pad)
    except Exception:
        if dossier_gepubliceerd:
            os.replace(dossier_backup, dossier_pad)
        raise


@app.route("/project/<tag>/opname/intake/preview", methods=["POST"])
@login_required
def opname_intake_preview(tag):
    st, dos = _load_state(tag), _dossier(tag)
    if not st or not dos:
        abort(404)
    f = request.files.get("pakket")
    if not f or not f.filename or os.path.splitext(f.filename)[1].lower() != ".zip":
        flash("Kies één MagicPlan-importpakket (.zip).")
        return redirect(url_for("opname", tag=tag))
    token = secrets.token_urlsafe(24)
    stage = _intake_stage_dir(tag, token)
    pakket = os.path.join(stage, "pakket.zip")
    os.makedirs(stage, exist_ok=False)
    try:
        f.save(pakket)
        from magicplan.intake import bouw_preview
        p = bouw_preview(pakket, dos, stage, st.get("magicplan_project_id", ""))
        # Dashboardfoto's en Vabi-uploads leven deels in projectstate/bestanden, buiten Dossier.
        # Ze blijven onaangeraakt; neem ze mee in de getoonde werkelijke behoudtelling.
        foto_count = len(dos.fotos) + sum(bool(st.get(k)) for k in ("foto_voorkant", "foto_huisnummer"))
        p["diff"]["fotos"].update(voor=foto_count, na=foto_count)
        p["diff"]["vabi_resultaten"]["project_state"] = {
            "huidig": bool(st.get("huidig")), "na": bool(st.get("na")), "beleid": "behouden"}
        staged_dossier = os.path.join(stage, "dossier.json")
        save_json(p["nieuw"], staged_dossier)
        basis_dossier = os.path.join(_pdir(tag), st["dossier_file"])
        publiek = {k: v for k, v in p.items() if k not in ("nieuw", "notes")}
        meta = {"token": token, "pakket_sha256": _bestand_sha256(pakket),
                "dossier_sha256": _bestand_sha256(staged_dossier),
                "basis_sha256": _bestand_sha256(basis_dossier),
                "basis_identiteit": {"bag_vboid": dos.identificatie.bag_vboid,
                    "postcode": dos.identificatie.postcode, "huisnummer": dos.identificatie.huisnummer},
                "preview": publiek}
        tijdelijk = os.path.join(stage, "metadata.tmp")
        with open(tijdelijk, "w", encoding="utf-8") as fh:
            json.dump(meta, fh, ensure_ascii=False, indent=2)
            fh.flush(); os.fsync(fh.fileno())
        os.replace(tijdelijk, os.path.join(stage, "metadata.json"))
    except Exception:
        app.logger.warning("MagicPlan-importpakket geweigerd", exc_info=True)
        _intake_cleanup(stage)
        flash("Importpakket geweigerd. Controleer identiteit, fingerprint en pakketinhoud.")
        return redirect(url_for("opname", tag=tag))
    return page(INTAKE_PREVIEW, stepper=stepper("opname", st), tag=tag, p=publiek, token=token)


@app.route("/project/<tag>/opname/intake/bevestig", methods=["POST"])
@login_required
def opname_intake_bevestig(tag):
    st, dos = _load_state(tag), _dossier(tag)
    token = request.form.get("token", "")
    stage = _intake_stage_dir(tag, token)
    if not st or not dos or not stage:
        abort(404)
    metadata = os.path.join(stage, "metadata.json")
    claim = os.path.join(stage, "metadata.consuming")
    try:
        os.replace(metadata, claim)  # atomische one-time claim; een tweede bevestiging verliest.
    except OSError:
        # Bij een gelijktijdige bevestiging gebruikt de winnaar metadata.consuming nog; diens
        # staging mag de verliezer niet opruimen. Een anderszins verweesde stage ruimen we wel op.
        if not os.path.isfile(claim):
            _intake_cleanup(stage)
        flash("De intake-preview is verlopen; upload het pakket opnieuw.")
        return redirect(url_for("opname", tag=tag))
    try:
        with open(claim, encoding="utf-8") as fh: meta = json.load(fh)
        pakket, dp = os.path.join(stage, "pakket.zip"), os.path.join(stage, "dossier.json")
        if meta.get("token") != token or meta.get("pakket_sha256") != _bestand_sha256(pakket) \
                or meta.get("dossier_sha256") != _bestand_sha256(dp):
            raise ValueError("staging gewijzigd")
        if _INTAKE_BEFORE_LOCK_HOOK:
            _INTAKE_BEFORE_LOCK_HOOK()
        with _intake_project_lock(tag):
            # CAS: pas NADAT de projectlock vaststaat de actuele pair opnieuw laden en vergelijken.
            st_nu, dos_nu = _load_state(tag), _dossier(tag)
            if not st_nu or not dos_nu:
                raise _IntakeRevisionError("project verdwenen")
            basis = os.path.join(_pdir(tag), st_nu["dossier_file"])
            state_pad = os.path.join(_pdir(tag), "project.json")
            basis_i = {"bag_vboid": dos_nu.identificatie.bag_vboid,
                       "postcode": dos_nu.identificatie.postcode, "huisnummer": dos_nu.identificatie.huisnummer}
            if meta.get("basis_sha256") != _bestand_sha256(basis) or meta.get("basis_identiteit") != basis_i:
                raise _IntakeRevisionError("basisrevisie gewijzigd")
            from magicplan.intake import merge
            nieuw = merge(dos_nu, load_json(dp)); p = meta["preview"]
            st_nieuw = copy.deepcopy(st_nu)
            st_nieuw["magicplan_project_id"] = p["manifest"]["project_id"]
            st_nieuw["intake_acties"] = p["acties"]
            st_nieuw.setdefault("import_historie", []).append({
                "tijd": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "bestand": "MagicPlan-pakket %s" % p["manifest"]["project_id"], "vlakken": len(nieuw.schil)})
            st_nieuw["import_historie"] = st_nieuw["import_historie"][-12:]
            _intake_atomic_pair(basis, nieuw, state_pad, st_nieuw, stage)
    except _IntakeRevisionError:
        flash("Import gestopt: dit project is sinds de preview gewijzigd. Maak een nieuwe preview.")
        return redirect(url_for("opname", tag=tag))
    except Exception:
        app.logger.warning("MagicPlan-intakebevestiging gestopt", exc_info=True)
        flash("Import gestopt: staging of opslag faalde; de vorige projectversie is behouden.")
        return redirect(url_for("opname", tag=tag))
    finally:
        _intake_cleanup(stage)
    flash("MagicPlan-import bevestigd; adviseurswerk en Vabi-resultaten zijn behouden.")
    return redirect(url_for("opname", tag=tag))


@app.route("/project/<tag>/opname/intake/annuleer", methods=["POST"])
@login_required
def opname_intake_annuleer(tag):
    if not _load_state(tag): abort(404)
    stage = _intake_stage_dir(tag, request.form.get("token", ""))
    if not stage: abort(404)
    _intake_cleanup(stage)
    flash("Intake-preview verwijderd; het dossier is niet gewijzigd.")
    return redirect(url_for("opname", tag=tag))


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
        # Herimport (taak 014/015): dakwerk uit de webapp-wizard mag een herimport nooit stil
        # wegvegen — geldt voor ZOWEL een CSV (kan sowieso nooit dakgeometrie leveren, dak = webapp
        # sinds 23-7) ALS een dossier-.json-upload (bv. een oudere export terugzetten). Alleen
        # vlakken overdragen wier id nog niet in de nieuwe opname voorkomt (een .json-upload kan
        # zijn eigen, al meegeëxporteerde wizardvlakken hebben — dan niet dubbel toevoegen).
        _nieuwe_ids = {s.id for s in nieuw.schil}
        _behouden = [s for s in dos.schil if s.bron == "webapp-wizard" and s.id not in _nieuwe_ids]
        if _behouden:
            nieuw.schil += _behouden
            _dak_fallback_opschonen(nieuw)
            notes.append("%d eerder met de webapp-dakwizard toegevoegde vlak(ken) zijn behouden "
                         "bij deze herimport." % len(_behouden))
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
    st["vabi_acties"] = [{"tekst": a, "prio": _is_prio_actie(a)} for a in acties]
    # behoud eerder ingevulde identificatie waar de import leeg is (bouwjaar: BAG/lead-waarde
    # mag niet weggevaagd worden door een CSV zonder Bouwjaar-veld)
    for attr in ("straat", "huisnummer", "postcode", "plaats", "woningtype", "bouwjaar", "bag_vboid"):
        if not getattr(nieuw.identificatie, attr, "") and getattr(oud, attr, ""):
            setattr(nieuw.identificatie, attr, getattr(oud, attr))
    save_json(nieuw, os.path.join(_pdir(tag), st["dossier_file"]))
    st["adres"] = "%s %s, %s" % (nieuw.identificatie.straat or "", nieuw.identificatie.huisnummer or "",
                                 nieuw.identificatie.plaats or "")
    # import-historie: datum/tijd + bestand + #vlakken, zodat je (ook op een ander device) ziet
    # welke opname de meest recente is (laatste 12 bewaard)
    st.setdefault("import_historie", []).append(
        {"tijd": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
         "bestand": f.filename, "vlakken": len(nieuw.schil)})
    st["import_historie"] = st["import_historie"][-12:]
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
        s.bouwjaarklasse = f.get("bouwjaarklasse", "").strip()
        s.rc_bron = f.get("rc_bron", "").strip()
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


# ---- DAK TOEVOEGEN (webapp-wizard: plat / driehoek-zadeldak / 9 geometrieën; herhaalbaar, auto-genummerd) ----
DAK_COMPAS = ["N", "NO", "O", "ZO", "Z", "ZW", "W", "NW"]


def _opp8(o):
    o = (o or "").upper()
    return DAK_COMPAS[(DAK_COMPAS.index(o) + 4) % 8] if o in DAK_COMPAS else ""


def _zij8(o):
    o = (o or "").upper()
    if o not in DAK_COMPAS:
        return ("", "")
    return (DAK_COMPAS[(DAK_COMPAS.index(o) + 2) % 8], DAK_COMPAS[(DAK_COMPAS.index(o) - 2) % 8])


def _volgend_dak_nr(dos):
    """Volgend dak-groepnummer (auto-nummering): hoogste dakN in de ids + 1 (start 1)."""
    n = 0
    for s in dos.schil:
        m = re.match(r"dak(\d+)", (s.id or ""))
        if m:
            n = max(n, int(m.group(1)))
    return n + 1


def _dak_fallback_opschonen(dos):
    """Verwijder de parser-placeholder (zie `vabi.preflight.dak_fallback_schildelen` — de gedeelde
    definitie, ook gebruikt door de Vabi-preflight-poort) zodra er een écht dakvlak naast staat.
    Zonder dit zou het dak dubbel meetellen in de Vabi-export (taak 014, live gevonden op het
    Essenhage-testproject: 55,56 m² legacy-placeholder naast 2x28,71 m² wizardvlakken).
    Verwijdert UITSLUITEND de placeholder — andere dakvlakken (bv. uit een oudere CSV met
    expliciete dakvelden, of eerder handmatig werk) worden nooit stil overschreven; bij twijfel
    (geen aantoonbare placeholder) doet deze functie niets."""
    from vabi.preflight import dak_fallback_schildelen
    fallback = dak_fallback_schildelen(dos.schil)
    if not fallback:
        return None
    fallback_ids = {id(s) for s in fallback}
    if not any(s.type == "dak" and id(s) not in fallback_ids for s in dos.schil):
        return None
    verwijderd_m2 = sum(s.oppervlakte_m2 or 0 for s in fallback)
    verwijderd_ids = [s.id or "(zonder id)" for s in fallback]
    dos.schil = [s for s in dos.schil if id(s) not in fallback_ids]
    return verwijderd_m2, verwijderd_ids


def _dak_toegevoegd_melding(basis, verwijderd, vervolg="Nog een dak? Kies opnieuw hieronder."):
    """Bouw de flash-tekst voor een dak-wizard-route: basismelding + (indien van toepassing) de
    _dak_fallback_opschonen-uitkomst, gedeeld door alle dak-toevoeg-routes zodat de bewoording
    maar op één plek hoeft te kloppen."""
    melding = basis
    if verwijderd:
        v_m2, v_ids = verwijderd
        melding += (" Placeholder-dak %s (%.2f m² footprint-schatting) verwijderd."
                    % (", ".join(v_ids), v_m2))
    return melding + " " + vervolg


def _erf_dak_kwargs(dos):
    """SchilDeel-kwargs die een nieuw dakvlak erft van de Constructies-DAK-standaard (MagicPlan-
    form, `dos.opname.dak_standaard`) — leeg/geen standaard -> Onbekend (geen gok). Gedeeld door
    alle dak-wizards zodat een nieuw BouwdeelStandaard-veld maar op één plek bijgehouden hoeft."""
    ds = getattr(dos.opname, "dak_standaard", None)
    return {
        "begrenzing": (ds.begrenzing if ds else "") or "Buitenlucht",
        "isolatie_aanwezig": (ds.isolatie_aanwezig if ds else "") or "Onbekend",
        "isolatiedikte_mm": ds.isolatiedikte_mm if ds else None,
        "bouwjaarklasse": (ds.bouwjaarklasse if ds else "") or "",
        "spouw_aanwezig": ds.spouw_aanwezig if ds else None,
        "rc_bron": (ds.rc_bron if ds else "") or "",
    }


@app.route("/project/<tag>/opname/dak/plat", methods=["POST"])
@login_required
def opname_dak_plat(tag):
    st, dos = _load_state(tag), _dossier(tag)
    if not st or not dos:
        abort(404)
    from core.dossier import SchilDeel
    breedte = _f2(request.form.get("breedte"))
    diepte = _f2(request.form.get("diepte"))
    maten_geldig = (breedte is not None and diepte is not None
                    and all(math.isfinite(x) and x > 0 for x in (breedte, diepte)))
    m2 = round(breedte * diepte, 2) if maten_geldig else (_f2(request.form.get("m2")) or 0.0)
    if not maten_geldig:
        breedte = diepte = None
    if not m2:
        flash("Vul een oppervlak in voor het platte dak.")
        return redirect(url_for("opname", tag=tag))
    nr = _volgend_dak_nr(dos)
    dos.schil.append(SchilDeel(id="dak%d-plat" % nr, type="dak", subtype="plat dak",
                               orientatie="", oppervlakte_m2=m2, hellingshoek=0,
                               breedte_m=breedte, diepte_m=diepte, geometrie_groep="dak%d" % nr,
                               rekenzone=int(request.form.get("rekenzone") or 1),
                               opmerkingen="Dak %d (plat) — webapp-invoer" % nr, bron="webapp-wizard",
                               **_erf_dak_kwargs(dos)))
    verwijderd = _dak_fallback_opschonen(dos)
    _dos_save(tag, st, dos)
    flash(_dak_toegevoegd_melding("Plat dak %d toegevoegd (%.2f m²)." % (nr, m2), verwijderd))
    return redirect(url_for("opname", tag=tag) + "#dak-toevoegen")


@app.route("/project/<tag>/opname/dak/driehoek", methods=["POST"])
@login_required
def opname_dak_driehoek(tag):
    """Zadeldak via de driehoek: lange zijde c (kopgevel-basis) x breedte (noklengte). Hellend vlak =
    schuine zijde x breedte (voor + achter); kopgevels = driehoek op de haakse gevels, alleen indien buiten."""
    st, dos = _load_state(tag), _dossier(tag)
    if not st or not dos:
        abort(404)
    from core.dossier import SchilDeel
    from core.geometry import dak_vlakken_zadeldak
    f = request.form
    o = (f.get("orient_hellend") or "").upper()
    c = _f2(f.get("lange_zijde")) or 0.0
    breedte = _f2(f.get("breedte")) or 0.0
    h1 = _f2(f.get("helling1")) or 0.0
    h2 = _f2(f.get("helling2")) or h1
    if not (o in DAK_COMPAS and all(math.isfinite(x) for x in (c, breedte, h1, h2))
            and c > 0 and breedte > 0 and 0 < h1 < 90 and 0 < h2 < 90):
        flash("Zadeldak: kies een oriëntatie, en vul lange zijde, breedte en geldige hellingshoeken (0-89°) in.")
        return redirect(url_for("opname", tag=tag) + "#dak-toevoegen")
    footprint = c * breedte
    zij = _zij8(o)
    vlakken = dak_vlakken_zadeldak(footprint, c, h1, orient_schuin=(o, _opp8(o)), orient_kopgevel=zij)
    # Eén nok voor beide vlakken. Bij ongelijke hoeken verschuift die nok: de twee horizontale
    # runs tellen op tot c en leveren dezelfde nokhoogte. core.geometry blijft bewust symmetrisch.
    nokhoogte = (c / (1 / math.tan(math.radians(h1)) + 1 / math.tan(math.radians(h2))))
    runs = {o: nokhoogte / math.tan(math.radians(h1)),
            _opp8(o): nokhoogte / math.tan(math.radians(h2))}
    hoeken = {o: h1, _opp8(o): h2}
    for v in vlakken:
        if v.get("kind") == "dak":
            hoek = hoeken[v["orientatie"]]
            v["m2"] = round(breedte * runs[v["orientatie"]] / math.cos(math.radians(hoek)), 2)
            v["hellingshoek"] = hoek
        elif h2 != h1:
            v["m2"] = round(0.5 * c * nokhoogte, 2)
    kop_buiten = {zij[0]: f.get("kopgevel1_buiten") == "on", zij[1]: f.get("kopgevel2_buiten") == "on"}
    nr = _volgend_dak_nr(dos)
    rz = int(f.get("rekenzone") or 1)
    # Alleen de hellende dakvlakken zelf erven de dak-standaard, niet de kopgevel-driehoek
    # hieronder (die is gevel-typed en hoort bij de gevel-standaard, niet de dak-standaard).
    n_dak = n_kop = 0
    for v in vlakken:
        if v.get("kind") == "gevel":     # kopgevel-driehoek -> alleen als die gevel aan buiten grenst
            if not kop_buiten.get(v.get("orientatie")):
                continue
            dos.schil.append(SchilDeel(id="dak%d-kopgevel-%s" % (nr, (v["orientatie"] or "x").lower()),
                                       type="gevel", subtype="kopgevel-driehoek", begrenzing="Buitenlucht",
                                       orientatie=v["orientatie"], oppervlakte_m2=v["m2"], isolatie_aanwezig="Onbekend",
                                       geometrie_groep="dak%d" % nr, bron="webapp-wizard",
                                       rekenzone=rz, opmerkingen="Dak %d — kopgevel-driehoek (zadeldak, basis %.2f m)" % (nr, c)))
            n_kop += 1
        else:
            dos.schil.append(SchilDeel(id="dak%d-schuin-%s" % (nr, (v["orientatie"] or "x").lower()),
                                       type="dak", subtype="schuin (zadeldak)",
                                       orientatie=v["orientatie"], oppervlakte_m2=v["m2"], hellingshoek=v.get("hellingshoek"),
                                       breedte_m=breedte, diepte_m=runs[v["orientatie"]], geometrie_groep="dak%d" % nr,
                                       rekenzone=rz, bron="webapp-wizard",
                                       opmerkingen="Dak %d — hellend vlak %s (c=%.2f x breedte=%.2f, %.0f°)"
                                       % (nr, v["orientatie"], c, breedte, v.get("hellingshoek") or h1),
                                       **_erf_dak_kwargs(dos)))
            n_dak += 1
    verwijderd = _dak_fallback_opschonen(dos)
    _dos_save(tag, st, dos)
    flash(_dak_toegevoegd_melding(
        "Zadeldak %d toegevoegd: %d hellend vlak + %d kopgevel." % (nr, n_dak, n_kop), verwijderd))
    return redirect(url_for("opname", tag=tag) + "#dak-toevoegen")


@app.route("/project/<tag>/opname/dak/negen", methods=["POST"])
@login_required
def opname_dak_negen(tag):
    """Zelf de m² per oriëntatie invoeren (9 geometrieën N..NW + Horizontaal) — voor een lastig dak."""
    st, dos = _load_state(tag), _dossier(tag)
    if not st or not dos:
        abort(404)
    from core.dossier import SchilDeel
    f = request.form
    nr = _volgend_dak_nr(dos)
    rz = int(f.get("rekenzone") or 1)
    helling = _f2(f.get("helling9"))
    n_add = 0
    for o in DAK_COMPAS + ["Horizontaal"]:
        m2 = _f2(f.get("m2_%s" % o))
        if not m2:
            continue
        dos.schil.append(SchilDeel(id="dak%d-%s" % (nr, o.lower()[:4]), type="dak", subtype="vlak (zelf ingevoerd)",
                                   orientatie=("" if o == "Horizontaal" else o),
                                   oppervlakte_m2=m2, hellingshoek=(0 if o == "Horizontaal" else helling),
                                   rekenzone=rz, bron="webapp-wizard",
                                   opmerkingen="Dak %d — m² zelf ingevoerd (%s)" % (nr, o),
                                   **_erf_dak_kwargs(dos)))
        n_add += 1
    if not n_add:
        flash("Geen m² ingevuld — vul minstens één oriëntatie in.")
        return redirect(url_for("opname", tag=tag) + "#dak-toevoegen")
    verwijderd = _dak_fallback_opschonen(dos)
    _dos_save(tag, st, dos)
    flash(_dak_toegevoegd_melding("Dak %d toegevoegd: %d vlak(ken) met eigen m²." % (nr, n_add), verwijderd))
    return redirect(url_for("opname", tag=tag) + "#dak-toevoegen")


@app.route("/project/<tag>/opname/dakraam", methods=["POST"])
@login_required
def opname_dakraam(tag):
    """Voeg een dakraam toe aan een dakvlak. Wordt een kozijn (subtype 'Dakraam') met de oriëntatie van
    dat dakvlak -> de VABI-generator plaatst het als deelvlak op het DAK-hoofdvlak (glas van het dak af)."""
    st, dos = _load_state(tag), _dossier(tag)
    if not st or not dos:
        abort(404)
    from core.dossier import SchilDeel
    f = request.form
    n_bestaand = sum(1 for s in dos.schil if "dakraam" in (s.subtype or "").lower())
    if n_bestaand >= 20:
        flash("Maximaal 20 dakramen bereikt.")
        return redirect(url_for("opname", tag=tag) + "#dak-toevoegen")
    o = (f.get("dak_orient") or "").strip()
    m2 = _f2(f.get("m2"))
    if not m2:
        b, h = _f2(f.get("breedte")), _f2(f.get("hoogte"))
        m2 = round(b * h, 2) if (b and h) else None
    if not m2:
        flash("Vul het dakraam-oppervlak in (breedte x hoogte, of direct m²).")
        return redirect(url_for("opname", tag=tag) + "#dak-toevoegen")
    nr = n_bestaand + 1
    dos.schil.append(SchilDeel(id="dakraam-%d-%s" % (nr, (o or "hor").lower()[:4]), type="kozijn", subtype="Dakraam",
                               orientatie=o, oppervlakte_m2=m2, glastype=f.get("glas", "").strip(),
                               kozijnmateriaal="Hout of kunststof", begrenzing="Buitenlucht", rekenzone=1,
                               bron="webapp-wizard",
                               toevoerrooster=f.get("rooster", "").strip(),
                               zonwering=f.get("zonwering", "").strip(),
                               opmerkingen=("Dakraam in dakvlak %s (glas van het dakvlak afgetrokken in Vabi)"
                                            % (o or "horizontaal")
                                            + (" | toevoerrooster: %s" % f.get("rooster").strip()
                                               if f.get("rooster", "").strip() else ""))))
    _dos_save(tag, st, dos)
    flash("Dakraam %d toegevoegd (%.2f m² in dakvlak %s). Nog een dakraam? Herhaal hieronder." % (nr, m2, o or "horizontaal"))
    return redirect(url_for("opname", tag=tag) + "#dak-toevoegen")


@app.route("/project/<tag>/opname/dakkapel", methods=["POST"])
@login_required
def opname_dakkapel(tag):
    """ISSO 82.1 §8.2.1: een dakkapel voegt voorvlak+2 wangen (gevel) + een plat dakje (dak) toe, en
    trekt het gat dat ze in het schuine moederdakvlak maakt van dát dakvlak af (core/geometry.dakkapel_vlakken)."""
    st, dos = _load_state(tag), _dossier(tag)
    if not st or not dos:
        abort(404)
    from core.dossier import SchilDeel
    from core.geometry import dakkapel_vlakken
    f = request.form
    try:
        moeder_i = int(f.get("moederdak_i", ""))
    except ValueError:
        moeder_i = -1
    if not (0 <= moeder_i < len(dos.schil)):
        flash("Kies een geldig moederdakvlak voor de dakkapel.")
        return redirect(url_for("opname", tag=tag) + "#dak-toevoegen")
    moeder = dos.schil[moeder_i]
    # Leg de classificatie vast vóór de dakkapelcorrectie. De gedeelde herkenner omvat
    # zowel de expliciete tag als legacy-dossiers met id="dak" en een lege bron.
    from vabi.preflight import dak_fallback_schildelen
    moeder_was_fallback = bool(dak_fallback_schildelen([moeder]))
    # ISSO 82.1 §8.2.1: een dakkapel breekt door een HELLEND vlak heen -> een plat dak of het
    # dakje van een andere dakkapel is server-side ook geen geldig moederdak (niet alleen de
    # dropdown-filter vertrouwen, dit endpoint is ook los aan te roepen).
    if ((moeder.type or "").lower() != "dak" or (moeder.hellingshoek or 0) <= 0
            or "dakkapel" in (moeder.id or "").lower()):
        flash("Kies een hellend dakvlak (hellingshoek > 0°) als moederdak voor de dakkapel.")
        return redirect(url_for("opname", tag=tag) + "#dak-toevoegen")
    b, h, d = _f2(f.get("breedte")), _f2(f.get("hoogte")), _f2(f.get("diepte"))
    if (not (b and h and d) or not all(math.isfinite(x) for x in (b, h, d))
            or b <= 0 or h <= 0 or d <= 0):
        flash("Vul een geldige, positieve breedte, hoogte en diepte van de dakkapel in.")
        return redirect(url_for("opname", tag=tag) + "#dak-toevoegen")
    stijging = d * math.tan(math.radians(moeder.hellingshoek))
    if stijging >= h:
        flash("Deze dakkapel is geometrisch niet haalbaar: bij %.0f° stijgt het moederdak over %.2f m "
              "diepte met %.2f m. De hoogte moet groter zijn dan die stijging."
              % (moeder.hellingshoek, d, stijging))
        return redirect(url_for("opname", tag=tag) + "#dak-toevoegen")
    vlakken = dakkapel_vlakken(b, h, d, hellingshoek_dakvlak_graden=moeder.hellingshoek)
    gat = vlakken["gat_schuin_dak_m2"]
    moeder_m2_voor = moeder.oppervlakte_m2 or 0
    if gat and gat > moeder_m2_voor:
        flash("Deze dakkapel past niet: het gat (%.2f m²) is groter dan het gekozen moederdak %s "
              "(%.2f m²). Controleer het moederdak en de maten (breedte/hoogte/diepte)."
              % (gat, moeder.id, moeder_m2_voor))
        return redirect(url_for("opname", tag=tag) + "#dak-toevoegen")
    nr = sum(1 for s in dos.schil if "dakkapel" in (s.id or "").lower() and "voorvlak" in (s.id or "").lower()) + 1
    wangen_geisoleerd = bool(f.get("wangen_geisoleerd"))
    try:
        rekenzone = int(f.get("rekenzone") or moeder.rekenzone or 1)
    except ValueError:
        rekenzone = moeder.rekenzone or 1
    orient = moeder.orientatie or ""
    zij_l, zij_r = _zij8(orient) if orient else ("", "")
    voorvlak = SchilDeel(id="dakkapel%d-voorvlak" % nr, type="gevel", subtype="Dakkapel voorvlak",
                         orientatie=orient, begrenzing="Buitenlucht", oppervlakte_m2=round(b * h, 2),
                         breedte_m=b, diepte_m=d, hoogte_m=h, moedervlak_id=moeder.id,
                         geometrie_groep="dakkapel%d" % nr, bron="webapp-wizard",
                         rekenzone=rekenzone, opmerkingen="Dakkapel %d — voorvlak in dakvlak %s" % (nr, moeder.id))
    wang_l = SchilDeel(id="dakkapel%d-wang-links" % nr, type="gevel", subtype="Dakkapel wang",
                       orientatie=zij_l, begrenzing="Buitenlucht", oppervlakte_m2=round(d * h, 2),
                       breedte_m=b, diepte_m=d, hoogte_m=h, moedervlak_id=moeder.id,
                       geometrie_groep="dakkapel%d" % nr, bron="webapp-wizard",
                       rekenzone=rekenzone, isolatie_aanwezig=("Ja" if wangen_geisoleerd else "Onbekend"),
                       opmerkingen="Dakkapel %d — linkerwang" % nr)
    wang_r = SchilDeel(id="dakkapel%d-wang-rechts" % nr, type="gevel", subtype="Dakkapel wang",
                       orientatie=zij_r, begrenzing="Buitenlucht", oppervlakte_m2=round(d * h, 2),
                       breedte_m=b, diepte_m=d, hoogte_m=h, moedervlak_id=moeder.id,
                       geometrie_groep="dakkapel%d" % nr, bron="webapp-wizard",
                       rekenzone=rekenzone, isolatie_aanwezig=("Ja" if wangen_geisoleerd else "Onbekend"),
                       opmerkingen="Dakkapel %d — rechterwang" % nr)
    dakje = SchilDeel(id="dakkapel%d-dakje" % nr, type="dak", subtype="plat (dakkapel)",
                      orientatie="", begrenzing="Buitenlucht", oppervlakte_m2=vlakken["dak_m2"],
                      breedte_m=b, diepte_m=d, hoogte_m=h, moedervlak_id=moeder.id,
                      geometrie_groep="dakkapel%d" % nr, bron="webapp-wizard",
                      hellingshoek=0, rekenzone=rekenzone, opmerkingen="Dakkapel %d — plat dakje" % nr)
    dos.schil += [voorvlak, wang_l, wang_r, dakje]
    if gat:
        moeder.oppervlakte_m2 = round(moeder_m2_voor - gat, 2)
    # Een dakkapel snijdt een gat uit het GEKOZEN moederdak — als dat toevallig de placeholder was
    # (bv. via de hybride API+report-PDF-route, taak 014-review), is het na deze correctie geen
    # onaangeroerde schatting meer maar bewust door de adviseur bevestigd/aangepast vlak: niet meer
    # weggooibaar (_dak_fallback_opschonen zou anders dit resterende, nog altijd echte dakoppervlak
    # verwijderen i.p.v. alleen een ongebruikte placeholder).
    if moeder_was_fallback:
        moeder.bron = "magicplan-import"
    _dos_save(tag, st, dos)
    flash("Dakkapel %d toegevoegd: %s. Nog een dakkapel? Herhaal hieronder." % (nr, vlakken["flag"]))
    return redirect(url_for("opname", tag=tag) + "#dak-toevoegen")


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
        export = generate_all.generate_all(dos, outdir, prefix="huidig")
    except Exception as e:
        flash("VABI-export genereren mislukte: %s" % e)
        return redirect(url_for("opname", tag=tag))
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
        for p in glob.glob(os.path.join(export["set_dir"], "*")):
            z.write(p, os.path.basename(p))
    mem.seek(0)
    return Response(mem.read(), mimetype="application/zip",
                    headers={"Content-Disposition": "attachment; filename=vabi_huidig_%s.zip" % tag})


# ---------------- plattegrond uit afbeelding (taak 022) ----------------
PLATTEGROND_IMPORT_TMPL = """{{stepper|safe}}
<h1>Plattegrond uit afbeelding — {{st.adres}}</h1>
<p class=lead><a href="{{url_for('opname', tag=tag)}}">&larr; Terug naar de opname</a></p>
<div class=warn><b>Gegevensbeleid:</b> pas na de knop <i>Afbeeldingen analyseren</i> worden de
gekozen beelden naar Anthropic gestuurd. Gebruik plattegronden zonder namen of andere
persoonsgegevens. De provider/modelversie wordt in het concept vastgelegd.</div>
{% if bestaand %}<div class=warn>Dit dossier bevat al geometrie. De import overschrijft die nooit;
maak hiervoor een leeg project.</div>{% endif %}
<div class=card><h2>1 · Upload in verdiepingvolgorde</h2>
<form method=post action="{{url_for('plattegrond_analyse', tag=tag)}}" enctype=multipart/form-data>
<label>Verdiepingsnamen, één per regel</label><textarea name=verdiepingsnamen required
placeholder="Begane grond&#10;1e verdieping"></textarea>
<label>JPG/PNG-bestanden in exact dezelfde volgorde</label>
<input type=file name=afbeeldingen accept="image/jpeg,image/png" multiple required>
<p class="muted small">Live providercall: alleen na deze expliciete actie. Zonder aantoonbare maatlijn
blijft oppervlakte onbekend en moet die in stap 2 handmatig worden ingevuld.</p>
<button class=btn type=submit {% if bestaand %}disabled{% endif %}>Afbeeldingen analyseren</button>
</form></div>
{% if concept %}<div class=card><h2>2 · Controleren en corrigeren</h2>
{% if concept.aandachtspunten %}<div class=warn><b>Aandachtspunten</b><ul>{% for a in concept.aandachtspunten %}<li>{{a}}</li>{% endfor %}</ul></div>{% endif %}
<p>Controleer iedere naam, functie, oppervlakte, contour en verbinding. In JSON zijn alle waarden
corrigeerbaar; <code>null</code>-oppervlakten moeten vóór bevestiging een gemeten waarde krijgen.</p>
<form method=post action="{{url_for('plattegrond_bevestig', tag=tag)}}">
<textarea name=bevestiging_json rows=28 required>{{bevestiging_json}}</textarea>
<label><input type=checkbox name=expliciet_bevestigd value=ja required> Ik heb elke waarde en alle onzekerheden gecontroleerd.</label>
<button class=btn type=submit>Gecontroleerde geometrie opslaan</button></form></div>{% endif %}
"""


def _pi_concept_pad(tag):
    return os.path.join(_pdir(tag), "plattegrond_import", "concept.json")


def _pi_bevestiging(concept):
    return {"expliciet_bevestigd": True, "verdiepingen": [{
        "bron_volgorde": v["volgorde"], "naam": v["naam"], "ruimtes": [{
            "naam": r["naam"], "functie": r["functie"], "oppervlakte_m2": r["oppervlakte_m2"],
            "contour_relatief": r["contour_relatief"], "aangrenzend": r["aangrenzend"]}
            for r in v["ruimtes"]]} for v in concept["verdiepingen"]]}


@app.route("/project/<tag>/plattegrond-import")
@login_required
def plattegrond_import_pagina(tag):
    st, dos = _load_state(tag), _dossier(tag)
    if not st or not dos:
        abort(404)
    concept = None
    try:
        with open(_pi_concept_pad(tag), encoding="utf-8") as fh:
            concept = json.load(fh)
    except (OSError, ValueError):
        pass
    bevestiging = json.dumps(_pi_bevestiging(concept), ensure_ascii=False, indent=2) if concept else ""
    return page(PLATTEGROND_IMPORT_TMPL, stepper=stepper("opname", st), tag=tag, st=st,
                concept=concept, bevestiging_json=bevestiging,
                bestaand=bool(dos.geometrie.vloeren or dos.geometrie.ruimtes))


@app.route("/project/<tag>/plattegrond-import/analyse", methods=["POST"])
@login_required
def plattegrond_analyse(tag):
    st, dos = _load_state(tag), _dossier(tag)
    if not st or not dos:
        abort(404)
    if dos.geometrie.vloeren or dos.geometrie.ruimtes:
        flash("Bestaande geometrie wordt niet overschreven; gebruik een leeg project.")
        return redirect(url_for("plattegrond_import_pagina", tag=tag))
    uploads = [f for f in request.files.getlist("afbeeldingen") if f and f.filename]
    namen = [x.strip() for x in request.form.get("verdiepingsnamen", "").splitlines() if x.strip()]
    if not uploads or len(uploads) != len(namen) or len(set(namen)) != len(namen):
        flash("Geef voor elk bestand precies één unieke verdiepingsnaam in dezelfde volgorde.")
        return redirect(url_for("plattegrond_import_pagina", tag=tag))
    root = os.path.join(_pdir(tag), "plattegrond_import")
    os.makedirs(root, exist_ok=True)
    beelden = []
    try:
        for i, (vloer_naam, upload) in enumerate(zip(namen, uploads), 1):
            data = upload.read(pi_mod.MAX_AFBEELDING_BYTES + 1)
            media = pi_mod.valideer_afbeeldingsbytes(upload.filename, data)
            ext = ".png" if media == "image/png" else ".jpg"
            bestand = "%02d-%s%s" % (i, re.sub(r"[^a-z0-9]+", "-", vloer_naam.lower()).strip("-") or "vloer", ext)
            with open(os.path.join(root, bestand), "wb") as fh:
                fh.write(data)
            beelden.append((bestand, data))
        raw = pi_mod.analyseer_met_anthropic(beelden, _cfg())
        if len(raw.get("verdiepingen") or []) != len(namen):
            raise pi_mod.PlattegrondImportFout("Providerantwoord bevat niet precies elke geüploade verdieping.")
        # De adviseursnamen en uploadvolgorde zijn leidend, nooit de provider.
        for i, vloer in enumerate(raw.get("verdiepingen") or []):
            vloer["naam"], vloer["afbeelding"] = namen[i], "plattegrond_import/" + beelden[i][0]
        concept = pi_mod.valideer_vision_resultaat(raw, _pdir(tag))
        with open(_pi_concept_pad(tag), "w", encoding="utf-8") as fh:
            json.dump(concept, fh, ensure_ascii=False, indent=2)
        flash("Analyse ontvangen. Controleer en corrigeer nu iedere waarde vóór bevestiging.")
    except pi_mod.PlattegrondImportFout as exc:
        flash(str(exc))
    return redirect(url_for("plattegrond_import_pagina", tag=tag))


@app.route("/project/<tag>/plattegrond-import/bevestig", methods=["POST"])
@login_required
def plattegrond_bevestig(tag):
    st, dos = _load_state(tag), _dossier(tag)
    if not st or not dos:
        abort(404)
    try:
        with open(_pi_concept_pad(tag), encoding="utf-8") as fh:
            concept = json.load(fh)
        bevestiging = json.loads(request.form.get("bevestiging_json", ""))
        bevestiging["expliciet_bevestigd"] = request.form.get("expliciet_bevestigd") == "ja"
        pi_mod.bevestig_in_dossier(dos, concept, bevestiging)
        _dos_save(tag, st, dos)
        flash("Gecontroleerde plattegrondgeometrie opgeslagen.")
        return redirect(url_for("ventilatieplan_pagina", tag=tag))
    except (OSError, ValueError, pi_mod.PlattegrondImportFout) as exc:
        flash("Bevestigen mislukt: %s" % str(exc)[:180])
        return redirect(url_for("plattegrond_import_pagina", tag=tag))


# ---------------- ventilatieplan (taak 020: sleepbare pijlen op de plattegrond) ----------------
VENTILATIEPLAN_TMPL = """{{stepper|safe}}
<h1>Ventilatieplan — {{st.adres}}</h1>
<p class=lead><a href="{{url_for('opname', tag=tag)}}">&larr; Terug naar de opname</a></p>
<div class="btn-row vp-balansrij">
<span id=vp-balans class="pill {{'green' if balans.sluitend else 'amber'}}">
Balans: toevoer {{'%.1f'|format(balans.toevoer)}} l/s {{'=' if balans.sluitend else '≠'}} afvoer {{'%.1f'|format(balans.afvoer)}} l/s</span>
<button type=button class="btn sec" id=vp-herbereken>Herbereken balans</button>
<a class="btn" href="{{url_for('ventilatieplan_pdf', tag=tag)}}">Download ventilatieplan (PDF)</a>
</div>
<p class="muted small">De tekening is leidend voor de balans hierboven — je kunt een marker bijstellen naar een
échte roostercapaciteit. De tabellen rechts komen rechtstreeks uit de rekenlaag (Nij Begun-vuistregels) en
veranderen niet mee; ze zijn het uitgangspunt waarmee de tekening is voorgevuld.</p>

<div class=vp-layout>
<div class=vp-verdiepingen>
<h2>Plan per verdieping</h2>
{% for v in verdiepingen_json %}
<div class=card>
<h3>{{v.naam}}
{% if v.ruimtes %}<select class=vp-ruimte-kiezer data-verdieping="{{v.naam}}">
{% for r in v.ruimtes %}<option value="{{r.naam}}">{{r.naam}}</option>{% endfor %}
</select>{% endif %}
</h3>
<div class=vp-canvas-wrap>
<svg class=vp-canvas viewBox="0 0 1000 750" data-verdieping="{{v.naam}}" data-soort="{{v.achtergrond_soort}}">
<rect x=0 y=0 width=1000 height=750 fill="var(--card)"></rect>
{% if v.achtergrond_soort == 'afbeelding' %}<image href="{{v.achtergrond_url}}" x=0 y=0 width=1000 height=750 preserveAspectRatio="xMidYMid meet"></image>
{% elif v.achtergrond_soort == 'contour' %}<polygon points="{% for p in v.contour_punten %}{{'%.1f'|format(p[0]*1000)}},{{'%.1f'|format(p[1]*750)}} {% endfor %}" fill="var(--tint)" stroke="var(--sub)" stroke-width=2></polygon>
{% else %}<text class=vp-empty x=500 y=375 text-anchor=middle>Geen plattegrond beschikbaar</text>{% endif %}
<g class=vp-ruimtes>
{% for r in v.ruimtes if r.contour %}<polygon class=vp-ruimte data-ruimte-id="{{r.naam}}" points="{% for p in r.contour %}{{'%.1f'|format(p[0]*1000)}},{{'%.1f'|format(p[1]*750)}} {% endfor %}"></polygon>
<text class=vp-ruimtelabel data-ruimte-id="{{r.naam}}" x="{{'%.1f'|format(r.label[0]*1000)}}" y="{{'%.1f'|format(r.label[1]*750)}}">{{r.naam}}</text>{% endfor %}
</g>
<line class=vp-koppellijn></line>
<g class=vp-markers></g>
</svg>
</div>
{% if v.heeft_ruimtegeometrie %}<p class="muted small">Slepen = verplaatsen · klik = 90° draaien · dubbelklik = waarde wijzigen of splitsen</p>
{% else %}<p class="warn">Ruimtecontouren ontbreken. Markers blijven via de ruimtekeuze gekoppeld; slepen is geblokkeerd tot gemeten ruimtegeometrie beschikbaar is.</p>{% endif %}
<div class=btn-row>
<button type=button class="btn sec vp-add" data-type=toevoer data-verdieping="{{v.naam}}">+ Toevoer</button>
<button type=button class="btn sec vp-add" data-type=afvoer data-verdieping="{{v.naam}}">+ Afvoer</button>
<span class=spacer></span>
<a class="btn sec" href="{{url_for('ventilatieplan_png', tag=tag, verdieping=v.naam)}}">Download plan (PNG)</a>
<button type=button class="btn sec vp-herstel" data-verdieping="{{v.naam}}">Herstel</button>
</div>
<details class=vp-instellen><summary>Ruimtecontouren kalibreren</summary>
<p class="muted small">Kies een ruimte, klik minimaal drie punten op de bestaande plattegrond en sla op. De preview is pas definitief na opslaan.</p>
<div class=btn-row><select class=vp-kalibratie-ruimte data-verdieping="{{v.naam}}">{% for r in v.ruimtes %}<option value="{{r.naam}}">{{r.naam}}</option>{% endfor %}</select>
<button type=button class="btn sec vp-kalibratie-start" data-verdieping="{{v.naam}}">Contour tekenen</button>
<button type=button class="btn sec vp-kalibratie-wis" data-verdieping="{{v.naam}}">Punten wissen</button>
<button type=button class="btn vp-kalibratie-save" data-verdieping="{{v.naam}}">Ruimtecontouren opslaan</button></div>
<p class="muted small vp-kalibratie-status" data-verdieping="{{v.naam}}" aria-live=polite></p>
</details>
<details class=vp-instellen><summary>Overstroomverbinding vastleggen</summary>
<p class="muted small">Leg expliciet vast van welke toevoerruimte de lucht naar welke natte ruimte stroomt. Zonder verbinding blijft de toets niet te bepalen en verschijnt geen groene pijl.</p>
<div class=btn-row><select class=vp-topologie-bron data-verdieping="{{v.naam}}">{% for r in v.ruimtes if r.toevoer %}<option value="{{r.naam}}">{{r.naam}}</option>{% endfor %}</select>
<span aria-hidden=true>→</span><select class=vp-topologie-doel data-verdieping="{{v.naam}}">{% for r in v.ruimtes if r.afvoerpunt %}<option value="{{r.naam}}">{{r.naam}}</option>{% endfor %}</select>
<button type=button class="btn vp-topologie-save" data-verdieping="{{v.naam}}">Verbinding toevoegen</button></div>
</details>
</div>
{% endfor %}
<div class=card><h3>Legenda</h3>
<div class=btn-row>
<span class=vp-legenda><svg width=18 height=18><path d="M9 1 L17 15 L1 15 Z" fill="var(--blue)"></path></svg> toevoer</span>
<span class=vp-legenda><svg width=18 height=18><ellipse cx=9 cy=9 rx=8 ry=6 fill="var(--orange)"></ellipse></svg> afvoer</span>
<span class=vp-legenda><svg width=18 height=18><path d="M9 1 L17 15 L1 15 Z" fill="var(--green)"></path></svg> overstroom</span>
</div></div>
</div>

<div class=vp-berekening>
<h2>Berekening</h2>
<div class=card><h3>Toevoer per verblijfsruimte</h3>
<div class=table-wrap><table><thead><tr><th>Ruimte</th><th>M2</th><th>Min. l/s</th><th>Advies l/s</th></tr></thead><tbody>
{% for r in res.rows %}{% if r.toevoer %}<tr><td data-label=Ruimte>{{r.naam}}</td><td data-label=M2>{{'%.1f'|format(r.opp)}}</td>
<td data-label="Min. l/s">{{'%.1f'|format(r.toevoer)}}</td><td data-label="Advies l/s"><b>{{'%.1f'|format(r.toevoer)}}</b></td></tr>{% endif %}{% endfor %}
</tbody></table></div></div>
<div class=card><h3>Afvoer per natte ruimte</h3>
<div class=table-wrap><table><thead><tr><th>Ruimte</th><th>Min. l/s</th><th>Advies l/s</th><th>Afvoerpunt</th></tr></thead><tbody>
{% for r in res.rows %}{% if r.afvoerpunt %}<tr><td data-label=Ruimte>{{r.naam}}</td><td data-label="Min. l/s">{{'%.1f'|format(r.afvoer)}}</td>
<td data-label="Advies l/s"><b>{{'%.1f'|format(r.afvoer_advies_ls)}}</b>{% if r.afvoer_herkomst == 'balansophoging' %} <span class="pill gray" title="Opgehoogd om de balans te sluiten (taak 019)">↑</span>{% endif %}</td>
<td data-label=Afvoerpunt>Ja</td></tr>{% endif %}{% endfor %}
</tbody></table></div></div>
<div class=card><h3>Vuistregels</h3>
<ul class=vp-vuistregels>
{% for t in toets %}<li><span class="pill {{'green' if t.status=='voldoet' else ('amber' if t.status=='niet te bepalen' else 'red')}}">{{t.status}}</span> {{t.regel}}
<span class="muted small">{{t.reden}}</span></li>{% endfor %}
</ul>
{% if res.waarschuwingen %}<div class=warn>{% for w in res.waarschuwingen %}<p>{{w}}</p>{% endfor %}</div>{% endif %}
</div>
</div>
</div>

<script src="{{url_for('static', filename='ventilatieplan.js')}}"></script>
<script>
window.VP_TAG = {{tag|tojson}};
window.VP_MARKER_TYPES = {{marker_types|tojson}};
window.VP_VERDIEPINGEN = {{verdiepingen_json|tojson}};
document.addEventListener('DOMContentLoaded', function(){ ventilatieplanInit(); });
</script>
"""


def _vp_context(tag, dos):
    """Bouwt de rekenlaag (taak 019) + de tekendata (taak 020) voor één keer op, gedeeld door de
    GET-pagina en de POST-routes (die na een wijziging dezelfde balans teruggeven)."""
    import dataclasses
    res = vent_verdeel_balans(vent_bereken(dos.geometrie.ruimtes))
    dos.ventilatieplan.systeem = dos.ventilatie.systeem   # gespiegeld, geen eigen bron van waarheid
    gewijzigd = vp_mod.zorg_voor_verdiepingen(dos, res["rows"])
    by_naam = {r["naam"]: r for r in res["rows"]}
    groepen = {naam: ruimtes for naam, _vloer, ruimtes in vp_mod.groepeer_per_verdieping(dos)}
    vloeren = {naam: vloer for naam, vloer, _r in vp_mod.groepeer_per_verdieping(dos)}
    verdiepingen_json = []
    for v in dos.ventilatieplan.verdiepingen:
        vloer = vloeren.get(v.naam)
        pad, soort = vp_mod.achtergrond_van(vloer)
        ruimtes_json = [{"naam": r.naam, "toevoer": (by_naam.get(r.naam) or {}).get("toevoer", 0.0),
                         "afvoer": (by_naam.get(r.naam) or {}).get("afvoer_advies_ls",
                                    (by_naam.get(r.naam) or {}).get("afvoer", 0.0)),
                         "afvoerpunt": bool((by_naam.get(r.naam) or {}).get("afvoerpunt")),
                         "contour": r.contour_relatief,
                         "label": vp_mod.polygoon_middelpunt(r.contour_relatief)}
                        for r in groepen.get(v.naam, [])]
        verdiepingen_json.append({
            "naam": v.naam,
            "achtergrond_soort": soort,
            "achtergrond_url": url_for("download", tag=tag, filename=pad) if pad else None,
            "contour_punten": vp_mod.contour_punten_relatief(vloer),
            "markers": [dataclasses.asdict(m) for m in v.markers],
            "ruimtes": ruimtes_json,
            "heeft_ruimtegeometrie": bool(ruimtes_json) and all(r["contour"] for r in ruimtes_json),
        })
    return res, gewijzigd, verdiepingen_json


@app.route("/project/<tag>/ventilatieplan")
@login_required
def ventilatieplan_pagina(tag):
    st = _load_state(tag)
    dos = _dossier(tag)
    if not st or not dos:
        abort(404)
    if not dos.geometrie.ruimtes:
        flash("Nog geen ruimtes in de opname — vul eerst de opname in voordat je het ventilatieplan tekent.")
        return redirect(url_for("opname", tag=tag))
    res, gewijzigd, verdiepingen_json = _vp_context(tag, dos)
    if gewijzigd:
        _dos_save(tag, st, dos)
    balans = vp_mod.marker_balans(dos)
    # UI/dossier bewaart begrijpelijk bron(toevoer)->doel(nat). Het rekencontract van
    # deurbelasting() begint juist bij de natte afvoer; transformeer expliciet op deze grens.
    rekentopologie = [[pad[1], pad[0]] for pad in dos.ventilatieplan.topologie if len(pad) == 2]
    toets = vent_toets_vuistregels(res, {"topologie": rekentopologie})
    return page(VENTILATIEPLAN_TMPL, stepper=stepper("opname", st), tag=tag, st=st, d=dos,
                res=res, balans=balans, toets=toets, verdiepingen_json=verdiepingen_json,
                marker_types=vp_mod.MARKER_TYPES)


def _vp_export_scene(tag, st, dos):
    """Exact dezelfde scene en rekentabellen als de schermroute, gereed voor beide exports."""
    res, gewijzigd, verdiepingen = _vp_context(tag, dos)
    if gewijzigd:
        _dos_save(tag, st, dos)
    balans = vp_mod.marker_balans(dos)
    rekentopologie = [[pad[1], pad[0]] for pad in dos.ventilatieplan.topologie if len(pad) == 2]
    toets = vent_toets_vuistregels(res, {"topologie": rekentopologie})
    vloeren = {naam: vloer for naam, vloer, _ruimtes in vp_mod.groepeer_per_verdieping(dos)}
    projectmap = os.path.realpath(_pdir(tag))
    for verdieping in verdiepingen:
        vloer = vloeren.get(verdieping["naam"])
        bron = (getattr(vloer, "plattegrond_afbeelding", None) or "") if vloer else ""
        if not bron:
            continue
        # Alleen een lokaal projectbestand; URL's, absolute paden en traversal worden nooit gelezen.
        if "://" in bron or os.path.isabs(bron):
            raise ValueError("Plattegrondachtergrond moet een lokaal projectbestand zijn.")
        pad = os.path.realpath(os.path.join(projectmap, bron))
        try:
            binnen_project = os.path.commonpath([projectmap, pad]) == projectmap
        except ValueError:
            binnen_project = False
        if not binnen_project or not os.path.isfile(pad):
            raise ValueError("Plattegrondachtergrond bestaat niet binnen dit project.")
        if os.path.getsize(pad) > 25 * 1024 * 1024:
            raise ValueError("Plattegrondachtergrond is groter dan 25 MB.")
        with open(pad, "rb") as fh:
            data = fh.read()
        if not (data.startswith(b"\x89PNG\r\n\x1a\n") or data.startswith(b"\xff\xd8\xff")):
            raise ValueError("Plattegrondachtergrond is geen geldige PNG of JPEG.")
        verdieping["achtergrond_data"] = data
    return vp_export.scene(verdiepingen, res, balans, toets, st.get("adres", ""),
                           dos.ventilatie.systeem, vp_export.opname_datum(dos))


@app.route("/project/<tag>/ventilatieplan/export.pdf")
@login_required
def ventilatieplan_pdf(tag):
    st, dos = _load_state(tag), _dossier(tag)
    if not st or not dos:
        abort(404)
    try:
        data = _vp_export_scene(tag, st, dos)
    except ValueError as exc:
        flash(str(exc))
        return redirect(url_for("ventilatieplan_pagina", tag=tag))
    if not data["verdiepingen"]:
        flash("Geen plattegrond beschikbaar — voeg eerst een vloercontour of ruimtecontouren toe.")
        return redirect(url_for("ventilatieplan_pagina", tag=tag))
    naam = "ventilatieplan-%s.pdf" % vp_export.bestands_slug(st.get("adres"))
    try:
        inhoud = vp_export.pdf(data)
    except ValueError as exc:
        flash("Plattegrond kon niet worden geëxporteerd: %s" % exc)
        return redirect(url_for("ventilatieplan_pagina", tag=tag))
    return Response(inhoud, mimetype="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=%s" % naam})


@app.route("/project/<tag>/ventilatieplan/<verdieping>/export.png")
@login_required
def ventilatieplan_png(tag, verdieping):
    st, dos = _load_state(tag), _dossier(tag)
    if not st or not dos:
        abort(404)
    try:
        data = _vp_export_scene(tag, st, dos)
    except ValueError as exc:
        abort(422, description=str(exc))
    vloer = next((v for v in data["verdiepingen"] if v["naam"] == verdieping), None)
    if vloer is None:
        abort(404, description="Geen plattegrond beschikbaar voor deze verdieping.")
    naam = "ventilatieplan-%s-%s.png" % (vp_export.bestands_slug(st.get("adres")),
                                         vp_export.bestands_slug(verdieping))
    try:
        inhoud = vp_export.verdieping_png(vloer)
    except ValueError as exc:
        abort(422, description="Plattegrond kon niet worden geëxporteerd: %s" % exc)
    return Response(inhoud, mimetype="image/png",
                    headers={"Content-Disposition": "attachment; filename=%s" % naam})


@app.route("/project/<tag>/ventilatieplan/<verdieping>/markers", methods=["POST"])
@login_required
def ventilatieplan_markers(tag, verdieping):
    st = _load_state(tag)
    dos = _dossier(tag)
    if not st or not dos:
        abort(404)
    v = next((v for v in dos.ventilatieplan.verdiepingen if v.naam == verdieping), None)
    if v is None:
        return {"ok": False, "fout": "Onbekende verdieping '%s'." % verdieping}, 404
    data = request.get_json(silent=True) or {}
    geldig = vp_mod.geldige_ruimtenamen_op_verdieping(dos, verdieping)
    contouren = vp_mod.ruimtecontouren_op_verdieping(dos, verdieping)
    markers, fout = vp_mod.valideer_markers(data.get("markers") or [], geldig, contouren)
    if fout:
        return {"ok": False, "fout": fout}, 400
    v.markers = markers
    _dos_save(tag, st, dos)
    return {"ok": True, "balans": vp_mod.marker_balans(dos)}


@app.route("/project/<tag>/ventilatieplan/<verdieping>/herstel", methods=["POST"])
@login_required
def ventilatieplan_herstel(tag, verdieping):
    import dataclasses
    st = _load_state(tag)
    dos = _dossier(tag)
    if not st or not dos:
        abort(404)
    res = vent_verdeel_balans(vent_bereken(dos.geometrie.ruimtes))
    v = vp_mod.herstel_verdieping(dos, verdieping, res["rows"])
    if v is None:
        return {"ok": False, "fout": "Onbekende verdieping '%s'." % verdieping}, 404
    _dos_save(tag, st, dos)
    return {"ok": True, "markers": [dataclasses.asdict(m) for m in v.markers],
            "balans": vp_mod.marker_balans(dos)}


@app.route("/project/<tag>/ventilatieplan/<verdieping>/ruimtepolygonen", methods=["POST"])
@login_required
def ventilatieplan_ruimtepolygonen(tag, verdieping):
    st, dos = _load_state(tag), _dossier(tag)
    if not st or not dos:
        abort(404)
    geldig = vp_mod.geldige_ruimtenamen_op_verdieping(dos, verdieping)
    if not geldig:
        return {"ok": False, "fout": "Onbekende verdieping '%s'." % verdieping}, 404
    polygonen, fout = vp_mod.valideer_ruimtepolygonen(
        (request.get_json(silent=True) or {}).get("polygonen"), geldig)
    if fout:
        return {"ok": False, "fout": fout}, 400
    for ruimte in dos.geometrie.ruimtes:
        if ruimte.naam in polygonen:
            ruimte.contour_relatief = polygonen[ruimte.naam]
    _dos_save(tag, st, dos)
    return {"ok": True}


@app.route("/project/<tag>/ventilatieplan/<verdieping>/topologie", methods=["POST"])
@login_required
def ventilatieplan_topologie(tag, verdieping):
    import dataclasses
    st, dos = _load_state(tag), _dossier(tag)
    if not st or not dos:
        abort(404)
    data = request.get_json(silent=True) or {}
    bron, doel = (data.get("bron") or "").strip(), (data.get("doel") or "").strip()
    groepen = {naam: ruimtes for naam, _vloer, ruimtes in vp_mod.groepeer_per_verdieping(dos)}
    ruimtes = groepen.get(verdieping)
    if ruimtes is None:
        return {"ok": False, "fout": "Onbekende verdieping '%s'." % verdieping}, 404
    res = vent_verdeel_balans(vent_bereken(dos.geometrie.ruimtes))
    rows = {r["naam"]: r for r in res["rows"]}
    namen = {r.naam for r in ruimtes}
    if bron not in namen or not (rows.get(bron) or {}).get("toevoer"):
        return {"ok": False, "fout": "Kies een toevoerruimte op deze verdieping."}, 400
    if doel not in namen or not (rows.get(doel) or {}).get("afvoerpunt"):
        return {"ok": False, "fout": "Kies een natte doelruimte op deze verdieping."}, 400
    if [bron, doel] not in dos.ventilatieplan.topologie:
        dos.ventilatieplan.topologie.append([bron, doel])
    v = vp_mod.herstel_verdieping(dos, verdieping, res["rows"])
    _dos_save(tag, st, dos)
    return {"ok": True, "markers": [dataclasses.asdict(m) for m in v.markers],
            "topologie": dos.ventilatieplan.topologie, "balans": vp_mod.marker_balans(dos)}


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
    from core.gedoogbeleid import gedoogbeleid_reminders
    _spouw = any(getattr(s, "spouw_aanwezig", None) is True
                 for s in (dos.schil or []) if getattr(s, "type", "") == "gevel")
    _pc = getattr(getattr(dos, "identificatie", None), "postcode", "") or ""
    return page(MAATREGELEN, stepper=stepper("maatregelen", st), groepen=suggesties(dos, catalog),
                boom=catalogus_boom(catalog), vrij=vrij, vrij_tot=vrij_tot, tag=tag, st=st,
                gedoog=gedoogbeleid_reminders(_pc, _spouw))


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
                # ook in het dossier zetten (voor validator/validate.py's KWACO-check en het
                # isolatieplan-Word-template V1-V6, die kwh_m2_na_maatregelen al verwachten maar
                # tot nu toe nooit gevuld kregen)
                try:
                    b = dos.berekening
                    b.kwh_m2_na_maatregelen = st["na"].get("behoefte")
                    b.indicator_type_na = st["na"].get("indicator_type") or ""
                    save_json(dos, os.path.join(_pdir(tag), st["dossier_file"]))
                except Exception:
                    pass
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
    current_vabi_set = generate_all.current_set_dir(outdir)
    vabi_files = sorted(os.path.basename(p) for p in glob.glob(os.path.join(current_vabi_set, "*.xml"))) if current_vabi_set else []
    # gewogen verliesoppervlakte Als (NTA 8800 §6.7.3)
    verlies = verliesoppervlak(dos)
    # gevels zijn BRUTO (b x h; ramen/deuren zitten erin) -> kozijnen niet dubbel tellen
    ag = dos.geometrie.gebruiksoppervlakte_ag_m2 or 0
    std_eigen = standaard_eis(dos)          # zelf voorgerekend (§5.3.2) -> kruiscontrole met de Vabi-Standaard
    std_vabi = (st.get("huidig") or {}).get("standaard")
    std_afwijking = None
    if std_eigen is not None and std_vabi is not None:
        std_afwijking = round(abs(std_eigen - float(std_vabi)), 1)   # >2 kWh/m²·jr = geometrie/woningtype nalopen
    return page(VABI, stepper=stepper("vabi", st), tag=tag, vabi_files=vabi_files, na=st.get("na"),
                h=st.get("huidig") or {}, st=st, verlies=verlies, ag=ag, renojaar=renojaar,
                std_eigen=std_eigen, std_afwijking=std_afwijking)


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


# ---------------- export als OneDrive-projectmap ----------------
# De zip is bewust een COMPLETE projectmap en niet een hoop losse bestanden: pak 'm uit in OneDrive
# en je hebt meteen de map waarin je zelf mailverkeer, facturen en aanvullende stukken kwijt kunt.
# De nummering houdt de mappen in de juiste volgorde in Verkenner/Finder.
ONEDRIVE_MAPPEN = [
    ("01_Opname", "MagicPlan-export en het opnamedossier (de ruwe woninggegevens)."),
    ("02_VABI", "Wat je in Vabi EPA-W importeert en wat je eruit exporteert (huidige + toekomstige staat)."),
    ("03_Isolatieplan", "Het plan zelf: Word/PDF, plan-JSON, ventilatieplan, berekeningen en checklists."),
    ("04_Fotos", "Foto's van de opname (voorkant + huisnummer verplicht voor het dossier)."),
    ("05_Correspondentie", "LEEG — hier zet je zelf het mailverkeer met de bewoner en Nij Begun in."),
    ("06_Facturen", "LEEG — hier zet je zelf de voorschot- en eindfactuur in."),
    ("07_Overig", "Eigen bijlagen en overige stukken."),
]


def _onedrive_map(bestand, submap=""):
    """Bepaal in welke projectmap een bestand hoort. Onbekend -> 07_Overig (nooit weglaten:
    een bestand kwijtraken bij de export is erger dan het in de verkeerde map zetten)."""
    if submap == "fotos":
        return "04_Fotos"
    if submap in ("vabi_huidig", "vabi_na"):
        return "02_VABI/" + ("huidige_staat" if submap == "vabi_huidig" else "toekomstige_staat")
    if submap == "bijlagen":
        return "07_Overig"
    n = bestand.lower()
    if n.startswith("dossier_") or n.endswith(".csv"):
        return "01_Opname"
    if n.startswith("vabi_export") or n.endswith(".xml"):
        return "02_VABI"
    if n.startswith("foto_"):
        return "04_Fotos"
    if n.startswith(("isolatieplan_", "ventilatie", "fotochecklist_", "haalbaarheid_", "rapport_",
                     "beoordeling")):
        return "03_Isolatieplan"
    return "07_Overig"


def _leesmij(adres, tag):
    r = ["PROJECTMAP — %s" % adres, "=" * (14 + len(adres)), "",
         "Gemaakt door de Nij Begun isolatieplan-tool op %s." % datetime.date.today().strftime("%d-%m-%Y"),
         "Projectcode: %s" % tag, "",
         "Zet deze map in OneDrive. Je mag er zelf van alles aan toevoegen — de tool leest deze map",
         "niet terug, dus je kunt niets stukmaken. Bij een volgende export krijg je opnieuw een",
         "complete map; wat jij zelf hebt toegevoegd zit daar NIET in, dus voeg nieuwe bestanden toe",
         "in plaats van de oude map te vervangen.", "", "INHOUD", "------"]
    for naam, uitleg in ONEDRIVE_MAPPEN:
        r += ["%-20s %s" % (naam + "/", uitleg)]
    r += ["", "BEWAARTERMIJN", "-------------",
          "Het projectdossier (BRL 9500-W, Bijlage 3) moet 15 jaar bewaard blijven.",
          "AVG: deze map bevat adresgegevens — deel 'm niet zonder reden en bewaar 'm in de",
          "zakelijke OneDrive (EU), niet op een privéschijf."]
    return "\n".join(r) + "\n"


def _vabi_publicatiebestanden(pdir, submap):
    """Actuele manifestset, of een legacy vlakke export van vóór taak 017."""
    outdir = os.path.join(pdir, submap)
    current = generate_all.current_set_dir(outdir)
    bron = current or outdir
    return [p for p in sorted(glob.glob(os.path.join(bron, "*"))) if os.path.isfile(p)]


@app.route("/project/<tag>/export")
@login_required
def export(tag):
    pdir = _pdir(tag)
    if not os.path.isdir(pdir):
        abort(404)
    st = _load_state(tag) or {}
    adres = st.get("adres") or tag
    # bovenste map in de zip = het adres, leesbaar: 'Testweg 5, Stadskanaal' -> 'Testweg 5 - Stadskanaal'
    wortel = _veilige_naam(re.sub(r"\s+", " ", adres.replace(",", " -").replace("/", "-"))) or tag
    gevuld = set()

    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
        def leg_in(pad, submap=""):
            naam = os.path.basename(pad)
            doel = _onedrive_map(naam, submap)
            gevuld.add(doel.split("/")[0])
            z.write(pad, "%s/%s/%s" % (wortel, doel, naam))

        for p in sorted(glob.glob(os.path.join(pdir, "*"))):
            if os.path.isfile(p) and not p.endswith("project.json"):   # project.json = interne status
                leg_in(p)
        for sub in ("vabi_huidig", "vabi_na", "fotos", "bijlagen"):
            bestanden = (_vabi_publicatiebestanden(pdir, sub) if sub.startswith("vabi_")
                          else sorted(glob.glob(os.path.join(pdir, sub, "*"))))
            for p in bestanden:
                if os.path.isfile(p):
                    leg_in(p, sub)

        # lege mappen overleven een zip niet: geef ze een uitleg-bestandje mee, anders mist
        # '05_Correspondentie' straks precies daar waar jij je mail kwijt wilt
        for naam, uitleg in ONEDRIVE_MAPPEN:
            if naam not in gevuld:
                z.writestr("%s/%s/_deze map is nog leeg.txt" % (wortel, naam),
                           "%s\n\n%s\n\nDit bestandje staat er alleen zodat de map in de zip blijft "
                           "bestaan; je mag het weggooien.\n" % (naam, uitleg))
        z.writestr("%s/LEESMIJ.txt" % wortel, _leesmij(adres, tag))

    mem.seek(0)
    return Response(mem.read(), mimetype="application/zip",
                    headers={"Content-Disposition": 'attachment; filename="%s.zip"' % wortel})


@app.route("/download/<tag>/<path:filename>")
@login_required
def download(tag, filename):
    pdir = _pdir(tag)
    if ".." in filename or not os.path.isdir(pdir):
        abort(404)
    delen = filename.replace("\\", "/").split("/")
    if len(delen) == 2 and delen[0] in ("vabi_huidig", "vabi_na"):
        bestanden = _vabi_publicatiebestanden(pdir, delen[0])
        match = next((p for p in bestanden if os.path.basename(p) == delen[1]), None)
        if not match:
            abort(404)
        return send_from_directory(os.path.dirname(match), os.path.basename(match), as_attachment=True)
    # bijlagen staan in de submap bijlagen/ — daar ook zoeken als het bestand niet in de root staat
    if not os.path.isfile(os.path.join(pdir, filename)) and os.path.isfile(os.path.join(pdir, "bijlagen", filename)):
        return send_from_directory(os.path.join(pdir, "bijlagen"), filename, as_attachment=True)
    return send_from_directory(pdir, filename, as_attachment=True)


# ---------------- leads (Nij Begun-portal-toewijzingen) ----------------
LEADS = """<h1>Leads</h1>
<p class=lead>Toegewezen bewoners uit het Nij Begun-portal — haal de mails op, volg de status, genereer de kennismakingsmail.</p>
<div class=card><h2>📥 Mails ophalen uit je mailbox</h2>
{% if mailbox_klaar %}
<p class=muted>Haalt de <b>{{mailbox_onderwerp}}</b>-mails van de afgelopen <b>{{mailbox_dagen}} dagen</b> op uit
<b>{{mailbox_gebruiker}}</b> ({{mailbox_map}}) en maakt er leads van. Dubbelen worden overgeslagen, dus je mag
gerust vaker klikken. De tool <b>leest alleen</b> — er wordt niets gemarkeerd, verplaatst of verwijderd.</p>
<form method=post action="{{url_for('leads_ophalen')}}"
      onsubmit="var b=this.querySelector('button');b.disabled=true;b.textContent='⏳ Bezig met ophalen…';">
<div class=btn-row><button class="btn lg">📥 Nieuwe portal-mails ophalen</button>
<span class="pill gray" title="Welke koppeling wordt gebruikt">{{'Microsoft Graph' if mailbox_bron=='graph' else 'IMAP'}}</span></div>
<p class="muted small" style="margin:8px 0 0">Het ophalen duurt <b>vijf tot vijftien seconden</b> — de knop
wacht op Microsoft. Even geduld, niet nog een keer tikken.</p></form>
{% else %}
<p class=muted>Nog niet ingesteld. Voor het <b>gedeelde info@-postvak</b> (Microsoft 365) is dit een blok
<code>"graph"</code> in <b>config.json</b> — je beheerder maakt daarvoor een app-registratie aan; de
volledige instructie voor hem staat in <b>docs/microsoft-graph-mailkoppeling.md</b>. Een gewoon postvak
kan ook via IMAP (blok <code>"mailbox"</code>). Zolang er niets staat, blijft slepen en plakken werken.</p>
{% endif %}</div>
<div class=card><h2>Handmatig toevoegen</h2>
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
<a class="btn sec" href="{{url_for('mails')}}" title="De drie bewonersmails nalezen">✉ Alle mails</a>
<a class="btn sec" href="{{url_for('leads_csv')}}">⬇ CSV</a></div></form></div>
{% if leads %}<div class=card><h2>{{leads|length}} lead(s)</h2>
<div class=lead-filters>
<input id=zoek type=search placeholder="Zoek op naam, adres, e-mail of telefoon…" aria-label="Leads zoeken">
<select id=statusfilter aria-label="Filter op status"><option value="">Alle statussen</option>
{% for s in statussen %}<option value="{{s}}">{{s}}</option>{% endfor %}</select></div>
<p class="muted small" id=filtermelding hidden></p>

<div class=lead-grid>
{% for l in leads %}
<article class="lead-card{{' is-klaar' if l.status in ('afgerond','vervallen') else ''}}"
         data-lid="{{l.id}}" data-status="{{l.status}}" data-zoek="{{(l.naam ~ ' ' ~ l.adres ~ ' ' ~ (l.email or '') ~ ' ' ~ (l.telefoon or ''))|lower}}">
  <header class=lead-kop>
    <div class=lead-titel><h3>{{l.naam}}</h3><p class=lead-adres>{{l.adres}}</p></div>
    <span class="pill {{l.pill}}">{{l.status}}</span>
  </header>

  <div class=lead-feiten>
    {% if l.bouwjaar %}<span class="pill blue" title="Bouwjaar volgens de BAG">{{l.bouwjaar}}</span>
      <span class="pill gray" title="Gebruiksoppervlakte volgens de BAG">{{l.oppervlakte_m2}} m²</span>
    {% else %}<span class="pill gray" title="Nog geen BAG-gegevens — klik op 🏛 om het opnieuw te proberen">BAG onbekend</span>{% endif %}
    <span class="lead-datum muted small" title="Datum binnengekomen">binnen {{l.ontvangen}}</span>
  </div>

  <div class=lead-contact>
    {% if l.telefoon %}<a href="tel:{{l.telefoon}}">📞 {{l.telefoon}}</a>{% endif %}
    {% if l.email %}<a href="mailto:{{l.email}}">✉ {{l.email}}</a>{% endif %}
    {% if not l.telefoon and not l.email %}<span class="muted small">Geen contactgegevens in de portal-mail</span>{% endif %}
  </div>

  <div class=lead-invoer>
    <form method=post action="{{url_for('leads_status', lid=l.id)}}" class=lead-veld>
      <label class="muted small">Status</label>
      <select name=status onchange="this.form.submit()">
      {% for s in statussen %}<option value="{{s}}" {{'selected' if s==l.status else ''}}>{{s}}</option>{% endfor %}
      </select></form>
    <form method=post action="{{url_for('leads_afspraak', lid=l.id)}}" class=lead-veld>
      <label class="muted small">Afspraak{% if l.afspraak_nl %} — {{l.afspraak_nl}}{% endif %}</label>
      <div class=row><input type=datetime-local name=wanneer value="{{l.afspraak or ''}}">
      <button class="btn sec" title="Afspraak opslaan (maakt ook het project aan)">📅</button></div></form>
  </div>

  <div class=lead-acties>
    <a class="btn sec" href="{{url_for('leads_mail', lid=l.id)}}">✉ Kennismaking</a>
    {# ALTIJD tonen — verstopt achter het datumveld was 'ie onvindbaar; zonder datum legt de app het uit #}
    <a class="btn sec" href="{{url_for('leads_mail', lid=l.id)}}?soort=bevestiging"
       title="Afspraak-bevestigingsmail (voorbereiding + verwachtingen)">✉ Bevestiging</a>
    {% if l.project_tag %}<a class="btn green" href="{{url_for('project', tag=l.project_tag)}}" title="Open het gekoppelde project">📂 Project</a>
    {% elif l.status in ('afspraak gepland','opname gedaan','plan ingediend','afgerond') %}
      <form method=post action="{{url_for('leads_project', lid=l.id)}}"><button class="btn" title="Maak een project met dit adres en ga naar de opname">➕ Project</button></form>{% endif %}
    <span class=spacer></span>
    {% if not l.bouwjaar %}<form method=post action="{{url_for('leads_bag', lid=l.id)}}"><button class="btn sec" title="Straat, bouwjaar en m² alsnog uit de BAG halen">🏛</button></form>{% endif %}
    <form method=post action="{{url_for('leads_weg', lid=l.id)}}" onsubmit="return confirm('Deze lead DEFINITIEF verwijderen (naam, adres, e-mail, telefoon)? Dit kan niet ongedaan worden gemaakt. Gebruik status \'vervallen\' als je 'm wilt bewaren.')"><button class="btn sec" title="Lead definitief verwijderen — bv. aanvraag geannuleerd (AVG)">🗑</button></form>
  </div>
</article>
{% endfor %}
</div>
<p class="muted small">Status wisselen slaat direct op. Volgorde: nieuw → mail gestuurd → gebeld → afspraak gepland → opname gedaan → plan ingediend → afgerond.</p></div>
<script>
/* Zoeken + statusfilter: puur in de browser, geen herladen. 52 leads blijven zo werkbaar.
   Het filter en de plek waar je werkte OVERLEVEN een statuswijziging: elke wijziging herlaadt de
   pagina (bewust — de server is de waarheid), dus filter in sessionStorage + terugspringen naar
   de kaart die je net aanraakte. Anders zoek je op je telefoon elke lead opnieuw op. */
(function(){
  var zoek=document.getElementById('zoek'), filt=document.getElementById('statusfilter'),
      melding=document.getElementById('filtermelding'), kaarten=[].slice.call(document.querySelectorAll('.lead-card'));
  function pas(){
    var q=(zoek.value||'').toLowerCase().trim(), s=filt.value, n=0;
    kaarten.forEach(function(k){
      var toon=(!q||k.dataset.zoek.indexOf(q)>=0)&&(!s||k.dataset.status===s);
      k.hidden=!toon; if(toon)n++;
    });
    var actief=q||s;
    melding.hidden=!actief;
    melding.textContent=actief?(n+' van '+kaarten.length+' lead(s) getoond'):'';
    try{sessionStorage.setItem('leads_zoek',zoek.value);sessionStorage.setItem('leads_status',s);}catch(e){}
  }
  zoek.addEventListener('input',pas); filt.addEventListener('change',pas);
  try{
    zoek.value=sessionStorage.getItem('leads_zoek')||'';
    filt.value=sessionStorage.getItem('leads_status')||'';
  }catch(e){}
  if(zoek.value||filt.value)pas();
  // onthoud bij elke wijziging (status/afspraak/knop) WELKE kaart het was...
  kaarten.forEach(function(k){
    [].slice.call(k.querySelectorAll('form')).forEach(function(f){
      f.addEventListener('submit',function(){
        try{sessionStorage.setItem('leads_focus',k.dataset.lid);}catch(e){}
      });
    });
  });
  // ...en spring er na het herladen naartoe, met een korte oplichting
  try{
    var terug=sessionStorage.getItem('leads_focus');
    if(terug){
      sessionStorage.removeItem('leads_focus');
      var k=document.querySelector('.lead-card[data-lid="'+terug+'"]');
      if(k&&!k.hidden){k.scrollIntoView({block:'center'});k.classList.add('is-net-gewijzigd');}
    }
  }catch(e){}
})();
</script>
{% else %}<div class=hint>Nog geen leads. Haal je mails op of plak je eerste portal-mail hierboven.</div>{% endif %}
{% if gewist %}<div class=card><h2>Geblokkeerd ({{gewist|length}})</h2>
<p class=muted>Adressen die je bewust hebt verwijderd. Die komen <b>niet</b> terug bij het ophalen van
mails — ook niet als het portaal er opnieuw over mailt. Er is alleen een adres-sleutel bewaard, geen
naam of contactgegevens.</p>
<p class="muted small">{{gewist|join(' · ')}}</p>
<form method=post action="{{url_for('leads_geblokkeerd')}}"
      onsubmit="return confirm('Alle blokkades opheffen? Verwijderde bewoners kunnen dan weer als lead binnenkomen.')">
<div class=btn-row><button class="btn sec">Blokkades opheffen</button></div></form></div>{% endif %}"""

# statuskleur op de leadkaart — in één oogopslag zien waar een lead staat
STATUS_PILL = {
    "nieuw": "blue", "mail gestuurd": "gray", "gebeld": "gray",
    "afspraak gepland": "amber", "opname gedaan": "amber",
    "plan ingediend": "blue", "afgerond": "green", "vervallen": "gray",
}

LEADS_ONTVANGST = """<h1>Ontvangstbevestiging — bulk</h1>
<p class=lead>{{n}} lead(s) met status <b>nieuw</b>. Maak in je mailprogramma één mail: plak de adressen in het
<b>BCC</b>-veld (nooit Aan/CC — AVG!), jezelf in Aan, en plak onderwerp + tekst. Verstuur zelf.</p>
<div class=card><h2>BCC-adressen ({{n}})</h2><textarea rows=4 id=bcc readonly>{{bcc}}</textarea>
<div class=btn-row><button class="btn sec" type=button onclick="navigator.clipboard.writeText(document.getElementById('bcc').value);this.textContent='✓ Gekopieerd'">Kopieer adressen</button></div></div>
<div class=card><h2>Onderwerp</h2><input readonly value="{{onderwerp}}">
<h2 style="margin-top:14px">Tekst</h2><textarea rows=14 id=body readonly>{{tekst}}</textarea>
<div class=btn-row><button class="btn sec" type=button onclick="navigator.clipboard.writeText(document.getElementById('body').value);this.textContent='✓ Gekopieerd'">Kopieer tekst</button>
<span class=spacer></span>
<form method=post action="{{url_for('leads_ontvangst_verstuurd')}}" onsubmit="return confirm('Deze {{n}} lead(s) markeren als mail gestuurd?')">
<input type=hidden name=ids value="{{ids}}">
<button class="btn green">✓ Verstuurd — markeer deze {{n}}</button></form>
<a class="btn ghost" href="{{url_for('leads_pagina')}}">← terug</a></div></div>"""

LEAD_MAIL = """<h1>{{'Afspraakbevestiging' if soort=='bevestiging' else 'Kennismakingsmail'}} — {{l.naam}}</h1>
<p class=lead>Concept. Kopieer of open 'm in je mailprogramma, lees 'm even na en <b>verstuur zelf</b>.</p>
<div class=hint>⚠ "Open in mailprogramma" opent je <b>standaard-mailaccount</b> — dat bepaalt je telefoon,
niet deze webapp. Opent hij in je persoonlijke account? Wissel dan in het opstelvenster het
<b>Van</b>-adres naar info@poortinga-energieadvies.nl (in de Outlook-app: tik op je adres in het
Van-veld), of zet info@ als standaardaccount in de Outlook-instellingen. Of gebruik <b>Kopieer tekst</b>
en plak 'm in een mail die je vanuit info@ start.</div>
<div class=card><div class=kv><dt>Aan</dt><dd>{{l.email or '—'}}</dd>
<dt>Onderwerp</dt><dd>{{onderwerp}}</dd><dt>Telefoon</dt><dd>{{l.telefoon or '—'}}</dd>
{% if soort=='bevestiging' %}<dt>Afspraak</dt><dd><b>{{afspraak_nl}}</b> — klopt dit niet, pas 'm dan eerst aan op de leadkaart (📅)</dd>{% endif %}</div></div>
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
        r["pill"] = STATUS_PILL.get(r.get("status", ""), "gray")
        r["afspraak_nl"] = leads_mod._afspraak_nl(r["afspraak"]) if r.get("afspraak") else ""
    rows.sort(key=lambda r: (r.get("status") in ("afgerond", "vervallen"), -r.get("id", 0)))
    cfg = _cfg()
    bron, inst = _mailbron(cfg)
    return page(LEADS, leads=rows, statussen=leads_mod.STATUSSEN, gewist=leads_mod.load_gewist(),
                mailbox_klaar=bool(bron), mailbox_bron=bron,
                mailbox_map=inst.get("map") or "Postvak IN",
                mailbox_onderwerp=inst.get("onderwerp"), mailbox_dagen=inst.get("dagen"),
                mailbox_gebruiker=inst.get("postvak") or inst.get("gebruiker", ""))


def _mailbron(cfg):
    """Welke mailkoppeling is ingesteld? -> ('graph'|'imap'|None, instellingen).
    Graph gaat voor: dat is de route voor het GEDEELDE info@-postvak (Microsoft 365)."""
    if graph_mod.is_ingesteld(cfg):
        return "graph", graph_mod.instellingen(cfg)
    if mailbox_mod.is_ingesteld(cfg):
        return "imap", mailbox_mod.instellingen(cfg)
    return None, {}


def _leads_toevoegen(tekst):
    """Gedeeld door plakken/uploaden en mail-ophalen. Het portaal stuurt drie soorten mails; we
    handelen ze los af op basis van WijzigingsType:
      - toewijzing  -> nieuwe lead (of contactgegevens bijwerken bij een bekende)
      - annulering  -> bestaande lead op 'vervallen' zetten, zodat je 'm niet meer benadert
    -> dict met de tellingen."""
    gevonden = leads_mod.parse_leads_bulk(tekst)
    if not gevonden:
        return {"nieuw": 0, "dubbel": 0, "geannuleerd": 0, "annul_onbekend": 0}
    nieuwe_ids = []

    def verwerk(rows):
        r = {"nieuw": 0, "dubbel": 0, "geannuleerd": 0, "annul_onbekend": 0}
        for lead in gevonden:
            if leads_mod.is_annulering(lead):
                _, res = leads_mod.annuleer_lead(lead, rows)
                r["geannuleerd" if res == "gevonden" else "annul_onbekend"] += 1
                continue
            _, nieuw = leads_mod.add_lead(lead, rows)     # muteert rows in plaats
            if nieuw:
                r["nieuw"] += 1
                nieuwe_ids.append(rows[-1]["id"])
            else:
                r["dubbel"] += 1
        return r

    res = leads_mod.wijzig(verwerk)
    if nieuwe_ids:
        _bag_verrijk_achtergrond(nieuwe_ids)
    return res


def _annulering_melding(res):
    """Zichtbare terugkoppeling over annuleringen: hoeveel leads op 'vervallen' gezet, en of er een
    annulering binnenkwam voor een adres dat we (nog) niet kennen. -> extra tekst voor de flash."""
    stukjes = []
    if res.get("geannuleerd"):
        stukjes.append("%d annulering(en) verwerkt → op 'vervallen' gezet (niet meer benaderen)"
                       % res["geannuleerd"])
    if res.get("annul_onbekend"):
        stukjes.append("%d annulering(en) voor een onbekend adres — geen lead gevonden om te "
                       "annuleren" % res["annul_onbekend"])
    return (" " + ". ".join(stukjes) + "." if stukjes else "")


@app.route("/leads/ophalen", methods=["POST"])
@login_required
def leads_ophalen():
    """Haal de portal-mails rechtstreeks uit het postvak en maak er leads van."""
    cfg = _cfg()
    bron, _ = _mailbron(cfg)
    if bron == "graph":
        teksten, fout = graph_mod.haal_teksten(cfg)
    else:
        teksten, fout = mailbox_mod.haal_teksten(cfg)
    if fout:
        flash(fout)
        return redirect(url_for("leads_pagina"))
    if not teksten:
        flash("Geen portal-mails gevonden in de ingestelde periode. Staat het onderwerp-filter goed, "
              "en kijk je in de juiste map?")
        return redirect(url_for("leads_pagina"))
    res = _leads_toevoegen("\n".join(teksten))
    if not any(res.values()):
        flash("%d mail(s) opgehaald, maar er zat geen lead-gegevensblok in. Is dit wel de "
              "toewijzingsmail van het portaal?" % len(teksten))
    else:
        flash("%d mail(s) opgehaald → %d nieuwe lead(s)%s.%s%s" % (
            len(teksten), res["nieuw"], (" · %d al bekend" % res["dubbel"]) if res["dubbel"] else "",
            " BAG-gegevens worden op de achtergrond opgehaald." if res["nieuw"] else "",
            _annulering_melding(res)))
    return redirect(url_for("leads_pagina"))


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
    # BULK: plak gerust 60 mails in één keer. BAG-gegevens komen er in de achtergrond bij, zodat
    # de pagina direct terugkomt; bij ~60 leads duurt die ronde een minuut (ververs dan even).
    res = _leads_toevoegen(tekst)
    if not any(res.values()):
        flash("Kon geen lead-gegevens vinden — plak de portal-mail(s) of sleep .eml-bestanden (met {...}-blok).")
        return redirect(url_for("leads_pagina"))
    flash("%d lead(s) toegevoegd%s.%s%s" % (
        res["nieuw"], (" · %d dubbel overgeslagen" % res["dubbel"]) if res["dubbel"] else "",
        " BAG-gegevens worden op de achtergrond opgehaald — ververs zo de pagina." if res["nieuw"] else "",
        _annulering_melding(res)))
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


BAG_VELDEN = ("straat", "woonplaats", "bouwjaar", "oppervlakte_m2", "gebruiksdoel", "verblijfsobject_id")


def _bag_toepassen(lead, info):
    """Alleen gevulde BAG-velden overnemen — nooit iets overschrijven met leeg."""
    for k in BAG_VELDEN:
        if info.get(k) not in (None, ""):
            lead[k] = info[k]


def _bag_verrijk_achtergrond(ids):
    """Haal voor deze leads de BAG-gegevens op ZONDER de gebruiker te laten wachten.
    Elke lead wordt apart weggeschreven: één traag of onvindbaar adres houdt de rest niet op.
    Het netwerkverkeer gebeurt buiten het slot; alleen het wegschrijven zit erin."""
    def werk():
        for lid in ids:
            try:
                rows = leads_mod.load_leads()
                r = next((x for x in rows if x.get("id") == lid), None)
                if not r or r.get("bouwjaar"):        # al verrijkt (of intussen verwijderd)
                    continue
                info, fout = bag_mod.bag_info(r.get("postcode", ""), r.get("huisnummer", ""),
                                              r.get("toevoeging", ""))
                if fout or not info:
                    continue                          # stil overslaan: de 🏛-knop blijft als fallback
                def zet(leads, _lid=lid, _info=info):
                    doel = next((x for x in leads if x.get("id") == _lid), None)
                    if doel:
                        _bag_toepassen(doel, _info)
                leads_mod.wijzig(zet)
            except Exception:
                continue                              # verrijking mag NOOIT een lead kwijtmaken
    threading.Thread(target=werk, daemon=True, name="bag-verrijking").start()


@app.route("/leads/<int:lid>/bag", methods=["POST"])
@login_required
def leads_bag(lid):
    """Handmatig alsnog verrijken — fallback voor adressen die de automatische ronde niet vond."""
    rows = leads_mod.load_leads()
    r = next((x for x in rows if x.get("id") == lid), None)
    if not r:
        abort(404)
    info, fout = bag_mod.bag_info(r.get("postcode", ""), r.get("huisnummer", ""), r.get("toevoeging", ""))
    if fout:
        flash(fout)
    else:
        leads_mod.wijzig(lambda leads: _bag_toepassen(
            next((x for x in leads if x.get("id") == lid), {}), info))
    return redirect(url_for("leads_pagina"))


@app.route("/leads/<int:lid>/weg", methods=["POST"])
@login_required
def leads_weg(lid):
    """Lead DEFINITIEF verwijderen (bv. de bewoner heeft de aanvraag geannuleerd). AVG: de
    persoonsgegevens (naam/adres/e-mail/telefoon) gaan uit out/leads. Een eventueel al aangemaakt
    PROJECT blijft bestaan — daar staan bewust geen persoonsgegevens in (alleen adres/BAG)."""
    rows = leads_mod.load_leads()
    lead = next((x for x in rows if x.get("id") == lid), None)
    if not lead:
        abort(404)
    naam = (lead.get("naam") or lead.get("email") or "lead %d" % lid).strip()
    # onthoud dat DIT adres bewust weg is, anders zet de volgende mail-ophaalronde 'm zo weer terug
    # (bewoners die zich hebben uitgeschreven kregen zo opnieuw een kennismakingsmail)
    leads_mod.onthoud_gewist(lead)
    leads_mod.save_leads([x for x in rows if x.get("id") != lid])
    flash("Lead '%s' definitief verwijderd%s. Dit adres komt bij een volgende ophaalronde niet "
          "terug — via 'Geblokkeerd' kun je dat terugdraaien."
          % (naam, " (het gekoppelde project %s blijft staan)" % lead["project_tag"]
             if lead.get("project_tag") else ""))
    return redirect(url_for("leads_pagina"))


@app.route("/leads/geblokkeerd", methods=["POST"])
@login_required
def leads_geblokkeerd():
    """Blokkade van verwijderde adressen opheffen — voor als iemand zich toch weer aanmeldt."""
    sleutel = (request.form.get("sleutel") or "").strip()
    rest = leads_mod.vergeet_gewist(sleutel or None)
    flash("Blokkade opgeheven voor %s. Nog %d adres(sen) geblokkeerd; haal de mails opnieuw op om "
          "ze terug te halen." % (("dit adres" if sleutel else "ALLE adressen"), len(rest)))
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
    # exact DEZE leads staan in de BCC-lijst -> alleen die markeren als 'verstuurd' (zie route hieronder)
    ids = ",".join(str(r.get("id")) for r in rows)
    return page(LEADS_ONTVANGST, n=len(rows), bcc=bcc, onderwerp=onderwerp, tekst=tekst, ids=ids)


@app.route("/leads/ontvangst/verstuurd", methods=["POST"])
@login_required
def leads_ontvangst_verstuurd():
    """Markeer ALLEEN de leads die daadwerkelijk in de BCC-lijst stonden (ids uit de ontvangst-pagina).
    Zo krijgt niemand die intussen is toegevoegd — of iemand zonder e-mailadres — stil 'mail gestuurd'
    terwijl hij de mail nooit kreeg; die blijft 'nieuw' en gaat mee in de VOLGENDE batch."""
    rows = leads_mod.load_leads()
    _raw = request.form.get("ids")
    _ids = None if _raw is None else {int(x) for x in _raw.split(",") if x.strip().isdigit()}
    n = 0
    for r in rows:
        if r.get("status") != "nieuw" or not r.get("email"):
            continue
        if _ids is not None and r.get("id") not in _ids:
            continue
        r["status"] = "mail gestuurd"
        n += 1
    leads_mod.save_leads(rows)
    flash("%d lead(s) gemarkeerd als 'mail gestuurd' — zij krijgen de ontvangstmail niet nog eens." % n)
    return redirect(url_for("leads_pagina"))


@app.route("/leads/<int:lid>/mail")
@login_required
def leads_mail(lid):
    r = next((x for x in leads_mod.load_leads() if x.get("id") == lid), None)
    if not r:
        abort(404)
    soort = request.args.get("soort", "")
    if soort == "bevestiging":
        if not (r.get("afspraak") or "").strip():
            # zonder datum zou de mail "nader te bepalen" zeggen — dat wil je nooit versturen
            flash("Voor de bevestigingsmail is eerst een afspraakdatum nodig: vul die in op de "
                  "leadkaart van %s en druk op 📅. Daarna staat de datum vanzelf in de mail."
                  % (r.get("naam") or "deze lead"))
            return redirect(url_for("leads_pagina"))
        onderwerp, tekst = leads_mod.bevestiging_mail(r, _cfg().get("adviseur", {}))
    else:
        onderwerp, tekst = leads_mod.concept_mail(r, _cfg().get("adviseur", {}))
    return page(LEAD_MAIL, l=r, onderwerp=onderwerp, tekst=tekst, soort=soort,
                afspraak_nl=leads_mod._afspraak_nl(r.get("afspraak", "")))


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
