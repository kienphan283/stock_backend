/**
 * WebSocket Service
 * Manages WebSocket connections and broadcasts real-time trade data
 */

import { Server as HttpServer } from "http";
import { Server as SocketIOServer, Socket } from "socket.io";
import { RedisStreamClient } from "../../infrastructure/redis";
import { config } from "../../infrastructure/config";
import { logger } from "../../utils";

export class WebSocketService {
  private io: SocketIOServer | null = null;
  private redisClient: RedisStreamClient;
  private connectedClients = new Set<Socket>();

  constructor(redisClient: RedisStreamClient) {
    this.redisClient = redisClient;
  }

  /**
   * Initialize WebSocket server
   */
  initialize(httpServer: HttpServer): void {
    this.io = new SocketIOServer(httpServer, {
      cors: {
        origin: config.corsOrigins,
        methods: ["GET", "POST"],
        credentials: true,
      },
      transports: ["websocket", "polling"],
    });

    this.io.on("connection", (socket: Socket) => {
      this.handleConnection(socket);
    });

    // Start listening to Redis
    this.startRedisListener();

    logger.success("✓ WebSocket server initialized");
  }

  /**
   * Handle new WebSocket connection
   */
  private handleConnection(socket: Socket): void {
    this.connectedClients.add(socket);
    logger.info(`Client connected: ${socket.id} (Total: ${this.connectedClients.size})`);

    socket.on("disconnect", () => {
      this.connectedClients.delete(socket);
      logger.info(`Client disconnected: ${socket.id} (Total: ${this.connectedClients.size})`);
    });

    socket.on("subscribe", (symbol: string) => {
      logger.info(`Client ${socket.id} subscribed to ${symbol}`);
      socket.join(`symbol:${symbol}`);
    });

    socket.on("unsubscribe", (symbol: string) => {
      logger.info(`Client ${socket.id} unsubscribed from ${symbol}`);
      socket.leave(`symbol:${symbol}`);
    });

    // Send connection confirmation
    socket.emit("connected", {
      message: "Connected to real-time stock data stream",
      timestamp: new Date().toISOString(),
    });
  }

  /**
   * Start listening to Redis PubSub channel
   */
  private async startRedisListener(): Promise<void> {
    try {
      await this.redisClient.subscribeToTrades(
        config.redisChannelTrades,
        (tradeData: any) => {
          // Broadcast to all clients subscribed to this symbol
          const symbol = tradeData.symbol;
          if (symbol && this.io) {
            this.io.to(`symbol:${symbol}`).emit("trade", tradeData);
            // Also broadcast to all clients (for general feed)
            this.io.emit("trade", tradeData);
          }
        }
      );
    } catch (error) {
      logger.error(`Error starting Redis listener: ${error}`);
    }
  }

  /**
   * Broadcast message to all connected clients
   */
  broadcast(event: string, data: any): void {
    if (this.io) {
      this.io.emit(event, data);
    }
  }

  /**
   * Broadcast to specific room (symbol)
   */
  broadcastToSymbol(symbol: string, event: string, data: any): void {
    if (this.io) {
      this.io.to(`symbol:${symbol}`).emit(event, data);
    }
  }

  /**
   * Get connected clients count
   */
  getConnectedCount(): number {
    return this.connectedClients.size;
  }

  /**
   * Close WebSocket server
   */
  async close(): Promise<void> {
    if (this.io) {
      this.io.close();
      this.io = null;
    }
    await this.redisClient.disconnect();
    logger.info("WebSocket service closed");
  }
}

