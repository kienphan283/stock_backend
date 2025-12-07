// MODULE: WebSocket connection manager.
// PURPOSE: Manage Socket.IO connections and delegate streaming to Redis bridge.

/**
 * WebSocket Service
 * Manages Socket.io connections and broadcasts
 */

import { logger } from "../utils";
import { wrapRedisCall, wrapWsEmit, ValidationError } from "../utils/errorHandler";
import { normalizeSymbol } from "../utils/validation";
import { RedisWebSocketBridge } from "./redis-bridge";
import { startMockRealtime } from "./mock-realtime";

export class SocketService {
  private io: any;
  private bridge: RedisWebSocketBridge;
  private stopMockRealtime: (() => void) | null = null;

  constructor(io: any) {
    this.io = io;
    this.bridge = new RedisWebSocketBridge(io);
    this.setupConnection();
    this.startBridge();

    // Optional mock realtime mode for development / testing when
    // real Alpaca / Redis Streams data is not available.
    if (process.env.MOCK_REALTIME_WS === "true") {
      this.stopMockRealtime = startMockRealtime(this.io);
    }
  }

  private setupConnection() {
    this.io.on("connection", (socket: any) => {
      logger.info(`[WebSocket] Client connected: ${socket.id}`);

      // Handle client subscriptions
      socket.on("subscribe", (payload: { symbol?: string } | string) => {
        try {
          const raw =
            typeof payload === "string" ? payload : payload?.symbol ?? "";
          const symbol = normalizeSymbol(raw);
          logger.info(`[WebSocket] Client ${socket.id} subscribed`, {
            symbol,
          });
          void wrapWsEmit(() => socket.join(symbol), `join:${symbol}`);
        } catch (err: any) {
          if (err instanceof ValidationError) {
            logger.warn(`[WebSocket] Rejecting invalid subscribe`, {
              client: socket.id,
              error: err.message,
            });
            socket.emit("error", { message: err.message });
          } else {
            logger.error("[WebSocket] subscribe handler failed", err);
          }
        }
      });

      socket.on("unsubscribe", (payload: { symbol?: string } | string) => {
        try {
          const raw =
            typeof payload === "string" ? payload : payload?.symbol ?? "";
          const symbol = normalizeSymbol(raw);
          logger.info(`[WebSocket] Client ${socket.id} unsubscribed`, {
            symbol,
          });
          void wrapWsEmit(() => socket.leave(symbol), `leave:${symbol}`);
        } catch (err: any) {
          if (err instanceof ValidationError) {
            logger.warn(`[WebSocket] Rejecting invalid unsubscribe`, {
              client: socket.id,
              error: err.message,
            });
            socket.emit("error", { message: err.message });
          } else {
            logger.error("[WebSocket] unsubscribe handler failed", err);
          }
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
    if (this.stopMockRealtime) {
      this.stopMockRealtime();
    }
    await this.bridge.stop();
  }
}
