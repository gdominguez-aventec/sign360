FROM node:20-bookworm-slim AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

ARG NUXT_PUBLIC_API_HOST=http://localhost:8000
ENV NUXT_PUBLIC_API_HOST=${NUXT_PUBLIC_API_HOST}

ARG NUXT_PUBLIC_ENV
ENV ENV=${NUXT_PUBLIC_ENV}

RUN npm run build

FROM node:20-bookworm-slim

WORKDIR /app

ENV NODE_ENV=production \
    HOST=0.0.0.0 \
    PORT=3000

COPY --from=builder /app/.output ./.output

EXPOSE 3000

CMD ["node", ".output/server/index.mjs"]
