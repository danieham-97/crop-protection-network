@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto try_python
py -3 seed-treatment-database\serve.py
if errorlevel 1 pause
exit /b
:try_python
where python >nul 2>nul
if errorlevel 1 goto missing
python seed-treatment-database\serve.py
if errorlevel 1 pause
exit /b
:missing
echo Install Python 3.11 or newer from https://www.python.org/downloads/
echo Or open seed-treatment-database\CPN_Seed_Treatment_Preview.html without installing anything.
pause
