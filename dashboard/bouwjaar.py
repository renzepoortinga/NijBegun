"""
Bouwjaar-hints voor de webapp: toont bij de opname wat je op basis van het bouwjaar waarschijnlijk
aantreft (constructie/installaties/risico's/let-op/maatregelen) uit docs/bouwjaarklasse-opnamegids.md.
"""
import os, re

TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GIDS = os.path.join(TOOL_DIR, "docs", "bouwjaarklasse-opnamegids.md")

# (van, tot, header-fragment zoals in de gids)
ERAS = [(0, 1945, "Vóór 1946"), (1946, 1964, "1946–1964"), (1965, 1974, "1965–1974"),
        (1975, 1982, "1975–1982"), (1983, 1991, "1983–1991"), (1992, 2005, "1992–2005"),
        (2006, 9999, "Vanaf 2006")]


def sectie_voor_bouwjaar(bouwjaar):
    """-> (titel, markdown) van het passende tijdvak, of (None, None)."""
    if not bouwjaar or not os.path.isfile(GIDS):
        return None, None
    frag = next((f for lo, hi, f in ERAS if lo <= int(bouwjaar) <= hi), None)
    if not frag:
        return None, None
    tekst = open(GIDS, encoding="utf-8").read()
    m = re.search(r"^## (%s[^\n]*)\n(.*?)(?=^## |\Z)" % re.escape(frag), tekst, re.M | re.S)
    return (m.group(1).strip(), m.group(2).strip()) if m else (None, None)


def md_naar_html(md):
    """Minimale markdown->HTML (koppen/bold/lijsten/tabellen/checkboxes) — voor de bouwjaar-hint
    én de veldgidsen in de webapp (/gids/<naam>)."""
    uit, in_ul, in_tbl, in_svg = [], False, False, False

    def sluit():
        nonlocal in_ul, in_tbl
        if in_ul:
            uit.append("</ul>"); in_ul = False
        if in_tbl:
            uit.append("</table></div>"); in_tbl = False

    for regel in (md or "").splitlines():
        r = regel.rstrip()
        # raw HTML/SVG-blok (bv. inline illustraties) verbatim doorlaten — anders wikkelt de renderer
        # elke regel in <p> en breekt de SVG. Blok start bij een regel met <svg en eindigt bij </svg>.
        if in_svg or r.lstrip().startswith("<svg"):
            sluit()
            uit.append(regel)
            if "</svg>" in r:
                in_svg = False
            elif not in_svg:
                in_svg = True
            continue
        r = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", r)
        r = re.sub(r"`([^`]+)`", r"<code>\1</code>", r)
        ls = r.lstrip()
        if ls.startswith("|"):
            cellen = [c.strip() for c in ls.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cellen if c):
                continue                          # separator-rij |---|---|
            rij = "<tr>" + "".join(("<th>%s</th>" if not in_tbl else "<td>%s</td>") % c
                                   for c in cellen) + "</tr>"
            if not in_tbl:
                sluit(); uit.append('<div class="table-wrap"><table>'); in_tbl = True
            uit.append(rij)
        elif r.startswith("### "):
            sluit(); uit.append("<h4>%s</h4>" % r[4:])
        elif r.startswith("## ") or r.startswith("# "):
            sluit(); uit.append("<h3>%s</h3>" % r.lstrip("#").strip())
        elif ls.startswith(("- [ ] ", "- [x] ", "- [X] ")):
            if not in_ul:
                sluit(); uit.append("<ul style='list-style:none;padding-left:4px'>"); in_ul = True
            uit.append("<li>%s %s</li>" % ("☑" if ls[3].lower() == "x" else "☐", ls[6:]))
        elif ls.startswith(("- ", "• ")):
            if not in_ul:
                sluit(); uit.append("<ul>"); in_ul = True
            uit.append("<li>%s</li>" % ls[2:])
        elif r.startswith("> "):
            sluit(); uit.append("<p class=muted>%s</p>" % r[2:])
        elif not r.strip() or r.strip() in ("---", "***"):
            sluit()
        else:
            sluit(); uit.append("<p>%s</p>" % r)
    sluit()
    return "\n".join(uit)


def hint(bouwjaar):
    """-> (titel, html) of (None, None)."""
    titel, md = sectie_voor_bouwjaar(bouwjaar)
    return (titel, md_naar_html(md)) if titel else (None, None)
