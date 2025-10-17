import { Request, Response } from 'express'
import { DataService } from '../services/dataService'
import { ApiResponse } from '../types/shared'

export class StockController {
  static async getAllStocks(req: Request, res: Response) {
    try {
      // Use async method since dataService now uses real data
      const stocks = await DataService.getAllStocks()
      const response: ApiResponse<typeof stocks> = {
        data: stocks,
        success: true
      }
      res.json(response)
    } catch (error) {
      const response: ApiResponse<null> = {
        error: 'Failed to fetch stocks',
        success: false
      }
      res.status(500).json(response)
    }
  }

  static async getStockByTicker(req: Request, res: Response) {
    try {
      const { ticker } = req.params

      // Try to get real data first, fallback to mock data
      const stock = await DataService.getStockByTickerWithRealData(ticker)

      if (!stock) {
        const response: ApiResponse<null> = {
          error: 'Stock not found',
          success: false
        }
        res.status(404).json(response)
        return
      }

      const response: ApiResponse<typeof stock> = {
        data: stock,
        success: true
      }
      res.json(response)
    } catch (error) {
      console.error('Error in getStockByTicker:', error)
      const response: ApiResponse<null> = {
        error: 'Failed to fetch stock',
        success: false
      }
      res.status(500).json(response)
    }
  }

  // New endpoint for real-time quote
  static async getStockQuote(req: Request, res: Response) {
    try {
      const { ticker } = req.params
      const quote = await DataService.getRealStockQuote(ticker)

      if (!quote) {
        const response: ApiResponse<null> = {
          error: 'Quote not available',
          success: false
        }
        res.status(404).json(response)
        return
      }

      const response: ApiResponse<typeof quote> = {
        data: quote,
        success: true
      }
      res.json(response)
    } catch (error) {
      console.error('Error in getStockQuote:', error)
      const response: ApiResponse<null> = {
        error: 'Failed to fetch quote',
        success: false
      }
      res.status(500).json(response)
    }
  }

  // New endpoint for price history
  static async getPriceHistory(req: Request, res: Response) {
    try {
      const { ticker } = req.params
      const { period = '3m' } = req.query

      const priceHistory = await DataService.getRealPriceHistory(period as string)

      if (!priceHistory) {
        const response: ApiResponse<null> = {
          error: 'Price history not available',
          success: false
        }
        res.status(404).json(response)
        return
      }

      const response: ApiResponse<typeof priceHistory> = {
        data: priceHistory,
        success: true
      }
      res.json(response)
    } catch (error) {
      console.error('Error in getPriceHistory:', error)
      const response: ApiResponse<null> = {
        error: 'Failed to fetch price history',
        success: false
      }
      res.status(500).json(response)
    }
  }

  // New endpoint for company news
  static async getCompanyNews(req: Request, res: Response) {
    try {
      const { ticker } = req.params
      const { limit = 16 } = req.query

      const news = await DataService.getRealNews(Number(limit))

      if (!news) {
        const response: ApiResponse<null> = {
          error: 'News not available',
          success: false
        }
        res.status(404).json(response)
        return
      }

      const response: ApiResponse<typeof news> = {
        data: news,
        success: true
      }
      res.json(response)
    } catch (error) {
      console.error('Error in getCompanyNews:', error)
      const response: ApiResponse<null> = {
        error: 'Failed to fetch news',
        success: false
      }
      res.status(500).json(response)
    }
  }

  // New endpoint for financials
  static async getFinancials(req: Request, res: Response) {
    try {
      const { ticker } = req.params
      const financials = await DataService.getRealFinancials()

      if (!financials) {
        const response: ApiResponse<null> = {
          error: 'Financials not available',
          success: false
        }
        res.status(404).json(response)
        return
      }

      const response: ApiResponse<typeof financials> = {
        data: financials,
        success: true
      }
      res.json(response)
    } catch (error) {
      console.error('Error in getFinancials:', error)
      const response: ApiResponse<null> = {
        error: 'Failed to fetch financials',
        success: false
      }
      res.status(500).json(response)
    }
  }

  // New endpoint for earnings
  static async getEarnings(req: Request, res: Response) {
    try {
      const { ticker } = req.params
      const earnings = await DataService.getRealEarnings()

      if (!earnings) {
        const response: ApiResponse<null> = {
          error: 'Earnings not available',
          success: false
        }
        res.status(404).json(response)
        return
      }

      const response: ApiResponse<typeof earnings> = {
        data: earnings,
        success: true
      }
      res.json(response)
    } catch (error) {
      console.error('Error in getEarnings:', error)
      const response: ApiResponse<null> = {
        error: 'Failed to fetch earnings',
        success: false
      }
      res.status(500).json(response)
    }
  }

  // New endpoint to refresh data
  static async refreshData(req: Request, res: Response) {
    try {
      const success = await DataService.refreshStockData()

      const response: ApiResponse<{ refreshed: boolean }> = {
        data: { refreshed: success },
        success: success
      }

      if (success) {
        res.json(response)
      } else {
        res.status(500).json({
          ...response,
          error: 'Failed to refresh data'
        })
      }
    } catch (error) {
      console.error('Error in refreshData:', error)
      const response: ApiResponse<null> = {
        error: 'Failed to refresh data',
        success: false
      }
      res.status(500).json(response)
    }
  }
}
