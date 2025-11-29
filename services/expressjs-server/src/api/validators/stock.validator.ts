/**
 * Stock Validators
 * Request validation schemas for stock endpoints
 */

import { z } from "zod";

export const tickerParamSchema = z.object({
  ticker: z.string().min(1).max(10).toUpperCase(),
});

export const periodQuerySchema = z.object({
  period: z
    .enum(["1d", "5d", "1m", "3m", "6m", "1y", "5y", "max"])
    .optional()
    .default("3m"),
});

export const limitQuerySchema = z.object({
  limit: z.coerce.number().int().min(1).max(100).optional().default(16),
});

export const searchQuerySchema = z.object({
  query: z.string().min(1).max(100),
});

export type TickerParam = z.infer<typeof tickerParamSchema>;
export type PeriodQuery = z.infer<typeof periodQuerySchema>;
export type LimitQuery = z.infer<typeof limitQuerySchema>;
export type SearchQuery = z.infer<typeof searchQuerySchema>;
