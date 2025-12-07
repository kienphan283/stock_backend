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
  /**
   * @swagger
   * /portfolio:
   *   get:
   *     summary: Get portfolio items
   *     tags: [Portfolio]
   *     responses:
   *       200:
   *         description: List of portfolio items with current values
   */
  router.get("/", portfolioController.getPortfolio);

  // POST /api/portfolio - Add item to portfolio
  /**
   * @swagger
   * /portfolio:
   *   post:
   *     summary: Add item to portfolio
   *     tags: [Portfolio]
   *     requestBody:
   *       required: true
   *       content:
   *         application/json:
   *           schema:
   *             type: object
   *             required:
   *               - ticker
   *               - quantity
   *               - buyPrice
   *             properties:
   *               ticker:
   *                 type: string
   *               quantity:
   *                 type: integer
   *                 minimum: 1
   *               cost:
   *                 type: number
   *                 minimum: 0
   *     responses:
   *       201:
   *         description: Item added to portfolio
   */
  router.post(
    "/",
    validateBody(portfolioItemSchema),
    portfolioController.addToPortfolio
  );

  // PATCH /api/portfolio/:ticker - Update portfolio item
  /**
   * @swagger
   * /portfolio/{ticker}:
   *   patch:
   *     summary: Update portfolio item
   *     tags: [Portfolio]
   *     parameters:
   *       - in: path
   *         name: ticker
   *         schema:
   *           type: string
   *         required: true
   *         description: Stock ticker symbol
   *     requestBody:
   *       required: true
   *       content:
   *         application/json:
   *           schema:
   *             type: object
   *             properties:
   *               quantity:
   *                 type: integer
   *                 minimum: 1
   *               cost:
   *                 type: number
   *                 minimum: 0
   *     responses:
   *       200:
   *         description: Portfolio item updated
   */
  router.patch(
    "/:ticker",
    validateParams(tickerParamSchema),
    validateBody(updatePortfolioItemSchema),
    portfolioController.updatePortfolioItem
  );

  // DELETE /api/portfolio/:ticker - Remove item from portfolio
  /**
   * @swagger
   * /portfolio/{ticker}:
   *   delete:
   *     summary: Remove item from portfolio
   *     tags: [Portfolio]
   *     parameters:
   *       - in: path
   *         name: ticker
   *         schema:
   *           type: string
   *         required: true
   *         description: Stock ticker symbol
   *     responses:
   *       200:
   *         description: Item removed from portfolio
   */
  router.delete(
    "/:ticker",
    validateParams(tickerParamSchema),
    portfolioController.removeFromPortfolio
  );

  return router;
};
