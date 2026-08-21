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
- [ ] PDF bevat elke verdieping met markers en waarden, leesbaar op A4.
- [ ] Tabellen zijn identiek aan het scherm, inclusief afvoerpunt en vuistregelstatus.
- [ ] Export draait offline op de VPS zonder handmatige stap.
- [ ] PNG per verdieping heeft transparante of witte achtergrond en is bruikbaar in Word.
- [ ] Dossier zonder plattegrond geeft een nette melding, geen lege pagina.
- [ ] `./scripts/verify.sh` slaagt.
- [ ] AI-review PASS door een andere agent dan de bouwer.

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

## Notes
Het aantal pagina's is variabel: voorblad + één pagina per verdieping + berekeningspagina.
