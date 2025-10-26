/**
 * Environment Configuration with Validation
 */

import { z } from "zod";

// Environment variable schema
const envSchema = z.object({
  PORT: z
    .string()
    .default("5000")
    .transform((val) => parseInt(val, 10))
    .pipe(z.number().min(1).max(65535)),

  NODE_ENV: z
    .enum(["development", "production", "test"])
    .default("development"),

  PYTHON_API_URL: z.string().url().default("http://localhost:8000"),

  PYTHON_API_TIMEOUT: z
    .string()
    .default("10000")
    .transform((val) => parseInt(val, 10))
    .pipe(z.number().positive()),

  CORS_ORIGINS: z
    .string()
    .default("http://localhost:3000,http://127.0.0.1:3000")
    .transform((val) => val.split(",")),

  LOG_LEVEL: z
    .enum(["error", "warn", "info", "debug"])
    .default("info"),
});

// Validate and parse environment variables
function validateEnv() {
  try {
    const parsed = envSchema.parse({
      PORT: process.env.PORT,
      NODE_ENV: process.env.NODE_ENV,
      PYTHON_API_URL: process.env.PYTHON_API_URL,
      PYTHON_API_TIMEOUT: process.env.PYTHON_API_TIMEOUT,
      CORS_ORIGINS: process.env.CORS_ORIGINS,
      LOG_LEVEL: process.env.LOG_LEVEL,
    });

    return parsed;
  } catch (error) {
    if (error instanceof z.ZodError) {
      console.error("❌ Invalid environment variables:");
      error.issues.forEach((issue) => {
        console.error(`  - ${issue.path.join(".")}: ${issue.message}`);
      });
      throw new Error("Environment validation failed");
    }
    throw error;
  }
}

// Validate on module load
const env = validateEnv();

// Export validated config
export const config = {
  // Server
  port: env.PORT,
  nodeEnv: env.NODE_ENV,

  // External APIs
  pythonApiUrl: env.PYTHON_API_URL,
  pythonApiTimeout: env.PYTHON_API_TIMEOUT,

  // CORS
  corsOrigins: env.CORS_ORIGINS,

  // Logging
  logLevel: env.LOG_LEVEL,

  // Development
  isDevelopment: env.NODE_ENV !== "production",
  isProduction: env.NODE_ENV === "production",
} as const;
