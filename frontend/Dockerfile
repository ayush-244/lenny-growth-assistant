# Build stage
FROM node:20-alpine AS build

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Pass a build arg if needed, but for runtime config we often use a script or proxy.
# Since we only have a local backend, we can bake it in or just use a proxy.
# We'll just build it normally. By default, VITE_API_URL isn't strictly needed 
# if the frontend calls a relative path or a known host, but for local docker compose
# it's best to call http://localhost:8000 directly from the browser since the browser 
# runs on the host machine, NOT inside the docker network.
ENV VITE_API_URL=http://localhost:8000

RUN npm run build

# Serve stage
FROM nginx:alpine

# Copy built assets from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Replace default nginx config to allow React Router to work (if we add routes later)
# and to run on port 3000 inside the container.
RUN echo 'server { \
    listen 3000; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html index.htm; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
