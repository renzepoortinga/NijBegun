"""Dependencyvrije PDF/PNG-export voor het interactieve ventilatieplan.

De Flask-pagina levert met ``_vp_context`` al de ene, canonieke scene op. Deze
module tekent die scene zowel naar PNG als naar de vloerpagina's van de PDF;
er is dus geen tweede plaatsings- of rekenpad voor de export.
"""
from __future__ import annotations

import datetime
import re
import struct
import textwrap
import unicodedata
import zlib


WIDTH, HEIGHT = 1200, 900
DISCLAIMER = "Indicatief ventilatieplan op basis van Nij Begun-vuistregels (BBL), geen rechten."


def bestands_slug(adres):
    tekst = unicodedata.normalize("NFKD", str(adres or "ventilatieplan"))
    tekst = tekst.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", tekst).strip("-")[:80] or "ventilatieplan"


def opname_datum(dos):
    return (getattr(getattr(dos, "opname", None), "opnamedatum", "") or "onbekend")


def bruikbare_verdiepingen(verdiepingen):
    """Een lege placeholder is geen plattegrond en mag niet als lege export doorgaan."""
    return [v for v in verdiepingen if (v.get("achtergrond_soort") in ("contour", "afbeelding")
                                        or any(r.get("contour") for r in v.get("ruimtes", [])))]


def scene(verdiepingen, res, balans, toets, adres, systeem, opnamedatum):
    return {"verdiepingen": bruikbare_verdiepingen(verdiepingen), "res": res,
            "balans": balans, "toets": toets, "adres": adres or "Adres onbekend",
            "systeem": systeem or "Onbekend", "opnamedatum": opnamedatum or "onbekend",
            "exportdatum": datetime.date.today().isoformat()}


_FONT = {
    "0":"111101101101111", "1":"010110010010111", "2":"111001111100111",
    "3":"111001111001111", "4":"101101111001001", "5":"111100111001111",
    "6":"111100111101111", "7":"111001001001001", "8":"111101111101111",
    "9":"111101111001111", ".":"000000000010010", "-":"000000111000000",
    " ":"000000000000000", "/":"001001010100100",
}
for _c, _bits in {
    "A":"010101111101101", "B":"110101110101110", "C":"011100100100011",
    "D":"110101101101110", "E":"111100110100111", "F":"111100110100100",
    "G":"011100101101011", "H":"101101111101101", "I":"111010010010111",
    "J":"001001001101010", "K":"101101110101101", "L":"100100100100111",
    "M":"101111111101101", "N":"101111111111101", "O":"010101101101010",
    "P":"110101110100100", "Q":"010101101111011", "R":"110101110101101",
    "S":"011100010001110", "T":"111010010010010", "U":"101101101101111",
    "V":"101101101101010", "W":"101101111111101", "X":"101101010101101",
    "Y":"101101010010010", "Z":"111001010100111", ":":"000010000010000",
}.items():
    _FONT[_c] = _bits


class _Raster:
    def __init__(self, width=WIDTH, height=HEIGHT):
        self.w, self.h = width, height
        self.data = bytearray(b"\xff" * (width * height * 3))

    def pixel(self, x, y, kleur):
        x, y = int(x), int(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.data[i:i+3] = bytes(kleur)

    def lijn(self, x0, y0, x1, y1, kleur, dikte=3):
        dx, dy = x1-x0, y1-y0
        stappen = max(1, int(max(abs(dx), abs(dy))))
        for i in range(stappen + 1):
            x, y = x0 + dx*i/stappen, y0 + dy*i/stappen
            for ox in range(-dikte//2, dikte//2+1):
                for oy in range(-dikte//2, dikte//2+1): self.pixel(x+ox, y+oy, kleur)

    def polygoon(self, punten, kleur, dikte=3):
        for i, p in enumerate(punten): self.lijn(*p, *punten[(i+1) % len(punten)], kleur, dikte)

    def cirkel(self, cx, cy, r, kleur):
        for y in range(int(cy-r), int(cy+r)+1):
            for x in range(int(cx-r), int(cx+r)+1):
                if (x-cx)**2 + (y-cy)**2 <= r*r: self.pixel(x, y, kleur)

    def tekst(self, x, y, tekst, kleur=(22, 39, 55), schaal=3):
        cursor = x
        for teken in str(tekst).upper():
            bits = _FONT.get(teken, _FONT.get(" "))
            for ry in range(5):
                for rx in range(3):
                    if bits[ry*3+rx] == "1":
                        for oy in range(schaal):
                            for ox in range(schaal): self.pixel(cursor+rx*schaal+ox, y+ry*schaal+oy, kleur)
            cursor += 4*schaal


def _vloer_raster(v):
    r = _Raster()
    donker, licht = (42, 61, 74), (161, 176, 184)
    r.tekst(35, 25, v.get("naam", "Verdieping"), schaal=4)
    def pts(rel): return [(60+p[0]*1080, 90+p[1]*760) for p in (rel or [])]
    contour = pts(v.get("contour_punten"))
    if contour: r.polygoon(contour, donker, 5)
    for ruimte in v.get("ruimtes", []):
        rp = pts(ruimte.get("contour"))
        if rp: r.polygoon(rp, licht, 3)
        lab = ruimte.get("label") or [.5, .5]
        r.tekst(60+lab[0]*1080, 90+lab[1]*760, ruimte.get("naam", ""), schaal=2)
    kleuren = {"toevoer": (0, 105, 170), "afvoer": (223, 103, 0), "overstroom": (25, 135, 84)}
    for m in v.get("markers", []):
        x, y = 60+m["x"]*1080, 90+m["y"]*760
        kleur = kleuren.get(m.get("type"), donker)
        if m.get("type") == "afvoer": r.cirkel(x, y, 25, kleur)
        else: r.polygoon([(x, y-30), (x+27, y+25), (x-27, y+25)], kleur, 8)
        r.tekst(x-18, y-7, "%.1f" % m.get("waarde_ls", 0), (255,255,255), 2)
    return r


def _png(raster):
    def chunk(typ, data):
        return struct.pack(">I", len(data)) + typ + data + struct.pack(">I", zlib.crc32(typ+data) & 0xffffffff)
    rows = b"".join(b"\0" + raster.data[y*raster.w*3:(y+1)*raster.w*3] for y in range(raster.h))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", raster.w, raster.h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b""))


def verdieping_png(v):
    return _png(_vloer_raster(v))


def _pdf_text(s):
    raw = str(s).replace("—", "-").replace("→", "->").replace("≠", "!=")
    return raw.encode("cp1252", "replace").replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _text_lines(lines, x=48, y=770, size=11, leading=16):
    out = [b"BT /F1 %d Tf %d %d Td" % (size, x, y)]
    eerste = True
    for line in lines:
        delen = textwrap.wrap(str(line), width=82, break_long_words=False,
                              break_on_hyphens=False) or [""]
        for deel in delen:
            if not eerste: out.append(b"0 -%d Td" % leading)
            out.append(b"(" + _pdf_text(deel) + b") Tj")
            eerste = False
    out.append(b"ET")
    return b"\n".join(out)


def pdf(scene_data):
    floors = scene_data["verdiepingen"]
    total = len(floors) + 2
    pages = []
    title = ["VENTILATIEPLAN", "", scene_data["adres"],
             "Exportdatum: %s" % scene_data["exportdatum"],
             "Ventilatiesysteem: %s" % scene_data["systeem"], "",
             "Balans: toevoer %.1f l/s %s afvoer %.1f l/s" % (
                 scene_data["balans"]["toevoer"], "=" if scene_data["balans"]["sluitend"] else "!=",
                 scene_data["balans"]["afvoer"])]
    pages.append((title, None))
    for v in floors: pages.append(([v["naam"], "Herkomst plattegrond: MagicPlan-opname, %s" % scene_data["opnamedatum"]], _vloer_raster(v)))
    rows = scene_data["res"]["rows"]
    lines = ["BEREKENING", "", "Toevoer per verblijfsruimte", "Ruimte | m2 | Min. l/s | Advies l/s"]
    for row in rows:
        if row.get("toevoer"):
            lines.append("%s | %.1f | %.1f | %.1f" % (row["naam"], row["opp"], row["toevoer"], row["toevoer"]))
    lines += ["", "Afvoer per natte ruimte", "Ruimte | Min. l/s | Advies l/s | Afvoerpunt"]
    for row in rows:
        if row.get("afvoerpunt"):
            lines.append("%s | %.1f | %.1f | Ja" % (row["naam"], row["afvoer"], row["afvoer_advies_ls"]))
    lines += ["", "Balans: toevoer %.1f l/s %s afvoer %.1f l/s" % (
        scene_data["balans"]["toevoer"], "=" if scene_data["balans"]["sluitend"] else "!=",
        scene_data["balans"]["afvoer"]), "", "Vuistregels / aandachtspunten"]
    lines += ["[%s] %s - %s" % (t["status"], t["regel"], t["reden"]) for t in scene_data["toets"]]
    lines += ["Waarschuwing: %s" % w for w in scene_data["res"].get("waarschuwingen", [])]
    pages.append((lines, None))

    objs = [None]  # 1-based
    def add(data): objs.append(data); return len(objs)-1
    catalog = add(b"")
    pages_obj = add(b"")
    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    page_ids = []
    for idx, (text, raster) in enumerate(pages, 1):
        image_id = None
        if raster:
            raw = bytes(raster.data)
            image_id = add(b"<< /Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode /Length %d >>\nstream\n" % (raster.w, raster.h, len(zlib.compress(raw))) + zlib.compress(raw) + b"\nendstream")
        if raster:
            # De herkomst staat bewust direct onder de tekening, niet alleen ergens op de pagina.
            content = (_text_lines(text[:1], 48, 805, 13, 15)
                       + b"\nq 510 0 0 382 42 205 cm /Im1 Do Q\n"
                       + _text_lines(text[1:], 48, 180, 9, 12))
        else:
            content = _text_lines(text, 48, 790, 11 if idx == total else 13, 15)
        footer = _text_lines([DISCLAIMER, "Pagina %d / %d" % (idx, total)], 48, 45, 8, 11)
        stream = content + b"\n" + footer
        content_id = add(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        resources = b"<< /Font << /F1 %d 0 R >>" % font
        if image_id: resources += b" /XObject << /Im1 %d 0 R >>" % image_id
        resources += b" >>"
        page_ids.append(add(b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 595 842] /Resources " % pages_obj + resources + b" /Contents %d 0 R >>" % content_id))
    objs[pages_obj] = b"<< /Type /Pages /Count %d /Kids [%s] >>" % (len(page_ids), b" ".join(b"%d 0 R" % x for x in page_ids))
    objs[catalog] = b"<< /Type /Catalog /Pages %d 0 R >>" % pages_obj
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for i, obj in enumerate(objs[1:], 1):
        offsets.append(len(out)); out += b"%d 0 obj\n" % i + obj + b"\nendobj\n"
    xref = len(out); out += b"xref\n0 %d\n0000000000 65535 f \n" % len(objs)
    out += b"".join(b"%010d 00000 n \n" % off for off in offsets[1:])
    out += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs), catalog, xref)
    return bytes(out)
