"""
Fingerprint van de MagicPlan-formulierdefinities (taak 015).

Doel: elk geïmporteerd dossier vastleggen bij WELKE stand van de live MagicPlan-forms het hoort,
zonder dat elke gewone import live moet bellen. Twee lagen:

1. Een GEDATEERDE, gecommitte snapshot (`refs/forms_snapshot.json`) — de laatst bevestigde live-stand
   (bron: docs/magicplan-forms-live.md). `stamp_dossier_meta()` gebruikt die snapshot bij elke import
   (CSV/API/hybride) om `Dossier.meta.magicplan_form_fingerprint` +
   `Dossier.meta.magicplan_form_snapshot_datum` te vullen — geen testafhankelijkheid, geen internet.
2. Een EXPLICIETE, aparte live-ververs-actie (`refresh_snapshot_live()` / CLI `--refresh-live`) die de
   ECHTE live forms ophaalt via `magicplan.form_push.fetch_forms/fetch_fields` (vereist .env +
   internet) en de snapshot herschrijft + herdateert. Nooit automatisch aangeroepen (golden rule:
   live API-calls alleen expliciet gevraagd).

Drift-detectie (CI, offline): `tests/run_tests.py` vergelijkt de fingerprint van de gecommitte
snapshot met de fingerprint die `core.mapping_manifest` verwacht (VERWACHTE_SNAPSHOT_FINGERPRINT).
Wijzigt iemand de snapshot (of loopt additions.json/de bulletlijst in magicplan-forms-live.md uit de
pas) zonder de verwachte fingerprint bij te werken, dan faalt die test luid — precies het "drift faalt
luid"-doel van taak 015. Dit vangt drift in het FORM-SPEC-document zelf; het vangt niet stil een
verkeerde live MagicPlan-stand op (dat vereist de aparte, expliciete --refresh-live-controle).
"""
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SNAPSHOT_PATH = os.path.join(HERE, "refs", "forms_snapshot.json")


def load_snapshot(path=DEFAULT_SNAPSHOT_PATH):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _canonical_field(f):
    """Eén veld -> stabiele, sorteerbare vorm (naam + genormaliseerde optielijst)."""
    opts = f.get("options")
    return {"name": f.get("name", ""), "options": sorted(opts) if opts else None}


def _canonical_forms(forms):
    """forms-dict (formnaam -> veldlijst) -> volledig gesorteerde, kanonieke vorm; ongevoelig voor
    volgorde in het bronbestand (alleen de INHOUD moet gelijk blijven om dezelfde fingerprint te geven)."""
    out = {}
    for form_naam, velden in forms.items():
        out[form_naam] = sorted((_canonical_field(f) for f in velden), key=lambda v: v["name"])
    return dict(sorted(out.items()))


def compute_fingerprint(forms):
    """forms-dict -> stabiele sha256-hex-fingerprint (12 tekens, genoeg om drift te signaleren)."""
    canon = _canonical_forms(forms)
    blob = json.dumps(canon, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def snapshot_fingerprint(path=DEFAULT_SNAPSHOT_PATH):
    snap = load_snapshot(path)
    return compute_fingerprint(snap["forms"])


def stamp_dossier_meta(dos, path=DEFAULT_SNAPSHOT_PATH):
    """Vult meta.magicplan_form_fingerprint + meta.magicplan_form_snapshot_datum + meta.
    magicplan_import_op op basis van de gecommitte snapshot (offline, geen live call). Aan te roepen
    vanuit elke MagicPlan-importroute (statistics_csv.build_dossier / assemble.build_dossier /
    extractor.map_plan_to_dossier)."""
    import datetime
    snap = load_snapshot(path)
    dos.meta.magicplan_form_fingerprint = compute_fingerprint(snap["forms"])
    dos.meta.magicplan_form_snapshot_datum = snap.get("_meta", {}).get("snapshot_datum", "")
    dos.meta.magicplan_import_op = datetime.datetime.now().isoformat(timespec="seconds")
    return dos


# ---------------- live refresh (expliciet, los, vereist .env + internet) ----------------
def refresh_snapshot_live(path=DEFAULT_SNAPSHOT_PATH):
    """Haalt de ECHTE live custom-forms + custom-fields op (form_push.fetch_forms/fetch_fields) en
    herschrijft de snapshot met de huidige veldnamen + opties, herdateerd op vandaag. Vereist .env
    (MAGICPLAN_API_KEY/MAGICPLAN_CUSTOMER_ID) + internet -> NOOIT vanuit build_dossier of tests
    aangeroepen; alleen via `python -m magicplan.form_fingerprint --refresh-live`."""
    import datetime
    from magicplan.form_push import _load_env, fetch_forms, fetch_fields

    env = _load_env()
    forms_out = {}
    for record in fetch_forms(env):
        naam = (record.get("name") or record.get("name_escaped") or "onbekend")
        velden = []
        for q in record.get("fields", record.get("questions", [])) or []:
            velden.append({"name": q.get("name", ""), "options": q.get("options") or None})
        forms_out[naam] = velden
    for record in fetch_fields(env):
        naam = (record.get("name") or record.get("name_escaped") or "onbekend")
        velden = []
        for q in record.get("fields", record.get("questions", [])) or []:
            velden.append({"name": q.get("name", ""), "options": q.get("options") or None})
        forms_out.setdefault(naam, velden)

    snap = {
        "_meta": {
            "snapshot_datum": datetime.date.today().isoformat(),
            "bron": "LIVE refresh via magicplan.form_push.fetch_forms/fetch_fields",
            "waarschuwing": "Automatisch ververst; controleer de diff voor je 'm commit.",
        },
        "forms": forms_out,
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(snap, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")
    return snap


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--refresh-live", action="store_true",
                     help="Haal de ECHTE live forms op en herschrijf de snapshot (vereist .env + internet).")
    ap.add_argument("--print-fingerprint", action="store_true",
                     help="Print de fingerprint van de huidige (gecommitte) snapshot en stop.")
    args = ap.parse_args()
    if args.refresh_live:
        snap = refresh_snapshot_live()
        print("Snapshot ververst -> %s (fingerprint %s)" % (
            snap["_meta"]["snapshot_datum"], compute_fingerprint(snap["forms"])))
    elif args.print_fingerprint:
        print(snapshot_fingerprint())
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
