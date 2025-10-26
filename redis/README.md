# Redis Configuration

Redis caching layer configuration and scripts.

## Structure
```
redis/
├── config/
│   └── redis.conf      # Redis configuration
├── scripts/
│   └── start-redis.sh  # Start script
├── docker/
│   └── Dockerfile      # Docker image
└── README.md
```

## Local Development

### Using Docker
```bash
docker run -d -p 6379:6379 -v ./config/redis.conf:/usr/local/etc/redis/redis.conf redis:latest
```

### Using local Redis
```bash
redis-server config/redis.conf
```

## Configuration
Edit `config/redis.conf` for custom settings:
- Port
- Memory limits
- Persistence
- Security
