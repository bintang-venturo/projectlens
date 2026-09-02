# ProjectLens

A Django-based RAG (Retrieval-Augmented Generation) application with a web UI. Upload PDF documents, index their contents into a vector database, and ask natural-language questions answered with source citations.

Upload a PDF. Ask a question. Get an answer grounded in your documents, with the exact source file and page number — all from the browser or the REST API.

## How It Works

```
PDF Upload → Parse Pages → Chunk Text → Embed → Store in ChromaDB
                                                        │
Question → Embed Query → Search ChromaDB → Top-K Chunks ┘
                                                │
                                    Build Context + Prompt
                                                │
                                        AI Provider (Gemini)
                                                │
                                    Answer + Source Citations
```

1. You upload a PDF via the web UI or the REST API.
2. A Celery worker asynchronously parses the PDF page by page, splits the text into chunks, generates vector embeddings, and stores them in ChromaDB.
3. You ask a question via the chat page or the chat API.
4. The system embeds your question, retrieves the most relevant chunks from ChromaDB, feeds them as context to an AI model, and returns an answer with citations pointing back to the source document and page.

## Prerequisites

- **Python 3.12+**
- **Docker and Docker Compose** (for PostgreSQL, Redis, and ChromaDB)
- **uv** (Python package manager) — install with `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **A Google Gemini API key** — get one at https://aistudio.google.com/apikey

## Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd projectlens
```

### 2. Start infrastructure services

```bash
docker compose up -d
```

This starts:

| Service    | Port  | Purpose             |
|------------|-------|---------------------|
| PostgreSQL | 5433  | Application database |
| Redis      | 6379  | Celery message broker |
| ChromaDB   | 8000  | Vector database      |

### 3. Configure environment variables

Copy the example and fill in your API key:

```bash
cp .env.example .env
```

Edit `.env` and set your Gemini API key:

```env
EMBEDDING_API_KEY=your-gemini-api-key-here
```

The full list of environment variables:

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `change-me-in-development` | Django secret key |
| `DEBUG` | `False` | Django debug mode |
| `DATABASE_NAME` | — | PostgreSQL database name |
| `DATABASE_USER` | — | PostgreSQL user |
| `DATABASE_PASSWORD` | — | PostgreSQL password |
| `DATABASE_HOST` | `localhost` | PostgreSQL host |
| `DATABASE_PORT` | — | PostgreSQL port |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `CHROMA_HOST` | `localhost` | ChromaDB host |
| `CHROMA_PORT` | `8000` | ChromaDB port |
| `EMBEDDING_PROVIDER` | `gemini` | Embedding provider name |
| `EMBEDDING_MODEL` | `text-embedding-004` | Embedding model name |
| `EMBEDDING_API_KEY` | — | API key for embedding and generation |
| `GENERATION_PROVIDER` | `gemini` | Generation provider name |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini generation model |
| `CHUNK_SIZE` | `1000` | Maximum characters per text chunk |
| `CHUNK_OVERLAP` | `150` | Character overlap between chunks |
| `RETRIEVAL_K` | `5` | Number of chunks retrieved per query |
| `MAX_UPLOAD_SIZE` | `52428800` | Maximum upload file size in bytes (50 MB) |
| `CHAT_HISTORY_LIMIT` | `10` | Maximum number of prior messages included in chat context |

### 4. Install dependencies

```bash
uv sync
```

### 5. Run database migrations

```bash
uv run python manage.py migrate
```

### 6. Start all services

```bash
python run.py
```

This starts Docker containers, Celery worker, and Django dev server in one command, then runs health checks to verify everything is working.

The application is now available at `http://localhost:8001` (port 8000 is used by ChromaDB).

#### Service management commands

| Command | Description |
|---------|-------------|
| `python run.py` | Start all services + health check |
| `python run.py --stop` | Stop all services |
| `python run.py --status` | Check status of all services |

#### What `run.py` does

1. **Docker containers** — starts Postgres, Redis, ChromaDB and waits for each port to be ready
2. **Celery worker** — kills any stale worker, starts a fresh one, verifies all tasks are registered (including `run_project_analysis`)
3. **Django server** — starts on port 8001 (configurable via `DJANGO_PORT` env var)
4. **Health checks** — HTTP check on Django, Redis PING, Postgres readiness, ChromaDB port, Celery task registration, and auto-cleanup of stuck analyses

Logs are written to `logs/django.log` and `logs/celery.log`.

#### Manual startup (alternative)

If you prefer to start services individually in separate terminals:

```bash
# Terminal 1 — Celery worker
uv run celery -A config worker --loglevel=info

# Terminal 2 — Django server (use port 8001, since ChromaDB uses 8000)
uv run python manage.py runserver 8001
```

> **Important:** If you add new Celery tasks (e.g. in a new Django app), you must restart the Celery worker for it to pick up the new tasks. A stale worker will silently drop unregistered tasks, leaving background jobs stuck in `PENDING` forever.

## Web UI

Open `http://localhost:8001` in your browser. The UI has three pages:

| Page | URL | Description |
|------|-----|-------------|
| Chat | `/` | Ask questions about your documents. Answers include source citations. Supports multi-turn conversations with session history. |
| Document Library | `/documents/` | Upload PDFs via drag-and-drop or file picker. View all documents with their processing status. Status auto-refreshes every 5 seconds while documents are being processed. |
| Settings | `/settings/` | Placeholder page (not wired to backend). |

The frontend uses Django templates with htmx for dynamic updates and Alpine.js for client-side interactivity. No build step required.

## REST API

The same functionality is also available via the REST API for programmatic access.

### Upload a PDF

```bash
curl -X POST http://localhost:8001/api/documents/ \
  -F "file=@/path/to/your/document.pdf"
```

Response:

```json
{
  "id": "a1b2c3d4-...",
  "name": "document.pdf",
  "file_size": 204800,
  "page_count": null,
  "status": "PENDING",
  "error_message": null,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

The document is processed asynchronously by the Celery worker. The status will transition from `PENDING` → `PROCESSING` → `COMPLETED` (or `FAILED` if something goes wrong).

### Check document status

```bash
curl http://localhost:8001/api/documents/{id}/
```

Wait until `status` is `COMPLETED` before asking questions.

### List all documents

```bash
curl http://localhost:8001/api/documents/
```

### Ask a question

```bash
curl -X POST http://localhost:8001/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"question": "How much money does each player start with?"}'
```

Response:

```json
{
  "session_id": "a1b2c3d4-...",
  "answer": "Each player starts with $1,500.",
  "citations": [
    {
      "source": "monopoly.pdf",
      "page": 4
    }
  ]
}
```

The answer is generated using only the content from your uploaded documents. Citations point to the exact source file and page number.

### Continue a conversation

Send the `session_id` from a previous response to continue the conversation with history:

```bash
curl -X POST http://localhost:8001/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"question": "What denominations is that divided into?", "session_id": "a1b2c3d4-..."}'
```

The AI model receives the prior conversation history so it can understand follow-up questions in context. Omit `session_id` (or send `null`) to start a fresh conversation.

### API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/documents/` | Upload a PDF document |
| `GET` | `/api/documents/` | List all documents |
| `GET` | `/api/documents/{id}/` | Get document details and status |
| `POST` | `/api/chat/` | Ask a question (supports conversation history via `session_id`) |

### Error responses

All errors return JSON with consistent structure:

```json
{
  "field_name": ["Error message."]
}
```

Common status codes:

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Document created |
| 400 | Validation error (bad input, non-PDF, empty file) |
| 404 | Document not found |

## Resetting Data

To clear all application data (documents, chat sessions, messages) but keep the schema:

```bash
uv run python manage.py flush --no-input
```

To also clear the vector store, restart the ChromaDB container:

```bash
docker compose restart chromadb
```

To nuke everything and start completely fresh (removes all Docker volumes):

```bash
docker compose down -v
docker compose up -d
uv run python manage.py migrate
```

## Running Tests

```bash
uv run pytest
```

Tests run without any external services — all AI providers and vector stores are mocked.

To run with verbose output:

```bash
uv run pytest -v
```

To run tests for a specific phase:

```bash
uv run pytest tests/test_phase12_chat_api.py -v
```

## Project Structure

```
projectlens/
├── config/              # Django settings, URLs, Celery config
├── apps/
│   ├── documents/       # Document model, upload API, validation
│   ├── ingestion/       # PDF parsing, chunking, Celery tasks
│   ├── retrieval/       # Query embedding, vector search
│   ├── chat/            # Chat API, RAG service, citations
│   ├── ai/              # AI provider abstractions (embedding + generation)
│   └── ui/              # Web UI — templates, views, static assets
│       ├── templates/ui/    # Django templates (base, chat, documents, settings)
│       ├── static/ui/       # Static files (logo, images)
│       ├── views.py         # Page views + htmx partials
│       └── urls.py          # UI URL routing
├── core/                # Shared services (ChromaDB client)
├── design/              # UI design references (Stitch mockups)
├── tests/               # All test files (366 tests)
├── data/                # Uploaded files (created at runtime)
├── docker-compose.yml   # PostgreSQL, Redis, ChromaDB
├── pyproject.toml       # Dependencies and project config
└── .env                 # Environment variables (not committed)
```

## Things to Know

**Document processing is asynchronous.** When you upload a PDF (via the web UI or the API), the status starts as `PENDING`. The Celery worker handles parsing, chunking, embedding, and vector storage in the background. The Document Library page auto-refreshes status every 5 seconds while documents are being processed.

**The Celery worker must be running.** Without it, uploaded documents will stay in `PENDING` status forever. Make sure to start it in a separate terminal before uploading.

**All answers are grounded in your documents.** The AI model is instructed to answer only from the provided context. If the answer isn't in your documents, it will say so rather than making something up. Citations always come from the retrieval metadata, never invented by the model.

**Conversations have memory.** In the web UI, multi-turn conversations work automatically — the session is maintained client-side. Via the API, send the `session_id` from a previous response to continue the conversation. Omit `session_id` to start fresh. History is capped at the last 10 messages (configurable via `CHAT_HISTORY_LIMIT`). The chat page also includes a sidebar for switching between conversations during the browser session.

**Only PDF files are supported.** The upload endpoint rejects non-PDF files, empty files, corrupt PDFs, and files larger than the configured maximum size (50 MB by default).

**Incremental ingestion.** Re-uploading a document with the same content won't re-embed existing chunks. The system checks ChromaDB for existing chunk IDs and only processes new ones.

**Questions search across all documents.** There is currently no way to scope a question to a specific document — the retrieval searches the entire vector collection.

**No authentication.** The API has no authentication or authorization. Do not expose it to the public internet without adding your own auth layer.

**The `.env` file contains secrets.** Never commit it to version control. Add `.env` to your `.gitignore`.

**AI provider is swappable.** The system uses abstractions for both embedding and generation. The current implementation uses Google Gemini, but providers can be replaced by implementing the `EmbeddingProvider` and `AIProvider` interfaces in `apps/ai/providers/`.

**The web UI has no build step.** The frontend uses Tailwind CSS via play-CDN, htmx, and Alpine.js — all loaded from CDN. No Node.js, npm, or bundler required. This is suitable for development and MVP use; a production deployment should switch to a compiled Tailwind build.
