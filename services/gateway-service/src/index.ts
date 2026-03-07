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
import swaggerUi from "swagger-ui-express";
import { swaggerSpec } from "./swagger";
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

  // LOGIC FIX CORS: 
  // Nếu config có chứa "*", ta set origin = true để thư viện tự động
  // phản hồi đúng tên miền của người gửi (Reflect Origin).
  // Điều này giúp vượt qua lỗi CORS khi dùng credentials: true.
  const corsOptions = {
    origin: config.corsOrigins.includes("*") ? true : config.corsOrigins,
    credentials: true,
  };

  const io = new Server(httpServer, {
    cors: corsOptions, // Áp dụng cho Socket.IO
    // Tối ưu WebSocket connection để tránh ngắt kết nối
    pingTimeout: 60000,
    pingInterval: 25000,
    transports: ["websocket", "polling"],
    allowEIO3: true,
  });

  // Initialize WebSocket service (owns RedisWebSocketBridge lifecycle)
  const socketService = new SocketService(io);

  // Middleware áp dụng cho Express API
  app.use(cors(corsOptions));

  app.use((req, res, next) => {
    logger.info(`Incoming Request: ${req.method} ${req.url} | Origin: ${req.headers.origin}`);
    next();
  });

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

  // Swagger Documentation
  app.use("/api-docs", swaggerUi.serve, swaggerUi.setup(swaggerSpec));

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

  // Explicitly bind to 0.0.0.0 so Railway's IPv4 load balancer can reach the container.
  // Without a host, Node.js may bind to '::' (IPv6-only) in Alpine, causing 502.
  httpServer.listen(PORT, "0.0.0.0", () => {
    logger.success(`🚀 Gateway service running on port ${PORT} (0.0.0.0)`);
    logger.info(`📝 Environment: ${config.nodeEnv}`);

    const originLog = config.corsOrigins.includes("*")
      ? "Allow ALL (Reflect Origin)"
      : config.corsOrigins.join(", ");

    logger.info(`🔗 CORS Origins: ${originLog}`);
    logger.info(`🐍 Market API: ${config.marketApiUrl}`);
    logger.info(`📡 WebSocket: Enabled`);
  });
};

// Global crash handlers — ensure all crashes appear in Railway logs
process.on("uncaughtException", (err) => {
  console.error("[FATAL] Uncaught Exception:", err);
  process.exit(1);
});

process.on("unhandledRejection", (reason) => {
  console.error("[FATAL] Unhandled Promise Rejection:", reason);
  process.exit(1);
});

// Start the server
startServer();

export { createApp };
