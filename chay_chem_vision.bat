@echo off
chcp 65001 >nul
cd /d "%~dp0"
python -m chem_vision %*
if errorlevel 1 pause
