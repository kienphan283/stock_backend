// SERVICE BOUNDARY: This service must NOT access Postgres or Kafka.
// It can only call market-api-service via HTTP and read Redis Streams.

/**
 * Gateway Service Entry Point
 * Smart REST API Gateway - proxies to market-api-service
 * No business logic, no DB access
 */

import express from "express";
import cors from "cors";
import helmet from "helmet";
import { createServer } from "http";
import { Server } from "socket.io";
import { config } from "./config";
import { logger } from "./utils";
import { createApiRoutes } from "./api/routes";
import {
  apiLimiter,
  errorHandler,
  metricsHandler,
  metricsMiddleware,
  notFoundHandler,
  requestLogger,
} from "./api/middlewares";
import { SocketService } from "./websocket/socket.service";

/**
 * Application Setup
 */
const createApp = () => {
  const app = express();
  const httpServer = createServer(app);
  const io = new Server(httpServer, {
    cors: {
      origin: config.corsOrigins,
      credentials: true,
    },
    // Tối ưu WebSocket connection để tránh ngắt kết nối
    pingTimeout: 60000, // 60 seconds - tăng timeout để tránh disconnect
    pingInterval: 25000, // 25 seconds - gửi ping mỗi 25s để keep-alive
    transports: ["websocket", "polling"], // Cho phép cả websocket và polling fallback
    allowEIO3: true, // Backward compatibility
  });

  // Initialize WebSocket service (owns RedisWebSocketBridge lifecycle)
  const socketService = new SocketService(io);

  // Middleware
  app.use(
    cors({
      origin: config.corsOrigins,
      credentials: true,
    })
  );

  app.use(
    helmet({
      crossOriginResourcePolicy: { policy: "cross-origin" },
    })
  );

  app.use(express.json());
  app.use(express.urlencoded({ extended: true }));
  app.use(metricsMiddleware);

  // Custom request logging
  if (config.isDevelopment) {
    app.use(requestLogger);
  }

  // API Routes (pure proxies to market-api-service)
  app.use("/api", apiLimiter, createApiRoutes());

  // Prometheus metrics
  app.get("/metrics", metricsHandler);

  // Health check endpoint
  app.get("/health", (req, res) => {
    res.json({
      status: "OK",
      timestamp: new Date().toISOString(),
      environment: config.nodeEnv,
      service: "gateway-service",
    });
  });

  // Error Handling
  app.use(notFoundHandler);
  app.use(errorHandler);

  return { app, httpServer, socketService };
};

/**
 * Start Server
 */
const startServer = () => {
  const { app, httpServer, socketService } = createApp();
  const PORT = config.port;

  httpServer.listen(PORT, () => {
    logger.success(`🚀 Gateway service running on port ${PORT}`);
    logger.info(`📝 Environment: ${config.nodeEnv}`);
    logger.info(`🔗 CORS Origins: ${config.corsOrigins.join(", ")}`);
    logger.info(`🐍 Market API: ${config.marketApiUrl}`);
    logger.info(`📡 WebSocket: Enabled`);
  });
};

// Start the server
startServer();

export { createApp };

