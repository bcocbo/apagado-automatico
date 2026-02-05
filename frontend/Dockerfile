# Frontend container with Nginx and task scheduler
FROM nginx:alpine

# Install necessary packages
RUN apk add --no-cache \
    curl \
    wget \
    nodejs \
    npm

# Create app directory
WORKDIR /usr/share/nginx/html

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Copy HTML files and assets
COPY src/ ./

# Install FullCalendar and other dependencies
RUN npm init -y && \
    npm install @fullcalendar/core @fullcalendar/daygrid @fullcalendar/timegrid @fullcalendar/interaction

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]