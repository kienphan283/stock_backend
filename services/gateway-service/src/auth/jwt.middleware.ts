import { Request, Response, NextFunction } from "express";
import jwt from "jsonwebtoken";
import { config } from "../config";
import { logger } from "../utils";

// Extend Express Request type to include user
declare global {
  namespace Express {
    interface Request {
      user?: any;
    }
  }
}

export const jwtMiddleware = (
  req: Request,
  res: Response,
  next: NextFunction
): void => {
  const authHeader = req.headers.authorization;

  if (!authHeader) {
    // If no token, just proceed. 
    // Protected routes will be blocked by downstream service or specific route guards if we add them.
    // Ideally Gateway should block if we enforce it here, 
    // but typically some routes like /login don't need token.
    // For this middleware, we just try to populate user if token exists.
    return next();
  }

  const token = authHeader.split(" ")[1]; // Bearer <token>

  if (!token) {
    return next();
  }

  try {
    const decoded = jwt.verify(token, config.jwtSecret);
    req.user = decoded;

    // Inject user info into headers for downstream services
    if (typeof decoded === 'object' && decoded !== null && 'sub' in decoded) {
      req.headers['x-user-id'] = (decoded as any).sub;
      req.headers['x-user-email'] = (decoded as any).email;
    }

    next();
  } catch (error) {
    logger.warn(`[JWT] Invalid token: ${(error as Error).message}`);
    // Optional: Return 401 here if we want to enforce valid tokens for all requests with header
    // res.status(401).json({ error: "Invalid token" });
    // For now, let's just proceed without user info, downstream might handle 401
    next();
  }
};
