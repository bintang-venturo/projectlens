# ProjectLens — Implementation PRD

## 1. Project Overview

**Project Name:** ProjectLens

**Goal:** Build a Django-based RAG application that allows users to upload PDF documents, process and index their contents into ChromaDB, and answer questions grounded in those documents with source citations (document name and page number).

### Technical decisions

- Python 3.12+
- Django + Django REST Framework
- PostgreSQL
- Redis + Celery
- ChromaDB
- External AI API for generation
- No Ollama
- No local LLM
- AI providers must be replaceable through abstractions
- PDF is the first supported document format
- pytest for automated testing

---

## 2. Architecture

```text
                    ┌─────────────────┐
                    │     Client      │
                    └────────┬────────┘
                             │ HTTP
                             ▼
                  ┌──────────────────────┐
                  │ Django REST API      │
                  └──────────┬───────────┘
                             │
             ┌───────────────┼────────────────┐
             ▼               ▼                ▼
       Document API      Search API       Chat API
             │               │                │
             ▼               ▼                ▼
       Document Service Retrieval Service  RAG Service
             │               │                │
             ▼               │                ▼
        Celery Task           │          AI Provider
             │               │          (External API)
             ▼               ▼
       PDF Parser        Chroma Service
             │               │
             ▼               ▼
         Chunker          ChromaDB
             │
             ▼
        Embedding Service
             │
             ▼
       External Embedding API

             ┌─────────────────┐
             │   PostgreSQL    │
             └─────────────────┘

             ┌─────────────────┐
             │      Redis      │
             └─────────────────┘
```

### Architectural principles

1. Django handles HTTP/API concerns.
2. Celery handles asynchronous ingestion.
3. PostgreSQL is the source of truth for application metadata.
4. ChromaDB is used only as the vector store.
5. AI providers must not be called directly from Django views.
6. PDF parsing, chunking, embedding, retrieval, and RAG are separate services.
7. AI providers use interfaces/abstractions.
8. Configuration comes from environment variables.
9. API keys and secrets must never be hardcoded.
10. Business logic must stay outside views and serializers.
11. Every important service must be testable.

---

# 3. Django Apps

Create the following structure:

```text
projectlens/
├── config/
├── apps/
│   ├── documents/
│   ├── ingestion/
│   ├── retrieval/
│   ├── chat/
│   └── ai/
├── core/
├── scripts/
├── tests/
├── data/
├── manage.py
├── docker-compose.yml
├── pyproject.toml
└── .env
```

### App responsibilities

#### `documents`
- Document model
- Document metadata
- Upload
- Document listing
- Document detail
- Document status

#### `ingestion`
- PDF parsing
- Page extraction
- Chunking
- Embedding
- Vector synchronization
- Celery ingestion tasks

#### `retrieval`
- Query embedding
- Vector search
- Similarity filtering
- Retrieval result normalization

#### `chat`
- Chat endpoint
- RAG orchestration
- Response generation
- Citation formatting

#### `ai`
- AI provider abstraction
- Generation provider implementation
- Embedding provider abstraction

---

# 4. Database Models

Use PostgreSQL.

## Document

```text
id
name
file
file_size
page_count
status
error_message
created_at
updated_at
```

Status values:

```text
PENDING
PROCESSING
COMPLETED
FAILED
```

## DocumentPage

```text
id
document
page_number
content
created_at
```

Constraint:

```text
unique(document, page_number)
```

## DocumentChunk

```text
id
document
page
chunk_index
chunk_id
content
metadata
created_at
```

Constraints:

```text
unique(document, page, chunk_index)
unique(chunk_id)
```

Deterministic chunk ID:

```text
{source_path}:{page_number}:{chunk_index}
```

`chunk_index` resets to `0` for each page.

## ChatSession

```text
id
created_at
updated_at
```

## ChatMessage

```text
id
session
role
content
created_at
```

Roles:

```text
USER
ASSISTANT
```

---

# 5. Document Upload

## Objective

Allow users to upload PDF files through a REST API.

### Endpoint

```http
POST /api/documents/
```

Request:

```text
multipart/form-data
file=<pdf>
```

### Validation

Reject:

- Non-PDF files
- Empty files
- Files above configured maximum size
- Corrupt/unreadable PDFs

### Success response

```json
{
  "id": "uuid",
  "name": "monopoly.pdf",
  "status": "PENDING"
}
```

### Required flow

```text
POST /api/documents/
        │
        ▼
Create Document
        │
        ▼
status = PENDING
        │
        ▼
Dispatch Celery task
        │
        ▼
Return HTTP 201
```

The API must not wait for the entire ingestion process.

---

# 6. PDF Parser

## Objective

Convert a PDF into page-level document objects.

Each parsed page must preserve:

```text
source
page_number
content
```

Example:

```python
{
    "content": "...",
    "metadata": {
        "source": "monopoly.pdf",
        "page": 4
    }
}
```

### Requirements

- Support PDF.
- Parse each page separately.
- Preserve original PDF page number.
- Preserve source filename/path.
- Handle empty pages safely.
- Ingestion errors must set Document status to `FAILED`.

### Extensibility

Create a parser interface:

```python
class DocumentParser(ABC):

    @abstractmethod
    def parse(self, file_path):
        ...
```

First implementation:

```text
PDFParser
```

Future implementations may include Markdown, CSV, HTML, and DOCX.

---

# 7. Chunking

## Objective

Split page content into semantic chunks optimized for vector retrieval.

Use:

```text
RecursiveCharacterTextSplitter
```

### Configuration

Do not hardcode chunk settings.

Use:

```env
CHUNK_SIZE=1000
CHUNK_OVERLAP=150
```

### Chunk metadata

```json
{
  "source": "monopoly.pdf",
  "page": 4,
  "chunk_index": 0
}
```

### Deterministic ID

```text
{source}:{page}:{chunk_index}
```

Example:

```text
monopoly.pdf:4:0
monopoly.pdf:4:1
monopoly.pdf:5:0
```

---

# 8. Embedding

## Objective

Convert text chunks into vector embeddings using an external embedding API/provider.

### Architecture

```text
EmbeddingService
       │
       ▼
EmbeddingProvider
       │
       ▼
External Embedding API
```

Interface:

```python
class EmbeddingProvider(ABC):

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        ...
```

The same embedding provider/model must be used for document chunks and user queries.

### Configuration

```env
EMBEDDING_PROVIDER=...
EMBEDDING_MODEL=...
EMBEDDING_API_KEY=...
```

---

# 9. Vector Storage

## Objective

Store embeddings and metadata in ChromaDB.

Collection:

```text
projectlens_documents
```

Each record must contain:

```text
id
embedding
metadata
```

Metadata example:

```json
{
  "document_id": "uuid",
  "source": "monopoly.pdf",
  "page": 4,
  "chunk_index": 0
}
```

## Incremental synchronization

Before embedding:

```text
Generate deterministic IDs
        │
        ▼
Get existing IDs from ChromaDB
        │
        ▼
Compare IDs
        │
        ▼
Only process new chunks
        │
        ▼
Generate embeddings
        │
        ▼
Upsert into ChromaDB
```

The system must skip existing chunks to avoid duplicate vectors and unnecessary embedding API calls.

### MVP limitation

Do not implement content-change detection yet. If source path, page number, and chunk index remain identical, the existing chunk may be considered unchanged.

---

# 10. Retrieval

## Objective

Find the most relevant chunks for a user's natural-language question.

### Flow

```text
User Question
      │
      ▼
Embed Query
      │
      ▼
Query ChromaDB
      │
      ▼
Top K Results
      │
      ▼
Normalize Results
```

Default:

```env
RETRIEVAL_K=5
```

### Retrieval result

```python
[
    {
        "content": "...",
        "source": "monopoly.pdf",
        "page": 4,
        "score": 0.91
    }
]
```

Retrieval service must not generate the final natural-language answer.

---

# 11. RAG

## Objective

Generate an answer grounded only in retrieved document context.

### Flow

```text
Question
   │
   ▼
Retrieval
   │
   ▼
Top K Chunks
   │
   ▼
Build Context
   │
   ▼
Prompt
   │
   ▼
AI Provider
   │
   ▼
Answer
```

### Prompt

The prompt must contain:

```text
context
question
```

Base instruction:

```text
You are a document question-answering assistant.

Answer the user's question using only the provided context.

If the context does not contain enough information to answer the question,
say that the information is not available in the provided documents.

Do not invent facts.

Context:
{context}

Question:
{question}
```

### AI provider

Application code must call an abstraction such as:

```python
AIProvider.generate(...)
```

Do not instantiate a specific vendor client directly inside the RAG service.

No Ollama or local LLM is allowed.

---

# 12. Citation

## Objective

Every generated answer must include the sources used to ground the answer.

Example:

```text
Answer:
Each player starts with $1,500.

Sources:
- Monopoly Rules — Page 4
```

### API structure

```json
{
  "answer": "Each player starts with $1,500.",
  "citations": [
    {
      "source": "monopoly.pdf",
      "page": 4
    }
  ]
}
```

### Rules

1. Citation must come from retrieval metadata.
2. The LLM must not invent page numbers.
3. Duplicate source/page combinations must be removed.
4. Original page numbers must be preserved.
5. Citations must be structured JSON data.

---

# 13. Chat API

## Objective

Expose question answering through REST API.

### Endpoint

```http
POST /api/chat/
```

Request:

```json
{
  "question": "How much money does each player start with?"
}
```

Response:

```json
{
  "answer": "Each player starts with $1,500.",
  "citations": [
    {
      "source": "monopoly.pdf",
      "page": 4
    }
  ]
}
```

### Flow

```text
POST /api/chat/
      │
      ▼
Validate Request
      │
      ▼
RetrievalService
      │
      ▼
Relevant Chunks
      │
      ▼
RAGService
      │
      ▼
AIProvider
      │
      ▼
Build Citations
      │
      ▼
JSON Response
```

---

# 14. Celery Ingestion Pipeline

Document ingestion must be asynchronous.

```text
Upload
  │
  ▼
Document.status = PENDING
  │
  ▼
Celery
  │
  ▼
PROCESSING
  │
  ├── PDF Parse
  ├── Save Pages
  ├── Chunk
  ├── Generate IDs
  ├── Check ChromaDB
  ├── Embed New Chunks
  ├── Store ChromaDB
  └── COMPLETED
```

On failure:

```text
Document.status = FAILED
Document.error_message = ...
```

---

# 15. API Endpoints

Minimum endpoints:

```text
POST   /api/documents/
GET    /api/documents/
GET    /api/documents/{id}/
POST   /api/chat/
```

All endpoints must:

- Return JSON.
- Validate input.
- Use appropriate HTTP status codes.
- Return consistent error structures.

---

# 16. Testing Requirements

Use pytest.

## Unit tests

```text
PDF parser
Chunker
Deterministic ID generation
Embedding service
Chroma service
Retrieval service
Citation builder
RAG service
```

## Integration tests

```text
Document upload
Ingestion pipeline
Vector synchronization
Chat API
```

Tests must not require real paid API calls.

External providers should be mocked in unit/integration tests where appropriate.

---

# 17. Definition of Done

## Infrastructure

- [ ] Django runs.
- [ ] PostgreSQL connection works.
- [ ] Redis connection works.
- [ ] ChromaDB connection works.
- [ ] Celery worker runs.
- [ ] Environment configuration works.

## Documents

- [ ] PDF can be uploaded.
- [ ] Document is stored in PostgreSQL.
- [ ] Status transitions PENDING → PROCESSING → COMPLETED.
- [ ] PDF is parsed page by page.
- [ ] Page numbers are preserved.

## Chunking

- [ ] RecursiveCharacterTextSplitter is used.
- [ ] Chunk size is configurable.
- [ ] Chunk overlap is configurable.
- [ ] Source/page metadata is preserved.
- [ ] Deterministic chunk IDs work.

## Vector

- [ ] Embedding provider abstraction exists.
- [ ] Embeddings can be generated.
- [ ] Chunks are stored in ChromaDB.
- [ ] Existing chunks are not embedded again.
- [ ] Incremental ingestion works.

## Retrieval

- [ ] Query embedding works.
- [ ] ChromaDB returns top-K results.
- [ ] Default K = 5.
- [ ] Retrieval results contain source/page/score.

## RAG

- [ ] Context is constructed.
- [ ] Prompt contains context and question.
- [ ] External AI API is called through the provider abstraction.
- [ ] Model is instructed not to invent information outside context.

## Citation

- [ ] Citation comes from retrieval metadata.
- [ ] Source filename is available.
- [ ] Page number is available.
- [ ] Duplicate citations are removed.

## API

- [ ] POST /api/documents/
- [ ] GET /api/documents/
- [ ] GET /api/documents/{id}/
- [ ] POST /api/chat/
- [ ] Consistent JSON responses.
- [ ] Consistent error responses.

---

# 18. Implementation Order

Implement strictly in this order:

```text
PHASE 01 — Architecture
       ↓
PHASE 02 — Django Apps
       ↓
PHASE 03 — Database Models
       ↓
PHASE 04 — Document Upload
       ↓
PHASE 05 — PDF Parser
       ↓
PHASE 06 — Chunking
       ↓
PHASE 07 — Embedding
       ↓
PHASE 08 — Vector Storage
       ↓
PHASE 09 — Retrieval
       ↓
PHASE 10 — RAG
       ↓
PHASE 11 — Citation
       ↓
PHASE 12 — Chat API
```

Do not skip phases.

---

# 19. Claude Code Execution Rules

Claude Code must follow these rules:

1. Do not implement the entire system in one step.
2. Implement one phase at a time.
3. Before changing code, inspect the existing project structure.
4. Do not overwrite working configuration unless necessary.
5. Reuse the existing Docker infrastructure.
6. Do not introduce Ollama.
7. Do not introduce a local LLM.
8. AI generation must use an external API provider.
9. Keep AI provider implementations behind abstractions.
10. Never hardcode API keys or secrets.
11. Use Celery for document ingestion.
12. PostgreSQL is the source of truth for application metadata.
13. ChromaDB is the vector database.
14. Keep business logic outside Django views and serializers.
15. Write tests for every service introduced.
16. Run relevant tests after every phase.
17. Do not proceed if the current phase is broken.
18. Do not make architectural changes that contradict this PRD without explaining the reason first.

### Required report after every phase

Claude Code must report:

```text
Phase:
Status:

Files changed:
- ...

Implementation:
- ...

Tests executed:
- ...

Test result:
PASS / FAIL

Known limitations:
- ...

Next phase:
...
```

---

# 20. First Claude Code Prompt

After placing this file in the project root, start Claude Code with:

> Read `PROJECTLENS_IMPLEMENTATION_PRD.md`.
>
> Do not implement anything yet.
>
> First inspect the existing ProjectLens repository and compare its current state against the PRD.
>
> Report:
> 1. Current architecture
> 2. Existing files
> 3. Existing dependencies
> 4. Existing infrastructure
> 5. What is already implemented
> 6. What is missing
> 7. Any conflicts between the current code and the PRD
> 8. Proposed implementation plan for PHASE 01
>
> Do not modify any files until I explicitly approve the plan.

