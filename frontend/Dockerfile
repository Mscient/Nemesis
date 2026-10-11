FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ── Production stage — serve with nginx ──
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx config: serve SPA and proxy /api to backend
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
