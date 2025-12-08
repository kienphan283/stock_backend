# Market Ingest Service

## Purpose and Responsibilities

- **Role**: Real-time ingestion service that connects to the Alpaca WebSocket API and publishes normalized messages into Kafka.
- **Responsibilities**:
  - Maintain a resilient WebSocket connection to Alpaca.
  - Subscribe to configured symbols for trades and bars.
  - Normalize incoming Alpaca messages into a simplified schema.
  - Publish trades and bars to Kafka topics used by downstream consumers.

## Runtime Dependencies

- **Inbound**:
  - WebSocket stream from Alpaca (configured via environment variables).
- **Outbound**:
  - Kafka broker, using topics defined in `shared/realtime/kafka_topics.py`:
    - `stock_trades_realtime`
    - `stock_bars_staging`
- **Infra**:
  - No direct connection to Postgres or Redis.

## Data Flow

- `Alpaca WS → AlpacaWebSocketClient (alpaca/websocket_client.py) → KafkaProducerWrapper (broker/producer.py) → Kafka`
- `main.py` creates an `AlpacaStreamingManager`, which manages the WebSocket client and restarts it on failures.

## Service Boundary Rules

- **MUST**:
  - Be the single source of truth for ingesting real-time market data from Alpaca in this system.
  - Publish only to well-defined Kafka topics (no direct DB or cache writes).
- **MUST NOT**:
  - Write to Postgres or Redis directly.
  - Expose HTTP or WebSocket APIs.

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

## Configuration & Running

This service is intended to be run via Docker Compose as part of the backend stack.
See `stock_backend/README.md` for full setup instructions.

Environment variables (handled via root `.env`):
- `KAFKA_BOOTSTRAP_SERVERS`
- `ALPACA_API_KEY`
- `ALPACA_SECRET_KEY`
- `ALPACA_WS_URL`
- `SUBSCRIBE_SYMBOLS`
