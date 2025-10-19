/**
 * Request Logging Middleware
 * Enhanced request logging
 */

import { Request, Response, NextFunction } from "express";
import { logger } from "../../utils";

export const requestLogger = (
  req: Request,
  res: Response,
  next: NextFunction
) => {
  const start = Date.now();

  // Log request
  logger.info(`→ ${req.method} ${req.path}`, {
    query: req.query,
    params: req.params,
    ip: req.ip,
  });

  // Log response on finish
  res.on("finish", () => {
    const duration = Date.now() - start;
    const logMessage = `← ${req.method} ${req.path} ${res.statusCode} (${duration}ms)`;

    if (res.statusCode >= 400) {
      logger.warn(logMessage);
    } else {
      logger.success(logMessage);
    }
  });

  next();
};
