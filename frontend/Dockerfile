# Etapa 1: Compilación de la SPA con Vite
FROM node:20-alpine AS build

WORKDIR /app

# Instalar dependencias con caché de capas
COPY frontend/package*.json ./
RUN npm ci

# Copiar código fuente y compilar bundle de producción
COPY frontend/ ./
RUN npm run build

# Etapa 2: Servidor Nginx y Reverse Proxy
FROM nginx:alpine AS runtime

# Copiar bundle compilado al directorio web
COPY --from=build /app/dist /usr/share/nginx/html

# Copiar configuración Nginx optimizada para SPA y proxy a la API
COPY config/nginx-spa.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
