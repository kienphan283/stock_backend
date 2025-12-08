import swaggerJsdoc from "swagger-jsdoc";
import { config } from "./config";

const options: swaggerJsdoc.Options = {
    definition: {
        openapi: "3.0.0",
        info: {
            title: "Stock Analytics API",
            version: "1.0.0",
            description: "API documentation for the ExpressJS backend service",
            contact: {
                name: "API Support",
                email: "support@example.com",
            },
        },
        servers: [
            {
                url: "https://gateway-wqzu.onrender.com",
                description: "Production Render Gateway",
            },
            {
                url: `http://localhost:${config.port}`,
                description: "Local Development Server",
            },
        ],
        components: {
            securitySchemes: {
                bearerAuth: {
                    type: "http",
                    scheme: "bearer",
                    bearerFormat: "JWT",
                },
            },
        },
        security: [
            {
                bearerAuth: [],
            },
        ],
    },
    apis: ["./src/api/routes/*.ts"], // Path to the API docs
};

export const swaggerSpec = swaggerJsdoc(options);
