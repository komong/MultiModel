#!/bin/bash
echo "=== Docker PS ==="
docker ps -a --format "table {{.Names}}	{{.Status}}	{{.Ports}}"
echo ""
echo "=== WSL IP ==="
ip addr show eth0 | grep inet
echo ""
echo "=== Listen 3000 ==="
ss -tlnp | grep 3000 || echo "Nothing on 3000"
echo ""
echo "=== iptables ==="
iptables -L DOCKER -n 2>/dev/null | head -20 || echo "no iptables"