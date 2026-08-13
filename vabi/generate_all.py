"""
Eén commando: dossier -> alle drie de VABI-bibliotheken (Constructies + Objecten + Installaties),
klaar om te importeren in EPA. Schrijft ook een korte import-instructie.

    python vabi/generate_all.py --dossier out/dossier.json --outdir out/vabi_import

Importvolgorde in EPA (per tegel > Importeren):
  1. Constructies   2. Objecten   3. Installaties
Daarna vul je zelf 'Algemeen' (bouwfase/opname/adres) en druk je op Rekenen.
"""
import os, sys, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.dossier import load_json                                  # noqa: E402
from vabi import constructie_generate, objecten_generate, installatie_generate  # noqa: E402
from vabi.preflight import assert_no_schil_kwaliteitsverklaring            # noqa: E402


def generate_all(dos, outdir, prefix=""):
    # Vóór mkdir en vóór elk bestand: nooit een gedeeltelijke exportset.
    assert_no_schil_kwaliteitsverklaring(dos)
    os.makedirs(outdir, exist_ok=True)
    p = (prefix + "_") if prefix else ""
    res = {}
    cpath = os.path.join(outdir, "%sConstructiebibliotheek.xml" % p)
    cmap, ciss = constructie_generate.write(dos, cpath)
    res["constructies"] = (cpath, len({m["naam"] for m in cmap.values()}), ciss)
    opath = os.path.join(outdir, "%sObjectenbibliotheek.xml" % p)
    omap, oiss, ostats = objecten_generate.write(dos, opath)
    res["objecten"] = (opath, ostats, oiss)
    ipath = os.path.join(outdir, "%sInstallatiebibliotheek.xml" % p)
    iflags = installatie_generate.write(dos, ipath)
    res["installaties"] = (ipath, None, iflags)
    # import-instructie
    readme = os.path.join(outdir, "IMPORTEREN.txt")
    with open(readme, "w", encoding="utf-8") as fh:
        fh.write("VABI-import (EPA 12.x) - importvolgorde:\n")
        fh.write("  0. EERST Algemeen invullen: Objecttype=Woning, Bouwfase=Bestaande bouw,\n")
        fh.write("     Opname=Basisopname. Laat je Bouwfase/Opname leeg, dan WEIGERT EPA de\n")
        fh.write("     objecten-import ('komen niet overeen met de waarden van de objecten').\n")
        fh.write("  1. Constructies > Importeren  -> %sConstructiebibliotheek.xml\n" % p)
        fh.write("  2. Objecten     > Importeren  -> %sObjectenbibliotheek.xml\n" % p)
        fh.write("  3. Installaties > Importeren  -> %sInstallatiebibliotheek.xml\n" % p)
        fh.write("Daarna: Algemeen aanvullen (adres/opdrachtgever) -> Rekenen.\n")
        # alle generator-flags mee het bestand in: dit is de ZELF-DOEN-IN-VABI-lijst
        alle_flags = []
        for _k in ("constructies", "objecten", "installaties"):
            _t = res.get(_k)
            if _t and _t[-1]:
                for x in _t[-1]:            # ontdubbel (resolve_constructies draait 2x)
                    if str(x) not in alle_flags:
                        alle_flags.append(str(x))
        if alle_flags:
            fh.write("\nZELF DOEN IN VABI (%d actiepunten):\n" % len(alle_flags))
            for a in alle_flags:
                fh.write("  - %s\n" % a)
    res["readme"] = readme
    return res


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser(description="Dossier -> alle 3 VABI-bibliotheken")
    ap.add_argument("--dossier", required=True)
    ap.add_argument("--outdir", default=os.path.join(root, "out", "vabi_import"))
    ap.add_argument("--prefix", default="")
    a = ap.parse_args()
    dos = load_json(a.dossier)
    res = generate_all(dos, a.outdir, a.prefix)
    print("VABI-bibliotheken gegenereerd in: %s\n" % a.outdir)
    cpath, cn, ciss = res["constructies"]
    print("  Constructies  : %d types  -> %s" % (cn, os.path.basename(cpath)))
    opath, ostats, oiss = res["objecten"]
    print("  Objecten      : %d gevels + %d deelvlakken -> %s" % (
        ostats["hoofdvlakken"], ostats["deelvlakken_geplaatst"], os.path.basename(opath)))
    ipath, _, iflags = res["installaties"]
    print("  Installaties  : -> %s" % os.path.basename(ipath))
    # ontdubbel (constructie- én objecten-generator roepen beide match_constructies -> zelfde issues)
    _seen, allflags = set(), []
    for f in (ciss or []) + (oiss or []) + (iflags or []):
        if f not in _seen:
            _seen.add(f); allflags.append(f)
    if allflags:
        print("\n  Aandachtspunten (adviseur verifieert in Vabi):")
        for f in allflags:
            print("    ! " + f)
    print("\n  Zie %s voor de importvolgorde." % os.path.basename(res["readme"]))


if __name__ == "__main__":
    main()
