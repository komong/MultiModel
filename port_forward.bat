@echo off
echo ========================================
echo  配置 WSL2 端口转发 (Langfuse :3000)
echo ========================================
echo.

:: 删除旧的转发规则
netsh interface portproxy delete v4tov4 listenport=3000 listenaddress=127.0.0.1 >nul 2>nul
netsh interface portproxy delete v4tov4 listenport=3001 listenaddress=127.0.0.1 >nul 2>nul
netsh interface portproxy delete v4tov4 listenport=5678 listenaddress=127.0.0.1 >nul 2>nul

:: 添加新的转发规则（指向当前 WSL IP: 172.31.220.236）
netsh interface portproxy add v4tov4 listenport=3000 listenaddress=127.0.0.1 connectport=3000 connectaddress=172.31.220.236
netsh interface portproxy add v4tov4 listenport=3001 listenaddress=127.0.0.1 connectport=3001 connectaddress=172.31.220.236
netsh interface portproxy add v4tov4 listenport=5678 listenaddress=127.0.0.1 connectport=5678 connectaddress=172.31.220.236

echo.
echo === 当前转发规则 ===
netsh interface portproxy show all

echo.
echo ========================================
echo  配置完成！尝试访问 http://localhost:3000
echo ========================================
pause
