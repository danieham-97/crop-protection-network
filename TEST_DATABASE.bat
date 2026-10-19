@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto try_python
py -3 seed-treatment-database\test_project.py
pause
exit /b
:try_python
where python >nul 2>nul
if errorlevel 1 goto missing
python seed-treatment-database\test_project.py
pause
exit /b
:missing
echo Install Python 3.11 or newer from https://www.python.org/downloads/
pause
