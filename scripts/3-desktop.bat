@echo off
set "DESKTOP_ROOT=U:\WRK2\OsmiumCore\DesktopClient"

echo Starting Desktop Frontend...
start "OsmiumCore Desktop Client" cmd /k "cd /d %DESKTOP_ROOT% && call conda activate oc && npm run dev"