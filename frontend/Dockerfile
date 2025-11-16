# Build stage
FROM node:20-slim AS builder

WORKDIR /app

# Copy package files
COPY frontend/package.json frontend/package-lock.json ./

# Install deps (including devDeps)
RUN npm ci

# Copy source
COPY frontend/ .

# Build production bundle (SvelteKit)
RUN npm run build

# Remove dev deps
RUN npm prune --production

# Runtime stage
FROM node:20-slim

WORKDIR /app

# Copy built app + production deps
COPY --from=builder /app/build ./build
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

# Environment
ENV NODE_ENV=production
ENV PORT=5173
ENV HOST=0.0.0.0
ENV ORIGIN=https://pumptech.surf

EXPOSE 5173


CMD ["node", "build/index.js"]
