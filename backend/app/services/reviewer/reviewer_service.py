import os
import json
import time
from typing import Dict, Any

from google import genai


class ReviewerService:

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
    # REVIEW PAPER
    # =========================================================

    def review_paper(
        self,
        manuscript: str
    ) -> Dict[str, Any]:

        prompt = f"""
You are an experienced academic peer reviewer.

Perform a detailed peer-review style assessment of the
following research manuscript.

IMPORTANT RULES:

1. Review ONLY what is supported by the manuscript.
2. Do not invent experiments, results, datasets or references.
3. Do not claim plagiarism.
4. Do not invent missing information.
5. Clearly identify when information is absent.
6. Distinguish major concerns from minor concerns.
7. Give technically specific and actionable feedback.
8. Do not rewrite the complete paper.
9. Evaluate methodology, experiments, results and discussion.
10. Reviewer recommendation must be descriptive, not a guaranteed
    prediction of acceptance.
11. Do not provide an acceptance probability.
12. Do not invent reviewer comments from an actual journal.
13. Focus on scientific rigor, reproducibility, clarity and evidence.

Return ONLY valid JSON.

Required JSON structure:

{{
  "overall_review": "",

  "novelty_review": {{
      "assessment": "",
      "strengths": [],
      "concerns": [],
      "evidence_from_manuscript": []
  }},

  "methodology_review": {{
      "assessment": "",
      "strengths": [],
      "concerns": [],
      "missing_details": [],
      "reproducibility_issues": []
  }},

  "dataset_review": {{
      "assessment": "",
      "strengths": [],
      "concerns": [],
      "missing_details": []
  }},

  "experiment_review": {{
      "assessment": "",
      "strengths": [],
      "concerns": [],
      "missing_experiments": [],
      "reproducibility_issues": []
  }},

  "results_review": {{
      "assessment": "",
      "strengths": [],
      "concerns": [],
      "evidence_quality": [],
      "missing_analysis": []
  }},

  "discussion_review": {{
      "assessment": "",
      "strengths": [],
      "concerns": [],
      "missing_discussion_points": []
  }},

  "citation_review": {{
      "assessment": "",
      "citation_concerns": [],
      "reference_concerns": [],
      "recommendations": []
  }},

  "major_concerns": [],

  "minor_concerns": [],

  "technical_issues": [],

  "reviewer_questions": [],

  "strengths": [],

  "improvement_priorities": [],

  "reviewer_recommendation": ""
}}

MANUSCRIPT:

{manuscript}
"""

        response = None
        last_error = None

        # -----------------------------------------------------
        # MODEL FALLBACK
        # -----------------------------------------------------

        for model_name in self.models:

            for attempt in range(2):

                try:

                    print(
                        f"[ReviewerService] "
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
                        f"[ReviewerService] "
                        f"Success with {model_name}"
                    )

                    break

                except Exception as e:

                    last_error = e
                    error_text = str(e)

                    print(
                        f"[ReviewerService] "
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
                "All Gemini models failed for reviewer analysis. "
                f"Last error: {last_error}"
            )

        # -----------------------------------------------------
        # RESPONSE
        # -----------------------------------------------------

        raw = response.text

        if not raw:
            raise RuntimeError(
                "Gemini returned an empty reviewer response."
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
                f"Reviewer returned invalid JSON: {str(e)}"
            )

        # -----------------------------------------------------
        # SAFETY DEFAULTS
        # -----------------------------------------------------

        defaults = {
            "overall_review": "",
            "novelty_review": {},
            "methodology_review": {},
            "dataset_review": {},
            "experiment_review": {},
            "results_review": {},
            "discussion_review": {},
            "citation_review": {},
            "major_concerns": [],
            "minor_concerns": [],
            "technical_issues": [],
            "reviewer_questions": [],
            "strengths": [],
            "improvement_priorities": [],
            "reviewer_recommendation": ""
        }

        for key, default_value in defaults.items():

            result.setdefault(
                key,
                default_value
            )

        return result