@echo off
title OCR Handwriting System
echo ================================================
echo   OCR Handwriting Recognition System
echo ================================================
echo.
echo Starting system, please wait...
echo.

python launcher.py

if %errorlevel% neq 0 (
    echo.
    echo Failed to start. Please check Python installation.
    echo Run: pip install -r requirements.txt
    pause
)