# ── Stage 1: Build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app

# Copy lockfile & install (ci = reproducible, exact lock)
COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps

# Copy source then build Next.js (server mode, NOT static export)
COPY . .
RUN npm run build

# ── Stage 2: Production runtime ───────────────────────────────────────────────
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
# PORT is injected by Railway; default to 3000 for safety
ENV PORT=3000

# Only copy what's needed at runtime (reduces image size ~60%)
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

EXPOSE 3000

CMD ["npm", "start"]
