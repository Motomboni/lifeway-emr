# Production Dockerfile for React frontend (build + nginx)
# Build from repo root: docker build -f frontend/Dockerfile -t emr-frontend .

# Stage 1: Build React app
FROM node:22-alpine AS builder

WORKDIR /app

# Optional: pass VITE_API_URL at build time for cross-origin API
# e.g. docker build --build-arg VITE_API_URL=https://api.example.com
# When unset, uses relative /api/v1 (same-origin with nginx proxy)
ARG VITE_API_URL=
ENV VITE_API_URL=$VITE_API_URL

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

COPY frontend/ .
# Build for production (assumes API proxy at /api when served from same origin)
ENV CI=true
ENV GENERATE_SOURCEMAP=false
RUN npm run build

# Stage 2: Production nginx
FROM nginx:1.25-alpine AS runtime

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx config (path relative to repo root when building from .)
COPY docker/nginx.prod.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder
COPY --from=builder /app/build /usr/share/nginx/html

# Non-root (nginx alpine runs as nginx by default; ensure static dir is readable)
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
