@echo off
cd /d "%~dp0"
if not exist output\history mkdir output\history
echo ==== %date% %time% >> output\history\daily.log
".venv\Scripts\python.exe" run.py >> output\history\daily.log 2>&1
exit /b %errorlevel%
