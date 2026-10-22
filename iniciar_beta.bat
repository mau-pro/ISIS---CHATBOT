@echo off
rem Doble clic para poner I-SIS en linea durante la prueba beta
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\iniciar_beta.ps1"
pause
