const SERVICE_NAME = "gateway-service";

enum LogLevel {
  INFO = "info",
  WARN = "warn",
  ERROR = "error",
}

type ConsoleFn = (...args: unknown[]) => void;

class Logger {
  private emit(level: LogLevel, consoleMethod: ConsoleFn, args: unknown[]): void {
    const [message, ...rest] = args;
    const payload: Record<string, unknown> = {
      service: SERVICE_NAME,
      level,
      timestamp: new Date().toISOString(),
      message: typeof message === "string" ? message : String(message),
    };

    if (rest.length === 1 && typeof rest[0] === "object") {
      Object.assign(payload, rest[0] as Record<string, unknown>);
    } else if (rest.length > 0) {
      payload.meta = rest;
    }

    consoleMethod(JSON.stringify(payload));
  }

  info(...args: unknown[]): void {
    this.emit(LogLevel.INFO, console.log, args);
  }

  warn(...args: unknown[]): void {
    this.emit(LogLevel.WARN, console.warn, args);
  }

  error(...args: unknown[]): void {
    this.emit(LogLevel.ERROR, console.error, args);
  }

  success(...args: unknown[]): void {
    this.info(...args);
  }

  apiCall(endpoint: string, method: string = "GET"): void {
    this.info(`api_call`, { endpoint, method });
  }

  apiSuccess(endpoint: string, duration?: number): void {
    this.info(`api_success`, { endpoint, duration });
  }

  apiError(endpoint: string, error: unknown): void {
    this.error(`api_error`, { endpoint, error });
  }
}

export const logger = new Logger();
