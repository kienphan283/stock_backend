/**
 * Portfolio Validators
 * Request validation schemas for portfolio endpoints
 */

import { z } from "zod";

export const portfolioItemSchema = z.object({
  ticker: z.string().min(1).max(10).toUpperCase(),
  quantity: z.number().int().min(1),
  cost: z.number().min(0),
});

export const updatePortfolioItemSchema = z.object({
  quantity: z.number().int().min(1).optional(),
  cost: z.number().min(0).optional(),
});

export type PortfolioItemInput = z.infer<typeof portfolioItemSchema>;
export type UpdatePortfolioItemInput = z.infer<
  typeof updatePortfolioItemSchema
>;
