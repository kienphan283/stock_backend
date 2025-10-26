/**
 * Stock related types
 */

export interface Stock {
  ticker: string;
  name: string;
  price: number;
  change?: number;
  changePercent?: number;
  volume?: number;
  marketCap?: number;
  pe?: number;
  eps?: number;
  high52?: number;
  low52?: number;
  sector: string;
  industry?: string;
  description?: string;
  website?: string;
  logo?: string;
}
