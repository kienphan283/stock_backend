## Market Ingest Service

### Purpose and Responsibilities

- **Role**: Realtime ingestion service that connects to the Alpaca WebSocket API and publishes normalized messages into Kafka.
- **Responsibilities**:
  - Maintain a resilient WebSocket connection to Alpaca.
  - Subscribe to configured symbols for trades and bars.
  - Normalize incoming Alpaca messages into a simplified schema.
  - Publish trades and bars to Kafka topics used by downstream consumers.

### Runtime Dependencies

- **Inbound**:
  - WebSocket stream from Alpaca (configured via environment variables).
- **Outbound**:
  - Kafka broker, using topics defined in `shared/realtime/kafka_topics.py`:
    - `stock_trades_realtime`
    - `stock_bars_staging`
- **Infra**:
  - No direct connection to Postgres or Redis.

### Data Flow

- `Alpaca WS → AlpacaWebSocketClient (alpaca/websocket_client.py) → KafkaProducerWrapper (broker/producer.py) → Kafka`
- `main.py` creates an `AlpacaStreamingManager`, which manages the WebSocket client and restarts it on failures.

### Service Boundary Rules

- **MUST**:
  - Be the single source of truth for ingesting realtime market data from Alpaca in this system.
  - Publish only to well-defined Kafka topics (no direct DB or cache writes).
- **MUST NOT**:
  - Write to Postgres or Redis directly.
  - Expose HTTP or WebSocket APIs.

### Shared Components Used

- Uses `shared/realtime/kafka_topics.py` for canonical Kafka topic names.
- Uses `shared/realtime/symbols.py` (`INGEST_DEFAULT_SYMBOLS`) via `config/settings.py` to normalize `SUBSCRIBE_SYMBOLS`.

# Market Ingest Service

Lightweight service that receives real-time market data from Alpaca WebSocket and publishes to Kafka topics.

## Purpose

- **Input:** Alpaca WebSocket stream (real-time trades and bars)
- **Output:** Kafka topics (`stock_trades_realtime`, `stock_bars_staging`)
- **No Database:** Pure ingestion service
- **No REST API:** Standalone service, no HTTP endpoints

## Architecture

```
Alpaca WebSocket
    ↓
AlpacaWebSocketClient
    ↓ (normalize messages)
KafkaProducerWrapper
    ↓
Kafka Topics
    - stock_trades_realtime
    - stock_bars_staging
```

## Configuration

Environment variables (in root `.env`):

```env
# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092

# Alpaca API
ALPACA_API_KEY=your_alpaca_api_key
ALPACA_SECRET_KEY=your_alpaca_secret_key
ALPACA_WS_URL=wss://stream.data.alpaca.markets/v2/iex

# Symbols to subscribe (comma-separated)
SUBSCRIBE_SYMBOLS=AAPL,MSFT,GOOGL,AMZN,NVDA
```

## Running

```bash
# Install dependencies
pip install -r requirements.txt

# Run service
python main.py
```

## Kafka Topics

### stock_trades_realtime
- **Key:** Symbol (e.g., "AAPL")
- **Value:** 
  ```json
  {
    "symbol": "AAPL",
    "price": 150.25,
    "size": 100,
    "timestamp": 1234567890000000000,
    "type": "trade"
  }
  ```

### stock_bars_staging
- **Key:** Symbol (e.g., "AAPL")
- **Value:**
  ```json
  {
    "symbol": "AAPL",
    "open": 150.00,
    "high": 150.50,
    "low": 149.75,
    "close": 150.25,
    "volume": 1000000,
    "timestamp": 1234567890000000000,
    "type": "bar"
  }
  ```

## Error Handling

- WebSocket reconnection: Automatic retry with 5-second delay
- Kafka errors: Logged, messages may be lost (consider adding retry queue)
- Authentication failures: Service stops, requires manual restart

## Dependencies

- `kafka-python`: Kafka producer
- `websocket-client`: Alpaca WebSocket client
- `pydantic-settings`: Configuration management

## Notes

- This service is stateless
- No persistence layer
- Designed to run as a single instance (or multiple instances with different symbol subscriptions)
- Messages are published to Kafka immediately upon receipt

