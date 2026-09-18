@echo off
set "AGENT_ROOT=U:\WRK2\OsmiumCore\Backend"

echo Starting LiveKit Agent...
start "OsmiumCore LiveKit Agent" cmd /k "cd /d %AGENT_ROOT% && call conda activate oc && python -m agent.main dev"