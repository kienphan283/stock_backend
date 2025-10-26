# Stock Backend - Microservices Architecture

Modern microservices-based backend for Snow Analytics Stock Platform.

## 🏗️ Architecture

```
stock_backend/
│
├── expressjs-server/      # Node.js/Express.js/TypeScript API
│   ├── src/
│   │   ├── api/           # Controllers, routes, middlewares, validators
│   │   ├── core/          # Business logic (services, interfaces)
│   │   ├── infrastructure/# External dependencies (DB, APIs, config)
│   │   ├── types/         # TypeScript type definitions
│   │   ├── utils/         # Utilities (logger, error handler)
│   │   └── index.ts       # Application entry point
│   ├── package.json
│   ├── tsconfig.json
│   └── README.md
│
├── restapi-server/        # Python FastAPI for Financial Data
│   ├── services/          # Business logic & data services
│   ├── tests/             # Unit & integration tests
│   ├── server.py          # FastAPI application entry point
│   ├── requirements.txt   # Python dependencies
│   └── README.md
│
├── etl/                   # ETL Pipelines & Data Processing
│   ├── pipelines/         # ETL pipeline scripts
│   ├── processors/        # Data transformation processors
│   ├── schedulers/        # Cron jobs & task schedulers
│   ├── tests/             # Pipeline tests
│   ├── requirements.txt
│   └── README.md
│
├── redis/                 # Redis Caching Layer
│   ├── config/
│   │   └── redis.conf     # Redis configuration
│   ├── scripts/
│   │   └── start-redis.sh # Start script
│   ├── docker/
│   │   └── Dockerfile     # Redis Docker image
│   └── README.md
│
├── shared/                # Shared code & types (optional)
│   ├── types/             # Common type definitions
│   ├── constants/         # Shared constants
│   └── utils/             # Common utilities
│
├── docker-compose.yml     # Orchestrate all services
├── .env.example           # Environment variables template
├── REFACTOR_PLAN.md       # Refactoring documentation
└── README.md              # This file
```

## 🚀 Services

### 1. **Express.js Server** (Port 5000)
- **Tech Stack:** Node.js, Express.js, TypeScript
- **Purpose:** Main REST API for stocks, portfolio, dividends
- **Architecture:** Clean Architecture with DI
- **Features:**
  - Stock management APIs
  - Portfolio tracking APIs
  - Dividend calendar APIs
  - Request validation (Zod)
  - Error handling
  - Logging

### 2. **REST API Server** (Port 8000)
- **Tech Stack:** Python, FastAPI, PostgreSQL
- **Purpose:** Financial data operations (Income Statement, Balance Sheet, Cash Flow)
- **Features:**
  - Financial statements API
  - Database integration (PostgreSQL)
  - Redis caching (optional)
  - Auto-generated API docs (Swagger/ReDoc)

### 3. **ETL Pipelines**
- **Tech Stack:** Python
- **Purpose:** Data extraction, transformation, and loading
- **Features:**
  - Stock data pipeline
  - Financial data pipeline
  - Dividend data pipeline
  - Scheduled tasks

### 4. **Redis**
- **Purpose:** Caching layer for performance
- **Features:**
  - API response caching
  - Session storage
  - Rate limiting support

## 📦 Quick Start

### Prerequisites
- Node.js 18+ and npm
- Python 3.11+
- PostgreSQL 14+
- Redis 7+ (optional)

### Installation

#### 1. Clone repository
```bash
git clone <repository-url>
cd stock_backend
```

#### 2. Setup Express.js Server
```bash
cd expressjs-server
npm install
cp .env.example .env
# Edit .env with your configuration
npm run dev
```

#### 3. Setup REST API Server
```bash
cd restapi-server
pip install -r requirements.txt
cp .env.example .env
# Edit .env with database credentials
python server.py
```

#### 4. Setup Redis (Optional)
```bash
cd redis
bash scripts/start-redis.sh
```

#### 5. Setup ETL Pipelines
```bash
cd etl
pip install -r requirements.txt
# Run pipelines manually or schedule them
python pipelines/stock_data_pipeline.py
```

### Using Docker Compose (Recommended)
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

## 🔧 Configuration

### Express.js Server (.env)
```env
PORT=5000
NODE_ENV=development
PYTHON_API_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:3000
```

### REST API Server (.env)
```env
DATABASE_URL=postgresql://user:password@localhost:5432/stock_db
REDIS_URL=redis://localhost:6379
CACHE_TTL=1800
```

### Redis (redis.conf)
```conf
bind 127.0.0.1
port 6379
maxmemory 256mb
maxmemory-policy allkeys-lru
```

## 🧪 Testing

### Express.js Server
```bash
cd expressjs-server
npm test
npm run test:coverage
```

### REST API Server
```bash
cd restapi-server
pytest
pytest --cov=services tests/
```

### ETL Pipelines
```bash
cd etl
pytest
```

## 📊 API Documentation

### Express.js Server
- Health Check: `http://localhost:5000/health`
- API Base: `http://localhost:5000/api`

### REST API Server
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health Check: `http://localhost:8000/health`

## 🏗️ Development Workflow

### Running Services Separately

#### Terminal 1 - Express.js Server
```bash
cd expressjs-server
npm run dev
```

#### Terminal 2 - REST API Server
```bash
cd restapi-server
python server.py
```

#### Terminal 3 - Redis
```bash
cd redis
bash scripts/start-redis.sh
```

### Running All Services Together
```bash
docker-compose up
```

## 📁 Refactoring from Old Structure

If you're migrating from the old structure, run:

```bash
chmod +x refactor.sh
./refactor.sh
```

This will:
1. ✅ Create new directory structure
2. ✅ Move Express.js files to `expressjs-server/`
3. ✅ Move FastAPI files to `restapi-server/`
4. ✅ Reorganize ETL pipelines
5. ✅ Create Redis configuration
6. ✅ Generate README files

## 🔗 Service Communication

```
┌─────────────────┐
│   Frontend      │
│  (Next.js)      │
└────────┬────────┘
         │
    ┌────▼────┐
    │  NGINX  │ (Load Balancer)
    └────┬────┘
         │
    ┌────▼──────────────────┐
    │                       │
┌───▼──────────┐   ┌────▼──────────┐
│ Express.js   │   │  REST API     │
│   Server     │◄──┤   Server      │
│  (Port 5000) │   │  (Port 8000)  │
└──────┬───────┘   └───────┬───────┘
       │                   │
       │           ┌───────▼────────┐
       │           │   PostgreSQL   │
       │           └────────────────┘
       │
   ┌───▼────┐
   │ Redis  │
   └────────┘
```

## 🚀 Deployment

### Docker Deployment
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Manual Deployment
1. Build Express.js server: `cd expressjs-server && npm run build`
2. Start services with PM2 or systemd
3. Configure NGINX as reverse proxy
4. Setup SSL certificates

## 📝 Contributing

1. Create feature branch: `git checkout -b feat/new-feature`
2. Make changes
3. Run tests: `npm test` or `pytest`
4. Commit: `git commit -m "feat: add new feature"`
5. Push: `git push origin feat/new-feature`
6. Create Pull Request

## 📄 License

MIT License

## 👥 Team

Snow Analytics Team

---

**Need help?** Check individual service READMEs or contact the team.
