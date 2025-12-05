// MODULE: Redis Streams → Socket.IO bridge.
// PURPOSE: Stream events from Redis Streams to WebSocket clients.

/**
 * Redis Streams → WebSocket Bridge
 *
 * Bridges Redis Stream messages into Socket.io events:
 *  - market:realtime:trades → trade_update
 *  - market:realtime:bars   → bar_update
 *
 * Emits to room = symbol (e.g. "AAPL") so only subscribed clients receive updates.
 */

import { redisClient } from "../infrastructure/redis/redisClient";
import { logger } from "../utils";
import { wrapRedisCall, wrapWsEmit } from "../utils/errorHandler";
import {
  GATEWAY_STOCK_TRADES_STREAM,
  GATEWAY_STOCK_BARS_STREAM,
  GATEWAY_CONSUMER_GROUP,
  GATEWAY_CONSUMER_NAME,
} from "../config/realtime.constants";

const STREAM_TRADES = GATEWAY_STOCK_TRADES_STREAM;
const STREAM_BARS = GATEWAY_STOCK_BARS_STREAM;
const CONSUMER_GROUP = GATEWAY_CONSUMER_GROUP;
const CONSUMER_NAME = GATEWAY_CONSUMER_NAME;

const STREAMS: string[] = [STREAM_TRADES, STREAM_BARS];

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export class RedisWebSocketBridge {
  private io: any;
  private redis: any | null = null;
  private running = false;

  constructor(io: any) {
    this.io = io;
  }

  /**
   * Initialize Redis connection, ensure consumer groups, and start listen loop.
   */
  async start(): Promise<void> {
    if (this.running) {
      return;
    }

    logger.info("[RedisBridge] Acquiring shared Redis client from infrastructure...");
    this.redis = redisClient();

    const pingResult = await wrapRedisCall(
      () => this.redis!.ping(),
      "ping",
      (err) => {
        logger.error("[RedisBridge] Failed to ping Redis", err);
        return true;
      }
    );
    if (!pingResult) {
      return;
    }

    // Ensure consumer groups exist
    for (const stream of STREAMS) {
      await wrapRedisCall(
        async () => {
          await this.redis!.xgroup("CREATE", stream, CONSUMER_GROUP, "0-0", "MKSTREAM");
          logger.info(
            `[RedisBridge] Consumer group '${CONSUMER_GROUP}' created for stream '${stream}'`
          );
        },
        `xgroup:${stream}`,
        (err: any) => {
          if (typeof err?.message === "string" && err.message.includes("BUSYGROUP")) {
            logger.info(
              `[RedisBridge] Consumer group '${CONSUMER_GROUP}' already exists for stream '${stream}'`
            );
            return true;
          }
          logger.error(
            `[RedisBridge] Error creating consumer group for stream '${stream}'`,
            err
          );
          return true;
        }
      );
    }

    this.running = true;
    logger.info(
      `[RedisBridge] Starting stream listeners for streams: ${STREAMS.join(
        ", "
      )}`
    );
    void this.listen();
  }

  /**
   * Blocking loop that reads from Redis Streams using XREADGROUP and
   * forwards messages into Socket.io.
   */
  private async listen(): Promise<void> {
    if (!this.redis) {
      logger.error("[RedisBridge] listen() called before Redis was initialized");
      return;
    }

    const client = this.redis;

    while (this.running) {
      try {
        // BLOCK for up to 5 seconds, read up to 50 messages per stream
        const args: (string | number)[] = [
          "GROUP",
          CONSUMER_GROUP,
          CONSUMER_NAME,
          "BLOCK",
          5000,
          "COUNT",
          50,
          "STREAMS",
          ...STREAMS,
          // Use ">" so we read new messages for this consumer in the group
          ...STREAMS.map(() => ">"),
        ];

        const result = (await (client as any).xreadgroup.apply(
          client,
          args as any[]
        )) as [string, [string, string[]][]][] | null;

        if (!result) {
          continue;
        }

        for (const [stream, entries] of result) {
          const streamName = stream as string;

          for (const [id, fields] of entries) {
            const ackMessage = async () =>
              wrapRedisCall(
                () => client.xack(streamName, CONSUMER_GROUP, id),
                "xack",
                (ackErr) => {
                  logger.error(
                    `[RedisBridge] Failed to ACK message ${id} on stream ${streamName}`,
                    ackErr
                  );
                  return true;
                }
              );

            // Convert flat [field, value, field, value, ...] to map
            const messageMap: Record<string, string> = {};
            for (let i = 0; i < fields.length; i += 2) {
              const key = fields[i];
              const value = fields[i + 1];
              if (key != null && value != null) {
                messageMap[String(key)] = String(value);
              }
            }

            // Log raw Redis message
            logger.info("[RedisBridge] RAW", {
              stream: streamName,
              id,
              message: messageMap,
            });

            const raw = messageMap["data"];
            if (!raw) {
              logger.warn(
                `[RedisBridge] Missing "data" field in message ${id} on stream ${streamName}`
              );
              await ackMessage();
              continue;
            }

            let payload: any;
            try {
              payload = JSON.parse(raw);
            } catch (parseErr) {
              logger.error(
                `[RedisBridge] Failed to parse JSON for message ${id} on stream ${streamName}`,
                parseErr
              );
              await ackMessage();
              continue;
            }

            const symbol: string | undefined = payload?.symbol;
            if (!symbol) {
              logger.warn(
                `[RedisBridge] Missing symbol in parsed payload for message ${id} on stream ${streamName}`
              );
              await ackMessage();
              continue;
            }

            const event =
              streamName === STREAM_TRADES ? "trade_update" : "bar_update";

            logger.info(
              `[RedisBridge] Received ${event} for symbol ${symbol} from stream ${streamName}`,
              payload
            );

            // Emit globally and to symbol-specific room
            await wrapWsEmit(
              () => this.io.emit(event, payload),
              `emit:${event}`,
              (err) => {
                logger.error("[WS] Failed to emit global event", err);
                return true;
              }
            );
            await wrapWsEmit(
              () => this.io.to(symbol).emit(event, payload),
              `emit:${event}:${symbol}`,
              (err) => {
                logger.error(`[WS] Failed to emit event to room ${symbol}`, err);
                return true;
              }
            );
            logger.info(`[WS] Emitted ${event} to room ${symbol}`, payload);

            // Acknowledge the message so it doesn't remain pending
            await ackMessage();
          }
        }
      } catch (err) {
        logger.error("[RedisBridge] Error while reading streams:", err);
        // Brief backoff to avoid tight error loop
        await sleep(1000);
      }
    }

    logger.info("[RedisBridge] Listener stopped");
  }

  /**
   * Stop the bridge and close Redis connection.
   */
  async stop(): Promise<void> {
    this.running = false;
    if (this.redis) {
      try {
        await this.redis.quit();
      } catch (err) {
        logger.error("[RedisBridge] Error while closing Redis connection", err);
      } finally {
        this.redis = null;
      }
    }
  }
}
