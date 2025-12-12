/**
 * Portfolio Routes
 * Pure proxy routes to market-api-service
 * Note: Portfolio management should be implemented in market-api-service
 */

import { Router, Request, Response } from "express";
import axios from "axios";
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

  // Helper to proxy requests
  const proxyRequest = async (req: Request, res: Response, method: string, path: string, body?: any) => {
    try {
      const url = `${baseUrl}/api/portfolio${path}`;
      // Log URL for debugging
      // console.log(`Proxying ${method} to ${url}`);

      const response = await axios({
        method,
        url,
        params: req.query,
        data: body,
      });
      res.json(response.data);
    } catch (error: any) {
      if (error.response) {
        res.status(error.response.status).json(error.response.data);
      } else {
        res.status(500).json({ success: false, error: error.message });
      }
    }
  };

  // GET /holdings
  router.get("/holdings", asyncHandler(async (req, res) => {
    await proxyRequest(req, res, "GET", "/holdings");
  }));

  // GET /transactions
  router.get("/transactions", asyncHandler(async (req, res) => {
    await proxyRequest(req, res, "GET", "/transactions");
  }));

  // POST /transactions
  router.post("/transactions", asyncHandler(async (req, res) => {
    await proxyRequest(req, res, "POST", "/transactions", req.body);
  }));

  // POST /create
  router.post("/create", asyncHandler(async (req, res) => {
    await proxyRequest(req, res, "POST", "/create", req.body);
  }));

  // GET /portfolios
  router.get("/portfolios", asyncHandler(async (req, res) => {
    await proxyRequest(req, res, "GET", "/portfolios");
  }));

  // Legacy/Other routes can be handled or left as TODO if not in backend yet
  // POST / (Add Stock) -> mapping to backend logic if exists? 
  // currently backend manual transaction add is POST /transactions
  // frontend service addStock calls POST /api/portfolio
  // We should align frontend to use POST /transactions or map it here.
  // For now, let's just fix the 404s we know about.

  return router;
};
