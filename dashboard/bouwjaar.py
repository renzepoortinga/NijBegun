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
    """Minimale markdown->HTML (koppen/bold/lijsten) voor de hint-weergave."""
    uit, in_ul = [], False
    for regel in (md or "").splitlines():
        r = regel.rstrip()
        r = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", r)
        if r.startswith("### "):
            if in_ul:
                uit.append("</ul>"); in_ul = False
            uit.append("<h4>%s</h4>" % r[4:])
        elif r.lstrip().startswith(("- ", "• ")):
            if not in_ul:
                uit.append("<ul>"); in_ul = True
            uit.append("<li>%s</li>" % r.lstrip()[2:])
        elif r.startswith("> "):
            uit.append("<p class=muted>%s</p>" % r[2:])
        elif not r.strip():
            if in_ul:
                uit.append("</ul>"); in_ul = False
        else:
            uit.append("<p>%s</p>" % r)
    if in_ul:
        uit.append("</ul>")
    return "\n".join(uit)


def hint(bouwjaar):
    """-> (titel, html) of (None, None)."""
    titel, md = sectie_voor_bouwjaar(bouwjaar)
    return (titel, md_naar_html(md)) if titel else (None, None)
