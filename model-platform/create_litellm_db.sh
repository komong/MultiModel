#!/bin/bash
# 在 langfuse-db 容器内创建 litellm 数据库
# 使用 5433 端口映射避免与已占用的 5432 冲突

# 找到正在运行的 postgres 容器名
DB_CONTAINER=$(docker ps --filter "ancestor=postgres:15" --format "{{.Names}}" | head -1)
if [ -z "$DB_CONTAINER" ]; then
    echo "错误: 找不到运行中的 postgres:15 容器"
    echo "尝试查找任何 postgres 容器..."
    DB_CONTAINER=$(docker ps --filter "name=postgres" --format "{{.Names}}" | head -1)
fi

if [ -z "$DB_CONTAINER" ]; then
    echo "错误: 没有找到任何运行中的 postgres 容器"
    exit 1
fi

echo "使用容器: $DB_CONTAINER"

# 创建 litellm 数据库（如果不存在）
DB_EXISTS=$(docker exec "$DB_CONTAINER" psql -U langfuse -tAc "SELECT 1 FROM pg_database WHERE datname='litellm'" 2>/dev/null || echo "")
if [ "$DB_EXISTS" = "1" ]; then
    echo "litellm 数据库已存在"
else
    docker exec "$DB_CONTAINER" psql -U langfuse -c "CREATE DATABASE litellm;"
    echo "litellm 数据库创建成功"
fi

# 显示所有数据库
echo ""
echo "=== 数据库列表 ==="
docker exec "$DB_CONTAINER" psql -U langfuse -l

# 检查当前端口映射
echo ""
echo "=== 容器端口映射 ==="
docker port "$DB_CONTAINER" 2>/dev/null || echo "无端口映射"

# 如果没有 5432 映射，提示需要用 docker network
echo ""
echo "=== 连接信息 ==="
echo "如果端口未映射，Windows 端需通过以下方式连接："
echo "  1. 直接在此容器网络内执行 SQL"
echo "  2. 或使用 host.docker.internal"
