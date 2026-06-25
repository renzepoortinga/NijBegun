"""
Canoniek dossier -> NTA8800-monitoringbestand (XML) voor import in Vabi EPA-W.

AANPAK (juni 2026): we bouwen de XML NIET meer zelf op, maar enten op een ECHT Vabi-
monitorbestand als sjabloon (vabi/monitor_template.xml = een echte EPA-W-export). We
vervangen alleen de DATA (identificatie, oppervlaktes, constructiedelen) met die uit het
dossier en laten de rest van de structuur exact intact -> de import kan niet meer struikelen
op afwijkende structuur/versie. Installaties + rekenresultaten komen vooralsnog uit het
sjabloon (Vabi herrekent bij import; adviseur verifieert/vult installaties aan).

    python vabi/monitor_generate.py --dossier dossier.json --out out/import_monitor.xml
"""
import os, sys, argparse
from lxml import etree
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.dossier import Dossier, load_json  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "monitor_template.xml")

# losse identificatie-velden -> dossierwaarde (per localname)
# oppervlakte-velden krijgen allemaal Ag (de woning-oppervlakte)
AREA_TAGS = {"SurfaceArea", "EffectiveSurfaceArea", "Gebruiksoppervlakte", "AangeslotenOppervlak"}


def L(e):
    return etree.QName(e).localname


def _num(v, fmt="%.2f"):
    return fmt % v if isinstance(v, (int, float)) else "0.00"


def _begrenzing(b):
    b = (b or "").lower()
    if "kruip" in b:
        return "Kruipruimte"
    if "grond" in b:
        return "Grond"
    return "Buiten"   # buitenlucht + onbekend -> veilige geldige enum


def _beglazing(g):
    g = (g or "").lower()
    for k, v in (("hr++", "HR++"), ("triple", "HR++"), ("hr+", "HR++"), ("hr", "HR++"),
                 ("dubbel", "Dubbel"), ("enkel", "Enkel")):
        if k in g:
            return v
    return "Dubbel"


def _kozijnmateriaal(m):
    m = (m or "").lower()
    return "Metaal" if ("metaal" in m or "alu" in m or "mto" in m) else "Hout/kunststof"


def _orientatie(s):
    if s.type in ("vloer", "dak"):
        return "horizontaal"
    o = (s.orientatie or "").upper()
    if o in ("NO", "NW", "ZO", "ZW"):
        return o
    return {"N": "NW", "O": "NO", "Z": "ZO", "W": "ZW"}.get(o, "ZW")


def _vlaktype(s):
    if s.type == "kozijn":
        return "dak" if "dak" in (s.subtype or "").lower() else "gevel"
    return s.type or "gevel"


def _omschrijving(s):
    # neutrale omschrijving (Vabi kan de Omschrijving als template-naam valideren)
    return {"gevel": "Gevel", "vloer": "Vloer", "dak": "Dak", "kozijn": "Raam"}.get(s.type, "Gevel")


def _sub(parent, ns, tag, text=None):
    el = etree.SubElement(parent, "{%s}%s" % (ns, tag) if ns else tag)
    if text is not None:
        el.text = str(text)
    return el


def _add_constructiedeel(cds, s, i, ns):
    cd = etree.SubElement(cds, "{%s}Constructiedeel" % ns if ns else "Constructiedeel")
    cd.set("id", str(900000 + i))
    _sub(cd, ns, "Omschrijving", _omschrijving(s))
    _sub(cd, ns, "Begrenzing", _begrenzing(s.begrenzing))
    _sub(cd, ns, "Hellingshoek", "0" if s.type in ("vloer", "dak") else "90")
    _sub(cd, ns, "Orientatie", _orientatie(s))
    _sub(cd, ns, "Oppervlakte", _num(s.oppervlakte_m2))
    _sub(cd, ns, "Vlaktype", _vlaktype(s))
    if s.type == "kozijn":
        raam = _sub(cd, ns, "Raam")
        _sub(raam, ns, "U", _num(s.u_huidig) if s.u_huidig is not None else "2.90")
        _sub(raam, ns, "g", "0.60")
        _sub(raam, ns, "Beglazing", _beglazing(s.glastype))
        _sub(raam, ns, "Kozijnmateriaal", _kozijnmateriaal(s.kozijnmateriaal))
        _sub(raam, ns, "ZonweringAutomatisch", "0")
    else:
        dicht = _sub(cd, ns, "Dicht")
        _sub(dicht, ns, "Rc", _num(s.rc_huidig) if s.rc_huidig is not None else "1.30")
        _sub(dicht, ns, "Isolatiedikte",
             _num(s.isolatiedikte_mm, "%g") if s.isolatiedikte_mm is not None else "0")
        _sub(dicht, ns, "DikteRietpakket", "0.00")


def build_tree(dos: Dossier):
    root = etree.parse(TEMPLATE).getroot()
    ag = _num(dos.geometrie.gebruiksoppervlakte_ag_m2)
    idf = dos.identificatie
    repl = {
        "BAGResidenceId": idf.bag_vboid or "", "ZipCode": idf.postcode or "",
        "Postcode": idf.postcode or "", "Number": idf.huisnummer or "",
        "Huisnr": idf.huisnummer or "", "ConstructionYear": str(idf.bouwjaar or ""),
        "Straatnaam": idf.straat or "", "Plaatsnaam": idf.plaats or "",
    }
    for e in root.iter():
        ln = L(e)
        if ln in repl:
            e.text = repl[ln]
        elif ln in AREA_TAGS:
            e.text = ag
    # constructiedelen vervangen door die uit het dossier
    for cds in root.iter():
        if L(cds) == "Constructiedelen":
            ns = etree.QName(cds).namespace
            for ch in list(cds):
                cds.remove(ch)
            for i, s in enumerate(dos.schil, 1):
                _add_constructiedeel(cds, s, i, ns)
            break
    return root


def to_xml(dos: Dossier) -> bytes:
    # declaratie met DUBBELE quotes, exact als het echte monitorbestand
    body = etree.tostring(build_tree(dos), pretty_print=True, encoding="utf-8",
                          xml_declaration=False)
    return b'<?xml version="1.0" encoding="UTF-8"?>\n' + body


def write(dos: Dossier, path: str):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(to_xml(dos))
    return path


def main():
    root_dir = os.path.dirname(HERE)
    ap = argparse.ArgumentParser(description="Dossier -> VABI monitoring-XML (sjabloon-invulling)")
    ap.add_argument("--dossier", required=True)
    ap.add_argument("--out", default=os.path.join(root_dir, "out", "import_monitor.xml"))
    a = ap.parse_args()
    dos = load_json(a.dossier)
    write(dos, a.out)
    print("OK: " + a.out)
    print("  %d constructiedelen | %s %s | bouwjaar %s (op echt monitorbestand-sjabloon)" % (
        len(dos.schil), dos.identificatie.postcode, dos.identificatie.huisnummer,
        dos.identificatie.bouwjaar))
    print("  LET OP: installaties/resultaten komen nog uit het sjabloon; Vabi herrekent bij import.")


if __name__ == "__main__":
    main()
