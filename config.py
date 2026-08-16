"""
Central config for the notes-generator pipeline.
Edit TOPICS to add/remove skills. Runs against your local
OpenAI-compatible freellmapi server.
"""

import json
import os
from pathlib import Path
from urllib.request import urlopen


def _load_dotenv_file() -> None:
    env_path = Path(__file__).with_name(".env")
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _normalize_api_key(value: str | None) -> str:
    if not value:
        return ""
    lowered = value.strip().lower()
    if lowered in {"replace-me", "not-needed-for-local", "none", "null"}:
        return ""
    return value.strip()


def _discover_models(base_url: str) -> list[str]:
    try:
        with urlopen(f"{base_url.rstrip('/')}/models", timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        models = payload.get("data", []) if isinstance(payload, dict) else []
        model_ids = []
        for model in models:
            if isinstance(model, dict):
                model_id = model.get("id") or model.get("name")
                if model_id:
                    model_ids.append(str(model_id))
            elif isinstance(model, str):
                model_ids.append(model)
        return model_ids
    except Exception:
        return []


_load_dotenv_file()

# ---- LLM endpoint (your local freellmapi, OpenAI-compatible) ----
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:3001/v1")
LLM_API_KEY = (
    _normalize_api_key(os.environ.get("LLM_API_KEY"))
    or _normalize_api_key(os.environ.get("OPENAI_API_KEY"))
    or "sk-local"
)
_discovered_models = _discover_models(LLM_BASE_URL)
LLM_MODEL = os.environ.get("LLM_MODEL") or (_discovered_models[0] if _discovered_models else "auto")
_env_model_candidates = [
    item.strip()
    for item in os.environ.get("LLM_MODEL_CANDIDATES", "").split(",")
    if item.strip()
]
LLM_MODEL_CANDIDATES = _env_model_candidates[:] or ["auto"]
if LLM_MODEL:
    LLM_MODEL_CANDIDATES.insert(0, LLM_MODEL)
for _model in _discovered_models:
    if _model and _model not in LLM_MODEL_CANDIDATES:
        LLM_MODEL_CANDIDATES.append(_model)
LLM_MODEL_CANDIDATES = list(dict.fromkeys(LLM_MODEL_CANDIDATES))

# Retry / rate-limit behavior for the loop-engineering calls
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 5
REQUEST_TIMEOUT = 400  # seconds — theory/ASCII generations can run long

# ---- Web search (DuckDuckGo, no API key — see search_client.py) ----
# Adds a light "current context" pass before Stage 1, so notes aren't purely
# frozen to the local model's training data. Safe to disable if you don't
# want the extra network calls / `ddgs` dependency.
ENABLE_SEARCH_CONTEXT = os.environ.get("ENABLE_SEARCH_CONTEXT", "true").lower() == "true"
SEARCH_RESULTS_PER_QUERY = 4
SEARCH_MAX_RETRIES = 2
SEARCH_RETRY_BACKOFF_SECONDS = 3

# ---- Portfolio relevance (fallback only) ----
# portfolio_scraper.py (Playwright) is the primary source of truth and
# writes to PORTFOLIO_DATA_PATH — this list is only used if that file is
# missing or empty. Each entry: {"name": ..., "description": ..., "stack": [...]}
PORTFOLIO_PROJECTS = [
    # {
    #     "name": "Example Project",
    #     "description": "One or two lines on what it does.",
    #     "stack": ["React", "Node.js", "MongoDB"],
    # },
]

# ---- Topics: seed manually for now; portfolio auto-extract is Phase 2 ----
TOPICS = [
    # "React.js",
    # "Node.js",
    # "Docker",
    # "Python / ML Basics",
    # "MongoDB",
    # "LLM / RAG Systems",
]

# ---- Output paths ----
# Anchored to this file's directory rather than left relative, so every
# entry point (generate_notes.py, run_all.py, convert_to_pdf.py, or a
# script imported from a different cwd) resolves to the same files instead
# of silently writing/reading a fresh copy in whatever directory the
# process happened to be launched from.
_BASE_DIR = Path(__file__).resolve().parent
PORTFOLIO_DATA_PATH = str(_BASE_DIR / "portfolio_data.json")
OUTPUT_MD_DIR = str(_BASE_DIR / "output" / "md")
OUTPUT_PDF_DIR = str(_BASE_DIR / "output" / "pdf")

TOPIC_THEMES = {
    "javascript": {"accent": "#F7DF1E", "text_on_accent": "#1a1a1a", "label": "JavaScript"},
    "typescript": {"accent": "#3178C6", "text_on_accent": "#ffffff", "label": "TypeScript"},
    "python": {"accent": "#3776AB", "text_on_accent": "#ffffff", "label": "Python"},
    "react": {"accent": "#61DAFB", "text_on_accent": "#1a1a1a", "label": "React"},
    "next": {"accent": "#0A0A0A", "text_on_accent": "#ffffff", "label": "Next.js"},
    "node": {"accent": "#339933", "text_on_accent": "#ffffff", "label": "Node.js"},
    "sql": {"accent": "#3E6E93", "text_on_accent": "#ffffff", "label": "SQL"},
    "docker": {"accent": "#2496ED", "text_on_accent": "#ffffff", "label": "Docker"},
    "pytorch": {"accent": "#EE4C2C", "text_on_accent": "#ffffff", "label": "PyTorch"},
}
DEFAULT_THEME = {"accent": "#0A2540", "text_on_accent": "#ffffff", "label": None}


def get_theme_for_topic(topic: str) -> dict:
    topic_lower = topic.lower()
    for keyword, theme in TOPIC_THEMES.items():
        if keyword in topic_lower:
            return theme
    return DEFAULT_THEME
