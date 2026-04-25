@echo off
cd /d %~dp0
git add .
git commit -m "Manual Update"
git push origin master:main --force
pause