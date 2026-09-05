FROM node:22-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends git python3 python3-pip bash curl ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY package*.json ./
RUN npm install --omit=dev
COPY . .
ENV HOST=0.0.0.0 PORT=8787 GRIM_DATA_DIR=/data
VOLUME ["/data"]
EXPOSE 8787
HEALTHCHECK --interval=20s --timeout=3s --retries=5 CMD curl -fsS http://127.0.0.1:8787/api/health || exit 1
CMD ["node","server.mjs"]
