/**
 * API Routes Index
 * Combines all route modules
 */

import { Router } from "express";
import {
  StockController,
  PortfolioController,
  DividendController,
} from "../controllers";
import { createStockRouter } from "./stocks.routes";
import { createPortfolioRouter } from "./portfolio.routes";
import { createDividendRouter } from "./dividends.routes";
import { createFinancialsRouter } from "./financials.routes";

export interface RoutesDependencies {
  stockController: StockController;
  portfolioController: PortfolioController;
  dividendController: DividendController;
}

export const createApiRoutes = (dependencies: RoutesDependencies): Router => {
  const router = Router();

  // Mount routes
  router.use("/stocks", createStockRouter(dependencies.stockController));
  router.use(
    "/portfolio",
    createPortfolioRouter(dependencies.portfolioController)
  );
  router.use(
    "/dividends",
    createDividendRouter(dependencies.dividendController)
  );
  router.use("/financials", createFinancialsRouter());

  // Health check
  router.get("/health", (req, res) => {
    res.json({
      success: true,
      message: "API is running",
      timestamp: new Date().toISOString(),
    });
  });

  return router;
};
