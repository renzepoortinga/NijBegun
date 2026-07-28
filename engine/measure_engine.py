"""
Maatregel-engine v1.1: kiest per schildeel de goedkoopste TOEPASSELIJKE hoofdmaatregel uit
de Maatregelencatalogus, op basis van Rc/U-drempels (werkt dus ook op VABI-monitordata).
De integrale Standaard (kWh/m2.jr) wordt door Vabi EPA-W bevestigd; deze engine kiest niet
blind 'elk vlak naar streefwaarde' (zou een spouw naar Rc 6 forceren = onnodig duur).
RVO-streefwaarden (referentie): dak Rc 8, gevel Rc 6, vloer Rc 3,5, glas U 1,2.
"""
import os, sys, json, re, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.dossier import load_json, save_json, Maatregel  # noqa

STREEF = {"dak": "Rc 8", "gevel": "Rc 6", "vloer": "Rc 3,5", "kozijn": "U 1,2"}
ONDERDEEL = {"V1": "A Gevel", "V2": "B Glas en kozijnen", "V3": "C Vloeren",
             "V4": "D Daken", "V5": "E Ventilatie"}
# Rc/U-drempels: onder deze waarde stelt de engine een maatregel voor
RC_TRIGGER = {"gevel": 2.5, "vloer": 2.5, "dak": 3.5}
U_TRIGGER_GLAS = 1.6
DELTA_MARK = "╚"
EXCLUDE = ("toeslag", "natuurvrij", "rooster", "opdikken", "meerwerk", "demont",
           "steiger", "hoogwerker", "verwijder", "afwerk", "herstel", "boorplan",
           "beveiliging", "dakrand", "sloop", "plaatsen", "leeghalen", "knieschot")
# meerwerk-subposten = de X-codes binnen een maatregelfamilie (V1-1-X5, V3-1-X9, ...).
# Dat scheidt meerwerk schoon van alternatieve kern-varianten (A/B/C-codes).
# zwaarder/bijzonder meerwerk -> categorie 3 (overig meerwerk -> categorie 2)
CAT3_KW = ("hoogwerker", "steiger", "rolsteiger", "mangat", "kruipluik", "sloop", "demont",
           "verwijder", "dakrand", "beveiliging", "dichtmaken", "knieschot", "leeghalen")
# administratieve/prijs-rijen (geen fysiek meerwerk) -> niet als subpost voorstellen
ADMIN_SKIP = ("minimum tarief", "minimaal tarief", "starttarief", "inmeten",
              "opname voor begin", "bijkomende kosten")

def is_delta(m):
    o = (m.get("omschrijving") or "")
    return o.strip().startswith(DELTA_MARK) or "meer-/minderprijs" in o.lower()
def price_incl(m):
    return m.get("prijs_per_eenheid_incl_btw") or m.get("prijs_per_eenheid_excl")

def _isolated_status(s):
    # 'Invoer = Kwaliteitsverklaring' betekent: er is AANTOONBAAR isolatie (met een gedeclareerde Rc).
    # MagicPlan slaat dan de vraag 'isolatie aanwezig?' over (die hangt onder Beslisschema), waardoor
    # het veld leeg/Onbekend bleef en de tool tóch isolatie voorstelde op een al geïsoleerd dak/vloer
    # (Essenhage 27-7). De Rc zelf komt uit de verklaring -> die zet de adviseur in Vabi.
    if (getattr(s, "rc_bron", "") or "").lower().startswith("kwaliteitsverklaring"):
        return True
    return s.isolatie_aanwezig in ("Wel", "Ja")   # nieuw vocab Ja/Nee + oud Wel/Niet

def element_spec(s):
    """(prefixes, trefwoorden, assumpties) als maatregel nodig; anders None."""
    t = s.type
    if t == "gevel":
        if _isolated_status(s):
            return None
        if s.rc_huidig is not None and s.rc_huidig >= RC_TRIGGER["gevel"]:
            return None
        # spouw onbekend -> aanname spouwvulling (meest voorkomend/goedkoopst); markeer
        if s.spouw_aanwezig is False:
            return (["V1-2", "V1-3"], ["gevelisolatie"], "")
        note = "" if s.spouw_aanwezig else "AANNAME: spouw aanwezig (controleer in opname)"
        return (["V1-1"], ["spouwmuurisolatie", "spouwisolatie"], note)
    if t == "vloer":
        if _isolated_status(s): return None
        if s.rc_huidig is not None and s.rc_huidig >= RC_TRIGGER["vloer"]: return None
        return (["V3"], ["vloerisolatie", "bodemisolatie"], "")
    if t == "dak":
        if _isolated_status(s): return None
        if s.rc_huidig is not None and s.rc_huidig >= RC_TRIGGER["dak"]: return None
        plat = "plat" in (s.subtype or "").lower()
        return (["V4-2"] if plat else ["V4-1"], ["dakisolatie"], "")
    if t == "kozijn":
        glas = (s.glastype or "").lower()
        if s.u_huidig is not None:
            if s.u_huidig <= U_TRIGGER_GLAS: return None       # al HR++/triple
        elif glas in ("hr++", "triple", "hr+"): return None
        if "deur" in (s.subtype or "").lower(): return None     # deuren v1 overslaan
        return (["V2"], ["hr++", "triple", "glas"], "")
    return None

def bracket_match(oms, m2):
    o = oms.lower()
    mt = re.search(r'van\s*([\d.]+)\s*m².?\s*tot\s*([\d.]+)\s*m²', o)
    if mt: return float(mt.group(1)) <= m2 < float(mt.group(2))
    mt = re.search(r'vanaf\s*([\d.]+)\s*m²', o)
    if mt: return m2 >= float(mt.group(1))
    mt = re.search(r'tot\s*([\d.]+)\s*m²', o)
    if mt: return m2 < float(mt.group(1))
    return None

def select_core(catalog, prefixes, keywords, m2):
    def ok(m):
        o = (m["omschrijving"] or "").lower()
        return (any(m["code"].startswith(p) for p in prefixes) and not is_delta(m)
                and (price_incl(m) or 0) > 0 and any(k in o for k in keywords)
                and not any(x in o for x in EXCLUDE))
    cand = [m for m in catalog["maatregelen"] if ok(m)]
    if not cand: return None
    exact = [m for m in cand if bracket_match(m["omschrijving"], m2) is True]
    return min(exact or cand, key=lambda m: price_incl(m))


def _family(code):
    parts = code.split("-")
    return "-".join(parts[:2]) if len(parts) >= 2 else code

def _is_meerwerk_code(code):
    return code.split("-")[-1][:1].upper() == "X"   # X-serie = meerwerk binnen de familie

def propose_subposten(catalog, maatregel):
    """Voorgestelde cat 2/3 meerwerk-subposten uit dezelfde maatregelfamilie (prijs per eenheid
    ingevuld; hoeveelheid 0 -> de adviseur vult die aan en bevestigt). Alleen de X-meerwerkrijen
    (plus zware trefwoorden als steiger/hoogwerker); kern-varianten en delta-rijen worden
    overgeslagen."""
    from core.dossier import Subpost
    fam = _family(maatregel.code) + "-"
    out, seen = [], set()
    for m in catalog["maatregelen"]:
        c = m["code"]
        if not c.startswith(fam) or c == maatregel.code or c in seen or is_delta(m):
            continue
        o = (m.get("omschrijving") or ""); ol = o.lower()
        if not (_is_meerwerk_code(c) or any(k in ol for k in CAT3_KW)):
            continue
        if any(k in ol for k in ADMIN_SKIP):
            continue
        prijs = price_incl(m)
        if not prijs or prijs <= 0:
            continue
        seen.add(c)
        out.append(Subpost(categorie=(3 if any(k in ol for k in CAT3_KW) else 2),
                           code=c, omschrijving=o.rstrip(), prijs_per_eenheid=round(prijs, 2),
                           eenheid=m.get("eenheid", "m²") or "m²", hoeveelheid=0.0, kosten=None))
    out.sort(key=lambda s: s.categorie)   # cat 2 eerst (zodat het template de juiste rij pakt)
    return out

def qv10_advies(dos):
    jaar = dos.identificatie.renovatiejaar or dos.identificatie.bouwjaar or 0
    if dos.opname.qv10_gemeten and dos.opname.qv10_waarde:
        return "qv;10 gemeten = %s dm3/s.m2 -> gebruik deze waarde in Vabi EPA-W." % dos.opname.qv10_waarde
    bron = "renovatiejaar %s" % dos.identificatie.renovatiejaar if dos.identificatie.renovatiejaar else "bouwjaar %s" % jaar
    return ("qv;10 niet gemeten -> forfaitair o.b.v. %s. LET OP: bij >=90%% vernieuwde buitenschil mag een "
            "renovatiejaar (volgende bouwjaarklasse) worden toegepast; een kierdichtingspakket + (na 1983) "
            "blowerdoortest verlaagt qv;10 (richt op ~1,5-2,0) en is vaak nodig om de Standaard te halen. "
            "Stel de qv;10 dienovereenkomstig in Vabi EPA-W in." % bron)

def propose_kierdichting(dos, catalog):
    out = []
    if dos.opname.qv10_gemeten:
        return out
    jaar = dos.identificatie.renovatiejaar or dos.identificatie.bouwjaar or 0
    if jaar >= 1983:
        hit = next((m for m in catalog["maatregelen"] if m["code"] == "V6-1-X1"), None)
        if hit:
            prijs = hit.get("prijs_per_eenheid_incl_btw") or hit.get("prijs_per_eenheid_excl") or 0
            out.append(Maatregel(code="V6-1-X1", onderdeel="E Ventilatie",
                       omschrijving=hit["omschrijving"].rstrip(), rc_u_doel="qv;10 ~1,5",
                       oppervlakte_m2=1, eenheid="pst", prijs_per_eenheid=round(prijs, 2),
                       kosten=round(prijs, 2), categorie=1))
    return out

def run(dossier, catalog, propose_meerwerk=True):
    groups = {}
    notes = set()
    for s in dossier.schil:
        spec = element_spec(s)
        if not spec: continue
        prefixes, keywords, note = spec
        if note: notes.add(note)
        key = tuple(prefixes)
        g = groups.setdefault(key, {"prefixes": prefixes, "keywords": keywords, "m2": 0.0, "type": s.type})
        g["m2"] += s.oppervlakte_m2 or 0.0
    maatregelen = []
    for g in groups.values():
        m2 = round(g["m2"], 2)
        hit = select_core(catalog, g["prefixes"], g["keywords"], m2)
        if not hit: continue
        prijs = round(price_incl(hit), 2)
        maat = Maatregel(
            code=hit["code"], onderdeel=ONDERDEEL.get(hit["code"][:2], ""),
            omschrijving=hit["omschrijving"].rstrip(), materiaal="",
            rc_u_doel=STREEF.get(g["type"], ""), oppervlakte_m2=m2,
            eenheid=hit.get("eenheid", "m²") or "m²",
            prijs_per_eenheid=prijs, kosten=round(prijs * m2, 2), categorie=1)
        if propose_meerwerk:
            maat.subposten = propose_subposten(catalog, maat)
        maatregelen.append(maat)
    maatregelen += propose_kierdichting(dossier, catalog)
    maatregelen.sort(key=lambda x: x.onderdeel)
    dossier.maatregelen = maatregelen
    notes.add(qv10_advies(dossier))
    return dossier, sorted(notes)

def main():
    here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
    ap = argparse.ArgumentParser()
    ap.add_argument("--dossier", default=os.path.join(root, "sample_dossier.json"))
    ap.add_argument("--catalog", default=os.path.join(root, "catalog", "catalog.json"))
    ap.add_argument("--out", default=os.path.join(root, "sample_dossier_auto.json"))
    a = ap.parse_args()
    dossier = load_json(a.dossier)
    catalog = json.load(open(a.catalog, encoding="utf-8"))
    dossier, notes = run(dossier, catalog)
    save_json(dossier, a.out)
    tot = sum((m.kosten or 0) for m in dossier.maatregelen)
    print("OK: " + a.out)
    for m in dossier.maatregelen:
        print("    %-9s %-32s %6.1f m2 x EUR%-7s = EUR%s"
              % (m.code, m.omschrijving[:32], m.oppervlakte_m2, m.prijs_per_eenheid, m.kosten))
    print("  TOTAAL incl. btw: EUR %.2f" % tot)
    for n in notes: print("  [!]", n)

if __name__ == "__main__":
    main()
