"""Harde dossiercontroles die moeten slagen voordat Vabi-export wordt geschreven."""


class VabiExportBlocked(ValueError):
    """Het dossier mag inhoudelijk niet als rekenbare Vabi-set worden geëxporteerd."""


def assert_no_schil_kwaliteitsverklaring(dos):
    """Blokkeer alleen de expliciete kwaliteitsverklaring voor een schildeel."""
    ids = [str(getattr(s, "id", "") or "(zonder id)") for s in dos.schil
           if (getattr(s, "rc_bron", "") or "").strip().casefold()
           == "kwaliteitsverklaring".casefold()]
    if ids:
        raise VabiExportBlocked(
            "VABI-export geblokkeerd: kwaliteitsverklaring geselecteerd voor "
            "schildeel/schildelen %s. Verwerk de kwaliteitsverklaring eerst correct "
            "in Vabi; de tool exporteert hiervoor geen rekenbare forfaitaire fallback."
            % ", ".join(ids)
        )
