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

  const callUpstream = async (url: string, options?: RequestInit) => {
    const response = await wrapHttpCall(() => fetch(url, options), `fetch:${url}`);
    if (!response) {
      return null;
    }
    const data = await response.json();
    return { status: response.status, data };
  };

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

  // GET /api/stocks/:ticker/price-history - Get price history
  router.get(
    "/:ticker/price-history",
    validateParams(tickerParamSchema),
    validateQuery(periodQuerySchema),
    asyncHandler(async (req: Request, res: Response) => {
      const { ticker } = req.params;
      const { period } = req.query;
      const responseUrl = `${baseUrl}/api/price-history/eod?symbol=${ticker}&period=${
        period || "3m"
      }`;
      const upstream = await callUpstream(responseUrl);
      if (!upstream) {
        return res.status(502).json({ success: false, error: "Upstream request failed" });
      }
      res.status(upstream.status).json(upstream.data);
    })
  );

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
