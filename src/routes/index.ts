import { Router } from 'express'
import stocksRouter from './stocks'
import portfolioRouter from './portfolio'
import dividendsRouter from './dividends'

const router = Router()

router.use('/stocks', stocksRouter)
router.use('/portfolio', portfolioRouter)
router.use('/dividends', dividendsRouter)

export default router
