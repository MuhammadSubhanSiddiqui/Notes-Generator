"""
Central config for the notes-generator pipeline.
Edit TOPICS to add/remove skills. Runs against your local
OpenAI-compatible freellmapi server.
"""

import os

# ---- LLM endpoint (your local freellmapi, OpenAI-compatible) ----
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:3001/v1")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "not-needed-for-local")  # freellmapi usually ignores this
LLM_MODEL = os.environ.get("LLM_MODEL")  # change to whatever model your local proxy routes to

# Retry / rate-limit behavior for the loop-engineering calls
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 5
REQUEST_TIMEOUT = 180  # seconds — theory/ASCII generations can run long

# ---- Web search (DuckDuckGo, no API key — see search_client.py) ----
# Adds a light "current context" pass before Stage 1, so notes aren't purely
# frozen to the local model's training data. Safe to disable if you don't
# want the extra network calls / `ddgs` dependency.
ENABLE_SEARCH_CONTEXT = os.environ.get("ENABLE_SEARCH_CONTEXT", "true").lower() == "true"
SEARCH_RESULTS_PER_QUERY = 4
SEARCH_MAX_RETRIES = 2
SEARCH_RETRY_BACKOFF_SECONDS = 3

# ---- Portfolio relevance ----
# muhammadsubhansiddiqui.netlify.app is a React SPA — its project list is
# client-side rendered, so it can't be scraped with a plain fetch. Until the
# Phase 2 Playwright/Selenium scraper exists, maintain this list by hand.
# Each entry: {"name": ..., "description": ..., "stack": [...]}
PORTFOLIO_PROJECTS = [
    # {
    #     "name": "Example Project",
    #     "description": "One or two lines on what it does.",
    #     "stack": ["React", "Node.js", "MongoDB"],
    # },
]

# ---- Topics: seed manually for now; portfolio auto-extract is Phase 2 ----
TOPICS = [
    "React.js",
    # "Node.js",
    # "Docker",
    # "Python / ML Basics",
    # "MongoDB",
    # "LLM / RAG Systems",
]

# ---- Output paths ----
OUTPUT_MD_DIR = "output/md"
OUTPUT_PDF_DIR = "output/pdf"
