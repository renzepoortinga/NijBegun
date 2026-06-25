@echo off
REM MagicPlan custom-forms bijwerken vanuit code (additions.json). Vereist internet + .env in de repo-root
REM met MAGICPLAN_API_KEY en MAGICPLAN_CUSTOMER_ID. IDEMPOTENT: veilig om opnieuw te draaien.
setlocal
cd /d "%~dp0.."

echo === STAP 1: DRY-RUN (haalt de forms op, toont wat er zou veranderen; wijzigt NIETS) ===
python magicplan\form_push.py --live
if errorlevel 1 (
  echo.
  echo Er zijn validatieproblemen of een fout. NIET publiceren. Sluit af.
  pause
  exit /b 1
)

echo.
echo Controleer hierboven welke velden worden toegevoegd. De gemergede JSON's staan in out\forms_merged\.
echo Druk op een toets om DAADWERKELIJK te publiceren naar MagicPlan, of sluit dit venster om te annuleren.
pause

echo === STAP 2: PUBLICEREN ===
python magicplan\form_push.py --live --publish
echo.
echo Klaar. Open MagicPlan en controleer de forms. (Maak eerst een proefopname voor je het in productie gebruikt.)
pause
