import json
import os
import time
from typing import Any

from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Global Gemini client
# ---------------------------------------------------------------------------

_client = None


# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------

DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"


def _normalise_model_name(name: str | None) -> str:
    """
    Normalize Gemini model names.

    Examples:
        models/gemini-3.6-flash -> gemini-3.6-flash
        gemini-3.6-flash        -> gemini-3.6-flash
    """
    value = (name or "").strip()

    if value.startswith("models/"):
        value = value.split("/", 1)[1]

    return value


def _configured_model(model: str | None = None) -> str:
    """
    Resolve the model deterministically.

    Priority:
        1. Explicit model argument
        2. GEMINI_MODEL from .env
        3. gemini-3.6-flash

    We intentionally do NOT auto-discover another model here.
    Automatic fallback can unexpectedly select another model and create
    quota/configuration problems.
    """
    selected = _normalise_model_name(
        model or os.getenv("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL
    )

    if not selected:
        return DEFAULT_GEMINI_MODEL

    return selected


# ---------------------------------------------------------------------------
# Gemini client
# ---------------------------------------------------------------------------

def _get_client():
    """
    Create and cache the Gemini client.
    """
    global _client

    if _client is not None:
        return _client

    key = os.getenv("GEMINI_API_KEY", "").strip()

    if not key:
        return None

    from google import genai

    _client = genai.Client(api_key=key)

    return _client


# ---------------------------------------------------------------------------
# Error helpers
# ---------------------------------------------------------------------------

def _is_quota_exhausted(message: str) -> bool:
    """
    Detect quota exhaustion errors where retrying immediately is not useful.

    Examples:
        GenerateRequestsPerDayPerProjectPerModel-FreeTier
        quota_exceeded
        daily quota
        You exceeded your current quota
    """
    upper = str(message).upper()

    quota_markers = (
        "GENERATEREQUESTSPERDAY",
        "GENERATE_CONTENT_FREE_TIER_REQUESTS",
        "GENERATECONTENTFREETIERREQUESTS",
        "QUOTA_EXCEEDED",
        "DAILY QUOTA",
        "PERDAY",
        "YOU EXCEEDED YOUR CURRENT QUOTA",
        "QUOTA HAS BEEN EXCEEDED",
    )

    return any(marker in upper for marker in quota_markers)


def _is_retryable(message: str) -> bool:
    """
    Detect temporary/transient API failures.

    Daily quota exhaustion is intentionally excluded because retrying
    does not restore a consumed daily quota.
    """
    if _is_quota_exhausted(message):
        return False

    upper = str(message).upper()

    transient_markers = (
        "500",
        "502",
        "503",
        "504",
        "UNAVAILABLE",
        "TIMEOUT",
        "DEADLINE",
        "INTERNAL",
        "TOO_MANY_REQUESTS",
    )

    # Generic 429 can be a temporary RPM/TPM rate-limit.
    # Daily quota 429 has already been excluded above.
    if "429" in upper:
        return True

    return any(marker in upper for marker in transient_markers)


def _is_model_not_found(message: str) -> bool:
    """
    Detect model-not-found / unavailable model errors.
    """
    upper = str(message).upper()

    return (
        "404" in upper
        or "NOT_FOUND" in upper
        or "MODEL_NOT_FOUND" in upper
    )


def _format_api_error(message: str, model_name: str) -> str:
    """
    Convert low-level Gemini errors into a useful backend error.
    """
    if _is_quota_exhausted(message):
        return (
            f"Gemini daily quota is exhausted for model '{model_name}'. "
            "No additional retry was attempted. "
            "Wait until the Gemini quota resets or use a project/API key "
            "with available quota."
        )

    if _is_model_not_found(message):
        return (
            f"Gemini model '{model_name}' is unavailable for the configured "
            "API key. Check GEMINI_MODEL in backend/.env."
        )

    return (
        f"Gemini request failed using model '{model_name}': {message}"
    )


# ---------------------------------------------------------------------------
# Single generation request
# ---------------------------------------------------------------------------

def _generate_once(
    client,
    model_name: str,
    prompt: str,
    temperature: float,
):
    """
    Perform one Gemini generateContent request.
    """
    from google.genai import types

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=temperature,
        ),
    )

    text = getattr(response, "text", None)

    if not text or not str(text).strip():
        raise RuntimeError("Gemini returned an empty response.")

    return str(text).strip()


# ---------------------------------------------------------------------------
# Plain text generation
# ---------------------------------------------------------------------------

def generate_text(
    prompt: str,
    model: str | None = None,
    temperature: float = 0.2,
):
    """
    Generate plain text using Gemini.

    Model resolution:
        explicit model
        -> GEMINI_MODEL
        -> gemini-3.6-flash

    Retry behaviour:
        - Temporary 429/RPM/TPM/5xx errors: retry with exponential backoff.
        - Daily quota exhaustion: NO retry.
        - Model not found: NO automatic model switching.
    """
    client = _get_client()

    if client is None:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. "
            "Configure it in backend/.env."
        )

    model_name = _configured_model(model)

    # Keep temperature in a valid range.
    try:
        temperature = float(temperature)
    except (TypeError, ValueError):
        temperature = 0.2

    temperature = max(0.0, min(1.0, temperature))

    last_error: Exception | None = None

    # Maximum of 3 total attempts for transient failures.
    for attempt in range(3):
        try:
            return _generate_once(
                client=client,
                model_name=model_name,
                prompt=prompt,
                temperature=temperature,
            )

        except Exception as exc:
            last_error = exc
            message = str(exc)

            # ---------------------------------------------------------------
            # Daily quota exhausted
            # ---------------------------------------------------------------
            if _is_quota_exhausted(message):
                raise RuntimeError(
                    _format_api_error(message, model_name)
                ) from exc

            # ---------------------------------------------------------------
            # Model unavailable
            # ---------------------------------------------------------------
            if _is_model_not_found(message):
                raise RuntimeError(
                    _format_api_error(message, model_name)
                ) from exc

            # ---------------------------------------------------------------
            # Temporary/transient failure
            # ---------------------------------------------------------------
            if attempt < 2 and _is_retryable(message):
                delay = 2 ** attempt
                time.sleep(delay)
                continue

            break

    final_message = str(last_error) if last_error else "Unknown Gemini error."

    raise RuntimeError(
        _format_api_error(final_message, model_name)
    ) from last_error


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def _strip_json_fences(raw: str) -> str:
    """
    Remove Markdown JSON code fences from Gemini output.

    Handles:
        ```json
        {...}
        ```

        ```
        {...}
        ```
    """
    text = (raw or "").strip()

    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    return text.strip()


def generate_json(
    prompt: str,
    model: str | None = None,
):
    """
    Generate JSON using the normal text generation path.

    Gemini is explicitly instructed to return JSON only.
    """
    raw = generate_text(
        prompt + "\n\nReturn ONLY valid JSON. Do not add Markdown.",
        model=model,
        temperature=0.2,
    )

    cleaned = _strip_json_fences(raw)

    try:
        return json.loads(cleaned)

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Gemini returned invalid JSON: "
            f"{exc}. Raw response was: {cleaned[:1000]}"
        ) from exc


# ---------------------------------------------------------------------------
# Structured response generation
# ---------------------------------------------------------------------------

def generate_structured_response(
    prompt: str,
    response_schema: Any,
    model: str | None = None,
    temperature: float = 0.2,
):
    """
    Generate a structured JSON response and validate it using the
    project's Pydantic response model.

    Example:
        result = generate_structured_response(
            prompt,
            MyResponseSchema,
        )
    """
    client = _get_client()

    if client is None:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. "
            "Configure it in backend/.env."
        )

    model_name = _configured_model(model)

    try:
        temperature = float(temperature)
    except (TypeError, ValueError):
        temperature = 0.2

    temperature = max(0.0, min(1.0, temperature))

    last_error: Exception | None = None

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

            if not text or not str(text).strip():
                raise RuntimeError(
                    "Gemini returned an empty structured response."
                )

            cleaned = _strip_json_fences(str(text))

            try:
                data = json.loads(cleaned)

            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    "Gemini returned invalid structured JSON: "
                    f"{exc}. Raw response was: {cleaned[:1500]}"
                ) from exc

            # Pydantic v2
            if hasattr(response_schema, "model_validate"):
                return response_schema.model_validate(data)

            # Pydantic v1 compatibility
            if hasattr(response_schema, "parse_obj"):
                return response_schema.parse_obj(data)

            # Fallback for schema-like callers
            return data

        except Exception as exc:
            last_error = exc
            message = str(exc)

            # ---------------------------------------------------------------
            # Daily quota exhausted -> never retry
            # ---------------------------------------------------------------
            if _is_quota_exhausted(message):
                raise RuntimeError(
                    "Structured LLM request failed: "
                    + _format_api_error(message, model_name)
                ) from exc

            # ---------------------------------------------------------------
            # Model unavailable -> don't silently switch models
            # ---------------------------------------------------------------
            if _is_model_not_found(message):
                raise RuntimeError(
                    "Structured LLM request failed: "
                    + _format_api_error(message, model_name)
                ) from exc

            # ---------------------------------------------------------------
            # Temporary/transient error -> retry
            # ---------------------------------------------------------------
            if attempt < 2 and _is_retryable(message):
                delay = 2 ** attempt
                time.sleep(delay)
                continue

            break

    final_message = (
        str(last_error)
        if last_error
        else "Unknown structured Gemini error."
    )

    raise RuntimeError(
        "Structured LLM request failed: "
        + _format_api_error(final_message, model_name)
    ) from last_error