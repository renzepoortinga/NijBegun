"""Isometrisch, read-only gebouwoverzicht van de opgeslagen opname."""

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


def _esc(value):
    return (str(value or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _project(point):
    x, y, z = point
    return ((x - z) * _COS30, (x + z) * .5 - y)


def _gevelnaam(s):
    naam = (s.gevel_naam or "").strip().lower().replace("gevel", "")
    return naam if naam in ("voor", "achter", "links", "rechts") else ""


def _footprint(dos):
    """Geef (breedte, diepte, gevelhoogte) of een verklaarde fallbackreden."""
    hoogte = getattr(dos.opname, "gevelhoogte_m", None)
    if not hoogte or hoogte <= 0:
        return None, "kon geen 3D-vorm afleiden: gevelhoogte ontbreekt"
    oppervlakken = {naam: 0.0 for naam in ("voor", "achter", "links", "rechts")}
    ids = {naam: [] for naam in oppervlakken}
    for s in dos.schil:
        if (s.type or "").lower() != "gevel" or "dakkapel" in (s.id or "").lower():
            continue
        naam = _gevelnaam(s)
        if naam:
            oppervlakken[naam] += max(0, s.oppervlakte_m2 or 0)
            ids[naam].append(s)
    if not all(oppervlakken.values()):
        return None, "kon geen 3D-vorm afleiden: voor-, achter-, linker- en rechtergevel zijn nodig"
    maten = {naam: oppervlakken[naam] / hoogte for naam in oppervlakken}
    # Tegenoverliggende zijden mogen door afronding verschillen, maar geen andere footprint beschrijven.
    for a, b in (("voor", "achter"), ("links", "rechts")):
        if abs(maten[a] - maten[b]) > max(.25, .1 * max(maten[a], maten[b])):
            return None, "kon geen 3D-vorm afleiden: tegenoverliggende gevelmaten zijn inconsistent"
    return ((maten["voor"] + maten["achter"]) / 2,
            (maten["links"] + maten["rechts"]) / 2, hoogte, ids), ""


def _face(points, fill, stroke, kind, label="", attrs=None):
    return {"points": points, "fill": fill, "stroke": stroke, "kind": kind,
            "label": label, "attrs": attrs or {}}


def _richting(orientatie):
    vectors = {"N": (0, -1), "NO": (1, -1), "O": (1, 0), "ZO": (1, 1),
               "Z": (0, 1), "ZW": (-1, 1), "W": (-1, 0), "NW": (-1, -1)}
    vx, vz = vectors.get((orientatie or "").strip().upper(), (0, 1))
    length = math.hypot(vx, vz)
    return vx / length, vz / length


def _dakvlak_geometry(s, width, depth, eave, paired=False):
    """Vier hoekpunten en basisdata voor één vlak, gedraaid naar zijn kompasrichting."""
    vx, vz = _richting(s.orientatie)
    tx, tz = -vz, vx
    run = s.diepte_m or min(width, depth) / 2
    span = s.breedte_m or math.sqrt(max(s.oppervlakte_m2 or 1, 1))
    angle = math.radians(s.hellingshoek or 0)
    rise = run * math.tan(angle)
    cx, cz = width / 2, depth / 2
    # Bij een dakpaar ligt de hoge rand op de gedeelde nok rond het midden;
    # bij één vlak loopt de hoge rand vanaf de buitenrand naar binnen.
    ridge = (cx, cz)
    eave_center = (cx + vx * run, cz + vz * run)
    half = span / 2
    e1 = (eave_center[0] - tx * half, eave, eave_center[1] - tz * half)
    e2 = (eave_center[0] + tx * half, eave, eave_center[1] + tz * half)
    r2 = (ridge[0] + tx * half, eave + rise, ridge[1] + tz * half)
    r1 = (ridge[0] - tx * half, eave + rise, ridge[1] - tz * half)
    return [e1, e2, r2, r1], {"v": (vx, vz), "t": (tx, tz), "run": run,
                               "span": span, "rise": rise, "eave_center": eave_center,
                               "ridge": ridge, "eave": eave, "paired": paired}


def _dak_faces(dos, width, depth, eave):
    daken = [s for s in dos.schil if (s.type or "").lower() == "dak"
             and "dakkapel" not in (s.id or "").lower()]
    faces, exact_ids, legacy_ids = [], set(), set()
    groups = {}
    for s in daken:
        groups.setdefault(s.geometrie_groep or s.id or "dak", []).append(s)
    for groep, delen in groups.items():
        schuin = [s for s in delen if (s.hellingshoek or 0) > 0]
        exact = bool(delen and all((s.breedte_m or 0) > 0 and (s.diepte_m or 0) > 0 for s in delen))
        (exact_ids if exact else legacy_ids).update((s.id or "") for s in delen)
        mode = "exact" if exact else "benaderd"
        for s in delen:
            if not exact:
                s_width = width
                s_run = (s.oppervlakte_m2 or width * depth) / max(s_width, .01)
                # Alleen lokale renderwaarden; het dossier blijft onaangeroerd.
                class _Legacy: pass
                render_s = _Legacy()
                render_s.id, render_s.orientatie = s.id, s.orientatie
                render_s.oppervlakte_m2, render_s.hellingshoek = s.oppervlakte_m2, s.hellingshoek
                render_s.breedte_m, render_s.diepte_m = s_width, s_run
            else:
                render_s = s
            points, _ = _dakvlak_geometry(render_s, width, depth, eave, len(schuin) >= 2)
            attrs = {"data-group": groep, "data-rendering": mode, "data-id": s.id or "",
                     "data-m2": "%.2f" % (s.oppervlakte_m2 or 0),
                     "data-orientation": s.orientatie or "Horizontaal",
                     "data-angle": "%.2f" % (s.hellingshoek or 0)}
            faces.append(_face(points, C_DAK, C_DAK_LINE, "dak", s.id, attrs))
    return faces, exact_ids, legacy_ids


def _dakkapel_faces(dos, width, depth, eave):
    groepen = {}
    for s in dos.schil:
        if "dakkapel" in (s.id or "").lower():
            groepen.setdefault(s.geometrie_groep or s.id, []).append(s)
    faces = []
    for groep, delen in groepen.items():
        maat = next((s for s in delen if s.breedte_m and s.diepte_m and s.hoogte_m), None)
        if not maat:
            continue
        w, d, h = min(maat.breedte_m, width * .8), min(maat.diepte_m, depth * .6), maat.hoogte_m
        parent = maat.moedervlak_id or ""
        moeder = next((s for s in dos.schil if s.id == parent), None)
        if not moeder:
            continue
        _, geo = _dakvlak_geometry(moeder, width, depth, eave, True)
        vx, vz = geo["v"]
        tx, tz = geo["t"]
        # 35% vanaf de goot richting nok; diepte loopt verder naar de nok.
        along_front = min(geo["run"] * .35, max(0, geo["run"] - d))
        front_c = (geo["eave_center"][0] - vx * along_front,
                   geo["eave_center"][1] - vz * along_front)
        back_c = (front_c[0] - vx * d, front_c[1] - vz * d)
        angle = math.radians(moeder.hellingshoek or 0)
        base_front = eave + along_front * math.tan(angle)
        base_back = base_front + d * math.tan(angle)
        top = base_front + h
        lf = (front_c[0] - tx * w / 2, base_front, front_c[1] - tz * w / 2)
        rf = (front_c[0] + tx * w / 2, base_front, front_c[1] + tz * w / 2)
        lb = (back_c[0] - tx * w / 2, base_back, back_c[1] - tz * w / 2)
        rb = (back_c[0] + tx * w / 2, base_back, back_c[1] + tz * w / 2)
        lft, rft = (lf[0], top, lf[2]), (rf[0], top, rf[2])
        lbt, rbt = (lb[0], top, lb[2]), (rb[0], top, rb[2])
        attrs = {"data-group": groep, "data-parent": parent, "data-rendering": "exact",
                 "data-id": maat.id or "", "data-m2": "%.2f" % (maat.oppervlakte_m2 or 0),
                 "data-orientation": maat.orientatie or moeder.orientatie or ""}
        faces.extend([
            _face([lf, rf, rft, lft], C_DAKKAPEL, C_DAKKAPEL_LINE, "dakkapel", maat.id, attrs),
            _face([lft, rft, rbt, lbt], C_DAKKAPEL, C_DAKKAPEL_LINE, "dakkapel-dak", maat.id, attrs),
        ])
    return faces


def _svg_start(width, height, titel):
    return ['<svg class="isometrie-canvas gebouw-isometrie" viewBox="0 0 %d %d" '
            'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="%s">' %
            (width, height, _esc(titel)),
            '<rect x="0" y="0" width="%d" height="%d" fill="%s"/>' % (width, height, C_CARD),
            '<text x="32" y="40" font-size="var(--svg-fs-8)" font-weight="700" fill="%s">%s</text>' %
            (C_INK, _esc(titel))]


def gebouw_svg(dos, titel="Gebouwoverzicht"):
    width, height = 900, 540
    result = _svg_start(width, height, titel)
    footprint, reden = _footprint(dos)
    if not footprint:
        result.append('<g data-state="fallback"><rect x="180" y="120" width="540" height="260" rx="10" '
                      'fill="%s" stroke="%s" stroke-width="2" stroke-dasharray="8 8"/>' %
                      (C_HOUSE, C_HOUSE_LINE))
        result.append('<text x="450" y="235" text-anchor="middle" font-size="var(--svg-fs-6)" '
                      'font-weight="650" fill="%s">Vereenvoudigd aanzicht</text>' % C_INK)
        result.append('<text x="450" y="270" text-anchor="middle" font-size="var(--svg-fs-4)" fill="%s">%s</text>' %
                      (C_SUB, _esc(reden)))
        for i, s in enumerate(dos.schil[:8]):
            result.append('<text x="450" y="%d" text-anchor="middle" font-size="var(--svg-fs-2)" fill="%s">%s · %.1f m&#178;</text>' %
                          (305 + i * 18, C_SUB, _esc(s.id), s.oppervlakte_m2 or 0))
        result.append('</g></svg>')
        return "".join(result)

    house_w, house_d, gevel_h, gevels = footprint
    wall_h = getattr(dos.opname, "gebouwhoogte_m", None) or gevel_h
    def gevel_line(naam):
        return C_KNOWN if gevels[naam] and all(s.rc_huidig or s.u_huidig for s in gevels[naam]) else C_UNKNOWN
    def gevel_label(naam):
        return ", ".join(s.id or naam for s in gevels[naam])
    faces = [
        _face([(0, 0, 0), (house_w, 0, 0), (house_w, wall_h, 0), (0, wall_h, 0)],
              C_HOUSE, gevel_line("voor"), "gevel-voor", gevel_label("voor")),
        _face([(house_w, 0, 0), (house_w, 0, house_d), (house_w, wall_h, house_d), (house_w, wall_h, 0)],
              C_HOUSE, gevel_line("rechts"), "gevel-rechts", gevel_label("rechts")),
        _face([(0, wall_h, 0), (house_w, wall_h, 0), (house_w, wall_h, house_d), (0, wall_h, house_d)],
              C_HOUSE, C_HOUSE_LINE, "bovenzijde"),
    ]
    dakfaces, exact, legacy = _dak_faces(dos, house_w, house_d, wall_h)
    faces.extend(dakfaces)
    faces.extend(_dakkapel_faces(dos, house_w, house_d, wall_h))
    points = [_project(p) for f in faces for p in f["points"]]
    min_x, max_x = min(p[0] for p in points), max(p[0] for p in points)
    min_y, max_y = min(p[1] for p in points), max(p[1] for p in points)
    scale = min(680 / max(1, max_x - min_x), 330 / max(1, max_y - min_y))
    def screen(point):
        px, py = _project(point)
        return "%.1f,%.1f" % ((px - (min_x + max_x) / 2) * scale + 450,
                              (py - (min_y + max_y) / 2) * scale + 255)
    result.append('<g data-view="isometrisch" data-height="%.2f">' % wall_h)
    for face in faces:
        attrs = " ".join('%s="%s"' % (_esc(k), _esc(v)) for k, v in face["attrs"].items())
        result.append('<polygon points="%s" fill="%s" stroke="%s" stroke-width="2" '
                      'stroke-linejoin="round" data-face="%s" %s>' %
                      (" ".join(screen(p) for p in face["points"]), face["fill"], face["stroke"],
                       _esc(face["kind"]), attrs))
        if face["label"]:
            result.append('<title>%s</title>' % _esc(face["label"]))
        result.append('</polygon>')
    result.append('</g>')
    # Traceerbaarheid blijft expliciet, ook voor niet-zichtbare achter-/linkergevels.
    result.append('<g data-layer="trace" aria-hidden="true">')
    for naam, delen in gevels.items():
        for s in delen:
            bekend = bool(s.rc_huidig or s.u_huidig)
            result.append('<text x="32" y="%d" font-size="var(--svg-fs-1)" fill="%s" '
                          'data-id="%s" data-orientation="%s">%s · %.1f m&#178;</text>' %
                          (445 + len(result) % 4 * 16, C_KNOWN if bekend else C_UNKNOWN,
                           _esc(s.id), _esc(s.orientatie), _esc(s.id), s.oppervlakte_m2 or 0))
    result.append('</g>')
    if legacy:
        result.append('<text x="868" y="500" text-anchor="end" font-size="var(--svg-fs-2)" fill="%s">'
                      '△ dak benaderd: renderingmaten ontbreken</text>' % C_SUB)
    elif exact:
        result.append('<text x="868" y="500" text-anchor="end" font-size="var(--svg-fs-2)" fill="%s">'
                      'Dak maatvast uit opgeslagen invoer</text>' % C_SUB)
    result.append('</svg>')
    return "".join(result)
