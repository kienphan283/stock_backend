/**
 * Logger utility
 * Centralized logging with consistent format
 */

export enum LogLevel {
  INFO = "INFO",
  WARN = "WARN",
  ERROR = "ERROR",
  DEBUG = "DEBUG",
  SUCCESS = "SUCCESS",
}

class Logger {
  private isDevelopment = process.env.NODE_ENV !== "production";

  private formatMessage(level: LogLevel, message: string, meta?: any): string {
    const timestamp = new Date().toISOString();
    const metaStr = meta ? ` | ${JSON.stringify(meta)}` : "";
    return `[${timestamp}] [${level}] ${message}${metaStr}`;
  }

  private getEmoji(level: LogLevel): string {
    const emojiMap = {
      [LogLevel.INFO]: "📘",
      [LogLevel.WARN]: "⚠️",
      [LogLevel.ERROR]: "❌",
      [LogLevel.DEBUG]: "🔍",
      [LogLevel.SUCCESS]: "✅",
    };
    return emojiMap[level] || "📝";
  }

  info(message: string, meta?: any): void {
    const emoji = this.getEmoji(LogLevel.INFO);
    console.log(`${emoji} ${this.formatMessage(LogLevel.INFO, message, meta)}`);
  }

  warn(message: string, meta?: any): void {
    const emoji = this.getEmoji(LogLevel.WARN);
    console.warn(
      `${emoji} ${this.formatMessage(LogLevel.WARN, message, meta)}`
    );
  }

  error(message: string, error?: any): void {
    const emoji = this.getEmoji(LogLevel.ERROR);
    const errorInfo = error?.stack || error?.message || error;
    console.error(
      `${emoji} ${this.formatMessage(LogLevel.ERROR, message)}`,
      errorInfo
    );
  }

  debug(message: string, meta?: any): void {
    if (this.isDevelopment) {
      const emoji = this.getEmoji(LogLevel.DEBUG);
      console.debug(
        `${emoji} ${this.formatMessage(LogLevel.DEBUG, message, meta)}`
      );
    }
  }

  success(message: string, meta?: any): void {
    const emoji = this.getEmoji(LogLevel.SUCCESS);
    console.log(
      `${emoji} ${this.formatMessage(LogLevel.SUCCESS, message, meta)}`
    );
  }

  // Specific loggers for common use cases
  apiCall(endpoint: string, method: string = "GET"): void {
    this.info(`API Call: ${method} ${endpoint}`);
  }

  apiSuccess(endpoint: string, duration?: number): void {
    const durationStr = duration ? ` (${duration}ms)` : "";
    this.success(`API Success: ${endpoint}${durationStr}`);
  }

  apiError(endpoint: string, error: any): void {
    this.error(`API Error: ${endpoint}`, error);
  }
}

export const logger = new Logger();
