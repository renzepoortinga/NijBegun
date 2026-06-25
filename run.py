#!/usr/bin/env python3
"""
Nij Begun & EPA - isolatieplan-tool (orchestrator).
Eén commando: VABI-monitoringbestand (of dossier-JSON) -> compleet isolatieplan +
ventilatieberekening + foto-checklist + validatie. Draait standalone (Python of .exe).

    python run.py --from-monitor "monitor.xml" [--straat .. --plaats .. --woningtype ..]
    python run.py --dossier dossier.json
"""
import os, sys, json, argparse, datetime, logging, traceback
TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOL_DIR)
from core.dossier import load_json, save_json, Adviseur            # noqa: E402
from vabi.monitor_xml import parse as parse_monitor               # noqa: E402
from engine.measure_engine import run as engine_run               # noqa: E402
from isolatieplan.fill_template import fill as fill_template      # noqa: E402
from validator.validate import validate, load_catalog_codes       # noqa: E402
from ventilatie.ventilatie import bereken as vent_bereken, rapport as vent_rapport  # noqa: E402
from foto.checklist import generate as foto_generate              # noqa: E402

log = logging.getLogger("nijbegun")

def setup_logging(out_dir):
    os.makedirs(out_dir, exist_ok=True); log.setLevel(logging.INFO)
    fh = logging.FileHandler(os.path.join(out_dir, "run.log"), encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s")); log.addHandler(fh)
    ch = logging.StreamHandler(); ch.setFormatter(logging.Formatter("%(message)s")); log.addHandler(ch)

def load_config(path):
    try:
        with open(path, encoding="utf-8") as fh: return json.load(fh)
    except FileNotFoundError:
        log.warning("config.json niet gevonden (%s) - standaard gebruikt", path); return {}
    except json.JSONDecodeError as e:
        raise SystemExit("FOUT: config.json ongeldig JSON: %s" % e)

def abspath(p): return p if os.path.isabs(p) else os.path.join(TOOL_DIR, p)

def merge_config(dos, cfg, args):
    adv = cfg.get("adviseur", {})
    if adv:
        dos.adviseur = Adviseur(**{k: adv.get(k, "") for k in
                     ("naam", "bedrijf", "telefoon", "email", "registratie")})
    wd = cfg.get("woning_default", {})
    if not dos.identificatie.woningtype:
        dos.identificatie.woningtype = args.woningtype or wd.get("woningtype", "")
    if args.straat or not dos.identificatie.straat:
        dos.identificatie.straat = args.straat or wd.get("straat", "") or dos.identificatie.straat
    if args.plaats or not dos.identificatie.plaats:
        dos.identificatie.plaats = args.plaats or wd.get("plaats", "") or dos.identificatie.plaats
    if not dos.ventilatie.systeem:
        dos.ventilatie.systeem = cfg.get("ventilatie_default", {}).get("systeem", "")
    today = datetime.date.today().isoformat()
    dos.opname.opnamedatum = dos.opname.opnamedatum or today
    dos.opname.rapportagedatum = dos.opname.rapportagedatum or today
    dos.opname.type_advies = dos.opname.type_advies or "Basis"
    return dos

def stage(name, fn):
    try: return fn()
    except Exception as e:
        log.error("FOUT in stap '%s': %s", name, e); log.error(traceback.format_exc())
        raise SystemExit("Afgebroken in stap '%s'. Zie out/run.log." % name)

def main():
    ap = argparse.ArgumentParser(description="Nij Begun isolatieplan-tool")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--from-monitor"); g.add_argument("--dossier")
    ap.add_argument("--config", default=os.path.join(TOOL_DIR, "config.json"))
    ap.add_argument("--out", default=os.path.join(TOOL_DIR, "out"))
    ap.add_argument("--template", default=None); ap.add_argument("--catalog", default=None)
    ap.add_argument("--straat", default=""); ap.add_argument("--plaats", default="")
    ap.add_argument("--woningtype", default=""); ap.add_argument("--situatie", default="bestaand")
    a = ap.parse_args()

    setup_logging(a.out); log.info("=== Nij Begun isolatieplan-tool ===")
    cfg = load_config(a.config)
    template = abspath(a.template or cfg.get("paths", {}).get("template", "templates/isolatieplan_template.docx"))
    catalog_path = abspath(a.catalog or cfg.get("paths", {}).get("catalog", "catalog/catalog.json"))
    for label, p in [("template", template), ("catalog", catalog_path)]:
        if not os.path.exists(p): raise SystemExit("FOUT: %s niet gevonden: %s" % (label, p))

    if a.from_monitor:
        if not os.path.exists(a.from_monitor): raise SystemExit("FOUT: monitorbestand niet gevonden: %s" % a.from_monitor)
        dos = stage("monitor inlezen", lambda: parse_monitor(a.from_monitor)[0])
        log.info("Monitor: %s %s | label %s | Standaard %s kWh/m2.jr | %d schildelen | %d ruimtes",
                 dos.identificatie.postcode, dos.identificatie.huisnummer, dos.berekening.label_huidig,
                 dos.berekening.standaard_eis_kwh_m2, len(dos.schil), len(dos.geometrie.ruimtes))
    else:
        if not os.path.exists(a.dossier): raise SystemExit("FOUT: dossier niet gevonden: %s" % a.dossier)
        dos = stage("dossier inlezen", lambda: load_json(a.dossier))

    dos = merge_config(dos, cfg, a)
    tag = ("%s_%s" % (dos.identificatie.postcode or "woning", dos.identificatie.huisnummer or "")).strip("_").replace(" ", "")

    catalog = stage("catalogus laden", lambda: json.load(open(catalog_path, encoding="utf-8")))
    dos, notes = stage("maatregel-engine", lambda: engine_run(dos, catalog))
    totaal = sum((m.kosten or 0) for m in dos.maatregelen)
    log.info("Maatregelen: %d | totaal incl. btw: EUR %.2f", len(dos.maatregelen), totaal)

    # ventilatie (uit MagicPlan-ruimtes)
    vent = vent_bereken(dos.geometrie.ruimtes, a.situatie) if dos.geometrie.ruimtes else None
    out_vent = os.path.join(a.out, "ventilatieberekening_%s.txt" % tag)
    with open(out_vent, "w", encoding="utf-8") as fh:
        fh.write(vent_rapport(vent) if vent else
                 "Ventilatieberekening: geen ruimtes beschikbaar.\n"
                 "Ruimtes komen uit de MagicPlan-plattegrond (opname). Voer een MagicPlan-opname in.\n")

    # foto-checklist
    out_foto = os.path.join(a.out, "fotochecklist_%s.txt" % tag)
    with open(out_foto, "w", encoding="utf-8") as fh: fh.write(foto_generate(dos))

    # validatie
    codes = load_catalog_codes(catalog_path)
    issues, dos = stage("validatie", lambda: validate(dos, codes))
    blockers = [m for s, m in issues if s == "BLOKKEREND"]

    # isolatieplan + dossier + rapport
    out_docx = os.path.join(a.out, "isolatieplan_%s.docx" % tag)
    out_json = os.path.join(a.out, "dossier_%s.json" % tag)
    out_rep = os.path.join(a.out, "rapport_%s.txt" % tag)
    stage("isolatieplan invullen", lambda: fill_template(dos, template, out_docx))
    save_json(dos, out_json)
    with open(out_rep, "w", encoding="utf-8") as fh:
        fh.write("NIJ BEGUN ISOLATIEPLAN - RAPPORT\n")
        fh.write("Adres: %s %s, %s %s | bouwjaar %s | %s\n" % (
            dos.identificatie.straat, dos.identificatie.huisnummer, dos.identificatie.postcode,
            dos.identificatie.plaats, dos.identificatie.bouwjaar, dos.identificatie.woningtype))
        fh.write("Label (huidig): %s | energiebehoefte: %s | Standaard-eis: %s kWh/m2.jr\n" % (
            dos.berekening.label_huidig, dos.berekening.kwh_m2_huidig, dos.berekening.standaard_eis_kwh_m2))
        fh.write("\nMaatregelen (catalogus, laagste kosten per vlak):\n")
        for m in dos.maatregelen:
            fh.write("  %-9s %-40s %7.1f m2  EUR %9.2f\n" % (m.code, m.omschrijving[:40], m.oppervlakte_m2, m.kosten or 0))
        fh.write("  TOTAAL incl. btw: EUR %.2f\n" % totaal)
        if any(m.subposten for m in dos.maatregelen):
            fh.write("\nBeschikbaar meerwerk (cat 2/3) - bevestig en vul de hoeveelheid in:\n")
            for m in dos.maatregelen:
                for s in m.subposten:
                    fh.write("  [cat %d] %-10s %-44s EUR %s/%s\n" % (
                        s.categorie, s.code, (s.omschrijving or "")[:44], s.prijs_per_eenheid, s.eenheid))
        if vent: fh.write("\nVentilatie (balans): maatgevend %.1f dm3/s (~%.0f m3/h)\n" % (vent["maatgevend_dm3s"], vent["maatgevend_m3h"]))
        fh.write("\nValidatie: %s\n" % dos.validatie.status.upper())
        for it in dos.validatie.issues: fh.write("  - %s\n" % it)
        for n in notes: fh.write("  [!] %s\n" % n)
        fh.write("\nLET OP: integrale Standaard (kWh/m2.jr na maatregelen) bevestigen in Vabi EPA-W.\n")

    log.info(""); log.info("KLAAR. Output in: %s", a.out)
    for f in (out_docx, out_json, out_rep, out_vent, out_foto): log.info("  - %s", os.path.basename(f))
    log.info("Validatie: %s (%d blokkerend)", dos.validatie.status.upper(), len(blockers))
    for n in notes: log.info("  [!] %s", n)
    sys.exit(2 if blockers else 0)

if __name__ == "__main__":
    main()
