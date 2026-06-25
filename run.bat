@echo off
REM Sleep een VABI-monitoringbestand (.xml) op dit bestand, of dubbelklik en kies.
cd /d "%~dp0"
if "%~1"=="" (
  set /p XML="Pad naar VABI monitoringbestand (.xml): "
) else (
  set XML=%~1
)
python run.py --from-monitor "%XML%"
pause
