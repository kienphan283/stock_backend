/**
 * IP Whitelist Middleware
 * Restricts access to certain endpoints by IP address
 * TODO: Implement IP whitelist
 */

import { Request, Response, NextFunction } from "express";
import { config } from "../config";
import { logger } from "../utils";

// TODO: Load from environment variable
const ALLOWED_IPS: string[] = process.env.ALLOWED_IPS?.split(",") || [];

export const ipWhitelistMiddleware = (
  req: Request,
  res: Response,
  next: NextFunction
): void => {
  // TODO: Implement IP whitelist check
  // 1. Get client IP from req.ip or req.headers['x-forwarded-for']
  // 2. Check if IP is in whitelist
  // 3. Reject if not whitelisted (for admin endpoints)
  
  if (ALLOWED_IPS.length === 0) {
    // No whitelist configured - allow all
    logger.warn("[IP Whitelist] No whitelist configured - allowing all IPs");
    return next();
  }

  const clientIp = req.ip || req.socket.remoteAddress || "unknown";
  
  // TODO: Check if clientIp is in ALLOWED_IPS
  // if (!ALLOWED_IPS.includes(clientIp)) {
  //   return res.status(403).json({ error: "IP not allowed" });
  // }

  logger.warn(`[IP Whitelist] IP whitelist check not yet implemented for ${clientIp}`);
  next();
};

