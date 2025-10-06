import { Router } from 'express'
import { PortfolioController } from '../controllers/portfolioController'

const router = Router()

router.get('/', PortfolioController.getPortfolio)

export default router
