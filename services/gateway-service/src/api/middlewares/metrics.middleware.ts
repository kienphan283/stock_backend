import client from "prom-client";
import { Request, Response, NextFunction } from "express";

client.collectDefaultMetrics();

const requestCounter = new client.Counter({
  name: "gateway_http_requests_total",
  help: "Total number of HTTP requests processed by the gateway",
  labelNames: ["method", "path", "status"] as const,
});

const requestDuration = new client.Histogram({
  name: "gateway_http_request_duration_seconds",
  help: "Request duration in seconds",
  buckets: [0.05, 0.1, 0.3, 0.5, 1, 2, 5],
  labelNames: ["method", "path", "status"] as const,
});

export const metricsMiddleware = (
  req: Request,
  res: Response,
  next: NextFunction
) => {
  const end = requestDuration.startTimer({
    method: req.method,
    path: req.route?.path || req.path,
  });

  res.on("finish", () => {
    const labels = {
      method: req.method,
      path: req.route?.path || req.path,
      status: String(res.statusCode),
    };
    requestCounter.inc(labels);
    end(labels);
  });

  next();
};

export async function metricsHandler(_: Request, res: Response) {
  res.set("Content-Type", client.register.contentType);
  res.end(await client.register.metrics());
}


