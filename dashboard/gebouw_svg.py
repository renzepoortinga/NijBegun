"""
Gebouwoverzicht (SVG) — read-only schematische tekening van wat al in het dossier staat.

Toont de woning als bovenaanzicht (compass-stijl, zelfde visuele taal als
docs/gevel-kompas.svg) met de gevels/panelen/kozijnen op hun bestaande, al opgeslagen
`orientatie` (komt uit de MagicPlan-import — er wordt hier niets herafgeleid), plus een
dakstrook met de dakvlakken (incl. dakkapel-onderdelen) relatief geschaald op m².

Puur een presentatielaag: geen nieuwe dossiervelden, geen invoer. MagicPlan blijft de
bron voor gevels; dit is alleen een visuele controle van wat er al staat — precies het
gat dat Inbrix' wireframes dichten en dat de tool tot nu toe niet had.

    from dashboard.gebouw_svg import gebouw_svg
    svg = gebouw_svg(dossier)
"""

# kleuren = de bestaande design-tokens uit dashboard/static/app.css (var(--...)), NIET losse hex-
# waarden: de SVG staat altijd inline in de pagina, dus CSS-custom-properties resolven gewoon in
# fill/stroke — zo volgt de tekening automatisch light/dark (prefers-color-scheme), net als de rest
# van de webapp. Loop je dit ooit los van de pagina (bv. als los .svg-bestand) dan vallen deze terug
# op de browser-default zwart — dat gebeurt hier niet, de SVG wordt altijd via {{gebouw_svg|safe}}
# inline gerenderd.
C_INK = "var(--ink)"
C_SUB = "var(--sub)"
C_CARD = "var(--card)"
C_HOUSE = "var(--info-bg)"
C_HOUSE_LINE = "var(--blue)"
C_DAK = "var(--tint)"
C_DAK_LINE = "var(--sub)"
C_DAKKAPEL = "var(--warn-bg)"
C_DAKKAPEL_LINE = "var(--orange)"
C_KNOWN = "var(--ok-fg)"     # Rc/U bekend
C_UNKNOWN = "var(--sub)"     # nog niet ingevuld

# posities rond de rechthoek (bovenaanzicht), 8-punts kompas
_COMPAS = ["N", "NO", "O", "ZO", "Z", "ZW", "W", "NW"]


def _esc(s):
    return (str(s or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _gevel_groepen(dos):
    """Gevels/panelen/kozijnen gegroepeerd op hun al-opgeslagen orientatie (of '' = onbekend)."""
    groepen = {}
    for s in dos.schil:
        if (s.type or "").lower() not in ("gevel", "paneel", "kozijn"):
            continue
        o = (s.orientatie or "").strip().upper() or "?"
        groepen.setdefault(o, []).append(s)
    return groepen


def _dak_vlakken(dos):
    return [s for s in dos.schil if (s.type or "").lower() == "dak"]


def _is_dakkapel(s):
    return "dakkapel" in (s.subtype or "").lower() or "dakkapel" in (s.id or "").lower()


def _kaartje(x, y, w, h, s):
    """Klein labelkaartje voor één schildeel: id + m² + (Rc/U indien bekend)."""
    bekend = bool(s.rc_huidig or s.u_huidig)
    kleur = C_KNOWN if bekend else C_UNKNOWN
    P = ['<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="8" fill="%s" '
         'stroke="%s" stroke-width="1.5"/>' % (x, y, w, h, C_CARD, C_HOUSE_LINE)]
    P.append('<text x="%.1f" y="%.1f" font-size="var(--svg-fs-3)" font-weight="650" fill="%s">%s</text>'
             % (x + 8, y + 18, C_INK, _esc((s.id or "")[:20])))
    P.append('<text x="%.1f" y="%.1f" font-size="var(--svg-fs-2)" fill="%s">%.1f m&#178;</text>'
             % (x + 8, y + 34, C_SUB, s.oppervlakte_m2 or 0))
    if bekend:
        waarde = "Rc %.2f" % s.rc_huidig if s.rc_huidig else "U %.2f" % s.u_huidig
        P.append('<circle cx="%.1f" cy="%.1f" r="4" fill="%s"/>' % (x + w - 14, y + 14, kleur))
        P.append('<text x="%.1f" y="%.1f" font-size="var(--svg-fs-1)" fill="%s" text-anchor="end">%s</text>'
                 % (x + w - 8, y + 34, C_SUB, waarde))
    return "".join(P)


def gebouw_svg(dos, titel="Gebouwoverzicht"):
    groepen = _gevel_groepen(dos)
    daken = _dak_vlakken(dos)

    width = 900
    house_cx, house_cy, house_w, house_h = 450, 230, 260, 200
    hx0, hy0 = house_cx - house_w / 2, house_cy - house_h / 2

    P = []
    # hoogte: kop + huis + dakstrook (dynamisch op basis van #dakvlakken)
    dak_rows = max(1, (len(daken) + 3) // 4)
    dak_y0 = hy0 + house_h + 90
    height = dak_y0 + dak_rows * 110 + 60
    P.append('<svg viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg" '
             'font-family="-apple-system, BlinkMacSystemFont, system-ui, Segoe UI, sans-serif">'
             % (width, height))
    P.append('<rect x="0" y="0" width="%d" height="%d" fill="%s"/>' % (width, height, C_CARD))
    P.append('<text x="32" y="40" font-size="var(--svg-fs-8)" font-weight="700" fill="%s">%s</text>' % (C_INK, _esc(titel)))
    P.append('<text x="32" y="62" font-size="var(--svg-fs-4)" fill="%s">Wat er nu in het dossier staat — bovenaanzicht + '
             'dakvlakken, gebaseerd op de geladen opname. Rekenwaarden komen uit MagicPlan/handmatige invoer, '
             'niet metrisch schaalvast.</text>' % C_SUB)

    # bovenaanzicht: het huis + gevelkaartjes op hun kompaspositie
    P.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="10" fill="%s" stroke="%s" stroke-width="2"/>'
             % (hx0, hy0, house_w, house_h, C_HOUSE, C_HOUSE_LINE))
    P.append('<text x="%.1f" y="%.1f" font-size="var(--svg-fs-5)" font-weight="650" fill="%s" text-anchor="middle">WONING</text>'
             % (house_cx, house_cy, C_INK))

    # kompasposities rond de rechthoek (N boven, O rechts, Z onder, W links, tussenrichtingen op hoeken)
    pos = {
        "N": (house_cx, hy0 - 60), "Z": (house_cx, hy0 + house_h + 60),
        "O": (hx0 + house_w + 90, house_cy), "W": (hx0 - 90, house_cy),
        "NO": (hx0 + house_w + 70, hy0 - 20), "ZO": (hx0 + house_w + 70, hy0 + house_h + 20),
        "NW": (hx0 - 70, hy0 - 20), "ZW": (hx0 - 70, hy0 + house_h + 20),
        "?": (house_cx, hy0 + house_h + 60),
    }
    kw, kh, gap = 128, 42, 6
    for o in list(_COMPAS) + ["?"]:
        leden = groepen.get(o, [])
        if not leden:
            continue
        cx, cy = pos.get(o, (house_cx, hy0 + house_h + 60))
        label = o if o != "?" else "onbekend"
        P.append('<text x="%.1f" y="%.1f" font-size="var(--svg-fs-2)" font-weight="650" fill="%s" text-anchor="middle">%s</text>'
                 % (cx, cy - kh / 2 - 6, C_SUB, label))
        for j, s in enumerate(leden[:4]):
            x = cx - kw / 2
            y = cy - kh / 2 + j * (kh + gap)
            P.append(_kaartje(x, y, kw, kh, s))
        if len(leden) > 4:
            P.append('<text x="%.1f" y="%.1f" font-size="var(--svg-fs-1)" fill="%s" text-anchor="middle">+%d meer</text>'
                     % (cx, cy - kh / 2 + 4 * (kh + gap) + 12, C_SUB, len(leden) - 4))
    if not any(groepen.values()):
        P.append('<text x="%.1f" y="%.1f" font-size="var(--svg-fs-4)" fill="%s" text-anchor="middle">Nog geen gevels in de '
                 'opname — deze verschijnen na een MagicPlan-import.</text>' % (house_cx, hy0 + house_h + 40, C_SUB))

    # dakstrook: elk dakvlak als kaartje, relatief geschaald op m² (dikte van de rand), 4 per rij
    P.append('<text x="32" y="%.1f" font-size="var(--svg-fs-6)" font-weight="650" fill="%s">Dak</text>' % (dak_y0 - 14, C_INK))
    if daken:
        max_m2 = max((s.oppervlakte_m2 or 0) for s in daken) or 1
        dw, dh, dgx, dgy = 190, 92, 18, 18
        for i, s in enumerate(daken):
            col, row = i % 4, i // 4
            x = 32 + col * (dw + dgx)
            y = dak_y0 + row * (dh + dgy)
            kapel = _is_dakkapel(s)
            fill, line = (C_DAKKAPEL, C_DAKKAPEL_LINE) if kapel else (C_DAK, C_DAK_LINE)
            rel = max(0.25, min(1.0, (s.oppervlakte_m2 or 0) / max_m2))
            P.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="10" fill="%s" stroke="%s" '
                     'stroke-width="%.1f"/>' % (x, y, dw, dh, fill, line, 1.5 + 2.5 * rel))
            P.append('<text x="%.1f" y="%.1f" font-size="var(--svg-fs-3)" font-weight="650" fill="%s">%s</text>'
                     % (x + 10, y + 22, C_INK, _esc((s.id or "")[:22])))
            P.append('<text x="%.1f" y="%.1f" font-size="var(--svg-fs-2)" fill="%s">%s%s</text>'
                     % (x + 10, y + 40, C_SUB, _esc((s.subtype or "")[:26]) or _esc(s.orientatie),
                        " · dakkapel" if kapel else ""))
            P.append('<text x="%.1f" y="%.1f" font-size="var(--svg-fs-4)" font-weight="700" fill="%s">%.1f m&#178;</text>'
                     % (x + 10, y + 62, C_INK, s.oppervlakte_m2 or 0))
            if s.hellingshoek:
                P.append('<text x="%.1f" y="%.1f" font-size="var(--svg-fs-2)" fill="%s">helling %.0f&#176;</text>'
                         % (x + 10, y + 80, C_SUB, s.hellingshoek))
    else:
        P.append('<text x="32" y="%.1f" font-size="var(--svg-fs-4)" fill="%s">Nog geen dak toegevoegd — zie "Dak toevoegen" '
                 'hieronder.</text>' % (dak_y0 + 20, C_SUB))

    P.append('</svg>')
    return "".join(P)
