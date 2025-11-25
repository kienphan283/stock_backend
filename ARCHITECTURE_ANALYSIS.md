# 🏗️ Real-Time Stock Data Pipeline - Complete Architecture Analysis

**Document Version:** 1.0  
**Last Updated:** 2025-01-15  
**Purpose:** Complete understanding of system architecture, data flows, and endpoint processing logic

---

## Table of Contents

1. [High-Level System Overview](#section-1-high-level-system-overview)
2. [Component Responsibilities](#section-2-component-responsibilities)
3. [Kafka/Redis/Data Flows](#section-3-kafkaredisdata-flows)
4. [API Endpoint Processing Breakdown](#section-4-api-endpoint-processing-breakdown)
5. [End-to-End Flow Map](#section-5-end-to-end-flow-map)
6. [Progress Assessment per Endpoint](#section-6-progress-assessment-per-endpoint)
7. [Missing Pieces + Recommendations](#section-7-missing-pieces--recommendations)

---

## Section 1: High-Level System Overview

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL DATA SOURCE                         │
│                    Alpaca WebSocket API                         │
│              (Real-time trades & bars)                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    KAFKA PRODUCER                               │
│              (etl/streaming/producer.py)                        │
│  • WebSocketService: Connects to Alpaca                         │
│  • PublisherService: Distributes to Redis + Kafka               │
└──────────────┬──────────────────────────────┬───────────────────┘
               │                              │
               ▼                              ▼
    ┌──────────────────┐          ┌──────────────────────┐
    │   REDIS PUBSUB   │          │   KAFKA TOPICS      │
    │ stock:trades:    │          │ • stock_trades_     │
    │   pubsub         │          │   realtime           │
    │                  │          │ • stock_bars_       │
    │ (Ultra low       │          │   staging           │
    │  latency)        │          │                     │
    └────────┬─────────┘          └──────────┬───────────┘
             │                              │
             │                              ▼
             │                  ┌──────────────────────┐
             │                  │  KAFKA CONSUMERS     │
             │                  │  • consumer_trades   │
             │                  │  • consumer_bars     │
             │                  └──────────┬───────────┘
             │                            │
             │                            ▼
             │                  ┌──────────────────────┐
             │                  │   POSTGRESQL DB      │
             │                  │ • stock_trades_      │
             │                  │   realtime           │
             │                  │ • stock_bars_         │
             │                  │   staging            │
             │                  └──────────┬───────────┘
             │                            │
             ▼                            │
┌──────────────────────────┐              │
│   EXPRESSJS SERVER       │              │
│   (Node.js/TypeScript)   │              │
│  • WebSocket Service     │              │
│  • HTTP API Gateway      │              │
│  • Redis Subscriber      │              │
└───────────┬──────────────┘              │
            │                              │
            │                              │
            ▼                              ▼
┌──────────────────────────┐  ┌──────────────────────┐
│   FASTAPI SERVER         │  │   POSTGRESQL DB      │
│   (Python)               │  │   (Read Service)    │
│  • REST API              │  │                     │
│  • Database Queries      │  │                     │
│  • Redis Caching         │  │                     │
└───────────┬──────────────┘  └──────────────────────┘
            │
            │ HTTP Proxy
            │
            ▼
┌──────────────────────────┐
│      FRONTEND            │
│  • WebSocket Client      │
│  • HTTP API Client       │
└──────────────────────────┘
```

### Key Architectural Decisions

1. **Separation of Concerns:**
   - **Real-time path:** Alpaca → Redis PubSub → ExpressJS WebSocket → Frontend (ultra low-latency)
   - **Persistence path:** Alpaca → Kafka → PostgreSQL → FastAPI → ExpressJS → Frontend (durable, queryable)

2. **Service Roles:**
   - **Kafka Producer:** Ingests Alpaca data, distributes to Redis (real-time) and Kafka (persistence)
   - **Kafka Consumers:** Asynchronously persist data to PostgreSQL
   - **ExpressJS:** Real-time gateway (WebSocket) + API proxy
   - **FastAPI:** Read service for historical/aggregated data

3. **Data Flow Patterns:**
   - **Write path:** Asynchronous (Kafka consumers write in batches)
   - **Read path:** Synchronous (FastAPI queries PostgreSQL directly)
   - **Real-time path:** Push-based (Redis PubSub → WebSocket)

---

## Section 2: Component Responsibilities

### 2.1 Kafka Producer (`etl/streaming/producer.py`)

**Purpose:** Connect to Alpaca WebSocket and distribute data to Redis and Kafka

**Components:**
- **WebSocketService** (`services/websocket_service.py`):
  - Manages Alpaca WebSocket connection lifecycle
  - Handles authentication, subscription, message parsing
  - Transforms Alpaca messages to internal format
  - Calls callbacks for trades and bars

- **PublisherService** (`services/publisher_service.py`):
  - Coordinates publishing to Redis and Kafka
  - `publish_trade()`: Publishes to Redis PubSub + Kafka topic `stock_trades_realtime`
  - `publish_bar()`: Publishes to Kafka topic `stock_bars_staging` (bars NOT published to Redis)

- **Infrastructure:**
  - `KafkaClient`: Publishes messages to Kafka topics
  - `RedisClient`: Publishes to Redis PubSub channel `stock:trades:pubsub`

**Protocols:** WebSocket (Alpaca), Kafka Producer API, Redis PubSub

**Data Transformation:**
- Alpaca trade format → Internal trade format: `{symbol, price, size, timestamp}`
- Alpaca bar format → Internal bar format: `{symbol, open, high, low, close, volume, trade_count, vwap, timestamp}`

---

### 2.2 Kafka Consumers

#### 2.2.1 Trades Consumer (`etl/streaming/consumer_trades.py`)

**Purpose:** Consume trade messages from Kafka and persist to PostgreSQL

**Process:**
1. Subscribes to Kafka topic: `stock_trades_realtime`
2. Consumer group: `trades-persistence-group`
3. Batches messages (default: 100 trades)
4. For each trade:
   - Gets/creates `stock_id` from `stocks` table
   - Converts timestamp from milliseconds to `TIMESTAMPTZ`
   - Adds to batch: `(stock_id, ts, price, size)`
5. Batch inserts to `market_data_oltp.stock_trades_realtime`

**Database Operations:**
- `get_or_create_stock_id()`: Ensures stock exists in `stocks` table
- `batch_insert_trades()`: Bulk insert with `ON CONFLICT DO NOTHING`

**Protocol:** Kafka Consumer API (asynchronous)

---

#### 2.2.2 Bars Consumer (`etl/streaming/consumer_bars.py`)

**Purpose:** Consume bar messages from Kafka and persist to PostgreSQL

**Process:**
1. Subscribes to Kafka topic: `stock_bars_staging`
2. Consumer group: `bars-persistence-group`
3. Batches messages (default: 100 bars)
4. For each bar:
   - Gets/creates `stock_id` from `stocks` table
   - Converts timestamp from milliseconds to `TIMESTAMPTZ`
   - Adds to batch: `(stock_id, '1m', ts, open, high, low, close, volume, trade_count, vwap)`
5. Batch inserts to `market_data_oltp.stock_bars_staging`

**Database Operations:**
- `get_or_create_stock_id()`: Ensures stock exists
- `batch_insert_bars()`: Bulk insert with `ON CONFLICT (stock_id, ts, timeframe) DO NOTHING`

**Protocol:** Kafka Consumer API (asynchronous)

---

### 2.3 ExpressJS Server (`expressjs-server/`)

**Purpose:** Real-time gateway and API proxy

**Components:**

#### 2.3.1 WebSocket Service (`core/services/websocket.service.ts`)
- **Initialization:** Attaches Socket.IO server to HTTP server
- **Redis Subscription:** Subscribes to `stock:trades:pubsub` channel
- **Message Broadcasting:**
  - Receives trade data from Redis
  - Broadcasts to all clients via Socket.IO event `"trade"`
  - Also broadcasts to symbol-specific rooms: `symbol:{SYMBOL}`

**Protocols:** Socket.IO (WebSocket), Redis PubSub

#### 2.3.2 HTTP API Routes
- **Bars Routes** (`api/routes/bars.routes.ts`): Proxies FastAPI bar endpoints
- **Stocks Routes** (`api/routes/stocks.routes.ts`): Proxies FastAPI stock endpoints
- **Portfolio/Dividends Routes**: Business logic endpoints

**Protocol:** HTTP REST (synchronous)

#### 2.3.3 Redis Client (`infrastructure/redis/redisClient.ts`)
- Connects to Redis using Docker service name `redis`
- Subscribes to PubSub channel: `stock:trades:pubsub`
- Parses JSON messages and calls callback

**Protocol:** Redis PubSub (asynchronous subscription)

---

### 2.4 FastAPI Server (`fastapi-server/server.py`)

**Purpose:** Read service for historical and aggregated data

**Components:**
- **Database Queries:** Direct PostgreSQL queries using `psycopg2`
- **Redis Caching:** Optional caching layer (if Redis available)
- **REST Endpoints:** Exposes data via HTTP REST API

**Protocols:** HTTP REST (synchronous), PostgreSQL (synchronous queries)

**Key Endpoints:**
- `/bars/{symbol}`: Get OHLC bars from `stock_bars_staging`
- `/bars/{symbol}/range`: Get bars in date range
- `/bars/latest`: Get latest bars for all symbols
- `/quote`: Get stock quote from `stock_eod_prices` or fallback to CSV loader

---

### 2.5 PostgreSQL Database

**Schema:** `market_data_oltp`

**Tables:**
1. **`stocks`**: Stock metadata
   - `stock_id` (PK), `stock_ticker`, `stock_name`, `exchange`

2. **`stock_trades_realtime`**: Real-time trade ticks
   - `trade_id` (PK), `stock_id` (FK), `ts`, `price`, `size`

3. **`stock_bars_staging`**: OHLC bar data (1-minute bars)
   - `id` (PK), `stock_id` (FK), `timeframe`, `ts`, `open_price`, `high_price`, `low_price`, `close_price`, `volume`, `trade_count`, `vwap`

4. **`stock_eod_prices`**: End-of-day prices (legacy/fallback)

---

## Section 3: Kafka/Redis/Data Flows

### 3.1 Real-Time Price Flow (Ultra Low-Latency)

```
Alpaca WebSocket
    │
    │ (Trade message received)
    ▼
WebSocketService.on_trade()
    │
    │ (Calls callback)
    ▼
PublisherService.publish_trade()
    │
    ├─► RedisClient.publish_trade()
    │   │
    │   └─► Redis PubSub: stock:trades:pubsub
    │       │
    │       │ (Message published)
    │       ▼
    │   RedisStreamClient.subscribeToTrades()
    │       │
    │       │ (Message received)
    │       ▼
    │   WebSocketService.startRedisListener()
    │       │
    │       │ (Broadcasts via Socket.IO)
    │       ▼
    │   Frontend WebSocket Client
    │
    └─► KafkaClient.publish()
        │
        └─► Kafka Topic: stock_trades_realtime
            │
            │ (Asynchronous consumption)
            ▼
        TradesConsumer.process_trade()
            │
            └─► PostgreSQL: stock_trades_realtime
```

**Latency:** ~1-3ms (Redis PubSub → WebSocket)

**Characteristics:**
- **Synchronous path:** Alpaca → Redis → ExpressJS → Frontend
- **Asynchronous path:** Alpaca → Kafka → Consumer → PostgreSQL (for persistence)

---

### 3.2 Bar Data Flow (Persistence + Charting)

```
Alpaca WebSocket
    │
    │ (Bar message received - 1-minute aggregation)
    ▼
WebSocketService.on_bar()
    │
    │ (Calls callback)
    ▼
PublisherService.publish_bar()
    │
    │ (NOT published to Redis - only Kafka)
    ▼
KafkaClient.publish()
    │
    └─► Kafka Topic: stock_bars_staging
        │
        │ (Asynchronous consumption)
        ▼
    BarsConsumer.process_bar()
        │
        └─► PostgreSQL: stock_bars_staging
            │
            │ (Query via FastAPI)
            ▼
        FastAPI.get_bars()
            │
            │ (HTTP proxy)
            ▼
        ExpressJS.get('/api/bars/:symbol')
            │
            └─► Frontend (Charting)
```

**Latency:** ~100-500ms (Kafka → DB → FastAPI → ExpressJS)

**Characteristics:**
- **No real-time path:** Bars are NOT published to Redis (only trades)
- **Purpose:** Historical data for charting
- **Query pattern:** FastAPI reads from PostgreSQL on-demand

---

### 3.3 API Request Flow (ExpressJS → FastAPI)

```
Frontend HTTP Request
    │
    │ GET /api/bars/AAPL
    ▼
ExpressJS Router (bars.routes.ts)
    │
    │ (Extracts params: symbol, limit)
    ▼
PythonFinancialClient.get('/bars/AAPL?limit=100')
    │
    │ HTTP GET http://fastapi-server:8000/bars/AAPL?limit=100
    ▼
FastAPI Endpoint (server.py:get_bars())
    │
    │ (Opens PostgreSQL connection)
    ▼
PostgreSQL Query
    │
    │ SELECT ... FROM stock_bars_staging
    │ JOIN stocks ON ...
    │ WHERE stock_ticker = 'AAPL'
    │ ORDER BY ts DESC LIMIT 100
    ▼
FastAPI Response
    │
    │ {success: true, symbol: "AAPL", count: 100, data: [...]}
    ▼
ExpressJS Response
    │
    └─► Frontend
```

**Protocol:** HTTP REST (synchronous)

**Error Handling:**
- FastAPI returns 404 if symbol not found
- ExpressJS forwards FastAPI errors to frontend
- Timeout: 30 seconds (configurable)

---

## Section 4: API Endpoint Processing Breakdown

### 4.1 ExpressJS Endpoints

#### 4.1.1 `GET /api/bars/:symbol`

**Route:** `expressjs-server/src/api/routes/bars.routes.ts:14-22`

**Input:**
- Path param: `symbol` (string, e.g., "AAPL")
- Query param: `limit` (number, default: 100)

**Processing:**
1. Extracts `symbol` from `req.params`
2. Parses `limit` from `req.query` (default: 100)
3. Calls `pythonClient.get('/bars/${symbol}?limit=${limit}')`
4. Returns JSON response directly from FastAPI

**Output:**
```json
{
  "success": true,
  "symbol": "AAPL",
  "count": 100,
  "data": [
    {
      "timestamp": "2025-01-15T10:30:00+00:00",
      "open": 150.0,
      "high": 150.5,
      "low": 149.75,
      "close": 150.25,
      "volume": 1000000,
      "trade_count": 500,
      "vwap": 150.15
    },
    ...
  ]
}
```

**Dependencies:**
- FastAPI server must be running
- FastAPI endpoint `/bars/{symbol}` must be accessible
- PostgreSQL must have data in `stock_bars_staging`

**Where Logic Ends:**
- ExpressJS does NOT query database directly
- ExpressJS does NOT validate symbol existence
- ExpressJS does NOT transform data
- **ExpressJS is a pure HTTP proxy** - forwards request to FastAPI and returns response

---

#### 4.1.2 `GET /api/bars/:symbol/range`

**Route:** `expressjs-server/src/api/routes/bars.routes.ts:26-47`

**Input:**
- Path param: `symbol` (string)
- Query params: `start` (ISO date string), `end` (ISO date string), `limit` (optional)

**Processing:**
1. Validates `start` and `end` are present (returns 400 if missing)
2. Builds query string: `?start=...&end=...&limit=...`
3. Calls `pythonClient.get('/bars/${symbol}/range?${queryParams}')`
4. Returns JSON response from FastAPI

**Output:**
```json
{
  "success": true,
  "symbol": "AAPL",
  "start": "2025-01-15T00:00:00Z",
  "end": "2025-01-15T23:59:59Z",
  "count": 50,
  "data": [...]
}
```

**Dependencies:** Same as `/api/bars/:symbol`

**Where Logic Ends:** Pure proxy - no validation or transformation

---

#### 4.1.3 `GET /api/bars/latest`

**Route:** `expressjs-server/src/api/routes/bars.routes.ts:51-58`

**Input:**
- Query param: `limit` (number, default: 10)

**Processing:**
1. Parses `limit` from query (default: 10)
2. Calls `pythonClient.get('/bars/latest?limit=${limit}')`
3. Returns JSON response from FastAPI

**Output:**
```json
{
  "success": true,
  "count": 10,
  "data": [
    {
      "symbol": "AAPL",
      "timestamp": "2025-01-15T10:30:00+00:00",
      "open": 150.0,
      ...
    },
    ...
  ]
}
```

**Dependencies:** FastAPI `/bars/latest` endpoint

---

#### 4.1.4 `GET /api/stocks/:ticker/quote`

**Route:** `expressjs-server/src/api/routes/stocks.routes.ts:30-33`

**Processing:**
1. Extracts `ticker` from params
2. Calls `stockController.getStockQuote(ticker)`
3. Controller calls `stockService.getQuote(ticker)`
4. Service calls `financialClient.getQuote(ticker)`
5. Client makes HTTP GET to FastAPI `/quote?ticker={ticker}`
6. Returns quote data

**Dependencies:**
- FastAPI `/quote` endpoint
- PostgreSQL `stock_eod_prices` table (or CSV fallback)

**Where Logic Ends:**
- ExpressJS transforms FastAPI response to internal `QuoteData` type
- No direct database access

---

#### 4.1.5 WebSocket: `ws://localhost:5000` (Socket.IO)

**Initialization:** `expressjs-server/src/core/services/websocket.service.ts:24-42`

**Connection Flow:**
1. Client connects via Socket.IO
2. Server emits `"connected"` event
3. Client can subscribe: `socket.emit("subscribe", "AAPL")`
4. Server joins client to room: `symbol:AAPL`

**Message Flow:**
1. Redis publishes trade to `stock:trades:pubsub`
2. `RedisStreamClient.subscribeToTrades()` receives message
3. `WebSocketService.startRedisListener()` callback fires
4. Server broadcasts to:
   - Symbol-specific room: `io.to('symbol:AAPL').emit('trade', data)`
   - All clients: `io.emit('trade', data)`

**Output Format:**
```json
{
  "symbol": "AAPL",
  "price": 150.25,
  "size": 100,
  "timestamp": 1705315800000
}
```

**Dependencies:**
- Redis PubSub channel `stock:trades:pubsub` must be active
- Kafka Producer must be publishing to Redis

---

### 4.2 FastAPI Endpoints

#### 4.2.1 `GET /bars/{symbol}`

**Route:** `fastapi-server/server.py:290-350`

**Input:**
- Path param: `symbol` (string)
- Query param: `limit` (int, default: 100, min: 1, max: 1000)

**Processing:**
1. Opens PostgreSQL connection
2. Executes JOIN query:
   ```sql
   SELECT 
       b.ts as timestamp,
       b.open_price as open,
       b.high_price as high,
       b.low_price as low,
       b.close_price as close,
       b.volume,
       b.trade_count,
       b.vwap
   FROM market_data_oltp.stock_bars_staging b
   JOIN market_data_oltp.stocks s ON s.stock_id = b.stock_id
   WHERE s.stock_ticker = %s
   ORDER BY b.ts DESC
   LIMIT %s
   ```
3. If no results:
   - Checks if symbol exists in `stocks` table
   - Returns 404 if symbol not found
   - Returns empty array if symbol exists but no bars
4. Converts results to list of dicts
5. Returns JSON response

**Output:**
```json
{
  "success": true,
  "symbol": "AAPL",
  "count": 100,
  "data": [
    {
      "timestamp": "2025-01-15T10:30:00+00:00",
      "open": 150.0,
      "high": 150.5,
      "low": 149.75,
      "close": 150.25,
      "volume": 1000000,
      "trade_count": 500,
      "vwap": 150.15
    }
  ]
}
```

**Dependencies:**
- PostgreSQL connection
- `stock_bars_staging` table must have data
- `stocks` table must have symbol entry

**Where Logic Ends:**
- Query executes successfully
- Data is returned as-is (no aggregation or transformation)
- **No caching** (Redis caching is optional but not implemented for this endpoint)

---

#### 4.2.2 `GET /bars/{symbol}/range`

**Route:** `fastapi-server/server.py:352-427`

**Input:**
- Path param: `symbol` (string)
- Query params: `start` (ISO date string), `end` (ISO date string), `limit` (int, default: 1000, max: 10000)

**Processing:**
1. Parses `start` and `end` to `datetime` objects
2. Validates date format (returns 400 if invalid)
3. Executes JOIN query with date range:
   ```sql
   SELECT ... FROM stock_bars_staging b
   JOIN stocks s ON s.stock_id = b.stock_id
   WHERE s.stock_ticker = %s
   AND b.ts >= %s
   AND b.ts <= %s
   ORDER BY b.ts DESC
   LIMIT %s
   ```
4. Returns results (same format as `/bars/{symbol}`)

**Dependencies:** Same as `/bars/{symbol}`

**Where Logic Ends:** Query returns filtered results

---

#### 4.2.3 `GET /bars/latest`

**Route:** `fastapi-server/server.py:429-480`

**Input:**
- Query param: `limit` (int, default: 10, max: 100)

**Processing:**
1. Executes query with `DISTINCT ON`:
   ```sql
   SELECT DISTINCT ON (s.stock_ticker)
       s.stock_ticker as symbol,
       b.ts as timestamp,
       b.open_price as open,
       ...
   FROM market_data_oltp.stock_bars_staging b
   JOIN market_data_oltp.stocks s ON b.stock_id = s.stock_id
   ORDER BY s.stock_ticker, b.ts DESC
   LIMIT %s
   ```
2. Groups results by symbol (takes latest bar per symbol)
3. Returns list of latest bars

**Output:**
```json
{
  "success": true,
  "count": 10,
  "data": [
    {
      "symbol": "AAPL",
      "timestamp": "2025-01-15T10:30:00+00:00",
      "open": 150.0,
      ...
    },
    {
      "symbol": "MSFT",
      "timestamp": "2025-01-15T10:30:00+00:00",
      "open": 380.0,
      ...
    }
  ]
}
```

**Dependencies:** PostgreSQL with multiple symbols in `stock_bars_staging`

---

#### 4.2.4 `GET /quote?ticker={ticker}`

**Route:** `fastapi-server/server.py:208-288`

**Input:**
- Query param: `ticker` (string, required)

**Processing:**
1. Queries `stocks` table for `stock_id`
2. If stock not found, FastAPI now returns null data (legacy `StockDataLoader` removed)
3. Queries `stock_eod_prices` for latest price:
   ```sql
   SELECT 
       close_price as current_price,
       open_price, high_price, low_price,
       volume, pct_change as percent_change
   FROM market_data_oltp.stock_eod_prices
   WHERE stock_id = %s
   ORDER BY trading_date DESC
   LIMIT 1
   ```
4. Gets previous close for change calculation
5. Calculates `change = current_price - previous_close`
6. Returns quote data

**Output:**
```json
{
  "success": true,
  "data": {
    "currentPrice": 150.25,
    "change": 0.50,
    "percentChange": 0.33,
    "high": 150.50,
    "low": 149.75,
    "open": 150.00,
    "previousClose": 149.75
  }
}
```

**Dependencies:**
- PostgreSQL `stock_eod_prices` table (or CSV fallback)
- **Note:** This endpoint does NOT read from `stock_trades_realtime` (real-time trades)

**Where Logic Ends:**
- Returns latest EOD price, NOT real-time price
- Real-time prices are only available via WebSocket

---

## Section 5: End-to-End Flow Map

### 5.1 Real-Time Trade Flow (Complete)

```
Step 1: Alpaca WebSocket receives trade
  │
  │ Message: {"T": "t", "S": "AAPL", "p": 150.25, "s": 100, "t": "2025-01-15T10:30:00Z"}
  ▼
Step 2: WebSocketService._on_message()
  │
  │ Parses message via AlpacaAdapter
  │ Identifies as trade: is_trade() = true
  │ Transforms: {symbol: "AAPL", price: 150.25, size: 100, timestamp: 1705315800000}
  ▼
Step 3: PublisherService.publish_trade()
  │
  ├─► Step 3a: RedisClient.publish_trade()
  │   │
  │   │ Channel: "stock:trades:pubsub"
  │   │ Message: JSON.stringify(trade_data)
  │   │
  │   └─► Redis PubSub publishes message
  │       │
  │       │ (Subscribers receive immediately)
  │       ▼
  │   Step 3b: RedisStreamClient.subscribeToTrades()
  │       │
  │       │ (ExpressJS subscribed to channel)
  │       │ Callback fires: (tradeData) => {...}
  │       ▼
  │   Step 3c: WebSocketService.startRedisListener()
  │       │
  │       │ Broadcasts via Socket.IO:
  │       │ - io.to('symbol:AAPL').emit('trade', tradeData)
  │       │ - io.emit('trade', tradeData)
  │       ▼
  │   Step 3d: Frontend WebSocket Client
  │       │
  │       │ Receives: socket.on('trade', (data) => {...})
  │       │ Updates UI in real-time
  │
  └─► Step 3e: KafkaClient.publish()
      │
      │ Topic: "stock_trades_realtime"
      │ Key: "AAPL"
      │ Value: trade_data (JSON)
      │
      └─► Kafka Topic stores message
          │
          │ (Asynchronous consumption - separate process)
          ▼
      Step 4: TradesConsumer.consume()
          │
          │ Kafka consumer polls for messages
          │ Receives message from topic
          ▼
      Step 5: TradesConsumer.process_trade()
          │
          │ Gets stock_id: get_or_create_stock_id("AAPL")
          │ Converts timestamp: datetime.fromtimestamp(1705315800000 / 1000)
          │ Adds to batch: (stock_id, ts, 150.25, 100)
          │
          │ (When batch reaches 100 trades)
          ▼
      Step 6: TradesConsumer.flush_trades()
          │
          │ Executes batch insert:
          │ INSERT INTO stock_trades_realtime (stock_id, ts, price, size)
          │ VALUES (1, '2025-01-15 10:30:00', 150.25, 100), ...
          │
          └─► PostgreSQL: stock_trades_realtime table
```

**Total Latency:**
- Real-time path (Steps 1-3d): **~1-3ms**
- Persistence path (Steps 1-6): **~100-500ms** (batch processing)

---

### 5.2 Bar Data Flow (Complete)

```
Step 1: Alpaca WebSocket receives bar (1-minute aggregation)
  │
  │ Message: {"T": "b", "S": "AAPL", "o": 150.0, "h": 150.5, "l": 149.75, "c": 150.25, "v": 1000000, ...}
  ▼
Step 2: WebSocketService._on_message()
  │
  │ Parses message via AlpacaAdapter
  │ Identifies as bar: is_bar() = true
  │ Transforms: {symbol: "AAPL", open: 150.0, high: 150.5, low: 149.75, close: 150.25, volume: 1000000, ...}
  ▼
Step 3: PublisherService.publish_bar()
  │
  │ (NOT published to Redis - only Kafka)
  │
  └─► Step 3a: KafkaClient.publish()
      │
      │ Topic: "stock_bars_staging"
      │ Key: "AAPL"
      │ Value: bar_data (JSON)
      │
      └─► Kafka Topic stores message
          │
          │ (Asynchronous consumption)
          ▼
      Step 4: BarsConsumer.consume()
          │
          │ Kafka consumer polls for messages
          │ Receives message from topic
          ▼
      Step 5: BarsConsumer.process_bar()
          │
          │ Gets stock_id: get_or_create_stock_id("AAPL")
          │ Converts timestamp: datetime.fromtimestamp(1705315800000 / 1000)
          │ Adds to batch: (stock_id, '1m', ts, 150.0, 150.5, 149.75, 150.25, 1000000, 500, 150.15)
          │
          │ (When batch reaches 100 bars)
          ▼
      Step 6: BarsConsumer.flush_bars()
          │
          │ Executes batch insert:
          │ INSERT INTO stock_bars_staging (stock_id, timeframe, ts, open_price, ...)
          │ VALUES (1, '1m', '2025-01-15 10:30:00', 150.0, ...), ...
          │
          └─► PostgreSQL: stock_bars_staging table
              │
              │ (Query on-demand via FastAPI)
              ▼
          Step 7: Frontend requests bars
              │
              │ GET /api/bars/AAPL?limit=100
              ▼
          Step 8: ExpressJS proxies to FastAPI
              │
              │ GET http://fastapi-server:8000/bars/AAPL?limit=100
              ▼
          Step 9: FastAPI queries PostgreSQL
              │
              │ SELECT ... FROM stock_bars_staging
              │ JOIN stocks ON ...
              │ WHERE stock_ticker = 'AAPL'
              │ ORDER BY ts DESC LIMIT 100
              ▼
          Step 10: FastAPI returns JSON
              │
              │ {success: true, symbol: "AAPL", count: 100, data: [...]}
              ▼
          Step 11: ExpressJS forwards response
              │
              └─► Frontend receives bars for charting
```

**Total Latency:**
- Persistence (Steps 1-6): **~100-500ms** (batch processing)
- Query (Steps 7-11): **~50-200ms** (synchronous database query)

---

### 5.3 API Request Flow (ExpressJS → FastAPI → PostgreSQL)

```
Step 1: Frontend HTTP Request
  │
  │ GET http://localhost:5000/api/bars/AAPL?limit=100
  ▼
Step 2: ExpressJS Router
  │
  │ Route: /api/bars/:symbol
  │ Handler: bars.routes.ts:14-22
  │ Extracts: symbol = "AAPL", limit = 100
  ▼
Step 3: PythonFinancialClient.get()
  │
  │ URL: http://fastapi-server:8000/bars/AAPL?limit=100
  │ Method: GET
  │ Timeout: 30 seconds
  │
  │ (HTTP request over Docker network)
  ▼
Step 4: FastAPI Endpoint
  │
  │ Route: /bars/{symbol}
  │ Handler: server.py:get_bars()
  │ Extracts: symbol = "AAPL", limit = 100
  ▼
Step 5: PostgreSQL Connection
  │
  │ psycopg2.connect(**DB_CONFIG)
  │ Opens connection to postgres:5432
  ▼
Step 6: SQL Query Execution
  │
  │ cur.execute("""
  │   SELECT b.ts, b.open_price, b.high_price, ...
  │   FROM market_data_oltp.stock_bars_staging b
  │   JOIN market_data_oltp.stocks s ON s.stock_id = b.stock_id
  │   WHERE s.stock_ticker = 'AAPL'
  │   ORDER BY b.ts DESC
  │   LIMIT 100
  │ """)
  │
  │ (Query executes on PostgreSQL)
  ▼
Step 7: Result Processing
  │
  │ bars = cur.fetchall()
  │ result = [dict(bar) for bar in bars]
  │
  │ Returns: {success: true, symbol: "AAPL", count: 100, data: result}
  ▼
Step 8: FastAPI HTTP Response
  │
  │ Status: 200 OK
  │ Body: JSON response
  ▼
Step 9: ExpressJS Receives Response
  │
  │ PythonFinancialClient.get() returns result
  │ ExpressJS returns: res.json(data)
  ▼
Step 10: Frontend Receives Response
  │
  └─► Frontend renders chart with bars data
```

**Total Latency:** **~50-200ms** (synchronous HTTP + database query)

---

## Section 6: Progress Assessment per Endpoint

### 6.1 ExpressJS Endpoints

#### ✅ `GET /api/bars/:symbol`
- **Status:** ✅ **Fully Implemented**
- **What Works:**
  - Route handler extracts params
  - Proxies to FastAPI correctly
  - Returns JSON response
- **Missing:**
  - No input validation (symbol format, limit bounds)
  - No error handling for FastAPI failures
  - No caching layer
- **Required for Completion:**
  - Input validation middleware
  - Error handling for FastAPI timeouts
  - Optional Redis caching

---

#### ✅ `GET /api/bars/:symbol/range`
- **Status:** ✅ **Fully Implemented**
- **What Works:**
  - Validates `start` and `end` are present
  - Builds query string correctly
  - Proxies to FastAPI
- **Missing:**
  - No date format validation
  - No date range validation (start < end)
- **Required for Completion:**
  - Date validation middleware
  - Range validation

---

#### ✅ `GET /api/bars/latest`
- **Status:** ✅ **Fully Implemented**
- **What Works:**
  - Proxies to FastAPI correctly
- **Missing:**
  - No input validation
- **Required for Completion:**
  - Limit validation (min/max)

---

#### ⚠️ `GET /api/stocks/:ticker/quote`
- **Status:** ⚠️ **Partially Implemented**
- **What Works:**
  - Controller → Service → Client chain works
  - Proxies to FastAPI `/quote` endpoint
- **Missing:**
  - FastAPI `/quote` reads from `stock_eod_prices` (EOD data), NOT real-time
  - No integration with `stock_trades_realtime` table
  - Real-time quotes only available via WebSocket
- **Required for Completion:**
  - FastAPI endpoint to read latest trade from `stock_trades_realtime`
  - Or: ExpressJS reads directly from Redis for latest price
  - Fallback logic if real-time data unavailable

---

#### ❌ `GET /api/stocks/:ticker` (Get Stock Details)
- **Status:** ❌ **Not Fully Implemented**
- **What Works:**
  - Controller calls `stockService.getStockByTicker()`
  - Service calls FastAPI `/profile` and `/quote`
- **Missing:**
  - FastAPI `/profile` uses CSV loader (not database)
  - No database integration for company profiles
- **Required for Completion:**
  - Database schema for company profiles
  - FastAPI endpoint to read from database
  - Or: Use external API (Alpaca REST API)

---

#### ❌ `GET /api/stocks/:ticker/financials`
- **Status:** ❌ **Not Fully Implemented**
- **What Works:**
  - Controller calls `stockService.getFinancials()`
  - Service calls FastAPI `/financials`
- **Missing:**
  - FastAPI `/financials` endpoint exists but uses CSV loader
  - No ticker parameter (returns hardcoded data)
- **Required for Completion:**
  - FastAPI `/api/financials?company={ticker}` endpoint (already exists)
  - Update ExpressJS to pass ticker parameter
  - Connect to PostgreSQL `financial_oltp` schema

---

#### ❌ `GET /api/stocks/:ticker/news`
- **Status:** ❌ **Not Fully Implemented**
- **What Works:**
  - Controller calls `stockService.getNews()`
  - Service calls FastAPI `/news`
- **Missing:**
  - FastAPI `/news` doesn't accept ticker parameter
  - Returns hardcoded news
- **Required for Completion:**
  - FastAPI `/news?ticker={ticker}` endpoint
  - Integration with news API (Finnhub, Alpha Vantage, etc.)

---

### 6.2 FastAPI Endpoints

#### ✅ `GET /bars/{symbol}`
- **Status:** ✅ **Fully Implemented**
- **What Works:**
  - JOIN query correctly joins `stock_bars_staging` with `stocks`
  - Returns proper JSON format
  - Handles symbol not found (404)
  - Handles empty results
- **Missing:**
  - No Redis caching (Redis client exists but not used)
  - No pagination (only limit)
- **Required for Completion:**
  - Implement Redis caching with TTL
  - Add pagination (offset/limit)

---

#### ✅ `GET /bars/{symbol}/range`
- **Status:** ✅ **Fully Implemented**
- **What Works:**
  - Date parsing and validation
  - JOIN query with date range filter
  - Returns proper JSON format
- **Missing:**
  - No Redis caching
  - No index optimization for date range queries
- **Required for Completion:**
  - Redis caching for common date ranges
  - Verify database indexes on `ts` column

---

#### ✅ `GET /bars/latest`
- **Status:** ✅ **Fully Implemented**
- **What Works:**
  - `DISTINCT ON` query correctly gets latest bar per symbol
  - Groups results properly
- **Missing:**
  - No Redis caching
  - Limit calculation (`limit * 10`) is a workaround
- **Required for Completion:**
  - Better query to get exactly N latest bars per symbol
  - Redis caching

---

#### ⚠️ `GET /quote?ticker={ticker}`
- **Status:** ⚠️ **Partially Implemented**
- **What Works:**
  - Queries `stock_eod_prices` for latest EOD price
  - Calculates change and percent change
  - Falls back to CSV loader if stock not found
- **Missing:**
  - **Does NOT read from `stock_trades_realtime`** (real-time trades)
  - Returns EOD price, not current real-time price
  - No integration with real-time data pipeline
- **Required for Completion:**
  - New endpoint: `GET /quote/realtime?ticker={ticker}`
  - Query `stock_trades_realtime` for latest trade
  - Or: Read from Redis for ultra-low latency
  - Fallback to EOD if real-time unavailable

---

#### ❌ `GET /profile?ticker={ticker}`
- **Status:** ❌ **Not Fully Implemented**
- **What Works:**
  - Uses CSV loader to get profile data
- **Missing:**
  - No database integration
  - No external API integration (Alpaca REST API)
- **Required for Completion:**
  - Database schema for company profiles
  - Or: Integrate with Alpaca REST API `/v2/assets/{symbol}`
  - Cache profiles in Redis

---

#### ❌ `GET /financials` (Legacy)
- **Status:** ❌ **Deprecated**
- **What Works:**
  - Returns CSV-loaded financial data
- **Missing:**
  - No ticker parameter
  - Uses CSV, not database
- **Required for Completion:**
  - Use `/api/financials?company={ticker}&type={IS|BS|CF}&period={quarterly|annual}` instead
  - This endpoint is already implemented and uses PostgreSQL

---

#### ✅ `GET /api/financials?company={ticker}&type={IS|BS|CF}&period={quarterly|annual}`
- **Status:** ✅ **Fully Implemented**
- **What Works:**
  - Queries PostgreSQL `financial_oltp` schema
  - Returns pivoted financial data
  - Supports Income Statement, Balance Sheet, Cash Flow
  - Supports quarterly and annual periods
- **Missing:**
  - No Redis caching (Redis client exists but not used)
- **Required for Completion:**
  - Implement Redis caching with TTL

---

## Section 7: Missing Pieces + Recommendations

### 7.1 Critical Missing Features

#### 7.1.1 Real-Time Quote Endpoint
**Problem:** `/quote` endpoint returns EOD price, not real-time price

**Solution:**
```python
# FastAPI: server.py
@app.get("/quote/realtime")
async def get_realtime_quote(ticker: str):
    # Option 1: Query PostgreSQL
    cur.execute("""
        SELECT price, ts, size
        FROM market_data_oltp.stock_trades_realtime t
        JOIN market_data_oltp.stocks s ON s.stock_id = t.stock_id
        WHERE s.stock_ticker = %s
        ORDER BY ts DESC
        LIMIT 1
    """, (ticker,))
    
    # Option 2: Read from Redis (ultra-low latency)
    # latest_price = redis_client.get(f"price:{ticker}")
```

**Priority:** 🔴 **High** - Real-time quotes are core functionality

---

#### 7.1.2 Redis Caching for FastAPI Endpoints
**Problem:** FastAPI endpoints don't use Redis caching (Redis client exists but unused)

**Solution:**
```python
# FastAPI: server.py
@app.get("/bars/{symbol}")
async def get_bars(symbol: str, limit: int = 100):
    # Check Redis cache
    cache_key = f"bars:{symbol}:{limit}"
    cached = REDIS_CLIENT.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Query database
    bars = query_bars_from_db(symbol, limit)
    
    # Cache for 60 seconds
    REDIS_CLIENT.setex(cache_key, 60, json.dumps(bars))
    return bars
```

**Priority:** 🟡 **Medium** - Improves performance but not critical

---

#### 7.1.3 Input Validation in ExpressJS
**Problem:** ExpressJS routes don't validate inputs (symbol format, date ranges, etc.)

**Solution:**
```typescript
// expressjs-server/src/api/validators/bars.validator.ts
export const barsSymbolSchema = z.object({
  symbol: z.string().regex(/^[A-Z]{1,5}$/, "Invalid symbol format"),
  limit: z.number().int().min(1).max(1000).optional().default(100),
});

export const barsRangeSchema = z.object({
  symbol: z.string().regex(/^[A-Z]{1,5}$/),
  start: z.string().datetime(),
  end: z.string().datetime(),
  limit: z.number().int().min(1).max(10000).optional().default(1000),
}).refine((data) => new Date(data.start) < new Date(data.end), {
  message: "Start date must be before end date",
});
```

**Priority:** 🟡 **Medium** - Prevents invalid requests

---

#### 7.1.4 Error Handling for FastAPI Failures
**Problem:** ExpressJS doesn't handle FastAPI timeouts or errors gracefully

**Solution:**
```typescript
// expressjs-server/src/api/routes/bars.routes.ts
router.get("/:symbol", asyncHandler(async (req: Request, res: Response) => {
  try {
    const data = await pythonClient.get(`/bars/${symbol}?limit=${limit}`);
    res.json(data);
  } catch (error) {
    if (error instanceof ExternalApiError) {
      if (error.message.includes("timeout")) {
        return res.status(504).json({
          success: false,
          error: "FastAPI server timeout",
        });
      }
    }
    throw error; // Re-throw for error handler
  }
}));
```

**Priority:** 🟡 **Medium** - Improves user experience

---

### 7.2 Architecture Improvements

#### 7.2.1 Separate Real-Time and Historical Quote Endpoints
**Current:** `/quote` returns EOD price (confusing)

**Recommendation:**
- `/quote?ticker={ticker}` → EOD price (current behavior)
- `/quote/realtime?ticker={ticker}` → Latest trade from `stock_trades_realtime`
- `/quote/redis?ticker={ticker}` → Latest price from Redis (ultra-low latency)

---

#### 7.2.2 Add Health Check Endpoints
**Current:** Basic health checks exist

**Recommendation:**
```python
# FastAPI
@app.get("/health/detailed")
async def detailed_health():
    return {
        "status": "healthy",
        "database": check_postgres_connection(),
        "redis": check_redis_connection(),
        "kafka": check_kafka_connection(),  # If needed
    }
```

```typescript
// ExpressJS
app.get("/health/detailed", async (req, res) => {
  const health = {
    status: "healthy",
    redis: await checkRedisConnection(),
    fastapi: await checkFastAPIConnection(),
  };
  res.json(health);
});
```

---

#### 7.2.3 Add Metrics and Monitoring
**Missing:** No metrics collection

**Recommendation:**
- Add Prometheus metrics for:
  - Request latency (ExpressJS, FastAPI)
  - Kafka consumer lag
  - Redis PubSub message rate
  - Database query performance
- Add logging for:
  - Slow queries (>100ms)
  - Failed FastAPI calls
  - Redis connection issues

---

### 7.3 Data Flow Improvements

#### 7.3.1 Bars Should Also Be Published to Redis (Optional)
**Current:** Only trades are published to Redis

**Recommendation:**
- Publish bars to Redis Stream (not PubSub) for charting
- Frontend can subscribe to bar updates for real-time charts
- Use Redis Streams for persistence and consumer groups

---

#### 7.3.2 Add WebSocket Authentication
**Current:** WebSocket connections are open to all

**Recommendation:**
```typescript
// ExpressJS WebSocket
io.use((socket, next) => {
  const token = socket.handshake.auth.token;
  if (validateToken(token)) {
    next();
  } else {
    next(new Error("Authentication failed"));
  }
});
```

---

### 7.4 Database Optimizations

#### 7.4.1 Add Database Indexes
**Current:** Basic indexes exist

**Recommendation:**
```sql
-- Optimize date range queries
CREATE INDEX idx_bars_ts_symbol ON market_data_oltp.stock_bars_staging (ts DESC, stock_id);

-- Optimize latest bar queries
CREATE INDEX idx_bars_latest ON market_data_oltp.stock_bars_staging (stock_id, ts DESC);

-- Optimize real-time trade queries
CREATE INDEX idx_trades_latest ON market_data_oltp.stock_trades_realtime (stock_id, ts DESC);
```

---

#### 7.4.2 Add Database Connection Pooling
**Current:** Each FastAPI request opens new connection

**Recommendation:**
```python
# FastAPI: Use connection pool
from psycopg2 import pool

connection_pool = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=20,
    **DB_CONFIG
)

@app.get("/bars/{symbol}")
async def get_bars(symbol: str):
    conn = connection_pool.getconn()
    try:
        # Use connection
    finally:
        connection_pool.putconn(conn)
```

---

### 7.5 Summary of Priorities

| Feature | Priority | Effort | Impact |
|---------|----------|--------|--------|
| Real-time quote endpoint | 🔴 High | Medium | High |
| Redis caching for FastAPI | 🟡 Medium | Low | Medium |
| Input validation | 🟡 Medium | Low | Medium |
| Error handling | 🟡 Medium | Low | Medium |
| Health check endpoints | 🟢 Low | Low | Low |
| Metrics/monitoring | 🟡 Medium | High | High |
| WebSocket authentication | 🟡 Medium | Medium | Medium |
| Database connection pooling | 🟡 Medium | Medium | Medium |
| Database indexes | 🟢 Low | Low | Medium |

---

## Conclusion

### Current State
- ✅ **Real-time trade flow:** Fully functional (Alpaca → Redis → ExpressJS → Frontend)
- ✅ **Bar persistence flow:** Fully functional (Alpaca → Kafka → PostgreSQL)
- ✅ **Bar query flow:** Fully functional (FastAPI → PostgreSQL → ExpressJS → Frontend)
- ⚠️ **Quote endpoints:** Partially functional (EOD prices only, no real-time)
- ❌ **Stock details endpoints:** Not fully implemented (missing database integration)

### Key Strengths
1. Clean separation of real-time and persistence paths
2. Proper use of Kafka for durable message storage
3. Efficient batch processing in consumers
4. Good error handling in database operations

### Key Weaknesses
1. No real-time quote endpoint (only EOD)
2. Missing Redis caching in FastAPI
3. Limited input validation
4. No metrics/monitoring

### Next Steps
1. Implement real-time quote endpoint (read from `stock_trades_realtime`)
2. Add Redis caching to FastAPI endpoints
3. Add input validation middleware
4. Set up monitoring and metrics

---

**Document End**


