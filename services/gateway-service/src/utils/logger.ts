const SERVICE_PREFIX = "[gateway-service]";

enum LogLevel {
  INFO = "INFO",
  WARN = "WARN",
  ERROR = "ERROR",
}

class Logger {
  private formatPrefix(level: LogLevel): string {
    const timestamp = new Date().toISOString();
    return `${SERVICE_PREFIX} ${timestamp} ${level}`;
  }

  private log(
    level: LogLevel,
    consoleMethod: (...args: unknown[]) => void,
    args: unknown[]
  ): void {
    consoleMethod(this.formatPrefix(level), ...args);
  }

  info(...args: unknown[]): void {
    this.log(LogLevel.INFO, console.log, args);
  }

  warn(...args: unknown[]): void {
    this.log(LogLevel.WARN, console.warn, args);
  }

  error(...args: unknown[]): void {
    this.log(LogLevel.ERROR, console.error, args);
  }

  success(...args: unknown[]): void {
    this.info(...args);
  }

  apiCall(endpoint: string, method: string = "GET"): void {
    this.info(`API Call: ${method} ${endpoint}`);
  }

  apiSuccess(endpoint: string, duration?: number): void {
    const durationStr = duration ? ` (${duration}ms)` : "";
    this.info(`API Success: ${endpoint}${durationStr}`);
  }

  apiError(endpoint: string, error: unknown): void {
    this.error(`API Error: ${endpoint}`, error);
  }
}

export const logger = new Logger();
