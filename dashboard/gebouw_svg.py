"""Read-only isometrisch gebouwoverzicht uit de opgeslagen dossiergeometrie.

Dit is uitsluitend een presentatielaag. Twee footprint-bronnen, in deze volgorde:
1. een ECHTE plattegrondcontour uit de MagicPlan-API (`VloerInfo.contour_m`, gevuld door
   `magicplan/assemble.py`) -> de gevels volgen de werkelijke (ook niet-rechthoekige) vorm;
2. zonder contour: een 3D-volume wordt alleen getekend als alle vier gevelrichtingen en een
   gevelhoogte een rechthoekige footprint dragen. Tegenoverliggende gevelbreedtes mogen
   maximaal 25% verschillen: dat is dezelfde grens waarmee de MagicPlan-import een mogelijke
   dubbeltelling signaleert.
Het dak blijft in beide gevallen op de rechthoekige (of bij een contour: bounding-box-)
footprint getekend — een dak dat zelf de polygon-vorm volgt is nog niet gebouwd.
De renderer corrigeert geen invoer en rekent geen NTA 8800-resultaten.
"""

from __future__ import annotations

import html
import math

from core.geometry import polygon_oppervlakte_m2

C_INK = "var(--ink)"
C_SUB = "var(--sub)"
C_CARD = "var(--card)"
C_HOUSE = "var(--info-bg)"
C_HOUSE_LINE = "var(--blue)"
C_DAK = "var(--tint)"
C_DAK_LINE = "var(--sub)"
C_DAKKAPEL = "var(--warn-bg)"
C_DAKKAPEL_LINE = "var(--orange)"
C_KNOWN = "var(--ok-fg)"
C_UNKNOWN = "var(--sub)"

_COS30 = math.sqrt(3) / 2
_SIN30 = .5
_GEVELNAMEN = {
    "voor": "voor", "voorgevel": "voor",
    "achter": "achter", "achtergevel": "achter",
    "links": "links", "linker": "links", "linkergevel": "links",
    "rechts": "rechts", "rechter": "rechts", "rechtergevel": "rechts",
}
_TOLERANTIE = .25


def _esc(value):
    return html.escape(str(value or ""), quote=True)


def _project(point):
    x, y, z = point
    return ((x - z) * _COS30, (x + z) * _SIN30 - y)


def _naam(schildeel):
    return _GEVELNAMEN.get((schildeel.gevel_naam or "").strip().lower(), "")


def _is_dakkapel(schildeel):
    return bool(schildeel.moedervlak_id or "dakkapel" in (schildeel.subtype or "").lower()
                or "dakkapel" in (schildeel.id or "").lower())


def _hoofgevels(dos):
    groepen = {naam: [] for naam in ("voor", "achter", "links", "rechts")}
    for schildeel in dos.schil:
        if (schildeel.type or "").lower() != "gevel" or _is_dakkapel(schildeel):
            continue
        naam = _naam(schildeel)
        if naam:
            groepen[naam].append(schildeel)
    return groepen


def _geldige_hoogte(hoogte):
    return bool(hoogte) and math.isfinite(hoogte) and hoogte > 0


def _footprint(dos):
    """Geef (breedte, diepte, gevelhoogte, groepen, reden) zonder maten te gokken."""
    groepen = _hoofgevels(dos)
    hoogte = dos.opname.gevelhoogte_m
    if not _geldige_hoogte(hoogte):
        return None, groepen, "gevelhoogte ontbreekt"
    if any(not groepen[naam] for naam in groepen):
        return None, groepen, "niet alle vier gevelnamen zijn aanwezig"
    oppervlakken = {naam: sum(max(0, s.oppervlakte_m2 or 0) for s in delen)
                    for naam, delen in groepen.items()}
    if any(not waarde for waarde in oppervlakken.values()):
        return None, groepen, "een gevel heeft geen bruikbaar oppervlak"
    maten = {naam: waarde / hoogte for naam, waarde in oppervlakken.items()}

    def consistent(a, b):
        return max(a, b) <= (1 + _TOLERANTIE) * min(a, b)

    if not consistent(maten["voor"], maten["achter"]):
        return None, groepen, "voor- en achtergevel verschillen meer dan 25%"
    if not consistent(maten["links"], maten["rechts"]):
        return None, groepen, "linker- en rechtergevel verschillen meer dan 25%"
    # Binnen de bestaande MagicPlan-tolerantie is het gemiddelde de enige
    # symmetrische afleiding; beide gemeten gevels wegen even zwaar.
    breedte = (maten["voor"] + maten["achter"]) / 2
    diepte = (maten["links"] + maten["rechts"]) / 2
    return (breedte, diepte, hoogte), groepen, ""


def _contour_geldig(contour):
    """Minstens 3 punten, en elke coördinaat een eindig getal (geen NaN/Infinity).

    `assemble.py` filtert dit al bij het inlezen, maar een dossier kan ook handmatig bewerkt of
    uit een ander pad komen -> hier nogmaals bewaken vóór er iets mee gerenderd wordt (zelfde
    'niet gokken'-regel: liever de rechthoek-fallback dan onbruikbare NaN-coördinaten tekenen)."""
    if not contour or len(contour) < 3:
        return False
    return all(len(p) == 2 and math.isfinite(p[0]) and math.isfinite(p[1]) for p in contour)


def _polygon_footprint(dos):
    """Geef (contour_xz, gevelhoogte) uit een ECHTE MagicPlan-plattegrondomtrek, of None.

    Alleen gevuld als de API-route (`magicplan/assemble.py`) een `contour_m` op een bouwlaag
    opsloeg (de CSV-route kent dit veld niet -> altijd None daar, aanroeper valt dan terug op
    `_footprint()`). Neemt de contour van de grootste bouwlaag (zelfde 'footprint-proxy'-logica
    als `assemble.geometry_from_plan`). Een lijnvormige/ontaarde contour wordt verworpen."""
    vloeren = [v for v in (dos.geometrie.vloeren or []) if _contour_geldig(v.contour_m)]
    if not vloeren:
        return None
    hoogte = dos.opname.gevelhoogte_m
    if not _geldige_hoogte(hoogte):
        return None
    grootste = max(vloeren, key=lambda v: v.oppervlakte_m2 or 0)
    if polygon_oppervlakte_m2(grootste.contour_m) <= 1.0:
        return None
    return grootste.contour_m, hoogte


def _muurvlakken(punten, wall_h):
    """Eén gevelvlak per zichtbare rand van een willekeurige (ook concave) veelhoek.

    Backface-culling voor déze iso-camera (kijkrichting ~ (+x,+y,-z), zie `_project`): een rand is
    zichtbaar als zijn naar-buiten-wijzende normaal (nx, nz) voldoet aan nx - nz > 0. De
    buiten-normaal volgt uit de omlooprichting (schoenveter-teken) van de hele veelhoek, NIET uit
    een 'wijst van het middelpunt af'-test: bij een concaaf grondvlak (bv. een L- of U-vorm) kan
    het simpele gemiddelde van de hoekpunten buiten de veelhoek vallen, wat bij sommige randen de
    normaal zou omdraaien en een echte buitenmuur ten onrechte zou verbergen (of andersom). De
    omlooprichting is wél altijd consistent voor een enkelvoudige (niet-zelfoverlappende) veelhoek.
    Geen volledige z-buffer — bij een sterk concaaf grondvlak kan een verre rand per ongeluk vóór
    een nabije rand belanden; de painter's-order-sortering hieronder dekt de gebruikelijke
    L-vormige aanbouw, niet elke denkbare vorm.

    Een contourrand komt niet 1-op-1 overeen met een MagicPlan-gevelnaam, dus deze vlakken
    dragen geen `deel` — traceerbaarheid van de onderliggende SchilDelen loopt via de
    render-metadata-laag onderaan `gebouw_svg`, niet via een label op de muur zelf.

    De gebouwde vlakpunten worden altijd in dezelfde canonieke omlooprichting opgeleverd
    (onder-links, onder-rechts, boven-rechts, boven-links vanuit het perspectief van de camera),
    ONGEACHT of de aangeleverde contour zelf met- of tegen de klok in loopt. `_shade()` (de
    richtingsafhankelijke helderheid) leest de normaal namelijk rechtstreeks uit de eerste twee
    randen van elk vlak zonder de omlooprichting van de brontekening te kennen — zonder deze
    normalisatie zou een tegen-de-klok-in aangeleverde MagicPlan-contour precies de omgekeerde
    (dus 'verkeerd om') schaduw krijgen van een fysiek identiek gebouw met de andere omlooprichting."""
    n = len(punten)
    schoenveter = sum(punten[i][0] * punten[(i + 1) % n][1] - punten[(i + 1) % n][0] * punten[i][1]
                      for i in range(n))
    teken = 1 if schoenveter >= 0 else -1
    ranked = []
    for i in range(n):
        x1, z1 = punten[i]
        x2, z2 = punten[(i + 1) % n]
        nx, nz = teken * (z2 - z1), teken * -(x2 - x1)
        if nx - nz <= 0:                          # niet zichtbaar voor deze camera -> weglaten
            continue
        if teken == -1:                           # canoniseer de omlooprichting (zie docstring)
            x1, z1, x2, z2 = x2, z2, x1, z1
        mx, mz = (x1 + x2) / 2, (z1 + z2) / 2
        diepte = mx + wall_h / 2 - mz
        ranked.append((diepte, _face([(x1, 0, z1), (x2, 0, z2), (x2, wall_h, z2), (x1, wall_h, z1)],
                                      None, "gevel-contour", C_HOUSE, C_HOUSE_LINE)))
    return [f for _, f in sorted(ranked, key=lambda t: t[0])]


def _dakvlakken(dos):
    return [s for s in dos.schil if (s.type or "").lower() == "dak" and not _is_dakkapel(s)]


def _attrs(schildeel, extra=""):
    return ('data-element-id="%s" data-oppervlakte-m2="%.2f" data-orientatie="%s"%s'
            % (_esc(schildeel.id), schildeel.oppervlakte_m2 or 0,
               _esc(schildeel.orientatie), extra))


def _fallback(dos, titel, reden):
    delen = [s for s in dos.schil if (s.type or "").lower() in ("gevel", "dak")]
    hoogte = 190 + max(1, len(delen)) * 28
    p = ['<svg viewBox="0 0 900 %d" xmlns="http://www.w3.org/2000/svg" role="img" '
         'aria-labelledby="gebouw-titel gebouw-uitleg">' % hoogte,
         '<title id="gebouw-titel">%s</title>' % _esc(titel),
         '<desc id="gebouw-uitleg">Vereenvoudigd aanzicht; kon geen betrouwbare 3D-vorm afleiden.</desc>',
         '<rect width="900" height="%d" fill="%s"/>' % (hoogte, C_CARD),
         '<text x="32" y="42" font-size="var(--svg-fs-8)" font-weight="700" fill="%s">%s</text>'
         % (C_INK, _esc(titel)),
         '<text x="32" y="76" font-size="var(--svg-fs-5)" font-weight="650" fill="%s">'
         'Kon geen 3D-vorm afleiden</text>' % C_INK,
         '<text x="32" y="102" font-size="var(--svg-fs-3)" fill="%s">%s. '
         'Controleer de vier gevelnamen, oppervlakken en gevelhoogte.</text>' % (C_SUB, _esc(reden))]
    if not delen:
        p.append('<text x="32" y="142" font-size="var(--svg-fs-4)" fill="%s">Nog geen gevels in de opname.</text>' % C_SUB)
    for index, deel in enumerate(delen):
        y = 142 + index * 28
        p.append('<g %s><text x="32" y="%d" font-size="var(--svg-fs-3)" fill="%s">%s · %.1f m² · %s</text></g>'
                 % (_attrs(deel), y, C_SUB, _esc(deel.id), deel.oppervlakte_m2 or 0,
                    _esc(deel.orientatie or "oriëntatie onbekend")))
    p.append('</svg>')
    return "".join(p)


def _face(points, schildeel=None, kind="vlak", fill=C_HOUSE, stroke=C_HOUSE_LINE,
          geometrie="exact"):
    return {"points": points, "deel": schildeel, "kind": kind, "fill": fill,
            "stroke": stroke, "geometrie": geometrie}


# Vaste 'zon' linksvoor-boven, in dezelfde (x,y,z)-ruimte als alle vlakpunten hier (y = omhoog).
# Consistent voor élk vlak (muur/dak/dakkapel/contour) -> geeft de isometrie diepte zonder ergens
# een hex-kleur te introduceren: puur een CSS brightness-filter bovenop de bestaande kleurtoken,
# dus blijft vanzelf correct in zowel het lichte als het donkere thema.
_ZON = (-0.25, 0.85, -0.45)


def _shade(points):
    """Helderheidsfactor (CSS brightness()) uit de vlaknormaal t.o.v. _ZON. Vlakken zijn hier
    steeds als 'onder-links, onder-rechts, boven-rechts, boven-links' opgebouwd (dezelfde
    winding als de rechthoek-gevels); cross(edge2, edge1) geeft daarmee de naar-buiten-wijzende
    normaal. Te weinig punten of een ontaarde (bijna-nul) normaal -> neutraal (1.0)."""
    if len(points) < 3:
        return 1.0
    (x0, y0, z0), (x1, y1, z1), (x2, y2, z2) = points[0], points[1], points[2]
    ax, ay, az = x1 - x0, y1 - y0, z1 - z0
    bx, by, bz = x2 - x0, y2 - y0, z2 - z0
    nx, ny, nz = by * az - bz * ay, bz * ax - bx * az, bx * ay - by * ax
    lengte = math.sqrt(nx * nx + ny * ny + nz * nz)
    if lengte < 1e-9:
        return 1.0
    dot = (nx * _ZON[0] + ny * _ZON[1] + nz * _ZON[2]) / lengte
    return max(0.6, min(1.15, 0.90 + 0.20 * dot))


def _orientatie_zijden(gevelgroepen):
    zijden = {}
    for naam, delen in gevelgroepen.items():
        for deel in delen:
            orientatie = (deel.orientatie or "").strip().upper()
            if orientatie:
                zijden[orientatie] = naam
    return zijden


def _dakvlakpunten(zijde, lengte, run, goothoogte, nokhoogte, breedte_huis, diepte_huis):
    """Vier punten met vaste volgorde: goot links/rechts, nok rechts/links."""
    if zijde in ("voor", "achter"):
        x0 = (breedte_huis - lengte) / 2
        z_goot = 0 if zijde == "voor" else diepte_huis
        z_nok = run if zijde == "voor" else diepte_huis - run
        return [(x0, goothoogte, z_goot), (x0 + lengte, goothoogte, z_goot),
                (x0 + lengte, nokhoogte, z_nok), (x0, nokhoogte, z_nok)]
    z0 = (diepte_huis - lengte) / 2
    x_goot = 0 if zijde == "links" else breedte_huis
    x_nok = run if zijde == "links" else breedte_huis - run
    return [(x_goot, goothoogte, z0), (x_goot, goothoogte, z0 + lengte),
            (x_nok, nokhoogte, z0 + lengte), (x_nok, nokhoogte, z0)]


def _roof_faces(dos, footprint, gevelgroepen):
    breedte_huis, diepte_huis, gevelhoogte = footprint
    faces, dakinfo, fouten = [], {}, []
    orientatie_zijden = _orientatie_zijden(gevelgroepen)
    daken = _dakvlakken(dos)
    groepen = {}
    for dak in daken:
        groepen.setdefault(dak.geometrie_groep or "legacy:%s" % dak.id, []).append(dak)
    for groepsnaam, groep in groepen.items():
        hellend = [d for d in groep if (d.hellingshoek or 0) > 0]
        exact_hellend = [d for d in hellend if d.breedte_m and d.diepte_m
                          and d.breedte_m > 0 and d.diepte_m > 0]
        groep_fout = ""
        exacte_info = []
        for dak in exact_hellend:
            zijde = orientatie_zijden.get((dak.orientatie or "").strip().upper())
            if not zijde:
                groep_fout = "dakvlak %s heeft geen gevelzijde voor oriëntatie %s" % (dak.id, dak.orientatie or "?")
                break
            zijde_lengte = breedte_huis if zijde in ("voor", "achter") else diepte_huis
            zijde_run = diepte_huis if zijde in ("voor", "achter") else breedte_huis
            if dak.breedte_m > zijde_lengte + .01 or dak.diepte_m > zijde_run + .01:
                groep_fout = "dakvlak %s past niet op de afgeleide footprint" % dak.id
                break
            berekende_nok = gevelhoogte + dak.diepte_m * math.tan(math.radians(dak.hellingshoek))
            gebouwhoogte = dos.opname.gebouwhoogte_m
            if (gebouwhoogte and math.isfinite(gebouwhoogte)
                    and abs(gebouwhoogte - berekende_nok) > .10):
                groep_fout = ("dakvlak %s: gebouwhoogte en helling/run verschillen meer dan 0,10 m"
                              % dak.id)
                break
            exacte_info.append((dak, zijde, berekende_nok))
        if not groep_fout and len(exacte_info) == 2:
            (dak_a, zijde_a, nok_a), (dak_b, zijde_b, nok_b) = exacte_info
            tegenover = {"voor": "achter", "achter": "voor", "links": "rechts", "rechts": "links"}
            overspanning = diepte_huis if zijde_a in ("voor", "achter") else breedte_huis
            if (zijde_b != tegenover[zijde_a]
                    or abs(dak_a.diepte_m + dak_b.diepte_m - overspanning) > .01
                    or abs(dak_a.breedte_m - dak_b.breedte_m) > .01
                    or abs(nok_a - nok_b) > .10):
                groep_fout = "dakgroep %s deelt geen geometrisch consistente nok" % groepsnaam
        if groep_fout:
            fouten.append(groep_fout)

        for dak in groep:
            exact = bool(dak.breedte_m and dak.diepte_m and dak.breedte_m > 0 and dak.diepte_m > 0)
            helling = math.radians(dak.hellingshoek or 0)
            lengte = dak.breedte_m if exact else breedte_huis
            if exact:
                run = dak.diepte_m
            elif helling and lengte > 0:
                schuine_diepte = (dak.oppervlakte_m2 or 0) / lengte
                run = schuine_diepte * math.cos(helling)
            else:
                run = diepte_huis
            lengte = max(.1, lengte)
            run = max(.1, run)
            if not hellend or not helling:
                if exact and (lengte > breedte_huis + .01 or run > diepte_huis + .01):
                    fouten.append("plat dakvlak %s past niet op de afgeleide footprint" % dak.id)
                    continue
                x0 = (breedte_huis - lengte) / 2
                z0 = (diepte_huis - run) / 2
                points = [(x0, gevelhoogte, z0), (x0 + lengte, gevelhoogte, z0),
                          (x0 + lengte, gevelhoogte, z0 + run), (x0, gevelhoogte, z0 + run)]
            else:
                if exact and groep_fout:
                    continue
                zijde = orientatie_zijden.get((dak.orientatie or "").strip().upper())
                if not zijde:
                    if exact:
                        continue
                    zijde = "voor"
                berekende_nok = gevelhoogte + run * math.tan(helling)
                gebouwhoogte = dos.opname.gebouwhoogte_m
                nokhoogte = (gebouwhoogte if exact and gebouwhoogte and math.isfinite(gebouwhoogte)
                             else berekende_nok)
                points = _dakvlakpunten(zijde, lengte, run, gevelhoogte, nokhoogte,
                                        breedte_huis, diepte_huis)
            geometrie = "exact" if exact else "benaderd"
            faces.append(_face(points, dak, "dakvlak", C_DAK, C_DAK_LINE, geometrie))
            dakinfo[dak.id] = {"points": points, "run": run, "lengte": lengte,
                               "helling": helling, "exact": exact}
    return faces, dakinfo, fouten


def _dakkapel_faces(dos, dakinfo):
    faces = []
    groepen = {}
    for deel in dos.schil:
        if _is_dakkapel(deel) and deel.moedervlak_id:
            groepen.setdefault(deel.geometrie_groep or deel.moedervlak_id, []).append(deel)
    for delen in groepen.values():
        rollen = {}
        for deel in delen:
            sleutel = (deel.id or "").lower()
            if "voorvlak" in sleutel:
                rollen["voor"] = deel
            elif "wang-links" in sleutel:
                rollen["links"] = deel
            elif "wang-rechts" in sleutel:
                rollen["rechts"] = deel
            elif "dakje" in sleutel or (deel.type or "").lower() == "dak":
                rollen["dak"] = deel
        basis = rollen.get("voor")
        if not basis or not all(rol in rollen for rol in ("voor", "links", "rechts", "dak")):
            continue
        moeder = dakinfo.get(basis.moedervlak_id)
        if not moeder or not (basis.breedte_m and basis.diepte_m and basis.hoogte_m):
            continue
        b, d, h = basis.breedte_m, basis.diepte_m, basis.hoogte_m
        if min(b, d, h) <= 0 or b > moeder["lengte"] or d > moeder["run"]:
            continue
        p0, p1, p2, p3 = moeder["points"]
        fractie_b = b / moeder["lengte"]
        fractie_d = d / moeder["run"]
        u0, u1 = (1 - fractie_b) / 2, (1 + fractie_b) / 2
        v0, v1 = (1 - fractie_d) / 2, (1 + fractie_d) / 2

        def interp(u, v):
            links = tuple(p0[i] + (p3[i] - p0[i]) * v for i in range(3))
            rechts = tuple(p1[i] + (p2[i] - p1[i]) * v for i in range(3))
            return tuple(links[i] + (rechts[i] - links[i]) * u for i in range(3))

        lf, rf, lb, rb = interp(u0, v0), interp(u1, v0), interp(u0, v1), interp(u1, v1)
        top = lf[1] + h
        lft, rft = (lf[0], top, lf[2]), (rf[0], top, rf[2])
        lbt, rbt = (lb[0], top, lb[2]), (rb[0], top, rb[2])
        punten = {
            "voor": [lf, rf, rft, lft],
            "links": [lb, lf, lft, lbt],
            "rechts": [rf, rb, rbt, rft],
            "dak": [lft, rft, rbt, lbt],
        }
        for kind, pts in punten.items():
            deel = rollen[kind]
            faces.append(_face(pts, deel, "dakkapel-%s" % kind,
                               C_DAKKAPEL, C_DAKKAPEL_LINE))
    return faces


def gebouw_svg(dos, titel="Gebouwoverzicht"):
    poly = _polygon_footprint(dos)
    if poly:
        # Echte, gemeten plattegrondcontour (assemble.py) -> geen rechthoek-aanname nodig voor de
        # gevels, dus de volledige _footprint()-consistentiecheck (25%-tolerantie tussen
        # tegenoverliggende gevels) is hier niet van toepassing; alleen de gevelgroepering (voor
        # de dakzijde-orientatie in _roof_faces) is nog nodig, zonder de rest van _footprint uit
        # te voeren.
        gevelgroepen = _hoofgevels(dos)
    else:
        footprint, gevelgroepen, reden = _footprint(dos)
        if not footprint:
            return _fallback(dos, titel, reden)

    if poly:
        contour, gevelhoogte = poly
        bx = [p[0] for p in contour]
        bz = [p[1] for p in contour]
        breedte, diepte = max(bx) - min(bx), max(bz) - min(bz)
        faces = _muurvlakken(contour, gevelhoogte)
        faces.append(_face([(x, gevelhoogte, z) for x, z in contour], None, "bovenzijde-contour",
                           C_HOUSE, C_HOUSE_LINE))
    else:
        breedte, diepte, gevelhoogte = footprint
        gevel_faces = {
            "voor": [(0, 0, 0), (breedte, 0, 0), (breedte, gevelhoogte, 0), (0, gevelhoogte, 0)],
            "rechts": [(breedte, 0, 0), (breedte, 0, diepte), (breedte, gevelhoogte, diepte), (breedte, gevelhoogte, 0)],
            "achter": [(breedte, 0, diepte), (0, 0, diepte), (0, gevelhoogte, diepte), (breedte, gevelhoogte, diepte)],
            "links": [(0, 0, diepte), (0, 0, 0), (0, gevelhoogte, 0), (0, gevelhoogte, diepte)],
        }
        faces = []
        for naam, punten in gevel_faces.items():
            delen = gevelgroepen[naam]
            bekend = all(s.rc_huidig or s.u_huidig for s in delen)
            faces.append(_face(punten, delen[0], "gevel-%s" % naam,
                               C_HOUSE, C_KNOWN if bekend else C_UNKNOWN))
            faces[-1]["delen"] = delen
    dakfaces, dakinfo, dakfouten = _roof_faces(dos, (breedte, diepte, gevelhoogte), gevelgroepen)
    faces.extend(dakfaces)
    faces.extend(_dakkapel_faces(dos, dakinfo))

    punten2d = [_project(point) for face in faces for point in face["points"]]
    min_x, max_x = min(x for x, _ in punten2d), max(x for x, _ in punten2d)
    min_y, max_y = min(y for _, y in punten2d), max(y for _, y in punten2d)
    schaal = min(700 / max(1, max_x - min_x), 330 / max(1, max_y - min_y))

    def scherm(point):
        x, y = _project(point)
        return "%.1f,%.1f" % (450 + (x - (min_x + max_x) / 2) * schaal,
                              255 + (y - (min_y + max_y) / 2) * schaal)

    grond2d = [_project(punt) for face in faces for punt in face["points"] if punt[1] == 0]
    p = ['<svg viewBox="0 0 900 540" xmlns="http://www.w3.org/2000/svg" role="img" '
         'aria-labelledby="gebouw-titel gebouw-uitleg">',
         '<title id="gebouw-titel">%s</title>' % _esc(titel),
         '<desc id="gebouw-uitleg">Isometrische weergave uit de opgeslagen gevel- en dakmaten.</desc>',
         '<defs><filter id="gebouw-schaduw" x="-50%" y="-50%" width="200%" height="200%">'
         '<feGaussianBlur stdDeviation="7"/></filter></defs>',
         '<rect width="900" height="540" fill="%s"/>' % C_CARD]
    if grond2d:
        gx = [450 + (x - (min_x + max_x) / 2) * schaal for x, _ in grond2d]
        gy = [255 + (y - (min_y + max_y) / 2) * schaal for _, y in grond2d]
        # Bewust 'black', niet een thema-token: een schaduw hoort in zowel licht als donker thema
        # donker te blijven (zelfde conventie als --shadow/--shadow-sm in app.css, die ook in
        # beide thema's rgba(0,0,0,...) blijven) — C_INK zou in donker thema bijna wit worden en
        # een lichtgevende halo tekenen i.p.v. een schaduw.
        p.append('<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" fill="black" fill-opacity="0.16" '
                 'filter="url(#gebouw-schaduw)"/>'
                 % ((min(gx) + max(gx)) / 2, max(gy) + 6,
                    max(20.0, (max(gx) - min(gx)) / 2 + 10), 10))
    p += [
         '<text x="32" y="42" font-size="var(--svg-fs-8)" font-weight="700" fill="%s">%s</text>'
         % (C_INK, _esc(titel)),
         '<text x="32" y="68" font-size="var(--svg-fs-3)" fill="%s" data-footprint-bron="%s">'
         'Footprint %.2f × %.2f m · gevel %.2f m%s</text>'
         % (C_SUB, "contour" if poly else "afgeleid", breedte, diepte, gevelhoogte,
            " · échte plattegrondcontour" if poly else "")]
    for face in faces:
        deel = face.get("deel")
        extra = ' data-geometrie="%s" data-punten-3d="%s"' % (
            face["geometrie"],
            _esc(" ".join("%.3f,%.3f,%.3f" % punt for punt in face["points"])))
        if deel:
            attrs = _attrs(deel, extra)
        elif face["kind"] in ("gevel-contour", "bovenzijde-contour"):
            # Geen 1-op-1 SchilDeel voor een contourrand (zie _muurvlakken) -> geen
            # data-element-id, wel expliciet gemarkeerd zodat "geen id" niet als omissie oogt.
            attrs = 'data-contour="true"%s' % extra
        else:
            attrs = ""
        if face.get("delen"):
            ids = ",".join(s.id or "" for s in face["delen"])
            attrs += ' data-element-ids="%s"' % _esc(ids)
        # Vlakke daktoppen (bovenzijde-contour) hebben geen betrouwbare winding (volgt de
        # MagicPlan-contour zoals aangeleverd) -> altijd de helderste 'plat boven'-tint, i.p.v.
        # een mogelijk verkeerd-om berekende normaal.
        shade = 1.07 if face["kind"] == "bovenzijde-contour" else _shade(face["points"])
        p.append('<polygon points="%s" fill="%s" stroke="%s" stroke-width="2" '
                 'stroke-linejoin="round" filter="brightness(%.3f)" data-face="%s" %s/>'
                 % (" ".join(scherm(point) for point in face["points"]), face["fill"],
                    face["stroke"], shade, face["kind"], attrs))
        if deel:
            cx = sum(point[0] for point in face["points"]) / len(face["points"])
            cy = sum(point[1] for point in face["points"]) / len(face["points"])
            cz = sum(point[2] for point in face["points"]) / len(face["points"])
            label_x, label_y = scherm((cx, cy, cz)).split(",")
            p.append('<text x="%s" y="%s" text-anchor="middle" font-size="var(--svg-fs-2)" '
                     'fill="%s">%s · %.1f m² · %s</text>'
                     % (label_x, label_y, C_INK, _esc(deel.id), deel.oppervlakte_m2 or 0,
                        _esc(deel.orientatie or "horizontaal")))
    # Ook niet-zichtbare samengevoegde geveldelen en de tweede dakkapelwang
    # blijven machineleesbaar/herleidbaar zonder extra fictieve 3D-vlakken.
    getekende_ids = {face["deel"].id for face in faces if face.get("deel")}
    relevante_delen = [s for s in dos.schil if (s.type or "").lower() in ("gevel", "dak")]
    p.append('<g data-render-metadata="elementen">')
    for deel in relevante_delen:
        if deel.id not in getekende_ids:
            p.append('<metadata %s>%s · %.2f m² · %s</metadata>'
                     % (_attrs(deel), _esc(deel.id), deel.oppervlakte_m2 or 0,
                        _esc(deel.orientatie)))
    p.append('</g>')
    benaderd = [face["deel"] for face in dakfaces if face["geometrie"] == "benaderd"]
    if benaderd:
        p.append('<text x="32" y="508" font-size="var(--svg-fs-3)" fill="%s">'
                 'Benaderd dakvlak: %s (legacy zonder renderingmaten)</text>'
                 % (C_SUB, _esc(", ".join(d.id or "" for d in benaderd))))
    if dakfouten:
        p.append('<text x="32" y="486" font-size="var(--svg-fs-3)" fill="var(--err-fg)">'
                 'Dak niet getekend: %s</text>' % _esc("; ".join(dakfouten)))
    herleidbaarheid = (
        'Gevelvlakken volgen de gemeten plattegrondcontour (data-contour); de onderliggende '
        'gevel-id\'s blijven herleidbaar via de metadatalaag hierboven, niet per muurvlak.'
        if poly else
        'Vlakken blijven via id, m² en oriëntatie herleidbaar in de tekening.')
    p.append('<text x="32" y="532" font-size="var(--svg-fs-2)" fill="%s">%s</text>'
             % (C_SUB, herleidbaarheid))
    p.append('</svg>')
    return "".join(p)
