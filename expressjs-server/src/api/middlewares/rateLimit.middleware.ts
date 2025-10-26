/**
 * Rate Limiting Middleware
 * Protects API from abuse by limiting requests per IP
 */

import { Request, Response, NextFunction } from "express";

interface RateLimitStore {
    [key: string]: {
        count: number;
        resetTime: number;
    };
}

const store: RateLimitStore = {};

interface RateLimitOptions {
    windowMs: number; // Time window in milliseconds
    max: number; // Max requests per window
    message?: string;
    statusCode?: number;
}

/**
 * Simple in-memory rate limiter
 * For production, use Redis-based rate limiting
 */
export function rateLimit(options: RateLimitOptions) {
    const {
        windowMs,
        max,
        message = "Too many requests, please try again later.",
        statusCode = 429,
    } = options;

    return (req: Request, res: Response, next: NextFunction) => {
        const key = req.ip || req.socket.remoteAddress || "unknown";
        const now = Date.now();

        // Clean up expired entries periodically
        if (Math.random() < 0.01) {
            Object.keys(store).forEach((k) => {
                if (store[k].resetTime < now) {
                    delete store[k];
                }
            });
        }

        // Initialize or get existing entry
        if (!store[key] || store[key].resetTime < now) {
            store[key] = {
                count: 1,
                resetTime: now + windowMs,
            };
            return next();
        }

        // Increment counter
        store[key].count++;

        // Set rate limit headers
        const remaining = Math.max(0, max - store[key].count);
        const resetTime = Math.ceil(store[key].resetTime / 1000);

        res.setHeader("X-RateLimit-Limit", max);
        res.setHeader("X-RateLimit-Remaining", remaining);
        res.setHeader("X-RateLimit-Reset", resetTime);

        // Check if limit exceeded
        if (store[key].count > max) {
            res.setHeader("Retry-After", Math.ceil((store[key].resetTime - now) / 1000));
            return res.status(statusCode).json({
                success: false,
                error: message,
                retryAfter: Math.ceil((store[key].resetTime - now) / 1000),
            });
        }

        next();
    };
}

// Predefined rate limiters
export const apiLimiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100, // 100 requests per 15 minutes
    message: "Too many API requests from this IP, please try again later.",
});

export const strictLimiter = rateLimit({
    windowMs: 60 * 1000, // 1 minute
    max: 10, // 10 requests per minute
    message: "Too many requests, please slow down.",
});

