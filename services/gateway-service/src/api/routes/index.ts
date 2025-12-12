/**
 * API Routes Index
 * Pure proxy routes to market-api-service
 */

import { Router } from "express";
import { createStockRouter } from "./stocks.routes";
// import { createPortfolioRouter } from "./portfolio.routes";
import { createDividendRouter } from "./dividends.routes";
import { createFinancialsRouter } from "./financials.routes";
import { createMarketRouter } from "./market.routes";
// import { createAuthRouter } from "./auth.routes";

export const createApiRoutes = (): Router => {
  const router = Router();

  // Mount routes (all are pure proxies)
  router.use("/stocks", createStockRouter());
  // router.use("/portfolio", createPortfolioRouter());
  router.use("/dividends", createDividendRouter());
  router.use("/financials", createFinancialsRouter());
  router.use("/market", createMarketRouter());
  // router.use("/auth", createAuthRouter());

  // Health check
  router.get("/health", (req, res) => {
    res.json({
      success: true,
      message: "API is running",
      timestamp: new Date().toISOString(),
      service: "gateway-service",
    });
  });

  return router;
};
