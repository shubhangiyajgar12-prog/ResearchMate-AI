import os
import json
import time
from typing import Dict, Any

from google import genai


class ImprovementService:

    def __init__(self):

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured."
            )

        self.client = genai.Client(
            api_key=api_key
        )

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
    # IMPROVEMENT PLAN
    # =========================================================

    def create_plan(
        self,
        manuscript: str
    ) -> Dict[str, Any]:

        prompt = f"""
You are an academic research improvement mentor.

Analyze the following research manuscript and create a detailed,
actionable improvement plan.

The objective is NOT to rewrite the complete manuscript.

Instead identify:
- what should be improved
- where it should be improved
- why it matters
- how the researcher should improve it
- what should be done first

IMPORTANT RULES:

1. Use ONLY information supported by the manuscript.
2. Do not invent experiments.
3. Do not invent datasets.
4. Do not invent references.
5. Do not invent numerical results.
6. Do not claim plagiarism.
7. Do not guarantee publication or acceptance.
8. Clearly mark information that is missing.
9. Preserve the researcher's technical meaning.
10. Prioritize changes that improve scientific rigor.
11. Separate quick fixes from substantial research improvements.
12. Make the plan practical and implementable.

Priority levels:

CRITICAL
HIGH
MEDIUM
LOW

Return ONLY valid JSON.

Required JSON:

{{
  "overall_plan": "",

  "priority_actions": [
    {{
      "priority": "CRITICAL",
      "section": "",
      "problem": "",
      "why_it_matters": "",
      "recommended_action": "",
      "expected_improvement": ""
    }}
  ],

  "section_improvements": [
    {{
      "section": "",
      "current_issue": "",
      "recommended_change": "",
      "priority": ""
    }}
  ],

  "methodology_improvements": [],

  "experiment_improvements": [],

  "writing_improvements": [],

  "citation_improvements": [],

  "formatting_improvements": [],

  "quick_fixes": [],

  "long_term_improvements": [],

  "revised_structure": [],

  "implementation_order": []
}}

MANUSCRIPT:

{manuscript}
"""

        response = None
        last_error = None

        # -----------------------------------------------------
        # GEMINI FALLBACK
        # -----------------------------------------------------

        for model_name in self.models:

            for attempt in range(2):

                try:

                    print(
                        f"[ImprovementService] "
                        f"Trying {model_name} "
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
                        f"[ImprovementService] "
                        f"Success with {model_name}"
                    )

                    break

                except Exception as e:

                    last_error = e
                    error_text = str(e)

                    print(
                        f"[ImprovementService] "
                        f"Model failed: "
                        f"{error_text[:400]}"
                    )

                    temporary_error = (
                        "503" in error_text
                        or "UNAVAILABLE" in error_text
                        or "429" in error_text
                        or "RESOURCE_EXHAUSTED" in error_text
                    )

                    if temporary_error:

                        if attempt == 0:
                            time.sleep(2)
                            continue

                        break

                    if (
                        "404" in error_text
                        or "NOT_FOUND" in error_text
                    ):
                        break

                    raise

            if response is not None:
                break

        # -----------------------------------------------------
        # ALL MODELS FAILED
        # -----------------------------------------------------

        if response is None:

            raise RuntimeError(
                "All Gemini models failed for improvement planning. "
                f"Last error: {last_error}"
            )

        # -----------------------------------------------------
        # RESPONSE
        # -----------------------------------------------------

        raw = response.text

        if not raw:
            raise RuntimeError(
                "Gemini returned an empty improvement plan."
            )

        raw = raw.strip()

        if raw.startswith("```json"):
            raw = raw[len("```json"):].strip()

        elif raw.startswith("```"):
            raw = raw[len("```"):].strip()

        if raw.endswith("```"):
            raw = raw[:-3].strip()

        # -----------------------------------------------------
        # JSON
        # -----------------------------------------------------

        try:

            result = json.loads(raw)

        except json.JSONDecodeError as e:

            raise RuntimeError(
                f"Improvement planner returned invalid JSON: {str(e)}"
            )

        # -----------------------------------------------------
        # DEFAULTS
        # -----------------------------------------------------

        defaults = {
            "overall_plan": "",
            "priority_actions": [],
            "section_improvements": [],
            "methodology_improvements": [],
            "experiment_improvements": [],
            "writing_improvements": [],
            "citation_improvements": [],
            "formatting_improvements": [],
            "quick_fixes": [],
            "long_term_improvements": [],
            "revised_structure": [],
            "implementation_order": []
        }

        for key, default_value in defaults.items():

            result.setdefault(
                key,
                default_value
            )

        return result