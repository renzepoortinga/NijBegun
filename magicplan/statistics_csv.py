"""MagicPlan **Statistics-CSV** -> dossier.

De Statistics-export bevat ALLES wat we nodig hebben en structureler dan de API-JSON:
PLAN/FLOOR/ROOM/WALL-attributes inclusief onze custom velden (oriëntatie per wand, glas/kozijn per
raam, deur-met-raam, begrenzing, thermische massa, ventilatie/verwarming). Categorische form-waarden
worden door MagicPlan ge-'dot' (spatie en '/' -> '.'); die herstellen we voor de bekende velden.

Gebruik:  python magicplan/statistics_csv.py --csv "Oosterkade 23 Statistics.csv" \
              --straat Oosterkade --huisnummer 23 --postcode 9503HN --plaats Stadskanaal \
              --out out/dossier_oosterkade_csv.json
"""
import csv, os, sys, io, json, argparse, re

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from core.dossier import (Dossier, Identificatie, Opname, Geometrie, Ruimte, VloerInfo,
                          SchilDeel, Ventilatie, Verwarming, Installaties,
                          Koeling, Tapwater, ZonneEnergieSysteem)
from core.geometry import (woningscheidende_wand_toeslag_m2, aantal_woningscheidende_wanden,
                           hellingshoek_uit_nok, dak_vlakken_zadeldak, dak_vlakken_lessenaar,
                           dak_vlakken_schilddak)


def _f(v):
    try:
        return float(str(v).replace(",", ".").strip())
    except Exception:
        return None


def _undot(v):
    """Herstel een ge-'dot' categorische waarde: 't.m' -> 't/m', overige '.' -> spatie."""
    s = (v or "").strip()
    if not s:
        return ""
    s = s.replace("t.m", "t/m")
    return s.replace(".", " ").strip()


def _eerste_jaar(klasse):
    """'1992 t/m 2013' / '1992.t.m.2013' -> 1992 (eerste jaartal in de klasse)."""
    m = re.search(r"(19|20)\d{2}", _undot(klasse))
    return int(m.group(0)) if m else None


# functie-classificatie uit de ruimtenaam (NL + EN), gespiegeld aan ventilatie/ventilatie.py
_FUNCTIE_KW = [
    ("keuken", ["keuken", "kitchen"]),
    ("badkamer", ["bad", "douche", "bathroom"]),
    ("toilet", ["toilet", "wc"]),
    ("wasruimte", ["was", "bijkeuken", "utility", "laundry"]),
    ("verkeer", ["hal", "hallway", "overloop", "gang", "trap", "entree", "portaal", "vestibule", "corridor", "hall"]),
    ("slaapkamer", ["slaap", "bed"]),
    ("verblijfsruimte", ["woon", "living", "studeer", "kantoor", "eet", "zit", "room"]),
]


def _functie_uit_naam(naam):
    n = (naam or "").lower()
    for f, kws in _FUNCTIE_KW:
        if any(k in n for k in kws):
            return f
    return "overig"

# Begrenzing-NAAMCONVENTIE: omdat MagicPlan geen los begrenzing-veld per buitengevel toelaat, kan de
# adviseur de WAND benoemen met een begrenzing-token (bv. "Achtergevel AOR garage", "Kelderwand grond",
# "buurwand AVR"). De gevel is dan parent: ramen/deuren in die wand erven de begrenzing. Volgorde =
# prioriteit (eerste match wint). 'AVR' (aangrenzende verwarmde ruimte/buurwoning) -> NIET in de schil.
_BEGR_TOKENS = [
    ("AVR", ("avr", "buurwoning", "buurwand", "woningscheidend", "aangrenzende woning", "naburige")),
    ("Onverwarmde kelder", ("onverwarmde kelder", "kelder")),
    ("Kruipruimte", ("kruipruimte", "kruip")),
    ("Grond", ("grond", "talud", "souterrain")),
    ("AOS", ("aos", "serre")),
    ("Sterk geventileerd", ("sterk geventileerd", "asgr")),
    ("AOR", ("aor", "garage", "onverwarmd")),
    ("Water", ("water",)),
]


def _begrenzing_uit_naam(naam):
    """Lees de begrenzing uit de wandnaam (naamconventie). Default Buitenlucht. 'AVR' = buiten de schil."""
    n = (naam or "").lower()
    for begr, toks in _BEGR_TOKENS:
        if any(t in n for t in toks):
            return begr
    return "Buitenlucht"


# Extra wandnaam-/ruimtenaam-tokens (MagicPlan-dropdowns slaan niet betrouwbaar op -> gebruik de NAAM):
_NAREKENEN_TOKS = ("narekenen", "nareken", "splits", "deels buiten", "deels binnen", "vabi-check")


def _narekenen_uit_naam(naam):
    """True als de adviseur de wand/het vlak markeerde om handmatig in Vabi na te rekenen (bv. een muur
    die deels aan buiten en deels aan binnen grenst; de tool neemt dan de héle muur)."""
    n = (naam or "").lower()
    return any(t in n for t in _NAREKENEN_TOKS)


def _isolatie_uit_naam(naam):
    """Per-wand isolatie-override uit de wandnaam (afwijkende gevel). 'ongeisoleerd'/'niet geisoleerd'
    -> Nee; 'geisoleerd'/'nageisoleerd'/'na-isolatie' -> Ja; anders None (= projectdefault)."""
    n = (naam or "").lower()
    if "ongeisoleerd" in n or "ongeïsoleerd" in n or "niet geisoleerd" in n or "niet geïsoleerd" in n:
        return "Nee"
    if "geisoleerd" in n or "geïsoleerd" in n or "nageisoleerd" in n or "na-isolatie" in n or "naisolatie" in n:
        return "Ja"
    return None


# --- Gevel-naamgeving i.p.v. kompas per wand (veel makkelijker in het veld) ---------------------------
# Benoem buitenmuren "voorgevel/achtergevel/linkergevel/rechtergevel"; de tool leidt de oriëntatie van
# de 3 andere gevels af uit die van de VOORGEVEL (projectveld "Oriëntatie voorgevel"). Conventie:
# 'vanaf de straat gezien' -> rechter = voorgevel -90°, linker = +90°, achter = +180°.
_GEVEL_NAAM_TOKENS = [
    ("voor",   ("voorgevel", "voorzijde", "voor gevel", "vooraanzicht")),
    ("achter", ("achtergevel", "achterzijde", "achter gevel")),
    ("rechts", ("rechtergevel", "rechter gevel", "rechterzijgevel", "rechter zijgevel",
                "zijgevel rechts", "rechterzijde")),
    ("links",  ("linkergevel", "linker gevel", "linkerzijgevel", "linker zijgevel",
                "zijgevel links", "linkerzijde")),
]
_COMPAS = ["n", "no", "o", "zo", "z", "zw", "w", "nw"]   # 8-punts, met de klok mee vanaf N (45°/stap)
_KOMPAS_SYN = {"noord": "n", "noordoost": "no", "oost": "o", "zuidoost": "zo", "zuid": "z",
               "zuidwest": "zw", "west": "w", "noordwest": "nw"}
# rotatie t.o.v. de voorgevel (45° = 1 stap; 90° = 2 stappen): rechter -90, links +90, achter +180.
_GEVEL_ROTATIE = {"voor": 0, "rechts": -2, "achter": 4, "links": 2}


def _gevel_naam_uit_naam(naam):
    """voor|achter|links|rechts uit de wandnaam, of '' als niet benoemd."""
    n = (naam or "").lower()
    for key, toks in _GEVEL_NAAM_TOKENS:
        if any(t in n for t in toks):
            return key
    return ""


def _norm_kompas(s):
    s = (s or "").strip().lower().replace("-", "").replace(" ", "")
    s = _KOMPAS_SYN.get(s, s)
    return s if s in _COMPAS else ""


def _orient_afleiden(gevel_naam, voorgevel_orient):
    """Leid de gevel-oriëntatie af uit de naam + de voorgevel-oriëntatie. '' als onbepaald."""
    vg = _norm_kompas(voorgevel_orient)
    if not vg or gevel_naam not in _GEVEL_ROTATIE:
        return ""
    return _COMPAS[(_COMPAS.index(vg) + _GEVEL_ROTATIE[gevel_naam]) % 8].upper()


def _orient_uit_naam(naam):
    """Expliciete kompas-override in de wandnaam (bv. 'Rechtergevel O', 'Zijgevel ZW'): het LAATSTE losse
    kompastoken (zodat het gevel-naamwoord zelf niet als richting wordt gelezen). '' als afwezig."""
    found = ""
    for tok in re.split(r"[\s,/]+", (naam or "").lower()):
        k = _norm_kompas(tok)
        if k:
            found = k
    return found.upper()


# Rekenzone uit de wand-/ruimtenaam (universeel, naam-gebaseerd -> robuust). Default 1.
_REKENZONE_RE = re.compile(r"(?:rekenzone|reken-?zone|zone|rz)\s*([123])\b")


def _rekenzone_uit_naam(naam):
    """'... zone 2' / '... rekenzone 3' / '... rz2' in de naam -> 2/3; anders 1."""
    m = _REKENZONE_RE.search((naam or "").lower())
    return int(m.group(1)) if m else 1


_KOZIJN_MAT = {"a": "Hout of kunststof", "b": "Metaal thermisch onderbroken",
               "c": "Metaal niet thermisch onderbroken"}


def _norm_kozijn_mat(v):
    """Kozijntype A/B/C (officieel formulier) -> kozijnmateriaal. A=hout/kunststof, B=metaal therm.
    onderbroken, C=metaal niet-onderbroken. Default Hout of kunststof."""
    s = _undot(v).strip().lower()
    if not s:
        return "Hout of kunststof"
    if s[0] in _KOZIJN_MAT and (len(s) == 1 or not s[1].isalpha()):
        return _KOZIJN_MAT[s[0]]
    if "thermisch onderbroken" in s:
        return "Metaal thermisch onderbroken"
    if "metaal" in s or "aluminium" in s:
        return "Metaal niet thermisch onderbroken"
    return "Hout of kunststof"


def _parse_sections(path):
    """Splits de CSV in secties op de hoofdkop-rijen. Geeft {sectienaam: [rows]}."""
    rows = list(csv.reader(open(path, encoding="utf-8-sig")))
    heads = {"PLAN ATTRIBUTES", "FLOOR ATTRIBUTES", "ROOM ATTRIBUTES", "WALL ATTRIBUTES",
             "OBJECT COUNT", "Object Attributes"}
    sec, cur = {}, None
    for r in rows:
        c0 = (r[0] if r else "").strip()
        if c0 in heads:
            cur = c0
            sec.setdefault(cur, []).append(r)
        elif cur:
            sec[cur].append(r)
    return sec


def _plan_kv(plan_rows):
    """PLAN ATTRIBUTES -> {key: raw_value}. Pakt key uit kolom 0 (zonder ': unit'), waarde kolom 1."""
    kv = {}
    for r in plan_rows[1:]:
        if len(r) < 2:
            continue
        key = re.sub(r":\s*m[²³]?$", "", (r[0] or "").strip()).strip()
        val = (r[1] or "").strip()
        if key:
            kv[key] = val
    return kv


def build_dossier(csv_path, straat="", huisnummer="", postcode="", plaats="", woningtype="",
                  gevelhoogte_m=None):
    sec = _parse_sections(csv_path)
    plan = _plan_kv(sec.get("PLAN ATTRIBUTES", []))
    G = lambda k: plan.get(k, "")
    notes = []

    dos = Dossier()
    bouwjaar_klasse = _undot(G("Bouwjaar") or G("Bouwjaar-klasse (vloer)"))
    # woningtype: CLI-arg wint; anders uit het MagicPlan-veld "Woningtype"
    woningtype = woningtype or _undot(G("Woningtype"))
    # renovatiejaar: alleen bij aantoonbare energiebesparende maatregel (ISSO 7.1.4) — adviseur vult
    renovatiejaar = _f(G("Renovatiejaar"))
    # oriëntatie van de VOORGEVEL (projectveld) -> de tool leidt de andere gevels af uit de wandnaam
    orientatie_voorgevel = _norm_kompas(_undot(G("Orientatie voorgevel")) or _undot(G("Oriëntatie voorgevel"))
                                        or _undot(G("Voorgevel orientatie")))
    dos.identificatie = Identificatie(
        straat=straat, huisnummer=str(huisnummer), postcode=postcode, plaats=plaats,
        bouwjaar=_eerste_jaar(bouwjaar_klasse), woningtype=woningtype,
        type_dak=_undot(G("Type dak")), orientatie_voorgevel=orientatie_voorgevel.upper(),
        renovatiejaar=int(renovatiejaar) if renovatiejaar else None)
    # gevelhoogte: CLI-arg wint; anders uit het MagicPlan-veld "Gevelhoogte (m)" / "Gevelhoogte"
    if gevelhoogte_m is None:
        gevelhoogte_m = _f(G("Gevelhoogte (m)")) or _f(G("Gevelhoogte"))
    # qv10 gemeten? alleen True bij een blowerdoormeting (ISSO 7.1.5) — uit het form-veld "Qv10 gemeten?"
    qv10_gem = _undot(G("Qv10 gemeten?")).strip().lower() in ("ja", "yes", "true", "gemeten")
    dos.opname = Opname(
        qv10_waarde=_f(G("Qv10-waarde (dm3/s.m2)")),
        qv10_gemeten=qv10_gem,
        gevelhoogte_m=gevelhoogte_m,
        thermische_massa_wanden=_undot(G("Thermische massa wanden")),
        thermische_massa_vloeren=_undot(G("Thermische massa vloeren")))

    # ---- geometrie: ruimtes (Ag) + verdiepingen ----
    geo = Geometrie()
    room_rows = sec.get("ROOM ATTRIBUTES", [])
    floor_names = set()
    for r in sec.get("FLOOR ATTRIBUTES", [])[1:]:
        if r and r[0].strip():
            floor_names.add(r[0].strip())
    vloer_split = {}   # begrenzing -> m2: begane-grondvloerdelen met afwijkende begrenzing (uit ruimtenaam)
    for r in room_rows[1:]:
        if not r:
            continue
        naam = (r[0] or "").strip()
        if not naam or naam in floor_names:
            continue
        ag = _f(r[1]) if len(r) > 1 else None
        if ag is None:
            continue
        geo.ruimtes.append(Ruimte(naam=naam, functie=_functie_uit_naam(naam), oppervlakte_m2=ag))
        rb = _begrenzing_uit_naam(naam)
        if rb not in ("Buitenlucht", "AVR"):   # ruimtenaam-token grond/kruip/kelder/... -> apart vloerdeel
            vloer_split[rb] = round(vloer_split.get(rb, 0.0) + ag, 2)
    geo.gebruiksoppervlakte_ag_m2 = _f(G("Total living area")) or sum(r.oppervlakte_m2 for r in geo.ruimtes)
    # ISSO 7.2.1: vloeroppervlak waarboven de netto hoogte < 1,5 m telt NIET mee voor Ag (schuin dak).
    # MagicPlan meet op vloerniveau (incl. de lage strook) -> adviseur vult de aftrek in het form-veld.
    # let op: veldnaam KOMMAVRIJ (CSV splitst op komma) -> "Ag-aftrek zolder (m2)"
    ag_aftrek = (_f(G("Ag-aftrek zolder (m2)")) or _f(G("Ag-aftrek zolder (m²)"))
                 or _f(G("Ag-aftrek zolder")) or _f(G("Vloeroppervlak onder 1.5m")) or 0.0)
    if ag_aftrek and geo.gebruiksoppervlakte_ag_m2:
        geo.gebruiksoppervlakte_ag_m2 = round(max(0.0, geo.gebruiksoppervlakte_ag_m2 - ag_aftrek), 2)
        notes.append("Ag verlaagd met %.2f m² (vloer <1,5 m onder schuin dak, ISSO 7.2.1)." % ag_aftrek)
    geo.perimeter_m = _f(G("Exterior perimeter"))

    # verdiepingshoogte: gemiddelde ceiling height of uit floor-attributes; gebouwhoogte schatten
    floor_hoogtes, floor_begrenzing, floor_footprint = [], {}, {}
    fa = sec.get("FLOOR ATTRIBUTES", [])
    if fa:
        hdr = fa[0]
        ci = {h.strip(): i for i, h in enumerate(hdr)}
        ch_i = ci.get("Ceiling Height")
        bg_i = ci.get("Begrenzing")
        gs_i = next((i for h, i in ci.items() if h.startswith("Ground surface without walls")), None)
        for r in fa[1:]:
            if not r or not r[0].strip():
                continue
            naam = r[0].strip()
            if ch_i is not None and ch_i < len(r):
                h = _f((r[ch_i] or "").replace("m", ""))
                if h:
                    floor_hoogtes.append(h)
                    geo.vloeren.append(VloerInfo(naam=naam, hoogte_m=h))
            if bg_i is not None and bg_i < len(r):
                floor_begrenzing[naam] = _undot(r[bg_i])
            if gs_i is not None and gs_i < len(r):
                fp = _f(r[gs_i])
                if fp:
                    floor_footprint[naam] = fp
    if dos.opname.gevelhoogte_m is None and floor_hoogtes:
        dos.opname.gevelhoogte_m = round(sum(floor_hoogtes), 2)  # som verdiepingshoogtes ~ gevelhoogte
    # begane-grond-footprint: verdieping met 'ground/grond/begane' in de naam, anders grootste
    # niet-kelder-vloer (kelder = 'basement/kelder'); fallback grootste overall.
    def _is_bg(n): return any(k in n.lower() for k in ("ground", "grond", "begane"))
    def _is_kelder(n): return any(k in n.lower() for k in ("basement", "kelder"))
    footprint_bg = (next((v for n, v in floor_footprint.items() if _is_bg(n)), None)
                    or max([v for n, v in floor_footprint.items() if not _is_kelder(n)] or [0])
                    or max(floor_footprint.values() or [0]) or None)
    dos.geometrie = geo

    # ---- WALL ATTRIBUTES (positioneel; header heeft dubbele kolomnamen) ----
    # 8=Type 4=Surf-zonder-openingen 3=Surface 11=Orientatie(wand) 9=Isolatie(wand) 12=Bron
    # 15=kozijn hout/kunststof 16=glas(raam) 17=orientatie(raam) 18=Type constructie(deur)
    # 19=opp raam in deur 20=glas(deur)
    wall_rows = sec.get("WALL ATTRIBUTES", [])
    # het 'Deels binnen/deels buiten? (narekenen)'-VINKJE op het wand-element: kolom op NAAM zoeken
    # in de header (robuust; positie kan schuiven). Vinkje aan = zelfde effect als 'narekenen' in de naam.
    _kop = wall_rows[0] if wall_rows else []
    _idx_nareken = next((i for i, h in enumerate(_kop)
                         if "nareken" in (h or "").lower() or "deels binnen" in (h or "").lower()), None)
    # 'Raam/paneel'-keuze op het venster-element (naam-gebaseerd; kolom kan schuiven). Het LIVE veld heet
    # "Raam = Ja | Paneel = Nee" (opties "Ja (raam)" / "Nee (dicht paneel)"). Waarde met 'paneel' erin
    # -> geen glas maar een DICHTE constructie (paneel-in-kozijn). Kolom afwezig -> alles blijft raam.
    _idx_raampaneel = next((i for i, h in enumerate(_kop)
                            if "raam/paneel" in (h or "").lower()
                            or ("raam" in (h or "").lower() and "paneel" in (h or "").lower())
                            or (h or "").strip().lower() == "paneel"), None)
    gevel_per = {}      # (orientatie, begrenzing) -> m2 (binnenwerks, zonder openingen)
    gevel_bruto = {}    # idem mét openingen (voor volledigheidscheck)
    orient_naam = {}    # orientatie -> gevel-naam (voor/achter/links/rechts) voor leesbaar label
    kozijnen = []
    panelen = []          # dichte panelen-in-kozijn (Raam/paneel = paneel): dichte constructie i.p.v. glas
    deuren = []
    cur_orient = ""           # oriëntatie van de huidige (moeder)wand
    cur_begr = "Buitenlucht"  # begrenzing van de moederwand (parent; ramen/deuren erven die)
    n_wall_ext = 0
    nareken_namen = []        # wanden die de adviseur markeerde om handmatig in Vabi na te rekenen
    for r in wall_rows[1:]:
        if len(r) < 12 or not (r[0] or "").strip():
            continue
        typ = (r[8] or "").strip() if len(r) > 8 else ""
        if typ == "Wall":
            # oriëntatie: expliciet wint (CSV-oriëntatiekolom of kompastoken in de naam), anders afleiden
            # uit de gevel-naam (voor/achter/links/rechts) + de voorgevel-oriëntatie.
            cur_gevel_naam = _gevel_naam_uit_naam(r[0])
            col_orient = (r[11] or "").strip() if len(r) > 11 else ""
            cur_orient = (col_orient or _orient_uit_naam(r[0])
                          or _orient_afleiden(cur_gevel_naam, orientatie_voorgevel))
            cur_begr = _begrenzing_uit_naam(r[0])   # begrenzing uit de wandnaam (naamconventie)
            cur_isol = _isolatie_uit_naam(r[0])     # per-wand isolatie-override (None = projectdefault)
            _chk = ((r[_idx_nareken] or "").strip().lower()
                    if (_idx_nareken is not None and len(r) > _idx_nareken) else "")
            cur_nareken = (_narekenen_uit_naam(r[0])            # naam-token (blijft werken) ...
                           or _chk in ("yes", "ja", "true", "1", "aan"))  # ... of het VINKJE op de wand
            cur_rz = _rekenzone_uit_naam(r[0])      # rekenzone uit de naam (default 1)
            if cur_begr == "AVR":      # buurwoning/woningscheidend -> NIET in de schil (ISSO p.66/75)
                cur_orient = ""        # ramen/deuren in deze wand vallen ook weg
                continue
            if cur_orient:  # oriëntatie bekend (ingevuld of afgeleid) = buitengevel (telt mee)
                n_wall_ext += 1
                k = (cur_orient, cur_begr, cur_isol or "", cur_nareken, cur_rz)
                gevel_per[k] = round(gevel_per.get(k, 0.0) + (_f(r[4]) or 0.0), 2)
                gevel_bruto[k] = round(gevel_bruto.get(k, 0.0) + (_f(r[3]) or 0.0), 2)
                if cur_gevel_naam and cur_orient not in orient_naam:
                    orient_naam[cur_orient] = cur_gevel_naam
                if cur_nareken:
                    nareken_namen.append(r[0].strip())
        elif typ == "Window":
            orient = ((r[17] or "").strip() if len(r) > 17 else "") or cur_orient
            if not orient:   # binnenraam / niet-buitengevel -> niet in thermische schil
                continue
            _rp = ((r[_idx_raampaneel] or "").strip().lower()
                   if (_idx_raampaneel is not None and len(r) > _idx_raampaneel) else "")
            if "paneel" in _rp:          # dicht paneel-in-kozijn -> dichte constructie (geen glas)
                def _bn(frag):
                    i = next((k for k, h in enumerate(_kop) if frag in (h or "").lower()), None)
                    return ((r[i] or "").strip() if (i is not None and len(r) > i) else "")
                panelen.append({"area": _f(r[3]) or 0.0, "orient": orient, "begr": cur_begr,
                                "isolatie": _undot(_bn("paneel - isolatie aanwezig")) or "Onbekend",
                                "dikte": _f(_bn("paneel - isolatiedikte")),
                                "bouwjaarklasse": _bn("paneel - bouwjaarklasse")})
            else:
                kozijnen.append({"area": _f(r[3]) or 0.0,
                                 "glas": (r[16] or "").strip() if len(r) > 16 else "",
                                 "orient": orient, "begr": cur_begr,
                                 "kozijn_hk": (r[15] or "").strip() if len(r) > 15 else ""})
        elif typ == "Door":
            orient = ((r[17] or "").strip() if len(r) > 17 else "") or cur_orient
            # deur-kolommen op NAAM (Deur-groep is 8-7 geherstructureerd: glas-velden conditioneel
            # onder 'Type constructie (deur)' + nieuwe 'Glas >= 65%'-vraag) — positioneel als fallback
            def _kol(frag, fb):
                return next((i for i, h in enumerate(_kop) if frag in (h or "").lower()), fb)
            def _byname(frag):
                i = _kol(frag, None)
                return ((r[i] or "").strip() if (i is not None and len(r) > i) else None)
            _ix_tc = _kol("type constructie", 18)
            tc = _undot(r[_ix_tc]) if len(r) > _ix_tc else ""
            if not orient and not tc:   # binnendeur -> niet in thermische schil
                continue
            # glas: 'Deur met raam' OF de 65%-variant (aparte kolommen); positioneel alleen als
            # de naam-kolommen helemaal ontbreken (legacy-export)
            _g1, _g2 = _byname("type glas (65"), _byname("type glas (indien")
            glas = (_g1 or _g2) if (_g1 is not None or _g2 is not None) else \
                   ((r[20] or "").strip() if len(r) > 20 else "")
            _o1, _o2 = _byname("oppervlakte glas 65"), _byname("oppervlakte raam in deur")
            opp = _f(_o1 or _o2) if (_o1 is not None or _o2 is not None) else \
                  (_f(r[19]) if len(r) > 19 else None)
            _blg = _f(_byname("bovenlicht - oppervlak glas"))
            if _blg:                     # glas-bovenlicht telt mee als glas-in-deur
                opp = (opp or 0.0) + _blg
            _blp = _f(_byname("bovenlicht-paneel - oppervlak"))
            if _blp:                     # paneel-bovenlicht = dichte paneel-constructie boven de deur
                panelen.append({"area": _blp, "orient": orient, "begr": cur_begr,
                                "isolatie": _undot(_byname("bovenlicht-paneel - isolatie aanwezig") or "") or "Onbekend",
                                "dikte": _f(_byname("bovenlicht-paneel - isolatiedikte")),
                                "bouwjaarklasse": _byname("bovenlicht-paneel - bouwjaarklasse") or ""})
            deuren.append({"area": _f(r[3]) or 0.0, "type_constructie": tc, "opp_raam": opp,
                           "glas": glas, "orient": orient, "begr": cur_begr})

    # ---- schil opbouwen ----
    schil = []

    # VABI-beslisboom per bouwdeel (nieuwe Constructies-form): Invoer (Kwaliteitsverklaring/Beslisschema)
    # -> Isolatie aanwezig? (Ja/Nee/Onbekend) -> isolatiedikte onbekend?/bouwjaar/dikte (mm)/spouw.
    # "Kwaliteitsverklaring" -> de tool VLAGT het (adviseur zet Invoer zelf in VABI; golden rule: niet gokken).
    # Valt terug op de oude platte velden (Rc-bron <deel> / Isolatie aanwezig) zodat oudere exports blijven werken.
    def _bouwdeel(prefix, oud_rcveld="", oud_isolveld="", oud_begrveld=""):
        gv = lambda *names: next((v for v in (_undot(G(n)) for n in names) if v), "")
        invoer = gv(prefix + " - invoer", prefix + " - invoer (override)")
        iso = gv(prefix + " - isolatie aanwezig?")
        dikte_onb = gv(prefix + " - isolatiedikte onbekend?").lower() in ("ja", "yes", "true")
        dikte = _f(G(prefix + " - isolatiedikte (mm)"))
        bouwjaar = gv(prefix + " - bouwjaar", prefix + " - bouwjaar (onbekend)")
        spouw_s = gv(prefix + " - spouw aanwezig?", prefix + " - spouw aanwezig (indien <40mm)?")
        begr = gv(prefix + " - begrenzing")
        oud_rc = _undot(G(oud_rcveld)) if oud_rcveld else ""
        # fallback naar de oude platte velden als de nieuwe boom leeg is
        if not (invoer or iso or dikte or bouwjaar):
            iso = (_undot(G(oud_isolveld)) if oud_isolveld else "") or _undot(G("Isolatie aanwezig"))
            if _undot(G("Isolatiedikte onbekend")).lower() == "yes":
                dikte_onb = True
        if not begr and oud_begrveld:
            begr = _undot(G(oud_begrveld))
        # rc_bron afleiden
        rcl = (invoer + " " + oud_rc).lower()
        if "kwaliteitsverklaring" in rcl or "verklaring" in rcl:
            rc = "Kwaliteitsverklaring"
        elif "opgemeten" in oud_rc.lower() or (dikte and not dikte_onb):
            rc = "Opgemeten dikte"
        elif dikte_onb or "onbekend" in (iso + " " + oud_rc).lower() or bouwjaar:
            rc = "Dikte onbekend"
        else:
            rc = ""
        spouw = None if not spouw_s else (spouw_s.lower() in ("ja", "yes", "true"))
        return {"rc_bron": rc,
                "isolatie": {"ja": "Ja", "nee": "Nee", "onbekend": "Onbekend"}.get(iso.lower(), iso or "Onbekend"),
                "dikte_mm": (dikte if not dikte_onb else None),
                "dikte_onbekend": dikte_onb, "spouw": spouw, "begrenzing": begr, "bouwjaar": bouwjaar}

    g_b = _bouwdeel("Gevel", "Rc-bron gevel", "Isolatie aanwezig")
    v_b = _bouwdeel("Vloer", "Rc-bron vloer", "", "Begrenzing (vloer)")
    d_b = _bouwdeel("Dakvlak 1", "Rc-bron dak")
    gevel_rc, vloer_rc, dak_rc = g_b["rc_bron"], v_b["rc_bron"], d_b["rc_bron"]
    isol = g_b["isolatie"] or "Onbekend"          # projectdefault gevel (wand-loop gebruikt dit)
    dikte_onbekend = g_b["dikte_onbekend"]
    # gevels per oriëntatie + ISSO 8.2 hart-op-hart-toeslag (woningtype-afhankelijk)
    n_buur = aantal_woningscheidende_wanden(woningtype)
    toeslag_tot = woningscheidende_wand_toeslag_m2(dos.opname.gevelhoogte_m, woningtype) if n_buur else 0.0
    n_gevel = max(len(gevel_per), 1)
    for (orient, begr, isol_ov, nareken, rz), opp in sorted(gevel_per.items()):
        extra = round(toeslag_tot / n_gevel, 2) if toeslag_tot else 0.0
        suffix = "" if begr == "Buitenlucht" else "-" + begr[:3].lower()
        if isol_ov or nareken:
            suffix += "-ov"
        if rz > 1:
            suffix += "-z%d" % rz
        gnaam = orient_naam.get(orient, "")
        gid = "gevel-%s%s" % (gnaam or orient, suffix)
        wand_isol = isol_ov or isol   # per-wand override wint van de projectdefault
        schil.append(SchilDeel(
            id=gid, type="gevel", subtype="", begrenzing=begr,
            orientatie=orient, gevel_naam=gnaam, oppervlakte_m2=round(opp + extra, 2),
            isolatie_aanwezig=wand_isol, rekenzone=rz, rc_bron=gevel_rc,
            isolatiedikte_mm=g_b["dikte_mm"], spouw_aanwezig=g_b["spouw"],
            opmerkingen=((("%sgevel" % gnaam + " | ") if gnaam else "")
                         + "binnenwerks; AVR/party-walls uitgefilterd"
                         + (" | begrenzing %s (naamconventie)" % begr if begr != "Buitenlucht" else "")
                         + (" | +%.2f m2 hart-op-hart (ISSO 8.2)" % extra if extra else "")
                         + (" | isolatie %s (per-wand override)" % isol_ov if isol_ov else "")
                         + (" | Rc/U via kwaliteitsverklaring (zet Invoer in Vabi)" if gevel_rc == "Kwaliteitsverklaring" else "")
                         + (" | NAREKENEN in Vabi (gemarkeerd: deels buiten/binnen of bijzonder)" if nareken else ""))))
    if orientatie_voorgevel:
        afg = lambda gn: _orient_afleiden(gn, orientatie_voorgevel) or "?"
        notes.append("Voorgevel-oriëntatie %s -> afgeleid: voorgevel=%s, rechtergevel=%s, achtergevel=%s, "
                     "linkergevel=%s (controleer; corrigeer via 'Oriëntatie voorgevel' of een kompastoken "
                     "in de gevelnaam, bv. 'Rechtergevel O')."
                     % (orientatie_voorgevel.upper(), afg("voor"), afg("rechts"), afg("achter"), afg("links")))
    if not gevel_per:
        notes.append("GEEN buitengevels met oriëntatie gevonden — benoem buitenmuren 'voorgevel/achtergevel/"
                     "linkergevel/rechtergevel' én vul 'Oriëntatie voorgevel' in (of geef per wand een kompasrichting).")
    else:
        # volledigheidscheck: getagde gevel (bruto) vs omtrek x gebouwhoogte, gecorrigeerd voor
        # woningtype (bij tussen/hoek zijn niet alle wanden buitengevel: ~(4-n_buur)/4 van de omtrek).
        bruto = sum(gevel_bruto.values())
        ext_fractie = max(4 - n_buur, 1) / 4.0
        schatting = (geo.perimeter_m or 0) * (dos.opname.gevelhoogte_m or 0) * ext_fractie
        if schatting and bruto < 0.6 * schatting:
            notes.append("Gevel mogelijk ONVOLLEDIG: %d buitenmuren getagd = %.0f m² bruto, maar verwacht "
                         "≈ %.0f m² (omtrek×hoogte×%.2f voor %s). Controleer of álle buitenmuren een "
                         "oriëntatie hebben (woningscheidende wand: géén oriëntatie)."
                         % (n_wall_ext, bruto, schatting, ext_fractie, woningtype or "onbekend woningtype"))

    if nareken_namen:
        notes.append("HANDMATIG NAREKENEN in Vabi (door jou gemarkeerd): %s. De tool nam telkens de héle "
                     "muur — corrigeer het gevel-oppervlak/de begrenzing voor het afwijkende deel."
                     % ", ".join(sorted(set(nareken_namen))))

    # vloer (begane grond): begrenzing uit Schil&zone/Floor; afwijkende delen (grond/kruip/kelder) via ruimtenaam
    vloer_begr = v_b["begrenzing"] or _undot(G("Begrenzing (vloer)")) or "Kruipruimte"
    bg_floor_area = footprint_bg or _f(G("Above grade living area"))  # begane-grond-footprint (niet de meerlaagse som)
    split_tot = round(sum(vloer_split.values()), 2)
    hoofd_area = round(max(0.0, (bg_floor_area or 0.0) - split_tot), 2) if split_tot else (bg_floor_area or 0.0)
    if n_buur:
        notes.append("Vloer-perimeter = volledige buitenomtrek (%.1f m), maar de WONINGSCHEIDENDE wand(en) "
                     "tellen NIET mee in de perimeter (opname-handleiding §3.4) — corrigeer de perimeter "
                     "in Vabi voor dit woningtype (%s, %d buurwand(en))."
                     % (geo.perimeter_m or 0, woningtype, n_buur))
    schil.append(SchilDeel(id="vloer", type="vloer", subtype="Begane grondvloer",
                           begrenzing=vloer_begr, oppervlakte_m2=hoofd_area or 0.0,
                           isolatie_aanwezig=v_b["isolatie"], rekenzone=1,
                           isolatiedikte_mm=v_b["dikte_mm"],
                           perimeter_m=geo.perimeter_m,   # randverlies begane-grondvloer (= buitenomtrek)
                           rc_bron=vloer_rc,
                           opmerkingen="opp = begane-grond-footprint (benadering); verifieer in Vabi"))
    for rb, rba in sorted(vloer_split.items()):
        schil.append(SchilDeel(id="vloer-%s" % rb[:4].lower().replace(" ", ""), type="vloer",
                               subtype="Begane grondvloer (deel)", begrenzing=rb, oppervlakte_m2=rba,
                               isolatie_aanwezig=v_b["isolatie"], rekenzone=1,
                               isolatiedikte_mm=v_b["dikte_mm"], rc_bron=vloer_rc,
                               opmerkingen="vloerdeel uit ruimtenaam (%s); room-based, verifieer m²-verdeling in Vabi" % rb))
    if vloer_split:
        notes.append("Begane grond gesplitst per begrenzing op basis van ruimtenamen: %s (hoofdvloer %s = %.1f m²). "
                     "Controleer de m²-verdeling in Vabi."
                     % (", ".join("%s=%.1f m²" % (k, v) for k, v in sorted(vloer_split.items())),
                        vloer_begr, hoofd_area or 0.0))

    # dak-per-vlak: gebruik dak-velden uit de opname indien aanwezig (helling uit nok/knie/breedte
    # of direct + oriëntaties van de schuine vlakken/kopgevels + plat dak), anders footprint-fallback.
    # dak-velden komen nu uit het CONSTRUCTIES-dakblok (geconsolideerd uit Object); oude Object-velden = fallback.
    type_dak = _undot(G("Dakvlak 1 - daktype") or G("Type dak")) or "Zadeldak"
    helling = _f(G("Dakvlak 1 - hellingshoek (°)")) or _f(G("Dakvlak 1 - hellingshoek")) or _f(G("Hellingshoek dak")) or _f(G("Dak hellingshoek"))
    breedte = _f(G("Dak - vloerbreedte (m)")) or _f(G("Dak vloerbreedte"))
    if helling is None:
        helling = hellingshoek_uit_nok(breedte, _f(G("Dak - nokhoogte (m, optioneel)")) or _f(G("Dak nokhoogte")),
                                       (_f(G("Dak - knieschothoogte (m, optioneel)")) or _f(G("Dak knieschothoogte")) or 0.0))
    o1 = _undot(G("Dakvlak 1 - oriëntatie") or G("Dakvlak 1 - orientatie") or G("Dak orientatie zijde 1") or G("Dak oriëntatie zijde 1"))
    o2 = _undot(G("Dakvlak 2 - oriëntatie") or G("Dakvlak 2 - orientatie") or G("Dak orientatie zijde 2") or G("Dak oriëntatie zijde 2"))
    k1 = _undot(G("Dak - kopgevel oriëntatie 1") or G("Dak - kopgevel orientatie 1") or G("Kopgevel orientatie 1") or G("Kopgevel oriëntatie 1"))
    k2 = _undot(G("Dak - kopgevel oriëntatie 2") or G("Dak - kopgevel orientatie 2") or G("Kopgevel orientatie 2") or G("Kopgevel oriëntatie 2"))
    plat_m2 = _f(G("Plat dak m2")) or _f(G("Plat dak m²"))   # legacy; plat dak nu als dakvlak met daktype 'Plat dak'
    plat_or = _undot(G("Plat dak orientatie")) or _undot(G("Plat dak oriëntatie"))
    dak_done = False
    tl = type_dak.lower()
    dakvlakken = []
    # SOBOLT-stijl: DIRECT ingevoerde m² per dakvlak WINT van de auto-berekening (adviseur weet het beste).
    # Elk Dakvlak N (1..3) met een ingevuld oppervlak wordt 1-op-1 een dakvlak met eigen type/oriëntatie/
    # helling/begrenzing; de geometrie-benadering is alleen de fallback wanneer geen m² is ingevuld.
    directe_vlakken = []
    for n in (1, 2, 3):
        p = "Dakvlak %d" % n
        m2_d = _f(G(p + " - oppervlak (m²)")) or _f(G(p + " - oppervlak (m2)"))
        if not m2_d:
            continue
        t_d = _undot(G(p + " - daktype")) or type_dak
        o_d = _undot(G(p + " - oriëntatie") or G(p + " - orientatie"))
        h_d = _f(G(p + " - hellingshoek (°)")) or _f(G(p + " - hellingshoek")) or helling
        b_d = _bouwdeel(p, "Rc-bron dak")
        schil.append(SchilDeel(
            id="dak-vlak%d-%s" % (n, (o_d or "x").lower()), type="dak", subtype=t_d,
            begrenzing=b_d["begrenzing"] or "Buitenlucht",
            orientatie=("" if o_d == "Horizontaal" else o_d),
            oppervlakte_m2=m2_d, hellingshoek=(0 if "plat" in t_d.lower() else h_d),
            isolatie_aanwezig=b_d["isolatie"], rekenzone=1, isolatiedikte_mm=b_d["dikte_mm"],
            rc_bron=b_d["rc_bron"] or dak_rc,
            opmerkingen="dakvlak %d: m² direct ingevoerd (heeft voorrang op auto-berekening)" % n))
        directe_vlakken.append(n)
        dak_done = True
    if directe_vlakken:
        notes.append("Dak: %d dakvlak(ken) met direct ingevoerde m² (%s) — auto-berekening overgeslagen."
                     % (len(directe_vlakken), ", ".join("vlak %d" % n for n in directe_vlakken)))
    if not dak_done and helling and "zadel" in tl and (o1 or o2):
        dakvlakken = dak_vlakken_zadeldak(bg_floor_area or 0.0, breedte or 0.0, helling,
                                          orient_schuin=(o1, o2), orient_kopgevel=(k1, k2))
    elif helling and "lessenaar" in tl and o1:
        dakvlakken = dak_vlakken_lessenaar(bg_floor_area or 0.0, helling, o1)
    elif helling and ("schild" in tl or "tent" in tl) and (o1 or o2 or k1 or k2):
        dakvlakken = dak_vlakken_schilddak(bg_floor_area or 0.0, helling, (o1, o2, k1, k2))
    elif "plat" in tl:
        _pa = _f(G("Dakvlak 1 - oppervlak (m²)")) or _f(G("Dakvlak 1 - oppervlak (m2)")) or plat_m2 or (bg_floor_area or 0.0)
        if _pa:
            dakvlakken = [{"kind": "dak", "type": "plat", "orientatie": o1 or plat_or or "", "m2": _pa, "hellingshoek": 0}]
    for v in dakvlakken:
        schil.append(SchilDeel(
            id="%s-%s-%s" % (v["kind"], (v.get("type") or "")[:4], v["orientatie"] or "x"),
            type=v["kind"], subtype=v.get("type", ""), begrenzing="Buitenlucht",
            orientatie=v["orientatie"], oppervlakte_m2=v["m2"], hellingshoek=v.get("hellingshoek"),
            isolatie_aanwezig=d_b["isolatie"], rekenzone=1, isolatiedikte_mm=d_b["dikte_mm"], rc_bron=dak_rc,
            opmerkingen="dak-per-vlak uit opname (%s, helling %.0f gr)" % (type_dak, helling)))
        dak_done = True
    if dakvlakken and ("schild" in tl or "tent" in tl):
        notes.append("Schilddak: totaal schuin dakoppervlak = footprint/cos(%.0f°), gelijk verdeeld over de "
                     "opgegeven zijden — verfijn de verdeling per dakvlak in Vabi." % helling)
    if plat_m2:
        schil.append(SchilDeel(id="dak-plat", type="dak", subtype="plat", begrenzing="Buitenlucht",
                               orientatie=plat_or or "", oppervlakte_m2=plat_m2, hellingshoek=0,
                               isolatie_aanwezig=d_b["isolatie"], rekenzone=1, isolatiedikte_mm=d_b["dikte_mm"], rc_bron=dak_rc,
                               opmerkingen="plat dak (bv. erker)"))
        dak_done = True
    if not dak_done:   # type 'Anders'/complex dak: 9 m²-vakjes per oriëntatie (N..NW + Horizontaal)
        for _o in ("N", "NO", "O", "ZO", "Z", "ZW", "W", "NW", "Horizontaal"):
            _m = _f(G("Dak m² " + _o))
            if _m:
                schil.append(SchilDeel(id="dak-%s" % _o.lower()[:4], type="dak", subtype="vlak (Anders)",
                    begrenzing="Buitenlucht", orientatie=("" if _o == "Horizontaal" else _o),
                    oppervlakte_m2=_m, hellingshoek=(0 if _o == "Horizontaal" else helling),
                    isolatie_aanwezig=d_b["isolatie"], rekenzone=1, isolatiedikte_mm=d_b["dikte_mm"], rc_bron=dak_rc,
                    opmerkingen="dak-m² per oriëntatie (handmatig, type Anders)"))
                dak_done = True
    if not dak_done:
        schil.append(SchilDeel(id="dak", type="dak", subtype=type_dak, begrenzing="Buitenlucht",
                               orientatie="", oppervlakte_m2=bg_floor_area or 0.0,
                               isolatie_aanwezig=d_b["isolatie"], rekenzone=1, isolatiedikte_mm=d_b["dikte_mm"], rc_bron=dak_rc,
                               opmerkingen="HELLINGSHOEK/dakvlakken ONTBREKEN -> dak-m2 = footprint (fallback)"))
        notes.append("Dak: geen hellingshoek/dakvlakken in de opname -> footprint-fallback. Voeg dak-velden toe "
                     "(Dak vloerbreedte/nokhoogte/knieschothoogte of Hellingshoek dak + oriëntaties schuine zijden).")

    # kozijnen (ramen): erven begrenzing + oriëntatie van de moederwand (parent/child); kozijn A/B/C
    for i, k in enumerate(kozijnen):
        # Nij Begun opname-handleiding: kleine ruiten < 0,65 m2 ALTIJD rekenen als 0,65 m2
        area = k["area"] or 0.0
        klein = 0 < area < 0.65
        schil.append(SchilDeel(
            id="raam-%d" % (i + 1), type="kozijn", subtype="Raam",
            begrenzing=k.get("begr", "Buitenlucht"),
            orientatie=k["orient"], oppervlakte_m2=(0.65 if klein else area),
            glastype=_undot(k["glas"]) or "", kozijnmateriaal=_norm_kozijn_mat(k.get("kozijn_hk", "")),
            opmerkingen=(("klein raam %.2f m2 -> 0,65 m2 (Nij Begun-regel)" % area if klein else "")
                         + ("" if k["glas"] else " GLASTYPE ONTBREEKT")).strip()))
    # panelen-in-kozijn: dichte constructie (ConstructieType=1), zelfde isolatie-beslisschema als een gevel.
    # De CSV geeft geen Rc/isolatie voor het venster -> isolatie Onbekend (forfaitair via bouwjaar); de
    # adviseur verfijnt Rc/isolatie in de webapp-opname of in Vabi.
    for i, p in enumerate(panelen):
        schil.append(SchilDeel(
            id="paneel-%d" % (i + 1), type="paneel", subtype="Paneel",
            begrenzing=p.get("begr", "Buitenlucht"), orientatie=p["orient"],
            oppervlakte_m2=p["area"] or 0.0, isolatie_aanwezig=p.get("isolatie", "Onbekend"),
            isolatiedikte_mm=p.get("dikte"),
            opmerkingen=("paneel-in-kozijn (dichte constructie) -> verifieer Rc/isolatie in Vabi"
                         + (" · bouwjaarklasse afwijkend: %s (zet in Vabi)" % p["bouwjaarklasse"]
                            if p.get("bouwjaarklasse") else ""))))
    if panelen:
        notes.append("%d paneel(en)-in-kozijn herkend (Raam/paneel=paneel) -> dichte constructie; "
                     "Rc/isolatie onbekend uit de CSV, verfijn in de webapp-opname of Vabi." % len(panelen))
    # deuren: erven begrenzing + oriëntatie van de moederwand. De VABI 'deur met raam >=65%'-vlag komt
    # uit de nieuwe 'Glas >= 65% van de deur?'-vraag; legacy-opnames vallen terug op de optienaam.
    for i, d in enumerate(deuren):
        tc_l = (d["type_constructie"] or "").lower()
        # de VABI-vlag geldt ALLEEN bij >=65% glas ('Deur met 65% glas'); 'Deur met raam' is een
        # gewone deur met glas < 65% (dus geen vlag)
        met_raam = "65" in tc_l
        schil.append(SchilDeel(
            id="deur-%d" % (i + 1), type="kozijn", subtype="Deur",
            begrenzing=d.get("begr", "Buitenlucht"),
            orientatie=d["orient"], oppervlakte_m2=d["area"],
            glastype=_undot(d["glas"]) or "", kozijnmateriaal="Hout of kunststof",
            deur_met_raam_glas65=met_raam))
    dos.schil = schil

    # ---- installaties ----
    vsys = _undot(G("Ventilatiesysteem (A-E)"))      # 'A Natuurlijke ventilatie'
    # subsysteem nu conditioneel per type: 'Subsysteem (A)'..'(E)' (whichever gevuld); oude platte = fallback
    sub = (_undot(G("Subsysteem (A)")) or _undot(G("Subsysteem (B)")) or _undot(G("Subsysteem (C)"))
           or _undot(G("Subsysteem (D)")) or _undot(G("Subsysteem (E)")) or _undot(G("Subsysteem (zie type)")))
    dos.ventilatie = Ventilatie(
        systeem=(vsys.split()[0] if vsys else ""),
        systeem_soort=_undot(G("Systeem (ventilatie)")),
        subsysteem_code=(sub.split()[0] if sub else ""))
    inst = Installaties()
    # G2: probeer meerdere naamvarianten (MagicPlan-form gebruikt '-', oude form had en-dash '–')
    def G2(*namen):
        for n in namen:
            v = _undot(G(n))
            if v:
                return v
        return ""
    def _int2(s):
        try:
            return int(round(float(str(s).replace(",", ".")))) if str(s).strip() else None
        except (ValueError, TypeError):
            return None
    # --- verwarming (conditionele kern-form) ---
    opwek = G2("Verwarming - type opwekker", "Verwarming – type opwekker")
    if opwek:
        hr = G2("HR-klasse (bij gasketel)")
        wpm = G2("WP medium (bij warmtepomp)")
        inst.verwarming = Verwarming(
            type_opwekker=opwek, subtype=(hr or wpm or ""),
            afgifte=G2("Verwarming - afgifte", "Verwarming – afgifte"),
            aanvoertemperatuur=G2("Verwarming - aanvoertemperatuur", "Verwarming – aanvoertemperatuur"),
            installatiejaar=_int2(G2("Verwarming - installatiejaar", "Verwarming – installatiejaar")))
    # --- koeling ---
    if G2("Koeling aanwezig?").strip().lower() in ("ja", "yes", "true"):
        inst.koeling = Koeling(
            aanwezig=True, systeem="Individueel",
            type_opwekker=G2("Koeling - type opwekker", "Koeling – type opwekker"),
            splitsysteem=G2("Koeling - splitsysteem", "Koeling – splitsysteem"))
    # --- tapwater ---
    tw = G2("Tapwater - toestel", "Tapwater – toestel")
    if tw:
        inst.tapwater = Tapwater(type_installatie="Individueel", type_toestel=tw,
                                 installatiejaar=_int2(G2("Tapwater - installatiejaar")))
    # --- zonne-energie / PV (uitgebreid; MEERDERE PV-systemen: 'PV-2 - ...', 'PV-3 - ...' enz.) ---
    def _pv_from(detail_prefix, systeem_label):
        pt = G2(detail_prefix + "paneeltype")
        aant = _int2(G2(detail_prefix + "aantal panelen"))
        ori = G2(detail_prefix + "orientatie", detail_prefix + "oriëntatie")
        if not (pt or aant or ori):
            return None
        return ZonneEnergieSysteem(
            systeem=systeem_label or "PV-panelen", pv_type=pt,
            fabricagejaar=G2(detail_prefix + "fabricagejaar"),
            bouwintegratie=G2(detail_prefix + "bouwintegratie"),
            orientatie=ori, hellingshoek=_f(G2(detail_prefix + "hellingshoek (graden)")),
            aantal=aant, oppervlak_per_paneel_m2=_f(G2(detail_prefix + "oppervlak per paneel (m2)")))
    ze = G2("Zonne-energie aanwezig?")
    if ze and ze.strip().lower() not in ("geen", "nee", ""):
        inst.zonne_energie = [ZonneEnergieSysteem(
            systeem=ze,
            pv_type=G2("PV - paneeltype"),
            fabricagejaar=G2("PV - fabricagejaar"),
            bouwintegratie=G2("PV - bouwintegratie"),
            orientatie=G2("PV - orientatie", "PV - oriëntatie"),
            hellingshoek=_f(G2("PV - hellingshoek (graden)")),
            aantal=_int2(G2("PV - aantal panelen")),
            oppervlak_per_paneel_m2=_f(G2("PV - oppervlak per paneel (m2)")))]
        for i in range(2, 6):   # extra PV-systemen (2e paneeltype/oriëntatie); leeg = overslaan
            extra = _pv_from("PV-%d - " % i, "PV-panelen")
            if extra:
                inst.zonne_energie.append(extra)
    # --- extra (2e/3e) verwarming/tapwater/koeling: hybride / meerdere toestellen ---
    for i in range(2, 4):
        ev = G2("Verwarming %d - type opwekker" % i)
        if ev:
            inst.verwarming_extra.append(Verwarming(
                type_opwekker=ev,
                subtype=G2("Verwarming %d - HR-klasse" % i, "Verwarming %d - WP medium" % i),
                afgifte=G2("Verwarming %d - afgifte" % i),
                installatiejaar=_int2(G2("Verwarming %d - installatiejaar" % i))))
        et = G2("Tapwater %d - toestel" % i)
        if et:
            inst.tapwater_extra.append(Tapwater(
                type_installatie="Individueel", type_toestel=et,
                installatiejaar=_int2(G2("Tapwater %d - installatiejaar" % i))))
        ek = G2("Koeling %d - type opwekker" % i)
        if ek:
            inst.koeling_extra.append(Koeling(
                aanwezig=True, systeem="Individueel", type_opwekker=ek,
                splitsysteem=G2("Koeling %d - splitsysteem" % i)))
    dos.installaties = inst
    # rekenzone per installatie (Installaties-form-veld; default 1)
    def _rz(*namen):
        v = _int2(G2(*namen))
        return v if v in (1, 2, 3) else 1
    dos.ventilatie.rekenzone = _rz("Ventilatie - rekenzone", "Ventilatie – rekenzone")
    inst.verwarming.rekenzone = _rz("Verwarming - rekenzone", "Verwarming – rekenzone")
    inst.tapwater.rekenzone = _rz("Tapwater - rekenzone", "Tapwater – rekenzone")
    inst.koeling.rekenzone = _rz("Koeling - rekenzone", "Koeling – rekenzone")
    for z in inst.zonne_energie:
        z.rekenzone = _rz("Zonne-energie - rekenzone", "Zonne-energie – rekenzone")

    # ---- gaten/flags ----
    if not woningtype:
        notes.append("Woningtype ONTBREEKT -> infiltratie-positie onbekend en hart-op-hart-toeslag = 0 "
                     "(voeg 'Woningtype' toe in MagicPlan).")
    if dos.opname.qv10_waarde is not None and not dos.opname.qv10_gemeten:
        notes.append("qv10 %.2f staat ingevuld maar 'Qv10 gemeten?'=Nee (ISSO 7.1.5: alleen meenemen als "
                     "GEMETEN met blowerdoor; anders rekent VABI forfaitair op bouwjaar/renovatiejaar)." % dos.opname.qv10_waarde)
    # thermische massa: codes 0=Licht/1=Zwaar/2=Zeer zwaar zijn live in EPA bevestigd (22-6-2026) en
    # worden automatisch geschreven door objecten_generate -> geen flag/handwerk meer nodig.
    if len(inst.zonne_energie) > 1:
        notes.append("%d PV-systemen opgenomen -> alle worden doorgezet naar VABI (controleer m²/oriëntatie per systeem)."
                     % len(inst.zonne_energie))
    n_extra = len(inst.verwarming_extra) + len(inst.tapwater_extra) + len(inst.koeling_extra)
    if n_extra:
        notes.append("Extra installatie(s) opgenomen (%dx verwarming, %dx tapwater, %dx koeling): de tool zet "
                     "exemplaar 1 volledig door; voeg de extra opwekker(s) in Vabi toe (golden rule: niet gegokt)."
                     % (len(inst.verwarming_extra), len(inst.tapwater_extra), len(inst.koeling_extra)))
    vent2 = G2("Ventilatie 2 - systeem (A-E)")
    if vent2:
        notes.append("Tweede ventilatiesysteem opgenomen (%s): de tool zet ventilatiesysteem 1 door; voeg het 2e "
                     "ventilatiesysteem in Vabi toe (golden rule: niet gegokt)." % vent2)
    kwv = sorted({s.type for s in dos.schil if s.rc_bron == "Kwaliteitsverklaring"})
    if kwv:
        notes.append("Kwaliteitsverklaring geselecteerd voor: %s. De tool kiest een forfaitaire constructie en "
                     "VLAGT het; zet Invoer=Kwaliteitsverklaring + de Rc/U-waarde zelf in VABI." % ", ".join(kwv))
    zones = set(s.rekenzone for s in dos.schil) | {dos.ventilatie.rekenzone, inst.verwarming.rekenzone,
              inst.tapwater.rekenzone, inst.koeling.rekenzone} | {z.rekenzone for z in inst.zonne_energie}
    if any(z > 1 for z in zones):
        notes.append("Meerdere rekenzones in gebruik (%s). De tool draagt de zone-indeling mee per vlak én "
                     "installatie; maak de zones in VABI aan en wijs vlakken/installaties toe (multi-zone VABI-"
                     "geometrie nog niet geautomatiseerd — stuur één multi-zone VABI-export, dan wire ik het)."
                     % ", ".join("zone %d" % z for z in sorted(zones)))
    dos.validatie.issues = notes
    return dos, notes


def main():
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="MagicPlan Statistics-CSV -> dossier")
    ap.add_argument("--csv", required=True)
    ap.add_argument("--straat", default="")
    ap.add_argument("--huisnummer", default="")
    ap.add_argument("--postcode", default="")
    ap.add_argument("--plaats", default="")
    ap.add_argument("--woningtype", default="")
    ap.add_argument("--gevelhoogte", type=float, default=None)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(HERE), "out", "dossier_csv.json"))
    a = ap.parse_args()
    dos, notes = build_dossier(a.csv, a.straat, a.huisnummer, a.postcode, a.plaats,
                               a.woningtype, a.gevelhoogte)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(dos.to_dict(), open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("OK: %s" % a.out)
    gevels = [s for s in dos.schil if s.type == "gevel"]
    print("  %s %s | %d ruimtes | Ag %.0f m2 | %d gevels (%.1f m2) | %d kozijnen | bouwjaar %s" % (
        dos.identificatie.postcode, dos.identificatie.huisnummer, len(dos.geometrie.ruimtes),
        dos.geometrie.gebruiksoppervlakte_ag_m2 or 0, len(gevels),
        sum(s.oppervlakte_m2 for s in gevels), sum(1 for s in dos.schil if s.type == "kozijn"),
        dos.identificatie.bouwjaar))
    print("  ventilatie %s/%s | verwarming %s" % (dos.ventilatie.systeem, dos.ventilatie.subsysteem_code,
                                                   dos.installaties.verwarming.type_opwekker))
    if notes:
        print("\n  LET OP / nameten:")
        for n in notes:
            print("   - " + n)


if __name__ == "__main__":
    main()
