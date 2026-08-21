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
                          Koeling, Tapwater, ZonneEnergieSysteem, BouwdeelStandaard)
from core.geometry import (woningscheidende_wand_toeslag_m2, aantal_woningscheidende_wanden,
                           hellingshoek_uit_nok, dak_vlakken_zadeldak, dak_vlakken_lessenaar,
                           dak_vlakken_schilddak, dakkapel_vlakken)


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
    # BERGING/OPSLAG vóór 'verblijfsruimte': anders matcht 'Storage Room'/'Closet' op het brede
    # trefwoord 'room' en zou de tool er 0,7 dm3/s.m2 toevoer op zetten. ISSO 82.1 §6.3.1: het
    # WERKELIJK GEBRUIK is leidend — een bergzolder/opslagruimte is géén verblijfsgebied (telt wel
    # mee voor Ag als hij binnen de thermische zone valt). Gebruikt de bewoner 'm als slaap-/werkkamer,
    # geef de ruimte dan die naam.
    ("overig", ["berging", "storage", "opslag", "kast", "closet", "schuur", "meterkast",
                "zolder", "attic", "vliering", "kruipruimte", "garage"]),
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
    ("Sterk geventileerd", ("sterk geventileerd", "asgr", "asv")),   # 'asv' = tolerante alias (officieel ASGR)
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


# ÉÉN VOCABULAIRE (aannames-audit 30-7). MagicPlan, de parser en de webapp gebruikten elk hun eigen
# schrijfwijze ('AOR (onverwarmd)' vs 'AOR'; 'HR dubbel glas met coating' vs 'HR (dubbel glas met
# coating)'). Stond een waarde niet in de webapp-keuzelijst, dan toonde het <select> de EERSTE optie
# en werd de waarde bij opslaan STIL overschreven (begrenzing -> Buitenlucht, glastype -> leeg).
# Daarom normaliseren we hier, bij binnenkomst, naar de canonieke set die de webapp ook gebruikt.
_BEGR_CANON = {
    "buitenlucht": "Buitenlucht", "buiten": "Buitenlucht", "grond": "Grond",
    "kruipruimte": "Kruipruimte", "kruip": "Kruipruimte", "water": "Water",
    "aor": "AOR", "aos": "AOS", "avr": "AVR",
    "asgr": "Sterk geventileerd", "asv": "Sterk geventileerd",
    "sterk geventileerd": "Sterk geventileerd", "sterk geventileerde ruimte": "Sterk geventileerd",
    "onverwarmde kelder": "Onverwarmde kelder", "kelder": "Onverwarmde kelder",
}


def _norm_begrenzing(v):
    """Elke schrijfwijze -> de canonieke begrenzing van de webapp/VABI-mapping. Leeg blijft leeg."""
    s = _undot(v or "").strip()
    if not s:
        return ""
    k = s.lower()
    return _BEGR_CANON.get(k) or _BEGR_CANON.get(k.split(" (")[0].strip()) or s


_GLAS_CANON = {
    "enkel": "Enkel", "voorzetglas": "Voorzetglas", "voorzetraam": "Voorzetglas",
    "dubbel": "Dubbel", "hr": "HR (dubbel glas met coating)",
    "hr dubbel glas met coating": "HR (dubbel glas met coating)",
    "hr (dubbel glas met coating)": "HR (dubbel glas met coating)",
    "hr+": "HR+", "hr++": "HR++", "triplehr": "TripleHR", "triple hr": "TripleHR",
    "vacuümglas": "Vacuümglas", "vacuumglas": "Vacuümglas", "onbekend": "Onbekend",
}


def _norm_glaslabel(v):
    """CSV-glaswaarde -> de canonieke glaskeuze van de webapp. Onbekende waarde blijft ongemoeid
    (dan ziet de adviseur 'm staan i.p.v. dat hij stil verdwijnt)."""
    s = _undot(v or "").strip()
    return _GLAS_CANON.get(s.lower(), s)


def _norm_kozijn_mat(v):
    """Kozijntype A/B/C (officieel formulier) -> kozijnmateriaal. A=hout/kunststof, B=metaal therm.
    onderbroken, C=metaal niet-onderbroken. Default Hout of kunststof."""
    s = _undot(v).strip().lower()
    # '?afwijkend' = de opname zegt 'ja, ander materiaal dan hout/kunststof' maar het formulier vraagt
    # niet WELK. Niet stil op hout/kunststof zetten (dat is juist het gunstigste type A) -> leeg laten
    # zodat de generator/adviseur het in Vabi moet invullen; de parser meldt het luid.
    if s == "?afwijkend":
        return ""
    if not s:
        return "Hout of kunststof"
    if s[0] in _KOZIJN_MAT and (len(s) == 1 or not s[1].isalpha()):
        return _KOZIJN_MAT[s[0]]
    if "thermisch onderbroken" in s and "niet" not in s:   # F5: 'niet thermisch onderbroken' uitsluiten
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
    # 1-OP-1-GARANTIE (audit 13-7): veldnamen kregen live al 2x een ander "(...)"-suffix, waardoor
    # exacte lookups een INGEVULD antwoord stil kwijtraakten (verzwolgen invoer). Daarom: eerst
    # exact, anders match op de veldnaam ZONDER het "(...)"-suffix — maar alleen als die basisnaam
    # ondubbelzinnig is (1 kandidaat). Nooit raden bij meerdere kandidaten.
    _basis = lambda k: " ".join(str(k).split(" (")[0].lower().split())
    _basis_map = {}
    for _pk in plan:
        _basis_map.setdefault(_basis(_pk), []).append(_pk)

    def G(k):
        v = plan.get(k, "")
        if v != "":
            return v
        _kand = _basis_map.get(_basis(k), [])
        return plan.get(_kand[0], "") if len(_kand) == 1 else ""
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
        thermische_massa_wanden=_undot(G("Gevel - thermische massa") or G("Thermische massa wanden")),
        thermische_massa_vloeren=_undot(G("Vloer - thermische massa") or G("Thermische massa vloeren")),
        # huidige woningstaat (isolatieplan sectie 3 V1/V3/V4/V6) die NIET uit de geometrie volgt
        gevel_isolatie_zijde=_undot(G("Gevel - isolatie aan zijde")),
        dak_isolatie_zijde=_undot(G("Dak - isolatie aan zijde")),
        bodemisolatie=_undot(G("Bodemisolatie kruipruimte")),
        kierdichting=_undot(G("Kierdichting")))

    # ---- geometrie: ruimtes (Ag) + verdiepingen ----
    geo = Geometrie()
    room_rows = sec.get("ROOM ATTRIBUTES", [])
    _room_kop = room_rows[0] if room_rows else []   # kolomkoppen voor de per-kamer element-fields
    floor_names = set()
    for r in sec.get("FLOOR ATTRIBUTES", [])[1:]:
        if r and r[0].strip():
            floor_names.add(r[0].strip())
    vloer_split = {}   # begrenzing -> m2: begane-grondvloerdelen met afwijkende begrenzing (uit ruimtenaam)
    kamer_verdieping = {}   # kamernaam -> verdiepingnaam (voor de zolder/dak-overlap-check)
    _kamers_per_verd = {}   # verdieping -> [(kamernaam, m2)] (dubbele-kamer-check hieronder)
    _cur_verd = ""
    for r in room_rows[1:]:
        if not r:
            continue
        naam = (r[0] or "").strip()
        if naam in floor_names:
            _cur_verd = naam
            continue
        if not naam:
            continue
        kamer_verdieping[naam] = _cur_verd
        ag = _f(r[1]) if len(r) > 1 else None
        if ag is None:
            continue
        _kamers_per_verd.setdefault(_cur_verd, []).append((naam, ag))
        # PER-KAMER element-fields (override op de Constructies-vloerstandaard). Kolom op KOP zoeken
        # (positie-onafhankelijk); leeg -> ruimtenaam-token, anders de projectstandaard.
        def _rv(*frags):
            for frag in frags:
                for k2, h in enumerate(_room_kop):
                    if frag in (h or "").strip().lower() and len(r) > k2 and (r[k2] or "").strip():
                        return _undot((r[k2] or "").strip())
            return ""
        _telt_mee = _rv("telt mee voor gebruiksoppervlakte")
        if _telt_mee and _telt_mee.strip().lower() in ("nee", "no", "false"):
            # buiten de thermische zone (NTA 8800 §6.3) -> niet in Ag en geen vloerdeel
            notes.append("Ruimte '%s' telt NIET mee voor het gebruiksoppervlak (veld 'Vloer - telt mee "
                         "voor gebruiksoppervlakte?' = Nee) -> buiten de thermische zone gelaten." % naam)
            continue
        _rz_room = _rv("vloer - rekenzone")
        geo.ruimtes.append(Ruimte(naam=naam, functie=_functie_uit_naam(naam), oppervlakte_m2=ag,
                                  rekenzone=(int(_rz_room) if _rz_room.strip().isdigit() else 1)))
        rb = _norm_begrenzing(_rv("vloer - begrenzing")) or _begrenzing_uit_naam(naam)
        if rb not in ("Buitenlucht", "AVR"):   # veld-override of ruimtenaam-token -> apart vloerdeel
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
    # DUBBELE KAMERS (Essenhage 30-7): staat een kamer per ongeluk meerdere keren in het plan (kopiëren/
    # dubbel tekenen), dan telt MagicPlan die kamer-m2 én zijn wanden meerdere keren mee -> te grote
    # gevel én te grote Ag. Zichtbaar doordat de SOM van de kamers groter is dan het vloeroppervlak van
    # die verdieping. Niet stil corrigeren (we weten niet wélke de echte is): luid melden mét de
    # verdachte kamers, zodat je ze in MagicPlan kunt verwijderen.
    for _vnaam, _kamers in _kamers_per_verd.items():
        _vlak = floor_footprint.get(_vnaam)
        if not _vlak or not _kamers:
            continue
        _som = round(sum(a for _, a in _kamers), 2)
        if _som - _vlak <= max(0.5, 0.02 * _vlak):        # kleine meetruis is normaal
            continue
        _tel = {}
        for _n, _a in _kamers:
            _tel.setdefault((_n, round(_a, 2)), []).append(_a)
        _verdacht = ["%s %.2f m2 (%dx)" % (_n, _a, len(v)) for (_n, _a), v in _tel.items() if len(v) > 1]
        notes.append(
            "FOUT — DUBBELE KAMER(S) op '%s': de kamers tellen samen op tot %.2f m2, maar de verdieping "
            "is %.2f m2 (%.2f m2 te veel). %s Een kamer die dubbel in het plan staat telt ook zijn "
            "WANDEN dubbel mee in de gevel én in het gebruiksoppervlak. Verwijder de dubbele kamer(s) "
            "in MagicPlan en exporteer opnieuw."
            % (_vnaam, _som, _vlak, _som - _vlak,
               ("Verdacht (zelfde naam én oppervlak): " + " · ".join(_verdacht) + ".")
               if _verdacht else "Controleer welke kamer dubbel staat."))
    if dos.opname.gevelhoogte_m is None and floor_hoogtes:
        dos.opname.gevelhoogte_m = round(sum(floor_hoogtes), 2)  # som verdiepingshoogtes ~ gevelhoogte
    # GEBOUWHOOGTE (tot de nok) ≠ gevelhoogte (tot de goot). UITSLUITEND handmatige invoer via het
    # MagicPlan-veld (eis Renze 12-7: geen berekende fallback — dit is opname-invoer). Ontbreekt het
    # veld -> geen waarde + LUIDE note; de generator schrijft dan 0 (nooit een sjabloonwaarde).
    gbh = (_f(G("Gebouwhoogte (m)")) or _f(G("Gebouwhoogte tot de nok (m)"))
           or _f(G("Gebouwhoogte (m, leeg = gevelhoogte + nokhoogte)")))
    if gbh:
        dos.opname.gebouwhoogte_m = gbh
    else:
        notes.append("GEBOUWHOOGTE ONTBREEKT: vul het veld 'Gebouwhoogte tot de nok (m)' in het "
                     "MagicPlan-Object-form in (handmatige invoer). In Vabi komt nu 0 te staan.")
    # PER-VERDIEPING Ag: de gemeten MagicPlan-vloeroppervlakken ("Ground surface without walls"
    # per verdieping) zijn DE meting -> VABI Verdiepingen krijgt die echte waarden per bouwlaag,
    # en Ag = de som daarvan (eis Renze 12-7: de gemeten 122,06 is juist, niet MagicPlans
    # "woonoppervlak"-heuristiek 87,13 die op kamertype filtert). De Ag-aftrek-zolder (handmatig
    # gemeten strook <1,5 m) gaat van de BOVENSTE verdieping af, zodat som == Ag blijft.
    for fnaam, fopp in floor_footprint.items():
        vi = next((v for v in geo.vloeren if v.naam == fnaam), None)
        if vi is not None:
            vi.oppervlakte_m2 = fopp
        else:
            geo.vloeren.append(VloerInfo(naam=fnaam, oppervlakte_m2=fopp))
    _gemeten = [v for v in geo.vloeren if (v.oppervlakte_m2 or 0) > 0]
    if _gemeten:
        if ag_aftrek:
            bovenste = _gemeten[-1]        # CSV-volgorde: Ground -> 1st -> 2nd (zolder = laatste)
            bovenste.oppervlakte_m2 = round(max(0.0, bovenste.oppervlakte_m2 - ag_aftrek), 2)
            notes.append("Verdieping '%s': %.2f m² afgetrokken (opgegeven zolderstrook <1,5 m)."
                         % (bovenste.naam, ag_aftrek))
        _vsom = round(sum(v.oppervlakte_m2 for v in _gemeten), 2)
        _mp_woon = geo.gebruiksoppervlakte_ag_m2
        geo.gebruiksoppervlakte_ag_m2 = _vsom      # Ag = som van de gemeten verdiepingen
        if _mp_woon and abs(_vsom - _mp_woon) > 0.02 * _vsom:
            notes.append("Ag = %.2f m² (som gemeten verdiepingen). MagicPlans eigen 'woonoppervlak' "
                         "was %.2f m² (kamertype-heuristiek, niet gebruikt) — check bij groot "
                         "verschil of alle ruimtes in de rekenzone horen." % (_vsom, _mp_woon))
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
    def _colv(r, *frags):
        """Waarde uit DEZE rij op kolomKOP-fragment (element-override). Eerste NIET-lege match wint;
        '' als de kolom ontbreekt of leeg is. Positie-onafhankelijk (kolommen kunnen schuiven)."""
        for frag in frags:
            for k, h in enumerate(_kop):
                if frag in (h or "").strip().lower() and len(r) > k and (r[k] or "").strip():
                    return _undot((r[k] or "").strip())
        return ""

    def _wand_override(r):
        """PER-WAND element-fields = override op de Constructies-standaard (drielaagse overerving:
        project-form = standaard, element-veld = afwijking op DIT vlak). None = niets ingevuld ->
        de projectstandaard blijft gelden. Zelfde vorm als _bouwdeel() zodat ze inwisselbaar zijn."""
        iso = _colv(r, "gevel - isolatie aanwezig")
        dikte_onb = _colv(r, "gevel - isolatiedikte onbekend").lower() in ("ja", "yes", "true")
        dikte = _f(_colv(r, "gevel - isolatiedikte (mm)"))
        bouwjaar = _colv(r, "gevel - bouwjaar (onbekend)", "gevel - bouwjaar")
        spouw_s = _colv(r, "gevel - spouw aanwezig")
        invoer = _colv(r, "gevel - invoer")
        if not (iso or dikte or bouwjaar or spouw_s or invoer or dikte_onb):
            return None
        rcl = invoer.lower()
        if "verklaring" in rcl:
            rc = "Kwaliteitsverklaring"
        elif dikte and not dikte_onb:
            rc = "Opgemeten dikte"
        elif dikte_onb or bouwjaar or "onbek" in iso.lower():
            rc = "Dikte onbekend"
        else:
            rc = ""
        # 'Onbekend' -> None (niet False): False = geverifieerd géén spouw (audit F4 15-7)
        spouw = (None if (not spouw_s or "onbek" in spouw_s.lower())
                 else (spouw_s.lower() in ("ja", "yes", "true")))
        return {"isolatie": {"ja": "Ja", "nee": "Nee", "onbekend": "Onbekend"}.get(iso.lower(), iso) or "",
                "dikte_mm": (dikte if not dikte_onb else None), "spouw": spouw,
                "bouwjaar": bouwjaar, "rc_bron": rc}

    gevel_per = {}      # (orientatie, begrenzing) -> m2 (binnenwerks, zonder openingen)
    gevel_bruto = {}    # idem mét openingen (voor volledigheidscheck + fallback)
    # GEVEL = BREEDTE x VERDIEPINGSHOOGTE per bouwlaag (methode Renze 14-7, NTA8800-getrouw):
    # bv. achtergevel 5,81 m -> BG 5,81x2,60 + 1e 5,81x2,38 = 28,92 m2 BRUTO (ramen/deuren gaan
    # er in Vabi als deelvlak af). De kamer-wandsom telde borstweringen als 0,46 m-strookjes.
    gevel_bxh = {}            # key -> {verdiepingnaam: som getikte wandbreedtes}
    gevel_bxh_onvolledig = set()   # keys waar een breedte ontbreekt -> fallback wandsom
    cur_verdieping = ""
    orient_naam = {}    # orientatie -> gevel-naam (voor/achter/links/rechts) voor leesbaar label
    kozijnen = []
    panelen = []          # dichte panelen-in-kozijn (Raam/paneel = paneel): dichte constructie i.p.v. glas
    deuren = []
    roosters_tel = 0      # kozijnen/deuren met toevoerrooster -> inventaris voor het ventilatieplan
    cur_orient = ""           # oriëntatie van de huidige (moeder)wand
    cur_begr = "Buitenlucht"  # begrenzing van de moederwand (parent; ramen/deuren erven die)
    # F2 (15-7): de Constructies-form biedt per bouwdeel een 'Gevel - begrenzing'-standaard. Die werd
    # gelezen maar nooit toegepast (alleen wandnaam-tokens werkten). Nu = fallback als een wand geen
    # eigen begrenzing-token heeft (een expliciet token op de wand wint nog steeds).
    _gevel_begr_default = _norm_begrenzing(G("Gevel - begrenzing"))
    n_wall_ext = 0
    nareken_namen = []        # wanden die de adviseur markeerde om handmatig in Vabi na te rekenen
    gevel_tikken = []         # per getikte buitenwand: kamer/wand/orient/breedte (tikfout-checks)
    _kamer_instantie = 0       # elke NIEUWE kamer-blok = uniek nummer (namen als 'Bedroom' herhalen)
    _vorige_kamer = None
    for r in wall_rows[1:]:
        _c0w = (r[0] or "").strip() if r else ""
        # verdieping-scheidingsrij in de WALL-sectie ('Ground Floor'/'1st Floor'/...) -> tracken
        if _c0w in floor_names and (len(r) <= 8 or not (r[8] or "").strip()):
            cur_verdieping = _c0w
        if len(r) < 12 or not _c0w:
            continue
        # nieuw kamer-blok = naam verandert OF de wandnummering reset naar 'Wall 0' (MagicPlan begint
        # elke kamer met Wall 0; vangt ook twee opeenvolgende kamers met dezelfde naam, bv. 2x 'Bedroom')
        _wandnaam0 = (r[1] or "").strip().lower() if len(r) > 1 else ""
        if _c0w != _vorige_kamer or _wandnaam0 in ("wall 0", "wall0"):
            _kamer_instantie += 1
            _vorige_kamer = _c0w
        typ = (r[8] or "").strip() if len(r) > 8 else ""
        if typ == "Wall":
            # ECHTE EXPORT (Essenhage 8-7): kolom 0 = KAMERnaam, kolom 1 = WANDnaam ('Wall 0' of door
            # de adviseur hernoemd naar 'Voorgevel' etc.). Tokens zoeken we in wand- én kamernaam.
            _wnaam = "%s %s" % ((r[1] or "") if len(r) > 1 else "", r[0] or "")
            # TIKBAAR 'Gevelnaam'-veld (8-7, geen typen meer): kolomwaarde bij de naam voegen zodat
            # de bestaande token-logica (voor/achter/links/rechts + Buurwand AVR) 'm oppakt.
            _ign = next((i for i, h in enumerate(_kop) if "gevelnaam" in (h or "").lower()), None)
            if _ign is not None and len(r) > _ign and (r[_ign] or "").strip():
                _wnaam += " " + _undot(r[_ign])
            cur_gevel_naam = _gevel_naam_uit_naam(_wnaam)
            # oriëntatie: de override-KOLOM op naam zoeken (positie schuift per export); anders
            # kompastoken in de naam; anders afleiden uit gevelnaam + voorgevel-oriëntatie.
            _io = next((i for i, h in enumerate(_kop) if "oriëntatie (override)" in (h or "").lower()
                        or "orientatie (override)" in (h or "").lower()), None)
            col_orient = ((r[_io] or "").strip() if (_io is not None and len(r) > _io) else "")
            if not col_orient and _io is None and len(r) > 11:
                _c11 = (r[11] or "").strip()          # LEGACY-export: kolom 11 was de oriëntatie
                col_orient = _c11 if _norm_kompas(_c11) else ""
            cur_orient = (_undot(col_orient) or _orient_uit_naam(_wnaam)
                          or _orient_afleiden(cur_gevel_naam, orientatie_voorgevel))
            # PER-WAND OVERRIDE (element-fields) — wint van naam-token én van de projectstandaard.
            _wov = _wand_override(r)
            _ov_begr = _norm_begrenzing(_colv(r, "gevel - begrenzing"))
            _wtok = _begrenzing_uit_naam(_wnaam)   # 'Buitenlucht' = géén expliciet token op de wand
            cur_begr = (_ov_begr or                                    # 1) veld op de wand
                        (_wtok if (_wtok and _wtok != "Buitenlucht")   # 2) token in de naam
                         else (_gevel_begr_default or "Buitenlucht")))  # 3) Constructies-standaard
            cur_isol = ((_wov or {}).get("isolatie") or _isolatie_uit_naam(_wnaam))
            _chk = ((r[_idx_nareken] or "").strip().lower()
                    if (_idx_nareken is not None and len(r) > _idx_nareken) else "")
            cur_nareken = (_narekenen_uit_naam(_wnaam)          # naam-token (blijft werken) ...
                           or _chk in ("yes", "ja", "true", "1", "aan"))  # ... of het VINKJE op de wand
            # "Grenst aan buiten (m)"-veld (metertje-idee): bij een narekenen-wand met ingevulde
            # buitenlengte splitst de tool ZELF: buitendeel = meters x wandhoogte telt als gevel,
            # de rest valt buiten de schil (binnen/AVR) -> geen handmatig naberekenen meer nodig.
            _ibm = next((i for i, h in enumerate(_kop) if "grenst aan buiten (m)" in (h or "").lower()), None)
            _bm = _f(r[_ibm]) if (_ibm is not None and len(r) > _ibm) else None
            _ih = next((i for i, h in enumerate(_kop) if (h or "").strip().lower().startswith("height")), 6)
            _wh = _f(r[_ih]) if len(r) > _ih else None
            _ov_rz = _colv(r, "gevel - rekenzone")
            cur_rz = (int(_ov_rz) if _ov_rz.strip().isdigit()          # veld op de wand wint ...
                      else _rekenzone_uit_naam(_wnaam))                 # ... anders het naam-token
            # signatuur van de per-wand override -> onderdeel van de groeperingssleutel, zodat een wand
            # met afwijkende isolatie/dikte/spouw/bron een EIGEN schildeel wordt (niet samengevoegd).
            _ovsig = ((_wov["dikte_mm"], _wov["spouw"], _wov["bouwjaar"], _wov["rc_bron"]) if _wov else None)
            if cur_begr == "AVR":      # buurwoning/woningscheidend -> NIET in de schil (ISSO p.66/75)
                cur_orient = ""        # ramen/deuren in deze wand vallen ook weg
                continue
            # DEELS-BUITEN ZONDER GEVEL-AANDUIDING (Essenhage-Hall-les 15-7): een wand met een
            # buitenlengte of deels-buiten-vinkje maar ZONDER voor/achter/links/rechts-tag heeft geen
            # oriëntatie -> zou stil uit de schil vallen. Nooit stil weglaten (geen aannames) -> LUIDE flag.
            if not cur_orient and (_bm or cur_nareken):
                notes.append("LET OP wand '%s'%s: gemarkeerd als deels-buiten%s, maar ZONDER "
                             "gevel-aanduiding (voor/achter/links/rechts) -> deze wand is NIET meegeteld in "
                             "de schil. Geef hem een gevel-tag, anders mist dit geveloppervlak."
                             % (_wnaam.strip(), (" (%s)" % cur_verdieping) if cur_verdieping else "",
                                (" met buitenlengte %.2f m" % _bm) if _bm else ""))
            if cur_orient:  # oriëntatie bekend (ingevuld of afgeleid) = buitengevel (telt mee)
                n_wall_ext += 1
                k = (cur_orient, cur_begr, cur_isol or "", cur_nareken, cur_rz, _ovsig)
                _bijdrage = _f(r[4]) or 0.0
                _w_breed = _f(r[5]) if len(r) > 5 else None    # effectieve gevelbreedte van dit segment
                # buitenlengte ingevuld -> ALTIJD splitsen (ook zonder het deels-buiten-vinkje): de
                # ingevoerde meters zijn de bewuste "dit deel grenst aan buiten"-uitspraak (eis Renze 15-7).
                if _bm and _wh:
                    _buiten_m2 = round(min(_bm * _wh, _bijdrage or (_bm * _wh)), 2)
                    notes.append("Wand '%s': gesplitst via 'Grenst aan buiten (m)' = %.2f m x %.2f m hoogte "
                                 "-> %.2f m2 opgeteld bij de gevel op orientatie %s%s (rest binnen/AVR, "
                                 "niet in de schil)."
                                 % (_wnaam.strip(), _bm, _wh, _buiten_m2, cur_orient or "onbekend",
                                    (" / %s" % cur_gevel_naam) if cur_gevel_naam else ""))
                    _bijdrage = _buiten_m2
                    _w_breed = _bm
                    k = (cur_orient, cur_begr, cur_isol or "", False, cur_rz, _ovsig)   # geen nareken-flag meer nodig
                    cur_nareken = False   # split via 'Grenst aan buiten (m)' heeft het OPGELOST ->
                    # geen "HANDMATIG NAREKENEN"-melding meer (regel ~521); dit was de tegenstrijdigheid
                elif cur_nareken:
                    # deels-buiten GEMARKEERD maar geen meters ingevuld -> FOUT (eis Renze 15-7): de hele
                    # wand telt nu mee (waarschijnlijk te veel). Vul de buitenlengte in.
                    notes.append("FOUT wand '%s'%s: gemarkeerd als deels-buiten, maar het veld 'Grenst aan "
                                 "buiten (m)' is LEEG -> vul het aantal meters in dat aan buiten grenst. Zolang "
                                 "het leeg is telt de HELE wand mee (%.2f m2), wat waarschijnlijk te veel is."
                                 % (_wnaam.strip(), (" (%s)" % cur_verdieping) if cur_verdieping else "",
                                    _bijdrage))
                gevel_per[k] = round(gevel_per.get(k, 0.0) + _bijdrage, 2)
                gevel_bruto[k] = round(gevel_bruto.get(k, 0.0) + (_f(r[3]) or 0.0), 2)
                # tik-administratie: gevel_bxh (breedte x verdiepingshoogte) wordt NA de wand-loop
                # uit deze tikken gebouwd, mét dedup van tegenoverliggende gelijke-breedte wanden.
                _wnr_m = re.search(r"wall\s*(\d+)", ((r[1] or "").strip().lower() if len(r) > 1 else ""))
                gevel_tikken.append({"kamer": (r[0] or "").strip(), "kamer_id": _kamer_instantie,
                                     "verdieping": cur_verdieping, "gevel_key": k,
                                     "wand": (r[1] or "").strip() if len(r) > 1 else "",
                                     "wandnr": int(_wnr_m.group(1)) if _wnr_m else None,
                                     "orient": cur_orient, "breedte": _f(r[5]) if len(r) > 5 else None,
                                     "breedte_eff": _w_breed, "m2": _f(r[3]) or 0.0})
                if cur_gevel_naam and cur_orient not in orient_naam:
                    orient_naam[cur_orient] = cur_gevel_naam
                if cur_nareken:
                    nareken_namen.append(("%s (%s)" % (r[1] or "wand", r[0] or "")).strip())
        elif typ == "Window":
            def _wn(frag, exact=False):
                """Waarde uit de raamrij op kolomKOP. exact=True: eerst een KALE kop die exact gelijk is
                ('Type glas'), pas daarna de vorm mét haakjes.

                Waarom: de export bevat zowel 'Type glas' (raam) als 'Type glas (indien glas in deur)'.
                Beide worden 'type glas' zodra je alles vóór ' (' afknipt, en dan won de DEUR-kolom —
                die bij een raam leeg is, waardoor het glastype overal leeg bleef (Essenhage 27-7).
                Daarom: exacte kop wint, en anders de eerste kandidaat mét een waarde."""
                kand = []
                for k, h in enumerate(_kop):
                    hl = (h or "").strip().lower()
                    if not hl:
                        continue
                    if exact:
                        if hl == frag:
                            kand.insert(0, k)                 # exacte kop: hoogste prioriteit
                        elif hl.split(" (")[0] == frag:
                            kand.append(k)
                    elif frag in hl:
                        kand.append(k)
                for k in kand:                                 # eerste kandidaat mét inhoud
                    if len(r) > k and (r[k] or "").strip():
                        return (r[k] or "").strip()
                return ((r[kand[0]] or "").strip() if (kand and len(r) > kand[0]) else None)
            orient = _undot(_wn("oriëntatie (override)") or "")
            if not orient and len(r) > 17 and _norm_kompas((r[17] or "").strip()):
                orient = (r[17] or "").strip()        # LEGACY-export: kolom 17 was raam-oriëntatie
            orient = orient or cur_orient
            if not orient:   # binnenraam / niet-buitengevel -> niet in thermische schil
                continue
            _rp = ((r[_idx_raampaneel] or "").strip().lower()
                   if (_idx_raampaneel is not None and len(r) > _idx_raampaneel) else "")
            # KOZIJNMATERIAAL (aannames-audit 30-7): het live veld heet 'Kozijnmateriaal afwijkend
            # (anders dan hout/kunststof)?' en is een JA/NEE-poort — er is GEEN vervolgveld dat vraagt
            # wélk materiaal. De oude lookup matchte die kop niet en viel terug op kolom 15, en dat is
            # in de huidige export 'Type glas' -> het glastype belandde in het kozijnmateriaal en werd
            # daarna stil op de default 'Hout of kunststof' gezet. Nu expliciet: Nee/leeg = hout/
            # kunststof (NTA kozijntype A); Ja = onbekend welk metaal -> LUIDE flag, want type B (Ufr
            # 3,8) en C (Ufr 7,0) schelen enorm in de Uw (NTA 8800 tabel 8.3).
            _hk_afw = _undot(_wn("kozijnmateriaal afwijkend") or "")
            # op NAAM: 'Kozijnmateriaal' (nieuw) of 'Kozijn' (legacy-export met kozijntype A/B/C).
            # Bewust GEEN positionele fallback meer: kolom 15 is in de huidige export 'Type glas'.
            _hk = (_wn("kozijnmateriaal", exact=True) or _wn("kozijn", exact=True) or "")
            if not _hk and _hk_afw.strip().lower().startswith("ja"):
                _hk = "?afwijkend"
            # BOVEN-/ONDERLICHT (na 1e echte opname): een apart vlak in hetzelfde kozijn met ander
            # glas (bv. enkel glas boven) of een dicht paneel (borstwering onder). Zelfde patroon als
            # het deur-bovenlicht ('Ja, met eigen glas' / 'Ja, met dicht paneel' + per tak eigen
            # velden). Veldnamen bevatten 'kozijn' zodat ze nooit botsen met de DEUR-kolommen
            # ('Bovenlicht - oppervlak glas'). Zonder oppervlak wordt er NIETS gesplitst — luide flag.
            _tot = _f(r[3]) or 0.0
            _sub_af = 0.0
            for _pref in ("bovenlicht", "onderlicht"):
                _aanw = (_wn(_pref + " in het kozijn") or "").strip().lower()
                _gopp = _f(_wn(_pref + " kozijn - oppervlak glas", exact=True))
                _popp = _f(_wn(_pref + " kozijn-paneel - oppervlak", exact=True))
                if _gopp:
                    kozijnen.append({"area": _gopp,
                                     "glas": _undot(_wn(_pref + " kozijn - type glas", exact=True) or ""),
                                     "orient": orient, "begr": cur_begr, "kozijn_hk": _hk})
                    _sub_af += _gopp
                elif _popp:
                    panelen.append({"area": _popp, "orient": orient, "begr": cur_begr,
                                    "isolatie": _undot(_wn(_pref + " kozijn-paneel - isolatie aanwezig")
                                                       or "") or "Onbekend",
                                    "dikte": _f(_wn(_pref + " kozijn-paneel - isolatiedikte")),
                                    "bouwjaarklasse": _wn(_pref + " kozijn-paneel - bouwjaarklasse") or ""})
                    _sub_af += _popp
                elif _aanw.startswith("ja"):
                    notes.append("raam '%s' (%s): %s aanwezig maar OPPERVLAK ontbreekt -> niet "
                                 "gesplitst; splits het kozijn zelf in Vabi."
                                 % ((r[0] or "?").strip(), orient, _pref))
                # ook een boven-/onderlicht kan een toevoerrooster hebben (los van het hoofdraam)
                if _aanw.startswith("ja") \
                        and (_wn(_pref + " kozijn - toevoerrooster") or "").strip().lower().startswith("ja"):
                    roosters_tel += 1
            if _sub_af:
                if _tot and _sub_af >= _tot:
                    notes.append("raam '%s' (%s): boven-/onderlicht (%.2f m2) >= het hele element "
                                 "(%.2f m2) -> hoofddeel op 0; controleer de m2 in Vabi."
                                 % ((r[0] or "?").strip(), orient, _sub_af, _tot))
                _tot = max(_tot - _sub_af, 0.0)
            if (_wn("toevoerrooster aanwezig") or "").strip().lower().startswith("ja"):
                roosters_tel += 1
            if "paneel" in _rp:          # dicht paneel-in-kozijn -> dichte constructie (geen glas)
                def _bn(frag):
                    i = next((k for k, h in enumerate(_kop) if frag in (h or "").lower()), None)
                    return ((r[i] or "").strip() if (i is not None and len(r) > i) else "")
                panelen.append({"area": _tot, "orient": orient, "begr": cur_begr,
                                "isolatie": _undot(_bn("paneel - isolatie aanwezig")) or "Onbekend",
                                "dikte": _f(_bn("paneel - isolatiedikte")),
                                "bouwjaarklasse": _bn("paneel - bouwjaarklasse")})
            elif _tot > 0:
                _g = _wn("type glas", exact=True)      # 'Type glas' (raam) — niet '(indien glas in deur)'
                kozijnen.append({"area": _tot,
                                 "glas": (_g if _g is not None else ((r[16] or "").strip() if len(r) > 16 else "")),
                                 "orient": orient, "begr": cur_begr, "kozijn_hk": _hk,
                                 # NTA 8800 §8.2.2.3.4: bedienbaar luik/rolluik verlaagt de effectieve Uw
                                 "zonwering": _undot(_wn("zonwering/luik aanwezig") or "")})
        elif typ == "Door":
            # LEGACY-fallback op kolom 17 alleen als het ECHT een kompaswaarde is: in de huidige export
            # staat op 17 'Toevoerrooster type' — zonder deze guard werd 'Zelfregelend (ZR)' de
            # oriëntatie van de deur (aannames-audit 30-7).
            _o17 = (r[17] or "").strip() if len(r) > 17 else ""
            orient = (_o17 if _norm_kompas(_o17) else "") or cur_orient
            # deur-kolommen op NAAM (Deur-groep is 8-7 geherstructureerd: glas-velden conditioneel
            # onder 'Type constructie (deur)' + nieuwe 'Glas >= 65%'-vraag) — positioneel als fallback
            def _kol(frag, fb):
                return next((i for i, h in enumerate(_kop) if frag in (h or "").lower()), fb)

            def _byname(frag):
                """Eerste kolom met die naam ÉN een waarde. De export bevat DUBBELE kolomnamen (de
                raam- en de deur-variant van hetzelfde veld, bv. 'Kozijnmateriaal afwijkend ...' op
                index 13 én 16). Pakken we blind de eerste, dan lezen we de lege raam-kolom op een
                deurrij — dezelfde fout als bij het glastype (aannames-audit 30-7)."""
                treffers = [i for i, h in enumerate(_kop) if frag in (h or "").lower()]
                for i in treffers:
                    if len(r) > i and (r[i] or "").strip():
                        return (r[i] or "").strip()
                i = treffers[0] if treffers else None
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
            _deur_area = _f(r[3]) or 0.0
            _blg = _f(_byname("bovenlicht - oppervlak glas"))
            _blgt = _undot(_byname("bovenlicht deur - type glas") or "")
            if _blg and _blgt:
                # eigen glastype opgegeven (vaak enkel glas boven een deur met beter glas) -> het
                # bovenlicht wordt een APART kozijn en gaat dan ook van het deurvlak AF (anders dubbel)
                kozijnen.append({"area": _blg, "glas": _blgt, "orient": orient,
                                 "begr": cur_begr, "kozijn_hk": ""})
                _deur_area = max(_deur_area - _blg, 0.0)
            elif _blg:                   # legacy: glas-bovenlicht telt mee als glas-in-deur
                opp = (opp or 0.0) + _blg
            _blp = _f(_byname("bovenlicht-paneel - oppervlak"))
            if _blp:                     # paneel-bovenlicht = dichte paneel-constructie boven de deur
                panelen.append({"area": _blp, "orient": orient, "begr": cur_begr,
                                "isolatie": _undot(_byname("bovenlicht-paneel - isolatie aanwezig") or "") or "Onbekend",
                                "dikte": _f(_byname("bovenlicht-paneel - isolatiedikte")),
                                "bouwjaarklasse": _byname("bovenlicht-paneel - bouwjaarklasse") or ""})
            if (_byname("toevoerrooster deur") or "").strip().lower().startswith("ja"):
                roosters_tel += 1
            deuren.append({"area": _deur_area, "type_constructie": tc, "opp_raam": opp,
                           "glas": glas, "orient": orient, "begr": cur_begr})

    # ---- gevel_bxh opbouwen uit de tikken, MET dedup (Essenhage-les 14-7) ----
    # GEOMETRISCHE WET: twee wanden van dezelfde kamer met GELIJKE breedte op dezelfde gevel zijn
    # tegenoverliggend (Wall 1 // Wall 3) — die kunnen fysiek niet allebei dezelfde buitengevel zijn.
    # De breedte van zo'n paar telt dus 1x (geen aanname; de kamer raakt de gevel maar aan één kant).
    from collections import defaultdict as _ddw
    gevel_onderbouwing = {}        # gevel_key -> verdieping -> ['kamer wand breedte', ...] (controle)
    _tel_breedtes = _ddw(list)     # (kamer_id, gevel_key) -> lijst effectieve breedtes (op volgorde)
    for _t in gevel_tikken:
        _tel_breedtes[(_t["kamer_id"], _t["gevel_key"])].append(_t)
    for (_kid, _gk), _tks in _tel_breedtes.items():
        _gezien = {}    # afgeronde breedte -> hoe vaak al geteld
        for _t in _tks:
            _be, _vd = _t["breedte_eff"], _t["verdieping"]
            if not _be or not _vd:
                gevel_bxh_onvolledig.add(_gk); continue
            _wr = round(_be, 2)
            if _gezien.get(_wr, 0) >= 1:
                # duplicaat parallelle wand (tegenoverliggend) -> NIET nog eens tellen
                notes.append("Gevel %s (kamer '%s'%s): tweede wand van %.2f m op dezelfde gevel is de "
                             "TEGENOVERLIGGENDE wand -> 1x geteld (kan niet dezelfde buitengevel zijn)."
                             % (_t["orient"], _t["kamer"], (" %s" % _vd) if _vd else "", _wr))
                _gezien[_wr] += 1
                continue
            # TEGENOVERLIGGEND OP WANDNUMMER (Essenhage 29-7): MagicPlan nummert de wanden rondom de
            # kamer, dus in een vierhoekige kamer liggen Wall n en Wall n+2 TEGENOVER elkaar. Staan die
            # beide op dezelfde gevel getagd, dan kan dat geometrisch niet (behalve bij een L-vorm) en
            # telt de tool ze tóch allebei mee -> te grote gevel. De breedte-dedup ziet dit niet als de
            # breedtes verschillen. Niet stil corrigeren (kan een L-vorm zijn): LUID melden.
            _nr = _t.get("wandnr")
            if _nr is not None:
                for _eerder in _tks:
                    _enr = _eerder.get("wandnr")
                    if (_eerder is not _t and _enr is not None and abs(_nr - _enr) == 2
                            and _eerder.get("verdieping") == _vd
                            and round(_eerder.get("breedte_eff") or 0, 2) != _wr
                            and _nr > _enr):
                        notes.append(
                            "FOUT of L-VORM — kamer '%s'%s: zowel Wall %d (%.2f m) als Wall %d (%.2f m) "
                            "staat op gevel %s. Die twee wanden liggen TEGENOVER elkaar (nummer +2), dus "
                            "ze kunnen niet dezelfde buitengevel zijn; de tool telt ze nu WEL allebei mee "
                            "(%.2f m breed). Controleer de gevelnaam van beide wanden — of het is een "
                            "L-vormige kamer, dan is het goed."
                            % (_t["kamer"] or "?", (" %s" % _vd) if _vd else "", _enr,
                               _eerder.get("breedte_eff") or 0, _nr, _be, _t["orient"],
                               (_eerder.get("breedte_eff") or 0) + _be))
                        break
            _gezien[_wr] = _gezien.get(_wr, 0) + 1
            _d_bxh = gevel_bxh.setdefault(_gk, {})
            _d_bxh[_vd] = round(_d_bxh.get(_vd, 0.0) + _be, 2)
            # ONDERBOUWING: leg vast WELKE wand is meegeteld, zodat de adviseur de gevel-m2 kan
            # controleren ('kan ik jou controleren?' — Renze 29-7). Komt in SchilDeel.opmerkingen.
            gevel_onderbouwing.setdefault(_gk, {}).setdefault(_vd, []).append(
                "%s %s %.2f m" % (_t["kamer"] or "?", _t["wand"] or "", _be))

    # ---- AUTO-PERIMETER (begane-grond buitengevel-breedtes) ----
    # De vloer-perimeter (randverlies, NEN-EN-ISO 13370) = de lengte van de begane-grondvloerrand die aan
    # buiten grenst. Dat is precies de som van de op de begane grond getikte BUITENgevel-breedtes: die zijn
    # al ontdubbeld voor tegenoverliggende wanden, en woningscheidende (AVR) wanden zitten er NIET in ->
    # de buurwand-correctie die de MagicPlan 'Exterior perimeter' vergt, is hiermee al gedaan. Bij een
    # deels-buiten-wand telt de 'Grenst aan buiten (m)'-lengte (breedte_eff), niet de hele wand.
    auto_perimeter = round(sum(_br for _verd in gevel_bxh.values()
                               for _vd, _br in _verd.items() if _is_bg(_vd or "")), 2)

    # ---- schil opbouwen ----
    schil = []

    # VABI-beslisboom per bouwdeel (nieuwe Constructies-form): Invoer (Kwaliteitsverklaring/Beslisschema)
    # -> Isolatie aanwezig? (Ja/Nee/Onbekend) -> isolatiedikte onbekend?/bouwjaar/dikte (mm)/spouw.
    # "Kwaliteitsverklaring" -> de tool VLAGT het (adviseur zet Invoer zelf in VABI; golden rule: niet gokken).
    # Valt terug op de oude platte velden (Rc-bron <deel> / Isolatie aanwezig) zodat oudere exports blijven werken.
    def _bouwdeel(prefix, oud_rcveld="", oud_isolveld="", oud_begrveld=""):
        # 11-7: de dak-boomvelden heten live "Dak N - ..." (was "Dakvlak N - ..."); probeer beide
        _alt = prefix.replace("Dakvlak", "Dak") if "Dakvlak" in prefix else None
        def gv(*names):
            alle = list(names) + ([n.replace(prefix, _alt) for n in names] if _alt else [])
            return next((v for v in (_undot(G(n)) for n in alle) if v), "")
        invoer = gv(prefix + " - invoer", prefix + " - invoer (override)")
        iso = gv(prefix + " - isolatie aanwezig?")
        dikte_onb = gv(prefix + " - isolatiedikte onbekend?").lower() in ("ja", "yes", "true")
        dikte = _f(G(prefix + " - isolatiedikte (mm)")) or (_f(G(_alt + " - isolatiedikte (mm)")) if _alt else None)
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
        # 'Onbekend' -> None (niet False!): False = geverifieerd géén spouw, None = onbekend (audit F4 15-7)
        spouw = (None if (not spouw_s or "onbek" in spouw_s.lower())
                 else (spouw_s.lower() in ("ja", "yes", "true")))
        return {"rc_bron": rc,
                "isolatie": {"ja": "Ja", "nee": "Nee", "onbekend": "Onbekend"}.get(iso.lower(), iso or "Onbekend"),
                "dikte_mm": (dikte if not dikte_onb else None),
                "dikte_onbekend": dikte_onb, "spouw": spouw, "begrenzing": begr, "bouwjaar": bouwjaar,
                # RUWE ingevuld-indicator (audit 12-7): 'isolatie' hierboven defaultt naar 'Onbekend'
                # en is dus altijd truthy — fallback-condities moeten HIERop testen, niet op isolatie.
                "ingevuld": bool(invoer or iso or dikte or bouwjaar or spouw_s or begr)}

    g_b = _bouwdeel("Gevel", "Rc-bron gevel", "Isolatie aanwezig")
    v_b = _bouwdeel("Vloer", "Rc-bron vloer", "", "Begrenzing (vloer)")
    d_b = _bouwdeel("Dakvlak 1", "Rc-bron dak")
    # DAK-ISOLATIE op FORM-niveau (Constructies, sinds 27-7): de afmetingen doe je in de webapp-wizard,
    # de isolatie hier. Elk nieuw dakvlak in de webapp erft deze standaard.
    _dak_form = _bouwdeel("Dak", "Rc-bron dak")
    if _dak_form["ingevuld"]:
        dos.opname.dak_standaard = BouwdeelStandaard(
            isolatie_aanwezig=_dak_form["isolatie"], isolatiedikte_mm=_dak_form["dikte_mm"],
            bouwjaarklasse=_dak_form["bouwjaar"], spouw_aanwezig=_dak_form["spouw"],
            rc_bron=_dak_form["rc_bron"], begrenzing=_dak_form["begrenzing"],
            isolatie_zijde=_undot(G("Dak - isolatie aan zijde")))
        notes.append("Dak-ISOLATIE uit de Constructies-form gelezen (isolatie %s%s) — elk dakvlak dat je "
                     "in de webapp toevoegt erft dit; de AFMETINGEN voer je in de webapp-dakwizard in."
                     % (_dak_form["isolatie"],
                        (", %s mm" % _dak_form["dikte_mm"]) if _dak_form["dikte_mm"] else ""))
    # rieten dak: NTA 8800 bijlage I geeft een Rc-toeslag d/0,105 -> Vabi rekent, wij signaleren
    if _undot(G("Rieten dak?")).strip().lower().startswith("ja"):
        _rd = _f(G("Rietdikte (mm)"))
        dos.opname.dak_standaard.riet_dikte_mm = _rd
        notes.append("RIETEN DAK opgegeven%s -> NTA 8800 bijlage I geeft een extra warmteweerstand "
                     "Rm;riet = d/0,105. Zet de rietlaag in Vabi bij de dakconstructie."
                     % ((" (%.0f mm)" % _rd) if _rd else " (dikte niet ingevuld)"))
    gevel_rc, vloer_rc, dak_rc = g_b["rc_bron"], v_b["rc_bron"], d_b["rc_bron"]
    isol = g_b["isolatie"] or "Onbekend"          # projectdefault gevel (wand-loop gebruikt dit)
    dikte_onbekend = g_b["dikte_onbekend"]
    # gevels per oriëntatie. HART-OP-HART GEVEL-TOESLAG (ISSO 8.2) wordt BEWUST NIET automatisch
    # toegepast (besluit Renze 19-7: te foutgevoelig om altijd goed te doen). De adviseur voegt de
    # toeslag zelf toe in VABI; de tool geeft er hieronder één luide melding voor.
    n_buur = aantal_woningscheidende_wanden(woningtype)
    if n_buur:
        _hoh = woningscheidende_wand_toeslag_m2(dos.opname.gevelhoogte_m, woningtype)
        _hoh_txt = ("ca. +%.2f m2 (0,11 m/gebouwscheidende wand x voor+achtergevel bij gevelhoogte "
                    "%.2f m)" % (_hoh, dos.opname.gevelhoogte_m) if _hoh else
                    "0,11 m per gebouwscheidende wand x gevelhoogte op voor- EN achtergevel "
                    "(gevelhoogte ontbreekt -> zelf berekenen)")
        notes.append("HART-OP-HART GEVEL-TOESLAG (ISSO 8.2) — ZELF TOEVOEGEN IN VABI (%s): %s. De tool "
                     "telt dit bewust NIET automatisch mee bij de gevel-m2." % (woningtype, _hoh_txt))
    verd_hoogte = {v.naam: v.hoogte_m for v in geo.vloeren if v.hoogte_m}
    # DIRECTE GEVELBREEDTE-INVOER (methode Renze 14-7, meest robuust): meet je de breedte van een
    # gevel, dan doet de tool breedte x verdiepingshoogte per bouwlaag — geen wandsom, geen dubbeltel.
    # Per gevelnaam (voor/achter/links/rechts) -> oriëntatie via de voorgevel-oriëntatie.
    gevelbreedte_per_orient = {}
    for _gnaam, _veld in (("voor", "Voorgevel - breedte (m)"), ("achter", "Achtergevel - breedte (m)"),
                          ("links", "Linkergevel - breedte (m)"), ("rechts", "Rechtergevel - breedte (m)")):
        _bm2 = _f(G(_veld))
        _oo = _orient_afleiden(_gnaam, orientatie_voorgevel)
        if _bm2 and _oo:
            gevelbreedte_per_orient[_oo] = _bm2
    gevel_refs = []     # {s, orient, bxh, extra} -> post-pass haalt de ZOLDER eruit (schuin dakvlak)
    # sorteren op de string-vorm: de sleutel bevat None/bool/str door elkaar (niet direct vergelijkbaar)
    for (orient, begr, isol_ov, nareken, rz, ovsig), opp_netto in sorted(gevel_per.items(),
                                                                        key=lambda kv: str(kv[0])):
        key = (orient, begr, isol_ov, nareken, rz, ovsig)
        # GEVEL-m2 = breedte x verdiepingshoogte per bouwlaag (BRUTO; ramen/deuren = deelvlakken
        # in Vabi). Voorkeur: de DIRECT GEMETEN gevelbreedte (rock-solid); anders de wandsom-breedte
        # per verdieping (met dedup); anders fallback bruto wandsom + note.
        bxh = gevel_bxh.get(key, {})
        _breedte_ov = gevelbreedte_per_orient.get(orient)
        if _breedte_ov and bxh:
            # override: elke GETIKTE verdieping krijgt de gemeten gevelbreedte (i.p.v. de wandsom)
            bxh = {vd: _breedte_ov for vd in bxh}
            notes.append("Gevel %s: DIRECT GEMETEN gevelbreedte %.2f m gebruikt (niet de wandsom) — "
                         "meest betrouwbaar." % (orient, _breedte_ov))
        _is_bxh = bool(bxh and (key not in gevel_bxh_onvolledig or _breedte_ov) and all(vd in verd_hoogte for vd in bxh))
        if _is_bxh:
            opp = round(sum(br * verd_hoogte[vd] for vd, br in bxh.items()), 2)
            # de opbouw-note komt in de ZOLDER-post-pass (dan is bekend of een verdieping schuin dak is)
        else:
            opp = gevel_bruto.get(key, opp_netto)
            notes.append("Gevel %s: b x h-methode niet mogelijk (wandbreedte of verdiepingshoogte "
                         "ontbreekt) -> bruto wandsom %.2f m2 gebruikt; controleer in Vabi." % (orient, opp))
        suffix = "" if begr == "Buitenlucht" else "-" + begr[:3].lower()
        if isol_ov or nareken:
            suffix += "-ov"
        if rz > 1:
            suffix += "-z%d" % rz
        gnaam = orient_naam.get(orient, "")
        gid = "gevel-%s%s" % (gnaam or orient, suffix)
        wand_isol = isol_ov or isol   # per-wand override wint van de projectdefault
        # per-wand override (element-fields) wint van de Constructies-standaard; leeg -> projectwaarde
        _ov_d, _ov_sp, _ov_bj, _ov_rc = ovsig if ovsig else (None, None, "", "")
        _w_dikte = _ov_d if _ov_d is not None else g_b["dikte_mm"]
        _w_spouw = _ov_sp if _ov_sp is not None else g_b["spouw"]
        _w_rcbron = _ov_rc or gevel_rc
        _gevel_s = SchilDeel(
            id=gid, type="gevel", subtype="", begrenzing=begr,
            orientatie=orient, gevel_naam=gnaam, oppervlakte_m2=round(opp, 2),
            isolatie_aanwezig=wand_isol, rekenzone=rz, rc_bron=_w_rcbron,
            bouwjaarklasse=_ov_bj,
            isolatiedikte_mm=_w_dikte, spouw_aanwezig=_w_spouw,
            opmerkingen=((("%sgevel" % gnaam + " | ") if gnaam else "")
                         + "BRUTO (ramen/deuren als deelvlak); AVR/party-walls uitgefilterd"
                         # CONTROLE-ONDERBOUWING: welke wanden zijn per bouwlaag meegeteld en hoe
                         # komt de m2 tot stand? Zo kun je de gevel-m2 zelf natrekken.
                         + (" | ONDERBOUWING: " + " ; ".join(
                             "%s = %s -> %.2f m x %.2f m = %.2f m2"
                             % (_vd, " + ".join(gevel_onderbouwing[key][_vd]),
                                bxh.get(_vd, 0.0), verd_hoogte.get(_vd, 0.0),
                                bxh.get(_vd, 0.0) * verd_hoogte.get(_vd, 0.0))
                             for _vd in bxh if _vd in gevel_onderbouwing.get(key, {}))
                            if (_is_bxh and gevel_onderbouwing.get(key)) else "")
                         + (" | begrenzing %s (naamconventie)" % begr if begr != "Buitenlucht" else "")
                         + (" | isolatie %s (per-wand override)" % isol_ov if isol_ov else "")
                         + (" | per-wand override: dikte/spouw/bron afwijkend van de Constructies-standaard"
                            if ovsig else "")
                         + (" | Rc/U via kwaliteitsverklaring (zet Invoer in Vabi)" if _w_rcbron == "Kwaliteitsverklaring" else "")
                         + (" | NAREKENEN in Vabi (gemarkeerd: deels buiten/binnen of bijzonder)" if nareken else "")))
        schil.append(_gevel_s)
        if _is_bxh:
            gevel_refs.append({"s": _gevel_s, "orient": orient, "bxh": dict(bxh)})
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
    vloer_begr = v_b["begrenzing"] or _undot(G("Begrenzing (vloer)"))
    if not vloer_begr:
        # audit 12-7: dit was een STILLE default. Kruipruimte blijft de meest voorkomende situatie,
        # maar de adviseur moet het WETEN (grond vs kruipruimte stuurt het warmteverlies).
        vloer_begr = "Kruipruimte"
        notes.append("VLOER-BEGRENZING ontbreekt in de opname -> 'Kruipruimte' aangenomen; "
                     "controleer (grond/kelder?) en pas zo nodig aan in de webapp of Vabi.")
    bg_floor_area = footprint_bg or _f(G("Above grade living area"))  # begane-grond-footprint (niet de meerlaagse som)
    split_tot = round(sum(vloer_split.values()), 2)
    hoofd_area = round(max(0.0, (bg_floor_area or 0.0) - split_tot), 2) if split_tot else (bg_floor_area or 0.0)
    # perimeter: liefst AUTO (som begane-grond buitengevel-breedtes; buurwanden zitten er al niet in en
    # deels-buiten-wanden tellen via hun buitenlengte), MAAR alleen als de tagging plausibel COMPLEET is —
    # anders onderschat je de perimeter fors. Compleet = auto >= 60% van de verwachte buitenomtrek
    # (sqrt(footprint) x aantal buitengevels; buitengevels = 4 - #buurwanden). Anders: MagicPlan-omtrek.
    _verwacht_perim = ((bg_floor_area or 0) ** 0.5) * max(4 - n_buur, 1) if bg_floor_area else 0
    _auto_compleet = bool(auto_perimeter and _verwacht_perim and auto_perimeter >= 0.6 * _verwacht_perim)
    vloer_perimeter = auto_perimeter if _auto_compleet else geo.perimeter_m
    if _auto_compleet:
        notes.append("Vloer-perimeter AUTOMATISCH berekend uit de begane-grond buitengevel-breedtes: %.1f m "
                     "(woningscheidende wanden tellen al niet mee; deels-buiten-wanden via hun buitenlengte). "
                     "Verifieer in Vabi." % auto_perimeter)
    else:
        if auto_perimeter:
            notes.append("Vloer-perimeter: som van de getikte begane-grond gevelbreedtes (%.1f m) lijkt "
                         "ONVOLLEDIG (verwacht ~%.0f m) -> MagicPlan-buitenomtrek %.1f m gebruikt. Tik álle "
                         "buitengevels op de begane grond voor een automatische perimeter."
                         % (auto_perimeter, _verwacht_perim, geo.perimeter_m or 0))
        if n_buur:
            notes.append("Vloer-perimeter = MagicPlan-buitenomtrek (%.1f m); de WONINGSCHEIDENDE wand(en) "
                         "tellen NIET mee in de perimeter (opname-handleiding §3.4) -> corrigeer 'm in Vabi "
                         "(%s, %d buurwand(en))." % (geo.perimeter_m or 0, woningtype, n_buur))
    schil.append(SchilDeel(id="vloer", type="vloer", subtype="Begane grondvloer",
                           begrenzing=vloer_begr, oppervlakte_m2=hoofd_area or 0.0,
                           isolatie_aanwezig=v_b["isolatie"], rekenzone=1,
                           isolatiedikte_mm=v_b["dikte_mm"],
                           perimeter_m=vloer_perimeter,   # randverlies begane-grondvloer (auto of MagicPlan-fallback)
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
    def _helling_ok(h, ctx):
        """audit 13-7: ongeldige helling (<=0 of >=89, bv. tikfout '95') gaf stil een TE KLEIN dak
        (cos-clamp naar footprint). Ongeldig -> luide note + geen berekening."""
        if h is None:
            return None
        if 0 < float(h) < 89:
            return float(h)
        notes.append("%s: hellingshoek %g° is ONGELDIG (moet tussen 0 en 89) -> dak NIET berekend; "
                     "corrigeer de invoer." % (ctx, float(h)))
        return None

    type_dak = _undot(G("Dakvlak 1 - daktype") or G("Type dak"))
    if not type_dak:
        # audit 13-7: dit was een STILLE Zadeldak-aanname; nu default + LUIDE note (legacy-pad —
        # de nieuwe type-masters per dak zijn leidend en eisen expliciete keuze)
        type_dak = "Zadeldak"
        notes.append("TYPE DAK ontbreekt in de opname -> 'Zadeldak' aangenomen (legacy-pad); "
                     "controleer het daktype en de dakvlakken in de webapp/Vabi.")
    helling = _f(G("Dakvlak 1 - hellingshoek (°)")) or _f(G("Dakvlak 1 - hellingshoek")) or _f(G("Hellingshoek dak")) or _f(G("Dak hellingshoek"))
    breedte = _f(G("Dak - vloerbreedte (m)")) or _f(G("Dak vloerbreedte"))
    if helling is None:
        _kn_leg = (_f(G("Dak - knieschothoogte (m, optioneel)")) or _f(G("Dak knieschothoogte")) or 0.0)
        _nok_leg = _f(G("Dak - nokhoogte (m, optioneel)")) or _f(G("Dak nokhoogte"))
        helling = hellingshoek_uit_nok(breedte, _nok_leg, _kn_leg)
        if helling and _nok_leg and not _kn_leg:
            notes.append("Dak: helling %g° BEREKEND uit nokhoogte ZONDER knieschot — heeft de zolder "
                         "een knieschot, vul die hoogte in (helling valt anders te steil uit; "
                         "Essenhage: 45° i.p.v. de echte 30°). Of meet de helling direct." % helling)
    helling = _helling_ok(helling, "Dak (legacy-pad)")
    o1 = _undot(G("Dakvlak 1 - oriëntatie") or G("Dakvlak 1 - orientatie") or G("Dak orientatie zijde 1") or G("Dak oriëntatie zijde 1"))
    o2 = _undot(G("Dakvlak 2 - oriëntatie") or G("Dakvlak 2 - orientatie") or G("Dak orientatie zijde 2") or G("Dak oriëntatie zijde 2"))
    k1 = _undot(G("Dak - kopgevel oriëntatie 1") or G("Dak - kopgevel orientatie 1") or G("Kopgevel orientatie 1") or G("Kopgevel oriëntatie 1"))
    k2 = _undot(G("Dak - kopgevel oriëntatie 2") or G("Dak - kopgevel orientatie 2") or G("Kopgevel orientatie 2") or G("Kopgevel oriëntatie 2"))
    plat_m2 = _f(G("Plat dak m2")) or _f(G("Plat dak m²"))   # legacy; plat dak nu als dakvlak met daktype 'Plat dak'
    plat_or = _undot(G("Plat dak orientatie")) or _undot(G("Plat dak oriëntatie"))
    # ---- NIEUW DAKMODEL (8-7): "Dak N - type" per DAK (kap) -> vlakken automatisch per type ----
    # Plat = footprint bovenste verdieping (of override) · Zadel = 2 schuine vlakken + 2 kopgevel-
    # driehoeken (auto, orientatie +/-90) · Schild = 4 vlakken zonder kopgevels · Lessenaar = 1 vlak
    # (hoge-zijde-gevel handmatig) · Afwijkend = de 9 m2-vakjes. Isolatie/begrenzing per dak N komt uit
    # de "Dakvlak N - invoer"-boom. Wordt de geometrie complex -> Afwijkend (zelf invoeren).
    _C8 = ["N", "NO", "O", "ZO", "Z", "ZW", "W", "NW"]
    def _opp8(o):
        o = (o or "").upper()
        return _C8[(_C8.index(o) + 4) % 8] if o in _C8 else ""
    def _zij8(o):
        o = (o or "").upper()
        return (_C8[(_C8.index(o) + 2) % 8], _C8[(_C8.index(o) - 2) % 8]) if o in _C8 else ("", "")
    _niet_kelder = [v for n2, v in floor_footprint.items() if not _is_kelder(n2)]
    top_fp = _niet_kelder[-1] if _niet_kelder else (bg_floor_area or 0.0)
    # PITCHED-DAK-FOOTPRINT (Essenhage-les 15-7): de bovenste verdieping is vaak een ZOLDER
    # (klein, binnen de kap). Een schuin dak overspant dan niet de zolder maar de verdieping
    # ERONDER. top_fp (zolder 22 m²) gaf dak 25 waar het echte dak 57 m² was. Voor een SCHUIN dak
    # (zadel/schild/lessenaar) nemen we daarom de verdieping onder de zolder als het dak die
    # duidelijk overspant; een PLAT dak blijft top_fp (dat ligt wél op de bovenste verdieping).
    _fp_namen = [n2 for n2 in floor_footprint if not _is_kelder(n2)]
    _top_verd_naam = _fp_namen[-1] if _fp_namen else ""
    dak_fp = top_fp
    dak_fp_bron = "footprint bovenste verdieping (%.1f m²)" % (top_fp or 0)
    if len(_fp_namen) >= 2:
        _onder_fp = floor_footprint.get(_fp_namen[-2], 0.0)
        if top_fp and _onder_fp and top_fp < 0.70 * _onder_fp:
            dak_fp = _onder_fp
            dak_fp_bron = ("footprint van de verdieping ONDER de zolder (%s = %.1f m²); de bovenste "
                           "verdieping (%.1f m²) is te klein en lijkt een zolder binnen de kap"
                           % (_fp_namen[-2], _onder_fp, top_fp))
    dak_done = False
    _force9 = False
    _heeft_plat_dak = False   # aanbouw-dak-detectie (is de uitbouw z'n eigen platte dak ingevoerd?)
    _dak_kappen = []          # (dak_nr, type, hoofdorientatie) voor dubbele-kap-detectie
    dak_klasse = {}    # per dak (1-3): bouwjaarklasse-antwoord -> wint op de eigen dak%d-vlakken
    for _dn in (1, 2, 3):
        # 13-7: live hernoemd naar 'Dak' / 'Extra dak A' / 'Extra dak B' (Dak 1/2/3 = legacy)
        _kand_pre = (("Dak", "Dak 1"), ("Extra dak A", "Dak 2"), ("Extra dak B", "Dak 3"))[_dn - 1]
        Pd = next((c for c in _kand_pre
                   if any((k or "").startswith(c + " - type") or (k or "").startswith(c + " zadel")
                          or (k or "").startswith(c + " plat") for k in plan)), "Dak %d" % _dn)
        # type-veld op PREFIX zoeken: de suffix is live al 2x hernoemd (leeg = .../HELE dak/EXTRA dak)
        _tkey = next((k for k in plan if (k or "").startswith(Pd + " - type")
                      or (_dn == 1 and (k or "").startswith("Type dak"))), None)
        t_n = _undot(plan.get(_tkey, "") if _tkey else (G(Pd + " - type") or ""))
        if not t_n:
            continue
        tn = t_n.lower()
        b_n = _bouwdeel(Pd, "Rc-bron dak")
        if not b_n["ingevuld"]:      # audit 12-7: isolatie defaultte altijd -> fallback draaide nooit
            b_n = _bouwdeel("Dakvlak %d" % _dn, "Rc-bron dak")
        if b_n["bouwjaar"]:
            dak_klasse[_dn] = b_n["bouwjaar"]    # per-dak klasse -> post-pass op de dak%d-vlakken
        vlakken_n = []
        if "plat" in tn:
            _heeft_plat_dak = True
            m2p = _f(G(Pd + " plat - oppervlak (m², leeg = footprint bovenste verdieping)")) or top_fp
            vlakken_n = [{"kind": "dak", "type": "plat", "orientatie": "", "m2": m2p or 0.0, "hellingshoek": 0}]
            if _dn > 1 and not _f(G(Pd + " plat - oppervlak (m², leeg = footprint bovenste verdieping)")):
                notes.append("Dak %d (plat): geen m² ingevuld -> footprint bovenste verdieping gebruikt "
                             "(%.1f m²) - klopt dat voor dit dakdeel? Zo niet: vul het oppervlak in." % (_dn, top_fp or 0))
        elif "zadel" in tn:
            o_z = _undot(G(Pd + " zadel - oriëntatie dakvlak 1"))
            br_z = _f(G(Pd + " zadel - vloerbreedte tussen de kopgevels (m)"))
            nok_z = _f(G(Pd + " zadel - nokhoogte boven zoldervloer (m)"))
            kn_z = _f(G(Pd + " zadel - knieschothoogte (m, leeg = 0)")) or 0.0
            kn_z2 = _f(G(Pd + " zadel - knieschothoogte vlak 2 (m, leeg = zelfde)"))
            _h_veld_z = _f(G(Pd + " zadel - hellingshoek (°, leeg = berekend uit nok/breedte)"))
            h_z = _helling_ok(_h_veld_z or hellingshoek_uit_nok(br_z, nok_z, kn_z), "Dak %d (zadel)" % _dn)
            if not _h_veld_z and nok_z and not kn_z and h_z:
                # Essenhage-les 14-7: nok 2,97 zonder knieschot gaf 45° waar het echte dak 30° was
                # (knieschot ~1,25 m). De formule kan het knieschot niet raden -> luide check.
                notes.append("Dak %d (zadel): helling %g° BEREKEND uit nokhoogte ZONDER knieschot — "
                             "heeft de zolder een knieschot/borstwering, vul die hoogte in (de helling "
                             "valt anders te STEIL uit en het dak te groot). Of meet de helling direct."
                             % (_dn, h_z))
            h_z2 = _helling_ok(_f(G(Pd + " zadel - hellingshoek vlak 2 (°, leeg = zelfde)"))
                               or ((hellingshoek_uit_nok(br_z, nok_z, kn_z2) or h_z) if kn_z2 else h_z),
                               "Dak %d (zadel, vlak 2)" % _dn)
            # OVERSPANNING + FOOTPRINT + KOPGEVEL-BASIS. 'vloerbreedte tussen de kopgevels' (br_z) is de
            # NOKLENGTE (afstand tussen de kopgevels). De kopgevel-driehoek staat HAAKS op de nok; z'n
            # basis is de OVERSPANNING (= footprint / noklengte), NIET de noklengte zelf. De oude code gaf
            # br_z als kopgevel-basis door -> te kleine/grote kopgevel bij hoek-/vrijstaande woningen
            # (Essenhage-kopgevel-fix 15-7; viel bij die tussenwoning niet op want kopgevels weggelaten).
            _c_ov = _f(G(Pd + " zadel - overspanning (m, leeg = auto)"))
            _fp_ov_z = _f(G(Pd + " zadel - grondoppervlak dat het dak overspant (m², leeg = auto)"))
            if _c_ov and br_z:                        # volledig expliciet (zoals de webapp): c x noklengte
                _fp_z = round(_c_ov * br_z, 2)
                _kop_basis = _c_ov
                _fp_bron_z = "overspanning %.2f m x noklengte %.2f m = %.1f m²" % (_c_ov, br_z, _fp_z)
            else:
                _fp_z = _fp_ov_z or dak_fp
                _kop_basis = _c_ov or (round(_fp_z / br_z, 2) if br_z else 0.0)
                _fp_bron_z = ("het INGEVULDE grondoppervlak %.1f m²" % _fp_ov_z) if _fp_ov_z else dak_fp_bron
            if h_z and o_z:
                vlakken_n = dak_vlakken_zadeldak(_fp_z, _kop_basis or 0.0, h_z,
                                                 orient_schuin=(o_z, _opp8(o_z)), orient_kopgevel=_zij8(o_z))
                notes.append("Dak %d (zadel): schuine vlakken berekend over %s (%.0f° helling); "
                             "kopgevel-basis (overspanning) = %.2f m. Verifieer in Vabi. Klopt de "
                             "overspanning niet? Vul 'overspanning (m)' + 'vloerbreedte tussen de kopgevels "
                             "(m)' in — dan is het dak volledig expliciet (zoals de webapp)."
                             % (_dn, _fp_bron_z, h_z, _kop_basis or 0.0))
                # KOPGEVEL-DRIEHOEKEN zitten op NOK-/zolderniveau. Ze zijn alleen BUITEN als op de
                # BOVENSTE verdieping een gevel met die orientatie is getikt. Een aanbouw-zijgevel op de
                # BEGANE GROND (bv. bijkeuken) maakt de nok-kopgevel NIET buiten (Essenhage-les 15-7: de
                # Laundry-aanbouw op NO/ZW zette de tussenwoning-kopgevels ten onrechte aan -> +8 m²).
                _buiten_orients = {t["orient"] for t in gevel_tikken
                                   if t.get("orient") and t.get("verdieping") == _top_verd_naam}
                _weg_kop = [v for v in vlakken_n if v.get("kind") == "gevel"
                            and v.get("orientatie") and v["orientatie"] not in _buiten_orients]
                if _weg_kop:
                    vlakken_n = [v for v in vlakken_n if v not in _weg_kop]
                    notes.append("Dak %d (zadel): kopgevel(s) %s WEGGELATEN — op de bovenste verdieping is "
                                 "op die zijde(n) geen buitengevel getikt (buurwand/tussenwoning; een "
                                 "aanbouw-zijgevel op de begane grond telt hier NIET). Is een kopgevel tóch "
                                 "buiten (bv. nok haaks op de straat, vrijstaand)? Tik die zijgevel dan op de "
                                 "ZOLDER als gevel, dan telt de driehoek automatisch mee."
                                 % (_dn, "/".join(v["orientatie"] for v in _weg_kop)))
                if h_z2 and h_z2 != h_z:   # asymmetrisch: vlak 2 met eigen helling op de halve footprint
                    for v in vlakken_n:
                        if v.get("kind") == "dak" and v.get("orientatie") == _opp8(o_z):
                            v["m2"] = round((_fp_z / 2.0) / max(0.087, __import__("math").cos(__import__("math").radians(h_z2))), 2)
                            v["hellingshoek"] = h_z2
                    notes.append("Dak %d (zadel): ASYMMETRISCH (%g°/%g°) -> vlakken per halve footprint "
                                 "berekend en kopgevels op vlak-1-helling benaderd; verifieer de m² in Vabi." % (_dn, h_z, h_z2))
            else:
                notes.append("Dak %d (zadel): hellingshoek (of nok/breedte) en/of oriëntatie ontbreekt -> "
                             "vul aan; dak overgeslagen." % _dn)
        elif "schild" in tn or "tent" in tn:
            h_s = _helling_ok(_f(G(Pd + " schild - hellingshoek lange vlakken (°)")), "Dak %d (schild)" % _dn)
            h_k = _f(G(Pd + " schild - hellingshoek kopschilden (°, leeg = zelfde)"))
            o_s = _undot(G(Pd + " schild - oriëntatie lang dakvlak 1"))
            if h_s and o_s:
                zij = _zij8(o_s)
                _fp_ov_s = _f(G(Pd + " schild - grondoppervlak dat het dak overspant (m², leeg = auto)"))
                _fp_s = _fp_ov_s or dak_fp
                vlakken_n = dak_vlakken_schilddak(_fp_s, h_s, (o_s, _opp8(o_s), zij[0], zij[1]))
                notes.append("Dak %d (schild): berekend over %s -> verifieer de m² in Vabi."
                             % (_dn, ("het INGEVULDE grondoppervlak %.1f m²" % _fp_ov_s) if _fp_ov_s else dak_fp_bron))
                if h_k and h_k != h_s:
                    notes.append("Dak %d (schild): kopschilden %g° wijken af van de lange vlakken %g° -> "
                                 "verfijn de vlakverdeling in Vabi." % (_dn, h_k, h_s))
            else:
                notes.append("Dak %d (schild): hellingshoek en/of oriëntatie ontbreekt -> vul aan; dak overgeslagen." % _dn)
        elif "lessenaar" in tn:
            o_l = _undot(G(Pd + " lessenaar - oriëntatie dakvlak (afwaterend naar)"))
            hl_ = _f(G(Pd + " lessenaar - hoogte lage zijde boven vloer (m)"))
            hh_ = _f(G(Pd + " lessenaar - hoogte hoge zijde boven vloer (m)"))
            h_l = _helling_ok(_f(G(Pd + " lessenaar - hellingshoek (°, leeg = berekend)")),
                              "Dak %d (lessenaar)" % _dn)
            if h_l and o_l:
                _fp_ov_l = _f(G(Pd + " lessenaar - grondoppervlak dat het dak overspant (m², leeg = auto)"))
                _fp_l = _fp_ov_l or dak_fp
                vlakken_n = dak_vlakken_lessenaar(_fp_l, h_l, o_l)
                notes.append("Dak %d (lessenaar): berekend over %s -> verifieer de m² in Vabi."
                             % (_dn, ("het INGEVULDE grondoppervlak %.1f m²" % _fp_ov_l) if _fp_ov_l else dak_fp_bron))
                if hh_ and hl_ is not None:
                    notes.append("Dak %d (lessenaar): hoge-zijde-opstand (%.2f m hoogteverschil) hoort bij de "
                                 "GEVEL aan de hoge kant -> reken die strook (hoogteverschil x gevelbreedte) "
                                 "handmatig na in Vabi." % (_dn, (hh_ - (hl_ or 0.0))))
            else:
                notes.append("Dak %d (lessenaar): hellingshoek en/of oriëntatie ontbreekt -> vul aan; dak overgeslagen." % _dn)
        elif "afwijkend" in tn or "anders" in tn:
            _force9 = True
            notes.append("Dak %d: type Afwijkend -> vul de 9 'Dak m² <oriëntatie>'-vakjes in (zelf gemeten)." % _dn)
        for v in vlakken_n:
            schil.append(SchilDeel(
                id="dak%d-%s-%s" % (_dn, (v.get("type") or "")[:5], v["orientatie"] or "x"),
                type=v["kind"], subtype=v.get("type", ""),
                begrenzing=(b_n["begrenzing"] or "Buitenlucht"),
                orientatie=v["orientatie"], oppervlakte_m2=v["m2"], hellingshoek=v.get("hellingshoek"),
                isolatie_aanwezig=b_n["isolatie"], rekenzone=1, isolatiedikte_mm=b_n["dikte_mm"],
                rc_bron=b_n["rc_bron"] or dak_rc,
                opmerkingen="dak %d (%s) auto-berekend uit type-invoer" % (_dn, t_n)))
            dak_done = True
        if vlakken_n:
            _dak_kappen.append((_dn, tn, next((v["orientatie"] for v in vlakken_n if v.get("orientatie")), "")))
        # --- dakkapellen + dakramen: PER DAKVLAK en PER GROEP (A/B) — 12-7 herontwerp na veldfeedback:
        # een zadeldak heeft dakramen/kapellen in voor- EN achtervlak, vaak met verschillend glas/maten.
        _hoofd_or = next((v["orientatie"] for v in vlakken_n if v.get("orientatie")), "")
        _hoofd_h = next((v.get("hellingshoek") for v in vlakken_n if v.get("hellingshoek")), None)
        def _Gp(pre):
            _k = next((k for k in plan if (k or "").startswith(pre)), None)
            return plan.get(_k, "") if _k else ""
        def _kies_vlak(waarde):
            w = _undot(waarde or "").lower()
            return _opp8(_hoofd_or) if ("2" in w or "tegenover" in w) else _hoofd_or
        def _trek_af(orient, m2):
            _kand = [s2 for s2 in schil if s2.id.startswith("dak%d-" % _dn) and s2.type == "dak"
                     and (s2.hellingshoek or 0) > 0]
            _hit = (next((s2 for s2 in _kand if (s2.orientatie or "") == orient), None)
                    or (max(_kand, key=lambda s2: s2.oppervlakte_m2 or 0) if _kand else None))
            if _hit:
                _hit.oppervlakte_m2 = round(max((_hit.oppervlakte_m2 or 0) - m2, 0.0), 2)
        # dakkapellen A/B (ISSO 82.1 par. 8.2.1: voorvlak+2 wangen=gevel, dakje=plat dak, gat afgetrokken)
        for _g, _v in (("A", (" - aantal dakkapellen (leeg = geen)", " - dakkapel breedte (m)",
                              " - dakkapel hoogte voorvlak (m)", " - dakkapel diepte (m)",
                              " - dakkapel A: dakvlak")),
                       ("B", (" - dakkapel B: aantal", " - dakkapel B: breedte (m)",
                              " - dakkapel B: hoogte voorvlak (m)", " - dakkapel B: diepte (m)",
                              " - dakkapel B: dakvlak"))):
            _ka, _kb = _f(_Gp(Pd + _v[0])), _f(_Gp(Pd + _v[1]))
            _kh, _kd = _f(_Gp(Pd + _v[2])), _f(_Gp(Pd + _v[3]))
            if not (_ka and _kb and _kh and _kd):
                continue
            _kor = _kies_vlak(_Gp(Pd + _v[4]))
            dk = dakkapel_vlakken(_kb, _kh, _kd, _hoofd_h)
            _n_kap = int(_ka)
            _sfx = "-" + _g.lower()
            schil.append(SchilDeel(id="dak%d-kapel%s-gevel" % (_dn, _sfx), type="gevel", subtype="dakkapel",
                begrenzing="Buitenlucht", orientatie=_kor, oppervlakte_m2=round(dk["gevel_m2"] * _n_kap, 2),
                isolatie_aanwezig=b_n["isolatie"], rekenzone=1, isolatiedikte_mm=b_n["dikte_mm"],
                rc_bron=b_n["rc_bron"] or dak_rc,
                opmerkingen="dakkapel %s voorvlak+2 wangen (%dx, vlak %s) — raam apart als kozijn opnemen"
                            % (_g, _n_kap, _kor or "?")))
            schil.append(SchilDeel(id="dak%d-kapel%s-plat" % (_dn, _sfx), type="dak", subtype="plat (dakkapel)",
                begrenzing="Buitenlucht", orientatie="", oppervlakte_m2=round(dk["dak_m2"] * _n_kap, 2),
                hellingshoek=0, isolatie_aanwezig=b_n["isolatie"], rekenzone=1,
                isolatiedikte_mm=b_n["dikte_mm"], rc_bron=b_n["rc_bron"] or dak_rc,
                opmerkingen="dakkapel %s plat dakje (%dx)" % (_g, _n_kap)))
            _gat_tot = round(dk["gat_schuin_dak_m2"] * _n_kap, 2)
            if _gat_tot:
                _trek_af(_kor, _gat_tot)
            notes.append("Dak %d kapel %s (%dx, vlak %s): %s" % (_dn, _g, _n_kap, _kor or "?", dk["flag"]))
        # dakramen-MATRIX (12-7, na veldfeedback "soms 10-20 dakramen, alle glastypes door elkaar"):
        # per dakvlak (1 = gekozen orientatie, 2 = tegenover) een m2-veld PER GLASTYPE -> onbeperkt
        # combineerbaar. A/B-groepen + enkelvoudige velden blijven legacy-fallback.
        _rw_groepen = []
        for _vl in (1, 2):
            _vor = _hoofd_or if _vl == 1 else _opp8(_hoofd_or)
            _vn = _f(_Gp(Pd + " dakramen vlak %d - aantal" % _vl))
            for _gt in ("Enkel", "Dubbel", "HR", "HR+", "HR++", "TripleHR", "Onbekend"):
                _gm = _f(G(Pd + " dakramen vlak %d - %s (m²)" % (_vl, _gt)) or
                         G(Pd + " dakramen vlak %d - %s (m2)" % (_vl, _gt)))
                if _gm:
                    _rw_groepen.append(("v%d-%s" % (_vl, _gt.lower().replace("+", "p")),
                                        _vn or 0, _gm, _gt, _vor))
        if not _rw_groepen:
         for _g in ("A", "B"):
            _rwn = _f(_Gp(Pd + " - dakramen %s: aantal" % _g))
            _rwm = _f(_Gp(Pd + " - dakramen %s: totaal oppervlak" % _g))
            if _rwn and _rwm:
                _rw_groepen.append((_g, _rwn, _rwm, _undot(_Gp(Pd + " - dakramen %s: type glas" % _g)),
                                    _kies_vlak(_Gp(Pd + " - dakramen %s: dakvlak" % _g))))
        if not _rw_groepen:
            _rwn = _f(G(Pd + " - dakramen aantal (leeg = geen)"))
            _rwm = _f(_Gp(Pd + " - dakramen totaal oppervlak"))
            if _rwn and _rwm:
                _rw_groepen.append(("", _rwn, _rwm, _undot(G(Pd + " - dakramen type glas")), _hoofd_or))
        for _g, _rwn, _rwm, _rwg, _ror in _rw_groepen:
            schil.append(SchilDeel(id="dak%d-dakraam%s" % (_dn, ("-" + _g.lower()) if _g else ""),
                type="kozijn", subtype="Dakraam", begrenzing="Buitenlucht", orientatie=_ror,
                oppervlakte_m2=_rwm, glastype=_rwg or "", kozijnmateriaal="Hout of kunststof",
                hellingshoek=_hoofd_h,
                opmerkingen="dakraam/-ramen (%dx) in dakvlak %s — in Vabi als raam op het DAKvlak"
                            % (int(_rwn), _ror or "?")))
            # audit-glas-F1 15-7: NIET hier van het dakvlak aftrekken. Het dakraam wordt in Vabi als
            # DEELVLAK op het dakvlak geplaatst (objecten) en dáár 1x afgetrokken; parser + objecten
            # trokken het glas allebei af -> dakvlak dubbel verlaagd. Dak blijft BRUTO.
            if _rwn and _rwm / max(_rwn, 1) < 0.65:
                notes.append("Dak %d dakramen %s: gemiddeld < 0,65 m2/stuk -> Nij Begun rekent kleine "
                             "ruiten als 0,65 m2; check het totaal." % (_dn, _g or "-"))
        # Ag-zolder-check: schuin dak met laag/geen knieschot en geen 'Ag-aftrek zolder' ingevuld ->
        # suggereer de 1,5m-lijn-aftrek (NEN 2580); we passen 'm NIET automatisch toe (Ag = heilig)
        if "zadel" in tn and (kn_z or 0) < 1.5 and not ag_aftrek and br_z and top_fp:
            try:
                from core.geometry import ag_onder_schuin_dak
                _agz, _weg = ag_onder_schuin_dak(top_fp, top_fp / br_z, h_z or 45.0, kn_z or 0.0)
                if _weg > 0.5:
                    notes.append("Zolder onder schuin dak: 'Ag-aftrek zolder' is leeg, maar de 1,5m-lijn "
                                 "kost hier ~%.1f m² (knieschot %.2f m, helling %g°). Vul de aftrek in "
                                 "(of laat MagicPlan de kamer op de 1,5m-lijn meten)." % (_weg, kn_z or 0.0, h_z or 0))
            except Exception:
                pass
    _zadels = [(n2, o2) for n2, t2, o2 in _dak_kappen if "zadel" in t2]
    if len(_zadels) >= 2:
        _c8i = {"N": 0, "NO": 1, "O": 2, "ZO": 3, "Z": 4, "ZW": 5, "W": 6, "NW": 7}
        for _i in range(len(_zadels) - 1):
            _o1, _o2 = _zadels[_i][1].upper(), _zadels[_i + 1][1].upper()
            if _o1 in _c8i and _o2 in _c8i and (_c8i[_o1] + 4) % 8 == _c8i[_o2]:
                notes.append("LET OP dak %d + dak %d: BEIDE 'Zadeldak' met tegenovergestelde oriëntaties "
                             "(%s/%s) - dit is vrijwel zeker één zadeldak dat DUBBEL is ingevoerd. "
                             "Eén zadeldak = 1 dak (de tool maakt beide vlakken + kopgevels zelf): "
                             "verwijder dak %d in MagicPlan, anders telt het dak 2x mee!"
                             % (_zadels[_i][0], _zadels[_i + 1][0], _o1, _o2, _zadels[_i + 1][0]))
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
        # audit 13-7: per-vlak helling ook door _helling_ok (tikfout 95° gaf hier anders stil door)
        h_d = _helling_ok(_f(G(p + " - hellingshoek (°)")) or _f(G(p + " - hellingshoek")),
                          "Dakvlak %d (direct)" % n) or helling
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
        # kopgevel-basis = OVERSPANNING (footprint / noklengte), niet de noklengte zelf (kopgevel-fix 15-7)
        _kop_leg = (round((bg_floor_area or 0.0) / breedte, 2) if breedte else 0.0)
        dakvlakken = dak_vlakken_zadeldak(bg_floor_area or 0.0, _kop_leg, helling,
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
            type=v["kind"], subtype=v.get("type", ""),
            begrenzing=((d_b.get("begrenzing") or "Buitenlucht") if v["kind"] == "dak" else "Buitenlucht"),  # F6
            orientatie=v["orientatie"], oppervlakte_m2=v["m2"], hellingshoek=v.get("hellingshoek"),
            isolatie_aanwezig=d_b["isolatie"], rekenzone=1, isolatiedikte_mm=d_b["dikte_mm"], rc_bron=dak_rc,
            opmerkingen="dak-per-vlak uit opname (%s, helling %.0f gr)" % (type_dak, (v.get("hellingshoek") or 0))))
        dak_done = True
    if dakvlakken and ("schild" in tl or "tent" in tl):
        notes.append("Schilddak: totaal schuin dakoppervlak = footprint/cos(%.0f°), gelijk verdeeld over de "
                     "opgegeven zijden — verfijn de verdeling per dakvlak in Vabi." % (helling or 0))
    if plat_m2:
        schil.append(SchilDeel(id="dak-plat", type="dak", subtype="plat",
                               begrenzing=(d_b.get("begrenzing") or "Buitenlucht"),  # F6
                               orientatie=plat_or or "", oppervlakte_m2=plat_m2, hellingshoek=0,
                               isolatie_aanwezig=d_b["isolatie"], rekenzone=1, isolatiedikte_mm=d_b["dikte_mm"], rc_bron=dak_rc,
                               opmerkingen="plat dak (bv. erker)"))
        dak_done = True
    if (not dak_done) or _force9:   # type 'Anders'/'Afwijkend': 9 m²-vakjes per oriëntatie (N..NW + Horizontaal)
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
        schil.append(SchilDeel(id="dak", type="dak", subtype=type_dak,
                               begrenzing=(d_b.get("begrenzing") or "Buitenlucht"),  # F6
                               orientatie="", oppervlakte_m2=bg_floor_area or 0.0,
                               isolatie_aanwezig=d_b["isolatie"], rekenzone=1, isolatiedikte_mm=d_b["dikte_mm"], rc_bron=dak_rc,
                               opmerkingen="HELLINGSHOEK/dakvlakken ONTBREKEN -> dak-m2 = footprint (fallback)"))
        notes.append("Dak: geen hellingshoek/dakvlakken in de opname -> footprint-fallback. Voeg dak-velden toe "
                     "(Dak vloerbreedte/nokhoogte/knieschothoogte of Hellingshoek dak + oriëntaties schuine zijden).")

    # AANBOUW-DAK-CHECK (Essenhage-les 15-7): is de begane grond fors groter dan het grondoppervlak dat
    # het hoofddak overspant, dan steekt er een aanbouw/uitbouw uit met een EIGEN (meestal plat) dak.
    # Is dat niet apart ingevoerd, dan ontbreekt dat dakoppervlak (EPA telde bij Essenhage ~10 m² extra).
    if footprint_bg and dak_fp and (footprint_bg - dak_fp) > 5 and not _heeft_plat_dak:
        notes.append("MOGELIJK DAK ONTBREEKT: de begane grond (%.1f m²) is ~%.1f m² groter dan het "
                     "grondoppervlak dat het hoofddak overspant (%.1f m²) — er lijkt een aanbouw/uitbouw "
                     "met een EIGEN dak te zijn (bv. een bijkeuken). Voer dat als 'Extra dak A' (meestal "
                     "plat) in, anders ontbreekt dat dakoppervlak in de berekening."
                     % (footprint_bg, footprint_bg - dak_fp, dak_fp))

    # DAKRAMEN-sectie (13-7, losgekoppeld van de daken): per ORIENTATIE (9) x glastype -> kozijn
    # subtype Dakraam; glas-m2 wordt afgetrokken van het dakvlak met die orientatie (anders note).
    for _ori in ("N", "NO", "O", "ZO", "Z", "ZW", "W", "NW", "Horizontaal"):
        _o = "" if _ori == "Horizontaal" else _ori
        _an = _f(G("Dakramen %s - aantal (optioneel)" % _ori))
        for _gt in ("Enkel", "Dubbel", "HR", "HR+", "HR++", "TripleHR", "Onbekend"):
            _m = _f(G("Dakramen %s - %s (m²)" % (_ori, _gt)) or G("Dakramen %s - %s (m2)" % (_ori, _gt)))
            if not _m:
                continue
            _vlak = next((s2 for s2 in schil if s2.type == "dak" and (s2.orientatie or "") == _o
                          and (s2.oppervlakte_m2 or 0) > 0), None)
            schil.append(SchilDeel(id="dakraam-%s-%s" % (_ori.lower()[:4], _gt.lower().replace("+", "p")),
                type="kozijn", subtype="Dakraam", begrenzing="Buitenlucht", orientatie=_o,
                oppervlakte_m2=_m, glastype=_gt, kozijnmateriaal="Hout of kunststof",
                hellingshoek=(_vlak.hellingshoek if _vlak else None),
                opmerkingen="dakraam (%s, %s) — in Vabi als raam op het dakvlak" % (_ori, _gt)))
            # NIET hier van het dakvlak aftrekken (audit-glas-F1 15-7): het dakraam is een apart
            # kozijn-SchilDeel (subtype Dakraam) en wordt in Vabi als DEELVLAK op het dakvlak geplaatst
            # -> de netto-aftrek gebeurt daar 1x (net als een raam in een gevel). Parser + objecten
            # trokken het glas allebei af -> dak-oppervlak dubbel verlaagd (te laag). Dak blijft BRUTO.
            if not _vlak:
                notes.append("Dakramen %s (%s, %.1f m2): geen dakvlak met die orientatie -> het dakraam "
                             "komt in Vabi mogelijk op een gevel; controleer het dak in Vabi." % (_ori, _gt, _m))
        _rr = _f(G("Dakramen %s - met ventilatierooster (aantal, leeg = geen)" % _ori))
        if _rr:
            notes.append("Dakramen %s: %d met VENTILATIEROOSTER -> telt als toevoervoorziening; "
                         "neem mee in het ventilatieplan/Vabi." % (_ori, int(_rr)))

    # kozijnen (ramen): erven begrenzing + oriëntatie van de moederwand (parent/child); kozijn A/B/C
    _n_koz_afw = sum(1 for k in kozijnen if k.get("kozijn_hk", "") == "?afwijkend")
    if _n_koz_afw:
        notes.append(
            "KOZIJNMATERIAAL ONBEKEND bij %d kozijn(en): de opname zegt 'afwijkend (anders dan hout/"
            "kunststof)', maar het MagicPlan-formulier vraagt NIET welk materiaal. Zet het type zelf in "
            "Vabi — metaal MET thermische onderbreking (Ufr 3,8) of ZONDER (Ufr 7,0) scheelt fors in de "
            "Uw (NTA 8800 tabel 8.3). De tool vult hier bewust niets in i.p.v. hout/kunststof aan te "
            "nemen (dat is juist het gunstigste type)." % _n_koz_afw)
    for i, k in enumerate(kozijnen):
        # Nij Begun opname-handleiding: kleine ruiten < 0,65 m2 ALTIJD rekenen als 0,65 m2
        area = k["area"] or 0.0
        klein = 0 < area < 0.65
        schil.append(SchilDeel(
            id="raam-%d" % (i + 1), type="kozijn", subtype="Raam",
            begrenzing=k.get("begr", "Buitenlucht"),
            orientatie=k["orient"], oppervlakte_m2=(0.65 if klein else area),
            glastype=_norm_glaslabel(k["glas"]), kozijnmateriaal=_norm_kozijn_mat(k.get("kozijn_hk", "")),
            zonwering=k.get("zonwering", ""),
            opmerkingen=(("klein raam %.2f m2 -> 0,65 m2 (Nij Begun-regel)" % area if klein else "")
                         + ("" if k["glas"] else " GLASTYPE ONTBREEKT")
                         + (" | zonwering/luik: %s (NTA 8.2.2.3.4 -> zet 'm in Vabi bij het raam)"
                            % k["zonwering"] if k.get("zonwering") and
                            not k["zonwering"].lower().startswith("nee") else "")).strip()))
    # panelen-in-kozijn: dichte constructie (ConstructieType=1), zelfde isolatie-beslisschema als een gevel.
    # De CSV geeft geen Rc/isolatie voor het venster -> isolatie Onbekend (forfaitair via bouwjaar); de
    # adviseur verfijnt Rc/isolatie in de webapp-opname of in Vabi.
    for i, p in enumerate(panelen):
        schil.append(SchilDeel(
            id="paneel-%d" % (i + 1), type="paneel", subtype="Paneel",
            begrenzing=p.get("begr", "Buitenlucht"), orientatie=p["orient"],
            oppervlakte_m2=p["area"] or 0.0, isolatie_aanwezig=p.get("isolatie", "Onbekend"),
            isolatiedikte_mm=p.get("dikte"),
            # F5 (15-7): de paneel-bouwjaarklasse OOK op het SchilDeel zetten, zodat de constructie-keuze
            # forfaitair op de paneel-eigen klasse rekent i.p.v. op het project-bouwjaar.
            bouwjaarklasse=p.get("bouwjaarklasse", ""),
            opmerkingen=("paneel-in-kozijn (dichte constructie) -> verifieer Rc/isolatie in Vabi"
                         + (" · bouwjaarklasse %s" % p["bouwjaarklasse"]
                            if p.get("bouwjaarklasse") else ""))))
    if roosters_tel:
        notes.append("%d kozijn(en)/deur(en) met TOEVOERROOSTER -> toevoervoorziening voor het "
                     "ventilatieplan; beoordeel zelf of ze zelfregelend zijn (Vabi-subsysteem)."
                     % roosters_tel)
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
            glastype=_norm_glaslabel(d["glas"]), kozijnmateriaal="Hout of kunststof",
            deur_met_raam_glas65=met_raam))
    # per-bouwdeel BOUWJAARKLASSE (beslisschema): het form-antwoord ("Gevel - bouwjaar (onbekend)"
    # = bv. 'Van 1975 t/m 1982') moet de constructie-keuze sturen — zonder dit viel de keuze terug
    # op het project-bouwjaar (en bij een lege export op 'Tot 1965': live gezien, 12-7).
    _klasse_per_type = {"gevel": g_b["bouwjaar"], "vloer": v_b["bouwjaar"], "dak": d_b["bouwjaar"]}
    for s in schil:
        if not getattr(s, "bouwjaarklasse", ""):
            # per-dak klasse-antwoord wint op de vlakken van dat dak (id-prefix dak1-/dak2-/dak3-)
            if s.type == "dak":
                for _n, _k in dak_klasse.items():
                    if s.id.startswith("dak%d-" % _n) and _k:
                        s.bouwjaarklasse = _k
                        break
            if not s.bouwjaarklasse:
                k = _klasse_per_type.get(s.type, "")
                if k:
                    s.bouwjaarklasse = k
    dos.schil = schil
    # VERSHEID: toon de projectdatum bovenaan, zodat je nooit per ongeluk een oude export analyseert
    # (Essenhage-les 15-7: een CSV van 11-7 toonde nog oude geveltags terwijl MagicPlan al gecorrigeerd was).
    _pdatum = _undot(G("Project creation date") or G("Projectdatum"))
    if _pdatum:
        notes.append("Deze opname komt uit een MagicPlan-export met projectdatum %s. Klopt dit niet met je "
                     "laatste wijzigingen? Exporteer dan een VERSE Statistics-CSV en laad die opnieuw." % _pdatum)
    if not dos.identificatie.bouwjaar:
        notes.append("BOUWJAAR ONTBREEKT in de export (Object-form 'Bouwjaar' — oudere formversie? "
                     "Herstart de MagicPlan-app en exporteer opnieuw, of vul het bouwjaar in de webapp "
                     "in). Zonder bouwjaar kan Vabi niet forfaitair rekenen.")
    # TIKFOUT-CHECKS (Essenhage-vergelijking 14-7: gevel was +26% door precies deze twee fouten).
    # Puur signaleren — de tool corrigeert NOOIT zelf (geen aannames).
    # (1) twee EVENWIJDIGE wanden in dezelfde kamer allebei als dezelfde gevel getikt (Wall 1 + Wall 3
    #     met gelijke breedte): een kamer heeft maar één wand op een gevel -> m² telt dubbel.
    from collections import defaultdict as _dd
    _per_kamer_ori = _dd(list)
    for t in gevel_tikken:
        # kamernamen zijn niet uniek (3x 'Bedroom') -> kamer_id (uniek per blok) in de sleutel
        _per_kamer_ori[(t["kamer_id"], t["kamer"], t["orient"])].append(t)
    for (_kid, _km, _ori), _ts in _per_kamer_ori.items():
        _vd = _ts[0].get("verdieping", "")
        if len(_ts) < 2:
            continue
        _breedtes = [round(t["breedte"], 1) for t in _ts if t["breedte"]]
        _dubbel = {b for b in _breedtes if _breedtes.count(b) >= 2}
        # gelijke-breedte dubbels (Wall 1 // Wall 3) zijn AL door de dedup 1x geteld -> geen aparte
        # tikfout-note meer (die sprak de dedup-note tegen). Alleen de VERSCHILLENDE-breedte dubbels
        # blijven onopgelost (kan een echte knik zijn of een tikfout) -> LET OP.
        _verschillend = len(set(_breedtes)) >= 2
        if _verschillend:
            notes.append("LET OP kamer '%s'%s: %d wanden als gevel %s getikt (breedtes %s m). Klopt dat "
                         "(geknikte/L-vormige gevel), of is het dubbel? Eén rechte gevel = één wand per "
                         "kamer — of vul de gemeten gevelbreedte in (dan negeert de tool de wandsom)."
                         % (_km, (" (%s)" % _vd if _vd else ""), len(_ts), _ori,
                            "/".join("%.1f" % b for b in _breedtes)))
    # ONMOGELIJKE HOEK (Essenhage-Laundry-les 15-7): TEGENOVERLIGGENDE wanden (Wall 0//Wall 2 of
    # Wall 1//Wall 3) van één kamer moeten 180° uit elkaar liggen (voor/achter of links/rechts).
    # Zijn ze getagd op oriëntaties die 90° apart liggen, dan is één tag zeker MISGETIKT.
    _perkamer = _dd(dict)      # kamer_id -> {wandnr: (orient, kamer, verdieping)}
    for _t in gevel_tikken:
        if _t.get("wandnr") is not None and _t["orient"] in map(str.upper, _COMPAS):
            _perkamer[_t["kamer_id"]][_t["wandnr"]] = (_t["orient"], _t["kamer"], _t.get("verdieping", ""))
    for _kid, _wd in _perkamer.items():
        for _a, _b in ((0, 2), (1, 3)):
            if _a in _wd and _b in _wd:
                _oa, _ob = _wd[_a][0], _wd[_b][0]
                _stap = abs(_COMPAS.index(_oa.lower()) - _COMPAS.index(_ob.lower())) % 8
                if _stap not in (0, 4):     # niet gelijk en niet 180° -> onmogelijk voor een rechthoek
                    notes.append("TIKFOUT (onmogelijke hoek) kamer '%s'%s: Wall %d = %s én Wall %d = %s, "
                                 "maar dat zijn TEGENOVERLIGGENDE wanden (moeten 180° uit elkaar, dus "
                                 "voor/achter óf links/rechts). Eén van deze twee is misgetikt — "
                                 "controleer in MagicPlan."
                                 % (_wd[_a][1], (" (%s)" % _wd[_a][2]) if _wd[_a][2] else "",
                                    _a, _oa, _b, _ob))
    # (1b) DUBBELTEL-CHECK (Essenhage-les 15-7): voor/achter overspannen dezelfde huisbreedte,
    #      links/rechts dezelfde huisdiepte. Wijkt op één verdieping de getikte breedte van een
    #      oriëntatie sterk af van de TEGENOVERLIGGENDE gevel, dan staat er waarschijnlijk een wand
    #      DUBBEL (bv. 3x dezelfde badkamer op de voorgevel: 1e verd. 9,44 m vs achtergevel 5,71 m).
    #      Puur signaleren; de tool corrigeert niets (geen aannames).
    _orient_bxh = {_ref["orient"]: _ref["bxh"] for _ref in gevel_refs if _ref.get("orient")}
    _gemeld_dt = set()
    for _o, _bx in _orient_bxh.items():
        if _o.lower() not in _COMPAS:
            continue
        _opp_o = _COMPAS[(_COMPAS.index(_o.lower()) + 4) % 8].upper()
        _opp_bx = _orient_bxh.get(_opp_o, {})
        for _vd, _br in _bx.items():
            _ref_br = _opp_bx.get(_vd)
            if _ref_br and _br > 1.25 * _ref_br and (_o, _vd) not in _gemeld_dt:
                _gemeld_dt.add((_o, _vd))
                notes.append("LET OP mogelijke DUBBELTEL: gevel %s is op '%s' %.2f m breed, maar de "
                             "TEGENOVERLIGGENDE gevel %s daar %.2f m — voor/achter (en links/rechts) "
                             "horen even breed te zijn. Staat dezelfde wand er meerdere keer (bv. een "
                             "kamer die meermaals is getekend/gekopieerd)? Controleer dat, of vul de "
                             "gemeten gevelbreedte van deze gevel in ('<gevel> - breedte (m)') zodat "
                             "de tool de wandsom negeert."
                             % (_o, _vd, _br, _opp_o, _ref_br))
    # (2) ZOLDER-UITSLUITING (eis Renze 14-7): op de bovenste verdieping onder een SCHUIN dakvlak is
    #     de voor/achtergevel het DAK zelf, geen verticale gevel. Die verdieping halen we automatisch
    #     uit de gevel-m² voor de oriëntaties die een schuin dakvlak hebben; de echte KOPGEVELS (haaks
    #     op de nok, andere oriëntatie) blijven wél gevel. De opbouw-note per gevel komt hier (nu is
    #     bekend welke oriëntatie schuin dak is).
    _verd_volgorde = [v.naam for v in geo.vloeren]
    _top_verd = _verd_volgorde[-1] if _verd_volgorde else ""
    _schuin_oris = {s.orientatie for s in schil if s.type == "dak" and (s.hellingshoek or 0) > 0 and s.orientatie}
    for _ref in gevel_refs:
        _s, _ori, _bxh = _ref["s"], _ref["orient"], _ref["bxh"]
        _excl = {vd for vd in _bxh if _ori in _schuin_oris and vd == _top_verd}
        _counted = {vd: br for vd, br in _bxh.items() if vd not in _excl}
        _opp = round(sum(br * verd_hoogte[vd] for vd, br in _counted.items()), 2)
        _s.oppervlakte_m2 = _opp
        _opbouw = " + ".join("%s %.2fx%.2f" % (vd, br, verd_hoogte[vd]) for vd, br in sorted(_counted.items())) or "—"
        _n = ("Gevel %s (%s): %s = %.2f m² BRUTO (breedte x verdiepingshoogte; ramen/deuren = deelvlak "
              "in Vabi)." % (_ori, orient_naam.get(_ori, "?"), _opbouw, _opp))
        if _excl:
            _weg = round(sum(_bxh[vd] * verd_hoogte[vd] for vd in _excl), 2)
            _n += (" ZOLDER %s (%.2f m²) NIET meegeteld: daar is de gevel het SCHUINE DAKVLAK (zit al in "
                   "het dak). Alleen echte kopgevels tellen op zolder." % ("/".join(sorted(_excl)), _weg))
            _s.opmerkingen += " | zolder %s uit gevel gehouden (schuin dak)" % "/".join(sorted(_excl))
            if not _counted:
                _n += (" LET OP: deze gevel bestaat ALLEEN uit zolder -> nu 0 m²; klopt dat (volledig "
                       "onder het schuine dak), of hoort er een lagere verdieping bij?")
        notes.append(_n)
    # TRANSPARANTIE-flags (geen aannames-verhulling): gevel = breedte x verdiepingshoogte per bouwlaag
    # (BRUTO; ramen/deuren gaan er in Vabi als deelvlak af); dak = footprint / cos(helling). Beide zijn
    # een STARTPUNT — controleer de opbouw-notes hierboven (breedte per verdieping) op tikfouten en
    # corrigeer per bouwdeel in Vabi.
    _gevel_tot = round(sum((s.oppervlakte_m2 or 0) for s in schil if s.type == "gevel"), 1)
    _dak_tot = round(sum((s.oppervlakte_m2 or 0) for s in schil if s.type == "dak"), 1)
    if _gevel_tot:
        notes.append("GEVEL-m² = %.1f m² BRUTO (breedte x verdiepingshoogte per bouwlaag; ramen/deuren "
                     "= deelvlakken in Vabi). Loop de opbouw-note per gevel na op te brede verdiepingen "
                     "(= dubbel getikt)." % _gevel_tot)
    if _dak_tot:
        notes.append("DAK-m² = %.1f m² (afgeleid: footprint / cos(helling)). Hangt volledig aan de "
                     "ingevoerde hellingshoek en footprint — controleer beide en het dak-m² in Vabi." % _dak_tot)

    # ---- installaties ----
    vsys = _undot(G("Ventilatiesysteem (A-E)"))      # 'A Natuurlijke ventilatie'
    # subsysteem nu conditioneel per type: 'Subsysteem (A)'..'(E)' (whichever gevuld); oude platte = fallback
    sub = (_undot(G("Subsysteem (A)")) or _undot(G("Subsysteem (B)")) or _undot(G("Subsysteem (C)"))
           or _undot(G("Subsysteem (D)")) or _undot(G("Subsysteem (E)")) or _undot(G("Subsysteem (zie type)")))
    dos.ventilatie = Ventilatie(
        systeem=(vsys.split()[0] if vsys else ""),
        systeem_soort=_undot(G("Systeem (ventilatie)")),
        subsysteem_code=(sub.split()[0] if sub else ""))
    if not dos.ventilatie.systeem:
        notes.append("VENTILATIESYSTEEM (A-E) ONTBREEKT in de opname — dit stuurt de Standaard! "
                     "Vul het veld in MagicPlan/de webapp in; anders houdt de VABI-installatiebib "
                     "de sjabloon-ventilatie.")
    inst = Installaties()
    # G2: probeer meerdere naamvarianten (MagicPlan-form gebruikt '-', oude form had en-dash '–')
    def G2(*namen):
        for n in namen:
            v = _undot(G(n))
            if v:
                return v
        return ""
    # Aanvoertemperatuur is geen categorische tekstwaarde: MagicPlan exporteert
    # de slash in bv. 90/70 als punt. Bewaar die punt voor de gerichte
    # normalisatie in installatie_generate.py in plaats van hem via _undot()
    # onherstelbaar in een spatie te veranderen.
    def G2_raw(*namen):
        for n in namen:
            v = (G(n) or "").strip()
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
            aanvoertemperatuur=G2_raw("Verwarming - aanvoertemperatuur",
                                     "Verwarming – aanvoertemperatuur"),
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
        _dwtw = G2("Douche-WTW (DWTW) aanwezig?", "DWTW aanwezig?").strip().lower()
        inst.tapwater = Tapwater(type_installatie="Individueel", type_toestel=tw,
                                 installatiejaar=_int2(G2("Tapwater - installatiejaar")),
                                 # NTA 8800 bijlage U: douche-WTW verlaagt de tapwaterbehoefte fors
                                 dwtw_aanwezig=(True if _dwtw.startswith("ja")
                                                else (False if _dwtw.startswith("nee") else None)))
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
            aantal=aant, oppervlak_per_paneel_m2=_f(G2(detail_prefix + "oppervlak per paneel (m2)")),
            # beschaduwing (NTA 8800 §17.3) — Vabi rekent de reductie, wij leggen de waarneming vast
            belemmering=(True if G2(detail_prefix + "belemmering/beschaduwing?",
                                    "PV - belemmering/beschaduwing?").strip().lower().startswith("ja")
                         else None))
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
            oppervlak_per_paneel_m2=_f(G2("PV - oppervlak per paneel (m2)")),
            # beschaduwing (NTA 8800 §17.3) — Vabi rekent de reductie, wij leggen de waarneming vast
            belemmering=(True if G2("PV - belemmering/beschaduwing?").strip().lower().startswith("ja")
                         else None))]
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
        notes.append("Woningtype ONTBREEKT -> infiltratie-positie onbekend; ook geen hart-op-hart-"
                     "toeslag-melding mogelijk (voeg 'Woningtype' toe in MagicPlan, zet de positie in Vabi).")
    if dos.opname.qv10_waarde is not None and not dos.opname.qv10_gemeten:
        notes.append("qv10 %.2f staat ingevuld maar 'Qv10 gemeten?'=Nee (ISSO 7.1.5: alleen meenemen als "
                     "GEMETEN met blowerdoor; anders rekent VABI forfaitair op bouwjaar/renovatiejaar)." % dos.opname.qv10_waarde)
    # thermische massa: codes 0=Licht/1=Zwaar/2=Zeer zwaar zijn live in EPA bevestigd (22-6-2026) en
    # worden automatisch geschreven door objecten_generate. LET OP (audit 15-7): een LEGE thermische
    # massa wordt daar LUID geflagd (de sjabloonwaarde is 'Zwaar' — fout bij een lichte constructie).
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
        notes.append("Kwaliteitsverklaring geselecteerd voor: %s. De VABI-export wordt geblokkeerd; "
                     "verwerk de kwaliteitsverklaring eerst correct in Vabi." % ", ".join(kwv))
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
