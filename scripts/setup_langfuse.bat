@echo off
echo ========== Langfuse 启动脚本 ==========
echo.

:: 1. 复制文件到 WSL
echo [1/5] 复制 docker-compose 文件到 WSL ...
copy /Y "d:\Desktop\Test\MultiModel\model-tracing\langfuse-docker-compose.yml" "\\wsl.localhost\Ubuntu\tmp\langfuse-docker-compose.yml" >nul
copy /Y "d:\Desktop\Test\MultiModel\run_wsl.sh" "\\wsl.localhost\Ubuntu\tmp\run_wsl.sh" >nul
echo [OK]

:: 2. 设置执行权限
echo [2/5] 设置权限 ...
wsl -d Ubuntu -e chmod +x /tmp/run_wsl.sh
echo [OK]

:: 3. 检查 Docker
echo [3/5] 检查 Docker ...
wsl -d Ubuntu -e service docker status
echo.

:: 4. 启动脚本
echo [4/5] 开始拉取镜像并启动 Langfuse ...
echo 注意：如果提示 sudo 密码，请在弹窗中输入 WSL 账户密码
wsl -d Ubuntu -e sudo bash /tmp/run_wsl.sh

:: 5. 最终状态
echo.
echo [5/5] 验证 ...
wsl -d Ubuntu -e curl -sI --connect-timeout 5 http://localhost:3000
echo.

echo ========== 完成 ==========
pause
