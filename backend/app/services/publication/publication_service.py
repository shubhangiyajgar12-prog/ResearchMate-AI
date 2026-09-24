import os
import json
import time
from typing import Dict, Any

from google import genai


class PublicationService:

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
    # PUBLICATION ANALYSIS
    # =========================================================

    def analyze_publication(
        self,
        manuscript: str,
        research_field: str
    ) -> Dict[str, Any]:

        prompt = f"""
You are an academic publication assistant.

Analyze the following research manuscript and provide a
publication preparation plan.

The system should help the researcher understand which types
of journals and conferences may fit the research and what
needs to be prepared before submission.

IMPORTANT RULES:

1. Do not guarantee publication or acceptance.
2. Do not generate an acceptance probability.
3. Do not invent journal or conference deadlines.
4. Do not invent impact factors.
5. Do not invent indexing information.
6. Do not claim a publisher is predatory without verified evidence.
7. If information cannot be verified from the manuscript,
   explicitly mark it as requiring external verification.
8. Do not invent references.
9. Do not invent missing manuscript content.
10. Distinguish recommendations from verified publication facts.
11. Treat journal/conference names as candidate venues requiring
    current verification before submission.
12. Focus on publication fit, requirements and preparation.

Return ONLY valid JSON.

Required JSON:

{{
  "publication_strategy": "",

  "journal_recommendations": [
    {{
      "venue_type": "journal",
      "name": "",
      "research_scope": "",
      "fit_reason": "",
      "relevance": 0,
      "technical_fit": 0,
      "submission_notes": "",
      "verification_required": true
    }}
  ],

  "conference_recommendations": [
    {{
      "venue_type": "conference",
      "name": "",
      "research_scope": "",
      "fit_reason": "",
      "relevance": 0,
      "technical_fit": 0,
      "submission_notes": "",
      "verification_required": true
    }}
  ],

  "publication_fit": {{
      "research_area": "",
      "topic_alignment": "",
      "methodology_alignment": "",
      "expected_audience": "",
      "strengths_for_publication": [],
      "publication_gaps": []
  }},

  "predatory_risk_checks": [
    {{
      "venue": "",
      "risk_indicator": "",
      "status": "requires_external_verification",
      "reason": ""
    }}
  ],

  "submission_checklist": [
    {{
      "item": "",
      "status": "missing",
      "importance": "high",
      "notes": ""
    }}
  ],

  "manuscript_requirements": [],

  "missing_submission_items": [],

  "cfp_and_deadline_notes": [],

  "preparation_plan": [
    {{
      "step": 1,
      "action": "",
      "reason": "",
      "priority": "high"
    }}
  ],

  "important_warnings": []
}}

RESEARCH FIELD:

{research_field}

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
                        f"[PublicationService] "
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
                        f"[PublicationService] "
                        f"Success with {model_name}"
                    )

                    break

                except Exception as e:

                    last_error = e
                    error_text = str(e)

                    print(
                        f"[PublicationService] "
                        f"{model_name} failed: "
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
                "All Gemini models failed for publication analysis. "
                f"Last error: {last_error}"
            )

        # -----------------------------------------------------
        # RESPONSE
        # -----------------------------------------------------

        raw = response.text

        if not raw:
            raise RuntimeError(
                "Gemini returned an empty publication response."
            )

        raw = raw.strip()

        if raw.startswith("```json"):
            raw = raw[len("```json"):].strip()

        elif raw.startswith("```"):
            raw = raw[len("```"):].strip()

        if raw.endswith("```"):
            raw = raw[:-3].strip()

        # -----------------------------------------------------
        # JSON PARSE
        # -----------------------------------------------------

        try:

            result = json.loads(raw)

        except json.JSONDecodeError as e:

            raise RuntimeError(
                f"Publication assistant returned invalid JSON: {str(e)}"
            )

        # -----------------------------------------------------
        # DEFAULTS
        # -----------------------------------------------------

        defaults = {
            "publication_strategy": "",
            "journal_recommendations": [],
            "conference_recommendations": [],
            "publication_fit": {},
            "predatory_risk_checks": [],
            "submission_checklist": [],
            "manuscript_requirements": [],
            "missing_submission_items": [],
            "cfp_and_deadline_notes": [],
            "preparation_plan": [],
            "important_warnings": []
        }

        for key, default_value in defaults.items():

            result.setdefault(
                key,
                default_value
            )

        return result