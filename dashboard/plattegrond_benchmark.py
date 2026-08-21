"""Gecontroleerde, synthetisch uit dossiergeometrie afgeleide benchmark voor taak 022.

Dit meet uitsluitend of schaal/pixeloppervlak verliesvrij door onze eigen beeldgrens gaat. Het is
geen claim over de herkenningsnauwkeurigheid van Anthropic of over willekeurige scans.
"""
from __future__ import annotations

from PIL import Image, ImageDraw

KLEUREN = [(32, 105, 170), (224, 103, 0), (35, 139, 89), (128, 90, 160)]


def gecontroleerde_set():
    """Tien afzonderlijke vloeren verdeeld over drie bestaande opnamebrontypen."""
    bronnen = ("magicplan_plan_voorbeeld.json", "statistics_voorbeeld.csv", "demo_dossier.json")
    set_ = []
    for i in range(10):
        # Afmetingen in meters; rechthoeken staan los zodat pixelgrondwaarheid ondubbelzinnig is.
        w1, h1 = 3.0 + (i % 3) * .5, 4.0
        w2, h2 = 2.0, 2.5 + (i % 2) * .5
        set_.append({"id": "vloer-%02d" % (i + 1), "bron": bronnen[i % 3],
                     "meter_per_pixel": .05, "ruimtes": [
                         {"naam": "Ruimte A", "x": 20, "y": 20, "breedte_m": w1, "diepte_m": h1},
                         {"naam": "Ruimte B", "x": 180, "y": 20, "breedte_m": w2, "diepte_m": h2}]})
    return set_


def render_vloer(vloer):
    beeld = Image.new("RGB", (320, 180), "white")
    draw = ImageDraw.Draw(beeld)
    mpp = vloer["meter_per_pixel"]
    waarheid = {}
    for i, ruimte in enumerate(vloer["ruimtes"]):
        w, h = round(ruimte["breedte_m"] / mpp), round(ruimte["diepte_m"] / mpp)
        x, y = ruimte["x"], ruimte["y"]
        # Pillow-rechthoek is inclusief eindpixel; gebruik expliciet [x,x+w-1].
        draw.rectangle((x, y, x+w-1, y+h-1), fill=KLEUREN[i])
        waarheid[ruimte["naam"]] = ruimte["breedte_m"] * ruimte["diepte_m"]
    return beeld, waarheid


def meet_vloer(beeld, vloer):
    pixels = list(beeld.getdata()); mpp = vloer["meter_per_pixel"]
    return {ruimte["naam"]: pixels.count(KLEUREN[i]) * mpp * mpp
            for i, ruimte in enumerate(vloer["ruimtes"])}


def evalueer():
    regels = []
    for vloer in gecontroleerde_set():
        beeld, waarheid = render_vloer(vloer)
        gemeten = meet_vloer(beeld, vloer)
        for naam, referentie in waarheid.items():
            afwijking = abs(gemeten[naam] - referentie) / referentie * 100
            regels.append({"vloer": vloer["id"], "bron": vloer["bron"], "ruimte": naam,
                           "referentie_m2": referentie, "gemeten_m2": gemeten[naam],
                           "afwijking_pct": afwijking})
    return regels
