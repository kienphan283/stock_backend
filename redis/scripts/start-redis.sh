#!/bin/bash

# Start Redis with custom configuration

REDIS_CONF="../config/redis.conf"

if [ ! -f "$REDIS_CONF" ]; then
    echo "❌ Redis configuration not found: $REDIS_CONF"
    exit 1
fi

echo "🚀 Starting Redis server..."
redis-server "$REDIS_CONF"
