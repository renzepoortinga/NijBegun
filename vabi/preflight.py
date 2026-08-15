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


def assert_no_dubbel_dak_fallback(dos):
    """Taak 014: de parser-placeholder ('magicplan-dak-fallback' — een footprint-schatting die
    ontstaat zolang een dossier geen enkel écht dakvlak heeft, zie statistics_csv.build_dossier)
    telt het dak dubbel als hij naast een écht (webapp-wizard of legacy-CSV) dakvlak blijft staan.
    De webapp verwijdert 'm automatisch zodra je een dakvlak toevoegt (dashboard.app.
    _dak_fallback_opschonen); deze poort is het vangnet voor elk ANDER pad naar een Vabi-export
    (CLI, JSON-upload, handmatig samengestelde dossiers, tests) waar die opschoning niet draait."""
    fallback_ids = {id(s) for s in dos.schil if getattr(s, "type", "") == "dak"
                    and getattr(s, "bron", "") == "magicplan-dak-fallback"}
    if not fallback_ids:
        return
    andere = [s for s in dos.schil if getattr(s, "type", "") == "dak" and id(s) not in fallback_ids]
    if not andere:
        return
    fallback = [s for s in dos.schil if id(s) in fallback_ids]
    raise VabiExportBlocked(
        "VABI-export geblokkeerd: er staat nog een placeholder-dak ('%s', %.2f m² footprint-"
        "schatting, geen meting) naast %d ander(e) dakvlak(ken) — samen zou dat dakoppervlak "
        "dubbel meetellen. Verwijder het placeholder-dak (via de webapp-dakwizard gebeurt dit "
        "automatisch bij het toevoegen van een dakvlak) voordat je exporteert."
        % (fallback[0].id or "dak", sum(s.oppervlakte_m2 or 0 for s in fallback), len(andere))
    )
