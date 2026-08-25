FROM node:22-alpine AS build
WORKDIR /app
COPY package.json tsconfig.json ./
RUN npm install
COPY src ./src
COPY test ./test
RUN npm run build && npm test

FROM node:22-alpine
WORKDIR /app
COPY --from=build /app/dist ./dist
COPY public ./public
COPY package.json ./package.json
ENV XUNIA_PLATFORM_HOST=0.0.0.0
ENV XUNIA_PLATFORM_PORT=4400
EXPOSE 4400
CMD ["node", "dist/src/server.js"]
