"""
Nij Begun leads — portal-toewijzingen ("AdviseurToegekend"-mails van smarttwin.nl) beheren.

De portal mailt per toegewezen bewoner een JSON-blok:
    {"BagAdresId":"0014...","AccountId":"...","Email":"...","Postcode":"9736GL","Huisnummer":106,
     "HuisnummerToevoeging":"","Voornaam":"Jan","Telefoonnummer":"06...","Achternaam":"de Boer",
     "Naam":"Jan de Boer","WijzigingsType":"AdviseurToegekend","WijzigingsReden":"Adviseur ... toegekend"}

Deze module: mail-tekst plakken -> lead parsen -> lokaal bewaren (out/leads/leads.json — AVG: blijft
lokaal, out/ is git-ignored) -> status volgen -> CONCEPT-kennismakingsmail genereren (de adviseur
verstuurt 'm ZELF vanuit de eigen mailclient; de tool verstuurt niets) -> CSV-export (Excel).
"""
import os, json, re, datetime

TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEADS_DIR = os.path.join(TOOL_DIR, "out", "leads")
LEADS_FILE = os.path.join(LEADS_DIR, "leads.json")

STATUSSEN = ["nieuw", "mail gestuurd", "gebeld", "afspraak gepland",
             "opname gedaan", "plan ingediend", "afgerond", "vervallen"]


# ---------------- opslag ----------------
def load_leads():
    if os.path.isfile(LEADS_FILE):
        try:
            with open(LEADS_FILE, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return []
    return []


def save_leads(leads):
    os.makedirs(LEADS_DIR, exist_ok=True)
    with open(LEADS_FILE, "w", encoding="utf-8") as fh:
        json.dump(leads, fh, ensure_ascii=False, indent=1)


def set_project_tag(lid, tag, leads=None):
    """Koppel een aangemaakt project (tag = postcode_huisnummer) aan de lead. AVG: alleen de
    tag-link wordt bewaard, geen persoonsgegevens verhuizen mee naar het project."""
    leads = load_leads() if leads is None else leads
    for r in leads:
        if r.get("id") == lid:
            r["project_tag"] = tag
            break
    save_leads(leads)
    return leads


# ---------------- parsen ----------------
def parse_lead(text):
    """Geplakte mail-tekst -> lead-dict, of None. Pakt het eerste {...}-blok (de mail bevat het
    JSON-blok letterlijk); accepteert ook een kaal JSON-object of losse 'Veld: waarde'-regels."""
    text = (text or "").strip()
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.S)
    d = None
    if m:
        try:
            d = json.loads(m.group(0))
        except Exception:
            d = None
    if d is None:                       # fallback: 'Veld: waarde'-regels
        d = {}
        for k in ("BagAdresId", "AccountId", "Email", "Postcode", "Huisnummer",
                  "HuisnummerToevoeging", "Voornaam", "Achternaam", "Naam", "Telefoonnummer"):
            mm = re.search(r"%s\W+([^\r\n,\"]+)" % k, text, re.I)
            if mm:
                d[k] = mm.group(1).strip()
        if not d:
            return None
    naam = str(d.get("Naam") or ("%s %s" % (d.get("Voornaam", ""), d.get("Achternaam", ""))).strip())
    lead = {
        "bag_id": str(d.get("BagAdresId", "")).strip(),
        "account_id": str(d.get("AccountId", "")).strip(),
        "naam": naam,
        "voornaam": str(d.get("Voornaam", "")).strip(),
        "email": str(d.get("Email", "")).strip(),
        "telefoon": str(d.get("Telefoonnummer", "")).strip(),
        "postcode": str(d.get("Postcode", "")).strip().upper().replace(" ", ""),
        "huisnummer": str(d.get("Huisnummer", "")).strip(),
        "toevoeging": str(d.get("HuisnummerToevoeging", "")).strip(),
        "reden": str(d.get("WijzigingsReden", "")).strip(),
    }
    if not (lead["naam"] or lead["postcode"] or lead["bag_id"]):
        return None
    return lead


def _sleutel(lead):
    """Dedupe-sleutel: BAG-id, anders postcode+huisnummer+toevoeging."""
    return lead.get("bag_id") or "%s-%s%s" % (lead.get("postcode", ""),
                                              lead.get("huisnummer", ""), lead.get("toevoeging", ""))


def add_lead(lead, leads=None):
    """Voeg toe (dedupe). -> (leads, toegevoegd:bool)."""
    leads = load_leads() if leads is None else leads
    if any(_sleutel(x) == _sleutel(lead) for x in leads):
        return leads, False
    lead = dict(lead)
    lead["id"] = max([x.get("id", 0) for x in leads] or [0]) + 1
    lead["status"] = "nieuw"
    lead["ontvangen"] = datetime.date.today().isoformat()
    lead["notitie"] = ""
    leads.append(lead)
    return leads, True


def adres(lead):
    hn = "%s%s" % (lead.get("huisnummer", ""), (" " + lead["toevoeging"]) if lead.get("toevoeging") else "")
    if lead.get("straat"):                   # BAG-verrijkt: echte straatnaam + woonplaats
        s = "%s %s" % (lead["straat"], hn)
        if lead.get("woonplaats"):
            s += " in " + lead["woonplaats"]
        return s
    return ("%s %s" % (lead.get("postcode", ""), hn)).strip()


# ---------------- concept-kennismakingsmail ----------------
# Wat de bewoner kan klaarleggen = precies wat de SCHIL-opname nodig heeft. Nij Begun (Maatregel 29)
# gaat over isolatie + ventilatie; installaties (cv-ketel/warmtepomp/PV) horen bij het ENERGIELABEL en
# niet bij het isolatieplan — daarom vragen we daar hier bewust NIET naar (ISSO 82.1: isolatie telt
# alleen mee indien waarneembaar of met schriftelijk bewijs aantoonbaar).
VOORBEREIDING = [
    "Facturen of offertes van eerder isolatiewerk (dak-, gevel-, spouw- of vloerisolatie), indien aanwezig",
    "Weet u of de woning eerder is geïsoleerd (dak/gevel/spouw/vloer)? Zo ja: welk jaar en door wie, indien bekend",
    "Bouwtekeningen van de woning of van een verbouwing/aanbouw, indien aanwezig",
    "Toegang tot het kruipruimteluik en de zolder (graag even vrij maken)",
]


def concept_mail(lead, adviseur=None):
    """-> (onderwerp, tekst). De adviseur kopieert/verstuurt dit ZELF (tool mailt niet)."""
    adviseur = adviseur or {}
    a_naam = adviseur.get("naam", "")
    a_bedrijf = adviseur.get("bedrijf", "")
    a_tel = adviseur.get("telefoon", "")
    a_mail = adviseur.get("email", "")
    aanhef = ("Beste %s," % (lead.get("naam") or "bewoner")).strip()
    onderwerp = "Uw isolatieadvies via Nij Begun — kennismaking en afspraak"
    regels = [
        aanhef, "",
        "Goed nieuws: via het Nij Begun-programma ben ik als isolatieadviseur aan uw woning "
        "(%s) gekoppeld. Ik help u met een persoonlijk isolatieplan, zodat u gebruik kunt maken "
        "van de subsidieregeling." % adres(lead),
        "",
        "Ik bel u binnenkort op %s om een afspraak te maken voor de woningopname. De opname duurt "
        "ongeveer 1,5 tot 2 uur; ik kom daarvoor bij u thuis en bekijk de hele woning (van kruipruimte "
        "tot zolder)." % (lead.get("telefoon") or "het bij Nij Begun bekende nummer"),
        "",
        "Het helpt enorm als u alvast het volgende klaarlegt (alleen wat u heeft):",
    ]
    regels += ["  •  " + v for v in VOORBEREIDING]
    regels += [
        "",
        "Heeft u vragen, of belt/mailt u liever zelf voor het maken van de afspraak? Dat kan "
        "natuurlijk ook — mijn gegevens staan hieronder.",
        "",
        "Met vriendelijke groet,", "",
        a_naam or "", a_bedrijf or "",
        ("Telefoon: %s" % a_tel) if a_tel else "",
        ("E-mail: %s" % a_mail) if a_mail else "",
    ]
    tekst = "\n".join(r for r in regels if r is not None)
    return onderwerp, re.sub(r"\n{3,}", "\n\n", tekst).strip() + "\n"


# ---------------- export ----------------
def to_csv(leads):
    """CSV voor Excel-NL (puntkomma; utf-8 BOM)."""
    kol = ["id", "ontvangen", "status", "naam", "straat", "woonplaats", "postcode", "huisnummer",
           "toevoeging", "bouwjaar", "oppervlakte_m2", "telefoon", "email", "bag_id", "notitie"]
    esc = lambda v: '"%s"' % str(v if v is not None else "").replace('"', '""')
    rijen = [";".join(kol)]
    for x in leads:
        rijen.append(";".join(esc(x.get(k, "")) for k in kol))
    return "﻿" + "\r\n".join(rijen) + "\r\n"
