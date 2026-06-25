"""
Verrijk de maatregelen in een dossier met prijzen uit catalog.json:
  prijs_per_eenheid (incl. btw) en kosten = oppervlakte x prijs.
Match op exacte code, anders op code-prefix; deltarijen worden overgeslagen.
"""
import os, sys, json, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.dossier import load_json, save_json  # noqa: E402

DELTA_MARK = "╚"  # box-drawing teken dat 'meer-/minderprijs'-deltarijen markeert

def load_catalog(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)

def is_delta(m):
    o = (m.get("omschrijving") or "")
    return o.strip().startswith(DELTA_MARK) or "meer-/minderprijs" in o.lower()

def pos_price(m):
    return (m.get("prijs_per_eenheid_incl_btw") or m.get("prijs_per_eenheid_excl") or 0) > 0

def find_price(catalog, code):
    ms = catalog["maatregelen"]
    for m in ms:
        if m["code"] == code and not is_delta(m) and pos_price(m):
            return m
    cand = [m for m in ms if m["code"].startswith(code) and not is_delta(m) and pos_price(m)]
    cand.sort(key=lambda m: m["code"])
    return cand[0] if cand else None

def price_dossier(dossier, catalog):
    n_ok = 0
    for m in dossier.maatregelen:
        hit = find_price(catalog, m.code)
        if not hit:
            continue
        prijs = hit.get("prijs_per_eenheid_incl_btw") or hit.get("prijs_per_eenheid_excl")
        if prijs is None:
            continue
        m.prijs_per_eenheid = round(prijs, 2)
        m.kosten = round(prijs * (m.oppervlakte_m2 or 0), 2)
        n_ok += 1
    return n_ok

def main():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    ap = argparse.ArgumentParser()
    ap.add_argument("--dossier", default=os.path.join(root, "sample_dossier.json"))
    ap.add_argument("--catalog", default=os.path.join(here, "catalog.json"))
    ap.add_argument("--out", default=os.path.join(root, "sample_dossier_priced.json"))
    a = ap.parse_args()
    dossier = load_json(a.dossier)
    catalog = load_catalog(a.catalog)
    n = price_dossier(dossier, catalog)
    total = sum((m.kosten or 0) for m in dossier.maatregelen)
    save_json(dossier, a.out)
    print("OK: " + a.out)
    print("  beprijsd: %d/%d maatregelen | totaal incl. btw: EUR %.2f"
          % (n, len(dossier.maatregelen), total))
    for m in dossier.maatregelen:
        print("    %-10s %s m2 x EUR%s = EUR%s"
              % (m.code, m.oppervlakte_m2, m.prijs_per_eenheid, m.kosten))

if __name__ == "__main__":
    main()
