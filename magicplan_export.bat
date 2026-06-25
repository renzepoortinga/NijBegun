@echo off
REM Haalt een MagicPlan-opname op via de API -> out\plan_raw.json + out\dossier_from_magicplan.json
cd /d "%~dp0"
echo === Stap 1: auth-check (workspace) ===
python magicplan\extractor.py --test
echo.
echo === Stap 2: project ophalen ===
set /p PID="Plak het MagicPlan project-ID en druk Enter: "
python magicplan\extractor.py --project-id %PID%
echo.
echo Klaar. Als het gelukt is staat out\plan_raw.json klaar - laat het de assistent weten.
pause
