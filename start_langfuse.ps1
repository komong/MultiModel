# Start Langfuse in WSL (Docker)
# 在 PowerShell (非 IDE 终端) 中运行此脚本

Write-Host "=== 启动 Langfuse (WSL Docker) ===" -ForegroundColor Cyan

# 1. 复制 docker-compose 文件到 WSL
$src = "d:\Desktop\Test\MultiModel\model-tracing\langfuse-docker-compose.yml"
$dst = "\\wsl.localhost\Ubuntu\tmp\langfuse-docker-compose.yml"
Copy-Item $src $dst -Force
Write-Host "[OK] 文件已复制到 WSL /tmp/" -ForegroundColor Green

# 2. 启动 Docker 并运行 Langfuse
wsl -d Ubuntu -- bash -c @"
# 启动 Docker（如果未运行）
if ! service docker status | grep -q "running"; then
    sudo service docker start 2>/dev/null
    sleep 2
fi
echo '[OK] Docker 已就绪'

# 启动 Langfuse
cd /tmp
docker compose -f langfuse-docker-compose.yml pull
docker compose -f langfuse-docker-compose.yml up -d

echo ''
echo '--- 容器状态 ---'
docker compose -f langfuse-docker-compose.yml ps
echo '---'
echo 'Langfuse 启动完成！访问 http://localhost:3000'
"@

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n=== 完成 ===" -ForegroundColor Cyan
    Write-Host "浏览器打开 http://localhost:3000 即可访问 Langfuse" -ForegroundColor Yellow
} else {
    Write-Host "`n=== 执行出错 ===" -ForegroundColor Red
    Write-Host "请在 WSL 中手动执行：" -ForegroundColor Yellow
    Write-Host "  cd /tmp && docker compose -f langfuse-docker-compose.yml up -d" -ForegroundColor White
}
