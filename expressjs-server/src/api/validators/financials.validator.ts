/**
 * Financials Validators
 * Zod schemas for validating financial data requests
 */

import { z } from "zod";

// Statement types validation (matches Python API expectations)
export const statementTypeSchema = z.enum([
    "IS",  // Income Statement
    "BS",  // Balance Sheet
    "CF",  // Cash Flow
]);

// Period types validation
export const periodTypeSchema = z.enum(["annual", "quarterly"]);

// Query parameters validation for GET /api/financials
export const getFinancialsQuerySchema = z.object({
    company: z
        .string()
        .min(1, "Company ticker is required")
        .max(10, "Company ticker must be at most 10 characters")
        .toUpperCase(),
    type: statementTypeSchema,
    period: periodTypeSchema,
});

export type GetFinancialsQuery = z.infer<typeof getFinancialsQuerySchema>;

