"""
Portal-mails ophalen uit een Microsoft 365-postvak via de Microsoft Graph API.

Waarom Graph en niet IMAP: het info@-postvak is een GEDEELD postvak. Dat heeft geen eigen wachtwoord,
en Microsoft heeft IMAP met basisauthenticatie grotendeels dichtgezet. Graph werkt met een eigen
app-identiteit (client credentials): de app logt in als zichzelf, niet als Renze, en de beheerder kan
met een Application Access Policy afdwingen dat die app UITSLUITEND bij dit ene postvak kan.

Alleen LEZEN. De app-registratie heeft genoeg aan Mail.Read (application); er wordt niets gemarkeerd,
verplaatst of verwijderd.

INSTELLEN — blok "graph" in config.json (staat in .gitignore; geheimen blijven lokaal/op de VPS):

    "graph": {
      "tenant_id": "<map-id / tenant-id>",
      "client_id": "<toepassings-id van de app-registratie>",
      "client_secret": "<geheim van de app-registratie>",
      "postvak": "info@poortinga-energieadvies.nl",
      "onderwerp": "AdviseurToegekend",
      "dagen": 30,
      "map": ""
    }

Wat de beheerder moet aanmaken staat in docs/microsoft-graph-mailkoppeling.md — geef hem dat document.

Geen externe bibliotheken: alles via urllib, zodat de VPS niets extra's nodig heeft.
"""
import json, urllib.request, urllib.parse, urllib.error, datetime, re

LOGIN = "https://login.microsoftonline.com/%s/oauth2/v2.0/token"
GRAPH = "https://graph.microsoft.com/v1.0"
TIMEOUT = 30

STANDAARD = {"onderwerp": "AdviseurToegekend", "dagen": 30, "map": ""}


def is_ingesteld(cfg):
    g = (cfg or {}).get("graph") or {}
    return all(str(g.get(k, "")).strip() for k in ("tenant_id", "client_id", "client_secret", "postvak"))


def instellingen(cfg):
    g = dict(STANDAARD)
    g.update((cfg or {}).get("graph") or {})
    return g


# ---------------- HTTP (injecteerbaar -> offline testbaar) ----------------
def _http(methode, url, headers=None, data=None):
    """-> (status, bytes). Foutcodes komen als gewone status terug, niet als exception:
    een 403 van Graph bevat juist de uitleg die de adviseur moet lezen."""
    req = urllib.request.Request(url, method=methode, data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def _fout_uitleg(status, ruw):
    """Graph-fout -> melding waar je iets aan hebt (geen ruwe JSON in de UI)."""
    tekst = ""
    try:
        j = json.loads(ruw or b"{}")
        tekst = (j.get("error", {}).get("message") if isinstance(j.get("error"), dict)
                 else j.get("error_description")) or ""
    except Exception:
        tekst = (ruw or b"")[:200].decode("utf-8", "replace")
    if status == 401:
        return ("Aanmelden bij Microsoft geweigerd (401). Controleer tenant-id, client-id en of het "
                "client secret nog geldig is — die verlopen. Details: %s" % tekst[:160])
    if status == 403:
        return ("Toegang geweigerd (403). Meestal is de toestemming Mail.Read nog niet door de "
                "beheerder verleend, of staat dit postvak niet in de Application Access Policy. "
                "Details: %s" % tekst[:160])
    if status == 404:
        return ("Postvak niet gevonden (404). Klopt het adres in \"postvak\"? Details: %s" % tekst[:160])
    return "Microsoft Graph gaf een fout (%s): %s" % (status, tekst[:180])


def token(g, http=None):
    """App-token ophalen (client credentials). -> (token, foutmelding)."""
    data = urllib.parse.urlencode({
        "client_id": g["client_id"], "client_secret": g["client_secret"],
        "scope": "https://graph.microsoft.com/.default", "grant_type": "client_credentials",
    }).encode()
    status, ruw = (http or _http)("POST", LOGIN % g["tenant_id"],
                                  {"Content-Type": "application/x-www-form-urlencoded"}, data)
    if status != 200:
        return None, _fout_uitleg(status, ruw)
    try:
        return json.loads(ruw)["access_token"], None
    except Exception:
        return None, "Onverwacht antwoord bij het aanmelden bij Microsoft."


# ---------------- pure helpers (offline testbaar) ----------------
def bericht_url(g, vandaag=None):
    """Graph-URL voor de berichten. Bewust ALLEEN op datum filteren en het onderwerp er daarna
    zelf uitzeven: Graph ondersteunt 'contains' op subject niet, en $search laat zich niet met
    $filter combineren. Simpel en voorspelbaar wint hier."""
    vandaag = vandaag or datetime.date.today()
    g = dict(STANDAARD, **(g or {}))
    basis = "%s/users/%s" % (GRAPH, urllib.parse.quote(g.get("postvak") or ""))
    if str(g.get("map") or "").strip():
        basis += "/mailFolders/%s" % urllib.parse.quote(g["map"].strip())
    q = {"$select": "subject,receivedDateTime,body", "$top": "200",
         "$orderby": "receivedDateTime desc"}
    dagen = int(g.get("dagen") or 0)
    if dagen > 0:
        sinds = vandaag - datetime.timedelta(days=dagen)
        q["$filter"] = "receivedDateTime ge %sT00:00:00Z" % sinds.isoformat()
    return basis + "/messages?" + urllib.parse.urlencode(q)


def _plat(html_of_tekst):
    """Graph levert met de Prefer-header platte tekst; valt dat tegen, dan tags eruit strippen."""
    t = html_of_tekst or ""
    if "<" in t and ">" in t:
        from html import unescape
        t = unescape(re.sub(r"<[^>]+>", " ", t))
    return t


def berichten_naar_teksten(berichten, onderwerp=""):
    """Graph-berichten -> lijst mailteksten. Filtert op onderwerp (hoofdletterongevoelig)."""
    zoek = (onderwerp or "").lower().strip()
    uit = []
    for b in berichten or []:
        onderw = (b.get("subject") or "")
        if zoek and zoek not in onderw.lower():
            continue
        inhoud = _plat(((b.get("body") or {}).get("content")) or "")
        if inhoud.strip():
            uit.append(inhoud)
    return uit


# ---------------- live ophalen ----------------
def haal_teksten(cfg, http=None):
    """-> (lijst mailteksten voor leads.parse_leads_bulk, foutmelding of None)."""
    if not is_ingesteld(cfg):
        return [], ("Microsoft-koppeling nog niet ingesteld. Zet het blok \"graph\" in config.json "
                    "(tenant_id, client_id, client_secret, postvak) — zie "
                    "docs/microsoft-graph-mailkoppeling.md.")
    g = instellingen(cfg)
    tok, fout = token(g, http=http)
    if fout:
        return [], fout
    status, ruw = (http or _http)("GET", bericht_url(g), {
        "Authorization": "Bearer %s" % tok,
        "Prefer": 'outlook.body-content-type="text"',      # platte tekst i.p.v. HTML
    }, None)
    if status != 200:
        return [], _fout_uitleg(status, ruw)
    try:
        berichten = json.loads(ruw).get("value") or []
    except Exception:
        return [], "Onverwacht antwoord van Microsoft Graph bij het ophalen van de berichten."
    return berichten_naar_teksten(berichten, g.get("onderwerp")), None
