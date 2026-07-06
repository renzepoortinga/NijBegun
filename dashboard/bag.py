"""
BAG-verrijking van leads (postcode+huisnummer -> straat/woonplaats + bouwjaar/oppervlakte/gebruiksdoel).

LIVE GEVERIFIEERD (26-6-2026, geen API-sleutel nodig, beide PDOK):
1) Locatieserver:  GET https://api.pdok.nl/bzk/locatieserver/search/v3_1/free
       ?q=<postcode huisnummer>&fq=type:adres&rows=10
   -> response.docs[]: weergavenaam ("Munsterheerd 106, 9736GL Groningen"), straatnaam, woonplaatsnaam,
      huis_nlt, postcode, nummeraanduiding_id (= de "BagAdresId" uit de portal-mail!),
      adresseerbaarobject_id (verblijfsobject-id), centroide_rd "POINT(x y)".
2) BAG-WFS:        GET https://service.pdok.nl/kadaster/bag/wfs/v2_0
       ?service=WFS&version=2.0.0&request=GetFeature&typeName=bag:verblijfsobject
       &outputFormat=application/json&count=20&srsName=EPSG:28992&bbox=x-1,y-1,x+1,y+1,EPSG:28992
   -> features[].properties: identificatie, oppervlakte, gebruiksdoel, bouwjaar, pandidentificatie,
      openbare_ruimte, huisnummer, woonplaats.  LET OP: CQL_FILTER wordt door deze WFS GENEGEERD ->
      daarom bbox rond de centroide + client-side match op identificatie (live bewezen).

Netwerk nodig -> draait op de adviseur-machine (de tool-sandbox heeft geen internet). De parse-functies
zijn puur (offline testbaar met fixtures). Fouten -> (None, melding); nooit een exception naar de UI.
"""
import json, re, urllib.request, urllib.parse

LOCATIESERVER = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"
BAG_WFS = "https://service.pdok.nl/kadaster/bag/wfs/v2_0"
TIMEOUT = 15


def _get_json(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json",
                                               "User-Agent": "nijbegun-epa-tool"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


# ---------------- pure parsers (offline testbaar) ----------------
def parse_locatieserver(j, huisnummer="", toevoeging=""):
    """Locatieserver-response -> adres-dict of None. Kiest exacte huisnummer(+toevoeging)-match."""
    docs = ((j or {}).get("response") or {}).get("docs") or []
    wens = ("%s%s" % (huisnummer, toevoeging or "")).lower().replace(" ", "")
    best = None
    for d in docs:
        hn = str(d.get("huis_nlt", d.get("huisnummer", ""))).lower().replace(" ", "")
        if wens and hn == wens:
            best = d
            break
        best = best or d
    if not best:
        return None
    m = re.search(r"POINT\(([\d.]+) ([\d.]+)\)", best.get("centroide_rd", ""))
    return {
        "weergavenaam": best.get("weergavenaam", ""),
        "straat": best.get("straatnaam", ""),
        "woonplaats": best.get("woonplaatsnaam", ""),
        "nummeraanduiding_id": best.get("nummeraanduiding_id", ""),
        "verblijfsobject_id": best.get("adresseerbaarobject_id", ""),
        "x": float(m.group(1)) if m else None,
        "y": float(m.group(2)) if m else None,
    }


def parse_wfs(j, verblijfsobject_id):
    """WFS-response -> verblijfsobject-props of None (match op identificatie; bbox kan buren bevatten)."""
    feats = (j or {}).get("features") or []
    props = [f.get("properties") or {} for f in feats]
    hit = next((p for p in props if p.get("identificatie") == verblijfsobject_id), None)
    if hit is None and len(props) == 1:      # bbox zo klein dat er maar 1 pand in zit
        hit = props[0]
    if not hit:
        return None
    return {"bouwjaar": hit.get("bouwjaar"), "oppervlakte_m2": hit.get("oppervlakte"),
            "gebruiksdoel": hit.get("gebruiksdoel", ""), "pand_id": hit.get("pandidentificatie", "")}


# ---------------- live opzoeken ----------------
def bag_info(postcode, huisnummer, toevoeging=""):
    """-> (info-dict, None) of (None, foutmelding). Info: straat/woonplaats/bouwjaar/oppervlakte/etc."""
    try:
        q = urllib.parse.quote("%s %s%s" % (postcode, huisnummer, (" " + toevoeging) if toevoeging else ""))
        adr = parse_locatieserver(_get_json("%s?q=%s&fq=type:adres&rows=10" % (LOCATIESERVER, q)),
                                  huisnummer, toevoeging)
        if not adr:
            return None, "Adres niet gevonden in de BAG (check postcode/huisnummer)."
        info = dict(adr)
        if adr["x"] is not None:
            d = 1.0
            bbox = "%s,%s,%s,%s,EPSG:28992" % (adr["x"] - d, adr["y"] - d, adr["x"] + d, adr["y"] + d)
            wfs = _get_json("%s?service=WFS&version=2.0.0&request=GetFeature&typeName=bag:verblijfsobject"
                            "&outputFormat=application/json&count=20&srsName=EPSG:28992&bbox=%s"
                            % (BAG_WFS, bbox))
            vo = parse_wfs(wfs, adr["verblijfsobject_id"])
            if vo:
                info.update(vo)
        return info, None
    except Exception as e:
        return None, "BAG-opzoeken mislukt (%s). Internet nodig; probeer zo nog eens." % (str(e)[:80])
