# Kafka Real-time Stock Data Pipeline

Real-time stock data streaming using Kafka and Alpaca Markets API.

## Architecture

```
Alpaca WebSocket → Producer → Kafka → Consumer → PostgreSQL
```

**Topics**: `stock_trades_realtime`, `stock_bars_staging`

## Quick Start

```bash
cd stock_backend
docker-compose up -d
```

Set credentials in `stock_backend/.env`:
```env
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
```

## Services

- **Kafka UI**: http://localhost:8080
- **Producer**: Streams Alpaca → Kafka
- **Consumer**: Writes Kafka → PostgreSQL

## Monitoring

```bash
# View logs
docker logs -f stock_kafka_producer
docker logs -f stock_kafka_consumer_db

# Check database
SELECT COUNT(*) FROM market_data_oltp.stock_trades_realtime;
```

## Notes

- Data flows during US market hours (9:30 AM - 4:00 PM ET)
- Symbols: AAPL, MSFT, GOOGL (edit `producer.py` to add more)
- Free IEX feed with Alpaca Paper Trading
