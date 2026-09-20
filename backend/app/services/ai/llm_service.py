import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not configured in the .env file."
    )

client = genai.Client(api_key=GEMINI_API_KEY)

# Primary model + fallbacks.
# All three are currently listed by Google as stable Gemini 3 Flash models.
MODELS = [
     "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
]

# Number of attempts per model.
MAX_RETRIES_PER_MODEL = 2


def _is_retryable_error(error: Exception) -> bool:
    """
    Return True for temporary Gemini/API errors where retrying
    or switching to another model is reasonable.
    """
    error_text = str(error).upper()

    retryable_markers = [
        "503",
        "UNAVAILABLE",
        "429",
        "RESOURCE_EXHAUSTED",
        "500",
        "INTERNAL",
        "DEADLINE_EXCEEDED",
        "TIMEOUT",
    ]

    return any(marker in error_text for marker in retryable_markers)


def _generate_with_model(
    model_name: str,
    prompt: str,
    response_schema,
):
    """
    Try one Gemini model with exponential backoff.
    """
    last_error = None

    for attempt in range(MAX_RETRIES_PER_MODEL):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                ),
            )

            # Preferred path: Gemini returns JSON text.
            if getattr(response, "text", None):
                try:
                    return response_schema.model_validate_json(response.text)
                except Exception as error:
                    raise RuntimeError(
                        "Gemini returned JSON, but it did not match the "
                        f"expected schema: {error}"
                    ) from error

            # Compatibility fallback for SDK versions exposing parsed output.
            if getattr(response, "parsed", None) is not None:
                return response.parsed

            raise RuntimeError(
                f"Gemini returned an empty response from {model_name}."
            )

        except Exception as error:
            last_error = error

            if not _is_retryable_error(error):
                raise

            # Exponential backoff: 2s, then 4s.
            if attempt < MAX_RETRIES_PER_MODEL - 1:
                wait_seconds = 2 ** (attempt + 1)
                print(
                    f"[Gemini] {model_name} temporary error. "
                    f"Retrying in {wait_seconds}s..."
                )
                time.sleep(wait_seconds)

    raise last_error


def generate_structured_response(
    prompt: str,
    response_schema,
):
    """
    Generate a structured Pydantic response from Gemini.

    Strategy:
    1. Try Gemini 3.8 Flash.
    2. Retry temporary errors with exponential backoff.
    3. Fall back to Gemini 3.7 Flash.
    4. Fall back to Gemini 3.6 Flash.
    5. If every model fails, raise a clear error.
    """
    errors = []

    for model_name in MODELS:
        try:
            print(f"[Gemini] Trying model: {model_name}")

            result = _generate_with_model(
                model_name=model_name,
                prompt=prompt,
                response_schema=response_schema,
            )

            print(f"[Gemini] Success with model: {model_name}")
            return result

        except Exception as error:
            errors.append(
                f"{model_name}: {type(error).__name__}: {error}"
            )

            print(
                f"[Gemini] {model_name} failed: "
                f"{type(error).__name__}: {error}"
            )

            # Continue to the next fallback model for temporary failures.
            if not _is_retryable_error(error):
                raise

    raise RuntimeError(
        "Gemini AI service is temporarily unavailable. "
        "All configured models failed after retries. "
        "Please try again shortly.\n\n"
        + "\n".join(errors)
    )
