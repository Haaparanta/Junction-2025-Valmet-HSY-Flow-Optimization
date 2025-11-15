FROM node:20-slim AS builder

WORKDIR /app

# Copy package files for dependency installation
COPY package.json package-lock.json ./

# Install all dependencies (including devDependencies for build)
RUN npm ci

# Copy application source code
COPY . .

# Build the production application
RUN npm run build

# Prune dev dependencies for production
RUN npm prune --production

# Production stage
FROM node:20-slim

WORKDIR /app

# Copy built application and production dependencies
COPY --from=builder /app/build ./build
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

# Set environment variables for production
ENV NODE_ENV=production
ENV PORT=5173
ENV HOST=0.0.0.0
ENV ORIGIN=https://pumptech.surf

# Expose port
EXPOSE 5173

# Run the production Node.js server (not preview)
CMD ["node", "build"]
