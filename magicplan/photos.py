"""
MagicPlan-foto's ophalen en lokaal opslaan voor het Nij Begun-fotoblad.

De MagicPlan REST v2 levert per project een plan met een foto-container (photos/images/fotos). Per foto
staat er doorgaans een directe (gesigneerde) URL in; soms alleen een id. Deze module NORMALISEERT de
foto-entries en downloadt de bytes naar out/projects/<tag>/fotos/ met een sprekende bestandsnaam
(volgnummer + bouwdeel), en levert Foto-objecten terug voor het dossier/fotoblad.

Ontwerp (zelfde golden rule als de rest van de MagicPlan-keten): we GOKKEN geen foto-endpoint. Zit er een
directe URL in de foto-entry -> die downloaden we (met de v2-headers key+customer). Zit er alleen een id
zonder URL -> dan flaggen we dat, zodat je 1x live het exacte foto-endpoint bevestigt i.p.v. te raden.

- Offline testbaar: `photo_entries(plan)` + `download_photos(entries, outdir, fetch)` met een injecteerbare
  fetch-callable (geen internet nodig).
- Live (Renze, .env + internet): `fetch_project_photos(project_id, outdir)` gebruikt de MagicPlanClient.
- AVG: foto's blijven LOKAAL op de adviseur-machine (out/ is git-ignored).

CLI:
    python magicplan/photos.py --project-id <ID> --tag <postcode_huisnr>   # -> out/projects/<tag>/fotos/
    python magicplan/photos.py --plan-json plan.json --out out/fotos       # offline mappen van een plan
"""
import os
import re
import sys
import json
import argparse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.dossier import Foto  # noqa: E402

TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT_OK = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif"}
# containers waar MagicPlan foto's kan plaatsen (zelfde defensieve aanpak als extractor.EXPECTED_CONTAINERS)
PHOTO_KEYS = ("photos", "images", "fotos", "pictures", "attachments")
URL_KEYS = ("url", "href", "downloadUrl", "download_url", "signedUrl", "src")
ID_KEYS = ("id", "photoId", "uuid", "attachmentId")
BOUWDEEL_KEYS = ("bouwdeel", "room", "category", "section", "group")
TAG_KEYS = ("tag", "label", "type", "name")


def _first(node, names):
    for n in names:
        if isinstance(node, dict) and node.get(n) not in (None, ""):
            return node[n]
    return None


def photo_entries(plan):
    """Plan-JSON -> lijst genormaliseerde foto-dicts: {url,id,file,bouwdeel,tag}.
    Zoekt de foto-container op topniveau en (defensief) één niveau diep in list-velden."""
    raw = _first(plan, PHOTO_KEYS)
    if raw is None and isinstance(plan, dict):
        for v in plan.values():                       # 1 niveau diep zoeken (bv. plan['project']['photos'])
            if isinstance(v, dict) and _first(v, PHOTO_KEYS) is not None:
                raw = _first(v, PHOTO_KEYS)
                break
    out = []
    for ph in (raw or []):
        if not isinstance(ph, dict):
            continue
        out.append({
            "url": _first(ph, URL_KEYS) or "",
            "id": str(_first(ph, ID_KEYS) or ""),
            "file": ph.get("file") or ph.get("filename") or ph.get("fileName") or "",
            "bouwdeel": str(_first(ph, BOUWDEEL_KEYS) or "-"),
            "tag": str(_first(ph, TAG_KEYS) or "overzicht"),
        })
    return out


def _ext_uit_url(url):
    m = re.search(r"\.(jpe?g|png|webp|heic|gif)(?:\?|#|$)", url or "", re.I)
    return ("." + m.group(1).lower()) if m else ".jpg"


def veilige_naam(entry, i):
    """Sprekende, bestandssysteem-veilige naam: '01_voorgevel_IMG1234.jpg'."""
    basis = os.path.basename(str(entry.get("file") or entry.get("id") or ("foto_%d" % (i + 1))))
    basis = re.sub(r"[^A-Za-z0-9._-]+", "_", basis).strip("_") or ("foto_%d" % (i + 1))
    if os.path.splitext(basis)[1].lower() not in EXT_OK:
        basis += _ext_uit_url(entry.get("url", ""))
    bd = re.sub(r"[^A-Za-z0-9]+", "", str(entry.get("bouwdeel", "")))[:14].lower()
    return ("%02d_%s_%s" % (i + 1, bd or "foto", basis))[:90]


def download_photos(entries, outdir, fetch):
    """Download elke foto (fetch(entry)->bytes) naar outdir. -> (fotos:[Foto], fouten:[(sleutel, reden)])."""
    os.makedirs(outdir, exist_ok=True)
    fotos, fouten = [], []
    for i, e in enumerate(entries):
        try:
            data = fetch(e)
            if not data:
                raise ValueError("lege download / geen data")
            naam = veilige_naam(e, i)
            with open(os.path.join(outdir, naam), "wb") as fh:
                fh.write(data)
            fotos.append(Foto(bestand=naam, bouwdeel=e.get("bouwdeel", "-"), type=e.get("tag", "overzicht")))
        except Exception as ex:                        # één foute foto stopt de rest niet
            fouten.append((e.get("id") or e.get("url") or ("#%d" % (i + 1)), str(ex)[:100]))
    return fotos, fouten


def _client_fetch(client):
    """Bouw een fetch(entry)->bytes op basis van de MagicPlanClient (headers key+customer).
    Golden rule: alleen directe URL's downloaden; id-zonder-URL wordt geflagd, niet gegokt."""
    def fetch(e):
        url = e.get("url")
        if not url:
            raise RuntimeError("foto heeft geen directe URL (alleen id=%s) — bevestig 1x live het "
                               "foto-endpoint en vul dat hier in" % (e.get("id") or "?"))
        req = urllib.request.Request(url)
        if not url.lower().startswith(("http://", "https://")):
            raise RuntimeError("ongeldige foto-URL: %s" % url[:60])
        req.add_header("key", client.key)
        req.add_header("customer", client.customer)
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()
    return fetch


def fetch_project_photos(project_id, outdir, env=None):
    """LIVE: plan ophalen + foto's downloaden. Draait op de adviseur-machine (.env + internet)."""
    from magicplan.extractor import MagicPlanClient, load_env
    env = env or load_env(os.path.join(TOOL_DIR, ".env"))
    client = MagicPlanClient(env)
    plan = client.get_project_plan(project_id)
    return download_photos(photo_entries(plan), outdir, _client_fetch(client))


def main():
    ap = argparse.ArgumentParser(description="MagicPlan-foto's downloaden naar het project.")
    ap.add_argument("--project-id", help="MagicPlan project-id (live ophalen via de v2-API)")
    ap.add_argument("--plan-json", help="lokaal opgeslagen plan-JSON (offline foto-entries tonen)")
    ap.add_argument("--tag", help="project-tag (postcode_huisnr) -> out/projects/<tag>/fotos/")
    ap.add_argument("--out", help="uitvoermap (overrulet --tag)")
    args = ap.parse_args()

    outdir = args.out or (os.path.join(TOOL_DIR, "out", "projects", args.tag, "fotos") if args.tag
                          else os.path.join(TOOL_DIR, "out", "fotos"))

    if args.plan_json:
        plan = json.load(open(args.plan_json, encoding="utf-8"))
        entries = photo_entries(plan)
        print("Gevonden foto-entries: %d" % len(entries))
        for i, e in enumerate(entries):
            print("  %2d  %-14s %-10s %s" % (i + 1, e["bouwdeel"], e["tag"], e["url"] or ("id:" + e["id"])))
        if args.out or args.tag:
            def fetch(e):
                req = urllib.request.Request(e["url"])
                with urllib.request.urlopen(req, timeout=60) as r:
                    return r.read()
            fotos, fouten = download_photos(entries, outdir, fetch)
            print("Gedownload: %d -> %s" % (len(fotos), outdir))
            for s, reden in fouten:
                print("  ! overgeslagen %s: %s" % (s, reden))
        return

    if not args.project_id:
        ap.error("geef --project-id (live) of --plan-json (offline) op")
    fotos, fouten = fetch_project_photos(args.project_id, outdir)
    print("Gedownload: %d foto('s) -> %s" % (len(fotos), outdir))
    for s, reden in fouten:
        print("  ! overgeslagen %s: %s" % (s, reden))


if __name__ == "__main__":
    main()
