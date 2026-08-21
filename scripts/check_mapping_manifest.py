"""
Mappingmanifest-drift-checker (taak 015).

Valideert `core/mapping_manifest.py` tegen de ECHTE code waar het naar verwijst, en genereert/
controleert `docs/mapping-overview.md` uit het manifest. Puur offline (geen live MagicPlan/VABI-
calls) — gebruikt de dossier-canon-dicts, webapp-optielijsten en het VABI-codebook (dat zichzelf al
afleidt uit een echte export) die al in de repo staan.

Gebruik:
    python scripts/check_mapping_manifest.py            # alle checks, exit 1 bij drift
    python scripts/check_mapping_manifest.py --write-doc # herschrijf docs/mapping-overview.md
    python scripts/check_mapping_manifest.py --check-doc # faalt als de doc niet meer bij het manifest past

Wat WEL gecontroleerd wordt:
  - elke `parser_canon`/`webapp_opties`/`vabi_codes`-referentie bestaat nog (module/attribuut) —
    een hernoemde of verwijderde dict/functie laat dit meteen luid falen.
  - parser -> webapp: elke canonieke waarde die de parser kan produceren, staat als optie in de
    webapp-`<select>` (anders toont de select stil de eerste optie en overschrijft opslaan de echte
    waarde — het exacte patroon uit de kozijnmateriaal-bug, aannames-audit 30-7 + 21-8).
  - vabi_codes (waar een dict): elke code is een niet-lege string (VABI-codes zijn altijd string-
    integers in dit project; een lege/None-code betekent 'nog niet bevestigd' en hoort NIET in de
    code-dict te staan, maar in de golden-rule-flaglogica van de generator).
  - Codebook-afgeleide velden (glas/kozijn): elke canonieke webapp-optie moet een code opleveren via
    de bijbehorende Codebook-methode (zelf afgeleid uit een echte VABI-export) — dat vangt drift
    tussen de webapp-optielijst en wat VABI daadwerkelijk kent.

Wat NIET gecontroleerd wordt (bewust, golden rule): of een `vabi_codes`-code zelf de juiste
BETEKENIS heeft in VABI — dat is mensenwerk (live EPA-import), vastgelegd in `bron_doc` per entry.
Dit script signaleert AFWIJKING, het bevestigt geen nieuwe waarheid.
"""
import argparse
import functools
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.mapping_manifest import MANIFEST, resolve  # noqa: E402

DOC_PATH = os.path.join(ROOT, "docs", "mapping-overview.md")


class DriftError(Exception):
    pass


@functools.lru_cache(maxsize=1)
def _codebook():
    # Parseert de 219-constructie XML-export -- 1x per proces (meerdere manifest-entries gebruiken
    # 'm; niet per entry opnieuw parsen, mappingmanifest-audit 21-8).
    from vabi.codebook import Codebook
    return Codebook.default()


def check_references(entry, errors):
    """Elke code-referentie moet nog bestaan (module + attribuut)."""
    for veldnaam in ("parser_canon", "webapp_opties", "vabi_codes", "vabi_codes_normalizer"):
        ref = getattr(entry, veldnaam)
        if ref is None or ref.startswith("vabi.codebook:"):
            continue
        try:
            resolve(ref)
        except Exception as exc:
            errors.append("%s: referentie %s=%r bestaat niet meer (%s)" % (entry.id, veldnaam, ref, exc))


def _canon_values(entry):
    """De set canonieke waarden die de parser voor deze entry kan opleveren."""
    if not entry.parser_canon or entry.parser_canon.startswith("vabi.codebook:"):
        return None
    obj = resolve(entry.parser_canon)
    if isinstance(obj, dict):
        return set(obj.values())
    return None


def check_parser_vs_webapp(entry, errors):
    """Elke waarde die de parser kan produceren, moet als optie in de webapp-<select> staan —
    anders overschrijft een webapp-save de waarde stil met de default (audit 30-7/21-8)."""
    if not entry.webapp_opties:
        return
    canon = _canon_values(entry)
    if canon is None:
        return
    opts = set(resolve(entry.webapp_opties))
    ontbreekt = canon - opts
    if ontbreekt:
        errors.append(
            "%s: parser kan %s produceren, maar dat ontbreekt in de webapp-optielijst %s "
            "(select toont dan stil de eerste optie en save overschrijft de echte waarde)"
            % (entry.id, sorted(ontbreekt), entry.webapp_opties))


def check_vabi_codes(entry, errors):
    ref = entry.vabi_codes
    if ref is None:
        return
    if ref.startswith("vabi.codebook:"):
        # Codebook-afgeleide velden: elke webapp-optie moet een code opleveren via de bijbehorende
        # methode (zelfvaliderend uit de echte VABI-export -- geen hardcoded codes om te vergelijken).
        # Loopt via dezelfde normalisatiefunctie als de echte generator (vabi_codes_normalizer),
        # anders krijgt de raw webapp-labeltekst tegen het codebook-trefwoord vergeleken, wat NIET is
        # hoe de generator het doet (zie vabi/constructie_generate.py::pick_raam).
        _, _, methode = ref.partition(":")
        cb = _codebook()
        fn = getattr(cb, methode.split(".")[-1])
        normalizer = resolve(entry.vabi_codes_normalizer) if entry.vabi_codes_normalizer else (lambda x: x)
        if entry.webapp_opties:
            for optie in resolve(entry.webapp_opties):
                if not optie or optie in entry.vabi_onbevestigde_opties:
                    continue
                code = fn(normalizer(optie))
                if code is None:
                    errors.append(
                        "%s: webapp-optie %r levert GEEN VABI-code op via %s (Codebook kent 'm niet "
                        "-- of de optietekst is gedrift van het trefwoord in vabi/codebook.py of "
                        "vabi/constructie_generate.py). Is dit BEWUST onbevestigd, voeg 'm toe aan "
                        "vabi_onbevestigde_opties in het manifest." % (entry.id, optie, ref))
        return
    codes = resolve(ref)
    if isinstance(codes, dict):
        for label, code in codes.items():
            if not code or not isinstance(code, str):
                errors.append("%s: code-dict %s heeft een lege/ongeldige code voor %r=%r"
                              % (entry.id, ref, label, code))
        if entry.webapp_opties:
            # zelfde lookup als de generator: kompas-/labelstring lowercase-genormaliseerd (zie bv.
            # vabi.objecten_generate._orient_code / _grenst_aan_code) tegen de code-dict.
            for optie in resolve(entry.webapp_opties):
                if not optie or optie in entry.vabi_onbevestigde_opties:
                    continue
                if codes.get(optie.strip().lower()) is None:
                    errors.append(
                        "%s: webapp-optie %r levert GEEN VABI-code op uit %s (lowercase-lookup). Is "
                        "dit BEWUST onbevestigd, voeg 'm toe aan vabi_onbevestigde_opties."
                        % (entry.id, optie, ref))
    elif callable(codes) and entry.webapp_opties:
        # functie-vorm (bv. _subtype_code): elke webapp-optie -> code, tenzij bewust onbevestigd
        # (golden rule: buiten Nij Begun-scope of nog niet in EPA geverifieerd).
        for optie in resolve(entry.webapp_opties):
            if not optie or optie in entry.vabi_onbevestigde_opties:
                continue
            if codes(optie) is None:
                errors.append(
                    "%s: webapp-optie %r levert GEEN VABI-code op via %s. Is dit BEWUST onbevestigd, "
                    "voeg 'm toe aan vabi_onbevestigde_opties in het manifest."
                    % (entry.id, optie, ref))


def run_checks():
    errors = []
    for entry in MANIFEST:
        check_references(entry, errors)
        check_parser_vs_webapp(entry, errors)
        check_vabi_codes(entry, errors)
    return errors


# ---------------- documentatie-generatie ----------------
def _fmt_ref(ref):
    return "`%s`" % ref if ref else "—"


def render_doc():
    lines = [
        "# Mappingoverzicht (gegenereerd)",
        "",
        "**NIET handmatig bewerken** — dit bestand wordt gegenereerd uit `core/mapping_manifest.py`",
        "via `python scripts/check_mapping_manifest.py --write-doc`. Wijzig het manifest, niet deze",
        "tabel; `--check-doc` faalt luid als ze uit elkaar lopen.",
        "",
    ]
    for entry in MANIFEST:
        lines += [
            "## %s" % entry.id,
            "",
            "| | |",
            "|---|---|",
            "| Bronform | %s |" % entry.bronform,
            "| Bronlabel | %s |" % entry.bronlabel,
            "| Verplicht | %s |" % entry.verplicht,
            "| Canoniek dossierveld | `%s` |" % entry.canoniek_veld,
            "| Parser-normalisatie | %s |" % _fmt_ref(entry.parser_canon),
            "| Webapp-opties | %s |" % _fmt_ref(entry.webapp_opties),
            "| VABI-pad | %s |" % entry.vabi_pad,
            "| VABI-codes | %s |" % _fmt_ref(entry.vabi_codes),
            "| VABI-codes normalizer | %s |" % _fmt_ref(entry.vabi_codes_normalizer),
            "| Bewust onbevestigde opties | %s |" % (", ".join(entry.vabi_onbevestigde_opties) or "—"),
            "| Bewijsstatus | **%s** |" % entry.bewijsstatus,
            "| Bron | %s |" % entry.bron_doc,
            "",
        ]
    return "\n".join(lines)


def write_doc(path=DOC_PATH):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(render_doc())


def check_doc(path=DOC_PATH):
    if not os.path.exists(path):
        return False
    with open(path, encoding="utf-8") as fh:
        huidig = fh.read()
    return huidig == render_doc()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write-doc", action="store_true", help="Herschrijf docs/mapping-overview.md uit het manifest.")
    ap.add_argument("--check-doc", action="store_true", help="Faal als de doc niet (meer) bij het manifest past.")
    args = ap.parse_args()

    if args.write_doc:
        write_doc()
        print("docs/mapping-overview.md geschreven uit %d manifest-entries." % len(MANIFEST))
        return 0
    if args.check_doc:
        if check_doc():
            print("docs/mapping-overview.md is actueel.")
            return 0
        print("DRIFT: docs/mapping-overview.md komt niet overeen met core/mapping_manifest.py "
              "-- draai: python scripts/check_mapping_manifest.py --write-doc")
        return 1

    errors = run_checks()
    if errors:
        print("DRIFT gevonden (%d):" % len(errors))
        for e in errors:
            print("  -", e)
        return 1
    print("Mappingmanifest: geen drift gevonden (%d entries gecontroleerd)." % len(MANIFEST))
    return 0


if __name__ == "__main__":
    sys.exit(main())
