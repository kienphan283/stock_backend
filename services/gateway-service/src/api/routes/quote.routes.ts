/**
 * Quote Routes
 * Pure proxy routes to market-api-service
 */

import { Router, Request, Response } from "express";
import { config } from "../../config";
import { logger } from "../../utils";
import { wrapHttpCall } from "../../utils/errorHandler";
import { asyncHandler } from "../middlewares";

export const createQuoteRouter = (): Router => {
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
     * /api/quote/previous-closes:
     *   get:
     *     summary: Get previous close prices for multiple symbols
     *     tags: [Quote]
     *     parameters:
     *       - in: query
     *         name: symbols
     *         required: true
     *         schema:
     *           type: string
     *         description: Comma-separated list of symbols
     *     responses:
     *       200:
     *         description: Previous close prices
     */
    // GET /api/quote/previous-closes
    router.get(
        "/previous-closes",
        asyncHandler(async (req: Request, res: Response) => {
            const { symbols } = req.query;
            if (!symbols) {
                return res.status(400).json({ success: false, error: "Missing symbols parameter" });
            }

            const url = `${baseUrl}/api/quote/previous-closes?symbols=${symbols}`;
            const upstream = await callUpstream(url);
            if (!upstream) {
                return res.status(502).json({ success: false, error: "Upstream request failed" });
            }
            res.status(upstream.status).json(upstream.data);
        })
    );

    /**
     * @swagger
     * /api/quote/latest-eod:
     *   get:
     *     summary: Get latest EOD data for multiple symbols
     *     tags: [Quote]
     *     parameters:
     *       - in: query
     *         name: symbols
     *         required: true
     *         schema:
     *           type: string
     *       - in: query
     *         name: auto_fetch
     *         schema:
     *           type: boolean
     *           default: true
     *     responses:
     *       200:
     *         description: Latest EOD data
     */
    // GET /api/quote/latest-eod
    router.get(
        "/latest-eod",
        asyncHandler(async (req: Request, res: Response) => {
            const { symbols, auto_fetch } = req.query;
            if (!symbols) {
                return res.status(400).json({ success: false, error: "Missing symbols parameter" });
            }

            const url = `${baseUrl}/api/quote/latest-eod?symbols=${symbols}&auto_fetch=${auto_fetch || true}`;
            const upstream = await callUpstream(url);
            if (!upstream) {
                return res.status(502).json({ success: false, error: "Upstream request failed" });
            }
            res.status(upstream.status).json(upstream.data);
        })
    );

    /**
     * @swagger
     * /api/quote:
     *   get:
     *     summary: Get single quote
     *     tags: [Quote]
     *     parameters:
     *       - in: query
     *         name: symbol
     *         required: true
     *         schema:
     *           type: string
     *     responses:
     *       200:
     *         description: Quote data
     */
    // GET /api/quote
    router.get(
        "/",
        asyncHandler(async (req: Request, res: Response) => {
            const { symbol, ticker } = req.query;
            const targetSymbol = symbol || ticker;

            if (!targetSymbol) {
                return res.status(400).json({ success: false, error: "Missing symbol parameter" });
            }

            const url = `${baseUrl}/api/quote?symbol=${targetSymbol}`;
            const upstream = await callUpstream(url);
            if (!upstream) {
                return res.status(502).json({ success: false, error: "Upstream request failed" });
            }
            res.status(upstream.status).json(upstream.data);
        })
    );

    return router;
};
