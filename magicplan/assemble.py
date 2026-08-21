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
                          SchilDeel, save_json)
from core.geometry import polygon_oppervlakte_m2
from magicplan.extractor import _g, _functie, _map_ventilatie, _map_installaties, _maak_vloer, _maak_dak
from magicplan import report_parser
from magicplan.form_fingerprint import stamp_dossier_meta


def _value(values, vid):
    for it in (values or []):
        if isinstance(it, dict) and it.get("id") == vid:
            return it.get("value")
    return None


def _getal(waarde, default=0.0):
    """Veilig naar float: niet-numeriek (bv. een string uit kapotte JSON) of niet-eindig
    (NaN/Infinity) -> `default`, nooit een crash en nooit een besmet getal dat verderop stil
    doorsijpelt (bv. via `max()`, dat NaN niet betrouwbaar uitsluit)."""
    try:
        v = float(waarde)
    except (TypeError, ValueError):
        return default
    return v if math.isfinite(v) else default


def _opp(waarde, default=0.0):
    """Zoals `_getal`, maar dan voor een grootheid die nooit negatief kan zijn (oppervlakte,
    raambreedte/-hoogte): een negatieve waarde uit onbetrouwbare brondata is even onbruikbaar als
    NaN, en zou anders bv. een raam-'oppervlak' bij het gevelvlak OPTELLEN i.p.v. aftrekken."""
    v = _getal(waarde, default)
    return v if (v is not None and v >= 0) else default


def _floor_contour_m(fl):
    """Reconstrueer de echte grondvlak-contour (meter) uit MagicPlans plattegrond-beeldkaart.

    Elke bouwlaag levert een `image_map` met een `symbol_id: "floor"`-entry: de buitenomtrek van
    die verdieping als polygon in PIXELS van de gerenderde plattegrond-SVG. Die coördinaten hebben
    geen bekende schaal op zichzelf, maar `statistics.area_with_walls` (m2, bruto incl. wanden -
    dezelfde grootheid als de omtrek beschrijft) laat een schaalfactor afleiden: schaal (m/px) =
    sqrt(werkelijke oppervlakte / pixel-oppervlakte), aannemend dat x/y gelijk geschaald zijn
    (bevestigd tegen een echte export: een losse kamer-omtrek gaf x- en y-schaal binnen ~1% van
    elkaar). Dit is de ENIGE plek waar we een niet-vierkante footprint kunnen terugvinden -
    zonder deze data valt de tool terug op de vierkant-benadering uit gevel-m2.

    Geeft None als de data ontbreekt of te ontaard is om te vertrouwen (liever geen contour dan
    een verzonnen vorm - zelfde 'niet gokken'-regel als de rest van de keten): geen/meerdere
    'floor'-entries (bij >1 weten we niet welke bij area_with_walls hoort), niet-numerieke of
    niet-eindige (NaN/Infinity) coördinaten, of een bruto/netto-verhouding (area_with_walls vs.
    area) die niet aannemelijk is (bruto hoort door de wanddikte iets groter te zijn dan netto,
    niet fors groter/kleiner - anders hoort de schaal vermoedelijk niet bij déze polygon)."""
    if not isinstance(fl, dict):
        return None
    stats = fl.get("statistics")
    stats = stats if isinstance(stats, dict) else {}
    werkelijke_opp = _getal(stats.get("area_with_walls"))
    if werkelijke_opp <= 0:
        return None
    image_map = fl.get("image_map")
    image_map = image_map if isinstance(image_map, list) else []
    entries = [e for e in image_map if isinstance(e, dict) and e.get("symbol_id") == "floor"]
    if len(entries) != 1:
        return None
    coords = entries[0].get("coordinates") or []
    if not isinstance(coords, list):
        return None
    if len(coords) < 8 or len(coords) % 2:  # minstens 4 punten, volledige (x, y)-paren
        return None
    try:
        punten_px = [(float(x), float(y)) for x, y in zip(coords[0::2], coords[1::2])]
    except (TypeError, ValueError):
        return None
    if any(not (math.isfinite(x) and math.isfinite(y)) for x, y in punten_px):
        return None  # NaN/Infinity in de brondata -> geen contour vertrouwen (niet gokken)
    opp_px = polygon_oppervlakte_m2(punten_px)  # eenheid hier: px2, functienaam blijft kloppen (m2-formule)
    if opp_px <= 0:
        return None
    netto_opp = _getal(stats.get("area"))
    if netto_opp > 0 and not (netto_opp <= werkelijke_opp <= netto_opp * 1.5):
        return None
    schaal = math.sqrt(werkelijke_opp / opp_px)  # m per pixel
    min_x = min(p[0] for p in punten_px)
    min_y = min(p[1] for p in punten_px)
    return [[round((x - min_x) * schaal, 3), round((y - min_y) * schaal, 3)] for x, y in punten_px]


def geometry_from_plan(plan):
    """Lees de echte MagicPlan v2-structuur: data.plan_data.floors[].rooms[].objects[]."""
    data = plan.get("data", plan)
    pd = data.get("plan_data", {})
    geo = Geometrie(gebruiksoppervlakte_ag_m2=_opp(pd.get("living_area")))
    windows, total_h, areas = [], 0.0, []
    for fl in pd.get("floors", []):
        area = _opp((fl.get("statistics") or {}).get("area"))
        ch = _getal(_value(fl.get("values"), "ceilingHeight"), None)
        geo.vloeren.append(VloerInfo(naam=fl.get("name", ""), oppervlakte_m2=area,
                                     hoogte_m=ch, contour_m=_floor_contour_m(fl)))
        if ch:
            total_h += ch
        areas.append((fl.get("name", ""), area))
        for rm in fl.get("rooms", []):
            rn = rm.get("name", "")
            ra = _opp((rm.get("statistics") or {}).get("area"))
            geo.ruimtes.append(Ruimte(naam=rn, functie=_functie(rn), oppervlakte_m2=ra))
            for o in rm.get("objects", []):
                sid = (o.get("symbol_id") or "").lower()
                if sid.startswith("window") or sid == "doorwithwindow":
                    w = _opp(_value(o.get("values"), "width"), None)
                    h = _opp(_value(o.get("values"), "height"), None)
                    a = round(w * h, 2) if w and h else 0.0
                    windows.append({"area": a, "room": rn})
    footprint = max((a for _, a in areas), default=0.0)   # grootste verdieping = footprint-proxy
    # buitenomtrek BENADEREN uit de footprint (de MagicPlan-perimeter telt binnenwanden mee);
    # 4*sqrt(opp) = omtrek vierkant, x1.15 voor niet-vierkante plattegrond. footprint > 0 bewaakt
    # zowel een lege/negatieve als een NaN-oppervlakte uit onbetrouwbare API-data (math.sqrt op een
    # negatief getal crasht; NaN faalt de '> 0'-test en valt dus terecht op 0.0 terug).
    perimeter = round(4 * math.sqrt(footprint) * 1.15, 1) if footprint > 0 else 0.0
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
        rc_bron=_g(p, "rc_bron", default="") or "", spouw_aanwezig=_g(p, "spouw_aanwezig", bool),
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
    stamp_dossier_meta(dos)
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
