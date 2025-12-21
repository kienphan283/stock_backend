/**
 * Auth Routes
 * Proxy routes to market-api-service/api/auth
 */

import { Router, Request, Response } from "express";
import { config } from "../../config";
import { asyncHandler } from "../middlewares";
import { wrapHttpCall } from "../../utils/errorHandler";

export const createAuthRouter = (): Router => {
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
     * POST /api/auth/register
     */
    router.post(
        "/register",
        asyncHandler(async (req: Request, res: Response) => {
            const url = `${baseUrl}/api/auth/register`;
            const upstream = await callUpstream(url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(req.body),
            });

            if (!upstream) {
                return res.status(502).json({ success: false, error: "Upstream request failed" });
            }
            res.status(upstream.status).json(upstream.data);
        })
    );

    /**
     * POST /api/auth/login
     */
    router.post(
        "/login",
        asyncHandler(async (req: Request, res: Response) => {
            const url = `${baseUrl}/api/auth/login`;
            // Login endpoint expects form-data in backend (OAuth2PasswordRequestForm)
            // But from frontend we might send JSON or Form. 
            // If backend uses OAuth2PasswordRequestForm, it expects form-url-encoded usually.
            // Let's check backend implementation again.
            // Backend: async def login(form_data: OAuth2PasswordRequestForm = Depends()):
            // This expects Content-Type: application/x-www-form-urlencoded

            const formData = new URLSearchParams();
            formData.append("username", req.body.email || req.body.username);
            formData.append("password", req.body.password);

            const upstream = await callUpstream(url, {
                method: "POST",
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
                body: formData.toString(),
            });

            if (!upstream) {
                return res.status(502).json({ success: false, error: "Upstream request failed" });
            }
            res.status(upstream.status).json(upstream.data);
        })
    );

    /**
     * POST /api/auth/oauth/login
     */
    router.post(
        "/oauth/login",
        asyncHandler(async (req: Request, res: Response) => {
            const url = `${baseUrl}/api/auth/oauth/login`;
            const upstream = await callUpstream(url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(req.body),
            });

            if (!upstream) {
                return res.status(502).json({ success: false, error: "Upstream request failed" });
            }
            res.status(upstream.status).json(upstream.data);
        })
    );

    /**
     * GET /api/auth/verify-email
     */
    router.get(
        "/verify-email",
        asyncHandler(async (req: Request, res: Response) => {
            const token = req.query.token as string;
            if (!token) {
                return res.status(400).json({ success: false, error: "Missing token" });
            }
            const url = `${baseUrl}/api/auth/verify-email?token=${token}`;
            const upstream = await callUpstream(url);
            if (!upstream) {
                return res.status(502).json({ success: false, error: "Upstream request failed" });
            }
            res.status(upstream.status).json(upstream.data);
        })
    );



    /**
     * POST /api/auth/verify-otp
     */
    router.post(
        "/verify-otp",
        asyncHandler(async (req: Request, res: Response) => {
            const url = `${baseUrl}/api/auth/verify-otp`;
            const upstream = await callUpstream(url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(req.body),
            });

            if (!upstream) {
                return res.status(502).json({ success: false, error: "Upstream request failed" });
            }
            res.status(upstream.status).json(upstream.data);
        })
    );

    /**
     * POST /api/auth/resend-otp
     */
    router.post(
        "/resend-otp",
        asyncHandler(async (req: Request, res: Response) => {
            const url = `${baseUrl}/api/auth/resend-otp`;
            const upstream = await callUpstream(url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(req.body),
            });

            if (!upstream) {
                return res.status(502).json({ success: false, error: "Upstream request failed" });
            }
            res.status(upstream.status).json(upstream.data);
        })
    );

    /**
     * PUT /api/auth/profile
     */
    router.put(
        "/profile",
        asyncHandler(async (req: Request, res: Response) => {
            // Check if user is authenticated via Middleware
            // req.user should be populated
            // We pass X-User-Id header to backend
            // But we need to make sure we forward the Authorization header too/instead?
            // Backend auth_router.update_profile might inspect different things.
            // For now, let's just proxy with body and headers.
            console.log("DEBUG GATEWAY INCOMING HEADERS:", JSON.stringify(req.headers)); // DEBUG LOG


            const url = `${baseUrl}/api/auth/profile`;
            const headers: Record<string, string> = { "Content-Type": "application/json" };

            // Forward User ID if available from JWT Middleware
            if (req.headers['x-user-id']) {
                headers['x-user-id'] = req.headers['x-user-id'] as string;
            }

            // CRITICAL FIX: Forward Authorization Header
            if (req.headers.authorization) {
                headers['Authorization'] = req.headers.authorization;
            }

            const upstream = await callUpstream(url, {
                method: "PUT",
                headers: headers,
                body: JSON.stringify(req.body),
            });

            if (!upstream) {
                return res.status(502).json({ success: false, error: "Upstream request failed" });
            }
            res.status(upstream.status).json(upstream.data);
        })
    );
    /**
     * POST /api/auth/forgot-password
     */
    router.post(
        "/forgot-password",
        asyncHandler(async (req: Request, res: Response) => {
            const url = `${baseUrl}/api/auth/forgot-password`;
            const upstream = await callUpstream(url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(req.body),
            });

            if (!upstream) {
                return res.status(502).json({ success: false, error: "Upstream request failed" });
            }
            res.status(upstream.status).json(upstream.data);
        })
    );

    /**
     * POST /api/auth/reset-password
     */
    router.post(
        "/reset-password",
        asyncHandler(async (req: Request, res: Response) => {
            const url = `${baseUrl}/api/auth/reset-password`;
            const upstream = await callUpstream(url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(req.body),
            });

            if (!upstream) {
                return res.status(502).json({ success: false, error: "Upstream request failed" });
            }
            res.status(upstream.status).json(upstream.data);
        })
    );

    return router;
};
