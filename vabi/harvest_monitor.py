"""
Monitor-harvester: leest meerdere NTA8800-monitoringbestanden (EP-online-standaard,
namespace http://schemas.ep-online.nl/monitoringbestand) en bouwt twee dingen op:

  1. ENUM-UNIVERSUM  - per leaf-pad de set waargenomen waarden (de echte enum-ruimte
     zoals die in geregistreerde projecten voorkomt).
  2. VERPLICHT-SIGNAAL - per leaf-pad in hoeveel van de N projecten het voorkomt. Een
     pad dat in ALLE projecten zit is (vrijwel zeker) verplicht voor een resultaat;
     dit beantwoordt Renze' vraag "wat is vereist om een uitkomst te krijgen?".

Het monitoringbestand is het LANDELIJKE standaardformaat (versie-stabiel), los van VABI's
interne bibliotheek-codes. Het is daarmee de betrouwbaarste bron voor de enum-ruimte +
verplichte structuur. PRIVACY: adres/BAG/namen/datums/coordinaten worden NOOIT geoogst.

    python vabi/harvest_monitor.py  "map/*.xml"
    -> vabi/refs/monitor_enum_universe.json + dekkings-/verplicht-rapport
"""
import os, sys, glob, json, re
import xml.etree.ElementTree as ET
from collections import defaultdict

# leaf-namen die NOOIT geoogst worden (persoonsgegevens / vrije getallen / identiteit)
PII = {
    "BAGResidenceId", "BAGBuildingId", "ZipCode", "Number", "BuildingAnnotation",
    "Street", "City", "Name", "FirstName", "LastName", "Email", "Phone", "Telephone",
    "X", "Y", "Latitude", "Longitude", "Date", "RegistrationDate", "RecordingDate",
    "AdvisorId", "RegistrationNumber", "CertificateNumber", "ProjectName", "Reference",
}
# leaf telt als 'enum-achtig' als waarde kort is en weinig distinct over corpus
ENUM_MAX_CARD = 25
FREE_NUM = re.compile(r"^-?\d+([.,]\d+)?$")
# waarde-patronen die nooit geoogst worden (identificeerbaar): NL-postcode, datum, lange id
POSTCODE = re.compile(r"^\d{4}\s?[A-Za-z]{2}$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}")
LONGID = re.compile(r"^\d{8,}$")


def _ln(tag):
    return tag.rsplit("}", 1)[-1]


def _looks_personal(name):
    n = name.lower()
    return name in PII or any(k in n for k in ("naam", "adres", "postcode", "huisnr",
                                               "datum", "date", "omschrijving"))


def _value_is_sensitive(val):
    return bool(POSTCODE.match(val) or DATE.match(val) or LONGID.match(val))


def _anon_source(name):
    # bronbestandsnaam bevat postcode-huisnr -> anonimiseer tot monitor_NN
    return name


class MonitorUniverse:
    def __init__(self):
        self.path_values = defaultdict(lambda: defaultdict(set))   # path -> value -> {srcs}
        self.path_in_src = defaultdict(set)                        # path -> {srcs}
        self.sources = []

    def ingest(self, fpath):
        # bronnaam anonimiseren (bestandsnaam bevat postcode-huisnummer)
        src = "monitor_%02d" % (len(self.sources) + 1)
        self.sources.append(src)
        root = ET.parse(fpath).getroot()

        def walk(el, path):
            name = _ln(el.tag)
            p = path + "/" + name if path else name
            kids = list(el)
            if kids:
                for k in kids:
                    walk(k, p)
            else:
                val = (el.text or "").strip()
                self.path_in_src[p].add(src)
                if val and not _looks_personal(name) and not _value_is_sensitive(val):
                    self.path_values[p][val].add(src)
        walk(root, "")

    def to_dict(self):
        n = len(self.sources)
        enums = {}
        for p, valmap in self.path_values.items():
            # alleen paden die als enum bruikbaar zijn (lage cardinaliteit, niet puur vrij getal)
            vals = list(valmap)
            non_free = [v for v in vals if not FREE_NUM.match(v)]
            if len(vals) <= ENUM_MAX_CARD and (non_free or len(vals) <= 8):
                enums[p] = {
                    "in_n_van_N": "%d/%d" % (len(self.path_in_src[p]), n),
                    "verplicht?": len(self.path_in_src[p]) == n,
                    "waarden": sorted(vals, key=lambda v: (len(v), v)),
                }
        return {"sources": self.sources, "N": n, "enums": enums}

    def report(self):
        n = len(self.sources)
        d = self.to_dict()["enums"]
        always = {p: v for p, v in d.items() if v["verplicht?"]}
        lines = ["MONITOR-UNIVERSUM  (%d projecten, %d enum-achtige velden)" % (n, len(d))]
        lines.append("\n== ALTIJD aanwezig (verplicht-kandidaten: %d) ==" % len(always))
        for p in sorted(always):
            vals = always[p]["waarden"]
            shown = " ".join(vals[:8]) + ("" if len(vals) <= 8 else " (+%d)" % (len(vals) - 8))
            lines.append("  %-58s %s" % (p.split("/", 2)[-1][-58:], shown))
        return "\n".join(lines)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    refs = os.path.join(here, "refs")
    args = []
    for a in sys.argv[1:]:
        args += glob.glob(a)
    if not args:
        print("Geef monitor-XML's of een glob op, bv: python vabi/harvest_monitor.py \"map/*.xml\"")
        return
    mu = MonitorUniverse()
    for p in sorted(args):
        try:
            mu.ingest(p)
            print("ingested:", os.path.basename(p))
        except Exception as e:
            print("SKIP %s (%s)" % (os.path.basename(p), e))
    os.makedirs(refs, exist_ok=True)
    out = os.path.join(refs, "monitor_enum_universe.json")
    json.dump(mu.to_dict(), open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n" + mu.report())
    print("\n-> %s" % out)


if __name__ == "__main__":
    main()
