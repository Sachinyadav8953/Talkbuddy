# Stage 1: Build React assets
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Stage 2: Serve compiled assets with Nginx
FROM nginx:alpine

# Copy custom nginx configuration for React routing fallback if necessary
# In simple cases, default configuration is fine. If routing is handled in react, we copy a custom conf:
# COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
