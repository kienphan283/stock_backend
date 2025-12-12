/**
 * Environment Configuration with Validation
 */

import fs from "fs";
import path from "path";
import dotenv from "dotenv";
import { z } from "zod";
import { logger } from "../utils";

const candidateEnvPaths = [
  path.resolve(process.cwd(), ".env"),
  path.resolve(process.cwd(), "..", ".env"),
  path.resolve(__dirname, "../../../.env"),
  path.resolve(__dirname, "../../.env"),
];

let envLoaded = false;
for (const envPath of candidateEnvPaths) {
  if (fs.existsSync(envPath)) {
    dotenv.config({ path: envPath });
    envLoaded = true;
    break;
  }
}

if (!envLoaded) {
  dotenv.config();
}

// Environment variable schema
const envSchema = z.object({
  PORT: z
    .string()
    .default("5000")
    .transform((val: string) => parseInt(val, 10))
    .pipe(z.number().min(1).max(65535)),

  NODE_ENV: z
    .enum(["development", "production", "test"])
    .default("development"),

  MARKET_API_URL: z.string().url().default("http://localhost:8000"),

  MARKET_API_TIMEOUT: z
    .string()
    .default("10000")
    .transform((val: string) => parseInt(val, 10))
    .pipe(z.number().positive()),

  CORS_ORIGINS: z
    .string()
    .default("http://localhost:3000,http://127.0.0.1:3000")
    .transform((val: string) => val.split(",")),

  LOG_LEVEL: z
    .enum(["error", "warn", "info", "debug"])
    .default("info"),

  REDIS_URL: z.string().optional(),
  REDIS_HOST: z.string().default("redis"),
  REDIS_PORT: z
    .string()
    .default("6379")
    .transform((val: string) => parseInt(val, 10)),

  JWT_SECRET: z.string().default("super-secret-key-change-me-in-prod"),
});

// Validate and parse environment variables
function validateEnv() {
  try {
    const marketApiUrlRaw = process.env.MARKET_API_URL || process.env.PYTHON_API_URL || process.env.FASTAPI_URL;
    const parsed = envSchema.parse({
      PORT: process.env.PORT,
      NODE_ENV: process.env.NODE_ENV,
      MARKET_API_URL: marketApiUrlRaw,
      MARKET_API_TIMEOUT: process.env.MARKET_API_TIMEOUT || process.env.PYTHON_API_TIMEOUT,
      CORS_ORIGINS: process.env.CORS_ORIGINS,
      LOG_LEVEL: process.env.LOG_LEVEL,
      REDIS_URL: process.env.REDIS_URL,
      REDIS_HOST: process.env.REDIS_HOST,
      REDIS_PORT: process.env.REDIS_PORT,
      JWT_SECRET: process.env.JWT_SECRET,
    });

    return parsed;
  } catch (error) {
    if (error instanceof z.ZodError) {
      logger.error("❌ Invalid environment variables:");
      error.issues.forEach((issue: z.ZodIssue) => {
        logger.error(`  - ${issue.path.join(".")}: ${issue.message}`);
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
  pythonApiUrl: env.MARKET_API_URL, // Keep for backward compatibility
  marketApiUrl: env.MARKET_API_URL,
  pythonApiTimeout: env.MARKET_API_TIMEOUT, // Keep for backward compatibility
  marketApiTimeout: env.MARKET_API_TIMEOUT,

  // CORS
  corsOrigins: env.CORS_ORIGINS,

  // Logging
  logLevel: env.LOG_LEVEL,

  // Redis
  redisUrl: env.REDIS_URL,
  redisHost: env.REDIS_HOST,
  redisPort: env.REDIS_PORT,

  // Security
  jwtSecret: env.JWT_SECRET,

  // Development
  isDevelopment: env.NODE_ENV !== "production",
  isProduction: env.NODE_ENV === "production",
} as const;
