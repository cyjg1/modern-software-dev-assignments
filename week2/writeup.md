# Week 2 Write-up
Tip: To preview this markdown file
- On Mac, press `Command (⌘) + Shift + V`
- On Windows/Linux, press `Ctrl + Shift + V`

## INSTRUCTIONS

Fill out all of the `TODO`s in this file.

## SUBMISSION DETAILS

Name: cyjg \
SUNet ID: 123456 \
Citations: Ollama structured outputs: https://ollama.com/blog/structured-outputs ; Ollama model library: https://ollama.com/library

This assignment took me about **TODO** hours to do.


## YOUR RESPONSES
For each exercise, please include what prompts you used to generate the answer, in addition to the location of the generated response. Make sure to clearly add comments in your code documenting which parts are generated.

### Exercise 1: Scaffold a New Feature
Prompt:
```
Implement `extract_action_items_llm(text: str) -> list[str]` in `week2/app/services/extract.py` using Ollama `chat()` with structured outputs (JSON schema). The function should:
- Return a list of action item strings extracted from notes
- Return `[]` for empty input
- De-duplicate and trim items
- Fall back to the existing heuristic extractor if Ollama is unavailable or returns invalid output
Use model `llama3.1:8b` by default.
```

Generated Code Snippets:
```
week2/app/services/extract.py:67
```

### Exercise 2: Add Unit Tests
Prompt:
```
Write unit tests for `extract_action_items_llm()` in `week2/tests/test_extract.py`. Cover:
- Parsing a JSON response and de-duplicating items
- Empty input returns an empty list (and does not call Ollama)
- Invalid JSON from Ollama triggers a fallback to the heuristic extractor
Mock/monkeypatch the Ollama `chat()` call so tests do not require Ollama to be running.
```

Generated Code Snippets:
```
week2/tests/test_extract.py:22
week2/tests/test_extract.py:48
week2/tests/test_extract.py:58
```

### Exercise 3: Refactor Existing Code for Clarity
Prompt:
```
Refactor the Week 2 backend for clarity:
- Define explicit Pydantic request/response schemas instead of `Dict[str, Any]`
- Update routers to use the schemas
- Improve app lifecycle by moving DB initialization to a FastAPI lifespan handler
- Make small cleanups in the DB layer and extraction service for readability/typing
Run `ruff` and `pytest` to confirm the app still works.
```

Generated/Modified Code Snippets:
```
week2/app/schemas.py:1
week2/app/routers/action_items.py:28
week2/app/routers/notes.py:20
week2/app/main.py:20
week2/app/db.py:23
week2/app/services/extract.py:32
```


### Exercise 4: Use Agentic Mode to Automate a Small Task
Prompt:
```
Add two small features:
1) Add a new LLM extraction endpoint and update the frontend to include an "Extract LLM" button that calls it.
2) Add an endpoint to list all notes and update the frontend to include a "List Notes" button that fetches and displays them.
Ensure the UI still supports marking action items done.
```

Generated Code Snippets:
```
week2/app/routers/action_items.py:45
week2/app/routers/notes.py:32
week2/frontend/index.html:31
week2/frontend/index.html:98
```


### Exercise 5: Generate a README from the Codebase
Prompt:
```
Analyze the Week 2 codebase and generate a `week2/README.md` that includes:
- Project overview
- How to set up and run the app
- API endpoints and functionality
- Instructions for running the test suite (and optional lint)
```

Generated Code Snippets:
```
week2/README.md:1
```


## SUBMISSION INSTRUCTIONS
1. Hit a `Command (⌘) + F` (or `Ctrl + F`) to find any remaining `TODO`s in this file. If no results are found, congratulations — you've completed all required fields.
2. Make sure you have all changes pushed to your remote repository for grading.
3. Submit via Gradescope.
