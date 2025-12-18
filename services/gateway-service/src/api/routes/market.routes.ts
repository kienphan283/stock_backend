/**
 * Market Routes
 * Proxy routes to market-api-service
 */

import { Router, Request, Response } from "express";
import { config } from "../../config";
import { logger } from "../../utils";
import { wrapHttpCall } from "../../utils/errorHandler";
import { asyncHandler } from "../middlewares";

export const createMarketRouter = (): Router => {
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

    /**
     * @swagger
     * /api/market/stocks:
     *   get:
     *     summary: Get all market stocks
     *     tags: [Market]
     *     responses:
     *       200:
     *         description: List of stocks for heatmap
     */
    // GET /api/market/stocks - Get stocks for heatmap
    router.get(
        "/stocks",
        asyncHandler(async (_req: Request, res: Response) => {
            const url = `${baseUrl}/api/market/stocks`;
            const upstream = await callUpstream(url);
            if (!upstream) {
                return res.status(502).json({ success: false, error: "Upstream request failed" });
            }
            res.status(upstream.status).json(upstream.data);
        })
    );

    /**
     * @swagger
     * /api/market/volumes:
     *   get:
     *     summary: Get accumulated volumes
     *     tags: [Market]
     *     parameters:
     *       - in: query
     *         name: symbols
     *         required: true
     *         schema:
     *           type: string
     *     responses:
     *       200:
     *         description: Stock volumes
     */
    // GET /api/market/volumes - Get accumulated volumes
    router.get(
        "/volumes",
        asyncHandler(async (req: Request, res: Response) => {
            const { symbols } = req.query;
            if (!symbols) {
                return res.status(400).json({ success: false, error: "Missing symbols parameter" });
            }

            const url = `${baseUrl}/api/market/volumes?symbols=${symbols}`;
            const upstream = await callUpstream(url);
            if (!upstream) {
                return res.status(502).json({ success: false, error: "Upstream request failed" });
            }
            res.status(upstream.status).json(upstream.data);
        })
    );



    /**
     * @swagger
     * /api/market/stocks/check:
     *   get:
     *     summary: Check if a stock exists
     *     tags: [Market]
     *     parameters:
     *       - in: query
     *         name: ticker
     *         required: true
     *         schema:
     *           type: string
     *     responses:
     *       200:
     *         description: Stock existence check result
     */
    // GET /api/market/stocks/check - Check if stock exists
    router.get(
        "/stocks/check",
        asyncHandler(async (req: Request, res: Response) => {
            const { ticker } = req.query;
            if (!ticker) {
                return res.status(400).json({ success: false, error: "Missing ticker parameter" });
            }

            const url = `${baseUrl}/api/market/stocks/check?ticker=${ticker}`;
            const upstream = await callUpstream(url);
            if (!upstream) {
                return res.status(502).json({ success: false, error: "Upstream request failed" });
            }
            res.status(upstream.status).json(upstream.data);
        })
    );

    return router;
};
