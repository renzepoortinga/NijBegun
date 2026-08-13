"""
Assembleer een compleet dossier uit de TWEE MagicPlan-bronnen (hybride):
  - API-plan-JSON (geometrie: verdiepingen/ruimtes/ramen)  -> extractor / out/plan_raw.json
  - project-report-PDF (form-antwoorden: alle tags + per-raam kozijn) -> report_parser

De geometrie-vertaling (gevel-m2 per orientatie, exacte begane-grond/dak-footprint) blijft het
lastige stuk: gevel-oppervlak is hier een benadering (omtrek x hoogte - openingen); de adviseur
verifieert/overschrijft in Vabi. Dak-m2 = footprint x 1/cos(helling) of het handmatige veld.

    python magicplan/assemble.py --plan out/plan_raw.json --report "Oosterkade 23 Report.pdf" --out out/dossier.json
"""
import os, sys, json, math, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.dossier import (Dossier, Identificatie, Opname, Geometrie, VloerInfo, Ruimte,  # noqa
                          SchilDeel, save_json, is_bcrg_isolatiekeuze)
from magicplan.extractor import _g, _functie, _map_ventilatie, _map_installaties, _maak_vloer, _maak_dak
from magicplan import report_parser


def _value(values, vid):
    for it in (values or []):
        if isinstance(it, dict) and it.get("id") == vid:
            return it.get("value")
    return None


def geometry_from_plan(plan):
    """Lees de echte MagicPlan v2-structuur: data.plan_data.floors[].rooms[].objects[]."""
    data = plan.get("data", plan)
    pd = data.get("plan_data", {})
    geo = Geometrie(gebruiksoppervlakte_ag_m2=float(pd.get("living_area") or 0))
    windows, total_h, areas = [], 0.0, []
    for fl in pd.get("floors", []):
        area = float((fl.get("statistics") or {}).get("area") or 0)
        ch = _value(fl.get("values"), "ceilingHeight")
        geo.vloeren.append(VloerInfo(naam=fl.get("name", ""), oppervlakte_m2=area,
                                     hoogte_m=float(ch) if ch else None))
        if ch:
            total_h += float(ch)
        areas.append((fl.get("name", ""), area))
        for rm in fl.get("rooms", []):
            rn = rm.get("name", "")
            ra = float((rm.get("statistics") or {}).get("area") or 0)
            geo.ruimtes.append(Ruimte(naam=rn, functie=_functie(rn), oppervlakte_m2=ra))
            for o in rm.get("objects", []):
                sid = (o.get("symbol_id") or "").lower()
                if sid.startswith("window") or sid == "doorwithwindow":
                    w = _value(o.get("values"), "width"); h = _value(o.get("values"), "height")
                    a = round(float(w) * float(h), 2) if w and h else 0.0
                    windows.append({"area": a, "room": rn})
    footprint = max((a for _, a in areas), default=0.0)   # grootste verdieping = footprint-proxy
    # buitenomtrek BENADEREN uit de footprint (de MagicPlan-perimeter telt binnenwanden mee);
    # 4*sqrt(opp) = omtrek vierkant, x1.15 voor niet-vierkante plattegrond.
    perimeter = round(4 * math.sqrt(footprint) * 1.15, 1) if footprint else 0.0
    return geo, windows, footprint, perimeter, total_h


def build_dossier(p, kozijnen, plan):
    """p = report-antwoorden {key:waarde}; kozijnen = per-raam report-blokken; plan = API-JSON."""
    dos = Dossier()
    dos.identificatie = Identificatie(
        bag_vboid=_g(p, "bag_vboid", default="") or "", postcode=_g(p, "postcode", default="") or "",
        huisnummer=str(_g(p, "huisnummer", default="") or ""), bouwjaar=_g(p, "bouwjaar", int),
        renovatiejaar=_g(p, "renovatiejaar", int), woningtype=_g(p, "woningtype", default="") or "",
        aantal_bouwlagen=_g(p, "bouwlagen", int))
    dos.opname = Opname(
        type_advies=_g(p, "type_advies", default="Basis") or "Basis",
        qv10_gemeten=_g(p, "qv10_gemeten", bool, False), qv10_waarde=_g(p, "qv10_waarde", float),
        bewijslast=_g(p, "bewijslast", default="Geen") or "Geen",
        gevelhoogte_m=_g(p, "gevelhoogte_m", float),
        gevel_tot_hartmaat_gemeten=_g(p, "gevel_tot_hartmaat_gemeten", bool, False))
    _map_ventilatie(p, dos)
    _map_installaties(p, dos)

    geo, windows, footprint, perimeter, total_h = geometry_from_plan(plan)
    if _g(p, "ag_m2", float):
        geo.gebruiksoppervlakte_ag_m2 = _g(p, "ag_m2", float)
    dos.geometrie = geo
    if dos.opname.gevelhoogte_m is None:
        dos.opname.gevelhoogte_m = total_h

    schil = []
    # gevel (algemeen-tags uit report + benaderd oppervlak)
    win_area = sum(w["area"] for w in windows)
    gevel_area = round(max(perimeter * total_h - win_area, 0.0), 2)
    # HART-OP-HART GEVEL-TOESLAG (ISSO 82.1 par. 8.2): de tool telt dit BEWUST NIET automatisch mee
    # (besluit Renze 19-7: te foutgevoelig om altijd goed te doen). Bij een hoek-/tussenwoning voegt
    # de adviseur de toeslag zelf toe in VABI. NB: het woningtype stuurt daarnaast (in VABI) de
    # forfaitaire infiltratie (ISSO 7.1.1).
    from core.geometry import aantal_woningscheidende_wanden, woningscheidende_wand_toeslag_m2
    if aantal_woningscheidende_wanden(dos.identificatie.woningtype):
        _hoh = woningscheidende_wand_toeslag_m2(dos.opname.gevelhoogte_m, dos.identificatie.woningtype)
        _hoh_txt = ("ca. +%.2f m2 (0,11 m/gebouwscheidende wand x voor+achtergevel)" % _hoh if _hoh
                    else "0,11 m per gebouwscheidende wand x gevelhoogte op voor- EN achtergevel")
        dos.validatie.issues.append(
            "HART-OP-HART GEVEL-TOESLAG (ISSO 8.2) — ZELF TOEVOEGEN IN VABI (%s): %s. De tool telt "
            "dit bewust NIET automatisch mee." % (dos.identificatie.woningtype, _hoh_txt))
    _gevel_opm = ("benaderd (omtrek x hoogte - openingen; party-walls nog niet uitgefilterd); "
                  "verifieer in Vabi. " + (_g(p, "gevel_afwijking", default="") or "")).strip()
    schil.append(SchilDeel(
        id="gevel", type="gevel", subtype=_g(p, "geveltype", default="") or "",
        begrenzing=_g(p, "gevel_begrenzing", default="Buitenlucht") or "Buitenlucht",
        oppervlakte_m2=gevel_area, isolatie_aanwezig=_g(p, "isolatie_aanwezig", default="Onbekend") or "Onbekend",
        rc_bron=("Kwaliteitsverklaring" if is_bcrg_isolatiekeuze(
                 _g(p, "isolatie_aanwezig", default=""))
                 else (_g(p, "rc_bron", default="") or "")),
        spouw_aanwezig=_g(p, "spouw_aanwezig", bool),
        bcrg_code=_g(p, "gevel_bcrg_code", default="") or "",
        isolatiedikte_mm=_g(p, "isolatie_mm", float),
        opmerkingen=_gevel_opm))
    # vloer + dak (hergebruik extractor-helpers met report-p)
    schil.append(_maak_vloer(p, footprint))
    schil.append(_maak_dak(p, footprint))
    # kozijnen: geometrie-ramen koppelen aan report-classificaties (op volgorde)
    for i, w in enumerate(windows):
        koz = kozijnen[i] if i < len(kozijnen) else {}
        schil.append(SchilDeel(
            id="kozijn-%d" % (i + 1), type="kozijn", subtype=koz.get("element", "Raam") or "Raam",
            begrenzing="Buitenlucht", orientatie="", oppervlakte_m2=w["area"],
            glastype=koz.get("glastype", "") or "",
            kozijnmateriaal=koz.get("kozijnmateriaal") or "Hout of kunststof",  # 80%-default; alleen afwijking invoeren
            opmerkingen="locatie: " + (w.get("room", "") or "")))
    dos.schil = schil
    # AUDIT 12-7: deze API-route bevat BENADERINGEN die de Statistics-CSV-route niet heeft
    # (gevel-m² = 4*sqrt(footprint)*1.15, footprint-proxy voor vloer/dak, geen dakgeometrie/
    # kopgevels, ramen op volgorde gekoppeld, Ag = MagicPlan-woonoppervlak-heuristiek).
    # Niet stil laten passeren: luide issue in het dossier zelf.
    dos.validatie.issues.append(
        "LET OP: dossier via de API-route (benaderingen: gevel-m², footprint-proxy, Ag-heuristiek, "
        "geen dakgeometrie). Gebruik voor de VABI-export de Statistics-CSV-route en verifieer "
        "ALLE oppervlakken in Vabi.")
    return dos


def main():
    here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
    ap = argparse.ArgumentParser(description="Combineer MagicPlan plan-JSON + report-PDF -> dossier")
    ap.add_argument("--plan", default=os.path.join(root, "out", "plan_raw.json"))
    ap.add_argument("--report", required=True, help="MagicPlan project-report-PDF")
    ap.add_argument("--out", default=os.path.join(root, "out", "dossier_assembled.json"))
    a = ap.parse_args()
    plan = json.load(open(a.plan, encoding="utf-8"))
    p, kozijnen = report_parser.parse(a.report)
    dos = build_dossier(p, kozijnen, plan)
    os.makedirs(os.path.dirname(a.out), exist_ok=True); save_json(dos, a.out)
    print("OK: %s" % a.out)
    print("  %s %s | %d ruimtes | %d schildelen (%d kozijn) | Ag %.0f m2 | bouwjaar %s" % (
        dos.identificatie.postcode, dos.identificatie.huisnummer, len(dos.geometrie.ruimtes),
        len(dos.schil), sum(1 for s in dos.schil if s.type == "kozijn"),
        dos.geometrie.gebruiksoppervlakte_ag_m2, dos.identificatie.bouwjaar))


if __name__ == "__main__":
    main()
