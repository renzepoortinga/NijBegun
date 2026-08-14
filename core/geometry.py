"""
Geometrie-helpers voor de schil-oppervlakten die NIET rechtstreeks uit MagicPlans plattegrond
komen: het schuine dakvlak en de kopgevel-driehoek bij een hellend dak.

MagicPlan meet de plattegrond (footprint) + per wand de oppervlakte; het schuine dak en de
gevel-driehoek (boven de muurplaat) volgen uit de footprint + de hellingshoek. Voor een eenvoudig
zadeldak rekent de tool dit uit; bij een complex dak voert de adviseur de m2 handmatig in.

Definities (zadeldak, nok in het midden):
  - breedte B  = overspanning loodrecht op de nok (= footprintbreedte)
  - lengte  L  = lengte langs de nok (= footprintlengte)
  - helling a  = dakhelling in graden
  Schuin dakvlak (2 vlakken samen) = B * L / cos(a)              [= footprint / cos(a)]
  Kopgevel-driehoek per kopgevel    = 0.5 * B * (B/2) * tan(a)   [twee kopgevels => x2]
"""
import math

# ISSO 82.1 (7e druk) par. 8.2: horizontale gevelafmetingen meet je BINNENWERKS, maar tot de
# HARTMAAT van de gebouwscheidende wand waar de rekenzone aan een ander gebouw grenst. Is de
# dikte niet meetbaar, tel dan +11 cm per gebouwscheidende wand bij de gevelBREEDTE op
# (hoekwoning +11 cm; tussenwoning +22 cm = 2 x 11). Uitgangspunt: gebouwscheidende wand = 22 cm
# dik -> halve dikte = 0,11 m. Die gevelbreedte geldt voor zowel de VOOR- als de ACHTERGEVEL.
HARTMAAT_GEBOUWSCHEIDENDE_WAND_M = 0.11


def polygon_oppervlakte_m2(punten):
    """Oppervlakte van een gesloten veelhoek via de schoenveter-formule.
    `punten` = lijst (x, y)-paren in dezelfde eenheid (bv. meter of pixel); de
    veelhoek hoeft niet convex te zijn, en de omloopvolgorde (met/tegen de klok
    mee) maakt niet uit -> geeft altijd 0.0 bij minder dan 3 punten."""
    if len(punten) < 3:
        return 0.0
    totaal = 0.0
    n = len(punten)
    for i in range(n):
        x1, y1 = punten[i]
        x2, y2 = punten[(i + 1) % n]
        totaal += x1 * y2 - x2 * y1
    return abs(totaal) / 2


def aantal_woningscheidende_wanden(woningtype):
    """Aantal gebouwscheidende (buur)wanden uit de woningpositie (ISSO 82.1 par. 7.1.1).
    vrijstaand -> 0 · hoek/eind/kop -> 1 · twee-onder-een-kap -> 1 · tussen -> 2."""
    w = (woningtype or "").lower()
    if "vrijstaand" in w:
        return 0
    if "tussen" in w:
        return 2
    if any(k in w for k in ("hoek", "kop", "eind", "twee", "2-onder", "2 onder",
                            "onder-een-kap", "onder een kap")):
        return 1
    return 0


def woningscheidende_wand_toeslag_m2(gevelhoogte_m, woningtype,
                                     halve_dikte_m=HARTMAAT_GEBOUWSCHEIDENDE_WAND_M):
    """Hart-op-hart gevel-toeslag (m2) bij een hoek-/tussenwoning (ISSO 82.1 par. 8.2).
    Per gebouwscheidende wand groeit de gevelBREEDTE met de halve wanddikte (0,11 m); die breedte
    geldt voor zowel de voor- als de achtergevel. Toeslag = 2 (voor+achter) x n_buurwanden x 0,11 x
    gevelhoogte. Tussenwoning (n=2): 0,44 x hoogte. Hoekwoning (n=1): 0,22 x hoogte. Vrijstaand: 0.
    Alleen toepassen als de gevel BINNENWERKS is gemeten (zoals MagicPlan doet), niet bij een
    meting die al tot de hartmaat is uitgevoerd."""
    n = aantal_woningscheidende_wanden(woningtype)
    if not gevelhoogte_m or gevelhoogte_m <= 0 or n == 0:
        return 0.0
    return round(2 * n * halve_dikte_m * gevelhoogte_m, 2)


def _cos(a_deg):
    return math.cos(math.radians(a_deg))


def _tan(a_deg):
    return math.tan(math.radians(a_deg))


def schuin_dakvlak_m2(footprint_m2, hellingshoek_graden):
    """Totaal schuin dakoppervlak uit horizontale projectie (footprint) en helling.
    footprint/cos(a). Geldig voor symmetrisch zadeldak en lessenaarsdak."""
    c = _cos(hellingshoek_graden)
    if c <= 0:
        return footprint_m2
    return round(footprint_m2 / c, 2)


def kopgevel_driehoek_m2(breedte_m, hellingshoek_graden, aantal_kopgevels=2):
    """Gevel-driehoek(en) boven de muurplaat bij een zadeldak met nok in het midden.
    Per kopgevel: 0.5 * B * (B/2)*tan(a). Default 2 kopgevels."""
    nokhoogte = (breedte_m / 2.0) * _tan(hellingshoek_graden)
    per_driehoek = 0.5 * breedte_m * nokhoogte
    return round(per_driehoek * aantal_kopgevels, 2)


def oppervlak_vorm(vorm, a=0.0, b=0.0):
    """m2 uit een vorm + maten (idee uit standaard EPA-opname: vorm-gebaseerde invoer).
    rechthoek: a*b · driehoek: 0.5*a*b · cirkel: pi*(a/2)^2 (a=diameter) · ellips: pi*(a/2)*(b/2)."""
    v = (vorm or "").lower()
    if "driehoek" in v:
        return round(0.5 * a * b, 2)
    if "cirkel" in v:
        return round(math.pi * (a / 2.0) ** 2, 2)
    if "ellips" in v:
        return round(math.pi * (a / 2.0) * (b / 2.0), 2)
    # rechthoek / overig
    return round(a * b, 2)


def dakkapel_vlakken(breedte_m, hoogte_m, diepte_m, hellingshoek_dakvlak_graden=None):
    """ISSO 82.1 §8.2.1: een (plat) dakkapel voegt vlakken toe aan de thermische schil:
      - voorvlak  = breedte × hoogte  -> GEVEL (het raam erin voer je apart op als kozijn)
      - 2 wangen  = 2 × diepte × hoogte -> GEVEL (oriëntaties ±90° t.o.v. het voorvlak)
      - plat dakje = breedte × diepte  -> PLAT DAK
    En het GAT dat de kapel in het schuine dakvlak maakt = (breedte × diepte)/cos(a) moet je
    van dat schuine dakvlak AFTREKKEN (anders dubbeltelling). Zonder hellingshoek slaan we de
    gat-aftrek over en flaggen we dat. -> dict {gevel_m2, dak_m2, gat_schuin_dak_m2, flag}."""
    gevel = breedte_m * hoogte_m + 2.0 * (diepte_m * hoogte_m)
    dak = breedte_m * diepte_m
    if hellingshoek_dakvlak_graden and 0 < hellingshoek_dakvlak_graden < 90:
        gat = round((breedte_m * diepte_m) / _cos(hellingshoek_dakvlak_graden), 2)
        flag = "dakkapel: voorvlak+2 wangen = gevel, dakje = plat dak; gat %.2f m2 van het schuine dakvlak afgetrokken." % gat
    else:
        gat = 0.0
        flag = "dakkapel: voorvlak+2 wangen = gevel, dakje = plat dak; GAT in het schuine dak NIET afgetrokken (hellingshoek onbekend) -> verifieer in Vabi."
    return {"gevel_m2": round(gevel, 2), "dak_m2": round(dak, 2), "gat_schuin_dak_m2": gat, "flag": flag}


def ag_onder_schuin_dak(footprint_m2, eave_lengte_m, hellingshoek_graden,
                        kniewandhoogte_m=0.0, min_hoogte_m=1.5, aantal_schuine_zijden=2):
    """Gebruiksoppervlakte (Ag) onder een schuin dak: alleen waar de hoogte >= 1,5 m telt mee.
    Per schuine zijde valt een strook met breedte x = (1,5 - kniewandhoogte)/tan(a) weg
    (0 als de kniewand al >= 1,5 m is). reductie = aantal_zijden * x * eave_lengte.

    footprint_m2 = volle vloeroppervlak (MagicPlan); eave_lengte_m = lengte langs de goot
    (= lengte van de nok). Geeft (ag_m2, weggevallen_m2)."""
    if hellingshoek_graden <= 0 or hellingshoek_graden >= 90:
        return round(footprint_m2, 2), 0.0
    strook = max(0.0, (min_hoogte_m - kniewandhoogte_m) / _tan(hellingshoek_graden))
    weg = round(min(strook * aantal_schuine_zijden * eave_lengte_m, footprint_m2), 2)
    return round(footprint_m2 - weg, 2), weg


def dak_en_kopgevel(footprint_m2, breedte_m, hellingshoek_graden,
                    type_dak="zadeldak", aantal_kopgevels=2):
    """-> dict met schuin dakoppervlak + extra gevel-m2 (kopgevel-driehoeken).
    type_dak: 'zadeldak' (2 kopgevels) | 'lessenaar' (1 kopgevel, half dakvlak) | 'plat' (geen helling)."""
    t = (type_dak or "zadeldak").lower()
    if "plat" in t:
        return {"dak_m2": round(footprint_m2, 2), "extra_gevel_m2": 0.0, "toelichting": "plat dak = footprint"}
    if "lessenaar" in t:
        return {"dak_m2": schuin_dakvlak_m2(footprint_m2, hellingshoek_graden),
                "extra_gevel_m2": 0.0,
                "toelichting": "lessenaar: schuin vlak = footprint/cos(a); zijgevel-driehoeken handmatig opgeven"}
    # zadeldak
    return {"dak_m2": schuin_dakvlak_m2(footprint_m2, hellingshoek_graden),
            "extra_gevel_m2": kopgevel_driehoek_m2(breedte_m, hellingshoek_graden, aantal_kopgevels),
            "toelichting": "zadeldak: dak = footprint/cos(a); gevel += %d kopgevel-driehoek(en)" % aantal_kopgevels}


def hellingshoek_uit_nok(vloerbreedte_m, nokhoogte_m, knieschothoogte_m=0.0, aantal_schuine_zijden=2):
    """Dakhelling (graden) uit de meetinstructie: vloerbreedte, nokhoogte, knieschothoogte.
    Symmetrisch zadeldak (nok in het midden): horizontale afstand b = vloerbreedte/aantal_schuine_zijden,
    hoogteverschil h = nokhoogte - knieschothoogte. tan(alpha) = h / b  ->  alpha = atan(h/b).
    Lessenaar: aantal_schuine_zijden=1 (b = volle vloerbreedte). Geeft None bij ongeldige invoer."""
    if not vloerbreedte_m or vloerbreedte_m <= 0:
        return None
    b = vloerbreedte_m / max(int(aantal_schuine_zijden or 1), 1)
    h = (nokhoogte_m or 0.0) - (knieschothoogte_m or 0.0)
    if h <= 0 or b <= 0:
        return None
    return round(math.degrees(math.atan(h / b)), 1)


def dakvlak_m2(footprint_of_breedte_lengte_m2, hellingshoek_graden, m2_handmatig=None):
    """Oppervlak van één (schuin) dakvlak. Handmatige m2 wint; anders horizontale projectie / cos(a).
    audit 13-7: een LEEG veld dat als 0.0 doorkomt mag de berekening niet blokkeren (gaf 0-m2-dak)."""
    if m2_handmatig:
        return round(float(m2_handmatig), 2)
    return schuin_dakvlak_m2(footprint_of_breedte_lengte_m2, hellingshoek_graden)


def dak_vlakken_lessenaar(footprint_m2, hellingshoek_graden, orient=""):
    """Lessenaarsdak (mono-pitch): ÉÉN schuin vlak = footprint/cos(a) op één oriëntatie. De twee
    zijgevel-driehoeken (trapezium-top) zijn klein en voert de adviseur zo nodig handmatig in Vabi in."""
    return [{"kind": "dak", "type": "lessenaar", "orientatie": orient,
             "m2": schuin_dakvlak_m2(footprint_m2, hellingshoek_graden), "hellingshoek": hellingshoek_graden}]


def dak_vlakken_schilddak(footprint_m2, hellingshoek_graden, orients=()):
    """Schilddak (hip/tentdak): ALLE zijden zijn dakvlakken (GEEN verticale kopgevel-driehoek, ánders
    dan een zadeldak). Totaal schuin oppervlak = footprint/cos(a), verdeeld over de opgegeven
    oriëntaties (gelijk verdeeld — de exacte verdeling van hoofd- vs schildvlakken verfijnt de adviseur
    in Vabi). Geeft dus uitsluitend dak-vlakken terug, geen gevel-driehoeken."""
    tot = schuin_dakvlak_m2(footprint_m2, hellingshoek_graden)
    os_ = [o for o in orients if o] or [""]
    per = round(tot / len(os_), 2)
    return [{"kind": "dak", "type": "schild", "orientatie": o, "m2": per,
             "hellingshoek": hellingshoek_graden} for o in os_]


def dak_vlakken_zadeldak(footprint_m2, breedte_m, hellingshoek_graden,
                         orient_schuin=(), orient_kopgevel=()):
    """Symmetrisch zadeldak -> lijst vlakken (dict: kind, type, orientatie, m2, hellingshoek).
    Twee schuine dakvlakken (samen footprint/cos(a), elk de helft) op orient_schuin=(o1,o2);
    kopgevel-driehoeken (kind='gevel') op orient_kopgevel=(k1,k2). Voor complexe daken voert
    de adviseur de vlakken handmatig per stuk in (m2 + orientatie)."""
    out = []
    tot = schuin_dakvlak_m2(footprint_m2, hellingshoek_graden)
    half = round(tot / 2.0, 2)
    for o in [x for x in orient_schuin if x][:2]:
        out.append({"kind": "dak", "type": "schuin", "orientatie": o, "m2": half,
                    "hellingshoek": hellingshoek_graden})
    kop = kopgevel_driehoek_m2(breedte_m, hellingshoek_graden, 1) if breedte_m else 0.0
    for k in [x for x in orient_kopgevel if x]:
        out.append({"kind": "gevel", "type": "kopgevel-driehoek", "orientatie": k, "m2": kop})
    return out


if __name__ == "__main__":
    # Oosterkade-achtig voorbeeld: footprint ~63 m2, breedte 6 m, helling 45 graden
    print("schuin dak (63 m2, 45 gr):", schuin_dakvlak_m2(63, 45), "m2")
    print("helling uit nok (breedte 6, nok 3, knie 0):", hellingshoek_uit_nok(6, 3, 0))
    print("kopgevel-driehoek (B=6, 45 gr, 2x):", kopgevel_driehoek_m2(6, 45), "m2")
    print(dak_en_kopgevel(63, 6, 45))
    print(dak_en_kopgevel(63, 6, 30, type_dak="plat"))
