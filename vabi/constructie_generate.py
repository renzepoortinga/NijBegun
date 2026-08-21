"""
Dossier -> VABI Constructiebibliotheek-XML (importeerbaar via EPA-tegel Constructies > Importeren).

GARANTIE-OP-IMPORT-ONTWERP: we verzinnen NOOIT zelf veldwaarden. We starten van een ECHTE
VABI-export (vabi/refs/standaard_constructies_*.xml = 219 standaard-constructies, per definitie
geldig) en kiezen per dossier-schildeel de best passende standaard-constructie. Elke uitgevoerde
<Constructie> is een LETTERLIJKE KLOON van een door-VABI-gekende constructie (alleen Guid + Naam
worden ververst). Daardoor kan de import niet struikelen op 'enum mismatch'.

De 219 = EPA's VOLLEDIGE forfaitaire Standaard-constructies-set (LIVE geverifieerd 19-7-2026: EPA's
knop "Standaard constructies" laadt exact 219 — 1-op-1 met deze template). Dimensies: opaak (gevel/
dak/vloer) isolatie-onbekend + 10..230 mm in 10mm-stappen x met/zonder spouw; glas 7 types (enkel/
dubbel/HR/HR+/HR++/TripleHR/voorzet) x 3 kozijnmaterialen; deur geisoleerd/niet; paneel 10..100 mm.
Een GEMETEN/afwijkende Rc/U hoort niet bij een forfaitaire preset en wordt geflagd. Een expliciete
kwaliteitsverklaring blokkeert de export volledig, zodat die nooit als rekenbare forfaitaire preset
kan belanden. De adviseur verwerkt de verklaring correct in Vabi; de tool gokt geen Rc/U-waarde.

De constructiebibliotheek bevat alleen constructie-TYPES (Rc/isolatie/glas), geen oppervlak/
orientatie -> die geometrie komt later in de Objectenbibliotheek. We leveren dus de UNIEKE set
types die de woning nodig heeft, plus een mapping schildeel->constructienaam voor de Objecten-stap.

    python vabi/constructie_generate.py --dossier out/dossier.json --out out/Constructiebibliotheek.xml

Harde validatie-poort: vóór schrijven controleert de tool dat elke enum-waarde in de door-VABI-
bekende set zit (codebook). Zo niet -> "NIET klaar voor import: ..." en GEEN bestand.
"""
import os, re, sys, copy, uuid, argparse
import xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.dossier import load_json            # noqa: E402
from vabi.codebook import Codebook            # noqa: E402
from vabi.preflight import assert_no_schil_kwaliteitsverklaring, assert_no_dubbel_dak_fallback  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "refs", "standaard_constructies_v120001001.xml")

# dossier-schiltype -> ConstructieType-code (geverifieerd uit de 12.0.1-export)
# 0=Gevel 1=Paneel(in kozijn) 2=Raam/kozijn 3=Deur 4=Dak 7=Vloer
TYPE_CODE = {"gevel": "0", "paneel": "1", "vloer": "7", "dak": "4", "kozijn": "2", "raam": "2", "deur": "3"}
# enum-velden die de poort moet bewaken
GATE_FIELDS = ("ConstructieType", "Glas", "Kozijn", "IsolatieAanwezig", "Bouwjaar",
               "Invoer", "SpouwAanwezig")


def _t(el, tag, default=None):
    c = el.find(tag)
    return c.text if (c is not None and c.text is not None) else default


def _num(s, default=None):
    try:
        return float(s)
    except (TypeError, ValueError):
        return default


class TemplatePool:
    """De 219 standaard-constructies, geparset + per ConstructieType gegroepeerd."""
    def __init__(self, path):
        self.root = ET.parse(path).getroot()
        self.cons = [c for c in self.root.iter() if _local(c.tag) == "Constructie"]
        self.by_type = {}
        for c in self.cons:
            self.by_type.setdefault(_t(c, "ConstructieType"), []).append(c)

    def pick_dicht(self, ctype, isolatie_aanwezig, dikte_mm, spouw, bouwjaarklasse):
        """Kies gevel/dak/vloer: match isolatiemodus + spouw + (dikte of bouwjaarklasse)."""
        cands = self.by_type.get(ctype, [])
        if not cands:
            return None
        # gewenste IsolatieAanwezig-modus
        ja = (isolatie_aanwezig or "").lower()
        if ja in ("ja", "wel") and dikte_mm is not None:
            want_isol, want_dikte = "0", dikte_mm
        elif ja in ("nee", "niet", "geen"):
            want_isol, want_dikte = "1", None
        else:                                   # onbekend/gedeeltelijk -> forfaitair via bouwjaar
            want_isol, want_dikte = "3", None

        # Luchtspouw is alleen relevant bij geen/onbekende of dunne isolatie (<40mm):
        # boven 40mm vervalt de spouw-keuze (ISSO 82.1 / NTA8800). Negeer 'm dan in de match.
        spouw_relevant = (want_isol != "0") or (want_dikte is not None and want_dikte < 40)

        def score(c):
            s = 0
            if _t(c, "IsolatieAanwezig") == want_isol:
                s += 100
            if spouw_relevant and spouw is not None and _t(c, "SpouwAanwezig") == ("1" if spouw else "0"):
                s += 20
            if want_isol == "0" and want_dikte is not None:
                d = _num(_t(c, "Isolatiedikte"))
                if d is not None:
                    s -= abs(d - want_dikte) / 10.0   # dichtste dikte wint
            if want_isol == "3" and bouwjaarklasse is not None:
                if _t(c, "Bouwjaar") == str(bouwjaarklasse):
                    s += 40
            return s
        return max(cands, key=score)

    def pick_raam(self, cb, glastype, kozijnmateriaal):
        cands = self.by_type.get("2", [])
        if not cands:
            return None
        wg = cb.glas_code(_norm_glas(glastype))
        wk = cb.kozijn_code(_norm_kozijn(kozijnmateriaal))

        def score(c):
            s = 0
            if wg is not None and _t(c, "Glas") == wg:
                s += 100
            if wk is not None and _t(c, "Kozijn") == wk:
                s += 50
            return s
        best = max(cands, key=score)
        return best

    def pick_deur(self, isolatie_aanwezig):
        cands = self.by_type.get("3", [])
        if not cands:
            return None
        want = "0" if (isolatie_aanwezig or "").lower() in ("ja", "wel") else "1"
        for c in cands:
            if _t(c, "IsolatieAanwezig") == want:
                return c
        return cands[0]


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _norm_glas(g):
    g = (g or "").lower()
    if "triple" in g or "3-voud" in g or "drie" in g:
        return "triplehr"
    if "voorzet" in g:      # audit-glas-F2 15-7: 'Voorzetglas' matchte de codebook-sleutel 'voorzetraam' niet
        return "voorzetraam"
    if "vacu" in g:
        # VABI-Beslisschema kent geen vacuumglas -> map naar HR++ (dichtstbij, geldig);
        # adviseur verfijnt via U-waarde/kwaliteitsverklaring (zie generator-issues).
        return "hr++"
    # HR-varianten EXPLICIET afvangen, van specifiek naar algemeen. De MagicPlan-optie heet
    # 'HR (dubbel glas met coating)' en bevat dus het woord 'dubbel'; in de codebook-sleutels staat
    # 'dubbel' vóór 'hr', waardoor HR-glas als DUBBEL (code 2) werd ingelezen i.p.v. HR (code 3)
    # -> te ongunstige Ugl. Gevonden op de echte Essenhage-opname (27-7).
    if "hr++" in g or "hr ++" in g:
        return "hr++"
    if "hr+" in g or "hr +" in g:
        return "hr+"
    if "hr" in g:
        return "hr"
    return g


def _norm_kozijn(k):
    k = (k or "").lower()
    if "alu" in k or "mto" in k:
        return "metaal"
    # audit-glas-F5 15-7: 'metaal NIET thermisch onderbroken' bevat 'onderbroken' -> viel op therm.
    # onderbroken (code 3). 'niet' expliciet uitsluiten; niet-TO/plain metaal = code 4.
    if "metaal" in k and "onderbroken" in k and "niet" not in k:
        return "therm. onderbroken metaal"
    if "metaal" in k:
        return "metaal"
    return k


def _classify(s):
    t = (s.type or "").lower()
    if t == "kozijn":
        # deur (incl. deur met raam >=65% glas -> in VABI een deur met de 65%-vlag)
        if getattr(s, "deur_met_raam_glas65", False) or "deur" in (s.subtype or "").lower():
            return "deur"
        return "raam"
    return t


def _jaar_uit_klassetekst(tekst):
    """Bouwjaarklasse-TEKST uit het MagicPlan-form ('Van 1975 t/m 1982', 'Tot 1965', 'Vanaf 2014',
    ook ge-dot 'Van.1975.t.m.1982') -> representatief jaar BINNEN die klasse, of None. De klassen in
    het form zijn 1-op-1 de beslisschema-klassen, dus het middenjaar valt gegarandeerd in de juiste."""
    jaren = [int(j) for j in re.findall(r"(19\d\d|20\d\d)", tekst or "")]
    if not jaren:
        return None
    t = (tekst or "").lower()
    if len(jaren) >= 2:
        return (jaren[0] + jaren[1]) // 2
    if "tot" in t or "voor" in t or "t/m" in t or "t.m" in t:
        return jaren[0] - 1
    return jaren[0] + 1          # 'vanaf X' / 'X en later'


def match_constructies(dos, pool, cb):
    """-> (gekozen_templates[list of unieke ET], mapping schil_id->naam, issues[list])."""
    bouwjaar = getattr(dos.identificatie, "bouwjaar", None)
    klasse = cb.bouwjaarklasse_code(bouwjaar) if bouwjaar else None
    chosen, seen, mapping, issues = [], {}, {}, []
    for s in dos.schil:
        kind = _classify(s)
        ctype = TYPE_CODE.get(kind)
        if ctype is None:
            issues.append("schildeel %s: onbekend type %r" % (s.id, s.type))
            continue
        if kind in ("gevel", "vloer", "dak", "paneel"):
            # paneel-in-kozijn = dichte constructie (ConstructieType=1), zelfde isolatie-beslisschema als een gevel
            # per-BOUWDEEL bouwjaarklasse (form-antwoord) wint van het project-bouwjaar
            s_klasse = klasse
            kj = _jaar_uit_klassetekst(getattr(s, "bouwjaarklasse", ""))
            if kj:
                s_klasse = cb.bouwjaarklasse_code(kj)
            tmpl = pool.pick_dicht(ctype, s.isolatie_aanwezig, s.isolatiedikte_mm,
                                   s.spouw_aanwezig, s_klasse)
            if kind != "paneel" and s_klasse is None and (s.isolatie_aanwezig or "").lower() == "onbekend":
                issues.append("schildeel %s: isolatie onbekend ZONDER bouwjaar(klasse) -> beslisschema "
                              "viel terug op de oudste klasse; vul bouwjaar of de klasse per bouwdeel in." % s.id)
        elif kind == "raam":
            tmpl = pool.pick_raam(cb, s.glastype, s.kozijnmateriaal)
            if "vacu" in (s.glastype or "").lower():
                issues.append("schildeel %s: vacuumglas gemapt naar HR++ (Beslisschema kent geen "
                              "vacuum); verifieer U-waarde/kwaliteitsverklaring in Vabi" % s.id)
            elif (s.glastype or "").strip() and cb.glas_code(_norm_glas(s.glastype)) is None:
                # audit-glas-F3 15-7: onherkend glastype (bv. 'Onbekend') viel stil op de eerste
                # raam-template (Dubbel) -> nu geflagd i.p.v. gegokt.
                issues.append("schildeel %s: glastype %r niet herkend -> tool koos een standaard-raam; "
                              "controleer de U-waarde / het glas in Vabi." % (s.id, s.glastype))
        else:
            tmpl = pool.pick_deur(s.isolatie_aanwezig)
            # audit-glas-F4 15-7: glas-in-deur (oppervlak + de >=65%-glas-vlag) komt niet in de
            # standaard-deurconstructie -> flag zodat de adviseur het glas/raam in Vabi zet.
            if getattr(s, "deur_met_raam_glas65", False) or (getattr(s, "glastype", "") or "").strip():
                issues.append("schildeel %s: deur met glas -> de tool koos een standaard-deur; zet het "
                              "glas/raam-in-deur (en zo nodig de 65-procent-glasvlag) in Vabi." % s.id)
        if tmpl is None:
            issues.append("schildeel %s: geen passende standaard-constructie (%s)" % (s.id, kind))
            continue
        naam = _t(tmpl, "Naam", "")
        # GUID DETERMINISTISCH afleiden uit de constructienaam (uuid5), NIET random (uuid4) en NIET
        # op id(tmpl): resolve_constructies wordt 2x apart aangeroepen (constructie- én objecten-
        # generator). Random/object-id-guids verschillen dan per aanroep -> de objecten verwijzen naar
        # guids die de constructiebibliotheek niet kent -> EPA "Enum mismatch" bij objecten-import.
        # uuid5(naam) is stabiel over beide aanroepen -> identieke NaamConstructie/GUID-verwijzingen.
        key = naam or str(id(tmpl))
        if key not in seen:
            seen[key] = str(uuid.uuid5(uuid.NAMESPACE_DNS, "vabi-constructie/" + str(key)))
            chosen.append((tmpl, seen[key]))
        # per schildeel: welke constructie (naam + guid) -> gedeeld met Objecten-generator
        mapping[s.id] = {"naam": naam, "guid": seen[key]}
    return chosen, mapping, issues


def assert_importable(chosen, cb):
    """Harde poort: elke enum-waarde van elke gekozen constructie moet door VABI gekend zijn."""
    problems = []
    for c, _guid in chosen:
        for f in GATE_FIELDS:
            v = _t(c, f)
            if v is not None and not cb.is_valid(f, v):
                problems.append("%s=%r (constructie %r)" % (f, v, _t(c, "Naam")))
    if problems:
        raise ValueError("NIET klaar voor import:\n  - " + "\n  - ".join(problems))


def resolve_constructies(dos, pool=None, cb=None):
    """Publiek: per schildeel de gekozen constructie (naam+guid) + de unieke gekloonde
    <Constructie>-elementen (guid gezet). Gedeeld door constructie- EN objecten-generator,
    zodat de NaamConstructie/GUID-verwijzingen in beide bibliotheken identiek zijn."""
    assert_no_schil_kwaliteitsverklaring(dos)
    assert_no_dubbel_dak_fallback(dos)
    pool = pool or TemplatePool(TEMPLATE)
    cb = cb or Codebook.from_export(TEMPLATE)
    chosen, mapping, issues = match_constructies(dos, pool, cb)
    assert_importable(chosen, cb)
    clones = []
    for tmpl, guid in chosen:
        clone = copy.deepcopy(tmpl)
        g = clone.find("Guid")
        if g is not None:
            g.text = guid
        clones.append(clone)
    return clones, mapping, issues


def build_tree(dos, pool, cb):
    clones, mapping, issues = resolve_constructies(dos, pool, cb)
    if not clones:
        raise ValueError("Geen constructies om te exporteren (issues: %s)" % issues)
    out_root = copy.deepcopy(pool.root)
    cons_container = next(c for c in out_root.iter() if _local(c.tag) == "Constructies")
    guid = cons_container.find("Guid")
    for ch in list(cons_container):
        if ch is not guid:
            cons_container.remove(ch)
    for i, clone in enumerate(clones):
        clone.set("Index", str(i))
        cons_container.append(clone)
    return out_root, mapping, issues


def write(dos, path, template=TEMPLATE):
    pool = TemplatePool(template)
    cb = Codebook.from_export(template)
    root, mapping, issues = build_tree(dos, pool, cb)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    body = ET.tostring(root, encoding="utf-8")
    with open(path, "wb") as fh:
        fh.write(b'<?xml version="1.0" encoding="UTF-8"?>\n' + body)
    return mapping, issues


def main():
    root_dir = os.path.dirname(HERE)
    ap = argparse.ArgumentParser(description="Dossier -> importeerbare VABI Constructiebibliotheek")
    ap.add_argument("--dossier", required=True)
    ap.add_argument("--out", default=os.path.join(root_dir, "out", "Constructiebibliotheek.xml"))
    ap.add_argument("--template", default=TEMPLATE)
    a = ap.parse_args()
    dos = load_json(a.dossier)
    mapping, issues = write(dos, a.out, a.template)
    print("OK: %s" % a.out)
    print("  %d unieke constructie-types geexporteerd (gekloond uit standaardbibliotheek):"
          % len({m["naam"] for m in mapping.values()}))
    for sid, m in mapping.items():
        print("    %-12s -> %s" % (sid, m["naam"]))
    if issues:
        print("  LET OP (%d):" % len(issues))
        for it in issues:
            print("    ! " + it)
    print("  -> import in EPA: tegel Constructies > Importeren > kies dit XML.")


if __name__ == "__main__":
    main()
