"""Read-only isometrisch gebouwoverzicht uit de opgeslagen dossiergeometrie.

Dit is uitsluitend een presentatielaag. Een 3D-volume wordt alleen getekend als
alle vier gevelrichtingen en een gevelhoogte een rechthoekige footprint dragen.
Tegenoverliggende gevelbreedtes mogen maximaal 25% verschillen: dat is dezelfde
grens waarmee de MagicPlan-import een mogelijke dubbeltelling signaleert. De
renderer corrigeert geen invoer en rekent geen NTA 8800-resultaten.
"""

from __future__ import annotations

import html
import math

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


def _footprint(dos):
    """Geef (breedte, diepte, gevelhoogte, groepen, reden) zonder maten te gokken."""
    groepen = _hoofgevels(dos)
    hoogte = dos.opname.gevelhoogte_m
    if not hoogte or not math.isfinite(hoogte) or hoogte <= 0:
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
          approximate=False):
    return {"points": points, "deel": schildeel, "kind": kind, "fill": fill,
            "stroke": stroke, "approximate": approximate}


def _roof_faces(dos, footprint):
    breedte_huis, diepte_huis, gevelhoogte = footprint
    faces, dakinfo = [], {}
    daken = _dakvlakken(dos)
    groepen = {}
    for dak in daken:
        groepen.setdefault(dak.geometrie_groep or "legacy:%s" % dak.id, []).append(dak)
    for groep in groepen.values():
        hellend = [d for d in groep if (d.hellingshoek or 0) > 0]
        for index, dak in enumerate(groep):
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
            lengte = min(max(.1, lengte), breedte_huis)
            run = min(max(.1, run), diepte_huis)
            x0 = (breedte_huis - lengte) / 2
            if not hellend or not helling:
                points = [(x0, gevelhoogte, 0), (x0 + lengte, gevelhoogte, 0),
                          (x0 + lengte, gevelhoogte, run), (x0, gevelhoogte, run)]
            else:
                # Twee vlakken uit dezelfde geometriegroep delen een nok; de
                # runs bepalen de verschoven nok bij een asymmetrisch dak.
                aan_voorzijde = index == 0
                z_goot = 0 if aan_voorzijde else diepte_huis
                z_nok = run if aan_voorzijde else diepte_huis - run
                berekende_nok = gevelhoogte + run * math.tan(helling)
                gebouwhoogte = dos.opname.gebouwhoogte_m
                nokhoogte = (gebouwhoogte if gebouwhoogte and math.isfinite(gebouwhoogte)
                             and gebouwhoogte >= gevelhoogte else berekende_nok)
                points = [(x0, gevelhoogte, z_goot), (x0 + lengte, gevelhoogte, z_goot),
                          (x0 + lengte, nokhoogte, z_nok), (x0, nokhoogte, z_nok)]
            faces.append(_face(points, dak, "dakvlak", C_DAK, C_DAK_LINE, not exact))
            dakinfo[dak.id] = {"points": points, "run": run, "lengte": lengte,
                               "helling": helling, "exact": exact}
    return faces, dakinfo


def _dakkapel_faces(dos, dakinfo):
    faces = []
    groepen = {}
    for deel in dos.schil:
        if _is_dakkapel(deel) and deel.moedervlak_id:
            groepen.setdefault(deel.geometrie_groep or deel.moedervlak_id, []).append(deel)
    for delen in groepen.values():
        basis = delen[0]
        moeder = dakinfo.get(basis.moedervlak_id)
        if not moeder or not (basis.breedte_m and basis.diepte_m and basis.hoogte_m):
            continue
        b, d, h = basis.breedte_m, basis.diepte_m, basis.hoogte_m
        if min(b, d, h) <= 0 or b > moeder["lengte"] or d > moeder["run"]:
            continue
        dakpunten = moeder["points"]
        x0 = (dakpunten[0][0] + dakpunten[1][0] - b) / 2
        z0 = dakpunten[0][2] + (dakpunten[2][2] - dakpunten[0][2]) * .3
        richting = 1 if dakpunten[2][2] >= dakpunten[0][2] else -1
        z1 = z0 + richting * d
        helling = moeder["helling"]
        y0 = dakpunten[0][1] + abs(z0 - dakpunten[0][2]) * math.tan(helling)
        y1 = dakpunten[0][1] + abs(z1 - dakpunten[0][2]) * math.tan(helling)
        top = y0 + h
        punten = {
            "voor": [(x0, y0, z0), (x0 + b, y0, z0), (x0 + b, top, z0), (x0, top, z0)],
            "zij": [(x0 + b, y0, z0), (x0 + b, y1, z1), (x0 + b, top, z1), (x0 + b, top, z0)],
            "dak": [(x0, top, z0), (x0 + b, top, z0), (x0 + b, top, z1), (x0, top, z1)],
        }
        for kind, pts in punten.items():
            deel = next((x for x in delen if kind in (x.id or "").lower()), basis)
            faces.append(_face(pts, deel, "dakkapel-%s" % kind,
                               C_DAKKAPEL, C_DAKKAPEL_LINE))
    return faces


def gebouw_svg(dos, titel="Gebouwoverzicht"):
    footprint, gevelgroepen, reden = _footprint(dos)
    if not footprint:
        return _fallback(dos, titel, reden)
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
    dakfaces, dakinfo = _roof_faces(dos, footprint)
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

    p = ['<svg viewBox="0 0 900 540" xmlns="http://www.w3.org/2000/svg" role="img" '
         'aria-labelledby="gebouw-titel gebouw-uitleg">',
         '<title id="gebouw-titel">%s</title>' % _esc(titel),
         '<desc id="gebouw-uitleg">Isometrische weergave uit de opgeslagen gevel- en dakmaten.</desc>',
         '<rect width="900" height="540" fill="%s"/>' % C_CARD,
         '<text x="32" y="42" font-size="var(--svg-fs-8)" font-weight="700" fill="%s">%s</text>'
         % (C_INK, _esc(titel)),
         '<text x="32" y="68" font-size="var(--svg-fs-3)" fill="%s">Footprint %.2f × %.2f m · gevel %.2f m</text>'
         % (C_SUB, breedte, diepte, gevelhoogte)]
    for face in faces:
        deel = face.get("deel")
        extra = ' data-geometrie="%s"' % ("benaderd" if face["approximate"] else "exact")
        attrs = _attrs(deel, extra) if deel else ""
        if face.get("delen"):
            ids = ",".join(s.id or "" for s in face["delen"])
            attrs += ' data-element-ids="%s"' % _esc(ids)
        p.append('<polygon points="%s" fill="%s" stroke="%s" stroke-width="2" '
                 'stroke-linejoin="round" data-face="%s" %s/>'
                 % (" ".join(scherm(point) for point in face["points"]), face["fill"],
                    face["stroke"], face["kind"], attrs))
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
    benaderd = [face["deel"] for face in dakfaces if face["approximate"]]
    if benaderd:
        p.append('<text x="32" y="508" font-size="var(--svg-fs-3)" fill="%s">'
                 'Benaderd dakvlak: %s (legacy zonder renderingmaten)</text>'
                 % (C_SUB, _esc(", ".join(d.id or "" for d in benaderd))))
    p.append('<text x="32" y="532" font-size="var(--svg-fs-2)" fill="%s">'
             'Vlakken blijven via id, m² en oriëntatie herleidbaar in de tekening.</text>' % C_SUB)
    p.append('</svg>')
    return "".join(p)
