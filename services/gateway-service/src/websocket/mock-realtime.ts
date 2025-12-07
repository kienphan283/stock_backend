// MODULE: Mock realtime WebSocket generator (dev/test only).
// PURPOSE: Emit synthetic `bar_update` and `trade_update` events when
// real Alpaca / Redis Streams data is not available (e.g. outside trading hours).
//
// This module does NOT touch Redis or Kafka – it only uses the Socket.io
// server instance already created in `index.ts`.
//
// Enable via env:
//   MOCK_REALTIME_WS=true

import { logger } from "../utils";
import { DEFAULT_TICKERS } from "../config/tickers.constants";

type IoType = {
  emit: (event: string, payload: any) => void;
};

// Use all 30 tickers from constants
const SYMBOLS = [...DEFAULT_TICKERS];

function randomSymbol(): string {
  return SYMBOLS[Math.floor(Math.random() * SYMBOLS.length)];
}

function createMockBar(symbol: string) {
  const base = 150 + Math.random() * 10;
  const open = base + (Math.random() - 0.5) * 2;
  const close = base + (Math.random() - 0.5) * 3;
  const high = Math.max(open, close) + Math.random() * 1.5;
  const low = Math.min(open, close) - Math.random() * 1.5;

  return {
    symbol: symbol.toUpperCase(),
    open: Number(open.toFixed(2)),
    high: Number(high.toFixed(2)),
    low: Number(low.toFixed(2)),
    close: Number(close.toFixed(2)),
    volume: 500_000 + Math.floor(Math.random() * 1_500_000),
    timestamp: Date.now(),
    type: "bar" as const,
  };
}

function createMockTrade(symbol: string) {
  const base = 150 + Math.random() * 10;

  return {
    symbol: symbol.toUpperCase(),
    price: Number(base.toFixed(2)),
    size: 100 + Math.floor(Math.random() * 1_000),
    timestamp: Date.now(),
    type: "trade" as const,
  };
}

export function startMockRealtime(io: IoType) {
  logger.info(
    "[MockRealtime] Enabled - emitting synthetic bar_update / trade_update events"
  );

  const barInterval = setInterval(() => {
    const symbol = randomSymbol();
    const payload = createMockBar(symbol);
    io.emit("bar_update", payload);
    logger.info("[MockRealtime] Emitted bar_update", payload);
  }, 3000); // every 3s

  const tradeInterval = setInterval(() => {
    const symbol = randomSymbol();
    const payload = createMockTrade(symbol);
    io.emit("trade_update", payload);
    logger.info("[MockRealtime] Emitted trade_update", payload);
  }, 3000); // every 3s

  return () => {
    clearInterval(barInterval);
    clearInterval(tradeInterval);
    logger.info("[MockRealtime] Stopped");
  };
}


