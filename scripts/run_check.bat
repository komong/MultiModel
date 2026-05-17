@echo off
copy /Y "d:\Desktop\Test\MultiModel\wsl_start.sh" "\\wsl.localhost\Ubuntu\tmp\wsl_start.sh" >nul
wsl -d Ubuntu -e bash -c "chmod +x /tmp/wsl_start.sh && bash /tmp/wsl_start.sh"
echo.
echo === 按任意键退出 ===
pause >nul