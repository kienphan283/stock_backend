/**
 * Validation Middleware
 * Middleware for validating requests using Zod schemas
 */

import { Request, Response, NextFunction } from "express";
import { z, ZodError } from "zod";
import { ValidationError } from "../../utils";

export const validate = (schema: z.ZodSchema) => {
  return (req: Request, res: Response, next: NextFunction) => {
    try {
      // Validate different parts of the request
      const data = {
        ...req.body,
        ...req.params,
        ...req.query,
      };

      schema.parse(data);
      next();
    } catch (error) {
      if (error instanceof ZodError) {
        const errors = error.issues.map((err: any) => ({
          field: err.path.join("."),
          message: err.message,
        }));

        next(
          new ValidationError(
            `Validation failed: ${errors
              .map((e: any) => `${e.field} - ${e.message}`)
              .join(", ")}`
          )
        );
      } else {
        next(error);
      }
    }
  };
};

export const validateParams = (schema: z.ZodSchema) => {
  return (req: Request, res: Response, next: NextFunction) => {
    try {
      req.params = schema.parse(req.params) as any;
      next();
    } catch (error) {
      if (error instanceof ZodError) {
        next(
          new ValidationError(error.issues[0]?.message || "Validation failed")
        );
      } else {
        next(error);
      }
    }
  };
};

export const validateQuery = (schema: z.ZodSchema) => {
  return (req: Request, res: Response, next: NextFunction) => {
    try {
      req.query = schema.parse(req.query) as any;
      next();
    } catch (error) {
      if (error instanceof ZodError) {
        next(
          new ValidationError(error.issues[0]?.message || "Validation failed")
        );
      } else {
        next(error);
      }
    }
  };
};

export const validateBody = (schema: z.ZodSchema) => {
  return (req: Request, res: Response, next: NextFunction) => {
    try {
      req.body = schema.parse(req.body);
      next();
    } catch (error) {
      if (error instanceof ZodError) {
        next(
          new ValidationError(error.issues[0]?.message || "Validation failed")
        );
      } else {
        next(error);
      }
    }
  };
};
