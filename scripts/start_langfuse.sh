#!/bin/bash
# 启动 Docker 守护进程（如果未运行）
if ! service docker status | grep -q "running"; then
    service docker start
fi

# 等待 Docker 就绪
sleep 2

# 启动 Langfuse
cd /tmp
docker compose -f langfuse-docker-compose.yml up -d

# 检查状态
echo "---"
docker compose -f langfuse-docker-compose.yml ps
echo "---"
echo "Langfuse should be available at http://localhost:3000"
