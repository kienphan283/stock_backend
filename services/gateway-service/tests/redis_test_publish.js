// Temporary manual test publisher for Redis Streams → Gateway WebSocket bridge.
// Usage:
//   REDIS_URL=redis://localhost:6379 npm run test:redis

/* eslint-disable @typescript-eslint/no-var-requires */
const Redis = require("ioredis");

async function main() {
  const redisUrl = process.env.REDIS_URL || "redis://localhost:6379";
  const redis = new Redis(redisUrl);

  const payload = {
    symbol: "AAPL",
    open: 100,
    close: 103,
    high: 104,
    low: 99,
    volume: 123456,
    timestamp: Date.now(),
    type: "bar",
  };

  await redis.xadd(
    "market:realtime:bars",
    "*",
    "symbol",
    payload.symbol,
    "data",
    JSON.stringify(payload)
  );

  // eslint-disable-next-line no-console
  console.log("Test bar pushed to market:realtime:bars!");
  await redis.quit();
  process.exit(0);
}

main().catch((err) => {
  // eslint-disable-next-line no-console
  console.error("Failed to publish test bar:", err);
  process.exit(1);
});







