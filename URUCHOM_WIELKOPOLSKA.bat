@echo off
chcp 65001 >nul
title Most Digital — Agent Wielkopolska
echo.
echo  ================================================
echo   Most Digital — szukam leadow w Wielkopolsce...
echo  ================================================
echo.
cd /d "%~dp0"
python wielkopolska.py
