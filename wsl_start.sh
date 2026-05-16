#!/bin/bash
# WSL启动自启脚本
# 启动 Docker
service docker start 2>/dev/null
sleep 2

# 启动 Langfuse
cd /tmp
docker compose -f langfuse-docker-compose.yml up -d 2>&1