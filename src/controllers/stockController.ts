import { Request, Response } from 'express'
import { DataService } from '../services/dataService'
import { ApiResponse } from '@stock-portfolio/shared'

export class StockController {
  static async getAllStocks(req: Request, res: Response) {
    try {
      const stocks = DataService.getAllStocks()
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
      const stock = DataService.getStockByTicker(ticker)

      if (!stock) {
        const response: ApiResponse<null> = {
          error: 'Stock not found',
          success: false
        }
        return res.status(404).json(response)
      }

      const response: ApiResponse<typeof stock> = {
        data: stock,
        success: true
      }
      res.json(response)
    } catch (error) {
      const response: ApiResponse<null> = {
        error: 'Failed to fetch stock',
        success: false
      }
      res.status(500).json(response)
    }
  }
}
