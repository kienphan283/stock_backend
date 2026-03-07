# Gateway Service Dockerfile
# Railway Root Directory: services/gateway-service/
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install all dependencies (including devDeps for TypeScript build)
RUN npm install

# Copy source code
COPY . .

# Build TypeScript
RUN npm run build

# Remove dev dependencies after build
RUN npm prune --production

EXPOSE 8080

CMD ["node", "dist/index.js"]
