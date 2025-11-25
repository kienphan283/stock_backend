/**
 * Application Entry Point
 * Initializes and starts the Express server with Dependency Injection
 */

import "./config/env";

import express from "express";
import { createServer } from "http";
import cors from "cors";
import helmet from "helmet";
import { config } from "./infrastructure/config";
import { logger } from "./utils";

// Infrastructure Layer
import {
  PythonFinancialClient,
  MockPortfolioRepository,
  RedisStreamClient,
} from "./infrastructure";

// Core Layer (Services)
import {
  StockService,
  PortfolioService,
  DividendService,
  WebSocketService,
} from "./core/services";

// API Layer (Controllers & Routes)
import {
  StockController,
  PortfolioController,
  DividendController,
} from "./api/controllers";
import { createApiRoutes } from "./api/routes";
import {
  errorHandler,
  notFoundHandler,
  requestLogger,
} from "./api/middlewares";

/**
 * Dependency Injection Container
 * Manually wires up all dependencies
 */
class Container {
  // Infrastructure
  public readonly financialClient = new PythonFinancialClient();
  public readonly portfolioRepository = new MockPortfolioRepository();

  // Services
  public readonly stockService = new StockService(this.financialClient);
  public readonly portfolioService = new PortfolioService(
    this.portfolioRepository
  );
  public readonly dividendService = new DividendService(this.financialClient);

  // Controllers
  public readonly stockController = new StockController(this.stockService);
  public readonly portfolioController = new PortfolioController(
    this.portfolioService,
    this.stockService
  );
  public readonly dividendController = new DividendController(
    this.dividendService
  );
}

/**
 * Application Setup
 */
const createApp = () => {
  const app = express();
  const container = new Container();

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

  // Custom request logging
  if (config.isDevelopment) {
    app.use(requestLogger);
  }

  // API Routes with Dependency Injection
  app.use(
    "/api",
    createApiRoutes({
      stockController: container.stockController,
      portfolioController: container.portfolioController,
      dividendController: container.dividendController,
    })
  );

  // Health check endpoint
  app.get("/health", (req, res) => {
    res.json({
      status: "OK",
      timestamp: new Date().toISOString(),
      environment: config.nodeEnv,
    });
  });

  // Error Handling
  app.use(notFoundHandler);
  app.use(errorHandler);

  return app;
};

/**
 * Start Server with WebSocket support
 */
const startServer = async () => {
  const app = createApp();
  const httpServer = createServer(app);
  const PORT = config.port;

  // Initialize Redis and WebSocket
  try {
    logger.info("Initializing Redis connection...");
    const redisClient = new RedisStreamClient();
    await redisClient.connect();

    const wsService = new WebSocketService(redisClient);
    wsService.initialize(httpServer);

    // Graceful shutdown
    process.on("SIGTERM", async () => {
      logger.info("SIGTERM received, shutting down gracefully...");
      await wsService.close();
      httpServer.close();
      process.exit(0);
    });

    process.on("SIGINT", async () => {
      logger.info("SIGINT received, shutting down gracefully...");
      await wsService.close();
      httpServer.close();
      process.exit(0);
    });
  } catch (error) {
    logger.error(`Failed to initialize WebSocket service: ${error}`);
    // Continue without WebSocket if Redis is unavailable
  }

  httpServer.listen(PORT, () => {
    logger.success(`🚀 Backend server running on port ${PORT}`);
    logger.info(`📝 Environment: ${config.nodeEnv}`);
    logger.info(`🔗 CORS Origins: ${config.corsOrigins.join(", ")}`);
    logger.info(`🐍 Python API: ${config.pythonApiUrl}`);
    logger.info(`📡 WebSocket server enabled`);
  });
};

// Start the server
startServer().catch((error) => {
  logger.error(`Failed to start server: ${error}`);
  process.exit(1);
});

export { createApp };
