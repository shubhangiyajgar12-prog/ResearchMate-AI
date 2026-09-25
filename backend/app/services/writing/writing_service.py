import re
from typing import Any

from app.services.ai.llm_service import (
    generate_json,
    generate_text,
)


class WritingService:

    # =========================================================
    # SECTION DETECTION
    # Deterministic — NOT AI generated
    # =========================================================

    SECTION_ALIASES = {
        "abstract": [
            "abstract",
        ],
        "introduction": [
            "introduction",
            "1 introduction",
        ],
        "background_related_work": [
            "background",
            "related work",
            "literature review",
        ],
        "methodology": [
            "methodology",
            "methods",
            "method",
            "materials and methods",
        ],
        "dataset_data_collection": [
            "dataset",
            "data collection",
            "data acquisition",
        ],
        "proposed_method_system": [
            "proposed method",
            "proposed system",
            "system architecture",
            "proposed approach",
        ],
        "experimental_setup": [
            "experimental setup",
            "experiments",
            "experimental methodology",
        ],
        "results": [
            "results",
            "experimental results",
        ],
        "discussion": [
            "discussion",
        ],
        "limitations": [
            "limitations",
        ],
        "conclusion": [
            "conclusion",
        ],
        "future_work": [
            "future work",
            "future scope",
        ],
        "references": [
            "references",
            "bibliography",
        ],
    }

    # =========================================================
    # BASIC HELPERS
    # =========================================================

    @staticmethod
    def _clean_list(
        value: Any,
    ) -> list[str]:

        if not isinstance(value, list):
            return []

        result = []

        for item in value:

            if isinstance(item, str):

                text = item.strip()

            elif isinstance(item, dict):

                text = (
                    item.get("text")
                    or item.get("message")
                    or item.get("reason")
                    or item.get("title")
                    or item.get("action")
                    or ""
                )

                text = str(text).strip()

            else:
                text = ""

            if text:
                result.append(text)

        return result

    @staticmethod
    def _clean_title_suggestions(
        value: Any,
    ) -> list[dict[str, str]]:

        if not isinstance(value, list):
            return []

        result: list[dict[str, str]] = []

        for item in value:

            if isinstance(item, str):
                title = item.strip()
                reason = (
                    "AI-generated title suggestion based on the supplied manuscript."
                )

            elif isinstance(item, dict):
                title = str(
                    item.get("title")
                    or item.get("suggested_title")
                    or item.get("text")
                    or ""
                ).strip()

                reason = str(
                    item.get("reason")
                    or item.get("explanation")
                    or item.get("rationale")
                    or ""
                ).strip()

                if not reason:
                    reason = (
                        "AI-generated title suggestion based on the supplied manuscript."
                    )

            else:
                continue

            if title:
                result.append(
                    {
                        "title": title,
                        "reason": reason,
                    }
                )

        return result

    @staticmethod
    def _extract_json(
        text: str,
    ) -> dict:

        text = (
            text or ""
        ).strip()

        if text.startswith("```json"):
            text = text[7:]

        elif text.startswith("```"):
            text = text[3:]

        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        import json

        return json.loads(
            text
        )

    # =========================================================
    # DETERMINISTIC SECTION DETECTION
    # =========================================================

    def detect_sections(
        self,
        manuscript: str,
    ) -> list[str]:

        if not manuscript:
            return []

        detected = []

        lines = manuscript.splitlines()

        for line in lines:

            normalized = re.sub(
                r"[^a-zA-Z0-9\s]",
                " ",
                line.lower(),
            )

            normalized = re.sub(
                r"\s+",
                " ",
                normalized,
            ).strip()

            if not normalized:
                continue

            for section_name, aliases in (
                self.SECTION_ALIASES.items()
            ):

                if section_name in detected:
                    continue

                for alias in aliases:

                    if (
                        normalized == alias
                        or normalized.startswith(
                            alias + " "
                        )
                    ):
                        detected.append(
                            section_name
                        )
                        break

        return detected

    # =========================================================
    # ANALYZE PAPER
    # =========================================================

    def analyze_paper(
        self,
        title: str,
        abstract: str,
        manuscript: str,
    ) -> dict:

        detected = self.detect_sections(
            manuscript
        )

        expected = list(
            self.SECTION_ALIASES.keys()
        )

        missing = [
            section
            for section in expected
            if section not in detected
            and section not in (
                "abstract",
            )
        ]

        structure_score = round(
            (
                len(detected)
                / max(
                    len(expected),
                    1,
                )
            )
            * 10,
            1,
        )

        prompt = f"""
You are an academic research writing assistant.

Analyze ONLY the supplied manuscript.

Do not invent:
- research results
- datasets
- metrics
- citations
- authors
- papers
- DOI values
- experimental numbers

If information is missing, say that it is missing.

Do not claim plagiarism.

Return JSON with exactly these top-level fields:

paper_structure
title_suggestions
abstract_feedback
academic_writing_feedback
citation_reference_feedback
formatting_feedback
overall_recommendations
strengths
improvement_areas

The deterministic section detection is:

{detected}

The deterministic structure score is:

{structure_score}

The AI may explain the evidence, but must not replace
these deterministic values.

MANUSCRIPT TITLE:
{title}

ABSTRACT:
{abstract}

MANUSCRIPT:
{manuscript}
"""

        try:

            result = generate_json(
                prompt
            )

        except Exception as exc:

            raise RuntimeError(
                "Writing AI analysis failed."
            ) from exc

        if not isinstance(
            result,
            dict,
        ):
            raise RuntimeError(
                "Writing AI returned an invalid object."
            )

        result["paper_structure"] = {
            "detected_sections": detected,
            "missing_sections": missing,
            "section_order_feedback": (
                result.get(
                    "paper_structure",
                    {},
                ).get(
                    "section_order_feedback",
                    "",
                )
            ),
            "structure_score": structure_score,
        }

        result["title_suggestions"] = (
            self._clean_title_suggestions(
                result.get(
                    "title_suggestions",
                    [],
                )
            )
        )

        result["overall_recommendations"] = (
            self._clean_list(
                result.get(
                    "overall_recommendations",
                    [],
                )
            )
        )

        result["strengths"] = (
            self._clean_list(
                result.get(
                    "strengths",
                    [],
                )
            )
        )

        result["improvement_areas"] = (
            self._clean_list(
                result.get(
                    "improvement_areas",
                    [],
                )
            )
        )

        return {
            "paper_structure": result[
                "paper_structure"
            ],

            "detected_sections": detected,

            "title_suggestions": result[
                "title_suggestions"
            ],

            "abstract_feedback": result.get(
                "abstract_feedback",
                {},
            ),

            "academic_writing_feedback": result.get(
                "academic_writing_feedback",
                {},
            ),

            "citation_reference_feedback": result.get(
                "citation_reference_feedback",
                {},
            ),

            "formatting_feedback": result.get(
                "formatting_feedback",
                {},
            ),

            "overall_recommendations": result[
                "overall_recommendations"
            ],

            "strengths": result[
                "strengths"
            ],

            "improvement_areas": result[
                "improvement_areas"
            ],
        }

    # =========================================================
    # SECTION WRITING ASSISTANT
    # =========================================================

    def assist_section(
        self,
        section_name: str,
        content: str,
        instruction: str,
        mode: str = "improve",
    ) -> str:

        section_name = (
            section_name
            or "unknown section"
        )

        prompt = f"""
You are assisting with academic research writing.

SECTION:
{section_name}

MODE:
{mode}

USER INSTRUCTION:
{instruction}

CURRENT TEXT:
{content}

Rules:

1. Preserve the author's meaning.
2. Do not invent facts.
3. Do not invent research results.
4. Do not invent numerical values.
5. Do not invent citations.
6. Do not invent datasets.
7. Do not invent references.
8. Do not introduce claims that cannot be supported
   by the supplied text.
9. If a result/value is missing, keep an explicit
   placeholder instead of inventing it.
10. Return only the revised text.
"""

        return generate_text(
            prompt,
            temperature=0.15,
        ).strip()