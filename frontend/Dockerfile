FROM node:20-alpine

# Enable corepack so pnpm is available without host install
RUN corepack enable && corepack prepare pnpm@9 --activate

WORKDIR /app

# Copy package manifest first for layer caching
COPY package.json pnpm-lock.yaml* ./

# Install deps (lockfile optional on first run)
RUN pnpm install --frozen-lockfile 2>/dev/null || pnpm install

# Source copied here; overridden by volume mount in dev
COPY . .

EXPOSE 5173

# --host 0.0.0.0 is required to be reachable from outside the container
CMD ["pnpm", "dev", "--host", "0.0.0.0"]
