FROM node:22-bookworm-slim AS build
WORKDIR /app
COPY package*.json tsconfig.json ./
RUN npm install --no-audit --no-fund
COPY src ./src
COPY test ./test
RUN npm run build && npm test

FROM node:22-bookworm-slim
WORKDIR /app
ENV NODE_ENV=production XUNIA_PORT=4317 XUNIA_DATA=/app/.xunia/chain.json
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/dist ./dist
RUN mkdir -p /app/.xunia && chown -R node:node /app
USER node
EXPOSE 4317
CMD ["node", "dist/src/node.js"]
