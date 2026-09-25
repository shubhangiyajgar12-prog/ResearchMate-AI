import json
import os
import time
from typing import Any

from dotenv import load_dotenv

load_dotenv()

_client = None


def _resolve_model(model: str | None = None) -> str:
    """Return a valid Gemini model id and prevent stale 2.5 Flash references."""
    raw = (model or os.getenv("GEMINI_MODEL") or "gemini-3.8-flash").strip()
    if raw.startswith("models/"):
        raw = raw.split("/", 1)[1]

    stale = {
        "gemini-2.5-flash",
        "gemini-2.5-flash-latest",
    }
    if raw in stale or not raw:
        return "gemini-3.8-flash"

    return raw


def _get_client():
    global _client

    if _client is not None:
        return _client

    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return None

    from google import genai

    _client = genai.Client(api_key=key)
    return _client


def _retryable(message: str) -> bool:
    upper = message.upper()
    return any(
        token in upper
        for token in (
            "429",
            "503",
            "UNAVAILABLE",
            "TIMEOUT",
            "RESOURCE_EXHAUSTED",
        )
    )


def generate_text(
    prompt: str,
    model: str | None = None,
    temperature: float = 0.2,
):
    client = _get_client()

    if client is None:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. Configure it in backend/.env."
        )

    model_name = _resolve_model(model)
    last: Exception | None = None

    from google.genai import types

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                ),
            )

            text = getattr(response, "text", None)
            if not text:
                raise RuntimeError("Gemini returned an empty response")

            return text

        except Exception as exc:
            last = exc
            if attempt < 2 and _retryable(str(exc)):
                time.sleep(2 ** attempt)
                continue
            break

    raise RuntimeError(
        f"LLM request failed using model '{model_name}': {last}"
    )


def generate_json(prompt: str, model: str | None = None):
    raw = generate_text(
        prompt + "\nReturn ONLY valid JSON.",
        model=model,
    ).strip()

    if raw.startswith("```json"):
        raw = raw[7:]
    elif raw.startswith("```"):
        raw = raw[3:]

    if raw.endswith("```"):
        raw = raw[:-3]

    return json.loads(raw.strip())


def generate_structured_response(
    prompt: str,
    response_schema: Any,
    model: str | None = None,
    temperature: float = 0.2,
):
    """Generate JSON from Gemini and validate it with the project's Pydantic model."""
    client = _get_client()

    if client is None:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. Configure it in backend/.env."
        )

    model_name = _resolve_model(model)
    last: Exception | None = None

    from google.genai import types

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    response_mime_type="application/json",
                    response_schema=response_schema,
                ),
            )

            text = getattr(response, "text", None)
            if not text:
                raise RuntimeError("Gemini returned an empty structured response")

            data = json.loads(text)
            return response_schema.model_validate(data)

        except Exception as exc:
            last = exc
            if attempt < 2 and _retryable(str(exc)):
                time.sleep(2 ** attempt)
                continue
            break

    raise RuntimeError(
        f"Structured LLM request failed using model '{model_name}': {last}"
    )
