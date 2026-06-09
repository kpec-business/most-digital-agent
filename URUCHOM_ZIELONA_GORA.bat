@echo off
chcp 65001 >nul
title Most Digital — Agent Zielona Gora
echo.
echo  ================================================
echo   Most Digital — szukam leadow w Zielonej Gorze...
echo  ================================================
echo.
cd /d "%~dp0"
python zielona_gora.py
