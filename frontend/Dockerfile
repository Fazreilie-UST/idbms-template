# Build stage
FROM node:20 AS build

WORKDIR /app
COPY . .
RUN npm install
RUN npm run build

# Production stage (nginx)
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]

EXPOSE 80