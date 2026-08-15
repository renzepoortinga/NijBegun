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


def dak_fallback_schildelen(schil):
    """Herken de dak-footprint-placeholder (taak 014/015): de expliciete `bron`-tag
    ('magicplan-dak-fallback') EN, voor dossiers van vóór dat veld bestond (o.a. het live
    Essenhage-project dat deze taak aanleiding gaf — die stond al op schijf toen de tag werd
    toegevoegd en heeft dus bron==""), het legacy-signaal `id == "dak"` — MITS `bron` nog leeg is.
    Die kale id is UNIEK voor de twee footprint-fallback-code-paden (statistics_csv.build_dossier +
    extractor._maak_dak) — de dak-wizard nummert altijd ('dak1-...'), en de oudere expliciete
    CSV-dakvelden-route gebruikt ook altijd een gesuffixte id ('dak-plat', 'dak-vlak1-zw', ...).
    Een NIET-lege, niet-fallback `bron` (bv. "magicplan-import", zoals `opname_dakkapel` zet
    zodra een adviseur een placeholder bewust als moederdak kiest en aanpast) wint altijd van het
    id-signaal — anders zou het id-vangnet voor legacy-dossiers een bewust behouden, verkleind maar
    nog altijd écht dakvlak alsnog als weggooibare placeholder blijven behandelen.
    Gedeeld door `dashboard.app._dak_fallback_opschonen` en `assert_no_dubbel_dak_fallback` zodat
    beide precies dezelfde definitie van "dit is de placeholder" gebruiken."""
    def _is_fallback(s):
        bron = getattr(s, "bron", "")
        if bron:
            return bron == "magicplan-dak-fallback"
        return getattr(s, "id", "") == "dak"
    return [s for s in schil if getattr(s, "type", "") == "dak" and _is_fallback(s)]


def assert_no_dubbel_dak_fallback(dos):
    """Taak 014: de parser-placeholder (zie `dak_fallback_schildelen`) telt het dak dubbel als hij
    naast een écht (webapp-wizard of legacy-CSV) dakvlak blijft staan. De webapp verwijdert 'm
    automatisch zodra je een dakvlak toevoegt (dashboard.app._dak_fallback_opschonen); deze poort
    is het vangnet voor elk ANDER pad naar een Vabi-export (CLI, JSON-upload, handmatig
    samengestelde dossiers, tests) waar die opschoning niet draait."""
    fallback = dak_fallback_schildelen(dos.schil)
    if not fallback:
        return
    fallback_ids = {id(s) for s in fallback}
    andere = [s for s in dos.schil if getattr(s, "type", "") == "dak" and id(s) not in fallback_ids]
    if not andere:
        return
    raise VabiExportBlocked(
        "VABI-export geblokkeerd: er staat nog een placeholder-dak ('%s', %.2f m² footprint-"
        "schatting, geen meting) naast %d ander(e) dakvlak(ken) — samen zou dat dakoppervlak "
        "dubbel meetellen. Verwijder het placeholder-dak (via de webapp-dakwizard gebeurt dit "
        "automatisch bij het toevoegen van een dakvlak) voordat je exporteert."
        % (fallback[0].id or "dak", sum(s.oppervlakte_m2 or 0 for s in fallback), len(andere))
    )
