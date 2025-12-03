import Redis from "ioredis";
import { config } from "../../config";
import { logger } from "../../utils";
import { wrapRedisCall } from "../../utils/errorHandler";

let client: Redis | null = null;

export function redisClient(): Redis {
  if (!client) {
    client = new Redis({
      host: config.redisHost,
      port: config.redisPort,
      lazyConnect: true,
    });

    client.on("error", (err) => {
      logger.error("[RedisClient] Error", err);
    });

    void wrapRedisCall(
      async () => {
        await client!.connect();
        logger.success(
          `[RedisClient] Connected to Redis at ${config.redisHost}:${config.redisPort}`
        );
      },
      "connect"
    );
  }

  return client;
}



