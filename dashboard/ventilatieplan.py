"""
Datalaag voor het interactieve ventilatieplan (taak 020): groepeert ruimtes per verdieping, plaatst
een startset markers (autoplaatsing) en valideert/bewaart de wijzigingen die de adviseur via
slepen/klikken/toetsen in de webapp aanbrengt.

Puur — geen Flask-afhankelijkheden, zodat de logica los te testen is (`dashboard/app.py` roept dit
alleen aan). De rekenlaag zelf (welke l/s waar, wie voldoet aan een vuistregel) komt volledig uit
taak 019 (`ventilatie.bereken()` + `verdeel_balans()`); dit bestand tekent en bewaart alleen wat de
adviseur ermee doet, het rekent niets opnieuw uit.
"""
from __future__ import annotations

import uuid

from core.dossier import VentilatieMarker, VentilatieplanVerdieping

MARKER_TYPES = ("toevoer", "afvoer", "overstroom")


def polygoon_middelpunt(punten):
    """Stabiel labelpunt voor een expliciet ruimtepolygoon; geen punten betekent kaartmidden."""
    if not punten:
        return [0.5, 0.5]
    return [round(sum(float(p[0]) for p in punten) / len(punten), 4),
            round(sum(float(p[1]) for p in punten) / len(punten), 4)]


def groepeer_per_verdieping(dos):
    """Geeft [(verdieping_naam, VloerInfo|None, [Ruimte, ...]), ...].

    Bij 0 of 1 vloer in de geometrie (verreweg de meeste huidige dossiers) gaat alles in één groep.
    Bij meerdere VloerInfo's wordt gekoppeld op `Ruimte.verdieping`; ruimtes die niet koppelen (een
    oudere opname, of een parserpad dat de verdieping nog niet doorgeeft — zie core/dossier.py) komen
    expliciet in een aparte 'niet gekoppeld'-groep terecht. Nooit stil bij de verkeerde verdieping
    ingedeeld, en nooit stilzwijgend weggelaten.
    """
    vloeren = list(dos.geometrie.vloeren or [])
    ruimtes = list(dos.geometrie.ruimtes or [])
    if len(vloeren) <= 1:
        naam = vloeren[0].naam if vloeren else "Begane grond"
        return [(naam, vloeren[0] if vloeren else None, ruimtes)]
    groepen = []
    bekend = {v.naam for v in vloeren}
    for v in vloeren:
        groepen.append((v.naam, v, [r for r in ruimtes if r.verdieping == v.naam]))
    niet_gekoppeld = [r for r in ruimtes if r.verdieping not in bekend]
    if niet_gekoppeld:
        groepen.append(("Niet gekoppeld aan een verdieping", None, niet_gekoppeld))
    return groepen


def achtergrond_van(vloer):
    """(pad_of_None, soort) volgens de spec-volgorde: MagicPlan-plattegrondafbeelding > contour_m >
    lege kaart. `soort` is voor de template ('afbeelding' | 'contour' | 'geen') — de contour zelf
    wordt getekend door de aanroeper (dashboard/gebouw_svg.py kent het polygon-tekenwerk al)."""
    if vloer is None:
        return None, "geen"
    if vloer.plattegrond_afbeelding:
        return vloer.plattegrond_afbeelding, "afbeelding"
    if vloer.contour_m:
        return None, "contour"
    return None, "geen"


def contour_punten_relatief(vloer):
    """Normaliseert `VloerInfo.contour_m` naar relatieve (0..1) coördinaten voor de top-down
    tekenachtergrond, met een kleine marge zodat de contourlijn niet tegen de rand van de kaart
    plakt. None als er geen (bruikbare) contour is — de template valt dan terug op de lege kaart."""
    if not vloer or not vloer.contour_m or len(vloer.contour_m) < 3:
        return None
    xs = [p[0] for p in vloer.contour_m]
    zs = [p[1] for p in vloer.contour_m]
    breedte = (max(xs) - min(xs)) or 1.0
    diepte = (max(zs) - min(zs)) or 1.0
    marge, schaal = 0.08, 0.84
    return [[round(marge + (x - min(xs)) / breedte * schaal, 4),
             round(marge + (z - min(zs)) / diepte * schaal, 4)] for x, z in vloer.contour_m]


def _nieuw_marker_id(bestaande_ids):
    while True:
        kandidaat = "m%s" % uuid.uuid4().hex[:8]
        if kandidaat not in bestaande_ids:
            return kandidaat


def _polygoon_oppervlakte(punten):
    return abs(sum(punten[i][0] * punten[(i + 1) % len(punten)][1]
                   - punten[(i + 1) % len(punten)][0] * punten[i][1]
                   for i in range(len(punten))) / 2.0)


def _orientatie(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _segmenten_kruisen(a, b, c, d):
    return (_orientatie(a, b, c) * _orientatie(a, b, d) < 0
            and _orientatie(c, d, a) * _orientatie(c, d, b) < 0)


def _zelfsnijdend(punten):
    n = len(punten)
    for i in range(n):
        a, b = punten[i], punten[(i + 1) % n]
        for j in range(i + 1, n):
            if j in (i, (i + 1) % n) or (j + 1) % n in (i, (i + 1) % n):
                continue
            if _segmenten_kruisen(a, b, punten[j], punten[(j + 1) % n]):
                return True
    return False


def _intern_punt(punten):
    """Vind deterministisch een aantoonbaar intern punt, ook voor C/U-vormen."""
    min_x, max_x = min(p[0] for p in punten), max(p[0] for p in punten)
    min_y, max_y = min(p[1] for p in punten), max(p[1] for p in punten)
    for resolutie in (9, 21, 41):
        for yi in range(1, resolutie):
            y = min_y + (max_y - min_y) * yi / resolutie
            for xi in range(1, resolutie):
                x = min_x + (max_x - min_x) * xi / resolutie
                if punt_in_polygoon(x, y, punten):
                    return [x, y]
    return None


def _segment_intersectie_t(a, b, c, d):
    """Parameter t op a+t(b-a) bij echte intersectie met segment c-d."""
    rx, ry, sx, sy = b[0] - a[0], b[1] - a[1], d[0] - c[0], d[1] - c[1]
    den = rx * sy - ry * sx
    if abs(den) < 1e-12:
        return None
    qx, qy = c[0] - a[0], c[1] - a[1]
    t, u = (qx * sy - qy * sx) / den, (qx * ry - qy * rx) / den
    return t if 0 <= t <= 1 and 0 <= u <= 1 else None


def _randpunt_van_naar(bron, doel):
    """Echte eerste bronrand-intersectie richting doel, met eindpunt epsilon binnen bron."""
    if not bron.contour_relatief or not doel.contour_relatief:
        return None
    a = _intern_punt(bron.contour_relatief)
    b = _intern_punt(doel.contour_relatief)
    if not a or not b:
        return None
    ts = []
    punten = bron.contour_relatief
    for i in range(len(punten)):
        t = _segment_intersectie_t(a, b, punten[i], punten[(i + 1) % len(punten)])
        if t is not None and t > 1e-9:
            ts.append(t)
    if not ts:
        return None
    t = max(0.0, min(ts) - 1e-4)
    p = [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]
    return [round(p[0], 6), round(p[1], 6)] if punt_in_polygoon(p[0], p[1], punten) else None


def auto_markers(ruimtes, res_rows, topologie=None):
    """Startset markers voor één verdieping.

    Toevoer voor elke ruimte die in de rekenlaag (taak 019) echt toevoer heeft gekregen, afvoer voor
    elke ruimte met een afvoerpunt — beide langs de rand als VERTREKPUNT (bron='auto'), niet op een
    gemeten wandpositie: het dossier kent geen wandcoördinaten per ruimte, dus 'in de buitengevel
    plaatsen' kan alleen bij benadering. De adviseur sleept ze naar de echte plek.

    Overstroommarkers worden uitsluitend gemaakt voor expliciet bevestigde bron->doel-verbindingen.
    Zonder topologie geen groene pijl. Met twee ruimtepolygonen ligt de marker controleerbaar op de
    bronrand richting het natte doel; zonder beide polygonen blijft de verbinding opgeslagen maar nog
    niet tekenbaar.
    """
    by_naam = {r["naam"]: r for r in res_rows}
    toevoer_namen = [r.naam for r in ruimtes if (by_naam.get(r.naam) or {}).get("toevoer")]
    afvoer_namen = [r.naam for r in ruimtes if (by_naam.get(r.naam) or {}).get("afvoerpunt")]
    markers = []
    ruimte_by_naam = {r.naam: r for r in ruimtes}
    n_t = len(toevoer_namen)
    for i, naam in enumerate(toevoer_namen):
        rij = by_naam[naam]
        midden = polygoon_middelpunt(ruimte_by_naam[naam].contour_relatief)
        x_t, y_t = (midden if ruimte_by_naam[naam].contour_relatief
                    else [0.06, round((i + 1) / (n_t + 1), 3)])
        markers.append(VentilatieMarker(
            id="t%d" % (i + 1), type="toevoer", ruimte_id=naam,
            waarde_ls=rij.get("toevoer", 0.0), x=x_t, y=y_t,
            rotatie=90, bron="auto"))
    n_a = len(afvoer_namen)
    for i, naam in enumerate(afvoer_namen):
        rij = by_naam[naam]
        midden = polygoon_middelpunt(ruimte_by_naam[naam].contour_relatief)
        x_a, y_a = (midden if ruimte_by_naam[naam].contour_relatief
                    else [0.5, round((i + 1) / (n_a + 1), 3)])
        waarde = rij.get("afvoer_advies_ls")
        if waarde is None:
            waarde = rij.get("afvoer", 0.0)
        markers.append(VentilatieMarker(
            id="a%d" % (i + 1), type="afvoer", ruimte_id=naam, waarde_ls=waarde,
            x=x_a, y=y_a, rotatie=0, bron="auto"))
    ruimte_by_naam = {r.naam: r for r in ruimtes}
    for i, pad in enumerate(topologie or []):
        if len(pad) != 2 or pad[0] not in ruimte_by_naam or pad[1] not in ruimte_by_naam:
            continue
        bron, doel = ruimte_by_naam[pad[0]], ruimte_by_naam[pad[1]]
        positie = _randpunt_van_naar(bron, doel)
        rij = by_naam.get(bron.naam) or {}
        if positie and rij.get("toevoer"):
            markers.append(VentilatieMarker(
                id="o%d" % (i + 1), type="overstroom", ruimte_id=bron.naam,
                waarde_ls=rij["toevoer"], x=positie[0], y=positie[1], rotatie=90, bron="auto"))
    return markers


def zorg_voor_verdiepingen(dos, res_rows):
    """Zorgt dat `dos.ventilatieplan` een `VentilatieplanVerdieping` heeft voor elke groep uit
    `groepeer_per_verdieping()`, en vult 'm bij de EERSTE keer (nog geen markers) met de
    autoplaatsing. Bestaande, al bewerkte verdiepingen blijven onaangeroerd. Muteert `dos` in place;
    geeft True terug als er iets is toegevoegd/gevuld (de aanroeper moet dan opslaan)."""
    gewijzigd = False
    bestaand = {v.naam: v for v in dos.ventilatieplan.verdiepingen}
    for naam, _vloer, ruimtes in groepeer_per_verdieping(dos):
        v = bestaand.get(naam)
        if v is None:
            v = VentilatieplanVerdieping(naam=naam)
            dos.ventilatieplan.verdiepingen.append(v)
            bestaand[naam] = v
            gewijzigd = True
        if not v.markers:
            v.markers = auto_markers(ruimtes, res_rows, dos.ventilatieplan.topologie)
            gewijzigd = True
        elif not dos.ventilatieplan.topologie and any(m.type == "overstroom" for m in v.markers):
            # Migreer de eerdere taak-020-proefversie: een groene pijl zonder bevestigde verbinding
            # is een fantoom en mag niet zichtbaar/persistent blijven.
            v.markers = [m for m in v.markers if m.type != "overstroom"]
            gewijzigd = True
    return gewijzigd


def herstel_verdieping(dos, verdieping_naam, res_rows):
    """Zet de markers van precies deze verdieping terug naar de automatische startset; andere
    verdiepingen blijven onaangeroerd (acceptatiecriterium taak 020). Geeft de bijgewerkte
    VentilatieplanVerdieping terug, of None als de naam niet bestaat."""
    groepen = {naam: ruimtes for naam, _, ruimtes in groepeer_per_verdieping(dos)}
    ruimtes = groepen.get(verdieping_naam)
    if ruimtes is None:
        return None
    for v in dos.ventilatieplan.verdiepingen:
        if v.naam == verdieping_naam:
            v.markers = auto_markers(ruimtes, res_rows, dos.ventilatieplan.topologie)
            return v
    return None


def geldige_ruimtenamen(dos):
    return {r.naam for r in (dos.geometrie.ruimtes or [])}


def geldige_ruimtenamen_op_verdieping(dos, verdieping_naam):
    """Ruimte-id's die uitsluitend bij de gevraagde verdieping horen."""
    for naam, _vloer, ruimtes in groepeer_per_verdieping(dos):
        if naam == verdieping_naam:
            return {r.naam for r in ruimtes}
    return set()


def ruimtecontouren_op_verdieping(dos, verdieping_naam):
    for naam, _vloer, ruimtes in groepeer_per_verdieping(dos):
        if naam == verdieping_naam:
            return {r.naam: r.contour_relatief for r in ruimtes if r.contour_relatief}
    return {}


def punt_in_polygoon(x, y, punten):
    binnen = False
    j = len(punten) - 1
    for i in range(len(punten)):
        xi, yi = punten[i]; xj, yj = punten[j]
        if ((yi > y) != (yj > y)) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            binnen = not binnen
        j = i
    return binnen


def valideer_ruimtepolygonen(polygonen, geldige_namen):
    if not isinstance(polygonen, dict):
        return None, "Ruimtepolygonen moeten per ruimtenaam worden aangeleverd."
    if not polygonen:
        return None, "Teken minimaal één ruimtecontour voordat je opslaat."
    resultaat = {}
    for naam, punten in polygonen.items():
        if naam not in geldige_namen:
            return None, "Onbekende ruimte '%s' op deze verdieping." % naam
        if not isinstance(punten, list) or len(punten) < 3:
            return None, "Ruimte '%s' heeft minimaal 3 punten nodig." % naam
        schoon = []
        for punt in punten:
            try:
                x, y = float(punt[0]), float(punt[1])
            except (TypeError, ValueError, IndexError):
                return None, "Ruimte '%s' bevat een ongeldig punt." % naam
            if not (0 <= x <= 1 and 0 <= y <= 1):
                return None, "Ruimte '%s' valt buiten het tekenvlak." % naam
            schoon.append([round(x, 4), round(y, 4)])
        if _zelfsnijdend(schoon):
            return None, "Ruimte '%s' heeft een zelfsnijdende contour." % naam
        if _polygoon_oppervlakte(schoon) < 1e-6:
            return None, "Ruimte '%s' heeft een degeneratieve contour zonder oppervlak." % naam
        resultaat[naam] = schoon
    return resultaat, None


def valideer_markers(markers_data, geldige_namen, ruimtecontouren=None):
    """`markers_data`: lijst dicts uit de POST-body (één verdieping). Geeft
    `(markers: [VentilatieMarker], fout: str|None)` terug. Weigert het HELE verzoek bij de eerste
    fout — nooit een deel van de tekening stil opslaan terwijl de rest wordt verworpen."""
    resultaat = []
    gebruikte_ids = set()
    for m in markers_data:
        typ = (m.get("type") or "").strip()
        if typ not in MARKER_TYPES:
            return None, "Onbekend markertype '%s' (moet zijn: %s)." % (typ, ", ".join(MARKER_TYPES))
        ruimte_id = (m.get("ruimte_id") or "").strip()
        if ruimte_id not in geldige_namen:
            return None, "Marker verwijst naar een onbekende ruimte '%s' — niet opgeslagen." % ruimte_id
        try:
            x = float(m.get("x", 0)); y = float(m.get("y", 0))
        except (TypeError, ValueError):
            return None, "Marker heeft geen geldige positie (x/y)."
        if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
            return None, "Marker valt buiten de tekening (x/y moeten tussen 0 en 1 liggen)."
        contour = (ruimtecontouren or {}).get(ruimte_id)
        if contour and not punt_in_polygoon(x, y, contour):
            return None, "Marker valt buiten ruimte '%s' — niet opgeslagen." % ruimte_id
        try:
            waarde = float(m.get("waarde_ls", 0))
        except (TypeError, ValueError):
            return None, "Marker heeft geen geldige l/s-waarde."
        try:
            rotatie = int(float(m.get("rotatie", 0))) % 360
        except (TypeError, ValueError):
            rotatie = 0
        mid = (m.get("id") or "").strip() or _nieuw_marker_id(gebruikte_ids)
        gebruikte_ids.add(mid)
        resultaat.append(VentilatieMarker(
            id=mid, type=typ, ruimte_id=ruimte_id, waarde_ls=round(waarde, 1),
            x=round(x, 4), y=round(y, 4), rotatie=rotatie, bron=(m.get("bron") or "handmatig")))
    return resultaat, None


def marker_balans(dos):
    """Som van alle toevoer- resp. afvoermarkers over ALLE verdiepingen — dit is de tekening zoals ze
    nu op het scherm staat, en kan afwijken van de rekenlaag-advieswaarden (taak 019) zodra de
    adviseur handmatig heeft bijgesteld (bv. een rooster met een vaste fabriekscapaciteit)."""
    toevoer = afvoer = 0.0
    for v in dos.ventilatieplan.verdiepingen:
        for m in v.markers:
            if m.type == "toevoer":
                toevoer += m.waarde_ls
            elif m.type == "afvoer":
                afvoer += m.waarde_ls
    toevoer, afvoer = round(toevoer, 1), round(afvoer, 1)
    return {"toevoer": toevoer, "afvoer": afvoer, "sluitend": abs(toevoer - afvoer) < 0.05}
