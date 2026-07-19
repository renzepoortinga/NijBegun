"""
Huisstijl-iconen voor de webapp genereren uit het OFFICIELE logo.

Bron (niet in de repo — staat in OneDrive bij Marketing):
    40_Marketing & Acquisitie/Huisstijl & Visitekaartjes/Logo/Poortinga versie 3.svg

Waarom een generator en geen losse plaatjes: zo is te herleiden waar elk bestand vandaan komt en
kun je ze opnieuw maken als het logo wijzigt. De PNG's worden EENMALIG gemaakt en meegecommit —
Pillow staat bewust NIET in requirements.txt, want de VPS hoeft ze alleen te serveren.

Draaien (alleen nodig als het logo verandert):
    python dashboard/make_icons.py --bron "<pad naar Poortinga versie 3.svg>"

Levert in dashboard/static/:
    logo.svg              volledige lockup, THEMA-BEWUST (woordmerk = currentColor -> werkt in dark mode)
    mark.svg              alleen het groene beeldmerk, vierkant (favicon voor moderne browsers)
    apple-touch-icon.png  180x180, navy vlak + groen merk (iPad-beginscherm; iOS wil PNG, geen SVG)
    icon-192.png          PWA-manifest
    icon-512.png          PWA-manifest
    favicon-32.png        fallback voor oudere browsers
"""
import os, re, argparse

HIER = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(HIER, "static")

NAVY = (11, 60, 73)        # #0b3c49  huisstijl-donkerblauw
GROEN = (142, 198, 64)     # #8ec640  huisstijl-groen

# Het beeldmerk uit het bron-SVG (class cls-4). Een <polyline> MET fill = gevuld vlak.
# Letterlijk overgenomen zodat het merk exact het origineel is.
MARK_POINTS = [
    (29.10, 25.17), (26.69, 34.26), (10.31, 34.26), (8.90, 34.26), (2.14, 25.22),
    (2.14, 13.92), (2.10, 13.92), (13.03, 2.67), (13.50, 2.52), (24.64, 2.56),
    (33.40, 11.25), (26.58, 17.13), (18.78, 9.60), (11.23, 17.23), (11.23, 25.17),
    (26.64, 25.17),
]
MARK_BOX = (2.10, 2.52, 33.40, 34.26)      # min-x, min-y, max-x, max-y


def _punten_str():
    return " ".join("%g,%g" % p for p in MARK_POINTS)


def maak_mark_svg():
    """Vierkant beeldmerk met wat lucht eromheen — als favicon.svg."""
    x0, y0, x1, y1 = MARK_BOX
    b, h = x1 - x0, y1 - y0
    zij = max(b, h) * 1.18                        # 9% lucht rondom
    vx, vy = x0 - (zij - b) / 2, y0 - (zij - h) / 2
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%g %g %g %g">\n'
            '  <title>Poortinga Energieadvies</title>\n'
            '  <polyline fill="#8ec640" points="%s"/>\n</svg>\n'
            % (vx, vy, zij, zij, _punten_str()))


def maak_logo_svg(bron_pad):
    """Volledige lockup, maar het woordmerk op currentColor zodat het in dark mode leesbaar blijft.
    Het groen blijft altijd groen (huisstijlkleur, werkt op licht en donker)."""
    with open(bron_pad, encoding="utf-8") as fh:
        svg = fh.read()
    # de <style>-regels vervangen: cls-3 (Poortinga) + cls-2 (Energieadvies) -> currentColor
    nieuwe_style = (".cls-1{fill:none}"
                    ".cls-2{fill:currentColor;opacity:.92}"      # 'Energieadvies' (dun)
                    ".cls-3{fill:currentColor}"                  # 'Poortinga'
                    ".cls-4{fill:#8ec640}")                      # beeldmerk
    svg = re.sub(r"<style>.*?</style>", "<style>%s</style>" % nieuwe_style, svg, flags=re.S)
    svg = svg.replace('<svg id="Layer_2" data-name="Layer 2"',
                      '<svg role="img" aria-label="Poortinga Energieadvies"')
    svg = re.sub(r"<\?xml[^>]*\?>\s*", "", svg)          # XML-declaratie hoeft niet inline
    return svg.strip() + "\n"


def _teken_merk(grootte, achtergrond, marge=0.20, ss=8):
    """Beeldmerk als PNG. Supersampling (ss) i.p.v. antialiasing achteraf = strakke randen."""
    from PIL import Image, ImageDraw
    groot = grootte * ss
    img = Image.new("RGB", (groot, groot), achtergrond)
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = MARK_BOX
    b, h = x1 - x0, y1 - y0
    vak = groot * (1 - 2 * marge)
    s = vak / max(b, h)
    dx = (groot - b * s) / 2 - x0 * s
    dy = (groot - h * s) / 2 - y0 * s
    d.polygon([(x * s + dx, y * s + dy) for x, y in MARK_POINTS], fill=GROEN)
    return img.resize((grootte, grootte), Image.LANCZOS)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bron", required=True, help="pad naar 'Poortinga versie 3.svg'")
    a = p.parse_args()
    os.makedirs(STATIC, exist_ok=True)

    for naam, inhoud in (("logo.svg", maak_logo_svg(a.bron)), ("mark.svg", maak_mark_svg())):
        with open(os.path.join(STATIC, naam), "w", encoding="utf-8") as fh:
            fh.write(inhoud)
        print("geschreven:", naam)

    # iOS/Android-iconen: navy vlak + groen merk (op een beginscherm veel herkenbaarder dan wit)
    for naam, px in (("apple-touch-icon.png", 180), ("icon-192.png", 192),
                     ("icon-512.png", 512), ("favicon-32.png", 32)):
        _teken_merk(px, NAVY).save(os.path.join(STATIC, naam))
        print("geschreven: %s (%dx%d)" % (naam, px, px))


if __name__ == "__main__":
    main()
