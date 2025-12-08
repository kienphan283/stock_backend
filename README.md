# Stock Backend

The core backend system handling data ingestion, processing, and API services for the Stock Platform. It manages real-time market data streaming, financial statement ETL processes, and serves data to the frontend.

## Technologies

- **Languages:** Python, Node.js
- **Frameworks:** FastAPI, Express
- **Data & Messaging:** PostgreSQL, Redis, Apache Kafka
- **Infrastructure:** Docker, Docker Compose

## __Setup & Run__

```bash
# 1. Configure Environment
cp .env.example .env

# 2. Start Services
docker-compose up --build -d

# 3. Initialize Data
docker exec -it stock_market_stream python generate_dictionary_from_api.py
docker exec -it stock_market_stream python etl/runner.py financial
```
