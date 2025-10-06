# SL-NASA-KNOWLEDGE-ENGINE

The SL-NASA-KNOWLEDGE-ENGINE Backend powers the AI core of LABI — an experimental Retrieval-Augmented Generation (RAG) search engine built to help researchers explore 608 NASA bioscience publications through natural language.
This repository hosts the FastAPI services, ingestion pipelines, and database connectors that transform unstructured literature into a structured knowledge graph and semantic vector indexes, enabling traceable, evidence-based responses without hallucinations.

## Demo & Project links

- Project demo (presentation): [Canva presentation](https://www.canva.com/design/DAG07k4RDdo/hFb0Pd2zLiUTt9w2yzaWbw/edit?utm_content=DAG07k4RDdo&utm_campaign=designshare&utm_medium=link2&utm_source=sharebutton)
- Project organization: [SL-NASA-Knowledge-Engine GitHub org](https://github.com/SL-NASA-Knowledge-Engine)
- Frontend repository: [SL-NASA-Knowledge-Engine-Frontend](https://github.com/SL-NASA-Knowledge-Engine/sl-nasa-knowledge-engine-frontend)

## What is LABI Search Engine?

LABI (Literature Analysis and Bioscience Intelligence) is a domain-specific AI assistant and knowledge engine for space bioscience research.
It allows researchers to ask natural-language questions and receive grounded, citation-supported answers derived solely from the NASA bioscience corpus.

The backend is responsible for:

- Structuring 608 NASA publications into a Neo4j knowledge graph (entities and relationships).
- Building semantic vector indexes for retrieval-based contextual search.
- Generating RAG-based responses grounded in the retrieved passages.
- Serving API endpoints consumed by the frontend chat interface.

Together, these components enable literature synthesis, comparison of experimental results, and discovery of hidden biological patterns — all in minutes instead of weeks.

## High-level architecture

- Backend (this repo): FastAPI application exposing REST endpoints for RAG queries and data management.

### Data layer

- Neo4j — stores entities, metadata, and relationships.
- Vector database — stores semantic embeddings of corpus passages.

### Pipeline

- Article ingestion and scraping.
- LLM-assisted triplet extraction and relation mapping.
- Neo4j population and indexing.
- Query-time retrieval + synthesis via LLM.

## Key backend features

- `main.py` — FastAPI entry point with automatic OpenAPI documentation (`/docs`).
- `api/router.py` — central routing file defining API endpoints.
- `KnowledgeGraphService` — orchestrates semantic retrieval and evidence-grounded synthesis.
- `Neo4jService` — manages Cypher queries and safe session handling.
- `OpenAIMessageService` — wraps LLM requests (Azure OpenAI compatible).
- `scripts/*.py` — end-to-end ingestion pipeline: scraping, triplet extraction, mapping, and database population.

## Running the backend locally

### Requirements

- Python 3.11+
- Neo4j (local or remote)
- API key for your LLM provider (e.g., Azure OpenAI)
- Optional: Docker for local Neo4j instance

### Quick start (Windows PowerShell)

```powershell
# Clone and enter the repo
git clone https://github.com/SL-NASA-Knowledge-Engine/SL-NASA-Knowledge-Engine-Backend
Set-Location SL-NASA-Knowledge-Engine-Backend

# Create and activate a virtual environment
python -m venv .venv
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process -Force
.\.venv\Scripts\Activate.ps1

# Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# Copy environment example
Copy-Item .env.example .env
notepad .env  # edit credentials and endpoints

# Start the FastAPI server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Once running:

- Base URL: http://127.0.0.1:8000/
- Interactive docs: http://127.0.0.1:8000/docs

## Data

The backend processes and structures 608 NASA bioscience publications.
Generated artifacts are stored in the `resources/` directory:

- `space_biology_scraped.json` — raw article content.
- `raw_triplets.json` — LLM-extracted subject–predicate–object triplets.
- `relation_map.json` — normalized relationship mappings.
- `top_relations.txt` — most frequent relation terms.

## Ingestion pipeline overview

- Scraping: `scripts/1_scraper.py` collects and cleans publication data.
- Triplet extraction: `scripts/2_build_triplets.py` identifies entity–relation–entity structures.
- Relation mapping: `scripts/3_create_mapping.py` standardizes relation labels.
- Graph population: `scripts/4_populate_neo4j.py` inserts nodes and edges into Neo4j.

Each step can be run independently and logs progress to `logs/` for reproducibility.

## API endpoints (examples)

| Endpoint | Method | Description |
|---|---:|---|
| /api/v1/hello | GET | Health/test endpoint |
| /api/v1/query | POST | Main RAG query — returns an answer and supporting citations |
| /api/v1/categories/top/{limit} | GET | Retrieve top categories by publication count |

## Development notes

- Configuration files: core/settings.py and core/logging_config.py.
- Ingestion scripts may call LLM APIs — monitor token usage and rate limits.
- Run pytest to execute unit tests (if available).
- Before committing, ensure .env and generated data files are excluded via .gitignore.

## Security and attribution

LABI is explicitly grounded in the NASA corpus to eliminate hallucinations and ensure scientific integrity.
Each generated answer includes source citations and evidence passages.
When deploying, use environment variables or secret managers to protect credentials.
Never commit `.env` or API keys to version control.

## Contributing

We welcome contributions! Areas of interest include:

- Enhancing triplet extraction and normalization logic.
- Adding streaming responses and improved error handling.
- Expanding the Neo4j schema with richer metadata.
- Strengthening test coverage for the RAG query pipeline.

Please open issues or pull requests at: [SL-NASA-Knowledge-Engine GitHub org](https://github.com/SL-NASA-Knowledge-Engine)

## Credits

This backend was developed using a combination of AI tools and human expertise:

- NotebookLM and Perplexity — literature analysis and theme extraction.
- GitHub Copilot — backend code suggestions and API implementation.
- Claude and ChatGPT — design and documentation prototyping.

Together, they supported the creation of LABI, a system that transforms NASA’s fragmented bioscience literature into a coherent, queryable intelligence engine for the future of space exploration.

