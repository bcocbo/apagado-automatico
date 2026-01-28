# Multi-stage build para React frontend
FROM node:18-alpine as builder

WORKDIR /app

# Copiar package files
COPY package*.json ./

# Instalar dependencias
RUN npm install --only=production --silent

# Copiar código fuente
COPY . .

# Build de la aplicación
RUN npm run build

# Etapa de producción con nginx
FROM nginx:alpine

# Crear usuario no-root
RUN addgroup -g 1001 -S appuser && \
    adduser -S appuser -G appuser -u 1001

# Copiar archivos build desde la carpeta build (no dist)
COPY --from=builder /app/build /usr/share/nginx/html

# Configuración nginx personalizada
COPY nginx.conf /etc/nginx/nginx.conf

# Crear directorios necesarios y asignar permisos
RUN mkdir -p /var/cache/nginx /var/log/nginx /var/run && \
    chown -R appuser:appuser /var/cache/nginx /var/log/nginx /var/run /usr/share/nginx/html /etc/nginx

# Cambiar a usuario no-root
USER appuser

# Exponer puerto
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Comando por defecto
CMD ["nginx", "-g", "daemon off;"]