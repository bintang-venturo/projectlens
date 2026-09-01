scripts/smoke_test.py

docker compose ps

docker exec pdf-rag-redis redis-cli ping

docker exec pdf-rag-postgres \
  pg_isready -U pdf_rag -d pdf_rag

curl http://localhost:8000/api/v2/heartbeat

uv run python scripts/test_gemini.py