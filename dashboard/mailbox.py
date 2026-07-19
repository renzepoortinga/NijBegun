"""
Portal-mails rechtstreeks uit de mailbox halen (IMAP) i.p.v. slepen/plakken.

Waarom: de Nij Begun-portalmails komen met tientallen tegelijk binnen. Ze handmatig uit Outlook
slepen is het meeste werk van de hele leadverwerking. Deze module logt in op het postvak, zoekt de
toewijzingsmails op en levert de RUWE TEKST aan; het parsen blijft in leads.py (één parser, één
plek waar het JSON-blok wordt gelezen).

INSTELLEN — in config.json (staat in .gitignore, dus geheimen blijven lokaal/op de VPS):

    "mailbox": {
      "host": "imap.jouwprovider.nl",
      "poort": 993,
      "gebruiker": "info@poortinga-energieadvies.nl",
      "wachtwoord": "<APP-wachtwoord, geen gewoon wachtwoord>",
      "map": "INBOX",
      "onderwerp": "AdviseurToegekend",
      "dagen": 30,
      "markeer_gelezen": false
    }

Gebruik een APP-WACHTWOORD (Microsoft 365 / Google: aparte code per applicatie) en geen gewoon
wachtwoord: dan kun je de toegang intrekken zonder je eigen wachtwoord te wijzigen, en heeft de
code nooit toegang tot je volledige account.

Alleen LEZEN: deze module verplaatst en verwijdert nooit iets. 'markeer_gelezen' is het enige wat
het postvak verandert, en staat standaard uit.
"""
import imaplib, email, datetime


STANDAARD = {"poort": 993, "map": "INBOX", "onderwerp": "AdviseurToegekend",
             "dagen": 30, "markeer_gelezen": False}


def is_ingesteld(cfg):
    """Genoeg gegevens om het te proberen? (host + gebruiker + wachtwoord)"""
    m = (cfg or {}).get("mailbox") or {}
    return all(str(m.get(k, "")).strip() for k in ("host", "gebruiker", "wachtwoord"))


def instellingen(cfg):
    m = dict(STANDAARD)
    m.update((cfg or {}).get("mailbox") or {})
    return m


# ---------------- pure helpers (offline testbaar) ----------------
def zoekopdracht(m, vandaag=None):
    """IMAP-zoekopdracht: alleen mails van de laatste N dagen met de portal-term in het onderwerp.
    -> lijst met IMAP-argumenten. Datumformaat is IMAP's eigen '01-Jan-2026'."""
    vandaag = vandaag or datetime.date.today()
    args = []
    dagen = int(m.get("dagen") or 0)
    if dagen > 0:
        sinds = vandaag - datetime.timedelta(days=dagen)
        args += ["SINCE", sinds.strftime("%d-%b-%Y")]
    onderwerp = (m.get("onderwerp") or "").strip()
    if onderwerp:
        args += ["SUBJECT", onderwerp]
    return args or ["ALL"]


def _mapnaam(naam):
    """Mapnamen met spaties moeten tussen aanhalingstekens ('Verwijderde items')."""
    naam = naam or "INBOX"
    return '"%s"' % naam if " " in naam and not naam.startswith('"') else naam


def berichten_naar_teksten(ruwe_berichten):
    """Ruwe .eml-bytes -> leesbare tekst per bericht (hergebruikt de bestaande MIME-decoder)."""
    from dashboard.leads import tekst_uit_eml
    uit = []
    for ruw in ruwe_berichten:
        t = tekst_uit_eml(ruw)
        if t:
            uit.append(t)
    return uit


# ---------------- live ophalen ----------------
def _verbind(m):
    imap = imaplib.IMAP4_SSL(m["host"], int(m.get("poort") or 993))
    imap.login(m["gebruiker"], m["wachtwoord"])
    return imap


def haal_berichten(cfg, verbind=None, maximaal=200):
    """-> (lijst ruwe berichten, foutmelding of None). Netwerk nodig.

    'verbind' is injecteerbaar zodat de flow zonder mailserver te testen is."""
    m = instellingen(cfg)
    if not is_ingesteld(cfg):
        return [], ("Mailbox nog niet ingesteld. Zet host/gebruiker/wachtwoord onder \"mailbox\" "
                    "in config.json (zie dashboard/mailbox.py voor het voorbeeld).")
    imap = None
    try:
        imap = (verbind or _verbind)(m)
        imap.select(_mapnaam(m.get("map")), readonly=not m.get("markeer_gelezen"))
        code, data = imap.search(None, *zoekopdracht(m))
        if code != "OK":
            return [], "Zoeken in de mailbox gaf een onverwacht antwoord (%s)." % code
        ids = (data[0] or b"").split()
        if not ids:
            return [], None                        # niets gevonden is geen fout
        ids = ids[-maximaal:]                      # nieuwste eerst begrenzen
        uit = []
        for i in ids:
            code, blok = imap.fetch(i, "(RFC822)")
            if code != "OK" or not blok:
                continue
            for deel in blok:
                if isinstance(deel, tuple) and deel[1]:
                    uit.append(deel[1])
                    break
        return uit, None
    except imaplib.IMAP4.error as e:
        return [], ("Inloggen of zoeken mislukte: %s. Controleer gebruiker/app-wachtwoord en of "
                    "IMAP aanstaat voor dit postvak." % str(e)[:120])
    except Exception as e:
        return [], "Mailbox benaderen mislukte (%s: %s)." % (type(e).__name__, str(e)[:120])
    finally:
        if imap is not None:
            try:
                imap.close()
            except Exception:
                pass
            try:
                imap.logout()
            except Exception:
                pass


def haal_teksten(cfg, verbind=None):
    """-> (lijst mailteksten klaar voor leads.parse_leads_bulk, foutmelding of None)."""
    ruw, fout = haal_berichten(cfg, verbind=verbind)
    if fout:
        return [], fout
    return berichten_naar_teksten(ruw), None
