@echo off
chcp 65001 >nul
title Most Digital — Agent Wroclaw
echo.
echo  ================================================
echo   Most Digital — szukam leadow we Wroclawiu...
echo  ================================================
echo.
cd /d "%~dp0"
python wroclaw.py
