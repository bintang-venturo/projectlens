#!/usr/bin/env bash

echo "Stopping all ProjectLens services..."

pkill -f "manage.py runserver" 2>/dev/null && echo "  ✓ Django stopped" || echo "  - Django not running"
pkill -f "celery -A config worker" 2>/dev/null && echo "  ✓ Celery stopped" || echo "  - Celery not running"
docker compose stop 2>/dev/null && echo "  ✓ Docker containers stopped" || echo "  - Docker containers not running"

echo "Done."
