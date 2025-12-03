import { logger } from "./logger";

type MaybePromise<T> = Promise<T> | T;
type ErrorHandler = (error: unknown) => boolean | void;

async function executeSafely<T>(
  label: string,
  fn: () => MaybePromise<T>,
  context?: string,
  onError?: ErrorHandler
): Promise<T | null> {
  try {
    return await fn();
  } catch (error) {
    const handled = onError?.(error);
    if (handled !== true) {
      const suffix = context ? ` (${context})` : "";
      logger.error(`${label}${suffix} failed`, error);
    }
    return null;
  }
}

export function wrapRedisCall<T>(
  fn: () => MaybePromise<T>,
  context?: string,
  onError?: ErrorHandler
): Promise<T | null> {
  return executeSafely("[Redis]", fn, context, onError);
}

export function wrapHttpCall<T>(
  fn: () => MaybePromise<T>,
  context?: string,
  onError?: ErrorHandler
): Promise<T | null> {
  return executeSafely("[HTTP]", fn, context, onError);
}

export function wrapWsEmit<T>(
  fn: () => MaybePromise<T>,
  context?: string,
  onError?: ErrorHandler
): Promise<T | null> {
  return executeSafely("[WebSocket]", fn, context, onError);
}
/**
 * Custom Error Classes
 * Provides specific error types for better error handling
 */

export enum ErrorCode {
  VALIDATION_ERROR = "VALIDATION_ERROR",
  NOT_FOUND = "NOT_FOUND",
  UNAUTHORIZED = "UNAUTHORIZED",
  FORBIDDEN = "FORBIDDEN",
  INTERNAL_ERROR = "INTERNAL_ERROR",
  BAD_REQUEST = "BAD_REQUEST",
  SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE",
  EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR",
}

export class AppError extends Error {
  public readonly code: ErrorCode;
  public readonly statusCode: number;
  public readonly isOperational: boolean;
  public readonly timestamp: string;

  constructor(
    message: string,
    code: ErrorCode = ErrorCode.INTERNAL_ERROR,
    statusCode: number = 500,
    isOperational: boolean = true
  ) {
    super(message);
    this.code = code;
    this.statusCode = statusCode;
    this.isOperational = isOperational;
    this.timestamp = new Date().toISOString();

    // Maintains proper stack trace for where our error was thrown
    Error.captureStackTrace(this, this.constructor);
    Object.setPrototypeOf(this, AppError.prototype);
  }

  toJSON() {
    return {
      success: false,
      error: this.message,
      code: this.code,
      timestamp: this.timestamp,
    };
  }
}

export class ValidationError extends AppError {
  constructor(message: string = "Validation failed") {
    super(message, ErrorCode.VALIDATION_ERROR, 400);
  }
}

export class NotFoundError extends AppError {
  constructor(resource: string = "Resource") {
    super(`${resource} not found`, ErrorCode.NOT_FOUND, 404);
  }
}

export class UnauthorizedError extends AppError {
  constructor(message: string = "Unauthorized") {
    super(message, ErrorCode.UNAUTHORIZED, 401);
  }
}

export class ForbiddenError extends AppError {
  constructor(message: string = "Forbidden") {
    super(message, ErrorCode.FORBIDDEN, 403);
  }
}

export class BadRequestError extends AppError {
  constructor(message: string = "Bad request") {
    super(message, ErrorCode.BAD_REQUEST, 400);
  }
}

export class ServiceUnavailableError extends AppError {
  constructor(service: string = "Service") {
    super(
      `${service} is currently unavailable`,
      ErrorCode.SERVICE_UNAVAILABLE,
      503
    );
  }
}

export class ExternalApiError extends AppError {
  public readonly apiName: string;

  constructor(apiName: string, message?: string) {
    super(
      message || `External API error: ${apiName}`,
      ErrorCode.EXTERNAL_API_ERROR,
      502
    );
    this.apiName = apiName;
  }
}
