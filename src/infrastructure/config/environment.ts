/**
 * Environment Configuration
 */

export const config = {
  // Server
  port: process.env.PORT || 5000,
  nodeEnv: process.env.NODE_ENV || "development",

  // External APIs
  pythonApiUrl: process.env.PYTHON_API_URL || "http://localhost:8000",
  pythonApiTimeout: parseInt(process.env.PYTHON_API_TIMEOUT || "10000", 10),

  // CORS
  corsOrigins: process.env.CORS_ORIGINS?.split(",") || [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
  ],

  // Logging
  logLevel: process.env.LOG_LEVEL || "info",

  // Development
  isDevelopment: process.env.NODE_ENV !== "production",
  isProduction: process.env.NODE_ENV === "production",
} as const;
