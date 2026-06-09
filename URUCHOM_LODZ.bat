@echo off
chcp 65001 >nul
title Most Digital — Agent Lodz
echo.
echo  ================================================
echo   Most Digital — szukam leadow w Lodzi...
echo  ================================================
echo.
cd /d "%~dp0"
python lodz.py
