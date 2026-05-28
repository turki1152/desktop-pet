@echo off
REM Launch the Desktop Pet with no console window using pythonw.
REM Double-click this file to start your pet.
cd /d "%~dp0"
start "" pythonw main.py
