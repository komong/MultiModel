#!/bin/bash
# 为 LiteLLM 准备 PostgreSQL 数据库
# 1. 给 langfuse-db 添加端口映射（如果尚未添加）
# 2. 创建 litellm 数据库

set -e

echo "=== 检查 langfuse-db 端口映射 ==="

# 检查是否已经有端口映射
PORT_MAPPED=$(docker port langfuse-db 2>/dev/null | grep 5432 || true)
if [ -z "$PORT_MAPPED" ]; then
    echo "langfuse-db 未映射 5432 端口，正在更新 compose 配置..."

    COMPOSE_FILE="/tmp/langfuse-docker-compose.yml"
    if [ ! -f "$COMPOSE_FILE" ]; then
        echo "错误: 找不到 $COMPOSE_FILE"
        exit 1
    fi

    # 备份原文件
    cp "$COMPOSE_FILE" "${COMPOSE_FILE}.bak"

    # 在 langfuse-db 服务中添加 ports 映射
    # 使用 sed 在 "langfuse-db:" 之后的 "image:" 行前插入 ports
    sed -i '/^  langfuse-db:/,/^  [a-z]/{/image:/i\    ports:\n      - "5432:5432"
}' "$COMPOSE_FILE"

    echo "端口映射已添加，重启 langfuse-db 容器..."
    cd /tmp
    docker compose -f langfuse-docker-compose.yml up -d langfuse-db
else
    echo "langfuse-db 已有端口映射: $PORT_MAPPED"
fi

echo ""
echo "=== 等待 PostgreSQL 就绪 ==="
for i in $(seq 1 30); do
    if docker exec langfuse-db pg_isready -U langfuse > /dev/null 2>&1; then
        echo "PostgreSQL 已就绪"
        break
    fi
    echo "等待中... ($i/30)"
    sleep 1
done

echo ""
echo "=== 创建 litellm 数据库 ==="
# 检查数据库是否已存在
DB_EXISTS=$(docker exec langfuse-db psql -U langfuse -tAc "SELECT 1 FROM pg_database WHERE datname='litellm'" 2>/dev/null || echo "")
if [ "$DB_EXISTS" = "1" ]; then
    echo "litellm 数据库已存在，跳过创建"
else
    docker exec langfuse-db psql -U langfuse -c "CREATE DATABASE litellm;"
    echo "litellm 数据库创建成功"
fi

echo ""
echo "=== 验证 ==="
docker exec langfuse-db psql -U langfuse -l | grep litellm
echo ""
echo "完成! LiteLLM 可使用的数据库连接串:"
echo "  DATABASE_URL=postgresql://langfuse:langfuse@localhost:5432/litellm"
