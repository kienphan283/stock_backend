/**
 * Redis Client for Real-Time Data Streaming
 * Connects to Redis PubSub for receiving trade updates
 */

import { createClient, RedisClientType } from "redis";
import { config } from "../config";
import { logger } from "../../utils";

export class RedisStreamClient {
  private client: RedisClientType | null = null;
  private subscriber: RedisClientType | null = null;
  private isConnected = false;

  /**
   * Connect to Redis
   * Uses Docker service name "redis" when running in containers
   * MUST use hostname "redis" in Docker, NOT IP address or localhost
   */
  async connect(): Promise<void> {
    try {
      // FIXED: Explicitly use environment variable with fallback to "redis"
      // In Docker: REDIS_HOST=redis (service name) - MUST use service name
      // Local dev: REDIS_HOST=localhost (or from .env)
      // NEVER use IP addresses or localhost in Docker
      const redisHost = process.env.REDIS_HOST || config.redisHost || "redis";
      const redisPort = Number(process.env.REDIS_PORT) || config.redisPort || 6379;
      
      // Validate host is not an IP address or localhost in Docker
      if (redisHost === "localhost" || redisHost === "127.0.0.1" || redisHost.startsWith("::1") || /^\d+\.\d+\.\d+\.\d+$/.test(redisHost)) {
        logger.warn(`⚠️  Warning: Redis host is set to ${redisHost}. In Docker, use service name "redis" instead.`);
      }
      
      logger.info(`Connecting to Redis at ${redisHost}:${redisPort} (using hostname, not IP)`);
      
      // Create subscriber client (separate connection for pub/sub)
      // FIXED: Explicitly use hostname, not IP address
      this.subscriber = createClient({
        socket: {
          host: redisHost,  // MUST be "redis" in Docker, NOT IP or localhost
          port: redisPort,
          connectTimeout: 10000,  // 10 second timeout
          reconnectStrategy: (retries) => {
            if (retries > 10) {
              logger.error("Redis connection failed after 10 retries");
              return new Error("Redis connection failed");
            }
            const delay = Math.min(retries * 100, 3000);
            logger.info(`Retrying Redis connection in ${delay}ms (attempt ${retries})`);
            return delay;
          },
        },
      });

      // Set up event handlers BEFORE connecting
      this.subscriber.on("error", (err) => {
        logger.error(`Redis Subscriber Error: ${err}`);
        this.isConnected = false;
      });

      this.subscriber.on("connect", () => {
        logger.info(`Redis Subscriber connecting to ${redisHost}:${redisPort}...`);
      });

      this.subscriber.on("ready", () => {
        logger.success(`✓ Redis Subscriber connected to ${redisHost}:${redisPort}`);
        this.isConnected = true;
      });

      this.subscriber.on("reconnecting", () => {
        logger.info(`Redis Subscriber reconnecting to ${redisHost}:${redisPort}...`);
      });

      this.subscriber.on("end", () => {
        logger.warn("Redis Subscriber connection ended");
        this.isConnected = false;
      });

      // FIXED: Connect with explicit error handling
      // The connect() promise resolves when connection is established
      await this.subscriber.connect();
      
      // Give a moment for ready event
      await new Promise(resolve => setTimeout(resolve, 500));
      
      if (!this.isConnected) {
        logger.warn("Redis connection established but ready event not yet fired");
      }
    } catch (error) {
      logger.error(`Failed to connect to Redis: ${error}`);
      this.isConnected = false;
      throw error;
    }
  }

  /**
   * Subscribe to trade channel
   * @param channel Channel name
   * @param callback Callback function for messages
   */
  async subscribeToTrades(
    channel: string,
    callback: (message: any) => void
  ): Promise<void> {
    if (!this.subscriber) {
      throw new Error("Redis subscriber not initialized");
    }

    try {
      await this.subscriber.subscribe(channel, (message, channelName) => {
        try {
          const tradeData = JSON.parse(message);
          callback(tradeData);
        } catch (error) {
          logger.error(`Error parsing Redis message: ${error}`);
        }
      });

      logger.info(`✓ Subscribed to Redis channel: ${channel}`);
    } catch (error) {
      logger.error(`Error subscribing to Redis channel: ${error}`);
      throw error;
    }
  }

  /**
   * Unsubscribe from channel
   */
  async unsubscribe(channel: string): Promise<void> {
    if (!this.subscriber) {
      return;
    }

    try {
      await this.subscriber.unsubscribe(channel);
      logger.info(`Unsubscribed from channel: ${channel}`);
    } catch (error) {
      logger.error(`Error unsubscribing: ${error}`);
    }
  }

  /**
   * Disconnect from Redis
   */
  async disconnect(): Promise<void> {
    if (this.subscriber) {
      await this.subscriber.quit();
      this.subscriber = null;
    }
    if (this.client) {
      await this.client.quit();
      this.client = null;
    }
    this.isConnected = false;
    logger.info("Redis client disconnected");
  }

  get connected(): boolean {
    return this.isConnected;
  }
}

