@echo off
echo Starting Bank Reconciliation System...

:: 确保当前目录为 BANK
cd /d "%~dp0System"

:: 运行 app.py
streamlit run app.py

pause