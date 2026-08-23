# Dockerfile du Dashboard.
# Build depuis la RACINE du projet : docker build -f services/dashboard/Dockerfile .

FROM node:22-slim AS build

WORKDIR /app

COPY services/dashboard/package.json services/dashboard/package-lock.json* ./
RUN npm install

COPY services/dashboard/ .
RUN npm run build

FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
