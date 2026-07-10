@echo off
cd /d C:\Users\56967\Desktop\openClode\securecode
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
