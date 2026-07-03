# syntax=docker/dockerfile:1
# Build-only image — output (dist/) is consumed by deploy/Dockerfile.caddy.
# There is no runtime stage here; the frontend is served as static files by Caddy.
FROM node:20-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build
