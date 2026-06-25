@echo off
REM Start het lokale Nij Begun & EPA dashboard. Dubbelklik en open daarna de browser.
cd /d "%~dp0"
echo Dashboard start op http://127.0.0.1:5000  (laat dit venster open; Ctrl+C om te stoppen)
python dashboard\app.py
pause
