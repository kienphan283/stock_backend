/**
 * Application Entry Point
 * Initializes and starts the Express server with Dependency Injection
 */

import express from "express";
import cors from "cors";
import helmet from "helmet";
import { config } from "./infrastructure/config";
import { logger } from "./utils";
import * as swaggerUi from "swagger-ui-express";
import { swaggerSpec } from "./infrastructure/swagger";

// Infrastructure Layer
import {
  PythonFinancialClient,
  MockPortfolioRepository,
} from "./infrastructure";

// Core Layer (Services)
import {
  StockService,
  PortfolioService,
  DividendService,
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

  // Swagger Documentation
  app.use("/api-docs", swaggerUi.serve, swaggerUi.setup(swaggerSpec));

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
 * Start Server
 */
const startServer = () => {
  const app = createApp();
  const PORT = config.port;

  app.listen(PORT, () => {
    logger.success(`🚀 Backend server running on port ${PORT}`);
    logger.info(`📝 Environment: ${config.nodeEnv}`);
    logger.info(`🔗 CORS Origins: ${config.corsOrigins.join(", ")}`);
    logger.info(`🐍 Python API: ${config.pythonApiUrl}`);
  });
};

// Start the server
startServer();

export { createApp };
