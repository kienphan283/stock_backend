import { Router } from "express";
import { Request, Response } from "express";

const router = Router();

// Proxy financials requests to Python API
router.get("/", async (req: Request, res: Response) => {
  try {
    const { company, type, period } = req.query;

    if (!company || !type || !period) {
      return res.status(400).json({
        success: false,
        error: "Missing required parameters: company, type, period",
      });
    }

    // Call Python API
    const pythonApiUrl = process.env.PYTHON_API_URL || "http://localhost:8000";
    const params = new URLSearchParams({
      company: company as string,
      type: type as string,
      period: period as string,
    });

    const response = await fetch(`${pythonApiUrl}/api/financials?${params}`);

    if (!response.ok) {
      const error: any = await response.json();
      return res.status(response.status).json({
        success: false,
        error: error.detail || "Failed to fetch financial data from Python API",
      });
    }

    const data = await response.json();

    return res.json({
      success: true,
      data: data,
    });
  } catch (error) {
    console.error("Error fetching financials:", error);
    return res.status(500).json({
      success: false,
      error: "Internal server error",
    });
  }
});

export default router;
