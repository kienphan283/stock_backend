/**
 * Stock Routes
 * Pure proxy routes to market-api-service
 */

import { Router, Request, Response } from "express";
import {
  validateParams,
  validateQuery,
  tickerParamSchema,
  periodQuerySchema,
  limitQuerySchema,
} from "../validators";
import { config } from "../../config";
import { logger } from "../../utils";
import { wrapHttpCall } from "../../utils/errorHandler";
import { asyncHandler } from "../middlewares";

export const createStockRouter = (): Router => {
  const router = Router();
  const baseUrl = config.marketApiUrl;

  const UPSTREAM_TIMEOUT_MS = 8000;

  const callUpstream = async (url: string, options?: RequestInit) => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), UPSTREAM_TIMEOUT_MS);
    const response = await wrapHttpCall(
      () => fetch(url, { ...options, signal: controller.signal }),
      `fetch:${url}`
    );
    clearTimeout(timer);
    if (!response) {
      return null;
    }
    const data = await response.json();
    return { status: response.status, data };
  };

  /**
   * @swagger
   * /api/stocks:
   *   get:
   *     summary: Retrieve a list of stocks
   *     description: Retrieve a list of stocks from the market API.
   *     responses:
   *       200:
   *         description: A list of stocks.
   *         content:
   *           application/json:
   *             schema:
   *               type: array
   *               items:
   *                 type: object
   *                 properties:
   *                   symbol:
   *                     type: string
   *                     description: The stock ticker symbol.
   *                     example: AAPL
   *                   name:
   *                     type: string
   *                     description: The company name.
   *                     example: Apple Inc.
   */
  // GET /api/stocks - Get all stocks (proxy to /api/companies)
  router.get(
    "/",
    asyncHandler(async (_req: Request, res: Response) => {
      const upstream = await callUpstream(`${baseUrl}/api/companies`);
      if (!upstream) {
        return res.status(502).json({ success: false, error: "Upstream request failed" });
      }
      res.status(upstream.status).json(upstream.data);
    })
  );

  /**
   * @swagger
   * /api/stocks/search:
   *   get:
   *     summary: Search for stocks
   *     tags: [Stocks]
   *     parameters:
   *       - in: query
   *         name: q
   *         required: true
   *         schema:
   *           type: string
   *         description: Search query
   *     responses:
   *       200:
   *         description: Search results
   */
  // GET /api/stocks/search - Search stocks
  router.get(
    "/search",
    asyncHandler(async (req: Request, res: Response) => {
      const { q } = req.query;
      const url = `${baseUrl}/api/search?q=${q}`;
      logger.info(`Proxying search request to: ${url}`);
      const upstream = await callUpstream(url);
      if (!upstream) {
        logger.error(`Upstream search failed for URL: ${url}`);
        return res.status(502).json({ success: false, error: "Upstream request failed" });
      }
      res.status(upstream.status).json(upstream.data);
    })
  );

  /**
   * @swagger
   * /api/stocks/{ticker}:
   *   get:
   *     summary: Get stock profile
   *     tags: [Stocks]
   *     parameters:
   *       - in: path
   *         name: ticker
   *         required: true
   *         schema:
   *           type: string
   *     responses:
   *       200:
   *         description: Stock profile
   */
  // GET /api/stocks/:ticker - Get stock by ticker (proxy to /api/profile)
  router.get(
    "/:ticker",
    validateParams(tickerParamSchema),
    asyncHandler(async (req: Request, res: Response) => {
      const { ticker } = req.params;
      const upstream = await callUpstream(`${baseUrl}/api/profile?symbol=${ticker}`);
      if (!upstream) {
        return res.status(502).json({ success: false, error: "Upstream request failed" });
      }
      res.status(upstream.status).json(upstream.data);
    })
  );

  /**
   * @swagger
   * /api/stocks/{ticker}/quote:
   *   get:
   *     summary: Get real-time quote
   *     tags: [Stocks]
   *     parameters:
   *       - in: path
   *         name: ticker
   *         required: true
   *         schema:
   *           type: string
   *     responses:
   *       200:
   *         description: Real-time quote
   */
  // GET /api/stocks/:ticker/quote - Get real-time quote
  router.get(
    "/:ticker/quote",
    validateParams(tickerParamSchema),
    asyncHandler(async (req: Request, res: Response) => {
      const { ticker } = req.params;
      const upstream = await callUpstream(`${baseUrl}/api/quote?symbol=${ticker}`);
      if (!upstream) {
        return res.status(502).json({ success: false, error: "Upstream request failed" });
      }
      res.status(upstream.status).json(upstream.data);
    })
  );

  /**
   * @swagger
   * /api/stocks/{ticker}/price-history:
   *   get:
   *     summary: Get price history
   *     tags: [Stocks]
   *     parameters:
   *       - in: path
   *         name: ticker
   *         required: true
   *         schema:
   *           type: string
   *       - in: query
   *         name: period
   *         schema:
   *           type: string
   *           default: 3m
   *     responses:
   *       200:
   *         description: Price history
   */
  // GET /api/stocks/:ticker/price-history - Get price history
  router.get(
    "/:ticker/price-history",
    validateParams(tickerParamSchema),
    validateQuery(periodQuerySchema),
    asyncHandler(async (req: Request, res: Response) => {
      const { ticker } = req.params;
      const { period } = req.query;
      const responseUrl = `${baseUrl}/api/price-history/eod?symbol=${ticker}&period=${period || "3m"
        }`;
      const upstream = await callUpstream(responseUrl);
      if (!upstream) {
        return res.status(502).json({ success: false, error: "Upstream request failed" });
      }
      res.status(upstream.status).json(upstream.data);
    })
  );

  /**
   * @swagger
   * /api/stocks/{ticker}/news:
   *   get:
   *     summary: Get company news
   *     tags: [Stocks]
   *     parameters:
   *       - in: path
   *         name: ticker
   *         required: true
   *         schema:
   *           type: string
   *       - in: query
   *         name: limit
   *         schema:
   *           type: integer
   *           default: 16
   *     responses:
   *       200:
   *         description: Company news
   */
  // GET /api/stocks/:ticker/news - Get company news
  router.get(
    "/:ticker/news",
    validateParams(tickerParamSchema),
    validateQuery(limitQuerySchema),
    asyncHandler(async (req: Request, res: Response) => {
      const { ticker } = req.params;
      const { limit } = req.query;
      const upstream = await callUpstream(
        `${baseUrl}/news?symbol=${ticker}&limit=${limit || 16}`
      );
      if (!upstream) {
        return res.status(502).json({ success: false, error: "Upstream request failed" });
      }
      res.status(upstream.status).json(upstream.data);
    })
  );

  /**
   * @swagger
   * /api/stocks/{ticker}/financials:
   *   get:
   *     summary: Get financials for a specific stock
   *     tags: [Stocks]
   *     parameters:
   *       - in: path
   *         name: ticker
   *         required: true
   *         schema:
   *           type: string
   *       - in: query
   *         name: type
   *         schema:
   *           type: string
   *           enum: [IS, BS, CF]
   *           default: IS
   *       - in: query
   *         name: period
   *         schema:
   *           type: string
   *           enum: [annual, quarterly]
   *           default: quarterly
   *     responses:
   *       200:
   *         description: Financial statements
   */
  // GET /api/stocks/:ticker/financials - Get financials (proxy to /api/financials)
  router.get(
    "/:ticker/financials",
    validateParams(tickerParamSchema),
    asyncHandler(async (req: Request, res: Response) => {
      const { ticker } = req.params;
      const { type = "IS", period = "quarterly" } = req.query;
      const upstream = await callUpstream(
        `${baseUrl}/api/financials?company=${ticker}&type=${type}&period=${period}`
      );
      if (!upstream) {
        return res.status(502).json({ success: false, error: "Upstream request failed" });
      }
      res.status(upstream.status).json(upstream.data);
    })
  );

  /**
   * @swagger
   * /api/stocks/{ticker}/earnings:
   *   get:
   *     summary: Get earnings data
   *     tags: [Stocks]
   *     parameters:
   *       - in: path
   *         name: ticker
   *         required: true
   *         schema:
   *           type: string
   *     responses:
   *       200:
   *         description: Earnings data
   */
  // GET /api/stocks/:ticker/earnings - Get earnings
  router.get(
    "/:ticker/earnings",
    validateParams(tickerParamSchema),
    asyncHandler(async (req: Request, res: Response) => {
      const { ticker } = req.params;
      const upstream = await callUpstream(`${baseUrl}/api/earnings?symbol=${ticker}`);
      if (!upstream) {
        return res.status(502).json({ success: false, error: "Upstream request failed" });
      }
      res.status(upstream.status).json(upstream.data);
    })
  );

  /**
   * @swagger
   * /api/stocks/refresh:
   *   post:
   *     summary: Trigger data refresh
   *     tags: [Stocks]
   *     responses:
   *       200:
   *         description: Refresh triggered
   */
  // POST /api/stocks/refresh - Refresh data
  router.post(
    "/refresh",
    asyncHandler(async (req: Request, res: Response) => {
      const upstream = await callUpstream(`${baseUrl}/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!upstream) {
        return res.status(502).json({ success: false, error: "Upstream request failed" });
      }
      res.status(upstream.status).json(upstream.data);
    })
  );

  return router;
};
