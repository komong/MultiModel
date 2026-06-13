#!/bin/bash
# Start a standalone PostgreSQL container for LiteLLM on port 5433
set -e

CONTAINER_NAME="litellm-postgres"
PORT=5433
USER="litellm"
PASS="litellm123"
DB="litellm"

echo "=== Starting LiteLLM PostgreSQL on port $PORT ==="

# Remove old container if exists
docker rm -f $CONTAINER_NAME 2>/dev/null || true

# Start new container
docker run -d \
  --name $CONTAINER_NAME \
  -e POSTGRES_USER=$USER \
  -e POSTGRES_PASSWORD=$PASS \
  -e POSTGRES_DB=$DB \
  -p $PORT:5432 \
  -v litellm_pg_data:/var/lib/postgresql/data \
  postgres:15-alpine

echo "=== Waiting for PostgreSQL to be ready ==="
for i in $(seq 1 30); do
  if docker exec $CONTAINER_NAME pg_isready -U $USER > /dev/null 2>&1; then
    echo "PostgreSQL ready!"
    break
  fi
  sleep 1
done

echo ""
echo "=== Connection Info ==="
echo "DATABASE_URL=postgresql://$USER:$PASS@localhost:$PORT/$DB"
echo ""
echo "Add this to your .env file"
