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
# audit 13-7: alleen 0=individueel is uit een echte EPA-export bevestigd voor Ventilatie/Systeem.
# collectief/gemeenschappelijk=1 is een dropdown-volgorde-AANNAME -> niet schrijven, wel flaggen.
SYSTEEM_SOORT = {"individueel": "0"}

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
    # audit 12-7: 'Voor 2018' (form-vocab) matchte op de substring '2018' -> code 4 = VANAF 2018 (fout).
    # 'Voor 2018' dekt meerdere EPA-brackets -> niet gokken: Onbekend + flag (in _wire_pv).
    if "voor 2018" in s or "<2018" in s: return "5"
    if "2001" in s: return "1"
    if "2011" in s: return "2"
    if "2015" in s or "2016" in s or "2017" in s: return "3"
    if "2018" in s or "vanaf" in s or "na 2018" in s: return "4"
    return "5"  # onbekend


def _pv_code(d, keuze, fallback=None):
    return d.get((keuze or "").strip().lower(), fallback)


# Verwarming: alleen HR107=4 is uit een echte EPA-export bevestigd. CR/VR/HR100/HR104 zijn
# dropdown-volgorde-AANNAMES op een CONDITIONELE sublijst (die globale codes kan hebben) -> audit
# 13-7: niet schrijven, wel flaggen (golden rule).
VERW_SUBTYPE = {"hr107": "4"}


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
        if "voor 2018" in (getattr(pv, "fabricagejaar", "") or "").lower():
            flags.append("PV-fabricagejaar 'Voor 2018' dekt meerdere EPA-klassen -> Onbekend gezet; "
                         "kies de juiste klasse in Vabi.")
        bw = _pv_bouwintegratie(getattr(pv, "bouwintegratie", ""))
        if bw is not None:
            _set(node, "Bouwintegratie", bw)
    aant = getattr(pv, "aantal", None)
    if aant:
        _set(node, "AantalPanelen", int(aant))
    else:
        flags.append("PV: aantal panelen ontbreekt -> sjabloonwaarde blijft staan; zet het aantal in Vabi.")
    if not (getattr(pv, "orientatie", "") or "").strip():
        flags.append("PV: oriëntatie ontbreekt -> sjabloonwaarde (Zuid) blijft staan; zet hem in Vabi.")
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
        elif soort:
            flags.append("ventilatie-systeemsoort '%s' niet EPA-bevestigd (alleen individueel) "
                         "-> sjabloon-default; zet 'm in Vabi." % getattr(vent, "systeem_soort", ""))
        _set(vnode, "Merk", getattr(vent, "merk", ""))
        _set(vnode, "Type", getattr(vent, "type", ""))
        _set(vnode, "Installatiejaar", getattr(vent, "installatiejaar", None))
        # het ventilatiesysteem-type (A1/B2/C3...) zit als code in de sjabloon; alleen
        # overschrijven als we het zeker kunnen mappen -> anders sjabloon-default + flag
        sub = getattr(vent, "subsysteem_code", "") or ""
        if sub:
            flags.append("ventilatiesysteem '%s' uit sjabloon overgenomen; verifieer in Vabi" % sub)
        if not (getattr(vent, "systeem", "") or "").strip():
            # audit 12-7: ventilatie is het ENIGE installatiedeel dat de Standaard beinvloedt —
            # leeg systeem mag nooit stil op de sjabloon-ventilatie blijven staan.
            flags.append("VENTILATIESYSTEEM ONTBREEKT in de opname -> sjabloon-ventilatie blijft "
                         "staan; zet het systeem (A-E) in Vabi (dit stuurt de Standaard!).")
    elif vnode is not None:
        flags.append("VENTILATIE ONTBREEKT volledig in het dossier -> sjabloon-ventilatie blijft "
                     "staan; vul de ventilatie in Vabi in (dit stuurt de Standaard!).")

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
        else:
            flags.append("verwarming-opwekkertype ONTBREEKT -> sjabloon (HR107-gasketel) blijft staan; "
                         "controleer in Vabi.")
        if not getattr(verw, "installatiejaar", None):
            flags.append("verwarming-installatiejaar ONTBREEKT -> sjabloonjaar blijft staan; zet het "
                         "echte jaar in Vabi.")
        st = (getattr(verw, "subtype", "") or "").lower().replace(" ", "")
        if st in VERW_SUBTYPE:
            _set(op, "SubType", VERW_SUBTYPE[st])
        elif st:
            flags.append("ketel-subtype '%s' niet EPA-bevestigd (alleen HR107) -> sjabloon-default; "
                         "zet de HR-klasse (CR/VR/HR100/HR104) zelf in Vabi." % getattr(verw, "subtype", ""))
        opl = (getattr(verw, "opstelplaats", "") or "").lower()
        if "binnen" in opl:
            _set(op, "OpstelplaatsOpwekker", "0")   # 0=binnen thermische zone: EPA-bevestigd
        elif "buiten" in opl:
            flags.append("opstelplaats 'buiten' niet EPA-bevestigd -> sjabloon-default; zet 'm in Vabi.")
        afg = (getattr(verw, "afgifte", "") or "").lower()
        if "lucht" in afg:
            _set(_find(root, "VerwarmingAfgifte") or op, "Afgiftesysteem", "3")  # enige LIVE-bevestigde afgiftecode
        elif afg:
            flags.append("afgiftesysteem '%s' nog niet auto-gecodeerd (alleen luchtverwarming bevestigd) "
                         "-> in Vabi zetten" % getattr(verw, "afgifte", ""))
        else:
            flags.append("AFGIFTESYSTEEM ONTBREEKT -> sjabloon-afgifte (LUCHTVERWARMING!) blijft staan; "
                         "zet het echte afgiftesysteem (radiatoren/vloer/...) in Vabi.")
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
            # audit 12-7: het échte jaarveld in de TapwaterOpwekker-node heet 'Jaar'
            # ('Installatiejaar' is daar een ongebruikt element) -> beide zetten.
            _set(top, "Jaar", tap.installatiejaar)
        else:
            flags.append("tapwater-installatiejaar ONTBREEKT -> sjabloonjaar blijft staan; zet het "
                         "echte jaar in Vabi.")
        # bevestigde codes
        ti = (getattr(tap, "type_installatie", "") or "").lower()
        if "individueel" in ti:
            _set(_find(root, "TapwaterInstallatie") or top, "TypeInstallatie", "0")
        tt = (getattr(tap, "type_toestel", "") or "").lower()
        if "combi" in tt:
            _set(top, "TypeToestel", "10")  # Gasgestookt combitoestel: EPA-bevestigd (globale code)
        elif tt:
            # audit 13-7: 'compleet'->TypeToestel=2 was FOUT ('Compleet toestel' is een TypeOpwekker-
            # waarde, niet TypeToestel; refs installatie_enums_EPA.md). Verwijderd -> flaggen.
            flags.append("tapwater-toestel '%s' niet EPA-bevestigd -> sjabloon-default; zet 't in Vabi."
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

    # KOELING (audit 12-7): de primaire koeling werd volledig genegeerd (geen write, geen flag).
    # Codes niet allemaal bevestigd -> niet gokken, wel LUID flaggen zodat de adviseur hem zet.
    koel = getattr(inst, "koeling", None) if inst is not None else None
    if koel is not None and (getattr(koel, "aanwezig", False) or (getattr(koel, "type_opwekker", "") or "").strip()):
        flags.append("KOELING aanwezig in de opname (%s) maar niet auto-gewired -> zet de koeling "
                     "handmatig in Vabi." % (getattr(koel, "type_opwekker", "") or "type onbekend"))

    # SJABLOON-VRIJE-TEKSTEN wissen (audit 12-7): opmerkingen van de sjabloonwoning ('Kelder behoort
    # tot thermische zone...', 'Wel MV box maar geen ventiel...') horen niet in andermans dossier.
    for e in root.iter():
        if _local(e.tag).endswith("Opmerkingen") and (e.text or "").strip():
            e.text = ""

    # vaste disclaimer: wat NIET uit het dossier komt, draagt sjabloonwaarden (energielabel-scope)
    flags.append("Installatie-details die de opname niet levert (merk/type/jaren/kwaliteits-"
                 "verklaringen/hulpenergie) dragen SJABLOONWAARDEN — voor Nij Begun telt alleen "
                 "de ventilatie; bij een energielabel ALLES nalopen in Vabi.")

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
