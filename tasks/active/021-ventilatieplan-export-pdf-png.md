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

## Notes
Het aantal pagina's is variabel: voorblad + één pagina per verdieping + berekeningspagina.
