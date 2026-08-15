"""Genereer en publiceer een complete, atomische VABI-importset."""
import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import uuid
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.dossier import load_json  # noqa: E402
from vabi import constructie_generate, objecten_generate, installatie_generate  # noqa: E402
from vabi.preflight import (  # noqa: E402
    assert_no_dubbel_dak_fallback,
    assert_no_schil_kwaliteitsverklaring,
)

MANIFEST = "CURRENT.json"
SETS_DIR = "sets"
_PREFIX_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def _write_instructions(path, prefix, res):
    p = (prefix + "_") if prefix else ""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("VABI-import (EPA 12.x) - importvolgorde:\n")
        fh.write("  0. EERST Algemeen invullen: Objecttype=Woning, Bouwfase=Bestaande bouw,\n")
        fh.write("     Opname=Basisopname. Laat je Bouwfase/Opname leeg, dan WEIGERT EPA de\n")
        fh.write("     objecten-import ('komen niet overeen met de waarden van de objecten').\n")
        fh.write("  1. Constructies > Importeren  -> %sConstructiebibliotheek.xml\n" % p)
        fh.write("  2. Objecten     > Importeren  -> %sObjectenbibliotheek.xml\n" % p)
        fh.write("  3. Installaties > Importeren  -> %sInstallatiebibliotheek.xml\n" % p)
        fh.write("Daarna: Algemeen aanvullen (adres/opdrachtgever) -> Rekenen.\n")
        flags = []
        for key in ("constructies", "objecten", "installaties"):
            for flag in (res.get(key) or (None, None, []))[-1] or []:
                if str(flag) not in flags:
                    flags.append(str(flag))
        if flags:
            fh.write("\nZELF DOEN IN VABI (%d actiepunten):\n" % len(flags))
            for flag in flags:
                fh.write("  - %s\n" % flag)


def _validate_set(setdir, filenames):
    """Valideer de complete set voordat de zichtbare pointer wisselt."""
    for name in filenames[:3]:
        path = os.path.join(setdir, name)
        if not os.path.isfile(path) or os.path.getsize(path) == 0:
            raise ValueError("Ontbrekend of leeg VABI-exportbestand: %s" % name)
        ET.parse(path)
    readme = os.path.join(setdir, filenames[3])
    if not os.path.isfile(readme) or os.path.getsize(readme) == 0:
        raise ValueError("Ontbrekende of lege VABI-importinstructie")


def current_set_dir(outdir):
    """Geef de gepubliceerde set terug; ``None`` als er nog geen is."""
    manifest = os.path.join(outdir, MANIFEST)
    if not os.path.isfile(manifest):
        return None
    with open(manifest, encoding="utf-8") as fh:
        data = json.load(fh)
    set_id = data.get("set_id")
    if not isinstance(set_id, str) or not set_id or set_id != os.path.basename(set_id):
        raise ValueError("Ongeldig VABI-exportmanifest")
    path = os.path.join(outdir, SETS_DIR, set_id)
    if not os.path.isdir(path):
        raise ValueError("VABI-exportmanifest verwijst naar ontbrekende set")
    return path


def generate_all(dos, outdir, prefix=""):
    if prefix and (not isinstance(prefix, str) or not _PREFIX_RE.fullmatch(prefix)):
        raise ValueError("Ongeldige VABI-bestandsprefix")
    assert_no_schil_kwaliteitsverklaring(dos)
    assert_no_dubbel_dak_fallback(dos)
    os.makedirs(outdir, exist_ok=True)
    sets_root = os.path.join(outdir, SETS_DIR)
    os.makedirs(sets_root, exist_ok=True)
    staging = tempfile.mkdtemp(prefix=".staging-", dir=sets_root)
    set_id = uuid.uuid4().hex
    published = os.path.join(sets_root, set_id)
    manifest_tmp = None
    visible = False
    p = (prefix + "_") if prefix else ""
    names = [p + "Constructiebibliotheek.xml", p + "Objectenbibliotheek.xml",
             p + "Installatiebibliotheek.xml", "IMPORTEREN.txt"]
    try:
        res = {}
        cpath = os.path.join(staging, names[0])
        cmap, ciss = constructie_generate.write(dos, cpath)
        res["constructies"] = (cpath, len({m["naam"] for m in cmap.values()}), ciss)
        opath = os.path.join(staging, names[1])
        _omap, oiss, ostats = objecten_generate.write(dos, opath)
        res["objecten"] = (opath, ostats, oiss)
        ipath = os.path.join(staging, names[2])
        iflags = installatie_generate.write(dos, ipath)
        res["installaties"] = (ipath, None, iflags)
        _write_instructions(os.path.join(staging, names[3]), prefix, res)
        _validate_set(staging, names)

        os.replace(staging, published)
        staging = None
        fd, manifest_tmp = tempfile.mkstemp(prefix=".CURRENT-", suffix=".json", dir=outdir)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"version": 1, "set_id": set_id, "files": names}, fh, indent=2)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(manifest_tmp, os.path.join(outdir, MANIFEST))
        manifest_tmp = None
        visible = True
        # Resultaatpaden horen bij de nu gepubliceerde immutable set.
        for key in ("constructies", "objecten", "installaties"):
            old = res[key]
            res[key] = (os.path.join(published, os.path.basename(old[0])),) + old[1:]
        res["readme"] = os.path.join(published, names[3])
        res["set_dir"] = published
        return res
    except Exception:
        # Een set die nog niet via CURRENT.json zichtbaar is, mag weg.
        if not visible and os.path.isdir(published):
            shutil.rmtree(published, ignore_errors=True)
        raise
    finally:
        if staging and os.path.isdir(staging):
            shutil.rmtree(staging, ignore_errors=True)
        if manifest_tmp:
            try:
                os.unlink(manifest_tmp)
            except FileNotFoundError:
                pass


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser(description="Dossier -> alle 3 VABI-bibliotheken")
    ap.add_argument("--dossier", required=True)
    ap.add_argument("--outdir", default=os.path.join(root, "out", "vabi_import"))
    ap.add_argument("--prefix", default="")
    args = ap.parse_args()
    res = generate_all(load_json(args.dossier), args.outdir, args.prefix)
    print("VABI-bibliotheken gegenereerd in: %s" % res["set_dir"])
    cpath, count, _cflags = res["constructies"]
    print("  Constructies  : %d types  -> %s" % (count, os.path.basename(cpath)))
    opath, stats, _oflags = res["objecten"]
    print("  Objecten      : %d gevels + %d deelvlakken -> %s" % (
        stats["hoofdvlakken"], stats["deelvlakken_geplaatst"], os.path.basename(opath)))
    print("  Installaties  : -> %s" % os.path.basename(res["installaties"][0]))
    seen, flags = set(), []
    for flag in (_cflags or []) + (_oflags or []) + (res["installaties"][2] or []):
        if flag not in seen:
            seen.add(flag)
            flags.append(flag)
    if flags:
        print("\n  Aandachtspunten (adviseur verifieert in Vabi):")
        for flag in flags:
            print("    ! " + flag)
    print("\n  Zie %s voor de importvolgorde." % os.path.basename(res["readme"]))


if __name__ == "__main__":
    main()
