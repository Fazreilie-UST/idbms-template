# syntax=docker/dockerfile:1.7

# ---------- Builder stage ----------
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci --no-audit --no-fund

COPY . .
RUN npm run build


# ---------- Runtime stage ----------
FROM nginx:1.27-alpine AS runtime

# Hardened config
RUN rm -f /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy compiled SPA
COPY --from=build /app/dist /usr/share/nginx/html

# Runtime env injection: writes window._env_ to /usr/share/nginx/html/env.js
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# nginx:alpine ships with a non-privileged 'nginx' user.
EXPOSE 80

ENTRYPOINT ["/entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
