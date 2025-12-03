// NOTE: This file mirrors Python's `shared/realtime/redis_streams.py`.
// Values MUST remain exactly the same.

/**
 * Realtime constants shared within the gateway-service.
 *
 * These values mirror the Redis Streams configuration defined in
 * `shared/realtime/redis_streams.py`. They MUST NOT be changed unless the
 * corresponding Python constants are updated in lockstep.
 */

export const GATEWAY_STOCK_TRADES_STREAM = "market:realtime:trades";
export const GATEWAY_STOCK_BARS_STREAM = "market:realtime:bars";

export const GATEWAY_CONSUMER_GROUP = "gateway_stream_consumers";
export const GATEWAY_CONSUMER_NAME = "gateway-consumer";


