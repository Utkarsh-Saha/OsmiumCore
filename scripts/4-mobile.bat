@echo off
set "MOBILE_ROOT=U:\WRK2\OsmiumCore\MobileApp"

echo Starting Mobile App (Expo)...
start "OsmiumCore Mobile App" cmd /k "cd /d %MOBILE_ROOT% && call conda activate oc && npx expo start"