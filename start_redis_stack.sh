#!/bin/bash

CONTAINER_NAME="redis-stack"
IMAGE="redis/redis-stack:latest"

# Check if container already exists
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  echo "Redis Stack container already exists."

  # Check if it's running
  if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Redis Stack is already running."
  else
    echo "Starting existing Redis Stack container..."
    docker start ${CONTAINER_NAME}
  fi
else
  echo "Creating new Redis Stack container..."
  docker run -d \
    --name ${CONTAINER_NAME} \
    -p 6379:6379 \
    -p 8001:8001 \
    redis/redis-stack:latest
fi
