import { Router } from "express";
import stocksRouter from "./stocks";
import portfolioRouter from "./portfolio";
import dividendsRouter from "./dividends";
import financialsRouter from "./financials";

const router = Router();

router.use("/stocks", stocksRouter);
router.use("/portfolio", portfolioRouter);
router.use("/dividends", dividendsRouter);
router.use("/financials", financialsRouter);

export default router;
