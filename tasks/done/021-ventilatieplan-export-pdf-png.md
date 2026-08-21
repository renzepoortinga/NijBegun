---
id: 021
assigned: Codex Builder
branch: feat/021-ventilatieplan-export
depends_on: [020]
---

# Task 021 — Ventilatieplan exporteren als PDF en PNG

## Goal
De adviseur levert het ventilatieplan af als een PDF die bewoner en installateur zonder uitleg
begrijpen, plus losse PNG's voor gebruik in het isolatieplan.

## Scope
- Knop "Download ventilatieplan (PDF)" op de ventilatieplanpagina en per verdieping
  "Download plan (PNG)".
- PDF: voorblad met adres, datum, ventilatiesysteem en balans; één pagina per verdieping met
  tekening; slotpagina Berekening met beide tabellen, balansregel en aandachtspunten.
- Voettekst op elke pagina: indicatief ventilatieplan op basis van Nij Begun-vuistregels (BBL),
  geen rechten; plus "Pagina X / N".
- Onder elke tekening de herkomst van de plattegrond (MagicPlan-opname, datum).
- Bestandsnaam met adres-slug zoals bestaande dossierexports.

## Out of scope
- Nieuwe zware dependency zonder expliciet akkoord. Gebruik bestaande projectdependencies en
  offline routes.
- De tekening inhoudelijk veranderen: scherm en export gebruiken dezelfde brondata/rendering.

## Acceptance criteria
- [x] PDF bevat elke verdieping met markers en waarden, leesbaar op A4.
- [x] Tabellen zijn identiek aan het scherm, inclusief afvoerpunt en vuistregelstatus.
- [x] Export draait offline op de VPS zonder handmatige stap.
- [x] PNG per verdieping heeft transparante of witte achtergrond en is bruikbaar in Word.
- [x] Dossier zonder plattegrond geeft een nette melding, geen lege pagina.
- [x] `./scripts/verify.sh` slaagt.
- [x] AI-review PASS door een andere agent dan de bouwer.

## Sessions

- 2026-08-21 Codex Manager: bestaand lokaal taakontwerp geclaimd nadat taak 020 via PR 21 op
  `main` is gemerged; eigen schone worktree vanaf actuele main aangemaakt.
- 2026-08-21 Codex Builder: dependencyvrije exportlaag gebouwd op de gedeelde `_vp_context`-scene:
  login-beveiligde PDF- en per-verdieping-PNG-routes, veilige adres-/verdiepingsslugs, A4-voorblad,
  vloerpagina's, berekenpagina, herkomst en paginavoeten. PDF is met pypdf structureel en inhoudelijk
  gecontroleerd (variabel paginatal/tekst); PNG's zijn op signature, 1200x900-IHDR en visueel
  gecontroleerd. Poppler (`pdfinfo`/`pdftoppm`) was niet geïnstalleerd op deze Windows-runner, dus
  PDF-rasterinspectie daarmee kon niet worden uitgevoerd; de in de PDF ingebedde, identieke
  vloer-rastering is rechtstreeks geïnspecteerd. Leegte-, auth-, route-, offline- en inhoudstests
  toegevoegd. `scripts/verify.sh` via Git Bash: PASS, 967/967 tests. Review staat nog open.
- 2026-08-21 Codex Builder: gerebased op de nieuwste `origin/main` (inclusief parallel afgeronde
  taken 020/023), zonder conflicten. Gericht gezocht naar `pdftoppm.exe`/`pdfinfo.exe` via PATH en
  de lokale Codex PDF-runtime; niet aanwezig. De eerste post-rebase verify-run rapporteerde één
  niet-zichtbaar/transiënt testfalen; een directe volledige testrun was 973/973 groen en de daarop
  volgende blocking `scripts/verify.sh` was PASS (973/973). Geen bronwijziging nodig.
- 2026-08-21 Codex Builder: review-FAIL verwerkt. Lokale achtergronden worden nu tegen de echte
  projectmap geresolved (remote/absoluut/traversal/te groot geweigerd) en 8-bit RGB/RGBA-PNG wordt
  met stdlib inclusief alle PNG-filters gedecodeerd en in exact hetzelfde vloerbeeld voor PNG én
  PDF gecomposited; tests bewijzen identieke rode bronpixels in beide. Marker-vorm, kleur, 0/90°-
  rotatie en 0,75 auto-opacity zijn gelijkgetrokken met het scherm; capaciteit blijft op scherm en
  export horizontaal leesbaar. Berekening pagineert na werkelijk gewrapte regels; 90 ruimtes plus
  15 lange aandachtspunten bewijzen variabel paginatal, laatste-regelgrens en iedere X/N-footer.
  PNG/marker-preview visueel gecontroleerd; blocking verify PASS, 983/983. **Open dependencykeuze:**
  JPEG-decodering kan niet robuust met stdlib; PIL/Pillow, cv2, imageio en Wand zijn niet geïnstalleerd
  en `make_icons.py` documenteert bewust dat Pillow niet op de VPS staat. Twee keer expliciet om
  managerakkoord voor Pillow gevraagd zonder antwoord; JPEG faalt daarom nu luid met instructie PNG
  te gebruiken, in plaats van een witte/onjuiste export te leveren.
- 2026-08-21 Codex Builder: reviewer bevestigt dat achtergrondresolutie, markersemantiek en dynamische
  paginering zijn hersteld; enig resterend acceptatieblok is JPEG-ondersteuning. Daarbij blijft het
  expliciete risico dat de stdlib-decoder palette-, grayscale- en interlaced PNG niet ondersteunt.
  Branch op nieuwste `origin/main` inclusief taak 016 gerebased (STATE-conflict inhoudelijk opgelost,
  beide statussen behouden). Renderfouten van zulke PNG-varianten worden nu op PDF als leesbare flash
  + redirect en op PNG als HTTP 422 afgehandeld, nooit als 500; beide routes hebben regressietests.
  Blocking verify na rebase: PASS, 1020/1020 tests. Taak blijft daarom `active/` en de
  JPEG-acceptatiecheckbox blijft open tot de dependencykeuze.
- 2026-08-21 Codex Builder: manager heeft `Pillow>=10` expliciet toegestaan en gemotiveerd: een
  onderhouden decoder is nodig voor veilige scherm/exportpariteit en upstream PNG-normalisatie is
  nog niet beschikbaar. Dependency toegevoegd aan `requirements.txt` en `pyproject.toml`; de eigen
  beperkte PNG-decoder vervangen door een begrensde Pillow-decode (maximaal 30 miljoen pixels,
  maximaal 25 MB bronbestand). JPEG en palette-, grayscale- en geldige Adam7-interlaced PNG zijn
  via de echte routes getest; JPEG-bronpixels zijn in zowel losse PNG als ingebed PDF-beeld bewezen.
  Blocking verify PASS, 1020/1020. Alle inhoudelijke acceptatiecriteria zijn afgevinkt; alleen de
  onafhankelijke herreview staat nog open.
- 2026-08-21 onafhankelijke Reviewer (andere leverancier): VERDICT PASS op `e00d710`. JPEG en alle
  gevraagde PNG-varianten renderen via echte routes en zijn in PNG/PDF aangetoond; traversal-, 25 MB-
  en 30 miljoen-pixelgrenzen, foutafhandeling, dependency-packaging, markersemantiek en paginering
  zijn intact. Eigen blocking verify eveneens PASS, 1020/1020; geen advisories. Enige niet-blokkerende
  documentatienit (`dependencyvrij`) direct gecorrigeerd naar `offline`.

## Notes
Het aantal pagina's is variabel: voorblad + één pagina per verdieping + berekeningspagina.
