# Real-Time Stock Data Pipeline

Complete real-time data pipeline for stock market application with three independent data flows.

## Architecture

```
┌─────────────────┐
│  Alpaca Markets │
│   (WebSocket)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Python Producer │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌───────┐  ┌────────┐
│ Redis │  │ Kafka  │
└───┬───┘  └───┬────┘
    │          │
    │     ┌────┴────┐
    │     │         │
    │     ▼         ▼
    │  Consumer  Consumer
    │  (Trades)  (Bars)
    │     │         │
    │     ▼         ▼
    │  PostgreSQL  PostgreSQL
    │     │         │
    │     └────┬────┘
    │          │
    ▼          ▼
┌─────────┐  ┌─────────┐
│ExpressJS│  │ FastAPI │
│WebSocket│  │  /bars  │
└────┬────┘  └────┬─────┘
     │           │
     └─────┬─────┘
           │
           ▼
      Frontend
```

## Data Flows

### A) Real-Time Price Stream (Ultra Low-Latency)
- **Path**: Alpaca → Producer → Redis PubSub → ExpressJS WebSocket → Frontend
- **Latency**: 1-3ms
- **Purpose**: Immediate real-time delivery to UI

### B) Real-Time Price Persistence (Durable)
- **Path**: Alpaca → Producer → Kafka → Consumer Trades → PostgreSQL
- **Purpose**: Durable logging, scalable processing, replay capability

### C) Bar Data Pipeline (Charting)
- **Path**: Alpaca → Producer → Kafka → Consumer Bars → PostgreSQL → FastAPI → ExpressJS → Frontend
- **Purpose**: Historical data / charting

## Quick Start

### 1. Prerequisites

- Docker and Docker Compose
- Alpaca API credentials (free paper trading account)
- `.env` file in project root with:

```env
ALPACA_API_KEY=your_key_here
ALPACA_API_SECRET=your_secret_here
ALPACA_API_BASE_URL=https://paper-api.alpaca.markets/v2
ALPACA_DATA_WS_URL=wss://stream.data.alpaca.markets/v2/iex
KAFKA_BOOTSTRAP_SERVERS=localhost:9093
REDIS_HOST=localhost
REDIS_PORT=6379
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=Web_quan_li_danh_muc
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
```

### 2. Start Infrastructure

```bash
# Start all services
docker-compose up -d postgres redis zookeeper kafka

# Wait for services to be healthy
docker-compose ps
```

### 3. Start Pipeline Services

```bash
# Start producer (Alpaca → Redis + Kafka)
docker-compose up -d kafka-producer

# Start trades consumer (Kafka → PostgreSQL)
docker-compose up -d kafka-consumer-trades

# Start bars consumer (Kafka → PostgreSQL)
docker-compose up -d kafka-consumer-bars

# Start API servers
docker-compose up -d fastapi-server expressjs-server
```

### 4. Verify Pipeline

```bash
# Check producer logs
docker logs -f stock_kafka_producer

# Check consumer logs
docker logs -f stock_kafka_consumer_trades
docker logs -f stock_kafka_consumer_bars

# Check database
docker exec -it stock_postgres psql -U postgres -d Web_quan_li_danh_muc -c "SELECT COUNT(*) FROM market_data_oltp.stock_trades_realtime;"
docker exec -it stock_postgres psql -U postgres -d Web_quan_li_danh_muc -c "SELECT COUNT(*) FROM market_data_oltp.stock_bars_staging;"
```

## Local Development

### Setup

```bash
cd etl/streaming
pip install -r requirements.txt
```

### Run Services

**Terminal 1 - Producer:**
```bash
python producer.py
```

**Terminal 2 - Trades Consumer:**
```bash
python consumer_trades.py
```

**Terminal 3 - Bars Consumer:**
```bash
python consumer_bars.py
```

## API Endpoints

### FastAPI (Port 8000)

- `GET /bars/{symbol}` - Get bars for symbol
- `GET /bars/{symbol}/range?start=...&end=...` - Get bars in date range
- `GET /bars/latest` - Get latest bars for all symbols

### ExpressJS (Port 5000)

- `GET /api/bars/{symbol}` - Proxy to FastAPI
- `GET /api/bars/{symbol}/range` - Proxy to FastAPI
- `GET /api/bars/latest` - Proxy to FastAPI
- WebSocket: `ws://localhost:5000` - Real-time trade updates

### WebSocket Client Example

```javascript
import io from 'socket.io-client';

const socket = io('http://localhost:5000');

socket.on('connect', () => {
  console.log('Connected to WebSocket');
  socket.emit('subscribe', 'AAPL'); // Subscribe to symbol
});

socket.on('trade', (tradeData) => {
  console.log('Trade update:', tradeData);
  // { symbol: 'AAPL', price: 150.25, size: 100, timestamp: ... }
});
```

## Monitoring

- **Kafka UI**: http://localhost:8080
- **FastAPI Docs**: http://localhost:8000/docs
- **ExpressJS Health**: http://localhost:5000/health

## Configuration

Edit `config/settings.py` or set environment variables:

- `SUBSCRIBED_SYMBOLS` - Comma-separated list (default: AAPL,MSFT,GOOGL)
- `BATCH_SIZE` - Batch insert size (default: 100)
- `REDIS_CHANNEL_TRADES` - Redis PubSub channel (default: stock:trades:pubsub)

## Troubleshooting

### Producer not connecting to Alpaca
- Check `ALPACA_API_KEY` and `ALPACA_API_SECRET` in `.env`
- Verify market hours (9:30 AM - 4:00 PM ET)

### No data in database
- Check consumer logs: `docker logs stock_kafka_consumer_trades`
- Verify Kafka topics: `docker exec -it stock_kafka kafka-topics --list --bootstrap-server localhost:9092`
- Check database connection in consumer logs

### WebSocket not receiving data
- Verify Redis connection: `docker exec -it stock_redis redis-cli ping`
- Check ExpressJS logs: `docker logs -f stock_expressjs`
- Verify Redis channel: `docker exec -it stock_redis redis-cli PUBSUB CHANNELS`

## Architecture Details

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed architecture documentation.

## Notes

- Data flows during US market hours (9:30 AM - 4:00 PM ET)
- Free IEX feed with Alpaca Paper Trading account
- Producer does NOT wait on DB writes (fire-and-forget to Kafka)
- UI does NOT read directly from Kafka (uses Redis for real-time)
