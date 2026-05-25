@echo off
copy /Y "d:\Desktop\Test\MultiModel\scripts\check_docker.sh" "\\wsl.localhost\Ubuntu\tmp\check_docker.sh" >nul
wsl -d Ubuntu -e bash -c "chmod +x /tmp/check_docker.sh && bash /tmp/check_docker.sh"
echo.
echo === 按任意键退出 ===
pause >nul
