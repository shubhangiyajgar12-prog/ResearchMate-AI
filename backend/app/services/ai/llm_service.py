import os
import time
import json
from dotenv import load_dotenv

load_dotenv()

_client = None


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


def generate_text(
    prompt: str,
    model: str | None = None,
    temperature: float = 0.2
):
    client = _get_client()

    if client is None:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. "
            "Configure it in backend/.env to enable LLM features."
        )

    model_name = model or os.getenv(
        "GEMINI_MODEL",
        "gemini-2.5-flash"
    )

    last = None

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={
                    "temperature": temperature
                }
            )

            if not getattr(response, "text", None):
                raise RuntimeError(
                    "Gemini returned an empty response"
                )

            return response.text

        except Exception as exc:
            last = exc

            if (
                attempt < 2
                and any(
                    x in str(exc).upper()
                    for x in (
                        "429",
                        "503",
                        "UNAVAILABLE",
                        "TIMEOUT"
                    )
                )
            ):
                time.sleep(2 ** attempt)
                continue

            break

    raise RuntimeError(f"LLM request failed: {last}")


def generate_json(
    prompt: str,
    model: str | None = None
):
    raw = generate_text(
        prompt + "\nReturn ONLY valid JSON.",
        model=model
    )

    raw = raw.strip()

    if raw.startswith("```json"):
        raw = raw[7:]

    if raw.startswith("```"):
        raw = raw[3:]

    if raw.endswith("```"):
        raw = raw[:-3]

    return json.loads(raw.strip())


def generate_structured_response(
    prompt: str,
    response_schema,
    model: str | None = None,
    temperature: float = 0.2
):
    """
    Generate a structured response using Gemini
    and validate it using the provided Pydantic schema.
    """

    client = _get_client()

    if client is None:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. "
            "Configure it in backend/.env to enable LLM features."
        )

    model_name = model or os.getenv(
        "GEMINI_MODEL",
        "gemini-2.5-flash"
    )

    last = None

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={
                    "temperature": temperature,
                    "response_mime_type": "application/json",
                    "response_schema": response_schema,
                },
            )

            if not getattr(response, "text", None):
                raise RuntimeError(
                    "Gemini returned an empty response"
                )

            # Parse JSON returned by Gemini
            data = json.loads(response.text)

            # Validate against the project's Pydantic schema
            return response_schema.model_validate(data)

        except Exception as exc:
            last = exc

            if (
                attempt < 2
                and any(
                    x in str(exc).upper()
                    for x in (
                        "429",
                        "503",
                        "UNAVAILABLE",
                        "TIMEOUT"
                    )
                )
            ):
                time.sleep(2 ** attempt)
                continue

            break

    raise RuntimeError(
        f"Structured LLM request failed: {last}"
    )