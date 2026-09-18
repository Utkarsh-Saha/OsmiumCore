@echo off
set "PROJECT_ROOT=U:\WRK2\OsmiumCore"

echo Starting FastAPI Backend...
start "OsmiumCore Backend" cmd /k "cd /d %PROJECT_ROOT% && call conda activate oc && python -m uvicorn Backend.app.main:app --reload --host 0.0.0.0 --port 8000"