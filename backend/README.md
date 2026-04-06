# LaoshiGPT Backend

## Run locally
1) python -m venv .venv
2) source .venv/bin/activate
3) pip install -e .[dev]
4) uvicorn app.main:app --reload

Health check: GET http://localhost:8000/health
