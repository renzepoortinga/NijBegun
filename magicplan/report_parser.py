"""
MagicPlan project-REPORT (PDF) -> form-antwoorden.

Ontdekking (juni 2026): de REST-API levert wel de geometrie maar NIET de ingevulde
custom-form-antwoorden. Die zitten wél in de project-report-PDF (Export), in een strak
'label-regel / waarde-regel'-formaat. Deze parser leest die uit -> {schema_key: waarde},
plus de per-raam kozijn-blokken. Samen met de API-geometrie (extractor.py) vormt dit het
volledige dossier (hybride).

Gebruik:
    python magicplan/report_parser.py --pdf "Oosterkade 23 Report.pdf"
"""
import os, sys, re, json, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


# PDF-label (genormaliseerd) -> canonieke veld-key (zelfde keys als extractor/schema)
LABEL_TO_KEY = {
    "bag verblijfsobject-id": "bag_vboid", "postcode": "postcode",
    "huisnummer (+toev.)": "huisnummer", "bouwjaar": "bouwjaar",
    "renovatiejaar (schil)": "renovatiejaar", "woningtype": "woningtype",
    "type advies": "type_advies", "gebruiksoppervlak ag [m2]": "ag_m2",
    "aantal bouwlagen": "bouwlagen", "qv;10 gemeten?": "qv10_gemeten",
    "qv;10 waarde [dm3/(s.m2)]": "qv10_waarde", "bewijslast isolatie": "bewijslast",
    # ventilatie
    "systeem (soort)": "vent_systeem_soort", "ventilatiesysteem": "vent_systeem",
    "co2-sturing aanwezig?": "vent_co2",
    "zelfregelende/vraaggestuurde roosters?": "vent_zelfregelend",
    "tijdsturing aanwezig?": "vent_tijdsturing",
    "passieve koeling via ventilatie?": "vent_passieve_koeling",
    "kwaliteitsverklaring (vla) aanwezig?": "vent_kwaliteitsverklaring",
    "vabi-subsysteemcode (indien bekend, bv. a1/c4b)": "vent_subsysteem_code",
    # gevel (algemeen)
    "constructietype gevel": "geveltype", "spouw aanwezig?": "spouw_aanwezig",
    "spouwbreedte [mm]": "spouw_mm", "begrenzing hoofdgevels": "gevel_begrenzing",
    "gevel - isolatie aanwezig?": "isolatie_aanwezig", "gevel - bepaling rc": "rc_bron",
    "gevel - isolatiedikte [mm]": "isolatie_mm", "afwijkende geveldelen": "gevel_afwijking",
    # vloer & dak (algemeen)
    "vloerconstructie": "vloerconstructie", "begrenzing vloer": "vloer_begrenzing",
    "vloer - isolatie aanwezig?": "vloer_iso", "vloer - bepaling rc": "vloer_rc_bron",
    "vloer - isolatiedikte [mm] (indien opgemeten)": "vloer_isolatie_mm",
    "kruipruimte diepte [cm]": "kruipruimte_diepte",
    "daktype": "daktype", "dak - isolatie aanwezig?": "dak_iso",
    "dak - bepaling rc": "dak_rc_bron", "rieten dak?": "rietdak",
    "dakhelling [graden]": "dakhelling", "dakoppervlak [m2] (handmatig)": "dak_oppervlak_m2",
    # kierdichting
    "v6 kierdichting - huidige staat": "kierdichting",
    # technische haalbaarheid
    "asbestverdenking?": "asbest", "loden leidingen aanwezig?": "lood",
    "bereikbaarheid": "bereikbaarheid", "obstakels": "obstakels",
    "vochtproblematiek geconstateerd?": "vocht",
    # installaties (energielabel-opname)
    "type opwekker": "verw_type_opwekker", "subtype": "verw_subtype",
    "afgiftesysteem": "verw_afgifte", "wateraanvoertemperatuur": "verw_aanvoertemp",
    "type toestel": "tap_type_toestel", "cw-klasse": "tap_cw_klasse",
}
# per-raam kozijn-velden (komen herhaald voor)
KOZIJN_LABELS = {"element": "element", "kozijnmateriaal": "kozijnmateriaal",
                 "beglazingstype": "glastype", "u-waarde glas [w/m2k]": "u_glas",
                 "u-waarde kozijn [w/m2k]": "u_kozijn"}
# regels die we overslaan (kopteksten/secties/ruis)
SKIP = re.compile(r"^(page \d+/\d+|oosterkade.*|projectgegevens|ventilatie|gevels|"
                  r"vloer & dak|kierdichting|kozijnen|technische haalbaarheid.*|installaties|"
                  r".*\(see photos page\))$", re.I)


def extract_text(pdf_path):
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join((pg.extract_text() or "") for pg in pdf.pages)


def parse(pdf_path):
    return parse_text(extract_text(pdf_path))


def parse_text(text):
    """Geef (project_answers{key:waarde}, kozijnen[list of {key:waarde}]) uit platte report-tekst."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    answers, kozijnen, cur = {}, [], None
    i = 0
    while i < len(lines):
        label = _norm(lines[i])
        # waarde = eerstvolgende regel die geen bekend label is en geen ruis
        val = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if label in KOZIJN_LABELS:
            if label == "element":          # nieuw kozijn-blok
                cur = {}; kozijnen.append(cur)
            if cur is not None and not SKIP.match(val):
                cur[KOZIJN_LABELS[label]] = val
            i += 2; continue
        if label in LABEL_TO_KEY:
            if not SKIP.match(val):
                answers[LABEL_TO_KEY[label]] = val
            i += 2; continue
        i += 1
    return answers, kozijnen


def main():
    ap = argparse.ArgumentParser(description="MagicPlan report-PDF -> form-antwoorden")
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    answers, kozijnen = parse(a.pdf)
    print("PROJECT-ANTWOORDEN (%d velden):" % len(answers))
    for k, v in answers.items():
        print("  %-22s = %s" % (k, str(v).encode("ascii", "replace").decode()[:50]))
    print("\nKOZIJNEN (%d):" % len(kozijnen))
    from collections import Counter
    glas = Counter(z.get("glastype", "?") for z in kozijnen)
    print("  beglazing-verdeling:", dict(glas))
    if a.out:
        json.dump({"project": answers, "kozijnen": kozijnen},
                  open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print("\n-> " + a.out)


if __name__ == "__main__":
    main()
