@echo off
echo === 启动 Langfuse (WSL Docker) ===

:: 复制 docker-compose 到 WSL
copy /Y "d:\Desktop\Test\MultiModel\model-tracing\langfuse-docker-compose.yml" "\\wsl.localhost\Ubuntu\tmp\langfuse-docker-compose.yml" >nul
echo [OK] 文件已复制到 WSL /tmp/

:: 在 WSL 中运行
wsl -d Ubuntu -e bash /tmp/start_langfuse.sh

echo.
echo === 按任意键退出 ===
pause >nul
