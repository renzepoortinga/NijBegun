"""
Dossier -> VABI Installatiebibliotheek-XML (Ventilatie/Verwarming/Tapwater/Koeling), importeerbaar
via de Installaties-tegel.

GARANTIE-OP-IMPORT-ONTWERP: kloon een ECHTE, valide Installatie-export (sjabloon) en overschrijf
alleen velden die we BETROUWBAAR uit het dossier hebben:
  - vrije tekst (Merk/Type/Installatiejaar/Naam)           -> nooit enum-risico
  - een paar bevestigde enums (Ventilatie.Systeem, e.d.)   -> via harde validatie-poort
De rest blijft de valide sjabloon-default; de adviseur verifieert/vervolledigt installaties in
Vabi (Vabi = rekenkern). Zo kan de import niet struikelen op een onbekende enum.

INSTALLATIE-ENUMS LIVE GEHARVEST uit EPA (22-6-2026, vabi/refs/installatie_enums_EPA.md): PV volledig
(ZonneEnergie-knoop + paneeltype/fabricagejaar/bouwintegratie/oriëntatie), verwarming gasketel+HR-subtypes
+ opstelplaats + luchtverwarming, tapwater individueel/combi/Gaskeur-CW. Niet-bevestigde codes (warmtepomp-
bron/koeling/biomassa/WKK/ventilatie-subsystemen) worden NIET gegokt -> sjabloon-default + flag (golden rule).

    python vabi/installatie_generate.py --dossier out/dossier.json --out out/Installatiebibliotheek.xml
"""
import os, sys, copy, argparse
import xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.dossier import load_json                       # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "refs", "installatie_template.xml")

# systeem-soort (individueel/collectief): codes uit echte exports (0=individueel gangbaar)
SYSTEEM_SOORT = {"individueel": "0", "collectief": "1", "gemeenschappelijk": "1"}

# Installatie-enumcodes LIVE GEHARVEST uit EPA (22-6-2026) — zie vabi/refs/installatie_enums_EPA.md.
# ZonneEnergie/PV:
PV_SYSTEEM = {"pv": "0", "pvt": "1", "zonneboiler": "2", "opslag": "3"}
PV_ORIENTATIE = {"n": "0", "no": "1", "o": "2", "zo": "3", "z": "4", "zw": "5", "w": "6", "nw": "7"}  # PV: klokrichting vanaf N (anders dan geometrie!)
PV_BOUWINTEGRATIE = {"niet": "0", "matig": "1", "goed": "2", "sterk": "2", "onbekend": "3"}


def _pv_paneeltype(s):
    s = (s or "").lower()
    if "mono" in s: return "1"
    if "multi" in s or "poly" in s: return "2"
    if "amorf" in s: return "3"
    if "cigs" in s or "koper" in s or "gallium" in s: return "5"
    if "cdte" in s or "cadmium" in s: return "6"
    return "0"  # kwaliteitsverklaring/onbekend


def _pv_fabricagejaar(s):
    s = (s or "").lower()
    if "voor 2001" in s or "<2001" in s: return "0"
    if "2001" in s: return "1"
    if "2011" in s: return "2"
    if "2015" in s or "2016" in s or "2017" in s: return "3"
    if "2018" in s or "vanaf" in s or "na 2018" in s: return "4"
    return "5"  # onbekend


def _pv_code(d, keuze, fallback=None):
    return d.get((keuze or "").strip().lower(), fallback)


# Verwarming (anker-codes; rest = dropdown-volgorde, zie refs):
VERW_SUBTYPE = {"cr": "0", "vr": "1", "hr100": "2", "hr104": "3", "hr107": "4"}


def _norm_orient(s):
    s = (s or "").strip().lower().replace("-", "").replace(" ", "")
    M = {"noord": "n", "noordoost": "no", "oost": "o", "zuidoost": "zo", "zuid": "z",
         "zuidwest": "zw", "west": "w", "noordwest": "nw"}
    return M.get(s, s)


def _pv_bouwintegratie(s):
    s = (s or "").lower()
    if "niet" in s or "geïntegreerd" in s or "geintegreerd" in s: return "0"
    if "matig" in s: return "1"
    if "goed" in s or "sterk" in s: return "2"
    if "onbekend" in s: return "3"
    return None


def _wire_pv(node, pv, flags):
    """Zet een ZonneEnergie-knoop op basis van een dossier-PV-systeem (codes LIVE geharvest)."""
    syst = (getattr(pv, "systeem", "") or "").lower()
    sys_code = "1" if "pvt" in syst else ("2" if "zonneboiler" in syst else ("3" if "opslag" in syst else "0"))
    _set(node, "ZonneEnergiesysteem", sys_code)
    _set(node, "Naam", getattr(pv, "type", "") or getattr(pv, "systeem", "") or "PV-systeem")
    _set(node, "Merk", getattr(pv, "merk", ""))
    _set(node, "Type", getattr(pv, "type", ""))
    if getattr(pv, "installatiejaar", None):
        _set(node, "Installatiejaar", pv.installatiejaar)
    if sys_code == "0":  # PV-panelen: paneeltype/fabricagejaar/bouwintegratie
        _set(node, "PiekvermogenPVPanelen", _pv_paneeltype(getattr(pv, "pv_type", "")))
        _set(node, "FabricagejaarPVPanelen", _pv_fabricagejaar(getattr(pv, "fabricagejaar", "")))
        bw = _pv_bouwintegratie(getattr(pv, "bouwintegratie", ""))
        if bw is not None:
            _set(node, "Bouwintegratie", bw)
    aant = getattr(pv, "aantal", None)
    if aant:
        _set(node, "AantalPanelen", int(aant))
    opp = getattr(pv, "oppervlak_per_paneel_m2", None)
    if opp:
        _set(node, "OppervlakPaneel", "%.2f" % float(opp))
    hh = getattr(pv, "hellingshoek", None)
    if hh is not None:
        _set(node, "Hellingshoek", int(round(float(hh))))  # PV: rauwe graden, niet de dak-enum
    ori = _norm_orient(getattr(pv, "orientatie", ""))
    if ori in PV_ORIENTATIE:
        _set(node, "Orientatie", PV_ORIENTATIE[ori])
    elif (getattr(pv, "orientatie", "") or "").strip():
        flags.append("PV-oriëntatie '%s' niet enkelvoudig (oost-west/plat) -> in Vabi splitsen/zetten"
                     % getattr(pv, "orientatie", ""))


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _set(el, tag, value):
    if el is None or value in (None, ""):
        return
    c = el.find(tag)
    if c is not None:
        c.text = str(value)


def _find(root, tag):
    return next((e for e in root.iter() if _local(e.tag) == tag), None)


def build_tree(dos):
    root = ET.parse(TEMPLATE).getroot()
    flags = []
    vent = getattr(dos, "ventilatie", None)
    inst = getattr(dos, "installaties", None)

    # --- Ventilatie (betrouwbaarst uit MagicPlan; cruciaal voor Nij Begun) ---
    vnode = _find(root, "Ventilatie")
    if vnode is not None and vent is not None:
        soort = (getattr(vent, "systeem_soort", "") or "").lower()
        if soort in SYSTEEM_SOORT:
            _set(vnode, "Systeem", SYSTEEM_SOORT[soort])
        _set(vnode, "Merk", getattr(vent, "merk", ""))
        _set(vnode, "Type", getattr(vent, "type", ""))
        _set(vnode, "Installatiejaar", getattr(vent, "installatiejaar", None))
        # het ventilatiesysteem-type (A1/B2/C3...) zit als code in de sjabloon; alleen
        # overschrijven als we het zeker kunnen mappen -> anders sjabloon-default + flag
        sub = getattr(vent, "subsysteem_code", "") or ""
        if sub:
            flags.append("ventilatiesysteem '%s' uit sjabloon overgenomen; verifieer in Vabi" % sub)

    # --- Verwarming-opwekker: vrije tekst overschrijven indien dossier ze heeft ---
    verw = getattr(inst, "verwarming", None) if inst is not None else None
    op = _find(root, "VerwarmingOpwekker")
    if op is not None and verw is not None:
        if getattr(verw, "merk", ""):
            _set(op, "Merk", verw.merk)
        if getattr(verw, "type", ""):
            _set(op, "Type", verw.type)
        if getattr(verw, "installatiejaar", None):
            _set(op, "Installatiejaar", verw.installatiejaar)
        # bevestigde codes (LIVE geharvest): alleen schrijven wat zeker is; rest sjabloon + flag
        to = (getattr(verw, "type_opwekker", "") or "").lower()
        if to and "warmtepomp" not in to and "wkk" not in to and "biomassa" not in to \
                and ("ketel" in to or "hr10" in to or to.strip() in ("cr", "vr") or "gas" in to):
            _set(op, "TypeOpwekker", "4")  # Gasgestookte ketel
        elif to:
            flags.append("verwarming-opwekkertype '%s' (warmtepomp/WKK/biomassa/...) niet auto-gecodeerd "
                         "-> in Vabi zetten" % getattr(verw, "type_opwekker", ""))
        st = (getattr(verw, "subtype", "") or "").lower().replace(" ", "")
        if st in VERW_SUBTYPE:
            _set(op, "SubType", VERW_SUBTYPE[st])
        opl = (getattr(verw, "opstelplaats", "") or "").lower()
        if "binnen" in opl:
            _set(op, "OpstelplaatsOpwekker", "0")
        elif "buiten" in opl:
            _set(op, "OpstelplaatsOpwekker", "1")
        afg = (getattr(verw, "afgifte", "") or "").lower()
        if "lucht" in afg:
            _set(_find(root, "VerwarmingAfgifte") or op, "Afgiftesysteem", "3")  # enige LIVE-bevestigde afgiftecode
        elif afg:
            flags.append("afgiftesysteem '%s' nog niet auto-gecodeerd (alleen luchtverwarming bevestigd) "
                         "-> in Vabi zetten" % getattr(verw, "afgifte", ""))
        if not getattr(verw, "merk", "") and not getattr(verw, "type", ""):
            flags.append("verwarming uit sjabloon (geen dossier-data); adviseur vult aan in Vabi")

    # --- Tapwater-opwekker: idem ---
    tap = getattr(inst, "tapwater", None) if inst is not None else None
    top = _find(root, "TapwaterOpwekker")
    if top is not None and tap is not None:
        if getattr(tap, "merk", ""):
            _set(top, "Merk", tap.merk)
        if getattr(tap, "type", ""):
            _set(top, "Type", tap.type)
        if getattr(tap, "installatiejaar", None):
            _set(top, "Installatiejaar", tap.installatiejaar)
        # bevestigde codes
        ti = (getattr(tap, "type_installatie", "") or "").lower()
        if "individueel" in ti:
            _set(_find(root, "TapwaterInstallatie") or top, "TypeInstallatie", "0")
        tt = (getattr(tap, "type_toestel", "") or "").lower()
        if "combi" in tt:
            _set(top, "TypeToestel", "10")  # Gasgestookt combitoestel
        elif "compleet" in tt:
            _set(top, "TypeToestel", "2")
        elif tt:
            flags.append("tapwater-toestel '%s' nog niet auto-gecodeerd -> in Vabi zetten"
                         % getattr(tap, "type_toestel", ""))
        gk = (getattr(tap, "gaskeur", "") or "").lower()
        if "cw" in gk and "zonder" not in gk:
            _set(top, "Gaskeur", "3")  # Gaskeur CW
        ao = (getattr(tap, "aangesloten_op", "") or "").lower()
        if "hele woning" in ao or "woning" in ao:
            _set(top, "AangeslotenOp", "0")

    # --- Zonne-energie / PV (node LIVE geharvest uit EPA; codes in installatie_enums_EPA.md) ---
    ze_list = _find(root, "ZonneEnergieList")
    ze_node = _find(root, "ZonneEnergie")
    pv_systemen = list(getattr(inst, "zonne_energie", []) or []) if inst is not None else []
    if ze_node is not None and ze_list is not None:
        if not pv_systemen:
            ze_list.remove(ze_node)  # geen PV in dossier -> sjabloon-PV verwijderen (geen fantoom)
        else:
            for i, pv in enumerate(pv_systemen):
                node = ze_node if i == 0 else copy.deepcopy(ze_node)
                if i > 0:
                    ze_list.append(node)
                _wire_pv(node, pv, flags)

    # extra (2e/3e) verwarming/tapwater/koeling: alleen exemplaar 1 wordt gewired -> flaggen (golden rule:
    # een 2e opwekkernode niet blind klonen; de adviseur voegt 'm in Vabi toe). PV-lijst is wél volledig gewired.
    if inst is not None:
        n_extra = (len(getattr(inst, "verwarming_extra", []) or []) + len(getattr(inst, "tapwater_extra", []) or [])
                   + len(getattr(inst, "koeling_extra", []) or []))
        if n_extra:
            flags.append("%d extra installatie(s) in het dossier (hybride/2e toestel): alleen exemplaar 1 is "
                         "gewired -> voeg de extra opwekker(s) handmatig in Vabi toe." % n_extra)

    # installatie-naam
    inode = _find(root, "Installatie")
    if inode is not None:
        _set(inode, "Naam", "Installatie (uit MagicPlan-opname)")
    return root, flags


def write(dos, path):
    if not os.path.exists(TEMPLATE):
        raise FileNotFoundError("Installatie-sjabloon ontbreekt: %s" % TEMPLATE)
    root, flags = build_tree(dos)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    body = ET.tostring(root, encoding="utf-8")
    with open(path, "wb") as fh:
        fh.write(b'<?xml version="1.0" encoding="UTF-8"?>\n' + body)
    return flags


def main():
    root_dir = os.path.dirname(HERE)
    ap = argparse.ArgumentParser(description="Dossier -> importeerbare VABI Installatiebibliotheek")
    ap.add_argument("--dossier", required=True)
    ap.add_argument("--out", default=os.path.join(root_dir, "out", "Installatiebibliotheek.xml"))
    a = ap.parse_args()
    dos = load_json(a.dossier)
    flags = write(dos, a.out)
    print("OK: %s" % a.out)
    for f in flags:
        print("  ! " + f)
    print("  -> import in EPA: tegel Installaties > Importeren.")


if __name__ == "__main__":
    main()
