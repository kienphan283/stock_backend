/**
 * Portfolio Routes
 * Pure proxy routes to market-api-service
 * Note: Portfolio management should be implemented in market-api-service
 */

import { Router, Request, Response } from "express";
import {
  validateParams,
  validateBody,
  tickerParamSchema,
  portfolioItemSchema,
  updatePortfolioItemSchema,
} from "../validators";
import { config } from "../../config";
import { asyncHandler } from "../middlewares";

export const createPortfolioRouter = (): Router => {
  const router = Router();
  const baseUrl = config.marketApiUrl;

  // GET /api/portfolio - Get portfolio
  // TODO: Implement portfolio endpoint in market-api-service
  router.get(
    "/",
    asyncHandler(async (req: Request, res: Response) => {
      // For now, return empty array until portfolio is implemented in market-api-service
      res.json({
        success: true,
        data: [],
        message: "Portfolio endpoint not yet implemented in market-api-service",
      });
    })
  );

  // POST /api/portfolio - Add item to portfolio
  router.post(
    "/",
    validateBody(portfolioItemSchema),
    asyncHandler(async (req: Request, res: Response) => {
      // TODO: Proxy to market-api-service when portfolio endpoint is implemented
      res.status(501).json({
        success: false,
        error: "Portfolio endpoint not yet implemented in market-api-service",
      });
    })
  );

  // PATCH /api/portfolio/:ticker - Update portfolio item
  router.patch(
    "/:ticker",
    validateParams(tickerParamSchema),
    validateBody(updatePortfolioItemSchema),
    asyncHandler(async (req: Request, res: Response) => {
      // TODO: Proxy to market-api-service when portfolio endpoint is implemented
      res.status(501).json({
        success: false,
        error: "Portfolio endpoint not yet implemented in market-api-service",
      });
    })
  );

  // DELETE /api/portfolio/:ticker - Remove item from portfolio
  router.delete(
    "/:ticker",
    validateParams(tickerParamSchema),
    asyncHandler(async (req: Request, res: Response) => {
      // TODO: Proxy to market-api-service when portfolio endpoint is implemented
      res.status(501).json({
        success: false,
        error: "Portfolio endpoint not yet implemented in market-api-service",
      });
    })
  );

  return router;
};
