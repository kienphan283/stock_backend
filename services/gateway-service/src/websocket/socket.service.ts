// MODULE: WebSocket connection manager.
// PURPOSE: Manage Socket.IO connections and delegate streaming to Redis bridge.

/**
 * WebSocket Service
 * Manages Socket.io connections and broadcasts
 */

import { logger } from "../utils";
import { wrapRedisCall, wrapWsEmit } from "../utils/errorHandler";
import { RedisWebSocketBridge } from "./redis-bridge";

export class SocketService {
  private io: any;
  private bridge: RedisWebSocketBridge;

  constructor(io: any) {
    this.io = io;
    this.bridge = new RedisWebSocketBridge(io);
    this.setupConnection();
    this.startBridge();
  }

  private setupConnection() {
    this.io.on("connection", (socket: any) => {
      logger.info(`[WebSocket] Client connected: ${socket.id}`);

      // Handle client subscriptions
      socket.on("subscribe", (payload: { symbol?: string } | string) => {
        const symbol =
          typeof payload === "string" ? payload : payload?.symbol ?? undefined;
        logger.info(
          `[WebSocket] Client ${socket.id} subscribed to ${symbol ?? "UNKNOWN"}`
        );
        if (symbol) {
          void wrapWsEmit(() => socket.join(symbol), `join:${symbol}`);
        }
      });

      socket.on("unsubscribe", (payload: { symbol?: string } | string) => {
        const symbol =
          typeof payload === "string" ? payload : payload?.symbol ?? undefined;
        logger.info(
          `[WebSocket] Client ${socket.id} unsubscribed from ${
            symbol ?? "UNKNOWN"
          }`
        );
        if (symbol) {
          void wrapWsEmit(() => socket.leave(symbol), `leave:${symbol}`);
        }
      });

      socket.on("disconnect", () => {
        logger.info(`[WebSocket] Client disconnected: ${socket.id}`);
      });
    });
  }

  private async startBridge() {
    const started = await wrapRedisCall(
      () => this.bridge.start(),
      "bridge_start",
      (error) => {
        logger.error("[WebSocket] Failed to start Redis Streams bridge:", error);
        return true;
      }
    );
    if (started !== null) {
      logger.info("[WebSocket] Redis Streams bridge started");
    }
  }

  public emitMarketUpdate(data: any) {
    this.io.emit("market_update", data);
  }

  public emitToSymbol(symbol: string, event: string, data: any) {
    this.io.to(symbol).emit(event, data);
  }

  public async stop() {
    await this.bridge.stop();
  }
}
