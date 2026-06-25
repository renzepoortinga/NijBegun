@echo off
REM Tast meerdere API-endpoints af om te vinden welke de form-antwoorden bevat.
cd /d "%~dp0"
set /p PID="Plak het MagicPlan project-ID en druk Enter: "
python magicplan\extractor.py --probe --project-id %PID%
echo.
echo Klaar. Stuur de assistent welke regel "FORM-ANTWOORDEN!" toont (of de hele lijst).
pause
