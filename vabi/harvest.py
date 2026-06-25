"""
VABI code-harvester: leest WILLEKEURIG veel VABI EPA-exports (onversleutelde per-tegel
bibliotheek-XML's: Constructie/Installatie/Objecten) en bouwt incrementeel het 'code-
universum' op = per (container, veld) de verzameling enum-codes die in de praktijk
voorkomen, plus decode-hints uit naburige Naam/Code/Type-velden. Meerdere exports mergen
tot een unie -> 'loop al je projecten langs' wordt herhaalbaar en cumulatief.

Doel: alle invoerwaarden verzamelen die nodig zijn om zelf een geldige import/export te
genereren. .epa-projectbestanden zijn versleutelde ZIP's (NIET te lezen); gebruik de
per-tegel EXPORT in EPA (onversleuteld) als voer.

    python vabi/harvest.py  export1.xml export2.xml ...   # of zonder args = alle refs
    -> schrijft vabi/refs/code_universe.json + print dekkingsrapport

Enum-detectie heuristiek: een veld telt als enum-kandidaat als ALLE waargenomen waarden
korte gehele getallen zijn in [-1, ENUM_MAX] en de cardinaliteit klein is. Vrije getallen
(oppervlakte/lengte/Rc/jaartal) vallen daar buiten. Aangevuld met een vaste allowlist van
bekende enum-velden zodat we niets missen.
"""
import os, sys, json, glob
import xml.etree.ElementTree as ET
from collections import defaultdict

ENUM_MAX = 60          # codes hoger dan dit = waarschijnlijk geen enum
ENUM_MAX_CARD = 40     # meer dan zoveel distinct waarden = geen enum (bv. id/jaar)

# velden die ALTIJD als enum gelden (ook al lijkt de heuristiek te twijfelen)
KNOWN_ENUM = {
    "ConstructieType", "Glas", "Kozijn", "IsolatieAanwezig", "Bouwjaar", "Invoer",
    "SpouwAanwezig", "RietenDak", "DeurMetRaamGlas65Procent", "Type", "TypeOpwekker",
    "TypeElektromotor", "Opstelplaats", "Orientatie", "GrenstAan", "Locatie",
    "AangrenzendGebouwfunctie", "Hoofdvlak", "BodemisolatieKruipruimte", "Eenheid",
    "Bron", "KwaliteitsverklaringInvoermethode", "InvoermethodeKwaliteitsverklaring",
    "DuurzaamBeng3", "Vlaktype", "Begrenzing",
}
# velden die NOOIT enum zijn (vrije getallen / identiteit) — beschermt tegen valse
# positieven EN tegen het lekken van adres-/persoonsgegevens naar het code-universum.
NEVER_ENUM = {
    "Oppervlakte", "OppervlaktePerConstructie", "Lengte", "Breedte", "Hoogte", "Rc",
    "Arc", "U", "G", "Perimeter", "Dikte", "Isolatiedikte", "Rietdikte", "Installatiejaar",
    "NominaalVermogen", "Volume", "Aantal", "PrijsPerEenheid", "Vastrecht", "Index",
    "Fabricagejaar", "FabricagejaarVentilator", "Spanning", "Stroomsterkte", "Arbeidsfactor",
    "ElektrischAsvermogen", "Salderingspercentage", "Opbrengstpercentage", "Levensduur",
    "RenteInvestering", "GrensPrijsplafond", "PrijsBovenPlafond", "AantalAangrenzendeGebouwen",
    # identiteit/adres -> nooit oogsten (privacy)
    "Huisnummer", "RefHuisnummer", "Bouwjaar", "Renovatiejaar", "Nummer", "AantalBouwlagenRekenzone",
    "AantalToiletgroepen", "Leidingdoorvoeren", "Gebruiksoppervlakte",
}
# hele secties die we overslaan: persoonsgegevens + maandelijkse energie-arrays (ruis).
SKIP_CONTAINERS = {
    "Adresgegevens", "Opdrachtgever", "Adviseur", "AdviseurGegevens", "Eigenaar",
    "Januari", "Februari", "Maart", "April", "Mei", "Juni", "Juli", "Augustus",
    "September", "Oktober", "November", "December",
}


def _ln(tag):
    return tag.rsplit("}", 1)[-1]


def _is_code(s):
    s = (s or "").strip()
    if not s or not s.lstrip("-").isdigit():
        return False
    return -1 <= int(s) <= ENUM_MAX


class CodeUniverse:
    def __init__(self):
        # (container, field) -> { code -> set(decode-hints) }
        self.values = defaultdict(lambda: defaultdict(set))
        self.sources = []
        self.versions = set()

    def ingest(self, path):
        root = ET.parse(path).getroot()
        self.sources.append(os.path.basename(path))
        for k in ("XmlVersie", "FullApplicationVersion"):
            el = root.find(".//" + k)
            if el is not None and el.text:
                self.versions.add("%s=%s" % (k, el.text))
        for parent in root.iter():
            container = _ln(parent.tag)
            if container in SKIP_CONTAINERS:
                continue
            # decode-hint = de Naam/Type-string van dit element (helpt codes duiden)
            hint = ""
            for hk in ("Naam", "Omschrijving", "NaamConstructie"):
                h = parent.find(hk)
                if h is not None and h.text:
                    hint = h.text.strip()
                    break
            for child in parent:
                field = _ln(child.tag)
                val = (child.text or "").strip()
                if field in NEVER_ENUM or not val:
                    continue
                if field in KNOWN_ENUM or _is_code(val):
                    self.values[(container, field)][val].add(hint)

    def prune(self):
        """Gooi velden weg met te hoge cardinaliteit (geen echte enum), tenzij known."""
        for key in list(self.values):
            container, field = key
            if field in KNOWN_ENUM:
                continue
            codes = self.values[key]
            non_int = any(not c.lstrip("-").isdigit() for c in codes)
            if non_int or len(codes) > ENUM_MAX_CARD:
                del self.values[key]

    def to_dict(self):
        out = {"sources": self.sources, "versions": sorted(self.versions), "enums": {}}
        for (container, field), codes in sorted(self.values.items()):
            key = "%s/%s" % (container, field)
            out["enums"][key] = {
                c: sorted(h for h in hints if h)[:4]
                for c, hints in sorted(codes.items(), key=lambda kv: (len(kv[0]), kv[0]))
            }
        return out

    def report(self):
        lines = ["CODE-UNIVERSUM  (bronnen: %d, versies: %s)" % (
            len(self.sources), ", ".join(sorted(self.versions)) or "?")]
        by_container = defaultdict(list)
        for (container, field), codes in self.values.items():
            by_container[container].append((field, codes))
        for container in sorted(by_container):
            lines.append("\n[%s]" % container)
            for field, codes in sorted(by_container[container]):
                sample = sorted(codes, key=lambda c: (len(c), c))
                # toon code->kortste hint
                shown = []
                for c in sample[:12]:
                    hints = [h for h in codes[c] if h]
                    shown.append("%s%s" % (c, ("=" + min(hints, key=len)) if hints else ""))
                more = "" if len(sample) <= 12 else " (+%d)" % (len(sample) - 12)
                lines.append("  %-30s %s%s" % (field, " ".join(shown), more))
        return "\n".join(lines)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    refs = os.path.join(here, "refs")
    args = sys.argv[1:]
    if not args:
        args = sorted(glob.glob(os.path.join(refs, "*.xml")))
        # ook losse Oosterkade-exports meenemen als ze in refs gekopieerd zijn
    cu = CodeUniverse()
    for p in args:
        try:
            cu.ingest(p)
            print("ingested:", os.path.basename(p))
        except Exception as e:
            print("SKIP %s (%s)" % (os.path.basename(p), e))
    cu.prune()
    os.makedirs(refs, exist_ok=True)
    out = os.path.join(refs, "code_universe.json")
    json.dump(cu.to_dict(), open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n" + cu.report())
    print("\n-> %s (%d enum-velden)" % (out, len(cu.values)))


if __name__ == "__main__":
    main()
