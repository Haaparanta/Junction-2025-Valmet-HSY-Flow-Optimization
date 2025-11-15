#!/bin/bash
set -e

# Production startup script for Google Cloud Run

# Replace placeholders in nginx config with actual environment variables
sed -i "s/PORT_PLACEHOLDER/${PORT:-8080}/g" /etc/nginx/sites-available/app
sed -i "s/BACKEND_PORT_PLACEHOLDER/${BACKEND_PORT:-8000}/g" /etc/nginx/sites-available/app
sed -i "s/FRONTEND_PORT_PLACEHOLDER/${FRONTEND_PORT:-5173}/g" /etc/nginx/sites-available/app

# Test nginx configuration
nginx -t

# Start backend in background
echo "Starting backend API on port ${BACKEND_PORT:-8000}..."
/app/start-backend.sh &
BACKEND_PID=$!

# Start frontend in background
echo "Starting frontend on port ${FRONTEND_PORT:-5173}..."
/app/start-frontend.sh > /var/log/frontend-startup.log 2>&1 &
FRONTEND_PID=$!

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 5

# Health check: verify backend is running
echo "Checking backend health..."
for i in {1..10}; do
    if curl -f http://localhost:${BACKEND_PORT:-8000}/api/health >/dev/null 2>&1; then
        echo "✓ Backend health check passed"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "⚠ Warning: Backend health check failed after 10 attempts"
        echo "Backend logs:"
        tail -20 /var/log/backend.out.log 2>/dev/null || echo "No backend logs found"
    fi
    sleep 1
done

# Health check: verify frontend is running
echo "Checking frontend health..."
for i in {1..10}; do
    if curl -f http://localhost:${FRONTEND_PORT:-5173}/ >/dev/null 2>&1; then
        echo "✓ Frontend health check passed"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "⚠ Warning: Frontend health check failed after 10 attempts"
        echo "Frontend startup logs:"
        cat /var/log/frontend-startup.log 2>/dev/null || echo "No frontend startup logs found"
        echo "Checking if frontend process is running..."
        ps aux | grep -E "node|frontend" | grep -v grep || echo "No frontend process found"
    fi
    sleep 1
done

# Function to cleanup on exit (for graceful shutdown)
cleanup() {
    echo "Shutting down services..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    exit
}
trap cleanup SIGTERM SIGINT

# Start nginx in foreground (Cloud Run expects main process to listen on PORT)
echo "Starting nginx on port ${PORT:-8080}..."
exec nginx -g "daemon off;"

