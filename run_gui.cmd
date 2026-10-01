@echo off
setlocal
cd /d "%~dp0"
py -3 run_gui.py
if errorlevel 1 pause
