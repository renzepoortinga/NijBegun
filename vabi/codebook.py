"""
VABI-codebook: leidt de 'taal van VABI' (integer enum-codes <-> betekenis) AF uit een
echte VABI EPA-export, in plaats van die te hardcoden. Zo is de tool zelfhelend tegen
VABI-releases: exporteer in EPA opnieuw 'Standaard constructies' -> dit codebook past zich aan.

Bron-export maak je in EPA: project openen -> tegel Constructies -> 'Standaard constructies'
(vult 219 standaard-constructies) -> 'Exporteren' -> XML. Alles in die export is per definitie
IMPORT-GELDIG (het is VABI's eigen data) -> perfecte bron voor de harde validatie-poort.

    from vabi.codebook import Codebook
    cb = Codebook.from_export("vabi/refs/standaard_constructies_v120001001.xml")
    cb.glas_code("HR++")          # -> "5"
    cb.valid("Glas")              # -> {"0","1","2","3","4","5","6"}
    cb.assert_valid("Glas", "9")  # -> raise (niet importeerbaar)

Geverifieerd op de 12.0.1-export (219 constructies). ConstructieType: 0=Gevel 1=Paneel
2=Raam 3=Deur 4=Dak 7=Vloer. Glas: 0=Enkel 1=Voorzetraam 2=Dubbel 3=HR 4=HR+ 5=HR++
6=TripleHR. Kozijn: 0=Hout/kunststof 3=Therm.onderbroken metaal 4=Metaal.
"""
import os
import re
import xml.etree.ElementTree as ET
from collections import defaultdict

# Enum-velden waarvoor we geldige codes + (waar mogelijk) betekenis afleiden.
ENUM_FIELDS = ("ConstructieType", "Glas", "Kozijn", "IsolatieAanwezig",
               "Bouwjaar", "Invoer", "SpouwAanwezig", "DeurMetRaamGlas65Procent",
               "RietenDak")

# Versie-onafhankelijke trefwoorden om een Naam-string te classificeren. We koppelen
# een trefwoord aan het VELD; de CODE halen we uit de export zelf (nooit hardcoden).
_GLAS_KEYS = ("enkel", "voorzetraam", "dubbel", "triplehr", "hr++", "hr+", "hr")
_KOZIJN_KEYS = ("therm. onderbroken metaal", "metaal", "hout/kunststof", "hout of kunststof")
_TYPE_KEYS = ("gevel", "paneel in kozijn", "vloer", "dak", "deur")


def _localname(tag):
    return tag.rsplit("}", 1)[-1]


class Codebook:
    def __init__(self, constructies):
        # constructies = lijst dicts met alle velden als string
        self._rows = constructies
        self._valid = defaultdict(set)
        for row in constructies:
            for f in ENUM_FIELDS:
                if row.get(f) not in (None, ""):
                    self._valid[f].add(row[f])
        # semantische maps label->code, afgeleid uit Naam (eerste match wint)
        self._glas, self._kozijn, self._type, self._bouwjaar = {}, {}, {}, {}
        for row in constructies:
            naam = (row.get("Naam") or "").lower()
            self._learn(self._glas, _GLAS_KEYS, naam, row.get("Glas"))
            self._learn(self._kozijn, _KOZIJN_KEYS, naam, row.get("Kozijn"))
            self._learn(self._type, _TYPE_KEYS, naam, row.get("ConstructieType"))
            m = re.search(r"\((?:[^)]*?)(\d{4})\s*-\s*(\d{4})\)", row.get("Naam") or "")
            if m and row.get("Bouwjaar") not in (None, "", "0"):
                self._bouwjaar[(int(m.group(1)), int(m.group(2)))] = row["Bouwjaar"]

    @staticmethod
    def _learn(store, keys, naam, code):
        if code in (None, ""):
            return
        for k in keys:
            if k in naam:
                store.setdefault(k, code)
                return

    # ---- constructors ----
    @classmethod
    def from_export(cls, path):
        root = ET.parse(path).getroot()
        rows = []
        for el in root.iter():
            if _localname(el.tag) == "Constructie":
                row = {}
                for ch in el:
                    row[_localname(ch.tag)] = (ch.text or "")
                if row:
                    rows.append(row)
        if not rows:
            raise ValueError("Geen <Constructie>-blokken gevonden in %s" % path)
        return cls(rows)

    @classmethod
    def default(cls):
        here = os.path.dirname(os.path.abspath(__file__))
        return cls.from_export(os.path.join(here, "refs", "standaard_constructies_v120001001.xml"))

    # ---- harde validatie-poort ----
    def valid(self, field):
        return set(self._valid.get(field, set()))

    def is_valid(self, field, code):
        return str(code) in self._valid.get(field, set())

    def assert_valid(self, field, code):
        if not self.is_valid(field, code):
            raise ValueError(
                "NIET klaar voor import: %s=%r is geen door VABI bekende code "
                "(geldig: %s)" % (field, code, sorted(self._valid.get(field, set()))))
        return str(code)

    # ---- semantische vertalers (dossierwaarde -> VABI-code) ----
    def glas_code(self, label):
        return self._match(self._glas, _GLAS_KEYS, label)

    def kozijn_code(self, label):
        return self._match(self._kozijn, _KOZIJN_KEYS, label)

    def constructietype_code(self, label):
        return self._match(self._type, _TYPE_KEYS, label)

    def bouwjaarklasse_code(self, jaar):
        if jaar is None:
            return None
        for (lo, hi), code in self._bouwjaar.items():
            if lo <= int(jaar) <= hi:
                return code
        return None

    @staticmethod
    def _match(store, keys, label):
        s = (label or "").lower()
        for k in keys:           # langste/meest-specifieke trefwoorden staan vooraan
            if k in s and k in store:
                return store[k]
        return None

    # ---- introspectie ----
    def summary(self):
        out = ["Codebook (%d constructies):" % len(self._rows)]
        for f in ENUM_FIELDS:
            out.append("  %-26s geldig: %s" % (f, sorted(self._valid.get(f, set()), key=lambda v: int(v) if v.lstrip("-").isdigit() else v)))
        return "\n".join(out)


if __name__ == "__main__":
    cb = Codebook.default()
    print(cb.summary())
    print("\nVertaaltests:")
    for lbl in ("HR++", "dubbel", "enkel", "TripleHR"):
        print("  glas %-9s -> %s" % (lbl, cb.glas_code(lbl)))
    for lbl in ("hout/kunststof", "metaal", "therm. onderbroken metaal"):
        print("  kozijn %-26s -> %s" % (lbl, cb.kozijn_code(lbl)))
    for lbl in ("gevel", "dak", "vloer", "deur", "paneel in kozijn"):
        print("  type %-18s -> %s" % (lbl, cb.constructietype_code(lbl)))
    for jr in (1970, 2000, 2019):
        print("  bouwjaar %d -> klasse %s" % (jr, cb.bouwjaarklasse_code(jr)))
