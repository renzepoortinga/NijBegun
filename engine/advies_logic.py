"""
Beslislogica "welk advies wanneer" — onze eigen, OFFLINE maatregel-adviesmotor (geen AI/tokens).
Bepaalt per bouwdeel + huidige staat welke maatregel(en) passen, met rationale en prioriteit, en
voegt de dossier-brede regels toe (ventilatie na isoleren; kierdichting). Voedt de kostenoptimalisatie
(engine/measure_engine) en de begeleidende tekst (engine/advies_text).

Het is bewust pure logica: transparante regels afgeleid uit de Maatregelencatalogus (families per
onderdeel A-E) + de RVO-streefwaarden en NTA8800-principes. Geen externe tool nagebouwd.

    from engine.advies_logic import adviseer_dossier
    advies = adviseer_dossier(dossier)   # -> {bouwdelen:[...], algemeen:[...]}

Kernprincipes (zoals een goede isolatieadviseur redeneert):
  1. Isoleer eerst het slechtst presterende, grootste vlak (meeste winst per euro).
  2. Spouw aanwezig -> spouwmuurisolatie is de goedkoopste effectieve eerste stap.
  3. Geen spouw / massief -> binnen- (voorzetwand) of buitengevelisolatie.
  4. Isoleren maakt luchtdichter -> borg ventilatie (balans/WTW) en kierdichting.
  5. Doel = de Standaard (Vabi rekent die exact); streefwaarden zijn richtinggevend.
"""
from __future__ import annotations

# RVO-streefwaarden per bouwdeel (richtinggevend doel). (Rc in m2K/W, U in W/m2K.)
STREEF = {"gevel": ("Rc", 5.0), "dak": ("Rc", 6.5), "vloer": ("Rc", 3.7),
          "raam": ("U", 1.6), "deur": ("U", 2.0), "paneel": ("U", 1.2)}

# minimale isolatiedikte (mm) waarboven een dicht deel als "op niveau" geldt voor advies-triggering
_DIKTE_OK = {"gevel": 80, "dak": 120, "vloer": 80}


def _kind(s):
    t = (s.type or "").lower()
    if t == "kozijn":
        if getattr(s, "deur_met_raam_glas65", False) or "deur" in (s.subtype or "").lower():
            return "deur"
        return "raam"
    return t


def _isolatie_op_niveau(s):
    """Heeft dit dichte deel al voldoende isolatie (dan geen isolatie-advies)?"""
    kind = _kind(s)
    ja = (s.isolatie_aanwezig or "").lower() in ("ja", "wel")
    if not ja:
        return False
    rc = getattr(s, "rc_huidig", None)
    streef = STREEF.get(kind)
    if rc is not None and streef and streef[0] == "Rc" and rc >= streef[1]:
        return True
    dikte = getattr(s, "isolatiedikte_mm", None)
    if dikte is not None and dikte >= _DIKTE_OK.get(kind, 80):
        return True
    return False


def _glas_zwak(glastype):
    g = (glastype or "").lower()
    return any(k in g for k in ("enkel", "voorzet", "dubbel")) and "hr" not in g and "triple" not in g and "vacu" not in g


# ---- adviesregels per bouwdeel ----
def adviseer_schildeel(s):
    """-> lijst adviezen [{situatie, advies, materialen, prioriteit, rationale, biobased, doel}]."""
    kind = _kind(s)
    adv = []
    streef = STREEF.get(kind)
    doel = ("%s %.1f" % streef) if streef else ""

    if kind == "gevel":
        if _isolatie_op_niveau(s):
            return []
        spouw = getattr(s, "spouw_aanwezig", None)
        if spouw is True:
            adv.append(dict(situatie="Spouwmuur aanwezig, niet/licht geisoleerd",
                            advies="Spouwmuurisolatie", materialen="minerale wol vlokken | EPS parels | PUR-schuim",
                            prioriteit=1, biobased=False, doel=doel,
                            rationale="Goedkoopste effectieve maatregel: de bestaande spouw wordt gevuld; "
                                      "snel uitvoerbaar, weinig overlast."))
        else:
            adv.append(dict(situatie="Geen (bruikbare) spouw / massieve gevel",
                            advies="Binnenisolatie (voorzetwand) of buitengevelisolatie",
                            materialen="voorzetwand glas-/hout-/hennep-/vlasvezel of PIR | buitengevel ETICS",
                            prioriteit=2, biobased=True, doel=doel,
                            rationale="Zonder spouw is na-isolatie aan binnen- of buitenzijde nodig. "
                                      "Buitenzijde is thermisch het best (geen koudebruggen), binnenzijde "
                                      "als de gevel buiten behouden moet blijven."))
    elif kind == "dak":
        if _isolatie_op_niveau(s):
            return []
        plat = "plat" in (s.subtype or "").lower()
        adv.append(dict(situatie="Dak niet/onvoldoende geisoleerd",
                        advies="Dakisolatie %s" % ("(plat dak)" if plat else "(hellend dak)"),
                        materialen="glaswol | PIR-platen | biobased (vlas/gras/hennep/houtvezel) | gespoten schuim",
                        prioriteit=1, biobased=True, doel=doel,
                        rationale="Warmte stijgt; een ongeisoleerd dak is een groot lek met hoog rendement. "
                                  "Binnenzijde isoleren of meenemen bij dakvervanging (buitenzijde)."))
    elif kind == "vloer":
        if _isolatie_op_niveau(s):
            return []
        kruip = "kruip" in (getattr(s, "begrenzing", "") or "").lower()
        adv.append(dict(situatie="Vloer niet/onvoldoende geisoleerd%s" % (", kruipruimte aanwezig" if kruip else ""),
                        advies="Bodemisolatie en/of vloerisolatie (onderzijde)",
                        materialen="EPS-korrels (bodem) | isolatiefolie | PUR-schuim | EPS-platen",
                        prioriteit=2, biobased=False, doel=doel,
                        rationale="Bij toegankelijke kruipruimte is bodem-/vloerisolatie goedkoop en comfortabel "
                                  "(minder koude voeten); combineer met kierdichting van vloerranden."))
    elif kind == "raam":
        if _glas_zwak(s.glastype):
            adv.append(dict(situatie="Enkel/dubbel glas (geen HR)",
                            advies="Vervangen door HR++ (of triple), of voorzetbeglazing bij behoud kozijn",
                            materialen="HR++ glas | triple | voorzetraam (monument/behoud)",
                            prioriteit=2, biobased=False, doel=doel,
                            rationale="HR++/triple halveert het glasverlies en stopt koudeval/tocht. "
                                      "Voorzetbeglazing waar het kozijn/monument behouden moet blijven."))
    elif kind == "deur":
        ja = (s.isolatie_aanwezig or "").lower() in ("ja", "wel")
        if not ja:
            adv.append(dict(situatie="Ongeisoleerde buitendeur",
                            advies="Vervangen door geisoleerde deur",
                            materialen="geisoleerde buitendeur", prioriteit=3, biobased=False, doel=doel,
                            rationale="Beperkt verlies en tocht; meestal kleine oppervlakte dus lagere prioriteit."))
    return adv


def adviseer_dossier(dossier):
    """Volledig advies: per bouwdeel + dossier-brede regels (ventilatie na isoleren, kierdichting)."""
    bouwdelen = []
    geisoleerd_iets = False
    for s in getattr(dossier, "schil", []) or []:
        for a in adviseer_schildeel(s):
            a["schildeel_id"] = getattr(s, "id", "")
            a["oppervlakte_m2"] = getattr(s, "oppervlakte_m2", 0)
            bouwdelen.append(a)
            if a["advies"].lower().startswith(("spouw", "dakisol", "bodem", "binnenisol", "vloerisol")):
                geisoleerd_iets = True

    algemeen = []
    # 1) ventilatie na isoleren
    vent = getattr(dossier, "ventilatie", None)
    syst = (getattr(vent, "systeem", "") or "").lower() if vent else ""
    if geisoleerd_iets:
        if syst.startswith("a") or "natuurlijk" in syst:
            algemeen.append(dict(situatie="Schil wordt luchtdichter + alleen natuurlijke ventilatie",
                                 advies="Ventilatie upgraden (mechanische afvoer met CO2-sturing of balans-WTW)",
                                 prioriteit=1,
                                 rationale="Isoleren verhoogt de luchtdichtheid; zonder adequate, liefst "
                                           "gebalanceerde ventilatie ontstaat vocht-/schimmelrisico. WTW bespaart "
                                           "bovendien energie. (Bijlage 'Waarom ventileren'.)"))
        else:
            algemeen.append(dict(situatie="Schil wordt luchtdichter, mechanische ventilatie aanwezig",
                                 advies="Ventilatiecapaciteit/sturing controleren (evt. CO2-sturing/WTW)",
                                 prioriteit=2,
                                 rationale="Controleer of de bestaande ventilatie na isoleren voldoende en "
                                           "gebalanceerd is; overweeg CO2-sturing of WTW."))
    # 2) kierdichting / luchtdichtheid
    opn = getattr(dossier, "opname", None)
    if geisoleerd_iets:
        algemeen.append(dict(situatie="Na isolatie",
                             advies="Kierdichting (kozijnen, vloerranden, muurplaten, draaiende delen)",
                             prioriteit=2,
                             rationale="Kierdichting verlaagt de infiltratie (qv;10) en is goedkoop; nodig om de "
                                       "Standaard te halen. Eventueel blowerdoortest om qv;10 aan te tonen."))
    # sorteer op prioriteit
    bouwdelen.sort(key=lambda a: a.get("prioriteit", 9))
    algemeen.sort(key=lambda a: a.get("prioriteit", 9))
    return {"bouwdelen": bouwdelen, "algemeen": algemeen}


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.dossier import Dossier, SchilDeel, Ventilatie
    dos = Dossier()
    dos.schil = [
        SchilDeel(id="gevel", type="gevel", isolatie_aanwezig="Nee", spouw_aanwezig=True, oppervlakte_m2=80),
        SchilDeel(id="dak", type="dak", isolatie_aanwezig="Onbekend", oppervlakte_m2=55),
        SchilDeel(id="vloer", type="vloer", isolatie_aanwezig="Nee", begrenzing="Kruipruimte", oppervlakte_m2=50),
        SchilDeel(id="raam-1", type="kozijn", glastype="Dubbel", oppervlakte_m2=12),
    ]
    try:
        dos.ventilatie = Ventilatie(systeem="A Natuurlijke ventilatie")
    except Exception:
        pass
    r = adviseer_dossier(dos)
    print("=== BOUWDELEN ===")
    for a in r["bouwdelen"]:
        print("P%d %-8s %s -> %s" % (a["prioriteit"], a["schildeel_id"], a["situatie"], a["advies"]))
    print("=== ALGEMEEN ===")
    for a in r["algemeen"]:
        print("P%d %s -> %s" % (a["prioriteit"], a["situatie"], a["advies"]))
