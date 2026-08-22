"""
Sluitend-validator = het KWACO-beoordelingsformulier als code.
Toetst een canoniek dossier op compleetheid/inhoud/kosten en rapporteert wat nog
ontbreekt voordat een isolatieplan ingediend mag worden.

Gebruik:
    python3 validator/validate.py --dossier sample_dossier_priced.json [--catalog catalog/catalog.json]
"""
import os, sys, json, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.dossier import load_json, save_json  # noqa

BLOCKER, WARN = "BLOKKEREND", "WAARSCHUWING"

def load_catalog_codes(path):
    if not path or not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        cat = json.load(fh)
    return {m["code"] for m in cat.get("maatregelen", [])}

def validate(dos, catalog_codes=None):
    issues = []
    def add(sev, msg):
        issues.append((sev, msg))

    idf = dos.identificatie
    # --- compleetheid: gegevens ---
    for veld, val in [("postcode", idf.postcode), ("huisnummer", idf.huisnummer),
                      ("bouwjaar", idf.bouwjaar), ("woningtype", idf.woningtype)]:
        if not val:
            add(BLOCKER, f"Gegevens: {veld} ontbreekt")
    if not dos.adviseur.naam:
        add(BLOCKER, "Adviseur: naam ontbreekt")
    # --- foto's ---
    fototypes = {f.type for f in dos.fotos}
    if "voorblad" not in fototypes:
        add(BLOCKER, "Voorbladfoto ontbreekt (adres+foto moeten overeenkomen)")
    if "huisnummer" not in fototypes:
        add(WARN, "Huisnummerfoto (dossier-marker) ontbreekt")
    # --- huidige woningstaat: schil ---
    if not dos.schil:
        add(BLOCKER, "Huidige woningstaat: geen schildelen vastgelegd")
    for s in dos.schil:
        if not s.begrenzing:
            add(WARN, f"Schildeel '{s.id or s.subtype}': begrenzing ontbreekt")
        if s.type in ("gevel", "vloer", "dak") and s.isolatie_aanwezig in ("", "Onbekend"):
            add(WARN, f"Schildeel '{s.id or s.subtype}': isolatiestatus onbekend")
    # --- maatregelen ---
    if not dos.maatregelen:
        add(BLOCKER, "Geen maatregelen voorgesteld")
    for m in dos.maatregelen:
        if not m.code:
            add(BLOCKER, f"Maatregel '{m.omschrijving}': maatregelcode ontbreekt")
        elif catalog_codes is not None and not any(
                c == m.code or c.startswith(m.code) for c in catalog_codes):
            add(BLOCKER, f"Maatregelcode '{m.code}' niet in catalogus")
        if not m.kosten or m.kosten <= 0:
            add(WARN, f"Maatregel '{m.code}': kosten ontbreken/0")
    # --- logische maatregelkeuze ---
    spouw_aanwezig = any(s.type == "gevel" and s.spouw_aanwezig for s in dos.schil)
    if spouw_aanwezig and any("binnen" in (m.omschrijving or "").lower()
                              and "gevel" in (m.omschrijving or "").lower()
                              for m in dos.maatregelen):
        add(WARN, "Binnengevelisolatie geadviseerd terwijl spouw aanwezig is - controleer keuze")
    # --- doeltreffendheid: Standaard gehaald? ---
    ber = dos.berekening
    if ber.standaard_eis_kwh_m2 is None:
        add(WARN, "Standaard-eis (kWh/m2.jr) ontbreekt - bereken in Vabi EPA-W")
    if ber.kwh_m2_na_maatregelen is None:
        add(WARN, "Warmteverlies NA maatregelen ontbreekt - herbereken in Vabi EPA-W")
    elif ber.indicator_type_na != "NettoWarmtebehoefte":
        # Fail-closed: kwh_m2_na_maatregelen kan de IndicatorEnergiebehoefte-fallback zijn (of een
        # legacy/ongetypeerd dossier) -- die overschat de warmtevraag (installaties tellen mee) en
        # mag NOOIT tot een BLOKKEREND "haalt de norm niet" leiden. Zie taak 028/Codex-review.
        add(WARN, "Warmteverlies NA maatregelen is niet vastgelegd als NettoWarmtebehoefte "
            "(mogelijk oudere/bredere indicator) - doeltreffendheid niet te bepalen, herimporteer in Vabi EPA-W")
    elif ber.standaard_eis_kwh_m2 is not None and ber.kwh_m2_na_maatregelen > ber.standaard_eis_kwh_m2:
        add(BLOCKER, "Doeltreffendheid: na maatregelen (%.1f) > Standaard (%.1f) - haalt de norm NIET"
            % (ber.kwh_m2_na_maatregelen, ber.standaard_eis_kwh_m2))
    # --- ventilatie ---
    if not dos.ventilatie.systeem:
        add(BLOCKER, "Ventilatiesysteem niet vastgelegd (ventilatieberekening vereist)")
    # --- uitvoerbaarheid: vloerisolatie -> kruipruimte ---
    if any("vloer" in (m.omschrijving or "").lower() for m in dos.maatregelen):
        if not any(h.kruipruimte_diepte_cm is not None for h in dos.haalbaarheid):
            add(WARN, "Vloerisolatie geadviseerd maar kruipruimtediepte niet vastgelegd")
        for h in dos.haalbaarheid:
            if h.kruipruimte_diepte_cm is not None and h.kruipruimte_diepte_cm < 35:
                add(BLOCKER, "Kruipruimte < 35 cm: vloerisolatie meestal niet uitvoerbaar")

    blockers = [m for s, m in issues if s == BLOCKER]
    dos.validatie.status = "sluitend" if not blockers else "onvolledig"
    dos.validatie.issues = [f"[{s}] {m}" for s, m in issues]
    return issues, dos

def main():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    ap = argparse.ArgumentParser()
    ap.add_argument("--dossier", default=os.path.join(root, "sample_dossier_priced.json"))
    ap.add_argument("--catalog", default=os.path.join(root, "catalog", "catalog.json"))
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    dos = load_json(a.dossier)
    codes = load_catalog_codes(a.catalog)
    issues, dos = validate(dos, codes)
    blk = sum(1 for s, _ in issues if s == BLOCKER)
    wrn = len(issues) - blk
    print("VALIDATIE: status = %s  (%d blokkerend, %d waarschuwingen)" % (
        dos.validatie.status.upper(), blk, wrn))
    for sev, msg in issues:
        print("  [%s] %s" % (sev, msg))
    if not issues:
        print("  Geen issues - dossier is sluitend.")
    if a.out:
        save_json(dos, a.out)
        print("  dossier met validatiestatus geschreven naar", a.out)

if __name__ == "__main__":
    main()
