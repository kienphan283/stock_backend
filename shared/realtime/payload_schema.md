# Realtime Payload Schema (Documentation Only)

This document describes the **logical schema** of realtime messages flowing
through the streaming pipeline:

Alpaca WebSocket → Kafka → Market Stream Service → Redis Streams → Gateway → WebSocket.

> This file does **not** change any runtime behavior. It only documents the
> existing contracts inferred from the code.

---

## 1. Trade payload

Produced by:
- `market-ingest-service/alpaca/websocket_client.py` (`handle_trade`)

Published to:
- Kafka topic: `stock_trades_realtime`
- Redis Stream: `market:realtime:trades`

Shape:

```jsonc
{
  "symbol": "AAPL",        // string, upper-case ticker
  "price": 195.50,         // number, last trade price
  "size": 100,             // number, trade size (shares)
  "timestamp": 1710000000, // Alpaca trade timestamp
  "type": "trade"          // literal string "trade"
}
```

The gateway (`gateway-service`) receives this JSON as a string in the Redis
Stream entry's `data` field, parses it, and emits it as-is to WebSocket
clients on the `trade_update` event.

---

## 2. Bar payload

Produced by:
- `market-ingest-service/alpaca/websocket_client.py` (`handle_bar`)

Published to:
- Kafka topic: `stock_bars_staging`
- Redis Stream: `market:realtime:bars`

Shape:

```jsonc
{
  "symbol": "AAPL",        // string, upper-case ticker
  "open": 195.00,          // number
  "high": 196.00,          // number
  "low": 194.50,           // number
  "close": 195.50,         // number
  "volume": 123456,        // number
  "timestamp": 1710000000, // Alpaca bar timestamp
  "type": "bar"            // literal string "bar"
}
```

The gateway receives this JSON as a string in Redis `data`, parses it, and
emits it to WebSocket clients on the `bar_update` event.

---

## 3. Redis Streams envelope

Market Stream Service publishes payloads to Redis Streams as:

```text
XADD market:realtime:trades * symbol "<SYMBOL>" data "<JSON>"
XADD market:realtime:bars   * symbol "<SYMBOL>" data "<JSON>"
```

Fields:

- `symbol`: string ticker, upper-case.
- `data`: JSON string of the payloads defined above.

The gateway's Redis bridge (`RedisWebSocketBridge`) expects:

- `symbol` field present and non-empty.
- `data` field containing valid JSON for the payload.

---

## 4. WebSocket events

Gateway emits:

- `trade_update` with the **trade payload** object
- `bar_update` with the **bar payload** object

Emission:

```ts
io.emit(event, payload);          // broadcast to all clients
io.to(symbol).emit(event, payload); // to room named by symbol, e.g. "AAPL"
```

Any changes to the payload structure or event names must be coordinated
across:

- `market-ingest-service` (producer)
- `market-stream-service` (Redis publisher)
- `gateway-service` (Redis bridge + WebSocket)



