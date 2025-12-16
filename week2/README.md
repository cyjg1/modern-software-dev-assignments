# Week 2 — Action Item Extractor

A minimal FastAPI + SQLite app that converts free-form meeting notes into a checklist of actionable items.

It supports two extraction modes:
- **Heuristic extraction** (fast, no dependencies)
- **LLM extraction via Ollama** (more flexible, requires a local Ollama server)

## Project Layout

- `week2/app/main.py` — FastAPI app + startup lifecycle + serving the HTML UI
- `week2/app/routers/` — API endpoints (`action_items.py`, `notes.py`)
- `week2/app/services/extract.py` — extraction logic (`extract_action_items`, `extract_action_items_llm`)
- `week2/app/db.py` — SQLite helpers (DB file is `week2/data/app.db`)
- `week2/frontend/index.html` — minimal frontend UI
- `week2/tests/` — unit tests

## Setup

Run all commands from the repository root: `modern-software-dev-assignments/`.

### Python + Poetry (recommended)

```bash
conda create -n cs146s python=3.11 -y
conda activate cs146s
python -m pip install -U pip poetry

cd modern-software-dev-assignments
poetry install
```

### Ollama (for LLM extraction)

Install Ollama, then pull a model (the default in code is `llama3.1:8b`):

```bash
ollama pull llama3.1:8b
```

Make sure Ollama is running (for example):

```bash
ollama run llama3.1:8b
```

## Run the App

```bash
cd modern-software-dev-assignments
poetry run uvicorn week2.app.main:app --reload
```

- UI: `http://127.0.0.1:8000/`
- OpenAPI docs: `http://127.0.0.1:8000/docs`

## API Endpoints

### Action items

- `POST /action-items/extract` — heuristic extraction
- `POST /action-items/extract-llm` — LLM extraction (Ollama); falls back to heuristics if Ollama fails
- `GET /action-items?note_id={id}` — list extracted items (optionally filtered by note)
- `POST /action-items/{action_item_id}/done` — mark an item as done/undone

Request body for both extract endpoints:

```json
{
  "text": "notes text",
  "save_note": true
}
```

### Notes

- `POST /notes` — create a note
- `GET /notes` — list all notes
- `GET /notes/{note_id}` — fetch a note by id

## Tests

Run the Week 2 tests:

```bash
cd modern-software-dev-assignments
poetry run pytest -q week2/tests
```

Optional lint:

```bash
poetry run ruff check week2
```

## Resetting Local Data

The SQLite DB is stored at `week2/data/app.db`. To reset local state, stop the server and delete that file.
