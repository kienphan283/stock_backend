/**
 * Portfolio Routes
 * Defines routes for portfolio endpoints
 */

import { Router } from "express";
import { PortfolioController } from "../controllers";
import {
  validateParams,
  validateBody,
  tickerParamSchema,
  portfolioItemSchema,
  updatePortfolioItemSchema,
} from "../validators";

export const createPortfolioRouter = (
  portfolioController: PortfolioController
): Router => {
  const router = Router();

  // GET /api/portfolio - Get portfolio with values
  router.get("/", portfolioController.getPortfolio);

  // POST /api/portfolio - Add item to portfolio
  router.post(
    "/",
    validateBody(portfolioItemSchema),
    portfolioController.addToPortfolio
  );

  // PATCH /api/portfolio/:ticker - Update portfolio item
  router.patch(
    "/:ticker",
    validateParams(tickerParamSchema),
    validateBody(updatePortfolioItemSchema),
    portfolioController.updatePortfolioItem
  );

  // DELETE /api/portfolio/:ticker - Remove item from portfolio
  router.delete(
    "/:ticker",
    validateParams(tickerParamSchema),
    portfolioController.removeFromPortfolio
  );

  return router;
};
