"""
Thin wrapper around the local OpenAI-compatible freellmapi.
Handles retries with backoff — local proxies can be flaky under load,
especially when chaining multiple calls per topic.
"""

import time
import sys
from openai import OpenAI, APIConnectionError, APITimeoutError, APIStatusError

from config import (
    LLM_BASE_URL,
    LLM_API_KEY,
    LLM_MODEL,
    LLM_MODEL_CANDIDATES,
    MAX_RETRIES,
    RETRY_BACKOFF_SECONDS,
    REQUEST_TIMEOUT,
)

_client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY, timeout=REQUEST_TIMEOUT)


def call_llm(prompt: str, stage_name: str = "") -> str:
    """
    Sends a single prompt to the local LLM and returns the text response.
    Retries on connection/timeout errors with backoff.
    """
    last_error = None
    model_candidates = [model for model in LLM_MODEL_CANDIDATES if model]
    if LLM_MODEL and LLM_MODEL not in model_candidates:
        model_candidates.insert(0, LLM_MODEL)

    for model in model_candidates:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = _client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.4,
                )
                content = response.choices[0].message.content
                if not content or not content.strip():
                    raise ValueError("Empty response from model")
                return content.strip()

            except (APIConnectionError, APITimeoutError) as e:
                last_error = e
                print(f"  [{stage_name}] model {model} attempt {attempt}/{MAX_RETRIES} failed: {e}. "
                      f"Is your local server running at {LLM_BASE_URL}?", file=sys.stderr)
            except APIStatusError as e:
                last_error = e
                print(f"  [{stage_name}] model {model} attempt {attempt}/{MAX_RETRIES} — server returned "
                      f"status {e.status_code}: {e.message}", file=sys.stderr)
                if e.status_code == 401:
                    break
            except Exception as e:
                last_error = e
                print(f"  [{stage_name}] model {model} attempt {attempt}/{MAX_RETRIES} unexpected error: {e}", file=sys.stderr)

            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    raise RuntimeError(f"LLM call failed for stage '{stage_name}' after {MAX_RETRIES} attempts: {last_error}")
