#!/usr/bin/env bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

DJANGO_PORT="${DJANGO_PORT:-8001}"

echo "========================================="
echo "  ProjectLens — Starting all services"
echo "========================================="
echo ""

# 1) Docker containers (Postgres, Redis, ChromaDB)
echo "[1/3] Starting Docker containers..."
docker compose up -d
echo "  ✓ Postgres  → localhost:5433"
echo "  ✓ Redis     → localhost:6379"
echo "  ✓ ChromaDB  → localhost:8000"
echo ""

# Wait for Postgres to be healthy
echo "  Waiting for Postgres..."
until docker exec projectlens-postgres pg_isready -U pdf_rag -d pdf_rag -q 2>/dev/null; do
  sleep 1
done
echo "  ✓ Postgres ready"
echo ""

# 2) Celery worker
echo "[2/3] Starting Celery worker..."
pkill -f "celery -A config worker" 2>/dev/null || true
sleep 1
.venv/bin/celery -A config worker -l info > logs/celery.log 2>&1 &
CELERY_PID=$!
echo "  ✓ Celery worker (PID $CELERY_PID) → logs/celery.log"
echo ""

# 3) Django dev server
echo "[3/3] Starting Django server..."
pkill -f "manage.py runserver" 2>/dev/null || true
sleep 1
.venv/bin/python manage.py runserver "$DJANGO_PORT" > logs/django.log 2>&1 &
DJANGO_PID=$!
echo "  ✓ Django (PID $DJANGO_PID) → http://127.0.0.1:$DJANGO_PORT/"
echo ""

echo "========================================="
echo "  All services running!"
echo "  App: http://127.0.0.1:$DJANGO_PORT/"
echo ""
echo "  Logs:"
echo "    tail -f logs/django.log"
echo "    tail -f logs/celery.log"
echo ""
echo "  Stop all:"
echo "    ./stop.sh"
echo "========================================="
