/**
 * Dividend related types
 */

export interface DividendEvent {
  id?: string;
  ticker: string;
  companyName: string;
  exDate: string;
  payDate: string;
  amount: number;
  frequency?: string;
  sector?: string;
  yield?: number;
}
