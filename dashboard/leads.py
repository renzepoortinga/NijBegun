"""
Nij Begun leads — portal-toewijzingen ("AdviseurToegekend"-mails van smarttwin.nl) beheren.

De portal mailt per toegewezen bewoner een JSON-blok:
    {"BagAdresId":"0014...","Email":"...","Postcode":"9736GL","Huisnummer":106,"Naam":"Jan de Boer",
     "WijzigingsType":"AdviseurToegekend","WijzigingsReden":"Adviseur ... toegekend"}

WijzigingsType stuurt de actie: AdviseurToegekend = nieuwe lead, AdviseurGeannuleerd = bestaande lead
op 'vervallen' (bewoner trekt de toewijzing in), contactwijziging = contactvelden bijwerken.

Deze module: mail-tekst plakken -> lead parsen -> lokaal bewaren (out/leads/leads.json — AVG: blijft
lokaal, out/ is git-ignored) -> status volgen -> CONCEPT-kennismakingsmail genereren (de adviseur
verstuurt 'm ZELF vanuit de eigen mailclient; de tool verstuurt niets) -> CSV-export (Excel).
"""
import os, json, re, datetime, threading

TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEADS_DIR = os.path.join(TOOL_DIR, "out", "leads")
LEADS_FILE = os.path.join(LEADS_DIR, "leads.json")

# leads.json wordt ook vanuit achtergrondwerk bijgewerkt (BAG-verrijking, mail-ophalen) terwijl de
# adviseur in de webapp klikt. Zonder slot kan een trage lees-wijzig-schrijf een verse statuswijziging
# overschrijven; wijzig() maakt van dat drietal één ondeelbare stap.
LOCK = threading.RLock()

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


def wijzig(fn):
    """Lees -> wijzig -> schrijf als één ondeelbare stap. fn(leads) mag de lijst aanpassen; de
    returnwaarde van fn wordt doorgegeven. Gebruik dit vanuit achtergrondwerk (BAG/mail-ophalen)."""
    with LOCK:
        leads = load_leads()
        uit = fn(leads)
        save_leads(leads)
        return uit


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


def wis_project_tag(tag):
    """Verwijder de koppeling naar een project bij ALLE leads die eraan hingen — te gebruiken
    zodra dat project wordt verwijderd, zodat de lead geen dode 'Project'-knop houdt."""
    with LOCK:
        leads = load_leads()
        n = 0
        for r in leads:
            if r.get("project_tag") == tag:
                r.pop("project_tag", None)
                n += 1
        if n:
            save_leads(leads)
        return n


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
        # het portaal stuurt verschillende soorten mails: AdviseurToegekend (nieuwe lead),
        # AdviseurGeannuleerd (bewoner trekt de toewijzing in) en contactwijzigingen. Dit veld
        # stuurt in de webapp de juiste actie aan (toevoegen / op 'vervallen' zetten / bijwerken).
        "wijzigingstype": str(d.get("WijzigingsType", "")).strip(),
    }
    if not (lead["naam"] or lead["postcode"] or lead["bag_id"]):
        return None
    return lead


def _sleutel(lead):
    """Dedupe-sleutel: BAG-id, anders postcode+huisnummer+toevoeging."""
    return lead.get("bag_id") or "%s-%s%s" % (lead.get("postcode", ""),
                                              lead.get("huisnummer", ""), lead.get("toevoeging", ""))


def is_annulering(lead):
    """Portaalmail waarin de bewoner de toewijzing intrekt (WijzigingsType AdviseurGeannuleerd)."""
    return "annul" in (lead.get("wijzigingstype", "") or "").lower() \
        or "geannuleerd" in (lead.get("wijzigingstype", "") or "").lower()


def annuleer_lead(lead, leads=None):
    """Zet de BESTAANDE lead op 'vervallen' zodat je 'm niet meer benadert. -> (leads, resultaat)
    waarbij resultaat = 'gevonden' | 'onbekend'. De lead wordt NOOIT verwijderd en een gekoppeld
    project blijft staan (de opname kan al gedaan zijn — dat besluit jij zelf)."""
    leads = load_leads() if leads is None else leads
    bestaand = next((x for x in leads if _sleutel(x) == _sleutel(lead)), None)
    if bestaand is None:
        return leads, "onbekend"
    bestaand["status"] = "vervallen"
    reden = (lead.get("reden") or "").strip()
    stempel = "Geannuleerd door bewoner op %s" % datetime.date.today().isoformat()
    if reden:
        stempel += " — %s" % reden
    oud = (bestaand.get("notitie") or "").strip()
    bestaand["notitie"] = (oud + "\n" + stempel).strip() if oud else stempel
    save_leads(leads)
    return leads, "gevonden"


# ---------------- verwijderde leads onthouden ----------------
# Wie je bewust hebt weggegooid (bv. bewoner heeft zich uitgeschreven) mag bij de volgende
# mail-ophaalronde NIET terugkomen. Daarom bewaren we alleen de dedupe-SLEUTEL van verwijderde
# leads — geen naam, adres of contactgegevens. AVG: dat is het minimum dat nodig is om jouw
# verwijdering te kunnen respecteren, en het staat lokaal in out/leads/.
GEWIST_FILE = os.path.join(LEADS_DIR, "verwijderd.json")


def load_gewist():
    if os.path.isfile(GEWIST_FILE):
        try:
            with open(GEWIST_FILE, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return []
    return []


def onthoud_gewist(lead):
    """Sleutel van een verwijderde lead bewaren, zodat hij niet opnieuw binnenkomt."""
    with LOCK:
        s = _sleutel(lead)
        lijst = load_gewist()
        if s and s not in lijst:
            lijst.append(s)
            os.makedirs(LEADS_DIR, exist_ok=True)
            with open(GEWIST_FILE, "w", encoding="utf-8") as fh:
                json.dump(lijst, fh, ensure_ascii=False, indent=1)
        return lijst


def vergeet_gewist(sleutel=None):
    """Blokkade opheffen: één sleutel, of alles (sleutel=None) — voor als je iemand tóch terugwilt."""
    with LOCK:
        lijst = [] if sleutel is None else [x for x in load_gewist() if x != sleutel]
        os.makedirs(LEADS_DIR, exist_ok=True)
        with open(GEWIST_FILE, "w", encoding="utf-8") as fh:
            json.dump(lijst, fh, ensure_ascii=False, indent=1)
        return lijst


# Velden die het portaal later nog kan wijzigen ("Contact gegevens gewijzigd door gebruiker"-mails).
# Bij een dubbele lead werken we die BIJ; status, afspraak, notitie en projectkoppeling blijven van jou.
CONTACTVELDEN = ("naam", "voornaam", "email", "telefoon")


def add_lead(lead, leads=None):
    """Voeg toe (dedupe). -> (leads, toegevoegd:bool).

    Een bekende lead wordt niet opnieuw toegevoegd, maar de CONTACTGEGEVENS worden wel bijgewerkt:
    het portaal stuurt ook wijzigingsmails, en een nieuw telefoonnummer moet je wél zien. Wat jij zelf
    hebt ingevuld (status/afspraak/notitie/project) blijft ongemoeid."""
    leads = load_leads() if leads is None else leads
    if _sleutel(lead) in load_gewist():          # bewust verwijderd -> nooit stilletjes terugzetten
        return leads, False
    bestaand = next((x for x in leads if _sleutel(x) == _sleutel(lead)), None)
    if bestaand is not None:
        for k in CONTACTVELDEN:
            nieuw = (lead.get(k) or "").strip()
            if nieuw and nieuw != (bestaand.get(k) or "").strip():
                bestaand[k] = nieuw
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


def _ondertekening(adviseur):
    """Bedrijfsmatige ondertekening: naam + bedrijf + e-mail. BEWUST zonder telefoonnummer
    (Renze wil per e-mail communiceren en neemt zelf contact op)."""
    return ["Met vriendelijke groet,", "",
            adviseur.get("naam", ""), adviseur.get("bedrijf", ""),
            ("E-mail: %s" % adviseur["email"]) if adviseur.get("email") else ""]


def concept_mail(lead, adviseur=None):
    """-> (onderwerp, tekst). De adviseur kopieert/verstuurt dit ZELF (tool mailt niet)."""
    adviseur = adviseur or {}
    bedrijf = adviseur.get("bedrijf") or adviseur.get("naam") or "ons bedrijf"
    aanhef = ("Beste %s," % (lead.get("naam") or "bewoner")).strip()
    onderwerp = "Uw isolatieadvies via Nij Begun: kennismaking en afspraak"
    regels = [
        aanhef, "",
        "Goed nieuws: via het Nij Begun-programma is %s als isolatieadviseur aan uw woning "
        "(%s) gekoppeld. Wij helpen u met een persoonlijk isolatieplan, zodat u gebruik kunt maken "
        "van de subsidieregeling." % (bedrijf, adres(lead)),
        "",
        "Wij nemen binnenkort contact met u op om een afspraak te maken voor de woningopname. De "
        "opname duurt ongeveer 1,5 tot 2 uur; wij komen daarvoor bij u thuis en bekijken de hele "
        "woning (van kruipruimte tot zolder).",
        "",
        "Het helpt enorm als u alvast het volgende klaarlegt (alleen wat u heeft):",
    ]
    regels += ["  •  " + v for v in VOORBEREIDING]
    regels += [
        "",
        # Nij Begun-kennisbank: bewonerswensen buiten de Standaard adviseren we wel (30% ISDE);
        # schimmel-/vochtklachten zijn een vast onderdeel van het opnameformulier.
        "Denkt u daarnaast alvast na over deze twee vragen? Die nemen wij mee in het isolatieplan:",
        "  •  Heeft u zelf wensen voor de woning, bijvoorbeeld ander glas, een dakkapel of het",
        "     vervangen van een deur? Ook wensen die buiten de Nij Begun-vergoeding vallen nemen",
        "     wij mee in het advies, vaak met 30% ISDE-subsidie.",
        "  •  Heeft u ergens in huis last van vocht, schimmel, tocht of koude ruimtes? Zulke klachten",
        "     noteren wij tijdens de opname; een goed isolatieplan pakt eerst de oorzaak aan voordat",
        "     er geïsoleerd wordt.",
        "",
        "Heeft u in de tussentijd vragen? Wij zijn het beste per e-mail bereikbaar.",
        "",
    ] + _ondertekening(adviseur)
    tekst = "\n".join(r for r in regels if r is not None)
    return onderwerp, re.sub(r"\n{3,}", "\n\n", tekst).strip() + "\n"


def parse_leads_bulk(text):
    """Meerdere geplakte portal-mails in één keer -> lijst leads (elk {...}-blok apart geparsed)."""
    blokken = re.findall(r"\{[^{}]*\}", text or "", re.S)
    uit = []
    for b in blokken:
        ld = parse_lead(b)
        if ld:
            uit.append(ld)
    if not uit:                      # fallback: hele tekst als één lead proberen
        ld = parse_lead(text)
        if ld:
            uit.append(ld)
    return uit


def tekst_uit_eml(data):
    """Ruwe .eml-bytes (uit Outlook gesleepte mail) -> leesbare tekst voor parse_leads_bulk.
    De MIME-decoder is nodig: portal-mails zijn vaak quoted-printable of base64 gecodeerd,
    waardoor het JSON-blok in de ruwe bytes onherkenbaar is. Voorkeur text/plain; alleen-HTML
    wordt van tags ontdaan."""
    import email, email.policy
    from html import unescape
    try:
        msg = email.message_from_bytes(data, policy=email.policy.default)
    except Exception:
        return ""
    delen = []
    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue
        ct = part.get_content_type()
        if ct not in ("text/plain", "text/html"):
            continue
        try:
            inhoud = part.get_content()
        except Exception:
            continue
        if ct == "text/html":
            inhoud = unescape(re.sub(r"<[^>]+>", " ", inhoud))
        delen.append((0 if ct == "text/plain" else 1, inhoud))
    if not delen:
        return ""
    delen.sort(key=lambda x: x[0])
    if any(p == 0 for p, _ in delen):            # text/plain aanwezig -> alleen die
        return "\n".join(t for p, t in delen if p == 0)
    return "\n".join(t for _, t in delen)


def set_afspraak(lid, wanneer, leads=None):
    """Afspraakdatum/-tijd (ISO 'YYYY-MM-DDTHH:MM') op de lead zetten."""
    leads = load_leads() if leads is None else leads
    for r in leads:
        if r.get("id") == lid:
            r["afspraak"] = (wanneer or "").strip()
            break
    save_leads(leads)
    return leads


def _afspraak_nl(iso):
    """'2026-07-15T14:30' -> 'woensdag 15 juli 2026 om 14:30'."""
    try:
        d = datetime.datetime.fromisoformat(iso)
        dagen = ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"]
        maanden = ["januari", "februari", "maart", "april", "mei", "juni", "juli",
                   "augustus", "september", "oktober", "november", "december"]
        return "%s %d %s %d om %02d:%02d" % (dagen[d.weekday()], d.day, maanden[d.month - 1],
                                             d.year, d.hour, d.minute)
    except Exception:
        return iso or "nader te bepalen"


def bevestiging_mail(lead, adviseur=None):
    """Afspraak-bevestigingsmail: datum/tijd + voorbereiding + Nij Begun-verwachtingsmanagement.
    De adviseur verstuurt ZELF (tool mailt niet)."""
    adviseur = adviseur or {}
    onderwerp = "Bevestiging afspraak woningopname op %s" % _afspraak_nl(lead.get("afspraak", ""))
    regels = [
        ("Beste %s," % (lead.get("naam") or "bewoner")).strip(), "",
        "Hierbij bevestigen wij onze afspraak voor de woningopname aan %s:" % adres(lead), "",
        "    %s" % _afspraak_nl(lead.get("afspraak", "")),
        "    De opname duurt ongeveer 1,5 tot 2 uur; wij bekijken de hele woning, van kruipruimte tot zolder.", "",
        "Wilt u ter voorbereiding alvast het volgende regelen?",
        "  •  Het kruipruimteluik bereikbaar maken (eventuele spullen er even af/omheen weg).",
        "  •  Raambekleding (gordijnen, rolgordijnen, plissés) opzij of omhoog, zodat alle ramen en",
        "     kozijnen goed zichtbaar zijn. Wij fotograferen en beoordelen elk raam.",
        "  •  Toegang tot de zolder (trap/luik vrij).",
        "  •  Facturen of offertes van eerder isolatiewerk klaarleggen, indien aanwezig.", "",
        "Goed om te weten: tijdens de opname maken wij foto's in alle ruimtes. Dat is verplicht voor het",
        "subsidiedossier. Persoonlijke spullen mag u uiteraard opzij leggen; er komen geen personen in beeld.", "",
        "Wat u van het Nij Begun-isolatieplan kunt verwachten:",
        "  •  De regeling vergoedt ISOLATIEmaatregelen die nodig zijn om de warmtevraag-norm (de",
        "     'Standaard') te halen: bijvoorbeeld spouwmuur-, dak-, vloerisolatie en beter glas, plus een",
        "     passend ventilatie-advies.",
        "  •  Niet alles valt binnen de regeling: bijvoorbeeld complete kozijnvervanging (zoals triple glas",
        "     in nieuwe kunststof kozijnen) wordt doorgaans niet 100% vergoed. Voor zulke wensen kijken wij",
        "     met u naar alternatieven (zoals 30% ISDE-subsidie), zodat u vooraf precies weet waar u aan",
        "     toe bent.", "",
        "Mocht de afspraak onverhoopt niet uitkomen, laat het ons dan per e-mail weten.", "",
    ] + _ondertekening(adviseur)
    tekst = "\n".join(r for r in regels if r is not None)
    return onderwerp, re.sub(r"\n{3,}", "\n\n", tekst).strip() + "\n"


def ontvangst_mail(adviseur=None):
    """Generieke ontvangstbevestiging (bulk, BCC): aanvraag ontvangen, drukte, wachtlijst-volgorde."""
    adviseur = adviseur or {}
    bedrijf = adviseur.get("bedrijf") or adviseur.get("naam") or "ons bedrijf"
    onderwerp = "Uw Nij Begun-aanvraag is in goede orde ontvangen"
    regels = [
        "Beste bewoner,", "",
        "Via het Nij Begun-portaal bent u aan %s toegewezen voor het opmaken van een isolatieplan "
        "voor uw woning." % bedrijf, "",
        "Uw aanvraag is in goede orde ontvangen, hartelijk dank voor uw aanmelding.", "",
        "Door de huidige drukte is de wachttijd op dit moment langer dan wij zouden willen. "
        "Wij streven ernaar iedereen zo spoedig mogelijk in te plannen voor de woningopname en werken de "
        "lijst op volgorde van aanmelding af. U staat op de lijst en hoeft verder niets te doen.", "",
        "Zodra u aan de beurt bent, nemen wij persoonlijk contact met u op om een afspraak te maken.", "",
        "Heeft u in de tussentijd vragen? Wij zijn het beste per e-mail bereikbaar.", "",
    ] + _ondertekening(adviseur)
    tekst = "\n".join(r for r in regels if r is not None)
    return onderwerp, re.sub(r"\n{3,}", "\n\n", tekst).strip() + "\n"


# ---------------- export ----------------
def to_csv(leads):
    """CSV voor Excel-NL (puntkomma; utf-8 BOM)."""
    kol = ["id", "ontvangen", "status", "afspraak", "naam", "straat", "woonplaats", "postcode", "huisnummer",
           "toevoeging", "bouwjaar", "oppervlakte_m2", "telefoon", "email", "bag_id", "notitie"]
    esc = lambda v: '"%s"' % str(v if v is not None else "").replace('"', '""')
    rijen = [";".join(kol)]
    for x in leads:
        rijen.append(";".join(esc(x.get(k, "")) for k in kol))
    return "﻿" + "\r\n".join(rijen) + "\r\n"
