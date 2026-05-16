#!/bin/bash
cd /tmp
echo "=== Docker ==="
service docker status
echo "=== Start ==="
sudo service docker start
sleep 2
echo "=== Pull ==="
docker compose -f langfuse-docker-compose.yml pull
echo "=== Up ==="
docker compose -f langfuse-docker-compose.yml up -d
echo "=== PS ==="
docker compose -f langfuse-docker-compose.yml ps
ip addr show eth0 2>/dev/null | grep inet
