"""
Visueel ventilatieplan (SVG) uit de ventilatieberekening (ventilatie/ventilatie.py: bereken()).

Schematisch, Apple-HIG-stijl: elke ruimte een kaart met TOEVOER (blauw, lucht in) en/of AFVOER (oranje,
lucht uit), plus een balans-balk (toevoer vs afvoer) en de Nij Begun-vuistregels-checklist. Bedoeld als
los exportbestand én als beeld in het isolatieplan. Cijfers komen 1-op-1 uit bereken() — niets verzonnen.

Toevoer komt fysiek via ROOSTERS (raambreedte bepaalt de roosterlengte) of WTW-ventielen; de exacte l/s per
rooster (kennisbank) verdeelt de adviseur over de beschikbare raambreedte — het plan toont de benodigde
toevoer per ruimte + een notitie, en gokt geen rooster-capaciteit (golden rule).

    from ventilatie.ventilatie import bereken
    from ventilatie.ventilatieplan_svg import ventilatieplan_svg
    svg = ventilatieplan_svg(bereken(dossier.geometrie.ruimtes), adres="Straat 1, Plaats")
"""

# kleuren (SF-achtig)
C_IN = "#0A84FF"       # toevoer (blauw)
C_OUT = "#FF9F0A"      # afvoer (oranje)
C_INK = "#1C1C1E"
C_SUB = "#8E8E93"
TINT = {"verblijfsruimte": "#EAF3FF", "slaapkamer": "#EAF3FF", "keuken": "#FFF4E5",
        "badkamer": "#FFF4E5", "toilet": "#FFF4E5", "wasruimte": "#FFF4E5"}
TINT_DEFAULT = "#F2F2F7"


def _esc(s):
    return (str(s or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def ventilatieplan_svg(res, adres="", titel="Ventilatieplan"):
    rows = res.get("rows", [])
    cols = 3
    cw, ch, gx, gy = 232, 104, 16, 16
    x0, y_cards = 32, 150
    n = max(len(rows), 1)
    n_rows = (n + cols - 1) // cols
    grid_h = n_rows * (ch + gy)
    warns = res.get("waarschuwingen", [])
    vuist = res.get("vuistregels", [])
    bal_y = y_cards + grid_h + 18
    checklist_y = bal_y + 92
    height = checklist_y + 24 + len(vuist) * 19 + len(warns) * 19 + 40
    width = x0 * 2 + cols * cw + (cols - 1) * gx

    P = []
    P.append('<svg viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg" '
             'font-family="-apple-system, BlinkMacSystemFont, system-ui, Segoe UI, sans-serif">' % (width, height))
    P.append('<defs><filter id="sh" x="-20%%" y="-20%%" width="140%%" height="140%%">'
             '<feDropShadow dx="0" dy="1" stdDeviation="3" flood-color="#000" flood-opacity="0.08"/></filter>'
             '<marker id="ain" markerWidth="9" markerHeight="9" refX="4.5" refY="8" orient="auto">'
             '<path d="M4.5 9L0 2h9z" fill="%s"/></marker>'
             '<marker id="aout" markerWidth="9" markerHeight="9" refX="4.5" refY="1" orient="auto">'
             '<path d="M4.5 0L9 7H0z" fill="%s"/></marker></defs>' % (C_IN, C_OUT))
    P.append('<rect x="0" y="0" width="%d" height="%d" fill="#ffffff"/>' % (width, height))

    # kop
    P.append('<text x="%d" y="48" font-size="26" font-weight="700" fill="%s">%s</text>'
             % (x0, C_INK, _esc(titel)))
    if adres:
        P.append('<text x="%d" y="72" font-size="14" fill="%s">%s</text>' % (x0, C_SUB, _esc(adres)))
    P.append('<text x="%d" y="104" font-size="13" fill="%s">Nij Begun-vuistregels (BBL) · %.1f dm³/s·m² per '
             'verblijfsgebied · afvoer keuken 21 / bad 14 / toilet 7 dm³/s · toevoer via roosters of WTW.</text>'
             % (x0, C_SUB, res.get("rate", 0.7)))
    # legenda
    lx = width - 250
    P.append('<rect x="%d" y="36" width="14" height="14" rx="4" fill="%s"/>'
             '<text x="%d" y="48" font-size="13" fill="%s">toevoer (in)</text>' % (lx, C_IN, lx + 20, C_INK))
    P.append('<rect x="%d" y="58" width="14" height="14" rx="4" fill="%s"/>'
             '<text x="%d" y="70" font-size="13" fill="%s">afvoer (uit)</text>' % (lx, C_OUT, lx + 20, C_INK))

    # ruimte-kaarten
    for i, r in enumerate(rows):
        cx = x0 + (i % cols) * (cw + gx)
        cy = y_cards + (i // cols) * (ch + gy)
        tint = TINT.get(r.get("functie"), TINT_DEFAULT)
        P.append('<rect x="%d" y="%d" width="%d" height="%d" rx="14" fill="%s" stroke="#E5E5EA" '
                 'filter="url(#sh)"/>' % (cx, cy, cw, ch, tint))
        P.append('<text x="%d" y="%d" font-size="15" font-weight="650" fill="%s">%s</text>'
                 % (cx + 16, cy + 28, C_INK, _esc(r.get("naam", ""))[:24]))
        P.append('<text x="%d" y="%d" font-size="12" fill="%s">%s · %.1f m²</text>'
                 % (cx + 16, cy + 46, C_SUB, _esc(r.get("functie", "")), r.get("opp", 0) or 0))
        toe, afv = r.get("toevoer", 0) or 0, r.get("afvoer", 0) or 0
        if toe:
            ay = cy + ch - 20
            P.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="2.5" '
                     'marker-end="url(#ain)"/>' % (cx + 24, cy + ch - 44, cx + 24, ay, C_IN))
            P.append('<text x="%d" y="%d" font-size="15" font-weight="700" fill="%s">%.0f</text>'
                     '<text x="%d" y="%d" font-size="11" fill="%s">l/s in</text>'
                     % (cx + 36, cy + ch - 30, C_IN, toe, cx + 36, cy + ch - 16, C_SUB))
        if afv:
            P.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="2.5" '
                     'marker-end="url(#aout)"/>' % (cx + cw - 28, cy + ch - 20, cx + cw - 28, cy + ch - 44, C_OUT))
            P.append('<text x="%d" y="%d" font-size="15" font-weight="700" fill="%s" text-anchor="end">%.0f</text>'
                     '<text x="%d" y="%d" font-size="11" fill="%s" text-anchor="end">l/s uit</text>'
                     % (cx + cw - 40, cy + ch - 30, C_OUT, afv, cx + cw - 40, cy + ch - 16, C_SUB))

    # balans-balk
    toe_t, afv_t = res.get("toevoer_totaal", 0), res.get("afvoer_totaal", 0)
    mg = res.get("maatgevend_dm3s", 0) or 1
    bw = width - 2 * x0 - 150
    P.append('<text x="%d" y="%d" font-size="15" font-weight="650" fill="%s">Balans</text>' % (x0, bal_y + 2, C_INK))
    for lbl, val, col, dy in (("toevoer", toe_t, C_IN, 22), ("afvoer", afv_t, C_OUT, 50)):
        w = int(bw * (val / mg)) if mg else 0
        P.append('<text x="%d" y="%d" font-size="12" fill="%s">%s</text>' % (x0, bal_y + dy + 12, C_SUB, lbl))
        P.append('<rect x="%d" y="%d" width="%d" height="16" rx="8" fill="#F2F2F7"/>' % (x0 + 70, bal_y + dy, bw, ))
        P.append('<rect x="%d" y="%d" width="%d" height="16" rx="8" fill="%s"/>' % (x0 + 70, bal_y + dy, max(w, 6), col))
        P.append('<text x="%d" y="%d" font-size="13" font-weight="700" fill="%s">%.0f dm³/s</text>'
                 % (x0 + 80 + bw, bal_y + dy + 13, C_INK, val))
    P.append('<text x="%d" y="%d" font-size="13" fill="%s">Maatgevende ventilatiehoeveelheid: '
             '<tspan font-weight="700" fill="%s">%.0f dm³/s</tspan> (~%.0f m³/h)</text>'
             % (x0, bal_y + 86, C_SUB, C_INK, mg, res.get("maatgevend_m3h", 0)))

    # checklist + waarschuwingen
    yy = checklist_y
    P.append('<text x="%d" y="%d" font-size="15" font-weight="650" fill="%s">Vuistregels (toetsen vóór indienen)</text>'
             % (x0, yy, C_INK))
    yy += 24
    for v in vuist:
        P.append('<text x="%d" y="%d" font-size="12.5" fill="%s">•  %s</text>' % (x0, yy, C_INK, _esc(v)))
        yy += 19
    for w in warns:
        P.append('<text x="%d" y="%d" font-size="12.5" fill="#D70015">⚠  %s</text>' % (x0, yy, _esc(w)))
        yy += 19
    P.append('</svg>')
    return "".join(P)


def schrijf(res, path, adres="", titel="Ventilatieplan"):
    svg = ventilatieplan_svg(res, adres=adres, titel=titel)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(svg)
    return path


if __name__ == "__main__":
    import os, sys
    here = os.path.dirname(os.path.abspath(__file__))
    # verwijder de script-dir uit het pad: die bevat ventilatie.py en zou de 'ventilatie'-package schaduwen
    sys.path = [p for p in sys.path if os.path.abspath(p or ".") != here]
    sys.path.insert(0, os.path.dirname(here))
    from core.dossier import load_json
    from ventilatie.ventilatie import bereken
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dos = load_json(os.path.join(root, "out", "dossier_9501TP_12.json"))
    res = bereken(dos.geometrie.ruimtes)
    out = os.path.join(root, "out", "ventilatieplan_demo.svg")
    schrijf(res, out, adres="%s %s, %s" % (dos.identificatie.straat, dos.identificatie.huisnummer, dos.identificatie.plaats))
    print("OK:", out)
