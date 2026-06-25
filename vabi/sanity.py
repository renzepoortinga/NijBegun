"""
Parameter-sanity-check vóór VABI-export. Waarborgt dat de belangrijke (vaak handmatig in
te schatten) parameters kloppen: geometrie-vertaling is de grootste foutbron (blueprint 9.3).
Geen NTA8800-berekening -- alleen plausibiliteit/outlier-detectie die de adviseur dwingt
om kritieke maten NA TE METEN voordat ze in Vabi gaan.

Niveaus:
  NAMETEN  - waarschijnlijk fout/onbetrouwbaar; ga terug en meet/controleer
  LET OP   - ontbreekt of verdacht; VABI heeft het nodig of het verdient een check
  INFO     - opmerking ter info

Gebruik:
    from vabi.sanity import check
    issues = check(dossier)   # -> [(niveau, melding), ...]
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.dossier import Dossier  # noqa: E402

# plausibele plafondhoogte voor woningen (m)
H_MIN, H_MAX = 2.2, 3.2
# typische verdiepingshoogte voor gebouwhoogte-check (m)
H_TYPISCH = 2.7


def check(dos: Dossier):
    issues = []

    # 1. Plafondhoogtes / nameten gebouwhoogte
    hoogtes = [(v.naam, v.hoogte_m) for v in dos.geometrie.vloeren if v.hoogte_m]
    for naam, h in hoogtes:
        if h < H_MIN or h > H_MAX:
            issues.append(("NAMETEN", "Plafondhoogte '%s' = %.2f m valt buiten %.1f-%.1f m "
                           "(meetfout?). Nameten." % (naam, h, H_MIN, H_MAX)))
    if len(hoogtes) >= 2:
        hs = [h for _, h in hoogtes]
        if max(hs) - min(hs) > 0.5:
            issues.append(("NAMETEN", "Plafondhoogtes lopen >0,5 m uiteen (%.2f vs %.2f m). "
                           "Controleer/nameten." % (max(hs), min(hs))))

    # 2. Gebouwhoogte vs bouwlagen
    n = dos.identificatie.aantal_bouwlagen
    if n and hoogtes:
        geschat = sum(h for _, h in hoogtes)
        verwacht = n * H_TYPISCH
        if abs(geschat - verwacht) > 1.5:
            issues.append(("LET OP", "Som verdiepingshoogtes %.1f m wijkt af van %d bouwlagen "
                           "(~%.1f m verwacht). Gebouwhoogte nameten." % (geschat, n, verwacht)))
    elif n and not hoogtes:
        issues.append(("LET OP", "Bouwlagen=%d maar geen verdiepingshoogtes vastgelegd; "
                       "gebouwhoogte kan niet geverifieerd worden." % n))

    # 3. Orientatie verplicht op verticale schildelen (VABI eist per vlak)
    for s in dos.schil:
        is_horizontaal = s.type in ("vloer", "dak") or "dak" in (s.subtype or "").lower()
        if not is_horizontaal and not s.orientatie:
            issues.append(("LET OP", "Schildeel '%s' (%s) heeft geen orientatie; "
                           "VABI vereist N/O/Z/W per vlak." % (s.subtype or s.id, s.type)))

    # 4. Begrenzing verplicht
    for s in dos.schil:
        if not s.begrenzing:
            issues.append(("LET OP", "Schildeel '%s' heeft geen begrenzing "
                           "(Buiten/AOR/Grond/aangrenzend)." % (s.subtype or s.id)))

    # 5. Oppervlakte = 0
    for s in dos.schil:
        if not s.oppervlakte_m2:
            issues.append(("NAMETEN", "Schildeel '%s' heeft oppervlakte 0 m2. "
                           "Nameten." % (s.subtype or s.id)))

    # 6. Rc/U aanwezig
    for s in dos.schil:
        if s.type == "kozijn":
            if s.u_huidig is None:
                issues.append(("LET OP", "Kozijn '%s' mist U-waarde." % (s.subtype or s.id)))
        else:
            if s.rc_huidig is None:
                issues.append(("LET OP", "Schildeel '%s' mist Rc-waarde "
                               "(forfaitair o.b.v. bouwjaar invullen?)." % (s.subtype or s.id)))

    # 7. Ag vs som vloeren (grove check)
    ag = dos.geometrie.gebruiksoppervlakte_ag_m2
    som_vloer = sum(v.oppervlakte_m2 for v in dos.geometrie.vloeren if v.oppervlakte_m2)
    if ag and som_vloer and som_vloer > ag * 1.1:
        issues.append(("LET OP", "Som vloeroppervlak (%.1f m2) > Ag (%.1f m2). "
                       "Controleer zonering/dubbeltelling." % (som_vloer, ag)))

    # 8. Ruimtes: dubbele namen / som vs Ag
    namen = [r.naam for r in dos.geometrie.ruimtes if r.naam]
    dubbel = sorted({nm for nm in namen if namen.count(nm) > 1})
    if dubbel:
        issues.append(("LET OP", "Dubbele ruimtenamen: %s. Hernoem functioneel "
                       "(voorkomt zoneringsfouten)." % ", ".join(dubbel)))
    som_ruimte = sum(r.oppervlakte_m2 for r in dos.geometrie.ruimtes if r.oppervlakte_m2)
    if ag and som_ruimte and som_ruimte > ag * 1.25:
        issues.append(("LET OP", "Som ruimteoppervlak (%.1f m2) fors > Ag (%.1f m2). "
                       "Controleer." % (som_ruimte, ag)))

    # 9. Installaties minimaal voor label
    if not dos.installaties.verwarming.type_opwekker:
        issues.append(("LET OP", "Geen type warmteopwekker ingevuld; nodig voor het energielabel."))
    if not dos.installaties.tapwater.type_toestel:
        issues.append(("INFO", "Geen warmtapwater-toestel ingevuld."))

    return issues


def rapport(issues) -> str:
    if not issues:
        return "Parameter-check: geen bijzonderheden. Geometrie/installaties plausibel.\n"
    out = ["Parameter-check vóór VABI-export (controleer dit eerst):"]
    for niveau in ("NAMETEN", "LET OP", "INFO"):
        regels = [m for lvl, m in issues if lvl == niveau]
        if regels:
            out.append("\n[%s]" % niveau)
            out.extend("  - " + r for r in regels)
    n_nameten = sum(1 for lvl, _ in issues if lvl == "NAMETEN")
    out.append("\n%d punt(en) om na te meten, %d totaal." % (n_nameten, len(issues)))
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    import argparse
    from core.dossier import load_json
    ap = argparse.ArgumentParser(description="Parameter-sanity-check op een dossier")
    ap.add_argument("--dossier", required=True)
    a = ap.parse_args()
    print(rapport(check(load_json(a.dossier))))
