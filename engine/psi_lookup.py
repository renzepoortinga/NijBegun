"""
Forfaitaire lineaire warmtedoorgangscoëfficiënten ψ per aansluitdetail — NTA 8800:2025+C1:2026,
bijlage I.1 (tabel I.1 laagbouw / grondgebonden, tabel I.2 gestapeld).

Waarvoor: (a) de adviseur weet wélke ψ hij in Vabi bij welk detail moet zetten als hij forfaitair
rekent, en (b) het voedt **Bijlage 7 "Detailtekeningen"** van het isolatieplan — de detailnummering
komt overeen met de ISSO-Referentiedetails.

Gouden regel blijft: de tool rekent de transmissie NIET zelf. Dit is een LOOKUP van normwaarden.

Kolom A / kolom B (NTA bijlage I.1):
  A = de aanvullende voorwaarden bij het detail zijn gehaald (goed uitgevoerde aansluiting)
  B = die voorwaarden zijn NIET gehaald -> ongunstiger ψ
Ontbreekt een detailpositie in de tabel, dan mag ψ = 0,50 W/(m·K) worden gehanteerd (NTA bijlage I.1).

LET OP (staat expliciet in de norm): deze forfaitaire waarden gelden bij constructies die voldoen aan
de nieuwbouw-eisen van het Bbl. In een BESTAANDE, nog niet geïsoleerde woning zijn ze dus indicatief;
ze zijn vooral bruikbaar voor de TOEKOMSTIGE staat (na de maatregelen) — precies waar bijlage 7 over gaat.
"""

PSI_DEFAULT = 0.50      # NTA bijlage I.1: detailpositie zonder tabelwaarde

# nr: (omschrijving, psi_A, psi_B, aanvullende voorwaarde)
TABEL_I1_LAAGBOUW = {
    1:  ("Fundering, niet-dragende gevel", 0.27, 0.41, "systeemvloer, isolatie ≤60 mm van de funderingsbalk, Rc;gevel ≥ 4,7"),
    2:  ("Fundering, deur", 0.45, 0.68, "systeemvloer, kopse zijde funderingsbalk geïsoleerd, Rc;vloer ≥ 3,7"),
    3:  ("Fundering, dragende gevel", 0.60, 0.90, "oplegging 50 % geïsoleerd, steenachtig ≤150 mm, Rc;gevel ≥ 4,7"),
    4:  ("Fundering, woningscheidende wand", 0.00, 0.00, "geen"),
    5:  ("Gevel, onderdorpel kozijn", 0.15, 0.25, "hart kozijn binnen de isolatielijn"),
    6:  ("Gevel, zijstijl kozijn", 0.09, 0.19, "hart kozijn binnen de isolatielijn"),
    7:  ("Gevel, bovendorpel kozijn", 0.10, 0.20, "hart kozijn binnen de isolatielijn"),
    8:  ("Gevel, woningscheidende wand", 0.10, 0.20, "isolatie ≥65 % van de spouwbladwaarde, hooguit onderbroken door hout"),
    9:  ("Niet-dragende gevel, dragende gevel", 0.14, 0.24, "isolatie ≥65 %, hooguit onderbroken door hout"),
    10: ("Gevel, verdiepingsvloer", 0.09, 0.19, "isolatie ≥65 %, hooguit onderbroken door hout"),
    11: ("Gevel, bovendorpel met rooster", 0.15, 0.25, "isolatie conform de spouwbladen"),
    12: ("Niet-dragende gevel, dragende gevel (doorlopend)", 0.00, 0.00, "isolatie conform de spouwbladen"),
    13: ("Dakvoet, gevel, hellend dak", 0.16, 0.26, "isolatie ≥65 % van de dakisolatie"),
    14: ("Hellend dak, woningscheidende wand", 0.03, 0.13, "isolatie ≥65 % van de dakisolatie"),
    15: ("Gevel, hellend dak", 0.13, 0.23, "isolatie ≥65 % van de dakisolatie"),
    16: ("Nok hellend dak", 0.05, 0.15, "isolatie conform het dak"),
    17: ("Hellend dak, kozijn dakkapel", 0.06, 0.09, "isolatie ≥65 % van de dakisolatie"),
    18: ("Hellend dak, plat dak dakkapel", 0.50, 0.75, "isolatie ≥65 % van de dakisolatie"),
    19: ("Hellend dak, zijwang dakkapel", 0.13, 0.23, "isolatie conform dak en zijwang"),
    20: ("Hellend dak, onderzijde dakraam", 0.12, 0.22, "binnenzijde dakraam binnen de isolatielijn"),
    21: ("Hellend dak, zijaansluiting dakraam", 0.14, 0.24, "binnenzijde dakraam binnen de isolatielijn"),
    22: ("Hellend dak, bovenzijde dakraam", 0.12, 0.22, "binnenzijde dakraam binnen de isolatielijn"),
    23: ("Zakgoot", 0.24, 0.36, "isolatie ≥65 % van de dakisolatie"),
    24: ("Hellend dak, opgaand werk gevel", 0.13, 0.23, "isolatie conform dak en gevel (rvs metselwerkdragers: 0,41/0,62)"),
}

TABEL_I2_GESTAPELD = {
    50: ("Fundering, dragende gevel", 0.61, 0.92, "systeemvloer, isolatie ≤60 mm van de funderingsbalk, Rc;gevel ≥ 4,7"),
    51: ("Niet-dragende gevel, doorlopende vloer boven onverwarmde ruimte", 0.64, 0.96, "koudebrugonderbreking Rc ≥ 1,5"),
    52: ("Kozijn, doorlopende vloer boven onverwarmde ruimte", 0.64, 0.96, "koudebrugonderbreking onder kozijn Rc ≥ 2,5"),
    53: ("Inwendige hoek gevels loggia", 0.00, 0.00, "isolatie niet onderbroken in de hoek"),
    54: ("Gevel, onderdorpel kozijn", 0.15, 0.25, "hart kozijn binnen de isolatielijn"),
    55: ("Gevel, zijstijl kozijn", 0.09, 0.19, "hart kozijn binnen de isolatielijn"),
    56: ("Gevel, bovendorpel kozijn", 0.10, 0.20, "hart kozijn binnen de isolatielijn"),
    57: ("Inwendige hoek gevels loggia met gevel", 0.00, 0.00, "isolatie niet onderbroken in de hoek"),
    58: ("Verdiepingsvloer, galerij/balkon, gevel", 0.70, 1.05, "aanstortnokken ≤300 mm h.o.h. 1000 mm (doorlopende isolatie: 0,13/0,23)"),
    59: ("Verdiepingsvloer, galerij/balkon, kozijn", 0.70, 1.05, "idem (doorlopende isolatie: 0,35/0,53)"),
    60: ("Dakvloer, opgaande gevel", 0.16, 0.26, "koudebrugonderbreking Rc ≥ 1,5"),
    61: ("Dakvloer, kozijn opgaand werk", 0.16, 0.26, "koudebrugonderbreking Rc ≥ 1,5 onder kozijn"),
    62: ("Gevel, dakvloer, borstwering", 0.39, 0.59, "koudebrugonderbreking dakrand Rc ≥ 2,5"),
    63: ("Overkragende vloer, gevel", 0.31, 0.47, "metselwerkonderbreking h.o.h. ≥300 mm"),
    64: ("Doorlopende overkragende vloer, gevel", 0.00, 0.00, "vloerisolatie sluit op gevelisolatie"),
    65: ("Gevel, vloer boven onverwarmde ruimte", 0.36, 0.54, "gevelisolatie ≥300 mm onder vloerpeil"),
    66: ("Overkragende vloer, gevel", 0.33, 0.50, "metselwerkonderbreking h.o.h. >300 mm"),
    67: ("Vloer boven onverwarmde ruimte, gevel", 0.78, 1.17, "gevelisolatie ≥300 mm onder vloerpeil"),
    68: ("Dakrand, gevel, dakvloer", 0.16, 0.26, "koudebrugonderbreking dakrand Rc ≥ 2,5"),
    69: ("Gevel, verdiepingsvloer", 0.33, 0.50, "metselwerkonderbreking h.o.h. ≥300 mm"),
    70: ("Dakrand, gevel, dakvloer", 0.19, 0.29, "koudebrugonderbreking dakrand Rc ≥ 2,5"),
    71: ("Dakvloer, opgaande gevel", 0.19, 0.29, "koudebrugonderbreking Rc ≥ 1,5"),
    72: ("Uitkragende dakvloer, gevel", 0.44, 0.66, "doorlopende dakisolatie, onderzijde Rc ≥ 2,5 over ≥1000 mm"),
    73: ("Vloer boven onverwarmde ruimte, galerij/balkon, gevel", 0.84, 1.26, "aanstortnokken (doorlopende isolatie: 0,27/0,41)"),
    74: ("Vloer boven onverwarmde ruimte, galerij/balkon, kozijn", 0.84, 1.26, "idem (doorlopende isolatie: 0,38/0,57)"),
}

_GESTAPELD_KW = ("galerij", "portiek", "maisonnette", "appartement", "flat", "meergezins",
                 "bovenwoning", "boven bedrijf", "gestapeld", "woongebouw")


def is_gestapeld(woningtype):
    """True = tabel I.2 (gestapeld gebouw), False = tabel I.1 (grondgebonden/laagbouw)."""
    return any(k in (woningtype or "").lower() for k in _GESTAPELD_KW)


def tabel_voor(woningtype):
    return TABEL_I2_GESTAPELD if is_gestapeld(woningtype) else TABEL_I1_LAAGBOUW


def psi(nr, woningtype="", voorwaarden_gehaald=True):
    """ψ-waarde voor detailpositie `nr`. Onbekende positie -> PSI_DEFAULT (0,50, NTA bijlage I.1)."""
    rij = tabel_voor(woningtype).get(nr)
    if not rij:
        return PSI_DEFAULT
    return rij[1] if voorwaarden_gehaald else rij[2]


def _heeft(dos, pred):
    return any(pred(s) for s in getattr(dos, "schil", []) or [])


def relevante_details(dos):
    """Leid uit het dossier af wélke aansluitdetails in deze woning voorkomen.

    Retourneert een lijst dicts: {nr, omschrijving, psi_a, psi_b, voorwaarde, bron}. Bedoeld voor
    **Bijlage 7 Detailtekeningen** en als hulp bij forfaitair rekenen in Vabi. Bewust conservatief:
    alleen details die uit de opname blijken; de adviseur vult aan wat hij ter plaatse ziet.
    """
    wt = getattr(getattr(dos, "identificatie", None), "woningtype", "") or ""
    tab = tabel_voor(wt)
    gestapeld = is_gestapeld(wt)
    nrs = []

    def _t(s, *types):
        return (getattr(s, "type", "") or "").lower() in types

    heeft_gevel = _heeft(dos, lambda s: _t(s, "gevel"))
    heeft_kozijn = _heeft(dos, lambda s: _t(s, "kozijn"))
    heeft_hellend = _heeft(dos, lambda s: _t(s, "dak") and (getattr(s, "hellingshoek", 0) or 0) > 0)
    heeft_plat = _heeft(dos, lambda s: _t(s, "dak") and not (getattr(s, "hellingshoek", 0) or 0))
    heeft_dakraam = _heeft(dos, lambda s: "dakraam" in (getattr(s, "subtype", "") or "").lower())
    heeft_dakkapel = _heeft(dos, lambda s: "dakkapel" in ((getattr(s, "subtype", "") or "")
                                                          + (getattr(s, "id", "") or "")).lower())
    heeft_buurwand = any(k in wt.lower() for k in ("tussen", "hoek", "kop", "eind", "twee", "2-onder", "geschakeld"))

    if gestapeld:
        if heeft_gevel:
            nrs += [50, 65]
        if heeft_kozijn:
            nrs += [54, 55, 56]
        nrs += [69]                      # gevel/verdiepingsvloer komt in elk gestapeld gebouw voor
        if heeft_plat:
            nrs += [68, 62]
    else:
        if heeft_gevel:
            nrs += [1, 3]
        if heeft_kozijn:
            nrs += [5, 6, 7]
        nrs += [10]                      # gevel/verdiepingsvloer
        if heeft_buurwand:
            nrs += [4, 8]
            if heeft_hellend:
                nrs += [14]
        if heeft_hellend:
            nrs += [13, 15, 16]
        if heeft_dakraam:
            nrs += [20, 21, 22]
        if heeft_dakkapel:
            nrs += [17, 18, 19]

    out = []
    for nr in sorted(set(nrs)):
        rij = tab.get(nr)
        if not rij:
            continue
        oms, pa, pb, vw = rij
        out.append({"nr": nr, "omschrijving": oms, "psi_a": pa, "psi_b": pb, "voorwaarde": vw,
                    "bron": "NTA 8800 bijlage I, tabel %s" % ("I.2" if gestapeld else "I.1")})
    return out
