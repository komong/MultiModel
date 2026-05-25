#!/bin/bash
echo "=== Docker 容器状态 ==="
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>&1
echo ""
echo "=== 镜像列表 ==="
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" 2>&1
