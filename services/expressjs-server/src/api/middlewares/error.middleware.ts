/**
 * Error Handling Middleware
 * Global error handler for Express
 */

import { Request, Response, NextFunction } from "express";
import { AppError } from "../../utils";
import { logger } from "../../utils";
import { config } from "../../infrastructure/config";

export const errorHandler = (
  err: Error | AppError,
  req: Request,
  res: Response,
  next: NextFunction
) => {
  // Log the error
  logger.error(`Error in ${req.method} ${req.path}`, err);

  // Handle AppError instances
  if (err instanceof AppError) {
    return res.status(err.statusCode).json({
      success: false,
      error: err.message,
      code: err.code,
      ...(config.isDevelopment && { stack: err.stack }),
    });
  }

  // Handle generic errors
  return res.status(500).json({
    success: false,
    error: config.isDevelopment ? err.message : "Internal server error",
    ...(config.isDevelopment && { stack: err.stack }),
  });
};

export const notFoundHandler = (req: Request, res: Response) => {
  res.status(404).json({
    success: false,
    error: `Route ${req.method} ${req.path} not found`,
  });
};
