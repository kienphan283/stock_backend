/**
 * Centralized validation helpers for gateway service.
 */

const SYMBOL_REGEX = /^[A-Z][A-Z0-9\.\-]{0,9}$/;

import { ValidationError } from "./errorHandler";

export function normalizeSymbol(raw: string): string {
  const candidate = (raw || "").trim().toUpperCase();
  if (!candidate || !SYMBOL_REGEX.test(candidate)) {
    throw new ValidationError(`Invalid symbol: ${raw}`);
  }
  return candidate;
}

export function parseSymbolsCsv(csv: string): string[] {
  const parts = (csv || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  const deduped: string[] = [];
  const seen = new Set<string>();
  for (const part of parts) {
    const normalized = normalizeSymbol(part);
    if (!seen.has(normalized)) {
      seen.add(normalized);
      deduped.push(normalized);
    }
  }
  if (deduped.length === 0) {
    throw new ValidationError("At least one valid symbol is required");
  }
  return deduped;
}


