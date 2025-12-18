/**
 * Search Routes
 * Proxy routes to market-api-service search endpoints
 */

import { Router, Request, Response } from "express";
import { config } from "../../config";
import { wrapHttpCall } from "../../utils/errorHandler";
import { asyncHandler } from "../middlewares";

export const createSearchRouter = (): Router => {
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
     * /api/search:
     *   get:
     *     summary: Search companies
     *     tags: [Search]
     *     parameters:
     *       - in: query
     *         name: q
     *         required: true
     *         schema:
     *           type: string
     *     responses:
     *       200:
     *         description: Search results
     */
    // GET /api/search - Search companies
    router.get(
        "/",
        asyncHandler(async (req: Request, res: Response) => {
            const { q } = req.query;

            // Allow empty query? Maybe not.
            if (!q) {
                return res.json({ success: true, count: 0, companies: [] });
            }

            const url = `${baseUrl}/api/search?q=${q}`;
            const upstream = await callUpstream(url);
            if (!upstream) {
                return res.status(502).json({ success: false, error: "Upstream request failed" });
            }
            res.status(upstream.status).json(upstream.data);
        })
    );

    return router;
};
