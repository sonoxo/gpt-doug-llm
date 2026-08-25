FROM node:22-alpine AS build
WORKDIR /app
COPY package.json tsconfig.json ./
RUN npm install --ignore-scripts
COPY src ./src
COPY test ./test
RUN npm run test

FROM node:22-alpine AS runtime
WORKDIR /app
RUN addgroup -S xunia && adduser -S -G xunia -h /app xunia && mkdir -p /data && chown -R xunia:xunia /app /data
COPY --from=build --chown=xunia:xunia /app/dist ./dist
COPY --chown=xunia:xunia public ./public
COPY --chown=xunia:xunia package.json ./package.json
ENV NODE_ENV=production \
    XUNIA_PLATFORM_HOST=0.0.0.0 \
    XUNIA_PLATFORM_PORT=4400 \
    XUNIA_DATA_DIR=/data
USER xunia
EXPOSE 4400
VOLUME ["/data"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD node -e "fetch('http://127.0.0.1:4400/health').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"
CMD ["node", "dist/src/server.js"]
