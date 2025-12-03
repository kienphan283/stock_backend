/**
 * Proxy Controller
 * Generic HTTP proxy to market-api-service
 */

import { Request, Response, NextFunction } from "express";
import { MarketApiClient } from "../../clients/market-api.client";
import { config } from "../../config";
import { logger } from "../../utils";
import { wrapHttpCall } from "../../utils/errorHandler";
import { asyncHandler } from "../middlewares";

/**
 * Hop-by-hop headers that should not be forwarded
 */
const HOP_BY_HOP_HEADERS = new Set([
  "host",
  "connection",
  "keep-alive",
  "transfer-encoding",
  "te",
  "trailer",
  "upgrade",
  "proxy-authorization",
  "proxy-authenticate",
]);

/**
 * Safely convert Express headers to HeadersInit
 * Filters out undefined values and hop-by-hop headers
 */
function sanitizeHeaders(req: Request): HeadersInit {
  const outgoingHeaders: Record<string, string> = Object.entries(req.headers)
    .filter(([key, value]) => {
      // Filter out undefined values
      if (value === undefined) return false;
      // Filter out hop-by-hop headers
      if (HOP_BY_HOP_HEADERS.has(key.toLowerCase())) return false;
      return true;
    })
    .reduce((acc, [key, value]) => {
      // Convert arrays to comma-separated strings
      acc[key] = Array.isArray(value) ? value.join(",") : String(value);
      return acc;
    }, {} as Record<string, string>);

  return outgoingHeaders;
}

export class ProxyController {
  private readonly apiClient: MarketApiClient;

  constructor() {
    this.apiClient = new MarketApiClient();
  }

  /**
   * Generic proxy method - forwards request to market-api-service
   */
  proxy = asyncHandler(async (req: Request, res: Response) => {
    const endpoint = req.path;
    const queryString = new URLSearchParams(req.query as Record<string, string>).toString();
    const fullEndpoint = queryString ? `${endpoint}?${queryString}` : endpoint;

    logger.info(`[Proxy] ${req.method} ${fullEndpoint}`);

    try {
      const response = await this.apiClient.proxyRequest(fullEndpoint, {
        method: req.method,
        body: req.method !== "GET" && req.method !== "HEAD" ? JSON.stringify(req.body) : undefined,
        headers: sanitizeHeaders(req),
      });

      // Forward response
      const data = await response.json();
      res.status(response.status).json(data);
    } catch (error) {
      logger.error(`[Proxy] Error proxying ${fullEndpoint}:`, error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : "Internal server error",
      });
    }
  });

  /**
   * Proxy GET request
   */
  proxyGet = asyncHandler(async (req: Request, res: Response) => {
    const endpoint = req.path;
    const queryString = new URLSearchParams(req.query as Record<string, string>).toString();
    const fullEndpoint = queryString ? `${endpoint}?${queryString}` : endpoint;

    try {
      const response = await wrapHttpCall(
        () =>
          fetch(`${config.marketApiUrl}${fullEndpoint}`, {
            method: "GET",
            headers: {
              "Content-Type": "application/json",
            },
          }),
        `fetch:${fullEndpoint}`
      );

      if (!response) {
        throw new Error("Upstream request failed");
      }

      const data = await response.json();
      res.status(response.status).json(data);
    } catch (error) {
      logger.error(`[Proxy] Error proxying GET ${fullEndpoint}:`, error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : "Internal server error",
      });
    }
  });

  /**
   * Proxy POST request
   */
  proxyPost = asyncHandler(async (req: Request, res: Response) => {
    const endpoint = req.path;

    try {
      const response = await wrapHttpCall(
        () =>
          fetch(`${config.marketApiUrl}${endpoint}`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(req.body),
          }),
        `fetch:${endpoint}`
      );

      if (!response) {
        throw new Error("Upstream request failed");
      }

      const data = await response.json();
      res.status(response.status).json(data);
    } catch (error) {
      logger.error(`[Proxy] Error proxying POST ${endpoint}:`, error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : "Internal server error",
      });
    }
  });
}

