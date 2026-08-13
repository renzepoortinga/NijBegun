"""Harde dossiercontroles die moeten slagen voordat Vabi-export wordt geschreven."""
from core.dossier import is_bcrg_isolatiekeuze


class VabiExportBlocked(ValueError):
    """Het dossier mag inhoudelijk niet als rekenbare Vabi-set worden geëxporteerd."""


def is_kwaliteitsverklaring(s):
    """Alleen de expliciete MagicPlan-isolatiekeuze activeert deze route."""
    return is_bcrg_isolatiekeuze(getattr(s, "isolatie_aanwezig", ""))


def assert_complete_schil_kwaliteitsverklaring(dos):
    """Een expliciete kwaliteitsverklaring vereist code én positieve dikte."""
    legacy = [str(getattr(s, "id", "") or "(zonder id)") for s in dos.schil
              if not is_kwaliteitsverklaring(s)
              and (getattr(s, "rc_bron", "") or "").strip().casefold() == "kwaliteitsverklaring"]
    if legacy:
        raise VabiExportBlocked(
            "VABI-export geblokkeerd: legacy kwaliteitsverklaring zonder de nieuwe expliciete "
            "isolatiekeuze voor %s. Kies 'Ja — kwaliteitsverklaring' en vul BCRG-code+dikte in; "
            "er wordt geen forfaitaire fallback gemaakt." % ", ".join(legacy)
        )
    ontbreekt_code, ontbreekt_dikte = [], []
    for s in dos.schil:
        if not is_kwaliteitsverklaring(s):
            continue
        sid = str(getattr(s, "id", "") or "(zonder id)")
        if not (getattr(s, "bcrg_code", "") or "").strip():
            ontbreekt_code.append(sid)
        try:
            geldig = float(getattr(s, "isolatiedikte_mm", None)) > 0
        except (TypeError, ValueError):
            geldig = False
        if not geldig:
            ontbreekt_dikte.append(sid)
    fouten = []
    if ontbreekt_code:
        fouten.append("BCRG-code ontbreekt voor %s" % ", ".join(ontbreekt_code))
    if ontbreekt_dikte:
        fouten.append("isolatiedikte ontbreekt voor %s" % ", ".join(ontbreekt_dikte))
    if fouten:
        raise VabiExportBlocked(
            "VABI-export geblokkeerd: kwaliteitsverklaring is niet compleet: %s. "
            "Vul de ontbrekende gegevens in; er wordt geen forfaitaire fallback gemaakt."
            % "; ".join(fouten)
        )


# Compatibele importnaam voor bestaande aanroepers; gedrag is aangescherpt naar compleetheidscontrole.
assert_no_schil_kwaliteitsverklaring = assert_complete_schil_kwaliteitsverklaring
