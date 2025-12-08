import Redis from "ioredis";
import { config } from "../../config";
import { logger } from "../../utils";
import { wrapRedisCall } from "../../utils/errorHandler";

let client: Redis | null = null;

export function redisClient(): Redis {
  if (!client) {
    // LOGIC MỚI: Ưu tiên dùng REDIS_URL nếu có (Dành cho Production/Upstash)
    if (config.redisUrl) {
      logger.info("[RedisClient] Initializing with REDIS_URL...");
      client = new Redis(config.redisUrl, {
        lazyConnect: true,
        // Upstash yêu cầu TLS, ioredis sẽ tự nhận diện qua protocol 'rediss://'
        // nhưng ta cứ thêm dòng này cho chắc chắn connect không bị treo
        tls: config.redisUrl.startsWith("rediss://") ? { rejectUnauthorized: false } : undefined
      });
    } else {
      // Logic cũ: Dùng Host/Port (Dành cho Local Docker)
      logger.info(`[RedisClient] Initializing with Host: ${config.redisHost}`);
      client = new Redis({
        host: config.redisHost,
        port: config.redisPort,
        lazyConnect: true,
      });
    }

    client.on("error", (err) => {
      logger.error("[RedisClient] Error", err);
    });

    void wrapRedisCall(
      async () => {
        await client!.connect();
        logger.success(
          `[RedisClient] Connected successfully`
        );
      },
      "connect"
    );
  }

  return client;
}



