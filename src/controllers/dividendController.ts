import { Request, Response } from 'express'
import { DividendEvent } from '@stock-portfolio/shared'

const mockDividendEvents: DividendEvent[] = [
  {
    ticker: 'AAPL',
    companyName: 'Apple Inc.',
    amount: 0.24,
    payDate: '2024-11-14',
    exDate: '2024-11-11',
    sector: 'Technology',
    yield: 0.52
  },
  {
    ticker: 'MSFT',
    companyName: 'Microsoft Corporation',
    amount: 0.75,
    payDate: '2024-11-14',
    exDate: '2024-11-11',
    sector: 'Technology',
    yield: 0.8
  },
  {
    ticker: 'JNJ',
    companyName: 'Johnson & Johnson',
    amount: 1.13,
    payDate: '2024-11-12',
    exDate: '2024-11-09',
    sector: 'Healthcare',
    yield: 2.9
  }
]

export class DividendController {
  static async getDividendCalendar(req: Request, res: Response) {
    try {
      res.json({ data: mockDividendEvents, success: true })
    } catch (error) {
      res.status(500).json({ error: 'Failed to fetch dividend calendar', success: false })
    }
  }

  static async getExDividendCalendar(req: Request, res: Response) {
    try {
      res.json({ data: mockDividendEvents, success: true })
    } catch (error) {
      res.status(500).json({ error: 'Failed to fetch ex-dividend calendar', success: false })
    }
  }
}
