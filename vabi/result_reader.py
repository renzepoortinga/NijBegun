"""
Lees het VABI-rekenresultaat terug uit een EPA-export/monitoringbestand (de Summary-node) ->
de kerngetallen voor het rapport en de Nij Begun-Standaardtoets.

Belangrijkste velden (uit Summary):
  - Standaard                  = de Standaard-eis voor DEZE woning (kWh/m2.jr) [geometrie-afhankelijk]
  - NettoWarmtebehoefte        = netto warmtebehoefte van de SCHIL (kWh/m2.jr) -> vergelijk met Standaard
  - IndicatorEnergiebehoefte   = brede energieprestatie-indicator (Ewe; incl. installaties/tapwater) —
                                  NIET de Standaard-toets-maat voor een isolatieplan (schil-only, M29)
  - Labelklasse                = energielabel (A++/.. )
  - IndicatorPrimaireFossieleEnergie, TOjuliNTA8800, Compactheid, Gebruiksoppervlakte, Verliesoppervlakte

Nij Begun-toets (M29, schil-only):  netto warmtebehoefte <= Standaard  ->  voldoet aan de Standaard.
(Ontbreekt NettoWarmtebehoefte in het exportbestand -- oudere Vabi-versie -- dan toont de tool die
export nog wel informatief via IndicatorEnergiebehoefte (_toetswaarde/_toetswaarde_bron), maar het
groen/rood-oordeel zelf (_voldoet_aan_standaard) is dan FAIL-CLOSED: None ("niet te bepalen"), nooit
een vervangend oordeel op de bredere indicator -- die overschat de warmtevraag omdat hij ook
installaties meeweegt. Zie docs/nta8800-analyse-vs-tool.md en de vergelijking met SOBOLT die dit
blootlegde, 21-8-2026, en de audit van 22-8-2026 die het fail-closed-gat blootlegde.)

    python vabi/result_reader.py --monitor "9503HN-23-- (monitor).xml"
"""
import os, argparse
import xml.etree.ElementTree as ET

KERN = ["Labelklasse", "IndicatorEnergiebehoefte", "NettoWarmtebehoefte", "Standaard",
        "IndicatorPrimaireFossieleEnergie", "TOjuliNTA8800", "NettoWarmtevraagTbvEPV",
        "Compactheid", "Gebruiksoppervlakte", "Verliesoppervlakte"]


def _ln(tag):
    return tag.rsplit("}", 1)[-1]


def _num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def read_results(path):
    root = ET.parse(path).getroot()
    summ = next((e for e in root.iter() if _ln(e.tag) == "Summary"), None)
    out = {}
    if summ is not None:
        for c in summ:
            name = _ln(c.tag)
            if name in KERN and c.text and c.text.strip():
                out[name] = c.text.strip()
    # Standaard-toets: netto warmtebehoefte (schil) is de juiste maat, niet de bredere
    # energiebehoefte-indicator (die ook installaties meeweegt) -- val terug op die laatste
    # alleen als een oudere export geen NettoWarmtebehoefte heeft.
    nwb = _num(out.get("NettoWarmtebehoefte"))
    eb = nwb if nwb is not None else _num(out.get("IndicatorEnergiebehoefte"))
    std = _num(out.get("Standaard"))
    out["_toetswaarde"] = eb
    out["_toetswaarde_bron"] = "NettoWarmtebehoefte" if nwb is not None else "IndicatorEnergiebehoefte (fallback)"
    # Provenance mag nooit "IndicatorEnergiebehoefte" claimen als die ZELF ook ontbreekt -- anders
    # suggereert het een fallback die niet heeft plaatsgevonden (audit-vervolgbevinding, Codex-review).
    if nwb is not None:
        out["_indicator_type"] = "NettoWarmtebehoefte"
    elif eb is not None:
        out["_indicator_type"] = "IndicatorEnergiebehoefte"
    else:
        out["_indicator_type"] = None
    # Fail-closed: een "voldoet"-oordeel mag alleen op de echte NettoWarmtebehoefte rusten. Bij de
    # IndicatorEnergiebehoefte-fallback (of ontbrekende Standaard) is het oordeel "niet te bepalen"
    # (None) -- nooit stilzwijgend rood (False) en nooit een verkeerd-maar-groen oordeel.
    out["_voldoet_aan_standaard"] = None
    out["_marge_kwh_m2"] = None
    if nwb is not None and std is not None and std > 0:
        out["_voldoet_aan_standaard"] = nwb <= std
        out["_marge_kwh_m2"] = round(std - nwb, 2)   # >0 = ruimte tot Standaard
    return out


def main():
    ap = argparse.ArgumentParser(description="Lees VABI-resultaat (Standaard-toets) uit monitor/export")
    ap.add_argument("--monitor", required=True)
    a = ap.parse_args()
    r = read_results(a.monitor)
    print("VABI-resultaat: %s" % os.path.basename(a.monitor))
    for k in KERN:
        if k in r:
            print("  %-32s = %s" % (k, r[k]))
    if r.get("_voldoet_aan_standaard") is None:
        print("\n  Standaard-toets: niet te bepalen (%s, geen NettoWarmtebehoefte of Standaard-eis)" %
              r.get("_toetswaarde_bron", "?"))
    elif "_voldoet_aan_standaard" in r:
        status = "VOLDOET" if r["_voldoet_aan_standaard"] else "VOLDOET NIET"
        print("\n  Standaard-toets: %s %.2f vs Standaard %.2f -> %s (marge %s kWh/m2.jr)" % (
            r["_toetswaarde_bron"], r["_toetswaarde"], _num(r["Standaard"]), status, r["_marge_kwh_m2"]))


if __name__ == "__main__":
    main()
