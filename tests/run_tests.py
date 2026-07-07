"""
Regressie-testsuite voor de Nij Begun & EPA-tool. Draai: python tests/run_tests.py
Test de hele keten offline tegen de echte voorbeeldbestanden. Exit 0 = alles groen.
"""
import os, sys, json, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
PROJECT = os.path.dirname(ROOT)  # map met de monitor-XML/template
MONITOR = os.path.join(HERE, "fixtures", "monitor_voorbeeld.xml")
TEMPLATE = os.path.join(ROOT, "templates", "isolatieplan_template.docx")
CATALOG = os.path.join(ROOT, "catalog", "catalog.json")

passed = failed = 0
def check(naam, cond, extra=""):
    global passed, failed
    if cond: passed += 1; print("  PASS", naam)
    else: failed += 1; print("  FAIL", naam, "-", extra)

from core.dossier import Dossier, load_json, save_json
from vabi.monitor_xml import parse as parse_monitor
from engine.measure_engine import run as engine_run
from ventilatie.ventilatie import bereken as vent_bereken
from isolatieplan.fill_template import fill as fill_template
from validator.validate import validate, load_catalog_codes

print("1. Core datamodel round-trip")
d = Dossier.build_sample() if hasattr(Dossier, "build_sample") else None
from core.dossier import build_sample
d = build_sample()
check("round-trip identiek", Dossier.from_dict(d.to_dict()).to_dict() == d.to_dict())
check("sample heeft ruimtes", len(d.geometrie.ruimtes) > 0)

print("2. Catalogus")
cat = json.load(open(CATALOG, encoding="utf-8"))
check("catalogus >300 maatregelen", len(cat["maatregelen"]) > 300, str(len(cat["maatregelen"])))
check("V6 kierdichting aanwezig", any(m["code"].startswith("V6") for m in cat["maatregelen"]))

print("3. VABI monitor-parser")
dos, _ = parse_monitor(MONITOR)
check("postcode 9501TP", dos.identificatie.postcode == "9501TP", dos.identificatie.postcode)
check("Standaard 64.0", dos.berekening.standaard_eis_kwh_m2 == 64.0, str(dos.berekening.standaard_eis_kwh_m2))
check("25 schildelen", len(dos.schil) == 25, str(len(dos.schil)))
check("glas-U geparsed", any(s.type == "kozijn" and s.u_huidig for s in dos.schil))

print("4. Maatregel-engine")
dos2, notes = engine_run(parse_monitor(MONITOR)[0], cat)
codes = {m["code"] for m in cat["maatregelen"]}
check("maatregelen voorgesteld", len(dos2.maatregelen) >= 3, str(len(dos2.maatregelen)))
check("alle codes uit catalogus", all(any(c == m.code or c.startswith(m.code) for c in codes) for m in dos2.maatregelen))
check("alle kosten > 0", all((m.kosten or 0) > 0 for m in dos2.maatregelen))
check("qv10-advies aanwezig", any("qv;10" in n for n in notes))
check("meerwerk-subposten voorgesteld", any(m.subposten for m in dos2.maatregelen))
check("subposten cat 2 en cat 3",
      any(s.categorie == 2 for m in dos2.maatregelen for s in m.subposten) and
      any(s.categorie == 3 for m in dos2.maatregelen for s in m.subposten))
check("subposten zonder admin-rijen",
      not any("minimum tarief" in (s.omschrijving or "").lower()
              for m in dos2.maatregelen for s in m.subposten))

print("5. Ventilatie (Nij Begun-vuistregels)")
v = vent_bereken(build_sample().geometrie.ruimtes)
check("keuken afvoer 21", any(r["functie"] == "keuken" and r["afvoer"] == 21.0 for r in v["rows"]))
check("maatgevend > 0", v["maatgevend_dm3s"] > 0)
check("rate 0,7 per verblijfsgebied (Nij Begun)", v["rate"] == 0.7)
check("vuistregel: geen afvoer in slaapkamer in checklist",
      any("slaapkamer" in vr.lower() for vr in v["vuistregels"]))
check("overstroom berekend", "overstroom_dm3s" in v and v["overstroom_dm3s"] >= 0)

print("6. Isolatieplan invullen (huidige staat)")
tmpdoc = os.path.join(tempfile.gettempdir(), "_t.docx")
n, tot = fill_template(dos2, TEMPLATE, tmpdoc)
import docx
dd = docx.Document(tmpdoc)
allcells = " ".join(c.text for t in dd.tables for r in t.rows for c in r.cells)
check("docx gemaakt + maatregelen", n >= 3 and os.path.exists(tmpdoc))
check("huidige staat ingevuld (U-waarde)", "U " in allcells and "W/m2K" in allcells)

print("7. Validator")
issues, dos2 = validate(dos2, load_catalog_codes(CATALOG))
check("validator geeft status", dos2.validatie.status in ("sluitend", "onvolledig"))
incompleet = Dossier()
iss2, incompleet = validate(incompleet, None)
check("leeg dossier = blokkerend", any(s == "BLOKKEREND" for s, _ in iss2))

print("8. Orchestrator end-to-end (subprocess)")
outdir = os.path.join(tempfile.gettempdir(), "nb_test_out")
r = subprocess.run([sys.executable, os.path.join(ROOT, "run.py"), "--from-monitor", MONITOR,
                    "--out", outdir, "--straat", "Essenhage", "--plaats", "Stadskanaal",
                    "--woningtype", "Tussenwoning"], capture_output=True, text=True)
files = os.listdir(outdir) if os.path.isdir(outdir) else []
check("isolatieplan docx output", any(f.startswith("isolatieplan_") and f.endswith(".docx") for f in files))
check("ventilatieberekening output", any(f.startswith("ventilatieberekening_") for f in files))
check("fotochecklist output", any(f.startswith("fotochecklist_") for f in files))
check("rapport output", any(f.startswith("rapport_") for f in files))
check("exitcode 0 of 2 (geen crash)", r.returncode in (0, 2), "rc=%s err=%s" % (r.returncode, r.stderr[-200:]))

print("9. VABI-generator (dossier -> monitoring-XML, round-trip)")
from vabi import monitor_generate as vgen
_sd = build_sample()
_gp = os.path.join(tempfile.gettempdir(), "gen_sample.xml")
vgen.write(_sd, _gp)
_rd, _ = parse_monitor(_gp)
check("generator schil round-trip", len(_rd.schil) == len(_sd.schil), "%d vs %d" % (len(_rd.schil), len(_sd.schil)))
check("generator postcode behouden", _rd.identificatie.postcode == _sd.identificatie.postcode)
check("generator gevel-Rc behouden", any(s.type == "gevel" and s.rc_huidig for s in _rd.schil))
check("generator installaties in XML", b"HR107" in vgen.to_xml(_sd))
_md, _ = parse_monitor(MONITOR)
_mp = os.path.join(tempfile.gettempdir(), "gen_monitor.xml")
vgen.write(_md, _mp)
_mr, _ = parse_monitor(_mp)
check("monitor 25 schil round-trip", len(_mr.schil) == len(_md.schil) == 25, "%d->%d" % (len(_md.schil), len(_mr.schil)))

print("10. Parameter-sanity-check")
from vabi.sanity import check as sanity_check
from core.dossier import VloerInfo
check("schone sample geen NAMETEN", all(l != "NAMETEN" for l, _ in sanity_check(build_sample())))
_bad = build_sample(); _bad.geometrie.vloeren.append(VloerInfo("Zolder", 20.0, 3.9))
check("outlier-hoogte -> NAMETEN", any(l == "NAMETEN" for l, _ in sanity_check(_bad)))
_no = build_sample()
for s in _no.schil:
    if s.type == "gevel": s.orientatie = ""
check("ontbrekende orientatie gevlagd", any("orientatie" in m for _, m in sanity_check(_no)))

print("11. MagicPlan-extractor (plan-JSON -> dossier)")
from magicplan.extractor import map_plan_to_dossier
_plan = json.load(open(os.path.join(HERE, "fixtures", "magicplan_plan_voorbeeld.json"), encoding="utf-8"))
_ed = map_plan_to_dossier(_plan)
check("extractor postcode", _ed.identificatie.postcode == "9501TP", _ed.identificatie.postcode)
check("extractor schil gevel+vloer+dak+kozijn",
      {"gevel", "vloer", "dak", "kozijn"} <= {s.type for s in _ed.schil})
check("extractor gevel-begrenzing (algemeen)",
      any(s.type == "gevel" and s.begrenzing == "Buitenlucht" for s in _ed.schil))
check("extractor vloerconstructie",
      any(s.type == "vloer" and s.subtype == "Houten vloer" for s in _ed.schil))
check("extractor dak helling + oppervlak",
      any(s.type == "dak" and s.hellingshoek == 45 and s.oppervlakte_m2 > 55 for s in _ed.schil))
check("extractor isolatie Ja/Nee",
      any(s.type == "gevel" and s.isolatie_aanwezig == "Nee" for s in _ed.schil))
check("extractor ruimtes + functie", any(r.functie == "keuken" for r in _ed.geometrie.ruimtes))
check("extractor installaties (subtype)", _ed.installaties.verwarming.subtype == "HR107")
_ed2, _ = engine_run(_ed, cat)
check("extractor -> engine draait", _ed2 is not None and isinstance(_ed2.maatregelen, list))
check("extractor -> engine maatregelen (gevel/vloer/dak)", len(_ed2.maatregelen) >= 2, str(len(_ed2.maatregelen)))

print("12. Prijsopbouw T7-T9 (cat 1/2/3 + clonen)")
from core.dossier import Maatregel as _M, Subpost as _Sub
_pd = build_sample()
_pd.maatregelen[0].subposten = [_Sub(categorie=2, code="V1-1-Z1", omschrijving="Opdikken",
                                     prijs_per_eenheid=2.5, eenheid="m2", hoeveelheid=48, kosten=120.0)]
_pp = os.path.join(tempfile.gettempdir(), "pb_test.docx")
fill_template(_pd, TEMPLATE, _pp)
_b0 = "|".join(c.text for r in [t for t in docx.Document(_pp).tables
              if t.rows and t.rows[0].cells[0].text.strip().lower().startswith("maatregel:")][0].rows
              for c in r.cells)
check("prijsopbouw cat1 code", _pd.maatregelen[0].code in _b0)
check("prijsopbouw cat2 subpost", "Opdikken" in _b0)
_pd5 = build_sample()
_pd5.maatregelen += [_M(code="V5-1", onderdeel="E Ventilatie", omschrijving="Roosters",
                        oppervlakte_m2=4, prijs_per_eenheid=50, kosten=200, eenheid="st"),
                     _M(code="V6-1", onderdeel="E Ventilatie", omschrijving="Kier",
                        oppervlakte_m2=1, prijs_per_eenheid=300, kosten=300, eenheid="pst")]
_pp5 = os.path.join(tempfile.gettempdir(), "pb_test5.docx")
fill_template(_pd5, TEMPLATE, _pp5)
_bl5 = [t for t in docx.Document(_pp5).tables
        if t.rows and t.rows[0].cells[0].text.strip().lower().startswith("maatregel:")]
check("prijsopbouw blok per maatregel (clonen)", len(_bl5) >= 5, str(len(_bl5)))

print("13. Catalogus-API (response -> catalog.json-structuur)")
from catalog.api_client import map_measures_to_catalog
from engine.measure_engine import select_core
_raw = json.load(open(os.path.join(HERE, "fixtures", "nijbegun_catalog_response.json"), encoding="utf-8"))
_capi = map_measures_to_catalog(_raw)
check("catalog-api versie-label (live-datum)", _capi["versie"].startswith("api"))
check("catalog-api aantal maatregelen (gevlakt: 2 brackets + X7 + bodem + dak + X1)",
      _capi["aantal_maatregelen"] == 6, str(_capi["aantal_maatregelen"]))
check("catalog-api incl-btw afgeleid", all(m.get("prijs_per_eenheid_incl_btw") for m in _capi["maatregelen"]))
check("catalog-api werkt in engine", select_core(_capi, ["V1-1"], ["spouwmuurisolatie"], 30.0) is not None)

print("14. MagicPlan report-PDF parser (form-antwoorden uit export)")
from magicplan.report_parser import parse_text
_rtxt = open(os.path.join(HERE, "fixtures", "report_sample.txt"), encoding="utf-8").read()
_ans, _koz = parse_text(_rtxt)
check("report postcode + bouwjaar", _ans.get("postcode") == "9503HN" and _ans.get("bouwjaar") == "1994")
check("report gevel/dak tags", _ans.get("geveltype") == "Spouwmuur" and _ans.get("dakhelling") == "45")
check("report ventilatie", _ans.get("vent_systeem") == "A Natuurlijke ventilatie" and _ans.get("vent_subsysteem_code") == "A1")
check("report kierdichting", _ans.get("kierdichting") == "Slecht-tochtklachten")
check("report kozijnen per raam", len(_koz) == 2 and _koz[0].get("glastype") == "HR++" and _koz[1].get("glastype") == "Dubbel (D)")

print("15. MagicPlan assemblage (report-antwoorden + API-geometrie -> dossier)")
from magicplan.assemble import build_dossier
from magicplan.report_parser import parse_text as _ptext
_p, _koz = _ptext(open(os.path.join(HERE, "fixtures", "report_sample.txt"), encoding="utf-8").read())
_planv2 = {"data": {"plan_data": {"living_area": 100.0, "floors": [
    {"name": "Ground Floor", "statistics": {"area": 50.0}, "values": [{"id": "ceilingHeight", "value": 2.6}],
     "rooms": [{"name": "Keuken", "statistics": {"area": 12.0}, "objects": [
         {"symbol_id": "windowhung", "values": [{"id": "width", "value": 1.5}, {"id": "height", "value": 1.5}]}]}]}]}}}
_ad = build_dossier(_p, _koz, _planv2)
check("assemble identificatie uit report", _ad.identificatie.postcode == "9503HN" and _ad.identificatie.bouwjaar == 1994)
check("assemble geometrie uit plan (ruimte+functie)", any(r.functie == "keuken" for r in _ad.geometrie.ruimtes))
check("assemble schil gevel+vloer+dak+kozijn", {"gevel", "vloer", "dak", "kozijn"} <= {s.type for s in _ad.schil})
check("assemble gevel-tag uit report", any(s.type == "gevel" and s.subtype == "Spouwmuur" for s in _ad.schil))
check("assemble kozijn-glas uit report", any(s.type == "kozijn" and s.glastype == "HR++" for s in _ad.schil))

print("16. VABI Constructiebibliotheek-generator (dossier -> importeerbare XML)")
import tempfile as _tf
import xml.etree.ElementTree as _ET
from vabi.constructie_generate import write as _cwrite
from vabi.codebook import Codebook as _CB
_cb = _CB.default()
_outc = os.path.join(_tf.gettempdir(), "test_constructiebib.xml")
_map, _iss = _cwrite(_ad, _outc)
_croot = _ET.parse(_outc).getroot()                      # well-formed?
_ccons = [c for c in _croot.iter() if c.tag.rsplit("}", 1)[-1] == "Constructie"]
check("constr-gen produceert constructies", len(_ccons) >= 1)
check("constr-gen header = VABI-export", _croot.findtext("XmlVersie") == "120001001")
check("constr-gen alle enums VABI-bekend", all(
    _cb.is_valid(_f, _c.findtext(_f)) for _c in _ccons
    for _f in ("ConstructieType", "Glas", "Kozijn", "IsolatieAanwezig", "Bouwjaar", "Invoer", "SpouwAanwezig")
    if _c.findtext(_f) is not None))
check("constr-gen unieke Guids", len({_c.findtext("Guid") for _c in _ccons}) == len(_ccons))
check("constr-gen mapping dekt schil", all(s.id in _map for s in _ad.schil if (s.type or "").lower() in ("gevel", "vloer", "dak", "kozijn")))

print("17. VABI Objectenbibliotheek-generator (geometrie -> importeerbare XML)")
import os.path as _op
if _op.exists(_op.join(HERE, "..", "vabi", "refs", "objecten_template.xml")):
    from vabi.objecten_generate import write as _owrite
    _outo = os.path.join(_tf.gettempdir(), "test_objectenbib.xml")
    _omap, _oiss, _ostats = _owrite(_ad, _outo)
    _oroot = _ET.parse(_outo).getroot()
    _ocons = {c.findtext("Guid") for c in _oroot.iter() if c.tag.rsplit("}", 1)[-1] == "Constructie" and c.find("Guid") is not None}
    _ohv = [e for e in _oroot.iter() if e.tag.rsplit("}", 1)[-1] == "Hoofdvlak"]
    _orefs = set()
    for _e in _oroot.iter():
        if _e.tag.rsplit("}", 1)[-1] in ("Hoofdvlak", "Deelvlak"):
            _c = _e.find("Constructie")
            if _c is not None and _c.text:
                _orefs.add(_c.text.strip())
    check("obj-gen produceert hoofdvlakken", len(_ohv) >= 1)
    check("obj-gen vlak-refs verwijzen naar embedded constructie", _orefs <= _ocons and len(_orefs) > 0)
    check("obj-gen well-formed Project", _oroot.tag.rsplit("}", 1)[-1] == "Project")
else:
    check("obj-gen (template aanwezig)", False)

print("18. VABI Installatiebibliotheek-generator")
if _op.exists(_op.join(HERE, "..", "vabi", "refs", "installatie_template.xml")):
    from vabi.installatie_generate import write as _iwrite
    _outi = os.path.join(_tf.gettempdir(), "test_installatiebib.xml")
    _iflags = _iwrite(_ad, _outi)
    _iroot = _ET.parse(_outi).getroot()
    check("inst-gen well-formed + heeft Ventilatie", any(e.tag.rsplit("}", 1)[-1] == "Ventilatie" for e in _iroot.iter()))
else:
    check("inst-gen (template aanwezig)", False)

print("19. VABI result_reader (Standaard-toets)")
from vabi.result_reader import read_results as _rr
_mon = os.path.join(_tf.gettempdir(), "test_summary_monitor.xml")
open(_mon, "w", encoding="utf-8").write(
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<tns:Energieprestatie xmlns:tns="http://schemas.ep-online.nl/monitoringbestand">'
    '<Summary><Labelklasse>B</Labelklasse>'
    '<IndicatorEnergiebehoefte>118.45</IndicatorEnergiebehoefte>'
    '<Standaard>91</Standaard></Summary></tns:Energieprestatie>')
_rres = _rr(_mon)
check("result_reader leest Summary", _rres.get("Labelklasse") == "B" and _rres.get("Standaard") == "91")
check("result_reader Standaard-toets (voldoet niet bij 118>91)", _rres.get("_voldoet_aan_standaard") is False)

print("20. Maatregel-advies met begeleidende tekst")
from engine.advies_text import genereer_advies as _gadv
from core.dossier import Maatregel as _Mt
_advms = [_Mt(onderdeel="A Gevel", omschrijving="Spouwmuurisolatie", rc_u_doel="Rc 1.1", oppervlakte_m2=60, kosten=1800),
          _Mt(onderdeel="E Ventilatie", omschrijving="CO2-sturing (C.4)", kosten=1500)]
_advtxt = _gadv(_ad, _advms,
                resultaat_huidig={"Labelklasse": "D", "IndicatorEnergiebehoefte": "165", "Standaard": "110"},
                resultaat_na={"IndicatorEnergiebehoefte": "98", "Standaard": "110", "_voldoet_aan_standaard": True})
check("advies bevat maatregelen + Standaard-conclusie", "Spouwmuurisolatie" in _advtxt and "voldoet aan de Standaard" in _advtxt)
check("advies toont huidige staat", "Huidige staat" in _advtxt and "165" in _advtxt)

print("21. Maatregel-beslislogica (welk advies wanneer)")
from engine.advies_logic import adviseer_dossier as _adl
from core.dossier import SchilDeel as _SD, Dossier as _Dos
_dl = _Dos()
_dl.schil = [_SD(id="gevel", type="gevel", isolatie_aanwezig="Nee", spouw_aanwezig=True, oppervlakte_m2=80),
             _SD(id="vloer", type="vloer", isolatie_aanwezig="Nee", begrenzing="Kruipruimte", oppervlakte_m2=50),
             _SD(id="raam-1", type="kozijn", glastype="Dubbel", oppervlakte_m2=12),
             _SD(id="gevel-ok", type="gevel", isolatie_aanwezig="Ja", isolatiedikte_mm=120, spouw_aanwezig=True)]
try:
    from core.dossier import Ventilatie as _V
    _dl.ventilatie = _V(systeem="A Natuurlijke ventilatie")
except Exception:
    pass
_radv = _adl(_dl)
_bd = _radv["bouwdelen"]
check("logic: spouw->spouwmuurisolatie", any(a["schildeel_id"] == "gevel" and "Spouwmuur" in a["advies"] for a in _bd))
check("logic: zwak glas->HR++", any(a["schildeel_id"] == "raam-1" and "HR++" in a["advies"] for a in _bd))
check("logic: goed geisoleerde gevel krijgt GEEN advies", not any(a["schildeel_id"] == "gevel-ok" for a in _bd))
check("logic: ventilatie-upgrade na isoleren", any("entilat" in a["advies"] for a in _radv["algemeen"]))
check("logic: kierdichting-regel", any("ierdicht" in a["advies"] for a in _radv["algemeen"]))

print("22. Dak/kopgevel-geometrie (hellend dak)")
from core.geometry import schuin_dakvlak_m2 as _sd, kopgevel_driehoek_m2 as _kd, dak_en_kopgevel as _dk
check("schuin dakvlak = footprint/cos", abs(_sd(63, 45) - 63 * (2 ** 0.5)) < 0.2)
check("kopgevel-driehoek 45gr B=6 -> 18 m2", abs(_kd(6, 45) - 18.0) < 0.1)
_z = _dk(63, 6, 45)
check("zadeldak: dak+extra gevel", _z["dak_m2"] > 63 and _z["extra_gevel_m2"] == 18.0)
check("plat dak: dak=footprint, geen extra gevel", _dk(63, 6, 30, type_dak="plat")["extra_gevel_m2"] == 0.0)
from core.geometry import ag_onder_schuin_dak as _ag
_agv, _weg = _ag(40, 8, 45, 0.7)
check("zolder Ag <1.5m wordt afgetrokken", abs(_agv - 27.2) < 0.1 and abs(_weg - 12.8) < 0.1)
check("zolder kniewand>=1.5m: geen reductie", _ag(40, 8, 45, 1.5)[0] == 40.0)
from core.geometry import dakkapel_vlakken as _dkp, oppervlak_vorm as _ov
check("dakkapel -> extra gevel + plat dak", _dkp(2.5, 1.4, 1.2)["gevel_m2"] > 0 and _dkp(2.5, 1.4, 1.2)["dak_m2"] == 3.0)
check("vorm driehoek = 0.5*a*b", _ov("driehoek", 6, 3) == 9.0)

print("23. Hart-op-hart gevel-toeslag woningscheidende wand (ISSO 82.1 par. 8.2)")
from core.geometry import (aantal_woningscheidende_wanden as _awsw,
                           woningscheidende_wand_toeslag_m2 as _wswt,
                           HARTMAAT_GEBOUWSCHEIDENDE_WAND_M as _hm)
check("aantal buurwanden: vrijstaand=0", _awsw("Vrijstaand") == 0)
check("aantal buurwanden: hoek/eind=1", _awsw("Kop-, eind- of hoekligging") == 1)
check("aantal buurwanden: tussen=2", _awsw("Tussenligging") == 2)
check("aantal buurwanden: 2-onder-1-kap=1", _awsw("Twee onder een kap") == 1)
check("halve wanddikte = 0,11 m", abs(_hm - 0.11) < 1e-9)
# ISSO 8.2: gevelbreedte +0,11 m/buurwand, geldt voor voor- EN achtergevel -> 2*n*0,11*h
check("toeslag tussen = 0,44*h (2*2*0,11)", abs(_wswt(2.6, "Tussenligging") - 0.44 * 2.6) < 0.01)
check("toeslag hoek = 0,22*h (2*1*0,11)", abs(_wswt(2.6, "Hoekwoning") - 0.22 * 2.6) < 0.01)
check("toeslag vrijstaand = 0", _wswt(2.6, "Vrijstaand") == 0.0)
check("toeslag zonder hoogte = 0", _wswt(None, "Tussenligging") == 0.0)

print("24. MagicPlan Statistics-CSV -> dossier (parser)")
from magicplan.statistics_csv import build_dossier as _csvdos, _undot as _ud
check("undot bouwjaar-klasse", _ud("1992.t.m.2013") == "1992 t/m 2013")
check("undot subsysteem", _ud("A1.Standaard") == "A1 Standaard")
_cf = os.path.join(HERE, "fixtures", "statistics_voorbeeld.csv")
_cd, _cn = _csvdos(_cf, straat="Test", huisnummer="1", postcode="1234AB", plaats="Plaats")
_cgev = [s for s in _cd.schil if s.type == "gevel"]
_ckoz = [s for s in _cd.schil if s.type == "kozijn"]
check("csv: bouwjaar uit klasse = 1992", _cd.identificatie.bouwjaar == 1992)
check("csv: 2 gevels per orientatie (ZW+NO)", {s.orientatie for s in _cgev} == {"ZW", "NO"})
check("csv: gevel-m2 = surface-zonder-openingen (9+9)", abs(sum(s.oppervlakte_m2 for s in _cgev) - 18.0) < 0.1)
check("csv: 2 kozijnen (binnendeur uitgefilterd)", len(_ckoz) == 2)
check("csv: ventilatie A / A1", _cd.ventilatie.systeem == "A" and _cd.ventilatie.subsysteem_code == "A1")
check("csv: verwarming HR107", _cd.installaties.verwarming.type_opwekker == "HR107")
check("csv: qv10 gelezen maar niet-gemeten", _cd.opname.qv10_waarde == 1.25 and _cd.opname.qv10_gemeten is False)
check("csv: woningtype-ontbreekt geflagd", any("Woningtype" in n for n in _cn))

print("25. Dak-per-vlak (hellingshoek uit nok + zadeldak-vlakken + parser-pad)")
from core.geometry import hellingshoek_uit_nok as _huk, dak_vlakken_zadeldak as _dvz
check("hellingshoek nok: breedte6 nok3 -> 45", _huk(6, 3, 0) == 45.0)
check("hellingshoek nok: knieschot meegerekend ~26.6", abs(_huk(8, 2.5, 0.5) - 26.6) < 0.2)
check("hellingshoek lessenaar (1 schuine zijde)", abs(_huk(4, 2, 0, 1) - 26.6) < 0.2)
_dv = _dvz(40, 8, 45, ("ZW", "NO"), ("NW",))
check("zadeldak: 2 schuine dakvlakken", sum(1 for v in _dv if v["kind"] == "dak") == 2)
check("zadeldak: schuin vlak = footprint/cos/2",
      abs([v for v in _dv if v["kind"] == "dak"][0]["m2"] - (40 * (2 ** 0.5)) / 2) < 0.1)
check("zadeldak: kopgevel-driehoek als gevel",
      any(v["kind"] == "gevel" and v["type"] == "kopgevel-driehoek" for v in _dv))
import tempfile as _tf
_dakcsv = ("PLAN ATTRIBUTES\nExterior perimeter: m,20,\nFloors,2,\n,Test\nBouwjaar,1992.t.m.2013\n"
           "Type dak,Zadeldak\nHellingshoek dak,45\nDak vloerbreedte,8\nDak orientatie zijde 1,ZW\n"
           "Dak orientatie zijde 2,NO\nKopgevel orientatie 1,NW\nPlat dak m2,6\nPlat dak orientatie,horizontaal\n\n"
           "FLOOR ATTRIBUTES,Ground surface without walls,Ceiling Height,Begrenzing\n"
           "Ground Floor,40,2.50 m,Kruipruimte\n\n"
           "WALL ATTRIBUTES,Wall,Symbol,Surf,SurfNoOpen,Width,Height,Ann,Type,Isol,Rekenzone,Orientatie\n"
           "Ground Floor,\nKitchen,Wall 0,Wall,10,9,4,2.5,1,Wall,,1,ZW\n")
_tp = _tf.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
_tp.write(_dakcsv); _tp.close()
_dd, _dn = _csvdos(_tp.name)
_dak = [s for s in _dd.schil if s.type == "dak"]
check("parser dak: 2 schuine + 1 plat dak", len(_dak) == 3 and any(s.subtype == "plat" for s in _dak))
check("parser dak: kopgevel als gevel NW",
      any(s.type == "gevel" and s.orientatie == "NW" and "kopgevel" in (s.subtype or "") for s in _dd.schil))

print("26. CSV-parser nieuwe opname-velden (woningtype/gevelhoogte/renovatiejaar/thermische massa)")
_velcsv = ("PLAN ATTRIBUTES\nExterior perimeter: m,20,\nBouwjaar,1992.t.m.2013\n"
           "Woningtype,Tussenwoning\nGevelhoogte (m),5.4\nRenovatiejaar,2015\n"
           "Thermische massa wanden,Zwaar\nThermische massa vloeren,Licht\n"
           "Qv10-waarde (dm3/s.m2),\n\n"
           "FLOOR ATTRIBUTES,Ground surface without walls,Ceiling Height,Begrenzing\n"
           "Ground Floor,40,2.50 m,Kruipruimte\n\n"
           "WALL ATTRIBUTES,Wall,Symbol,Surf,SurfNoOpen,Width,Height,Ann,Type,Isol,Rekenzone,Orientatie\n"
           "Ground Floor,\nKitchen,Wall 0,Wall,10,9,4,2.5,1,Wall,,1,ZW\n")
_vp = _tf.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
_vp.write(_velcsv); _vp.close()
_vd, _vn = _csvdos(_vp.name)
check("csv: woningtype uit veld", _vd.identificatie.woningtype == "Tussenwoning")
check("csv: gevelhoogte uit veld", _vd.opname.gevelhoogte_m == 5.4)
check("csv: renovatiejaar uit veld", _vd.identificatie.renovatiejaar == 2015)
check("csv: thermische massa wanden=Zwaar", _vd.opname.thermische_massa_wanden == "Zwaar")
check("csv: thermische massa vloeren=Licht", _vd.opname.thermische_massa_vloeren == "Licht")
check("csv: tussenwoning hart-op-hart-toeslag toegepast",
      any("hart-op-hart" in (s.opmerkingen or "") for s in _vd.schil if s.type == "gevel"))
check("csv: thermische massa gevuld zonder handmatig-flag", not any("HANDMATIG" in n for n in _vn))
# CLI-arg overrulet het CSV-veld
_vd2, _ = _csvdos(_vp.name, woningtype="Vrijstaand", gevelhoogte_m=3.0)
check("csv: CLI-arg overrulet veld (woningtype+gevelhoogte)",
      _vd2.identificatie.woningtype == "Vrijstaand" and _vd2.opname.gevelhoogte_m == 3.0)
# VABI objecten-generator: thermische massa nu volledig gewired (0=Licht/1=Zwaar/2=Zeer zwaar)
from vabi.objecten_generate import build_tree as _objbuild
_otree, _omap, _oiss, _ostats = _objbuild(_vd)
_alg_v = next((a for a in _otree.iter() if a.tag.rsplit("}", 1)[-1] == "Algemeen" and a.find("Bouwjaar") is not None), None)
check("obj-gen: Licht-vloer -> TypeBouwwijzeVloeren=0", _alg_v is not None and _alg_v.findtext("TypeBouwwijzeVloeren") == "0")
check("obj-gen: Zwaar-wand -> TypeBouwwijzeWanden=1", _alg_v is not None and _alg_v.findtext("TypeBouwwijzeWanden") == "1")

# Ag + vloer-perimeter dossier-gestuurd in de objecten-XML
from xml.etree import ElementTree as _ET
_agcsv = ("PLAN ATTRIBUTES\nExterior perimeter: m,24,\nBouwjaar,1992.t.m.2013\n"
          "Woningtype,Vrijstaand\nGevelhoogte (m),5.4\nTotal living area,120\n\n"
          "FLOOR ATTRIBUTES,Ground surface without walls,Ceiling Height,Begrenzing\n"
          "Ground Floor,60,2.50 m,Kruipruimte\nFirst Floor,60,2.50 m,Buitenlucht\n\n"
          "ROOM ATTRIBUTES\nLiving room,70\nBedroom,50\n\n"
          "WALL ATTRIBUTES,Wall,Symbol,Surf,SurfNoOpen,Width,Height,Ann,Type,Isol,Rekenzone,Orientatie\n"
          "Ground Floor,\nLiving room,Wall 0,Wall,10,9,4,2.5,1,Wall,,1,ZW\n")
_ap = _tf.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
_ap.write(_agcsv); _ap.close()
_ad, _an = _csvdos(_ap.name)
check("csv: vloer-perimeter = buitenomtrek (24)",
      any(s.type == "vloer" and s.perimeter_m == 24.0 for s in _ad.schil))
_atree, _amap, _aiss, _astats = _objbuild(_ad)
_axml = _ET.tostring(_atree, encoding="unicode")
_alg = next((a for a in _atree.iter() if a.tag.rsplit("}", 1)[-1] == "Algemeen"
             and a.find("Bouwjaar") is not None), None)
# EPA enum-mismatch-fix (23-6): de DIRECTE Rekenzone>Algemeen-<Gebruiksoppervlakte> is een ENUM/vlag
# (echte export = "1"), GEEN m2-veld -> overschrijven met de gemeten m2 gaf "Enum mismatch" bij objecten-
# import. De Ag dragen we via de Verdiepingen-som (zie check hieronder). Dus dit veld NIET op 120 zetten.
check("obj-gen: rekenzone-<Gebruiksoppervlakte> NIET overschreven met m2 (enum, geen oppervlak)",
      _alg is not None and _alg.find("Gebruiksoppervlakte").text != "120.00")
check("obj-gen: bouwjaar uit dossier (1992) i.p.v. sjabloon (1994)",
      _alg is not None and _alg.find("Bouwjaar").text == "1992")
_verd_sum = round(sum(float(v.find("Gebruiksoppervlakte").text)
                      for v in _alg.find("Verdiepingen") if v.tag.rsplit("}", 1)[-1] == "Verdieping"), 1)
check("obj-gen: Verdiepingen-som = Ag (120)", _verd_sum == 120.0)
check("obj-gen: AantalBouwlagenRekenzone = 2", _alg.find("AantalBouwlagenRekenzone").text == "2")
# objecten-sjabloon MOET versie-consistent zijn met de constructie-sjabloon (beide 12.0.1) -> anders
# importeert EPA niet. Het oude objecten-sjabloon was 12.0.0 (120000061); nu 12.0.1 (live bewezen 23-6).
check("obj-gen: XmlVersie = 120001001 (sjabloon versie-consistent met constructies)",
      _atree.findtext("XmlVersie") == "120001001")
# vloer-hoofdvlak heeft de perimeter 24
_vloer_hv = [h for h in _atree.iter() if h.tag.rsplit("}", 1)[-1] == "Hoofdvlak"
             and (h.findtext("NaamConstructie") or "").lower().startswith("vloer")]
check("obj-gen: vloer-hoofdvlak perimeter = 24",
      any((h.findtext("Perimeter") or "") == "24.00" for h in _vloer_hv))

# qv10: niet-gemeten -> forfaitair (Qv10Gemeten != 1); gemeten -> wel geschreven (ISSO 7.1.5)
def _alg_of(_tree):
    return next((a for a in _tree.iter() if a.tag.rsplit("}", 1)[-1] == "Algemeen"
                 and a.find("Bouwjaar") is not None), None)
_ad.opname.qv10_waarde = 1.25; _ad.opname.qv10_gemeten = False
_t_ng = _alg_of(_objbuild(_ad)[0])
check("obj-gen: qv10 niet-gemeten -> forfaitair (Gemeten!=1)", _t_ng.findtext("Qv10Gemeten") != "1")
_ad.opname.qv10_gemeten = True
_t_g = _alg_of(_objbuild(_ad)[0])
check("obj-gen: qv10 gemeten -> Gemeten=1 + waarde",
      _t_g.findtext("Qv10Gemeten") == "1" and _t_g.findtext("Qv10Waarde") == "1.250")

# begrenzing -> GrenstAan (uit echt sjabloon afgeleid: 0 buiten / 2 grond / 3 kruipruimte / 4 AOR)
from vabi.objecten_generate import _grenst_aan_code as _gac
check("grenstaan: buitenlucht=0", _gac("Buitenlucht") == "0")
check("grenstaan: grond=2", _gac("Grond") == "2")
check("grenstaan: kruipruimte=3", _gac("Kruipruimte") == "3")
check("grenstaan: water=1 (EPA-bevestigd)", _gac("Water") == "1")
check("grenstaan: onverwarmde kelder=7", _gac("Onverwarmde kelder") == "7")
check("grenstaan: AOR basis = buitenlucht (0)", _gac("AOR") == "0")
check("grenstaan: AOR detail = 4", _gac("AOR", basis=False) == "4")
check("grenstaan: AOS basis=0 / detail=5", _gac("AOS") == "0" and _gac("AOS", basis=False) == "5")
check("grenstaan: ASGR detail = 6", _gac("ASGR", basis=False) == "6")
check("grenstaan: onbekend -> None (niet gokken)", _gac("Iets onbekends xyz") is None)
for _s in _ad.schil:
    if _s.type == "vloer":
        _s.begrenzing = "Grond"
_vl_gr = [h for h in _objbuild(_ad)[0].iter() if h.tag.rsplit("}", 1)[-1] == "Hoofdvlak"
          and (h.findtext("NaamConstructie") or "").lower().startswith("vloer")]
check("obj-gen: vloer-begrenzing Grond -> GrenstAan 2", any(h.findtext("GrenstAan") == "2" for h in _vl_gr))
for _s in _ad.schil:
    if _s.type == "vloer":
        _s.begrenzing = "Iets onbekends xyz"
check("obj-gen: onbekende begrenzing geflagd (niet gegokt)",
      any("GrenstAan-mapping" in i for i in _objbuild(_ad)[2]))

# dak Hellingshoek-ENUM: plat=6 / hellend=3 (geverifieerd vabi_enums; GEEN rauwe graden)
from core.dossier import SchilDeel as _SD
_ad.schil.append(_SD(id="dakplat", type="dak", subtype="plat", begrenzing="Buitenlucht",
                     orientatie="", oppervlakte_m2=20.0, hellingshoek=0, rekenzone=1))
_ad.schil.append(_SD(id="dakhel", type="dak", subtype="schuin", begrenzing="Buitenlucht",
                     orientatie="ZW", oppervlakte_m2=30.0, hellingshoek=45, rekenzone=1))
_dakhv = {(h.findtext("Naam") or ""): h.findtext("Hellingshoek") for h in _objbuild(_ad)[0].iter()
          if h.tag.rsplit("}", 1)[-1] == "Hoofdvlak" and "dak" in (h.findtext("Naam") or "").lower()}
check("obj-gen: plat dakvlak -> Hellingshoek 6", _dakhv.get("Dak dakplat") == "6")
check("obj-gen: hellend dakvlak -> Hellingshoek 3", _dakhv.get("Dak dakhel") == "3")

# Gebouwhoogte uit opname (vrije float; gevelhoogte_m=5.4 uit agcsv)
_gh = next((e for e in _objbuild(_ad)[0].iter() if e.tag.rsplit("}", 1)[-1] == "Gebouwhoogte"), None)
check("obj-gen: Gebouwhoogte uit opname (5.40)", _gh is not None and _gh.text == "5.40")
# perimeter-guard: vloer Buitenlucht -> GEEN perimeter-override (ISSO 8.3 alleen grond/kruip/kelder)
for _s in _ad.schil:
    if _s.type == "vloer":
        _s.begrenzing = "Buitenlucht"; _s.perimeter_m = 30.0
_vl_bl = [h for h in _objbuild(_ad)[0].iter() if h.tag.rsplit("}", 1)[-1] == "Hoofdvlak"
          and (h.findtext("NaamConstructie") or "").lower().startswith("vloer")]
check("obj-gen: vloer Buitenlucht -> geen perimeter-override",
      all((h.findtext("Perimeter") or "") != "30.00" for h in _vl_bl))

print("27. Parser parent/child: begrenzing-naamconventie + kozijn A/B/C + Qv10-gemeten")
def _wrow(d, n=18):
    rr = [""] * n
    for kk, vv in d.items():
        rr[kk] = str(vv)
    return ",".join(rr)
_nc = "\n".join([
    "PLAN ATTRIBUTES", "Exterior perimeter: m,20,", "Bouwjaar,1975 t/m 1982",
    "Woningtype,Tussenwoning", "Gevelhoogte (m),6", "Qv10 gemeten?,Ja", "Qv10-waarde (dm3/s.m2),0.8", "",
    "FLOOR ATTRIBUTES,Ground surface without walls,Ceiling Height,Begrenzing",
    "Ground Floor,60,2.60 m,Kruipruimte", "",
    "WALL ATTRIBUTES,c1,c2,Surface,SurfNoOpen,c5,c6,c7,Type,Isol,c10,Orientatie,Bron,c13,c14,Kozijn,Glas,RaamOrient",
    "Ground Floor",
    _wrow({0: "Voorgevel", 3: 18, 4: 18, 8: "Wall", 11: "ZW"}),
    _wrow({0: "raam1", 3: 3.5, 8: "Window", 15: "B", 16: "HR++ glas", 17: "ZW"}),
    _wrow({0: "Achtergevel AOR garage", 3: 18, 4: 18, 8: "Wall", 11: "NO"}),
    _wrow({0: "buurwand AVR", 3: 18, 4: 18, 8: "Wall", 11: "O"}), "",
])
_npf = _tf.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
_npf.write(_nc); _npf.close()
_nd, _nn = _csvdos(_npf.name)
_gev = {s.orientatie: s for s in _nd.schil if s.type == "gevel"}
check("csv: gevel AOR uit wandnaam (NO)", bool(_gev.get("NO")) and _gev["NO"].begrenzing == "AOR")
check("csv: AVR-wand uitgesloten uit schil (geen O-gevel)", "O" not in _gev)
check("csv: 'Qv10 gemeten?'=Ja -> qv10_gemeten True", _nd.opname.qv10_gemeten is True)
_ram = [s for s in _nd.schil if s.subtype == "Raam"]
check("csv: raam erft begrenzing van moederwand (ZW=Buitenlucht)", bool(_ram) and _ram[0].begrenzing == "Buitenlucht")
check("csv: kozijn B -> Metaal thermisch onderbroken", bool(_ram) and _ram[0].kozijnmateriaal == "Metaal thermisch onderbroken")

# NL-ruimtenamen correct classificeren (anders ventilatiebalans fout) — gevonden in de ultieme check
from magicplan.statistics_csv import _functie_uit_naam as _fun
check("functie: Woonkamer -> verblijfsruimte", _fun("Woonkamer") == "verblijfsruimte")
check("functie: Keuken -> keuken", _fun("Keuken") == "keuken")
check("functie: Slaapkamer 1 -> slaapkamer", _fun("Slaapkamer 1") == "slaapkamer")
check("functie: Badkamer -> badkamer", _fun("Badkamer") == "badkamer")
from core.dossier import Ruimte as _R
_vres = vent_bereken([_R(naam="Woonkamer", functie="verblijfsruimte", oppervlakte_m2=30),
                      _R(naam="Keuken", functie="keuken", oppervlakte_m2=12),
                      _R(naam="Slaapkamer", functie="slaapkamer", oppervlakte_m2=14)])
check("ventilatie NL: keuken afvoer 21 + woonkamer toevoer 21",
      any(r["functie"] == "keuken" and r["afvoer"] == 21.0 for r in _vres["rows"])
      and any(r["functie"] == "verblijfsruimte" and r["toevoer"] == 21.0 for r in _vres["rows"]))

print("\n28. Installaties: PV-knoop + verwarming/tapwater-codes (LIVE geharvest uit EPA)")
from core.dossier import ZonneEnergieSysteem as _ZE
import vabi.installatie_generate as _ig
def _iloc(e): return e.tag.rsplit('}', 1)[-1]

_id = build_sample()
_id.installaties.zonne_energie = [_ZE(systeem="PV-panelen", aantal=12, oppervlak_per_paneel_m2=1.7,
    orientatie="Zuid", hellingshoek=35, pv_type="Monokristallijn", fabricagejaar="Vanaf 2018",
    bouwintegratie="Goed geventileerd")]
_ir, _iflags = _ig.build_tree(_id)
_ze = [e for e in _ir.iter() if _iloc(e) == "ZonneEnergie"]
_zd = {_iloc(c): (c.text or "").strip() for c in _ze[0]} if _ze else {}
check("inst: PV ZonneEnergiesysteem=0 (PV-panelen)", _zd.get("ZonneEnergiesysteem") == "0")
check("inst: PV paneeltype Mono=1", _zd.get("PiekvermogenPVPanelen") == "1")
check("inst: PV fabricagejaar Vanaf2018=4", _zd.get("FabricagejaarPVPanelen") == "4")
check("inst: PV oriëntatie Zuid=4 (PV-enum, niet geometrie)", _zd.get("Orientatie") == "4")
check("inst: PV bouwintegratie Goed=2", _zd.get("Bouwintegratie") == "2")
check("inst: PV hellingshoek rauwe graden (35)", _zd.get("Hellingshoek") == "35")
check("inst: PV aantal panelen 12", _zd.get("AantalPanelen") == "12")

_id2 = build_sample(); _id2.installaties.zonne_energie = []
_ir2, _ = _ig.build_tree(_id2)
check("inst: geen PV -> ZonneEnergie-knoop verwijderd (geen fantoom)",
      not [e for e in _ir2.iter() if _iloc(e) == "ZonneEnergie"])

_op = [e for e in _ir.iter() if _iloc(e) == "VerwarmingOpwekker"][0]
check("inst: gasketel -> TypeOpwekker 4", _op.find("TypeOpwekker").text == "4")
_id.installaties.verwarming.type_opwekker = "Warmtepomp elektrisch"
_ir3, _f3 = _ig.build_tree(_id)
check("inst: warmtepomp NIET auto-gecodeerd -> geflagd (golden rule)",
      any("warmtepomp" in f.lower() or "opwekkertype" in f.lower() for f in _f3))
_id.installaties.tapwater.type_toestel = "Gasgestookt combitoestel"
_ir4, _ = _ig.build_tree(_id)
_top = [e for e in _ir4.iter() if _iloc(e) == "TapwaterOpwekker"][0]
check("inst: tapwater combitoestel -> TypeToestel 10", _top.find("TypeToestel").text == "10")

print("\n29. Opname-tokens: narekenen-vlag + per-wand isolatie-override + vloer-split + Ag-aftrek <1,5 m")
_tok = "\n".join([
    "PLAN ATTRIBUTES", "Exterior perimeter: m,24,", "Bouwjaar,1975 t/m 1982",
    "Woningtype,Tussenwoning", "Gevelhoogte (m),6", "Isolatie aanwezig,Ja",
    "Begrenzing (vloer),Kruipruimte", "Ag-aftrek zolder (m2),8", "Total living area,100", "",
    "FLOOR ATTRIBUTES,Ground surface without walls,Ceiling Height,Begrenzing",
    "Ground Floor,60,2.50 m,Kruipruimte", "",
    "ROOM ATTRIBUTES", "Woonkamer,40", "Studeerkamer grond,20", "",
    "WALL ATTRIBUTES,c1,c2,Surface,SurfNoOpen,c5,c6,c7,Type,Isol,c10,Orientatie,Bron,c13,c14,Kozijn,Glas,RaamOrient",
    "Ground Floor",
    _wrow({0: "Voorgevel", 3: 18, 4: 18, 8: "Wall", 11: "ZW"}),
    _wrow({0: "Zijgevel ongeisoleerd", 3: 12, 4: 12, 8: "Wall", 11: "NO"}),
    _wrow({0: "Achtergevel narekenen", 3: 18, 4: 18, 8: "Wall", 11: "O"}), "",
])
_tkp = _tf.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
_tkp.write(_tok); _tkp.close()
_td, _tn = _csvdos(_tkp.name)
_tgev = {s.orientatie: s for s in _td.schil if s.type == "gevel"}
check("token: per-wand 'ongeisoleerd' -> isolatie_aanwezig Nee (override)",
      bool(_tgev.get("NO")) and _tgev["NO"].isolatie_aanwezig == "Nee")
check("token: normale gevel houdt projectdefault (Ja)",
      bool(_tgev.get("ZW")) and _tgev["ZW"].isolatie_aanwezig == "Ja")
check("token: 'narekenen'-wand -> flag in notes", any("NAREKENEN" in n for n in _tn))
check("token: narekenen-gevel heeft opmerking", any("NAREKENEN" in (s.opmerkingen or "") for s in _td.schil if s.type == "gevel"))
_tvl = [s for s in _td.schil if s.type == "vloer"]
check("token: ruimtenaam 'grond' -> apart vloerdeel met begrenzing Grond",
      any(s.begrenzing == "Grond" and abs((s.oppervlakte_m2 or 0) - 20.0) < 0.1 for s in _tvl))
check("token: hoofdvloer verlaagd met het grond-deel (60-20=40)",
      any(s.subtype == "Begane grondvloer" and abs((s.oppervlakte_m2 or 0) - 40.0) < 0.1 for s in _tvl))
check("token: Ag-aftrek zolder 8 m² toegepast (100-8=92)",
      abs((_td.geometrie.gebruiksoppervlakte_ag_m2 or 0) - 92.0) < 0.1)
check("token: Ag-aftrek gemeld in notes", any("Ag verlaagd" in n for n in _tn))

print("\n30. Objecten<->constructies: gedeelde (deterministische) GUIDs — EPA enum-mismatch-fix")
from vabi.constructie_generate import resolve_constructies as _rc
import vabi.constructie_generate as _cg2, vabi.objecten_generate as _og2
import xml.etree.ElementTree as _ETg
_dzg = build_sample()
_m1 = _rc(_dzg)[1]; _m2 = _rc(_dzg)[1]
check("guid deterministisch over 2 aanroepen (zelfde per constructie)",
      bool(_m1) and all(_m1[k]["guid"] == _m2[k]["guid"] for k in _m1))
_tdg = _tf.mkdtemp()
_cpg = os.path.join(_tdg, "c.xml"); _opg = os.path.join(_tdg, "o.xml")
_cg2.write(_dzg, _cpg); _og2.write(_dzg, _opg)
def _loc2(e): return e.tag.rsplit("}", 1)[-1]
_cguids = set((c.findtext("Guid") or "").strip().lower()
              for c in _ETg.parse(_cpg).getroot().iter() if _loc2(c) == "Constructie")
_orefs = set((e.text or "").strip().lower()
             for e in _ETg.parse(_opg).getroot().iter() if _loc2(e) == "Constructie" and (e.text or "").strip())
check("objecten constructie-refs bestaan ALLEMAAL in constructiebib (geen EPA enum-mismatch)",
      bool(_orefs) and not (_orefs - _cguids))

print("\n31. Gevel-naamgeving -> oriëntatie-afleiding + meerdere PV + kwaliteitsverklaring-flag")
from magicplan.statistics_csv import (_orient_afleiden as _oa, _orient_uit_naam as _ou,
                                      _gevel_naam_uit_naam as _gn)
# 8-punts rotatie (Oost-vanaf-straat): voorgevel Z -> rechter O, links W, achter N
check("afleiden: voorgevel Z -> rechtergevel O", _oa("rechts", "Z") == "O")
check("afleiden: voorgevel Z -> linkergevel W", _oa("links", "Z") == "W")
check("afleiden: voorgevel Z -> achtergevel N", _oa("achter", "Z") == "N")
check("afleiden: voorgevel Z -> voorgevel Z", _oa("voor", "Z") == "Z")
check("afleiden: intercardinaal voorgevel NO -> rechtergevel NW", _oa("rechts", "NO") == "NW")
check("afleiden: geen voorgevel-orientatie -> leeg", _oa("rechts", "") == "")
check("naam: 'Linkergevel ...' -> links", _gn("Linkergevel woonkamer") == "links")
check("naam: kompastoken-override 'Rechtergevel ZW' -> ZW", _ou("Rechtergevel ZW") == "ZW")
check("naam: zonder kompastoken -> leeg", _ou("Voorgevel") == "")
# CSV-integratie: 4 benoemde gevels zonder kompaskolom + naam-override + 2 PV + kwaliteitsverklaring
_gv = "\n".join([
    "PLAN ATTRIBUTES", "Bouwjaar,1975 t/m 1982", "Woningtype,Vrijstaand",
    "Orientatie voorgevel,Z", "Total living area,120", "Exterior perimeter: m,40",
    "Rc-bron gevel,Kwaliteitsverklaring",
    "Zonne-energie aanwezig?,Ja", "PV - paneeltype,Monokristallijn", "PV - aantal panelen,10", "PV - orientatie,Zuid",
    "PV-2 - paneeltype,Polykristallijn", "PV-2 - aantal panelen,6", "PV-2 - orientatie,Oost", "",
    "FLOOR ATTRIBUTES,Ground surface without walls,Ceiling Height,Begrenzing",
    "Ground Floor,80,2.60 m,Kruipruimte", "",
    "WALL ATTRIBUTES,c1,c2,Surface,SurfNoOpen,c5,c6,c7,Type,Isol,c10,Orientatie,Bron",
    "Ground Floor",
    _wrow({0: "Voorgevel", 3: 30, 4: 27, 8: "Wall"}),
    _wrow({0: "Achtergevel", 3: 30, 4: 28, 8: "Wall"}),
    _wrow({0: "Linkergevel", 3: 20, 4: 20, 8: "Wall"}),
    _wrow({0: "Rechtergevel ZW", 3: 20, 4: 20, 8: "Wall"}), "",   # naam-override ZW i.p.v. afgeleid O
])
_gp = _tf.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
_gp.write(_gv); _gp.close()
_gd, _gnotes = _csvdos(_gp.name)
_gmap = {s.orientatie: s for s in _gd.schil if s.type == "gevel"}
check("csv: voorgevel afgeleid Z (naam=voor)", bool(_gmap.get("Z")) and _gmap["Z"].gevel_naam == "voor")
check("csv: achtergevel afgeleid N", bool(_gmap.get("N")) and _gmap["N"].gevel_naam == "achter")
check("csv: linkergevel afgeleid W", bool(_gmap.get("W")) and _gmap["W"].gevel_naam == "links")
check("csv: rechtergevel kompas-override ZW wint van afgeleid O",
      "O" not in _gmap and bool(_gmap.get("ZW")) and _gmap["ZW"].gevel_naam == "rechts")
check("csv: 2 PV-systemen ingelezen", len(_gd.installaties.zonne_energie) == 2)
check("csv: 2e PV = polykristallijn/Oost",
      any("poly" in (z.pv_type or "").lower() for z in _gd.installaties.zonne_energie))
check("csv: gevels rc_bron = Kwaliteitsverklaring",
      bool([s for s in _gd.schil if s.type == "gevel"])
      and all(s.rc_bron == "Kwaliteitsverklaring" for s in _gd.schil if s.type == "gevel"))
check("csv: kwaliteitsverklaring geflagd in notes", any("kwaliteitsverklaring" in n.lower() for n in _gnotes))
# constructie-generator vlagt de kwaliteitsverklaring
_kvdir = _tf.mkdtemp(); _kvpath = os.path.join(_kvdir, "c.xml")
from vabi.constructie_generate import write as _cwrite2
_, _kviss = _cwrite2(_gd, _kvpath)
check("constr-gen: kwaliteitsverklaring -> issue voor adviseur",
      any("kwaliteitsverklaring" in i.lower() for i in _kviss))

print("\n32. MagicPlan form_push: merge + validatie (offline)")
import magicplan.form_push as _fp
_fform = {"name": "Nij Begun", "context": ["plan"], "children": [
    {"id": "s1", "name": "Gevels", "type": "section", "comparisonValue": None},
    {"id": "q1", "name": "Geveltype", "type": "question", "dataType": "list", "comparisonValue": None, "required": True},
    {"id": "s2", "name": "Vloer & Dak", "type": "section", "comparisonValue": None},
]}
_frec = {"id": "rec1", "form": _fform}
_fadd = _fp.load_additions()
_frec, _fadded, _freq, _fprobs = _fp.merge_record(_frec, _fadd, verbose=False)
check("form_push: 'Oriëntatie voorgevel' toegevoegd", "Oriëntatie voorgevel" in _fadded)
check("form_push: Rc-bron gevel/vloer/dak toegevoegd (4 velden totaal)", len(_fadded) == 4)
check("form_push: geen validatieproblemen", _fprobs == [])
check("form_push: nieuw veld na de juiste sectie (Gevels)",
      any(c.get("name") == "Oriëntatie voorgevel" for c in _fp._form_of(_frec)["children"]))
check("form_push: idempotent (2e merge voegt 0 toe)",
      _fp.merge_record({"id": "rec1", "form": _fp._form_of(_frec)}, _fadd, verbose=False)[1] == [])
check("form_push: name_escaped gestript + context = string-array",
      "name_escaped" not in json.dumps(_frec) and _fp._form_of(_frec)["context"] == ["plan"])

print("\n33. Schilddak/lessenaar + rekenzone")
from core.geometry import (dak_vlakken_schilddak as _ds, dak_vlakken_lessenaar as _dl,
                           dak_vlakken_zadeldak as _dz)
check("geom: lessenaar = 1 dakvlak (footprint/cos)", len(_dl(60, 30, "O")) == 1 and _dl(60, 30, "O")[0]["kind"] == "dak")
_sch = _ds(60, 45, ("N", "O", "Z", "W"))
check("geom: schilddak = alleen dakvlakken (GEEN kopgevel-gevel)", len(_sch) == 4 and all(v["kind"] == "dak" for v in _sch))
check("geom: zadeldak heeft wél een kopgevel-gevel", any(v["kind"] == "gevel" for v in _dz(60, 6, 45, ("O", "W"), ("N", "Z"))))
from magicplan.statistics_csv import _rekenzone_uit_naam as _rzn
check("parser: 'Rechtergevel zone2' -> rekenzone 2", _rzn("Rechtergevel zone2") == 2)
check("parser: 'Slaapkamer rekenzone 3' -> 3", _rzn("Slaapkamer rekenzone 3") == 3)
check("parser: gewone naam -> rekenzone 1", _rzn("Voorgevel") == 1)
_sv = "\n".join([
    "PLAN ATTRIBUTES", "Woningtype,Vrijstaand", "Orientatie voorgevel,Z", "Total living area,120",
    "Exterior perimeter: m,40", "Type dak,Schilddak", "Hellingshoek dak,45",
    "Dak orientatie zijde 1,Z", "Dak orientatie zijde 2,N", "Kopgevel orientatie 1,O", "Kopgevel orientatie 2,W",
    "Ventilatie - rekenzone,2", "",
    "FLOOR ATTRIBUTES,Ground surface without walls,Ceiling Height,Begrenzing", "Ground Floor,80,2.6 m,Kruipruimte", "",
    "WALL ATTRIBUTES,c1,c2,Surface,SurfNoOpen,c5,c6,c7,Type,Isol,c10,Orientatie,Bron", "Ground Floor",
    _wrow({0: "Voorgevel", 3: 30, 4: 28, 8: "Wall"}),
    _wrow({0: "Rechtergevel zone2", 3: 20, 4: 20, 8: "Wall"}), "",
])
_svp = _tf.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8"); _svp.write(_sv); _svp.close()
_svd, _svn = _csvdos(_svp.name)
_dak = [s for s in _svd.schil if s.type == "dak"]
check("csv: schilddak -> 4 dakvlakken", len(_dak) == 4 and all("schild" in (s.subtype or "") for s in _dak))
check("csv: schilddak geeft GEEN kopgevel-gevel", not any("kopgevel" in (s.subtype or "") for s in _svd.schil))
_rg = [s for s in _svd.schil if s.type == "gevel" and s.orientatie == "O"]
check("csv: 'Rechtergevel zone2' -> gevel rekenzone 2", bool(_rg) and _rg[0].rekenzone == 2)
check("csv: ventilatie rekenzone 2 uit Installaties-form", _svd.ventilatie.rekenzone == 2)
check("csv: meerdere rekenzones geflagd", any("rekenzone" in n.lower() and "zone 2" in n for n in _svn))

print("\n34. Webapp: maatregel-selectie + visueel ventilatieplan")
from dashboard.measures import laad_catalog as _lc, suggesties as _sug, bouw_maatregelen as _bm
_wcat = _lc()
_wdos = build_sample()
_grp = _sug(_wdos, _wcat)
check("measures: advies-groepen gevonden", len(_grp) >= 1)
check("measures: elke groep heeft kandidaten + goedkoopste eerst",
      all(g["kandidaten"] and g["kandidaten"][0]["prijs"] <= g["kandidaten"][-1]["prijs"] for g in _grp))
_keuze = [{"code": g["default_code"], "onderdeel": g["onderdeel"], "m2": g["m2"],
          "rc_u_doel": g["rc_u_doel"], "subposten": []} for g in _grp]
_maat, _tot = _bm(_wcat, _keuze)
check("measures: selectie -> maatregelen met kosten", len(_maat) == len(_grp) and all(m.kosten for m in _maat))
check("measures: totaal = som maatregelkosten", abs(_tot - round(sum(m.kosten for m in _maat), 2)) < 0.01)
from ventilatie.ventilatie import bereken as _vber
from ventilatie.ventilatieplan_svg import ventilatieplan_svg as _vsvg
_vres = _vber([_R(naam="Woonkamer", functie="verblijfsruimte", oppervlakte_m2=30),
              _R(naam="Keuken", functie="keuken", oppervlakte_m2=10),
              _R(naam="Badkamer", functie="badkamer", oppervlakte_m2=6)])
_svgtxt = _vsvg(_vres, adres="Teststraat 1")
check("ventilatieplan-svg: geldige SVG-string", _svgtxt.startswith("<svg") and _svgtxt.rstrip().endswith("</svg>"))
import xml.etree.ElementTree as _ETv
check("ventilatieplan-svg: well-formed XML", bool(_ETv.fromstring(_svgtxt)))
check("ventilatieplan-svg: toont toevoer + afvoer", "l/s in" in _svgtxt and "l/s uit" in _svgtxt)

print("\n35. Webapp (Flask) — laadt + kernroutes + Beoordelingscheck")
try:
    import dashboard.app as _WA
    _WA.app.config.update(TESTING=True)
    _routes = {r.rule for r in _WA.app.url_map.iter_rules()}
    check("webapp: stappen-routes geregistreerd", {"/project/<tag>/opname", "/project/<tag>/huidig",
          "/project/<tag>/maatregelen", "/project/<tag>/vabi", "/project/<tag>/afronden",
          "/project/<tag>/export", "/guide"} <= _routes)
    _wc = _WA.app.test_client()
    check("webapp: login-pagina laadt", _wc.get("/login").status_code == 200)
    with _wc.session_transaction() as _s:   # direct inloggen (config kan echte pw_hash+MFA bevatten)
        _s["ingelogd"] = True
    _home = _wc.get("/")
    check("webapp: projecten-overzicht (ingelogd)", _home.status_code == 200)
    check("webapp: woningtype = dropdown (geen vrij tekstveld)",
          "Twee-onder-een-kap" in _home.get_data(as_text=True) and "<select name=woningtype" in _home.get_data(as_text=True))
    check("webapp: ingebouwde guide", _wc.get("/guide").status_code == 200)
    # leeg project aanmaken ZONDER bestand -> gaat naar de opname-stap
    _rn = _wc.post("/nieuw", data={"straat": "Teststraat 9", "postcode": "9999ZZ",
                   "plaats": "Groningen", "woningtype": "Hoekwoning"})
    check("webapp: leeg project zonder upload -> opname-stap",
          _rn.status_code in (302, 303) and _rn.headers["Location"].endswith("/opname"))
    _ptag = _rn.headers["Location"].rstrip("/").split("/")[-2]
    _op = _wc.get("/project/%s/opname" % _ptag)
    check("webapp: opname toont MagicPlan-import + woningtype-dropdown",
          "MagicPlan-opname inladen" in _op.get_data(as_text=True)
          and 'selected' in _op.get_data(as_text=True))
    check("webapp: huidige-staat-stap laadt (VABI-export terug)",
          _wc.get("/project/%s/huidig" % _ptag).status_code == 200)
    import shutil as _sh35
    _sh35.rmtree(_WA._pdir(_ptag), ignore_errors=True)
    _bd = _WA._beoordeling("x", {"foto_voorkant": "", "foto_huisnummer": "", "na": {}}, build_sample())
    check("webapp: Beoordelingscheck spiegelt kennisbank (>=6 punten)", len(_bd) >= 6)
except Exception as _e:
    check("webapp: laadt zonder fout", False)
    print("     " + repr(_e)[:160])

print("\n36. Catalogus-API live-mapping (JSON:API -> catalog.json)")
try:
    from catalog.api_client import map_measures_to_catalog
    _raw = {"data": [
        {"id": "V1-1-A1", "type": "measure", "attributes": {
            "name": "Spouwmuurisolatie 60", "unit": "m²", "rcValue": 1.7, "thicknessInMm": 60,
            "isBiobased": False,
            "regularCosts": [
                {"id": "V1-1-A1", "type": "cost", "attributes": {"contractorValuePerUnit": 23.09,
                 "diyValuePerUnit": 18.8, "minUnits": 0, "maxUnits": 45, "unit": "m²"}},
                {"id": "V1-1-A2", "type": "cost", "attributes": {"contractorValuePerUnit": 21.13,
                 "minUnits": 45, "maxUnits": 75, "unit": "m²"}}],
            "additionalCosts": [
                {"id": "V1-1-X7", "type": "cost", "attributes": {"contractorValuePerUnit": 91.13,
                 "unit": "won", "notes": "Betreft: Spouw richting dak dichtmaken van binnenuit"}}]}},
        {"id": "V1-2-A1", "type": "measure", "attributes": {"name": "Andere", "unit": "m²",
            "regularCosts": [{"id": "V1-2-A1", "type": "cost", "attributes": {
                "contractorValuePerUnit": 50.0, "minUnits": 0, "maxUnits": None, "unit": "m²"}}],
            "additionalCosts": [{"id": "V1-1-X7", "type": "cost", "attributes": {
                "contractorValuePerUnit": 91.13, "unit": "won", "notes": "Betreft: dubbel"}}]}},
    ]}
    _cat = map_measures_to_catalog(_raw)
    _ms = {m["code"]: m for m in _cat["maatregelen"]}
    check("api-map: 4 rijen (2 brackets + 1 bracket + 1 X; gedeelde X gededupe)", len(_cat["maatregelen"]) == 4)
    check("api-map: V1-1-A1 incl=23.09 / excl~19.08",
          _ms["V1-1-A1"]["prijs_per_eenheid_incl_btw"] == 23.09 and abs(_ms["V1-1-A1"]["prijs_per_eenheid_excl"] - 19.0826) < 0.01)
    check("api-map: bracket-tekst in omschrijving", "van 0 m² tot 45 m²" in _ms["V1-1-A1"]["omschrijving"])
    check("api-map: onderdeel uit code-prefix", _ms["V1-1-A1"]["onderdeel"] == "A Gevel")
    check("api-map: X-code 1x (gededupe over measures)",
          sum(1 for m in _cat["maatregelen"] if m["code"] == "V1-1-X7") == 1)
    check("api-map: 'Betreft:' uit X-notitie gestript", not _ms["V1-1-X7"]["omschrijving"].startswith("Betreft"))
    check("api-map: extra rc_waarde meegenomen", _ms["V1-1-A1"].get("rc_waarde") == 1.7)
except Exception as _e:
    check("api-map: mapper draait zonder fout", False)
    print("     " + repr(_e)[:160])

print("\n37. Parser: VABI-beslisboom per bouwdeel (nieuwe Constructies-form)")
try:
    import tempfile as _tf2
    from magicplan.statistics_csv import build_dossier as _bd2
    _boomcsv = ("PLAN ATTRIBUTES\nExterior perimeter: m,20,\nBouwjaar,1992.t.m.2013\nWoningtype,Tussenwoning\n"
                "Gevelhoogte (m),5.4\n"
                "Gevel - invoer,Beslisschema\nGevel - isolatie aanwezig?,Ja\nGevel - isolatiedikte onbekend?,Nee\n"
                "Gevel - isolatiedikte (mm),80\nGevel - begrenzing,Buitenlucht\n"
                "Vloer - invoer,Kwaliteitsverklaring\nVloer - begrenzing,Kruipruimte\n\n"
                "FLOOR ATTRIBUTES,Ground surface without walls,Ceiling Height,Begrenzing\n"
                "Ground Floor,40,2.50 m,Kruipruimte\n\n"
                "WALL ATTRIBUTES,Wall,Symbol,Surf,SurfNoOpen,Width,Height,Ann,Type,Isol,Rekenzone,Orientatie\n"
                "Ground Floor,\nVoorgevel,Wall 0,Wall,10,9,4,2.5,1,Wall,,1,ZW\n")
    _bp = _tf2.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8"); _bp.write(_boomcsv); _bp.close()
    _bdo, _bn = _bd2(_bp.name)
    _gev = next((s for s in _bdo.schil if s.type == "gevel"), None)
    _vlo = next((s for s in _bdo.schil if s.type == "vloer"), None)
    check("boom: gevel rc_bron=Opgemeten dikte (80mm bekend)", _gev is not None and _gev.rc_bron == "Opgemeten dikte")
    check("boom: gevel isolatie=Ja + dikte 80mm",
          _gev is not None and _gev.isolatie_aanwezig == "Ja" and _gev.isolatiedikte_mm == 80.0)
    check("boom: vloer rc_bron=Kwaliteitsverklaring (Invoer=KV)", _vlo is not None and _vlo.rc_bron == "Kwaliteitsverklaring")
except Exception as _e:
    check("boom: parser draait zonder fout", False); print("     " + repr(_e)[:160])

print("\n38. Parser: dak geconsolideerd uit Constructies + 9 m²-vakjes (type Anders)")
try:
    import tempfile as _tf3
    from magicplan.statistics_csv import build_dossier as _bd3
    _dak2 = ("PLAN ATTRIBUTES\nExterior perimeter: m,24,\nBouwjaar,1992.t.m.2013\nWoningtype,Tussenwoning\nGevelhoogte (m),5.4\n"
             "Dakvlak 1 - daktype,Zadeldak\nDak - vloerbreedte (m),8\nDakvlak 1 - hellingshoek (°),45\n"
             "Dakvlak 1 - oriëntatie,ZW\nDakvlak 2 - oriëntatie,NO\nDak - kopgevel oriëntatie 1,NW\nDak - kopgevel oriëntatie 2,ZO\n\n"
             "FLOOR ATTRIBUTES,Ground surface without walls,Ceiling Height,Begrenzing\nGround Floor,40,2.50 m,Kruipruimte\n\n"
             "WALL ATTRIBUTES,Wall,Symbol,Surf,SurfNoOpen,Width,Height,Ann,Type,Isol,Rekenzone,Orientatie\n"
             "Ground Floor,\nVoorgevel,Wall 0,Wall,10,9,4,2.5,1,Wall,,1,ZW\n")
    _dp = _tf3.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8"); _dp.write(_dak2); _dp.close()
    _ddo, _ = _bd3(_dp.name)
    check("dak-uit-Constructies: 2 schuine dakvlakken (zadeldak)", len([s for s in _ddo.schil if s.type == "dak"]) == 2)
    check("dak-uit-Constructies: kopgevel-driehoek als gevel",
          any(s.type == "gevel" and "kopgevel" in (s.subtype or "") for s in _ddo.schil))
    _av = ("PLAN ATTRIBUTES\nExterior perimeter: m,24,\nBouwjaar,1992.t.m.2013\nWoningtype,Vrijstaand\nGevelhoogte (m),5.4\n"
           "Dakvlak 1 - daktype,Anders\nDak m² Z,30\nDak m² Horizontaal,12\n\n"
           "FLOOR ATTRIBUTES,Ground surface without walls,Ceiling Height,Begrenzing\nGround Floor,40,2.50 m,Kruipruimte\n\n"
           "WALL ATTRIBUTES,Wall,Symbol,Surf,SurfNoOpen,Width,Height,Ann,Type,Isol,Rekenzone,Orientatie\n"
           "Ground Floor,\nVoorgevel,Wall 0,Wall,10,9,4,2.5,1,Wall,,1,ZW\n")
    _ap2 = _tf3.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8"); _ap2.write(_av); _ap2.close()
    _ado, _ = _bd3(_ap2.name)
    _adak = [s for s in _ado.schil if s.type == "dak"]
    check("dak 9-vakjes (Anders): 2 vlakken, Z=30 m²",
          len(_adak) == 2 and any(abs(s.oppervlakte_m2 - 30) < 0.1 for s in _adak))
except Exception as _e:
    check("dak-uit-Constructies: parser draait zonder fout", False); print("     " + repr(_e)[:170])

print("\n39. Parser: rekenzone default 1 + 2e tapwater/ventilatie")
try:
    import tempfile as _tf4
    from magicplan.statistics_csv import build_dossier as _bd4
    _ic = ("PLAN ATTRIBUTES\nExterior perimeter: m,20,\nBouwjaar,1992.t.m.2013\nWoningtype,Tussenwoning\nGevelhoogte (m),5.4\n"
           "Verwarming - type opwekker,Gasgestookte ketel\nTapwater - toestel,Combiketel (gas)\n"
           "Tapwater 2 - toestel,Elektrische boiler\nTapwater 2 - installatiejaar,2020\n"
           "Ventilatiesysteem (A-E),C Mechanische afvoer\nSubsysteem (C),C1 Standaard\n"
           "Tweede ventilatiesysteem?,Ja\nVentilatie 2 - systeem (A-E),D Mechanische balansventilatie\n\n"
           "FLOOR ATTRIBUTES,Ground surface without walls,Ceiling Height,Begrenzing\nGround Floor,40,2.50 m,Kruipruimte\n\n"
           "WALL ATTRIBUTES,Wall,Symbol,Surf,SurfNoOpen,Width,Height,Ann,Type,Isol,Rekenzone,Orientatie\n"
           "Ground Floor,\nVoorgevel,Wall 0,Wall,10,9,4,2.5,1,Wall,,1,ZW\n")
    _ip = _tf4.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8"); _ip.write(_ic); _ip.close()
    _ido, _inotes = _bd4(_ip.name)
    check("rekenzone default 1 (leeg) op ventilatie + verwarming",
          _ido.ventilatie.rekenzone == 1 and _ido.installaties.verwarming.rekenzone == 1)
    check("2e tapwater gelezen (tapwater_extra)",
          len(_ido.installaties.tapwater_extra) == 1 and "boiler" in (_ido.installaties.tapwater_extra[0].type_toestel or "").lower())
    check("2e ventilatiesysteem geflagd", any("Tweede ventilatiesysteem" in n for n in _inotes))
except Exception as _e:
    check("installaties-extra: parser draait zonder fout", False); print("     " + repr(_e)[:170])

print("\n40. Leads (Nij Begun-portal): parsen + dedupe + concept-mail + CSV")
try:
    import dashboard.leads as _L
    _mail = ('Contact met adviseur\n{"BagAdresId":"0014200099999999","Email":"piet@test.example",'
             '"Postcode":"9999XX","Huisnummer":12,"HuisnummerToevoeging":"a","Voornaam":"Piet",'
             '"Telefoonnummer":"0612345678","Achternaam":"Test","Naam":"Piet Test",'
             '"WijzigingsType":"AdviseurToegekend","WijzigingsReden":"Adviseur toegekend."}')
    _ld = _L.parse_lead(_mail)
    check("lead: JSON uit mail-tekst geparsed", _ld is not None and _ld["naam"] == "Piet Test"
          and _ld["postcode"] == "9999XX" and _ld["huisnummer"] == "12" and _ld["toevoeging"] == "a")
    _rows, _n1 = _L.add_lead(_ld, [])
    _rows, _n2 = _L.add_lead(_ld, _rows)
    check("lead: dedupe op BAG-id", _n1 and not _n2 and len(_rows) == 1 and _rows[0]["status"] == "nieuw")
    _ond, _txt = _L.concept_mail(_rows[0], {"naam": "R. Poortinga", "telefoon": "06-1", "email": "a@b.nl"})
    check("lead: concept-mail met aanhef + voorbereiding + ondertekening",
          "Beste Piet Test" in _txt and "kruipruimte" in _txt and "R. Poortinga" in _txt and "Nij Begun" in _ond + _txt)
    _csv = _L.to_csv(_rows)
    check("lead: CSV Excel-NL (puntkomma + naam erin)", ";" in _csv.splitlines()[0] and "Piet Test" in _csv)
    check("lead: onzin-tekst -> None (geen crash)", _L.parse_lead("hallo dit is geen lead") is None)
except Exception as _e:
    check("leads: module draait zonder fout", False); print("     " + repr(_e)[:170])

print("\n41. BAG-verrijking (parsers offline; structuur live geverifieerd 26-6)")
try:
    import dashboard.bag as _B
    _ls = {"response": {"docs": [
        {"weergavenaam": "Teststraat 12a, 9999XX Testdorp", "straatnaam": "Teststraat",
         "woonplaatsnaam": "Testdorp", "huis_nlt": "12a", "postcode": "9999XX",
         "nummeraanduiding_id": "0014200099999999", "adresseerbaarobject_id": "0014010099999999",
         "centroide_rd": "POINT(235729.987 585202.818)"},
        {"weergavenaam": "Teststraat 12, 9999XX Testdorp", "straatnaam": "Teststraat",
         "woonplaatsnaam": "Testdorp", "huis_nlt": "12", "postcode": "9999XX",
         "nummeraanduiding_id": "0014200088888888", "adresseerbaarobject_id": "0014010088888888",
         "centroide_rd": "POINT(1000.0 2000.0)"}]}}
    _a = _B.parse_locatieserver(_ls, "12", "a")
    check("bag: locatieserver-parse kiest exacte huisnummer+toevoeging-match",
          _a is not None and _a["verblijfsobject_id"] == "0014010099999999"
          and _a["straat"] == "Teststraat" and _a["x"] == 235729.987)
    _wfs = {"features": [
        {"properties": {"identificatie": "0014010077777777", "oppervlakte": 80, "bouwjaar": 1975,
                        "gebruiksdoel": "woonfunctie", "pandidentificatie": "p1"}},
        {"properties": {"identificatie": "0014010099999999", "oppervlakte": 109, "bouwjaar": 1982,
                        "gebruiksdoel": "woonfunctie", "pandidentificatie": "p2"}}]}
    _v = _B.parse_wfs(_wfs, "0014010099999999")
    check("bag: wfs-parse matcht op verblijfsobject-id (bbox kan buren bevatten)",
          _v is not None and _v["bouwjaar"] == 1982 and _v["oppervlakte_m2"] == 109)
    check("bag: lege respons -> None (geen crash)",
          _B.parse_locatieserver({}, "1") is None and _B.parse_wfs({}, "x") is None)
    from dashboard.leads import adres as _adr
    check("lead-adres met BAG-straat", _adr({"straat": "Teststraat", "huisnummer": "12", "toevoeging": "a",
          "woonplaats": "Testdorp", "postcode": "9999XX"}) == "Teststraat 12 a in Testdorp")
    import dashboard.app as _WA2
    check("webapp: BAG-route geregistreerd", "/leads/<int:lid>/bag" in {r.rule for r in _WA2.app.url_map.iter_rules()})
except Exception as _e:
    check("bag: module draait zonder fout", False); print("     " + repr(_e)[:170])

print("\n42. Webapp v2: opname-editor + catalogus-kiezer + varianten")
try:
    from dashboard.measures import catalogus_boom as _cb, _schoon_label as _sl, zoek_maatregel as _zm
    _cat = json.load(open(CATALOG, encoding="utf-8"))
    _boom = _cb(_cat)
    check("catalogus-boom: 6 categorieën (V1..V6)", len(_boom) == 6 and _boom[0]["naam"] == "Gevel")
    _v11 = next(s for c in _boom for s in c["subs"] if s["code"] == "V1-1")
    check("catalogus-boom: V1-1 heeft kern + bijkomende kosten (X)",
          len(_v11["kern"]) > 0 and any(r["code"].split("-")[2].startswith("X") for r in _v11["meerwerk"]))
    check("catalogus-boom: sub-label geschoond (geen bracket)", "m² tot" not in _v11["naam"])
    check("schoon-label", _sl("Spouwmuurisolatie vlokken 60 mm van 0 m² tot 45 m²") == "Spouwmuurisolatie vlokken")
    check("zoek-maatregel", (_zm(_cat, "V1-1-A1") or {}).get("code") == "V1-1-A1")
    import dashboard.app as _WA3
    _rr = {r.rule for r in _WA3.app.url_map.iter_rules()}
    check("webapp v2: opname-editor-routes", {"/project/<tag>/opname", "/project/<tag>/opname/el/<int:i>",
          "/project/<tag>/opname/el/nieuw", "/project/<tag>/opname/vabi_huidig",
          "/project/<tag>/maatregelen/add", "/project/<tag>/toelichting"} <= _rr)
    check("webapp v2: stap 'opname' in de stepper", any(s == "opname" for s, _ in _WA3.STAPPEN))
except Exception as _e:
    check("webapp v2: modules draaien zonder fout", False); print("     " + repr(_e)[:170])

print("\n43. Beveiliging (hosting): wachtwoord-hash + TOTP-MFA + rate-limit")
try:
    import dashboard.security as _S
    _h = _S.hash_password("geheim-wachtwoord")
    check("pw-hash: rondje klopt + fout wachtwoord faalt",
          _S.check_password("geheim-wachtwoord", _h) and not _S.check_password("fout", _h))
    # RFC 6238-testvector (secret '12345678901234567890', T=59s, SHA1, 6 cijfers -> 287082)
    check("totp: RFC 6238-vector", _S.totp_code("GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ", t=59) == "287082")
    _sec = _S.nieuw_totp_secret()
    check("totp: eigen secret verifieert (venster)", _S.check_totp(_sec, _S.totp_code(_sec)))
    check("totp: foute code faalt", not _S.check_totp(_sec, "000000") or _S.totp_code(_sec) == "000000")
    _S._pogingen.clear()
    for _ in range(5):
        _S.poging_mislukt("1.2.3.4")
    check("rate-limit: 5 missers -> blok", _S.geblokkeerd("1.2.3.4") and not _S.geblokkeerd("5.6.7.8"))
    _S._pogingen.clear()
    _ok, _ = _S.login_check({}, "lokaalpw", "", "9.9.9.9", fallback_pw="lokaalpw")
    check("login: lokale modus (geen hash) werkt", _ok)
    _cfg2 = {"pw_hash": _h, "totp_secret": _sec}
    _ok1, _ = _S.login_check(_cfg2, "geheim-wachtwoord", _S.totp_code(_sec), "9.9.9.8")
    _ok2, _m2 = _S.login_check(_cfg2, "geheim-wachtwoord", "000000", "9.9.9.7")
    check("login: hash+MFA goed -> ok; foute code -> geweigerd", _ok1 and not _ok2 and "code" in _m2)
    import dashboard.app as _WA4
    check("app: secret key persistent + origin-check geregistreerd",
          bool(_WA4.app.secret_key) and any(f.__name__ == "_origin_check"
          for f in _WA4.app.before_request_funcs.get(None, [])))
    os.environ["NIJBEGUN_PW_HASH"] = _h
    os.environ["NIJBEGUN_TOTP_SECRET"] = _sec
    _d = _WA4._dash_cfg()
    check("app: PaaS env-vars overrulen config (Render/Railway)",
          _d.get("pw_hash") == _h and _d.get("totp_secret") == _sec)
    del os.environ["NIJBEGUN_PW_HASH"], os.environ["NIJBEGUN_TOTP_SECRET"]
except Exception as _e:
    check("beveiliging: module draait zonder fout", False); print("     " + repr(_e)[:170])

print("\n44. Deep-dive-fixes: dak direct-m² wint + kozijn 0,65-regel + perimeter-note")
try:
    import tempfile as _tf5
    from magicplan.statistics_csv import build_dossier as _bd5
    _dd5 = ("PLAN ATTRIBUTES\nExterior perimeter: m,24,\nBouwjaar,1992.t.m.2013\nWoningtype,Tussenwoning\nGevelhoogte (m),5.4\n"
            "Dakvlak 1 - daktype,Zadeldak\nDakvlak 1 - oppervlak (m²),33.92\nDakvlak 1 - oriëntatie,Z\nDakvlak 1 - hellingshoek (°),45\n"
            "Dakvlak 2 - daktype,Plat dak\nDakvlak 2 - oppervlak (m²),5.53\nDak - vloerbreedte (m),8\n\n"
            "FLOOR ATTRIBUTES,Ground surface without walls,Ceiling Height,Begrenzing\nGround Floor,40,2.50 m,Kruipruimte\n\n"
            "WALL ATTRIBUTES,Wall,Symbol,Surf,SurfNoOpen,Width,Height,Ann,Type,Isol,Rekenzone,Orientatie\n"
            "Ground Floor,\nVoorgevel,Wall 0,Wall,10,9,4,2.5,1,Wall,,1,Z\n")
    _p5 = _tf5.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8"); _p5.write(_dd5); _p5.close()
    _d5, _n5 = _bd5(_p5.name)
    _dk5 = [s for s in _d5.schil if s.type == "dak"]
    check("dak: direct ingevoerde m² winnen (2 vlakken, 33.92 + 5.53; geen auto-berekening)",
          len(_dk5) == 2 and {round(s.oppervlakte_m2, 2) for s in _dk5} == {33.92, 5.53})
    check("dak: direct-m²-note aanwezig", any("direct ingevoerde m²" in n for n in _n5))
    check("perimeter: woningscheidende-wand-note bij tussenwoning", any("WONINGSCHEIDENDE" in n for n in _n5))
    # kozijn < 0.65 m2 -> 0.65 (via assemble/kozijn-route: window in WALL-attributen)
    _kc = ("PLAN ATTRIBUTES\nExterior perimeter: m,20,\nBouwjaar,1992.t.m.2013\nWoningtype,Vrijstaand\nGevelhoogte (m),5.4\n\n"
           "FLOOR ATTRIBUTES,Ground surface without walls,Ceiling Height,Begrenzing\nGround Floor,40,2.50 m,Kruipruimte\n\n"
           "WALL ATTRIBUTES,Wall,Symbol,Surf,SurfNoOpen,Width,Height,Ann,Type,Isol,Rekenzone,Orientatie\n"
           "Ground Floor,\nVoorgevel,Wall 0,Wall,10,9,4,2.5,1,Wall,,1,Z\n"
           "Voorgevel,Window 1,Window,0.36,0.36,0.6,0.6,1,Window,HR++,1,Z\n")
    _pk = _tf5.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8"); _pk.write(_kc); _pk.close()
    _dk, _ = _bd5(_pk.name)
    _rr5 = [s for s in _dk.schil if s.type == "kozijn" and s.subtype == "Raam"]
    check("kozijn: klein raam (0,36 m²) -> 0,65 m² (Nij Begun-regel)",
          bool(_rr5) and abs(_rr5[0].oppervlakte_m2 - 0.65) < 0.001 and "0,65" in (_rr5[0].opmerkingen or ""))
except Exception as _e:
    check("deep-dive-fixes: parser draait zonder fout", False); print("     " + repr(_e)[:170])

print("\n45. Parser: 'Deels binnen/buiten'-VINKJE op de wand (kolom op naam, i.p.v. typen)")
try:
    import tempfile as _tf6
    from magicplan.statistics_csv import build_dossier as _bd6
    _vc = ("PLAN ATTRIBUTES\nExterior perimeter: m,20,\nBouwjaar,1992.t.m.2013\nWoningtype,Vrijstaand\nGevelhoogte (m),5.4\n\n"
           "FLOOR ATTRIBUTES,Ground surface without walls,Ceiling Height,Begrenzing\nGround Floor,40,2.50 m,Kruipruimte\n\n"
           "WALL ATTRIBUTES,Wall,Symbol,Surf,SurfNoOpen,Width,Height,Ann,Type,Isol,Rekenzone,Orientatie,Bron,Deels binnen/deels buiten? (narekenen)\n"
           "Ground Floor,\nVoorgevel,Wall 0,Wall,10,9,4,2.5,1,Wall,,1,Z,,No\n"
           "Achtergevel,Wall 1,Wall,12,11,5,2.5,1,Wall,,1,N,,Yes\n")
    _pv6 = _tf6.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8"); _pv6.write(_vc); _pv6.close()
    _dv6, _nv6 = _bd6(_pv6.name)
    _gz = [s for s in _dv6.schil if s.type == "gevel" and "kopgevel" not in (s.subtype or "")]
    check("vinkje: aangevinkte wand -> NAREKENEN-flag (zonder typen)",
          any("NAREKENEN" in (s.opmerkingen or "") for s in _gz)
          and any("NAREKENEN" in n and "Achtergevel" in n for n in _nv6))
    check("vinkje: niet-aangevinkte wand blijft gewoon", any("NAREKENEN" not in (s.opmerkingen or "") for s in _gz))
except Exception as _e:
    check("vinkje: parser draait zonder fout", False); print("     " + repr(_e)[:170])

print("\n46. Bouwjaar-hints + isolatieplan-JSON (leverformaat M29 punt 10a)")
try:
    import dashboard.bouwjaar as _BJ
    _t75, _h75 = _BJ.hint(1975)
    check("bouwjaar-hint 1975 -> tijdvak 1975–1982 + html", _t75 is not None and "1975" in _t75
          and "<h4>" in _h75 and "<li>" in _h75)
    _t30, _ = _BJ.hint(1930)
    check("bouwjaar-hint 1930 -> vooroorlogs", _t30 is not None and "1946" in _t30)
    check("bouwjaar-hint zonder bouwjaar -> None", _BJ.hint(None) == (None, None))
    import os as _os, io as _io, shutil as _sh, json as _js
    import dashboard.app as _WA5
    _WA5.app.config.update(TESTING=True)
    _c5 = _WA5.app.test_client()
    with _c5.session_transaction() as _s5:
        _s5["ingelogd"] = True
    with open(os.path.join(ROOT, "out", "demo_dossier.json"), "rb") as _fh:
        _r5 = _c5.post("/nieuw", data={"bestand": (_io.BytesIO(_fh.read()), "d.json"), "straat": "T 1",
                       "plaats": "X", "woningtype": "Tussenwoning"}, content_type="multipart/form-data")
    _tag5 = _r5.headers["Location"].rstrip("/").split("/")[-2]
    _c5.get("/project/%s/afronden" % _tag5)
    _jp = _os.path.join(_WA5._pdir(_tag5), "isolatieplan_%s.json" % _tag5)
    check("isolatieplan-JSON gegenereerd bij afronden", _os.path.isfile(_jp))
    _pj = _js.load(open(_jp, encoding="utf-8"))
    check("plan-JSON: formaat + rekenkern + maatregelen-array",
          _pj.get("formaat") == "nijbegun-isolatieplan" and "Vabi" in _pj["tool"]["rekenkern"]
          and isinstance(_pj.get("maatregelen_subsidietabel"), list))
    _sh.rmtree(_WA5._pdir(_tag5))
except Exception as _e:
    check("bouwjaar/plan-json: draait zonder fout", False); print("     " + repr(_e)[:170])

print("\n47. Nij Begun-focus: mail-scope, leads->project, MagicPlan-foto's, HIG-CSS, spouwinspectie")
try:
    import os as _o7, tempfile as _tf7, shutil as _sh7
    # (a) kennismakingsmail is zuiver schil/ventilatie — geen installatie-vragen
    import dashboard.leads as _LS
    _blob = " ".join(_LS.VOORBEREIDING).lower()
    check("mail: geen cv-ketel/warmtepomp/zonnepanelen-vraag (label, niet M29)",
          "cv-ketel" not in _blob and "warmtepomp" not in _blob and "zonnepanel" not in _blob)
    check("mail: wel isolatie-bewijslast gevraagd",
          any(("isolatiewerk" in v.lower()) or ("geïsoleerd" in v.lower()) for v in _LS.VOORBEREIDING))
    # (b) MagicPlan-foto's: parse + download met injecteerbare fetch (offline)
    from magicplan import photos as _PH
    _plan = {"photos": [{"url": "https://x/a.jpg", "bouwdeel": "voorgevel", "tag": "overzicht"},
                        {"id": "p2", "bouwdeel": "dak"}]}
    _ents = _PH.photo_entries(_plan)
    check("photos: entries geparsed (url + id-only)", len(_ents) == 2 and _ents[0]["url"].endswith("a.jpg"))
    _td = _tf7.mkdtemp()
    _fotos, _fout = _PH.download_photos(_ents, _td, lambda e: b"JPEGDATA" if e.get("url") else (_ for _ in ()).throw(RuntimeError("geen url")))
    check("photos: 1 gedownload, 1 geflagd (id zonder url — niet gegokt)", len(_fotos) == 1 and len(_fout) == 1)
    check("photos: bestand op schijf + Foto.bouwdeel", _o7.path.isfile(_o7.path.join(_td, _fotos[0].bestand)) and _fotos[0].bouwdeel == "voorgevel")
    _sh7.rmtree(_td, ignore_errors=True)
    # (c) HIG-CSS: dark mode + safe-area + table-wrap aanwezig
    _css = open(_o7.path.join(ROOT, "dashboard", "static", "app.css"), encoding="utf-8").read()
    check("HIG-CSS: dark mode + safe-area + 44px + table-wrap",
          "prefers-color-scheme: dark" in _css and "safe-area-inset" in _css and ".table-wrap" in _css and "46px" in _css)
    # (d) spouwinspectie-gids bestaat + endoscopie wijst ernaar
    check("spouwinspectie-gids aanwezig", _o7.path.isfile(_o7.path.join(ROOT, "docs", "spouwinspectie-gids.md")))
    check("endoscopie-werkwijze verwijst naar spouwinspectie-gids",
          "spouwinspectie-gids" in open(_o7.path.join(ROOT, "docs", "endoscopie-werkwijze.md"), encoding="utf-8").read())
    # (e) leads -> project (geïsoleerd van echte leads.json)
    import dashboard.app as _WL
    _WL.app.config.update(TESTING=True)
    _cl = _WL.app.test_client()
    with _cl.session_transaction() as _s7:
        _s7["ingelogd"] = True
    _od, _of = _LS.LEADS_DIR, _LS.LEADS_FILE
    _tmp = _tf7.mkdtemp(); _LS.LEADS_DIR = _tmp; _LS.LEADS_FILE = _o7.path.join(_tmp, "leads.json")
    try:
        _rows, _ = _LS.add_lead({"bag_id": "TESTBAG1", "naam": "Testpersoon", "postcode": "9999ZZ",
                                 "huisnummer": "7", "toevoeging": "", "straat": "Teststraat",
                                 "woonplaats": "Groningen", "bouwjaar": 1975, "woningtype": "Tussenwoning"})
        _LS.save_leads(_rows); _lid = _rows[-1]["id"]
        _rp = _cl.post("/leads/%d/project" % _lid)
        check("leads->project: redirect naar opname", _rp.status_code in (302, 303) and _rp.headers["Location"].endswith("/opname"))
        _ptag = _rp.headers["Location"].rstrip("/").split("/")[-2]
        _l2 = next(x for x in _LS.load_leads() if x["id"] == _lid)
        check("leads->project: tag gekoppeld + status doorgezet", _l2.get("project_tag") == _ptag and _l2["status"] == "opname gedaan")
        _dos = _WL._dossier(_ptag)
        check("leads->project: adres/bouwjaar over, GEEN persoonsgegevens in dossier",
              _dos.identificatie.bouwjaar == 1975 and _dos.identificatie.postcode == "9999ZZ"
              and "Testpersoon" not in json.dumps(_dos.to_dict()))
        _rp2 = _cl.post("/leads/%d/project" % _lid)     # idempotent
        check("leads->project: idempotent (opent bestaand, overschrijft niet)", _rp2.status_code in (302, 303))
        _sh7.rmtree(_WL._pdir(_ptag), ignore_errors=True)
    finally:
        _LS.LEADS_DIR, _LS.LEADS_FILE = _od, _of
except Exception as _e:
    check("Nij Begun-focus: draait zonder fout", False); print("     " + repr(_e)[:180])

print("\n48. Raam-invoer versimpelen (alleen Type glas; kozijn/rooster/paneel defaulten)")
try:
    # (a) parser-defaults: leeg kozijnmateriaal -> Hout of kunststof; afwijking blijft werken
    from magicplan.statistics_csv import _norm_kozijn_mat as _nkm
    check("raam: leeg kozijnmateriaal -> Hout of kunststof (default)", _nkm("") == "Hout of kunststof")
    check("raam: 'b' -> Metaal thermisch onderbroken (afwijking werkt nog)", _nkm("b").startswith("Metaal"))
    # (b) form_push: set_optional + set_default op een nagebootste 'Raam/paneel'-veldgroep
    import magicplan.form_push as _FP
    _form = {"name": "Raam/paneel", "context": ["windows"], "children": [
        {"id": "q1", "type": "question", "name": "Type glas", "dataType": "list", "required": True,
         "fields": {"options": ["Enkel", "Dubbel", "HR++"]}},
        {"id": "q2", "type": "question", "name": "Kozijnmateriaal", "dataType": "list", "required": True,
         "fields": {"options": ["Metaal TO", "Hout of kunststof", "Metaal niet-TO"]}},
        {"id": "q3", "type": "question", "name": "Raam/paneel", "dataType": "list", "required": True,
         "fields": {"options": ["Paneel", "Raam"]}}]}
    _rec, _a48, _rq48, _pb48 = _FP.merge_record({"id": "r48", "form": _form}, _FP.load_additions(), verbose=False)
    _bn = {c["name"]: c for c in _FP._form_of(_rec)["children"]}
    check("raam: Type glas blijft VERPLICHT", _bn["Type glas"]["required"] is True)
    check("raam: Kozijnmateriaal optioneel + 'Hout of kunststof' vooraan",
          _bn["Kozijnmateriaal"]["required"] is False and _bn["Kozijnmateriaal"]["fields"]["options"][0] == "Hout of kunststof")
    check("raam: Raam/paneel optioneel + 'Raam' vooraan",
          _bn["Raam/paneel"]["required"] is False and _bn["Raam/paneel"]["fields"]["options"][0] == "Raam")
    check("form_push: geen structurele problemen na optioneel/default", _pb48 == [])
except Exception as _e:
    check("raam-invoer: draait zonder fout", False); print("     " + repr(_e)[:170])

print("\n49. Paneel-in-kozijn (dichte constructie, ConstructieType=1) end-to-end")
try:
    from core.dossier import Dossier as _D9, SchilDeel as _S9, Identificatie as _I9
    import vabi.constructie_generate as _CG9
    # (a) TYPE_CODE + classify: paneel -> ConstructieType 1, dichte match (geen glas)
    check("paneel: TYPE_CODE=1 (Paneel)", _CG9.TYPE_CODE.get("paneel") == "1")
    check("paneel: _classify blijft 'paneel' (geen kozijn/raam)", _CG9._classify(_S9(id="p", type="paneel")) == "paneel")
    # (b) generator kiest een ConstructieType-1 constructie voor een paneel (pool+cb intern gebouwd)
    _dos9 = _D9(identificatie=_I9(postcode="9999ZZ", huisnummer="1", bouwjaar=1975))
    _dos9.schil = [_S9(id="paneel-1", type="paneel", subtype="Paneel", orientatie="Z",
                       begrenzing="Buitenlucht", oppervlakte_m2=1.2, isolatie_aanwezig="Nee")]
    _clones9, _map9, _iss9 = _CG9.resolve_constructies(_dos9)
    check("paneel: kreeg een passende constructie (geen 'onbekend type')",
          "paneel-1" in _map9 and not any("onbekend type" in x for x in _iss9))
    _ct = next((_CG9._t(c, "ConstructieType") for c in _clones9), None)
    check("paneel: gekozen constructie is ConstructieType=1", _ct == "1")
    # (c) webapp: paneel toevoegen -> valt in de dichte-branch (Rc/isolatie), niet glas
    import dashboard.app as _WP9
    _WP9.app.config.update(TESTING=True)
    _c9 = _WP9.app.test_client()
    with _c9.session_transaction() as _s9:
        _s9["ingelogd"] = True
    _r9 = _c9.post("/nieuw", data={"straat": "Paneelstraat 1", "postcode": "9999ZP", "plaats": "X", "woningtype": "Tussenwoning"})
    _tg9 = _r9.headers["Location"].rstrip("/").split("/")[-2]
    _c9.post("/project/%s/opname/el/nieuw" % _tg9, data={"type": "paneel"})
    _d9 = _WP9._dossier(_tg9)
    _pn = next((s for s in _d9.schil if s.type == "paneel"), None)
    check("webapp: paneel toevoegbaar (type=paneel, subtype=Paneel)", _pn is not None and _pn.subtype == "Paneel")
    _op9 = _c9.get("/project/%s/opname" % _tg9).get_data(as_text=True)
    check("webapp: paneel-keuze in de dropdown", "Paneel (dicht)" in _op9)
    import shutil as _sh9; _sh9.rmtree(_WP9._pdir(_tg9), ignore_errors=True)
except Exception as _e:
    check("paneel-in-kozijn: draait zonder fout", False); print("     " + repr(_e)[:180])

print("\n50. form_push: element-veldgroepen (custom-fields) + list-conditie (Paneel-branch)")
try:
    import magicplan.form_push as _FP5
    # (a) robuuste list-extractie: {data:{forms,publish_to}} -> records + workgroup-ids
    _recs, _wg = _FP5._records_from_list({"data": {"forms": [{"id": "a"}], "publish_to": [{"id": "ws1"}]}})
    check("list-extractie: forms+publish_to uit dict-shape", _recs == [{"id": "a"}] and _wg == ["ws1"])
    _recs2, _ = _FP5._records_from_list({"data": [{"id": "b"}]})
    check("list-extractie: platte list-shape werkt ook", _recs2 == [{"id": "b"}])
    # (b) 'Raam/paneel'-veldgroep mergen: Paneel-branch aanhangen (list-conditie) + raam-defaults
    _fg = {"id": "fldRaam", "form": {"id": "q", "name": "Raam/paneel", "context": ["windows"],
           "type": "custom-form", "children": [
        {"id": "g1", "type": "question", "name": "Type glas", "dataType": "list", "required": True,
         "comparisonValue": None, "fields": {"options": ["Enkel", "HR++"]}},
        {"id": "g2", "type": "question", "name": "Kozijnmateriaal", "dataType": "list", "required": True,
         "comparisonValue": None, "fields": {"options": ["Metaal TO", "Hout of kunststof"]}},
        {"id": "g3", "type": "question", "name": "Raam/paneel", "dataType": "list", "required": True,
         "comparisonValue": None, "fields": {"options": ["Raam", "Paneel"]}, "children": []}]}}
    _rec5, _add5, _req5, _pb5 = _FP5.merge_record(_fg, _FP5.load_additions(), verbose=False)
    _bn5 = {c["name"]: c for c in _FP5._form_of(_rec5)["children"]}
    _kids5 = _bn5["Raam/paneel"].get("children", [])
    check("field-group: Paneel-branch aangehangen met list-conditie 'Paneel'",
          any(k["name"].startswith("Paneel - isolatie") and k.get("comparisonValue") == "Paneel" for k in _kids5))
    check("field-group: Kozijnmateriaal optioneel + 'Hout of kunststof' vooraan",
          _bn5["Kozijnmateriaal"]["required"] is False and _bn5["Kozijnmateriaal"]["fields"]["options"][0] == "Hout of kunststof")
    check("field-group: Raam/paneel optioneel + 'Raam' vooraan",
          _bn5["Raam/paneel"]["required"] is False and _bn5["Raam/paneel"]["fields"]["options"][0] == "Raam")
    check("field-group: geen structurele validatieproblemen", _pb5 == [])
    # (c) idempotent: nog eens mergen voegt de Paneel-branch niet dubbel toe
    _rec5b, _add5b, _, _ = _FP5.merge_record(_FP5._form_of(_rec5), _FP5.load_additions(), verbose=False)
    _kids5b = {c["name"]: c for c in _FP5._form_of(_rec5b)["children"]}["Raam/paneel"].get("children", [])
    check("field-group: idempotent (geen dubbele Paneel-velden)", len(_kids5b) == len(_kids5))
except Exception as _e:
    check("form_push field-groups: draait zonder fout", False); print("     " + repr(_e)[:180])

print("\n=== RESULTAAT: %d geslaagd, %d gefaald ===" % (passed, failed))
sys.exit(1 if failed else 0)
