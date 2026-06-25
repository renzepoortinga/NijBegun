"""
Bouw de MASTER enum-catalogus van VABI EPA: voegt alle bronnen samen tot EEN bestand
(vabi/refs/vabi_enums.json) dat per VABI-veld de geldige integer-codes + betekenis +
verplicht-vlag bevat. Dit is het fundament van de configurator/generators (de harde
validatie-poort leest hieruit). Volledig OFFLINE, herhaalbaar, geen tokens.

Bronnen (allemaal al in vabi/refs/):
  - vabi_enum_inventory.json      = COMPLETE veldkaart (237 dropdowns/22 domeinen, uit de exe)
  - code_universe.json            = integer-codes + Naam-hints (uit per-tegel bibliotheek-exports)
  - monitor_enum_universe.json    = standaard-enumstrings + VERPLICHT-vlag (uit 14 monitors)

Uitvoer:
  - vabi_enums.json               = per (domein/veld): codes{code:betekenis}, verplicht?, monitor-waarden
  - dekkingsrapport (stdout)      = welke van de 237 velden hebben al codes, welke missen nog
                                    -> stuurt welke EXTRA exports nog nodig zijn

    python vabi/build_enum_catalog.py
"""
import os, json, re
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REFS = os.path.join(HERE, "refs")


def _load(name):
    p = os.path.join(REFS, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def build():
    inventory = _load("vabi_enum_inventory.json")          # domein -> [enums]
    cu = _load("code_universe.json").get("enums", {})      # "Container/Field" -> {code: [hints]}
    mon = _load("monitor_enum_universe.json").get("enums", {})  # "pad" -> {waarden, verplicht?}

    # index code_universe + monitor op genormaliseerde veldnaam (laatste pad-segment)
    cu_by_field = defaultdict(dict)
    for key, codes in cu.items():
        field = key.split("/")[-1]
        for code, hints in codes.items():
            cu_by_field[_norm(field)].setdefault(code, set()).update(h for h in hints if h)
    mon_by_field = defaultdict(lambda: {"waarden": set(), "verplicht": False, "field": ""})
    for path, info in mon.items():
        field = path.split("/")[-1]
        slot = mon_by_field[_norm(field)]
        slot["field"] = field
        slot["waarden"].update(info.get("waarden", []))
        if info.get("verplicht?"):
            slot["verplicht"] = True

    catalog, have, missing = {}, 0, []
    for domein, enums in inventory.items():
        catalog[domein] = {}
        for enum in enums:
            nf = _norm(enum)
            codes = {c: sorted(h)[:3] for c, h in cu_by_field.get(nf, {}).items()}
            mslot = mon_by_field.get(nf, {})
            entry = {
                "codes": dict(sorted(codes.items(), key=lambda kv: (len(kv[0]), kv[0]))),
                "verplicht": bool(mslot.get("verplicht")),
                "monitor_waarden": sorted(mslot.get("waarden", []))[:25],
                "heeft_codes": bool(codes),
            }
            catalog[domein][enum] = entry
            if codes:
                have += 1
            else:
                missing.append("%s/%s" % (domein, enum))

    out = {"_meta": {"velden_totaal": sum(len(v) for v in inventory.values()),
                     "met_codes": have, "zonder_codes": len(missing)},
           "domeinen": catalog}
    json.dump(out, open(os.path.join(REFS, "vabi_enums.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return out, missing


def main():
    out, missing = build()
    m = out["_meta"]
    print("MASTER-CATALOGUS vabi/refs/vabi_enums.json")
    print("  velden: %d | met codes: %d | nog zonder codes: %d" % (
        m["velden_totaal"], m["met_codes"], m["zonder_codes"]))
    # toon per domein de dekking
    print("\nDekking per domein (velden met codes / totaal):")
    for dom, fields in out["domeinen"].items():
        n = len(fields); k = sum(1 for f in fields.values() if f["heeft_codes"])
        bar = "#" * int(10 * k / n) if n else ""
        print("  %-18s %2d/%-2d %s" % (dom, k, n, bar))
    print("\nNog aan te vullen (een export van een project met deze installaties lost het op):")
    for x in missing[:40]:
        print("  - " + x)
    if len(missing) > 40:
        print("  ... (+%d)" % (len(missing) - 40))


if __name__ == "__main__":
    main()
