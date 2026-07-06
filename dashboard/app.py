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
from dashboard.measures import laad_catalog, suggesties, bouw_maatregelen             # noqa: E402
from dashboard import leads as leads_mod                                              # noqa: E402
from dashboard import bag as bag_mod                                                  # noqa: E402
from ventilatie.ventilatie import bereken as vent_bereken                             # noqa: E402
from ventilatie.ventilatieplan_svg import ventilatieplan_svg                          # noqa: E402
from isolatieplan import fill_template                                                # noqa: E402
from foto import checklist as foto_checklist                                          # noqa: E402
from validator import validate as validator_mod                                       # noqa: E402

PROJECTS_DIR = os.path.join(TOOL_DIR, "out", "projects")
UPLOAD_DIR = os.path.join(TOOL_DIR, "out", "_uploads")
CONFIG = os.path.join(TOOL_DIR, "config.json")
TEMPLATE_DOCX = os.path.join(TOOL_DIR, "templates", "isolatieplan_template.docx")
DEFAULT_PW = "nijbegun"
STAPPEN = [("inladen", "Inladen"), ("maatregelen", "Maatregelen"), ("vabi", "VABI-toets"),
           ("afronden", "Afronden"), ("klaar", "Opleveren")]

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


app.secret_key = (_cfg().get("dashboard", {}).get("secret") or secrets.token_hex(16))


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
            return json.load(fh)
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
    ]
    return out


# ---------------- HTML ----------------
BASE = """<!doctype html><html lang=nl><head><meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1">
<title>Nij Begun · isolatieplan</title>
<link rel="stylesheet" href="{{url_for('static', filename='app.css')}}"></head><body>
<div class=topbar><span class=brand>🏠 Nij Begun · isolatieplan</span>
<nav>{% if session.ingelogd %}<a href="{{url_for('leads_pagina')}}">Leads</a><a href="{{url_for('home')}}">Projecten</a><a href="{{url_for('guide')}}">Guide</a>
<a href="{{url_for('logout')}}">Uitloggen</a>{% endif %}</nav></div>
<div class="wrap {{wrapclass or ''}}">
{% if default_pw %}<div class=warn>⚠ Geen wachtwoord ingesteld (default actief). Zet <code>"dashboard":{"wachtwoord":"…"}</code> in config.json.</div>{% endif %}
{% with msgs = get_flashed_messages() %}{% for m in msgs %}<div class=warn>{{m}}</div>{% endfor %}{% endwith %}
{{ body|safe }}</div></body></html>"""


def stepper(active, st):
    done = set()
    order = [s for s, _ in STAPPEN]
    if st:
        for s in order:
            if order.index(s) < order.index(st.get("stap", "inladen")):
                done.add(s)
    parts = ['<div class=stepper>']
    for s, lbl in STAPPEN:
        cls = "active" if s == active else ("done" if s in done else "")
        parts.append('<div class="step %s"><div class=bar></div>%s</div>' % (cls, lbl))
    parts.append('</div>')
    return "".join(parts)


def page(body_tmpl, wrapclass="", **ctx):
    body = render_template_string(body_tmpl, **ctx)
    return render_template_string(BASE, body=body, wrapclass=wrapclass,
                                  default_pw=(_password() == DEFAULT_PW))


LOGIN = """<div class=card style="max-width:400px;margin:10vh auto">
<h1>Inloggen</h1><p class=lead>Je persoonlijke, lokale isolatieplan-werkplek.</p>
<form method=post><label>Wachtwoord</label><input type=password name=wachtwoord autofocus>
<div class=btn-row><button class="btn lg">Inloggen</button></div></form></div>"""

HOME = """<h1>Projecten</h1><p class=lead>Van kloppende VABI-export naar een ingediend Nij Begun-isolatieplan — stap voor stap.</p>
<div class=card><h2>Nieuw project</h2>
<p class=muted>Upload een <b>VABI-export</b> (.xml — de woning die in Vabi al klopt), een <b>dossier</b> (.json) of een MagicPlan <b>Statistics-CSV</b>.</p>
<form method=post action="{{url_for('nieuw')}}" enctype=multipart/form-data>
<div class=file-drop>Sleep hier je bestand of kies het<br><input type=file name=bestand accept=".xml,.json,.csv" required></div>
<div class=grid2>
<div><label>Straat + huisnummer</label><input name=straat placeholder="bv. Oosterkade 23"></div>
<div><label>Plaats</label><input name=plaats></div>
<div><label>Postcode</label><input name=postcode placeholder="(bij CSV)"></div>
<div><label>Woningtype</label><input name=woningtype value="Tussenwoning"></div></div>
<div class=btn-row><button class="btn lg">Project starten →</button>
<a class="btn ghost" href="{{url_for('guide')}}">Eerst de guide lezen</a></div></form></div>
{% if projects %}<div class=card><h2>Lopende projecten</h2><table>
<tr><th>Adres</th><th>Stap</th><th>Standaard</th><th>Maatregelen</th><th></th></tr>
{% for p in projects %}<tr><td>{{p.adres}}</td>
<td><span class="pill gray">{{p.stap}}</span></td>
<td>{% if p.voldoet is none %}<span class=muted>—</span>{% elif p.voldoet %}<span class="pill green">voldoet</span>{% else %}<span class="pill amber">nog niet</span>{% endif %}</td>
<td>{{p.n}}{% if p.totaal %} · &euro;{{'%.0f'|format(p.totaal)}}{% endif %}</td>
<td><a class="btn sec" href="{{url_for('project', tag=p.tag)}}">openen →</a></td></tr>{% endfor %}</table></div>
{% endif %}"""

INLADEN = """{{stepper|safe}}<h1>Inladen & controleren</h1>
<p class=lead>Controleer de gegevens en voeg de verplichte foto's toe (voorkant + huisnummer).</p>
<div class="verdict {{ 'ok' if h.voldoet else 'no' }}"><span class=ico>{{ '✅' if h.voldoet else '🎯' }}</span>
<div><b>Huidige staat — label {{h.label}}</b><br>
<span class=muted>energiebehoefte {{h.behoefte if h.behoefte is not none else '—'}} vs Standaard {{h.standaard if h.standaard is not none else '—'}} kWh/m²·jr
{% if h.voldoet %}→ voldoet al{% elif h.marge is not none %}→ {{h.marge}} kWh/m²·jr te overbruggen{% endif %}</span></div></div>
<div class=hint>De huidige staat komt uit de VABI-export. Klopt dit niet? Pas het in Vabi aan en upload opnieuw. <b>Vabi blijft de rekenkern.</b></div>
<form method=post enctype=multipart/form-data><div class=card><h2>Projectgegevens</h2><div class=grid2>
<div><label>Adres</label><input name=adres value="{{d.identificatie.straat}} {{d.identificatie.huisnummer}}"></div>
<div><label>Postcode</label><input name=postcode value="{{d.identificatie.postcode}}"></div>
<div><label>Plaats</label><input name=plaats value="{{d.identificatie.plaats}}"></div>
<div><label>Woningtype</label><input name=woningtype value="{{d.identificatie.woningtype}}"></div>
<div><label>Bouwjaar</label><input name=bouwjaar value="{{d.identificatie.bouwjaar or ''}}"></div>
<div><label>Adviseur</label><input name=adviseur value="{{d.adviseur.naam or cfg_naam}}"></div></div></div>
<div class=card><h2>Verplichte foto's</h2><div class=grid2>
<div><label>Foto voorkant woning{% if st.foto_voorkant %} ✓{% endif %}</label><input type=file name=foto_voorkant accept="image/*"></div>
<div><label>Foto huisnummer{% if st.foto_huisnummer %} ✓{% endif %}</label><input type=file name=foto_huisnummer accept="image/*"></div></div>
<p class=muted small>Kwaliteitscommissie-eis: adres én foto op de voorkant komen overeen · ≥8 MP · max 5 MB (SNN).</p></div>
<div class=btn-row><div class=spacer></div><button class="btn lg">Door naar maatregelen →</button></div></form>"""

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
{% if g.note %}<p class=muted small>{{g.note}}</p>{% endif %}
<input type=hidden name="onderdeel_{{loop.index0}}" value="{{g.onderdeel}}">
<input type=hidden name="m2_{{loop.index0}}" value="{{g.m2}}">
<input type=hidden name="doel_{{loop.index0}}" value="{{g.rc_u_doel}}">
<label>Maatregel (catalogus)</label>
<select name="code_{{loop.index0}}" class=cm data-grp="{{loop.index0}}">
{% for k in g.kandidaten %}<option value="{{k.code}}" data-prijs="{{k.prijs}}" {{'selected' if k.code==g.default_code else ''}}>{{k.code}} · {{k.omschrijving[:70]}} — €{{'%.2f'|format(k.prijs)}}/{{k.eenheid}}</option>{% endfor %}</select>
<p class=muted small>doelwaarde {{g.rc_u_doel}} · regel-subtotaal <b class=sub data-grp="{{loop.index0}}">€{{'%.0f'|format(g.kandidaten[0].kosten)}}</b></p>
</div>{% endfor %}
<div class=totalbar><span class=t>Subsidietabel (Standaard)</span><span class=v id=tot>€0</span>
<div class=spacer></div><button class="btn lg">Door naar VABI-toets →</button></div></form>
<script>
function recalc(){var tot=0;document.querySelectorAll('.meas-group').forEach(function(g,i){
var m2=parseFloat(g.dataset.m2)||0;var sel=g.querySelector('.cm');var pr=parseFloat(sel.selectedOptions[0].dataset.prijs)||0;
var sub=Math.round(pr*m2);g.querySelector('.sub').textContent='€'+sub.toLocaleString('nl-NL');
var bk=g.querySelector('.bk').value;if(bk==='standaard')tot+=sub;});
document.getElementById('tot').textContent='€'+tot.toLocaleString('nl-NL');}
document.getElementById('mf').addEventListener('change',recalc);recalc();
</script>"""

VABI = """{{stepper|safe}}<h1>VABI-toets met maatregelen</h1>
<p class=lead>Genereer de VABI-import mét de gekozen maatregelen, reken in Vabi, en upload de nieuwe export terug.</p>
<div class=card><h2>1 · Importeer in Vabi EPA-W</h2>
<p class=muted>De toekomstige staat (maatregelen verwerkt) als 3 bibliotheken. Importeer in EPA-W → <b>Constructies → Objecten → Installaties</b> → Rekenen.</p>
<ul class=files>{% for f in vabi_files %}<li>{{f}} <a class="btn sec" href="{{url_for('download', tag=tag, filename='vabi_na/'+f)}}">download</a></li>{% endfor %}</ul></div>
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
<p class=lead>Het isolatieplan, het visuele ventilatieplan en de indien-check — klaar voor oplevering.</p>
<div class=card><h2>Klaar voor indienen? (Beoordelingsformulier)</h2><ul class=check>
{% for ok, txt in beoord %}<li><span class="mk {{'ok2' if ok else 'no2'}}">{{ '✓' if ok else '○' }}</span>{{txt}}</li>{% endfor %}</ul>
<p class=muted small>Spiegelt de compleetheidscriteria van de Nij Begun-kwaliteitscommissie.</p></div>
<div class=card><h2>Ventilatieplan</h2><div class=svgbox>{{vent_svg|safe}}</div></div>
<div class=card><h2>Gegenereerde bestanden</h2><ul class=files>
{% for f in files %}<li>{{f}} <a class="btn sec" href="{{url_for('download', tag=tag, filename=f)}}">download</a></li>{% endfor %}</ul></div>
<div class=btn-row><a class="btn sec" href="{{url_for('afronden', tag=tag)}}?regen=1">Opnieuw genereren</a><div class=spacer></div>
<a class="btn lg green" href="{{url_for('export', tag=tag)}}">⬇ Exporteer de bundel (.zip)</a></div>"""

GUIDE = """<h1>Guide — zo maak je een Nij Begun-isolatieplan</h1>
<p class=lead>De volledige werkwijze, met de eisen van de Nij Begun-kennisbank erin verwerkt.</p>
<div class=card><h2>De flow in 5 stappen</h2>
<div class=stepper>{% for s,l in stappen %}<div class="step done"><div class=bar></div>{{l}}</div>{% endfor %}</div>
<dl class=kv><dt>1 · Inladen</dt><dd>Upload de <b>kloppende VABI-export</b> (of dossier/CSV). De webapp leest de huidige Standaard. Voeg de verplichte foto's toe: <b>voorkant + huisnummer</b> (moeten met het adres overeenkomen).</dd>
<dt>2 · Maatregelen</dt><dd>Vink per bouwdeel aan wat je toepast (Nij Begun-catalogus). <b>Standaard-maatregelen</b> → subsidietabel (50/100%); <b>wenselijke extra's</b> → markeer als 30% ISDE.</dd>
<dt>3 · VABI-toets</dt><dd>Importeer de gegenereerde toekomstige staat in Vabi, reken, en upload de export terug. <b>Voldoet de set aan de Standaard?</b> Zo niet → pakket uitbreiden.</dd>
<dt>4 · Afronden</dt><dd>Isolatieplan (Word) + <b>visueel ventilatieplan</b> + foto-checklist worden gegenereerd. De <b>indien-check</b> spiegelt het Beoordelingsformulier.</dd>
<dt>5 · Opleveren</dt><dd>Exporteer de bundel en dien in via leveranciers@nijbegun.nl. De eerste 4 plannen worden 100% gecontroleerd.</dd></dl></div>
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
<p class=muted small>Bron: adviseurs-nijbegun.nl/support. Details in docs/nijbegun-kennisbank-eisen.md.</p>
<div class=btn-row><a class="btn" href="{{url_for('home')}}">← naar projecten</a></div>"""


# ---------------- routes ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("wachtwoord") == _password():
            session["ingelogd"] = True
            return redirect(url_for("home"))
        flash("Onjuist wachtwoord.")
    return page(LOGIN, wrapclass="narrow")


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
            rows.append({"tag": tag, "adres": st.get("adres", tag), "stap": st.get("stap", "inladen"),
                         "voldoet": na.get("voldoet"), "n": len(st.get("keuze", [])),
                         "totaal": st.get("totaal", 0)})
    return page(HOME, projects=rows)


@app.route("/guide")
@login_required
def guide():
    return page(GUIDE, stappen=STAPPEN)


@app.route("/nieuw", methods=["POST"])
@login_required
def nieuw():
    f = request.files.get("bestand")
    if not f or not f.filename:
        flash("Geen bestand gekozen."); return redirect(url_for("home"))
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in (".xml", ".json", ".csv"):
        flash("Alleen .xml (VABI), .json (dossier) of .csv (MagicPlan)."); return redirect(url_for("home"))
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    up = os.path.join(UPLOAD_DIR, "upload" + ext)
    f.save(up)
    huidig = None
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
    # adres uit formulier overschrijven indien gegeven
    straat = request.form.get("straat", "").strip()
    if straat:
        dos.identificatie.straat = straat
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
          dos.identificatie.plaats or ""), "stap": "inladen", "dossier_file": dfile, "huidig": huidig,
          "na": None, "foto_voorkant": "", "foto_huisnummer": "", "keuze": [], "totaal": 0}
    _save_state(tag, st)
    return redirect(url_for("inladen", tag=tag))


@app.route("/project/<tag>")
@login_required
def project(tag):
    st = _load_state(tag)
    if not st:
        abort(404)
    return redirect(url_for(st.get("stap", "inladen") if st.get("stap") != "klaar" else "afronden", tag=tag))


@app.route("/project/<tag>/inladen", methods=["GET", "POST"])
@login_required
def inladen(tag):
    st = _load_state(tag)
    dos = _dossier(tag)
    if not st or not dos:
        abort(404)
    if request.method == "POST":
        a = request.form.get("adres", "").strip()
        if a:
            parts = a.rsplit(" ", 1)
            dos.identificatie.straat = parts[0]
            if len(parts) > 1:
                dos.identificatie.huisnummer = parts[1]
        dos.identificatie.postcode = request.form.get("postcode", dos.identificatie.postcode)
        dos.identificatie.plaats = request.form.get("plaats", dos.identificatie.plaats)
        dos.identificatie.woningtype = request.form.get("woningtype", dos.identificatie.woningtype)
        bj = request.form.get("bouwjaar", "").strip()
        if bj.isdigit():
            dos.identificatie.bouwjaar = int(bj)
        if request.form.get("adviseur"):
            dos.adviseur.naam = request.form["adviseur"].strip()
        for veld in ("foto_voorkant", "foto_huisnummer"):
            fp = request.files.get(veld)
            if fp and fp.filename:
                ext = os.path.splitext(fp.filename)[1].lower() or ".jpg"
                naam = "%s_%s%s" % (veld, tag, ext)
                fp.save(os.path.join(_pdir(tag), naam))
                st[veld] = naam
        save_json(dos, os.path.join(_pdir(tag), st["dossier_file"]))
        st["adres"] = "%s %s, %s" % (dos.identificatie.straat or "", dos.identificatie.huisnummer or "",
                                     dos.identificatie.plaats or "")
        st["stap"] = "maatregelen"
        _save_state(tag, st)
        return redirect(url_for("maatregelen", tag=tag))
    return page(INLADEN, stepper=stepper("inladen", st), st=st, d=dos, h=st.get("huidig") or {},
                cfg_naam=_cfg().get("adviseur", {}).get("naam", ""))


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
        keuze_std, keuze_isde = [], []
        for i in range(len(groepen)):
            bucket = request.form.get("bucket_%d" % i, "standaard")
            if bucket == "geen":
                continue
            item = {"code": request.form.get("code_%d" % i), "onderdeel": request.form.get("onderdeel_%d" % i),
                    "m2": float(request.form.get("m2_%d" % i) or 0), "rc_u_doel": request.form.get("doel_%d" % i, ""),
                    "subposten": []}
            (keuze_std if bucket == "standaard" else keuze_isde).append(item)
        maatregelen_std, totaal = bouw_maatregelen(catalog, keuze_std)
        maatregelen_isde, _ = bouw_maatregelen(catalog, keuze_isde)
        dos.maatregelen = maatregelen_std
        save_json(dos, os.path.join(_pdir(tag), st["dossier_file"]))
        st["keuze"] = keuze_std
        st["isde"] = [{"code": m.code, "onderdeel": m.onderdeel, "omschrijving": m.omschrijving} for m in maatregelen_isde]
        st["totaal"] = totaal
        st["stap"] = "vabi"
        _save_state(tag, st)
        return redirect(url_for("vabi", tag=tag))
    return page(MAATREGELEN, stepper=stepper("maatregelen", st), groepen=suggesties(dos, catalog))


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
    # genereer toekomstige-staat-bibliotheken
    try:
        toekomst = _toekomstige_staat(dos, dos.maatregelen)
        generate_all.generate_all(toekomst, outdir, prefix="na")
    except Exception as e:
        flash("VABI-import genereren mislukte: %s" % e)
    vabi_files = sorted(os.path.basename(p) for p in glob.glob(os.path.join(outdir, "*.xml")))
    return page(VABI, stepper=stepper("vabi", st), tag=tag, vabi_files=vabi_files, na=st.get("na"))


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
            fill_template.fill(dos, TEMPLATE_DOCX, os.path.join(pdir, "isolatieplan_%s.docx" % tag))
        except Exception as e:
            flash("Isolatieplan genereren mislukte: %s" % e)
        try:
            with open(os.path.join(pdir, "fotochecklist_%s.txt" % tag), "w", encoding="utf-8") as fh:
                fh.write(foto_checklist.generate(dos))
        except Exception:
            pass
    # ventilatieplan (altijd vers)
    vres = vent_bereken(dos.geometrie.ruimtes)
    svg = ventilatieplan_svg(vres, adres=st.get("adres", ""))
    with open(os.path.join(pdir, "ventilatieplan_%s.svg" % tag), "w", encoding="utf-8") as fh:
        fh.write(svg)
    st["stap"] = "klaar"
    _save_state(tag, st)
    files = sorted(os.path.basename(p) for p in glob.glob(os.path.join(pdir, "*"))
                   if os.path.isfile(p) and not p.endswith("project.json"))
    return page(AFRONDEN, stepper=stepper("afronden", st), tag=tag, vent_svg=svg,
                beoord=_beoordeling(tag, st, dos), files=files)


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
    mem.seek(0)
    return Response(mem.read(), mimetype="application/zip",
                    headers={"Content-Disposition": "attachment; filename=isolatieplan_%s.zip" % tag})


@app.route("/download/<tag>/<path:filename>")
@login_required
def download(tag, filename):
    pdir = _pdir(tag)
    if ".." in filename or not os.path.isdir(pdir):
        abort(404)
    return send_from_directory(pdir, filename, as_attachment=True)


# ---------------- leads (Nij Begun-portal-toewijzingen) ----------------
LEADS = """<h1>Leads</h1>
<p class=lead>Toegewezen bewoners uit het Nij Begun-portal — plak de mail, volg de status, genereer de kennismakingsmail.</p>
<div class=card><h2>Nieuwe lead toevoegen</h2>
<p class=muted>Plak hieronder de <b>hele portal-mail</b> (het JSON-blok wordt eruit gehaald) en klik toevoegen.
De gegevens blijven <b>lokaal</b> op deze computer (AVG).</p>
<form method=post action="{{url_for('leads_add')}}">
<textarea name=mailtekst rows=4 placeholder='{"BagAdresId":"...","Email":"...","Naam":"..."}'></textarea>
<div class=btn-row><button class=btn>Lead toevoegen</button>
<span class=spacer></span><a class="btn sec" href="{{url_for('leads_csv')}}">⬇ Export naar Excel (CSV)</a></div></form></div>
{% if leads %}<div class=card><h2>{{leads|length}} lead(s)</h2><table>
<tr><th>Ontvangen</th><th>Naam</th><th>Adres</th><th>Contact</th><th>Status</th><th></th></tr>
{% for l in leads %}<tr>
<td class=small>{{l.ontvangen}}</td>
<td><b>{{l.naam}}</b></td>
<td>{{l.adres}}{% if l.bouwjaar %}<br><span class="pill blue">{{l.bouwjaar}}</span> <span class="pill gray">{{l.oppervlakte_m2}} m²</span>{% endif %}</td>
<td class=small>{{l.telefoon}}<br>{{l.email}}</td>
<td><form method=post action="{{url_for('leads_status', lid=l.id)}}">
<select name=status onchange="this.form.submit()">
{% for s in statussen %}<option value="{{s}}" {{'selected' if s==l.status else ''}}>{{s}}</option>{% endfor %}
</select></form></td>
<td style="white-space:nowrap">{% if not l.bouwjaar %}<form method=post style="display:inline" action="{{url_for('leads_bag', lid=l.id)}}"><button class="btn sec" title="Straat + bouwjaar + m² uit de BAG halen">🏛 BAG</button></form> {% endif %}<a class="btn sec" href="{{url_for('leads_mail', lid=l.id)}}">✉ mail</a></td></tr>{% endfor %}</table>
<p class="muted small">Status wisselen slaat direct op. Volgorde: nieuw → mail gestuurd → gebeld → afspraak gepland → opname gedaan → plan ingediend → afgerond.</p></div>
{% else %}<div class=hint>Nog geen leads. Plak je eerste portal-mail hierboven.</div>{% endif %}"""

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
<div class=hint>De mail vraagt de bewoner alvast klaar te leggen: facturen/tekeningen van eerder isolatiewerk,
typeplaatje cv-ketel, toegang kruipruimte/zolder en PV-gegevens — precies de bewijslast die ISSO 82.1 bij de
opname vraagt (isolatie telt alleen mee indien waarneembaar of met factuur/tekening aantoonbaar).</div>"""


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
    lead = leads_mod.parse_lead(request.form.get("mailtekst", ""))
    if not lead:
        flash("Kon geen lead-gegevens vinden in de geplakte tekst — plak de hele portal-mail (met het {...}-blok).")
        return redirect(url_for("leads_pagina"))
    rows, nieuw = leads_mod.add_lead(lead)
    leads_mod.save_leads(rows)
    if not nieuw:
        flash("Lead bestaat al (zelfde adres/BAG-id) — niet dubbel toegevoegd.")
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


@app.route("/leads/<int:lid>/mail")
@login_required
def leads_mail(lid):
    r = next((x for x in leads_mod.load_leads() if x.get("id") == lid), None)
    if not r:
        abort(404)
    onderwerp, tekst = leads_mod.concept_mail(r, _cfg().get("adviseur", {}))
    return page(LEAD_MAIL, l=r, onderwerp=onderwerp, tekst=tekst)


@app.route("/leads/export.csv")
@login_required
def leads_csv():
    csv = leads_mod.to_csv(leads_mod.load_leads())
    return Response(csv, mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=nijbegun_leads.csv"})


if __name__ == "__main__":
    print("Nij Begun isolatieplan-webapp -> http://127.0.0.1:5000  (Ctrl+C om te stoppen)")
    if _password() == DEFAULT_PW:
        print("  LET OP: default-wachtwoord 'nijbegun' actief. Stel er een in via config.json.")
    app.run(host="127.0.0.1", port=5000, debug=False)
