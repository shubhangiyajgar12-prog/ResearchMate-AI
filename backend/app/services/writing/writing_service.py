import os
import json
import time
from typing import Dict, Any

from google import genai


class WritingService:

    def __init__(self):

        # ---------------------------------------------------------
        # Gemini API Key
        # ---------------------------------------------------------

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured in the environment."
            )

        # ---------------------------------------------------------
        # Gemini Client
        # ---------------------------------------------------------

        self.client = genai.Client(
            api_key=api_key
        )

        # ---------------------------------------------------------
        # Gemini Model Fallback List
        #
        # If one model is unavailable / overloaded,
        # the next model will automatically be tried.
        # ---------------------------------------------------------

        configured_model = os.getenv("GEMINI_MODEL")

        self.models = []

        if configured_model:
            self.models.append(configured_model)

        fallback_models = [
            "gemini-3.8-flash",
            "gemini-3.7-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash-lite",
        ]

        for model in fallback_models:

            if model not in self.models:
                self.models.append(model)

    # =========================================================
    # ANALYZE PAPER
    # =========================================================

    def analyze_paper(
        self,
        title: str,
        abstract: str,
        manuscript: str
    ) -> Dict[str, Any]:

        # ---------------------------------------------------------
        # Build Academic Writing Analysis Prompt
        # ---------------------------------------------------------

        prompt = f"""
You are an expert academic research writing mentor,
research methodology expert, and scientific publication reviewer.

Analyze the following research paper carefully.

Your job is NOT to rewrite the complete paper.

Your job is to provide a detailed, structured and actionable
academic writing analysis.

IMPORTANT RULES:

1. Do not invent references.
2. Do not invent experimental results.
3. Do not invent datasets.
4. Do not invent numerical values.
5. Do not claim that something is plagiarized.
6. Identify similarity/citation concerns only as risks.
7. Preserve the researcher's original meaning.
8. Do not change technical facts without evidence.
9. Focus on academic quality, clarity, structure,
   technical writing and publication readiness.
10. Give practical recommendations that a researcher
    can directly apply.
11. If information is missing from the manuscript,
    explicitly identify it as missing.
12. Do not assume that missing information exists.
13. Do not create fake citations or fake papers.
14. Use the actual manuscript as the only source
    for paper-specific claims.

Return ONLY valid JSON.

Required JSON structure:

{{
  "paper_structure": {{
      "detected_sections": [],
      "missing_sections": [],
      "section_order_feedback": "",
      "structure_score": 0
  }},

  "title_suggestions": [
      {{
          "title": "",
          "reason": ""
      }}
  ],

  "abstract_feedback": {{
      "has_background": true,
      "has_problem": true,
      "has_method": true,
      "has_results": true,
      "has_conclusion": true,
      "strengths": [],
      "issues": [],
      "suggested_improvements": []
  }},

  "academic_writing_feedback": {{
      "clarity": 0,
      "conciseness": 0,
      "academic_tone": 0,
      "grammar": 0,
      "technical_precision": 0,
      "coherence": 0,
      "strengths": [],
      "issues": [],
      "examples_to_improve": []
  }},

  "citation_reference_feedback": {{
      "citation_style_observations": [],
      "citation_risks": [],
      "reference_consistency_issues": [],
      "recommendations": []
  }},

  "formatting_feedback": {{
      "heading_issues": [],
      "paragraph_issues": [],
      "figure_table_issues": [],
      "equation_issues": [],
      "general_formatting_issues": []
  }},

  "overall_recommendations": [],

  "strengths": [],

  "improvement_areas": []
}}

ACADEMIC PAPER:

TITLE:
{title}

ABSTRACT:
{abstract}

MANUSCRIPT:
{manuscript}
"""

        # ---------------------------------------------------------
        # Gemini Request With Automatic Model Fallback
        # ---------------------------------------------------------

        response = None
        last_error = None

        for model_name in self.models:

            # Try each model a maximum of 2 times
            for attempt in range(2):

                try:

                    print(
                        f"[WritingService] "
                        f"Trying model: {model_name} "
                        f"(attempt {attempt + 1}/2)"
                    )

                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config={
                            "temperature": 0.2,
                            "response_mime_type": "application/json"
                        }
                    )

                    print(
                        f"[WritingService] "
                        f"Success with model: {model_name}"
                    )

                    break

                except Exception as e:

                    last_error = e
                    error_text = str(e)

                    print(
                        f"[WritingService] "
                        f"Model failed: {model_name}"
                    )

                    print(
                        f"[WritingService] "
                        f"Error: {error_text[:500]}"
                    )

                    # -------------------------------------------------
                    # Temporary availability / overload errors
                    # Retry once before switching model.
                    # -------------------------------------------------

                    if (
                        "503" in error_text
                        or "UNAVAILABLE" in error_text
                        or "429" in error_text
                        or "RESOURCE_EXHAUSTED" in error_text
                    ):

                        if attempt == 0:

                            print(
                                "[WritingService] "
                                "Temporary Gemini error. "
                                "Retrying..."
                            )

                            time.sleep(2)
                            continue

                        print(
                            "[WritingService] "
                            f"Switching from {model_name} "
                            "to next model."
                        )

                        break

                    # -------------------------------------------------
                    # Model not found / invalid model
                    # Try next model.
                    # -------------------------------------------------

                    if (
                        "404" in error_text
                        or "NOT_FOUND" in error_text
                    ):

                        print(
                            "[WritingService] "
                            f"Model {model_name} unavailable. "
                            "Trying next model."
                        )

                        break

                    # -------------------------------------------------
                    # Other errors
                    # -------------------------------------------------

                    raise

            # If successful, stop model loop
            if response is not None:
                break

        # ---------------------------------------------------------
        # All models failed
        # ---------------------------------------------------------

        if response is None:

            raise RuntimeError(
                "Writing analysis failed because all Gemini models "
                f"were unavailable. Last error: {last_error}"
            )

        # ---------------------------------------------------------
        # Read Gemini Response
        # ---------------------------------------------------------

        raw = response.text

        if not raw:
            raise RuntimeError(
                "Gemini returned an empty response."
            )

        raw = raw.strip()

        # ---------------------------------------------------------
        # Remove Markdown JSON Fences
        # ---------------------------------------------------------

        if raw.startswith("```json"):

            raw = raw[len("```json"):].strip()

        elif raw.startswith("```"):

            raw = raw[len("```"):].strip()

        if raw.endswith("```"):

            raw = raw[:-3].strip()

        # ---------------------------------------------------------
        # Parse JSON
        # ---------------------------------------------------------

        try:

            result = json.loads(raw)

        except json.JSONDecodeError as e:

            print(
                "[WritingService] "
                "Gemini returned invalid JSON."
            )

            print(
                f"[WritingService] Raw response: {raw[:1000]}"
            )

            raise RuntimeError(
                f"Gemini returned invalid JSON: {str(e)}"
            )

        # ---------------------------------------------------------
        # Ensure Expected Keys Exist
        # ---------------------------------------------------------

        result.setdefault(
            "paper_structure",
            {}
        )

        result.setdefault(
            "title_suggestions",
            []
        )

        result.setdefault(
            "abstract_feedback",
            {}
        )

        result.setdefault(
            "academic_writing_feedback",
            {}
        )

        result.setdefault(
            "citation_reference_feedback",
            {}
        )

        result.setdefault(
            "formatting_feedback",
            {}
        )

        result.setdefault(
            "overall_recommendations",
            []
        )

        result.setdefault(
            "strengths",
            []
        )

        result.setdefault(
            "improvement_areas",
            []
        )

        # ---------------------------------------------------------
        # Return Final Structured Result
        # ---------------------------------------------------------

        return result