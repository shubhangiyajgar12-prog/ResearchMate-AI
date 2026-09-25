import re
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy.orm import Session
from app.services.ai.llm_service import generate_text
from app.database.database import get_db

from app.models.research_project import ResearchProject
from app.models.literature_paper import LiteraturePaper
from app.models.paper_analysis import PaperAnalysis
from app.models.manuscript import (
    Manuscript,
    ManuscriptVersion,
)

from app.schemas.manuscript import (
    ManuscriptCreate,
    ManuscriptUpdate,
    ManuscriptResponse,
    ManuscriptVersionResponse,
    WritingAssistRequest,
    WritingAssistResponse,
    WritingReadinessResponse,
)

from app.schemas.writing import WritingAnalysisRequest

from app.services.writing.writing_service import (
    WritingService,
)


router = APIRouter(
    prefix="/writing",
    tags=["Writing"],
)


# ============================================================
# HELPERS
# ============================================================

DEFAULT_SECTIONS = {
    "title": "",
    "abstract": "",
    "keywords": "",
    "introduction": "",
    "background_related_work": "",
    "problem_statement": "",
    "research_objectives": "",
    "research_questions": "",
    "literature_review": "",
    "research_gap": "",
    "methodology": "",
    "dataset_data_collection": "",
    "proposed_method_system": "",
    "experimental_setup": "",
    "results": "",
    "discussion": "",
    "limitations": "",
    "conclusion": "",
    "future_work": "",
    "references": "",
}
def _build_project_context(
    project_id: int,
    db: Session,
    selected_paper_ids: list[int] | None = None,
):
    """
    Build an evidence-first, project-scoped context for AI writing.

    The current ResearchProject model stores title, description,
    research_field, status and timestamps. This helper never invents
    additional project facts.
    """

    project = _project_or_404(project_id, db)

    selected_ids = None

    if selected_paper_ids:
        try:
            selected_ids = {
                int(value)
                for value in selected_paper_ids
            }
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=400,
                detail=(
                    "selected_paper_ids must contain valid "
                    "integer paper IDs."
                ),
            ) from exc

    papers = (
        db.query(LiteraturePaper)
        .filter(
            LiteraturePaper.project_id == project_id
        )
        .all()
    )

    # Keep the complete project library for the UI. The AI context is
    # intentionally smaller and is built separately below.
    all_project_papers = list(papers)

    if selected_ids is not None:
        found_ids = {
            paper.id
            for paper in papers
            if paper.id in selected_ids
        }

        missing_ids = sorted(
            selected_ids - found_ids
        )

        if missing_ids:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Selected paper(s) do not belong to this "
                    f"research project: {missing_ids}"
                ),
            )

        papers = [
            paper
            for paper in papers
            if paper.id in selected_ids
        ]

    analyses = (
        db.query(PaperAnalysis)
        .filter(
            PaperAnalysis.project_id == project_id
        )
        .all()
    )

    analysis_by_paper = {
        analysis.literature_paper_id: analysis
        for analysis in analyses
    }

    # Deterministic retrieval ranking from stored project terms.
    # This is deliberately conservative: a paper is allowed into the
    # AI context only when it has a meaningful project-topic signal.
    context_text = " ".join(
        [
            project.title or "",
            project.description or "",
            project.research_field or "",
        ]
    ).lower()

    stop_words = {
        "research", "study", "studies", "system", "using", "based",
        "analysis", "detection", "detect", "model", "models", "approach",
        "method", "methods", "project", "the", "and", "for", "with",
        "from", "into", "this", "that", "paper", "papers", "existing",
        "identify", "identifying", "gap", "gaps", "computer", "vision",
        "artificial", "intelligence", "deep", "learning", "application",
        "applications", "development", "design", "proposed", "propose",
        "real", "time", "multi", "class", "technique", "techniques",
    }

    def clean_tokens(text: str):
        return {
            token
            for token in re.findall(r"[a-z0-9]{3,}", text.lower())
            if token not in stop_words
        }

    context_tokens = clean_tokens(context_text)

    # Explicit domain aliases prevent generic words such as "existing"
    # or "detection" from making unrelated papers look relevant.
    alias_groups = [
        {"helmet", "helmets", "motorcycle", "motorcyclist", "rider",
         "riders", "traffic", "road", "roadway", "vehicle"},
        {"accident", "accidents", "crash", "crashes", "collision",
         "collisions", "road", "traffic"},
        {"license", "licence", "plate", "numberplate", "number", "vehicle"},
        {"yolo", "yolov8", "yolov9", "yolov10", "yolov11"},
        {"cancer", "tumor", "tumour", "oncology"},
        {"healthcare", "medical", "clinical", "patient", "disease"},
        {"weapon", "weapons", "firearm", "gun", "knife", "surveillance"},
        {"face", "facial", "recognition"},
    ]

    active_aliases = []
    for group in alias_groups:
        if context_tokens.intersection(group):
            active_aliases.append(group)

    context_phrases = set(
        re.findall(
            r"[a-z0-9]+(?:\s+[a-z0-9]+)+",
            context_text,
        )
    )

    ranked = []

    for paper in papers:
        title = (paper.title or "").lower()
        abstract = (paper.abstract or "").lower()
        paper_text = f"{title} {abstract}"

        paper_tokens = clean_tokens(paper_text)
        title_tokens = clean_tokens(title)

        token_overlap = len(context_tokens.intersection(paper_tokens))
        title_overlap = len(context_tokens.intersection(title_tokens))

        alias_hits = 0
        for group in active_aliases:
            if any(term in paper_text for term in group):
                alias_hits += 1

        # Strong exact phrase signals.
        phrase_hits = 0
        for phrase in (
            "helmet violation",
            "helmet detection",
            "non-helmeted",
            "motorcycle rider",
            "traffic violation",
            "road accident",
            "accident detection",
            "license plate",
            "number plate",
            "vehicle detection",
            "yolov8",
        ):
            if phrase in paper_text and phrase in context_text:
                phrase_hits += 1

        # Exact multi-word overlap from the project title/description.
        project_terms = re.findall(
            r"[a-z0-9]+(?:\s+[a-z0-9]+)+",
            context_text,
        )
        exact_phrase_hits = sum(
            1 for phrase in project_terms
            if len(phrase.split()) >= 2 and phrase in paper_text
        )

        relevance_score = (
            exact_phrase_hits * 10
            + phrase_hits * 8
            + alias_hits * 7
            + title_overlap * 4
            + token_overlap
        )

        # If the project has a recognizable domain, require at least one
        # strong domain signal. This removes unrelated saved papers from
        # the AI context while still keeping them safely in the database.
        strong_domain_match = (
            alias_hits > 0
            or exact_phrase_hits > 0
            or title_overlap >= 2
        )

        ranked.append(
            (
                relevance_score,
                strong_domain_match,
                title_overlap,
                token_overlap,
                paper.year or 0,
                paper.id,
                paper,
            )
        )

    ranked.sort(
        key=lambda row: (
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
        ),
        reverse=True,
    )

    if selected_ids is None:
        # Do not silently feed unrelated papers to the LLM.
        relevant = [
            row for row in ranked
            if row[0] >= 7 and row[1]
        ]

        # If there is no strong match, use only papers with at least two
        # meaningful project-term overlaps. This is safer than arbitrary
        # "latest five" fallback.
        if not relevant:
            relevant = [
                row for row in ranked
                if row[2] >= 2 or row[3] >= 3
            ]

        ranked = relevant

    ranked = ranked[:8]

    literature = []

    for relevance_score, _, _, _, _, _, paper in ranked:
        analysis = analysis_by_paper.get(
            paper.id
        )

        document_evidence = ""

        if analysis:
            document_evidence = (
                analysis.extracted_text or ""
            )[:6000]

        literature.append(
            {
                "paper_id": paper.id,
                "title": paper.title,
                "year": paper.year,
                "authors": paper.authors,
                "doi": paper.doi,
                "abstract": (
                    paper.abstract or ""
                )[:4000],
                "document_evidence": document_evidence,
                "retrieval_note": (
                    "Saved in the selected research project."
                ),
                "relevance_signal": (
                    "Strong project-topic match"
                    if relevance_score >= 7
                    else "Meaningful project-term overlap"
                ),
            }
        )

    analysed_ids = {
        analysis.literature_paper_id
        for analysis in analyses
    }

    all_literature = []
    for paper in all_project_papers:
        all_literature.append({
            "paper_id": paper.id,
            "title": paper.title,
            "year": paper.year,
            "authors": paper.authors,
            "doi": paper.doi,
            "abstract": (paper.abstract or "")[:1000],
            "analysed": paper.id in analysed_ids,
        })

    return {
        "project": {
            "id": project.id,
            "title": project.title,
            "description": project.description,
            "research_field": project.research_field,
            "status": project.status,
        },
        "literature": literature,
        "all_literature": all_literature,
        "literature_count": len(all_project_papers),
        "context_literature_count": len(literature),
        "analysed_paper_count": len(
            [
                paper_id
                for paper_id in analysed_ids
                if (
                    selected_ids is None
                    or paper_id in selected_ids
                )
            ]
        ),
        "analysed_paper_ids": sorted(
            [
                paper_id
                for paper_id in analysed_ids
                if (
                    selected_ids is None
                    or paper_id in selected_ids
                )
            ]
        ),
    }


def _project_or_404(
    project_id: int,
    db: Session,
):
    project = (
        db.query(ResearchProject)
        .filter(
            ResearchProject.id == project_id
        )
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Research project not found.",
        )

    return project


def _paper_or_404(
    project_id: int,
    paper_id: int,
    db: Session,
):
    paper = (
        db.query(LiteraturePaper)
        .filter(
            LiteraturePaper.id == paper_id,
            LiteraturePaper.project_id == project_id,
        )
        .first()
    )

    if not paper:
        raise HTTPException(
            status_code=404,
            detail="Paper not found in this research project.",
        )

    return paper


def _word_count(
    title: str,
    abstract: str,
    sections: dict,
) -> int:

    parts = [
        title or "",
        abstract or "",
    ]

    for value in sections.values():
        if isinstance(value, str):
            parts.append(value)

    text = " ".join(parts)

    return len(
        text.split()
    )


def _character_count(
    title: str,
    abstract: str,
    sections: dict,
) -> int:

    parts = [
        title or "",
        abstract or "",
    ]

    for value in sections.values():
        if isinstance(value, str):
            parts.append(value)

    return len(
        "\n".join(parts)
    )


def _normalize_sections(
    sections: dict | None,
) -> dict:

    normalized = dict(DEFAULT_SECTIONS)

    if isinstance(sections, dict):

        for key, value in sections.items():

            if key not in normalized:
                normalized[key] = ""

            if value is None:
                normalized[key] = ""

            elif isinstance(value, str):
                normalized[key] = value

            else:
                normalized[key] = str(value)

    return normalized


def _manuscript_response(
    manuscript: Manuscript,
):
    sections = _normalize_sections(
        manuscript.sections
    )

    return {
        "id": manuscript.id,
        "project_id": manuscript.project_id,
        "paper_id": manuscript.paper_id,

        "title": manuscript.title or "",
        "abstract": manuscript.abstract or "",

        "keywords": (
            manuscript.keywords
            if isinstance(manuscript.keywords, list)
            else []
        ),

        "sections": sections,

        "status": manuscript.status or "draft",

        "current_version": (
            manuscript.current_version or 1
        ),

        "word_count": _word_count(
            manuscript.title or "",
            manuscript.abstract or "",
            sections,
        ),

        "character_count": _character_count(
            manuscript.title or "",
            manuscript.abstract or "",
            sections,
        ),

        "created_at": manuscript.created_at,
        "updated_at": manuscript.updated_at,
    }


# ============================================================
# CREATE MANUSCRIPT
# ============================================================

@router.post(
    "/projects/{project_id}/manuscript",
    response_model=ManuscriptResponse,
)
def create_manuscript(
    project_id: int,
    payload: ManuscriptCreate,
    db: Session = Depends(get_db),
):

    _project_or_404(
        project_id,
        db,
    )

    if payload.paper_id is not None:

        _paper_or_404(
            project_id,
            payload.paper_id,
            db,
        )

    existing = (
        db.query(Manuscript)
        .filter(
            Manuscript.project_id == project_id
        )
        .first()
    )

    if existing:

        raise HTTPException(
            status_code=409,
            detail=(
                "A manuscript already exists for "
                "this research project."
            ),
        )

    sections = _normalize_sections(
        payload.sections
    )

    manuscript = Manuscript(
        project_id=project_id,
        paper_id=payload.paper_id,

        title=payload.title.strip(),

        abstract=payload.abstract.strip(),

        keywords=[
            str(keyword).strip()
            for keyword in payload.keywords
            if str(keyword).strip()
        ],

        sections=sections,

        status="draft",

        current_version=1,
    )

    db.add(manuscript)

    db.commit()

    db.refresh(manuscript)

    # Create initial version
    version = ManuscriptVersion(
        manuscript_id=manuscript.id,
        version_number=1,

        title=manuscript.title or "",
        abstract=manuscript.abstract or "",

        keywords=manuscript.keywords or [],

        sections=sections,

        change_summary="Initial manuscript created.",
    )

    db.add(version)

    db.commit()

    db.refresh(manuscript)

    return _manuscript_response(
        manuscript
    )


# ============================================================
# GET MANUSCRIPT
# ============================================================

@router.get(
    "/projects/{project_id}/manuscript",
    response_model=ManuscriptResponse,
)
def get_manuscript(
    project_id: int,
    db: Session = Depends(get_db),
):

    _project_or_404(
        project_id,
        db,
    )

    manuscript = (
        db.query(Manuscript)
        .filter(
            Manuscript.project_id == project_id
        )
        .first()
    )

    if not manuscript:

        raise HTTPException(
            status_code=404,
            detail="Manuscript not found.",
        )

    return _manuscript_response(
        manuscript
    )


# ============================================================
# UPDATE MANUSCRIPT
# ============================================================

@router.put(
    "/projects/{project_id}/manuscript",
    response_model=ManuscriptResponse,
)
def update_manuscript(
    project_id: int,
    payload: ManuscriptUpdate,
    db: Session = Depends(get_db),
):

    _project_or_404(
        project_id,
        db,
    )

    manuscript = (
        db.query(Manuscript)
        .filter(
            Manuscript.project_id == project_id
        )
        .first()
    )

    if not manuscript:

        raise HTTPException(
            status_code=404,
            detail="Manuscript not found.",
        )

    if payload.paper_id is not None:

        _paper_or_404(
            project_id,
            payload.paper_id,
            db,
        )

        manuscript.paper_id = payload.paper_id

    manuscript.title = (
        payload.title.strip()
    )

    manuscript.abstract = (
        payload.abstract.strip()
    )

    manuscript.keywords = [
        str(keyword).strip()
        for keyword in payload.keywords
        if str(keyword).strip()
    ]

    manuscript.sections = _normalize_sections(
        payload.sections
    )

    manuscript.status = (
        payload.status.strip()
        or "draft"
    )

    next_version = (
        manuscript.current_version + 1
    )

    version = ManuscriptVersion(
        manuscript_id=manuscript.id,

        version_number=next_version,

        title=manuscript.title or "",

        abstract=manuscript.abstract or "",

        keywords=manuscript.keywords or [],

        sections=manuscript.sections or {},

        change_summary=(
            payload.change_summary.strip()
            or "Manuscript updated."
        ),
    )

    manuscript.current_version = next_version

    db.add(version)

    db.commit()

    db.refresh(manuscript)

    return _manuscript_response(
        manuscript
    )


# ============================================================
# GET VERSION HISTORY
# ============================================================

@router.get(
    "/projects/{project_id}/versions",
    response_model=list[
        ManuscriptVersionResponse
    ],
)
def get_versions(
    project_id: int,
    db: Session = Depends(get_db),
):

    _project_or_404(
        project_id,
        db,
    )

    manuscript = (
        db.query(Manuscript)
        .filter(
            Manuscript.project_id == project_id
        )
        .first()
    )

    if not manuscript:

        raise HTTPException(
            status_code=404,
            detail="Manuscript not found.",
        )

    versions = (
        db.query(ManuscriptVersion)
        .filter(
            ManuscriptVersion.manuscript_id
            == manuscript.id
        )
        .order_by(
            ManuscriptVersion.version_number.desc()
        )
        .all()
    )

    return versions


# ============================================================
# RESTORE VERSION
# ============================================================

@router.post(
    "/projects/{project_id}/versions/{version_id}/restore",
    response_model=ManuscriptResponse,
)
def restore_version(
    project_id: int,
    version_id: int,
    db: Session = Depends(get_db),
):

    _project_or_404(
        project_id,
        db,
    )

    manuscript = (
        db.query(Manuscript)
        .filter(
            Manuscript.project_id == project_id
        )
        .first()
    )

    if not manuscript:

        raise HTTPException(
            status_code=404,
            detail="Manuscript not found.",
        )

    version = (
        db.query(ManuscriptVersion)
        .filter(
            ManuscriptVersion.id == version_id,
            ManuscriptVersion.manuscript_id
            == manuscript.id,
        )
        .first()
    )

    if not version:

        raise HTTPException(
            status_code=404,
            detail=(
                "Version not found for this "
                "research project."
            ),
        )

    next_version = (
        manuscript.current_version + 1
    )

    manuscript.title = (
        version.title or ""
    )

    manuscript.abstract = (
        version.abstract or ""
    )

    manuscript.keywords = (
        version.keywords or []
    )

    manuscript.sections = (
        _normalize_sections(
            version.sections
        )
    )

    manuscript.current_version = next_version

    new_version = ManuscriptVersion(
        manuscript_id=manuscript.id,

        version_number=next_version,

        title=manuscript.title or "",

        abstract=manuscript.abstract or "",

        keywords=manuscript.keywords or [],

        sections=manuscript.sections or {},

        change_summary=(
            f"Restored from version "
            f"{version.version_number}."
        ),
    )

    db.add(new_version)

    db.commit()

    db.refresh(manuscript)

    return _manuscript_response(
        manuscript
    )


# ============================================================
# PROJECT CONTEXT FOR WRITING WORKSPACE
# ============================================================

@router.get(
    "/projects/{project_id}/context"
)
def get_project_writing_context(
    project_id: int,
    db: Session = Depends(get_db),
):
    """
    Return the real stored research context used by the Writing
    workspace. This endpoint is read-only.

    The frontend does not choose a paper here. The project is the
    source of truth, and the backend ranks the project's own saved
    literature deterministically.
    """

    context = _build_project_context(
        project_id=project_id,
        db=db,
        selected_paper_ids=None,
    )

    return {
        "success": True,
        "project": context["project"],
        "literature": context["literature"],
        "literature_count": context["literature_count"],
        "context_literature_count": context[
            "context_literature_count"
        ],
        "analysed_paper_count": context[
            "analysed_paper_count"
        ],
        "analysed_paper_ids": context[
            "analysed_paper_ids"
        ],
        "evidence_note": (
            "Literature shown here is restricted to papers saved "
            "under this research project. Ordering is a deterministic "
            "project-term retrieval heuristic; it is not an AI "
            "relevance score."
        ),
    }


# ============================================================
# MANUSCRIPT TITLE + ABSTRACT GENERATION
# ============================================================

@router.post(
    "/projects/{project_id}/metadata/generate"
)
def generate_manuscript_metadata(
    project_id: int,
    payload: dict | None = None,
    db: Session = Depends(get_db),
):
    """Generate manuscript title and abstract from one project only.

    This endpoint does not create or save a manuscript by itself. The
    frontend receives the generated metadata and the normal Save
    Manuscript action persists it, so the user can review it first.
    """

    payload = payload or {}
    context = _build_project_context(
        project_id=project_id,
        db=db,
        selected_paper_ids=None,
    )

    project = context["project"]
    literature = context["literature"]

    project_title = project.get("title") or "Research project"
    field = project.get("research_field") or "research"
    description = project.get("description") or "No detailed project description is stored."

    evidence_blocks = []
    for paper in literature[:8]:
        evidence_blocks.append(
            "\n".join(
                [
                    f"Paper title: {paper.get('title') or 'Unknown'}",
                    f"Year: {paper.get('year') or 'Unknown'}",
                    f"Authors: {paper.get('authors') or 'Unknown'}",
                    f"DOI: {paper.get('doi') or 'Not stored'}",
                    f"Abstract: {paper.get('abstract') or 'Abstract unavailable'}",
                    f"Document evidence: {paper.get('document_evidence') or 'No PDF-derived evidence stored'}",
                ]
            )
        )

    evidence_text = "\n\n---\n\n".join(evidence_blocks)
    if not evidence_text:
        evidence_text = "No project-scoped literature is currently saved."

    instruction = str(payload.get("instruction") or "").strip()

    prompt = f"""
You are the manuscript metadata writer for ResearchMate AI.
Generate a research-paper title and abstract for ONE exact research project.

PROJECT
Title: {project_title}
Field: {field}
Description/context:
{description}

PROJECT-SCOPED LITERATURE
{evidence_text}

USER INSTRUCTION
{instruction or 'Generate a concise publication-ready title and a structured academic abstract.'}

NON-NEGOTIABLE EVIDENCE RULES
1. Stay strictly within this project.
2. Never invent authors, DOI, journal names, datasets, sample sizes, results,
   accuracy/precision/recall/F1 values, statistics, or numerical claims.
3. A paper abstract supports only claims actually stated in that abstract.
4. PDF/document evidence supports only what is present in the supplied evidence.
5. Do not claim novelty as a proven fact. Use wording such as "the proposed study"
   or "the project investigates" when novelty has not been established.
6. Do not invent completed experiments. If results are not stored, the abstract
   must describe the planned/proposed study without fabricated outcomes.
7. The title must match the exact project topic and must not introduce a different domain.
8. Return JSON only in this exact shape:
{{
  "title": "...",
  "abstract": "..."
}}
"""

    ai_error = None
    generated = ""
    try:
        generated = generate_text(
            prompt,
            temperature=0.15,
        ) or ""
    except Exception as exc:
        ai_error = str(exc)

    title = ""
    abstract = ""

    # Parse structured JSON first, then gracefully handle an LLM that returned
    # a plain JSON-like response with markdown fences.
    if generated.strip():
        raw = generated.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)
        try:
            import json
            parsed = json.loads(raw)
            title = str(parsed.get("title") or "").strip()
            abstract = str(parsed.get("abstract") or "").strip()
        except Exception:
            # Last-resort extraction for malformed structured output.
            title_match = re.search(
                r'"title"\s*:\s*"((?:\\.|[^"\\])*)"',
                raw,
                flags=re.DOTALL,
            )
            abstract_match = re.search(
                r'"abstract"\s*:\s*"((?:\\.|[^"\\])*)"',
                raw,
                flags=re.DOTALL,
            )
            if title_match:
                title = title_match.group(1).replace('\\"', '"').strip()
            if abstract_match:
                abstract = abstract_match.group(1).replace('\\"', '"').strip()

    # Deterministic evidence-only fallback. It intentionally avoids claiming
    # results or other facts that are not stored in the database.
    if not title:
        title = project_title

    if not abstract:
        if literature:
            paper_names = "; ".join(
                paper.get("title")
                for paper in literature[:5]
                if paper.get("title")
            )
            abstract = (
                f"This research project investigates {project_title} within the field of {field}. "
                f"The stored project description states: {description} "
                f"The project-scoped literature currently available to the manuscript workspace includes {paper_names}. "
                "These sources provide background for defining the research problem and positioning the proposed study. "
                "The current project record does not contain validated experimental results, so no performance outcome is claimed in this abstract. "
                "The proposed work should be developed and evaluated using a reproducible methodology and evidence-based analysis."
            )
        else:
            abstract = (
                f"This research project investigates {project_title} within the field of {field}. "
                f"The stored project description states: {description} "
                "The proposed study is intended to address the stated research problem through a systematic and reproducible research process. "
                "No experimental results or quantitative performance claims are currently stored for this project, so this abstract does not report unsupported outcomes."
            )

    return {
        "success": True,
        "project_id": project_id,
        "title": title,
        "abstract": abstract,
        "generation_mode": "ai" if not ai_error and generated.strip() else "deterministic_fallback",
        "evidence": {
            "literature_count": context["literature_count"],
            "context_literature_count": context["context_literature_count"],
            "analysed_paper_count": context["analysed_paper_count"],
        },
        "evidence_note": (
            "Metadata is generated from this project's stored context and project-scoped literature. "
            "Review it before saving or submitting the manuscript."
        ),
    }


# ============================================================
# PROJECT-AWARE AI DRAFT GENERATION
# ============================================================

@router.post(
    "/projects/{project_id}/sections/{section_name}/generate"
)
def generate_section_draft(
    project_id: int,
    section_name: str,
    payload: dict | None = None,
    db: Session = Depends(get_db),
):
    """
    Generate one manuscript section from the selected project and
    project-scoped saved literature.
    """

    payload = payload or {}

    if section_name not in DEFAULT_SECTIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported manuscript section: {section_name}"
            ),
        )

    selected_paper_ids = payload.get(
        "selected_paper_ids"
    )

    if selected_paper_ids is not None and not isinstance(
        selected_paper_ids,
        list,
    ):
        raise HTTPException(
            status_code=400,
            detail="selected_paper_ids must be a list of paper IDs.",
        )

    context = _build_project_context(
        project_id=project_id,
        db=db,
        selected_paper_ids=selected_paper_ids,
    )

    project = context["project"]
    literature = context["literature"]

    manuscript = (
        db.query(Manuscript)
        .filter(
            Manuscript.project_id == project_id
        )
        .first()
    )

    sections = (
        _normalize_sections(
            manuscript.sections
        )
        if manuscript
        else dict(DEFAULT_SECTIONS)
    )

    current_title = (
        manuscript.title
        if manuscript
        else ""
    )

    current_abstract = (
        manuscript.abstract
        if manuscript
        else ""
    )

    current_section = (
        sections.get(section_name)
        or ""
    )

    instruction = str(
        payload.get(
            "instruction",
            "",
        )
    ).strip()

    section_rules = {
        "title": """
Generate a concise research-paper title using only the project
context. Do not claim results or novelty that are not established.
""",
        "abstract": """
Write a structured academic abstract from available evidence.
Include results only if actual project results are available.
Otherwise explicitly state that results are not yet available.
""",
        "introduction": """
Write a publication-style introduction in 4-6 coherent paragraphs.
Start from the real application/problem in the project, explain why
the problem matters, summarize only the most relevant prior work,
identify an evidence-supported research need, and end with the
project's stated objective or a clearly marked proposed objective.
Do not write generic filler such as "in today's world".
""",
        "background_related_work": """
Summarize relevant background and related work using the supplied
saved literature. Distinguish paper-reported facts from synthesis.
""",
        "problem_statement": """
Write a precise academic problem statement in 1-3 paragraphs.
Use the project title and description as the primary source and use
relevant literature only to support the existence/nature of the
problem. Clearly distinguish established facts from a proposed
research direction. Do not invent statistics or performance claims.
""",
        "research_objectives": """
Produce 3-5 concise, actionable research objectives derived from the
project description and evidence. If the database does not explicitly
store objectives, present these as proposed research objectives rather
than completed facts.
""",
        "research_questions": """
Produce 2-4 focused research questions derived from the project's
problem and evidence. If they are not stored, present them as
proposed research questions, not as previously approved facts.
""",
        "literature_review": """
Write a connected literature review, not a list of paper summaries.
Group the supplied relevant papers by approach/theme, compare their
reported methods and limitations, and identify what the literature
does and does not establish. Use only the supplied metadata/abstract/
document evidence and cite papers in simple author-year form only when
the author/year metadata is available.
""",
        "research_gap": """
Describe only evidence-supported gap signals. A repeated limitation
or difference across papers is a candidate research direction, not
proof of novelty.
""",
        "methodology": """
Describe only methodology information actually stored in the project,
manuscript, or supplied literature evidence. Never invent datasets,
architectures, hyperparameters, preprocessing, hardware, or metrics.
""",
        "dataset_data_collection": """
Describe only explicit dataset or data-collection information found
in the project evidence or literature. If unavailable, say so.
""",
        "proposed_method_system": """
Describe the proposed system only from stored project/manuscript
information. Do not invent implementation details.
""",
        "experimental_setup": """
Describe only actual stored experimental setup information. Do not
invent hardware, train/test splits, hyperparameters, or evaluation
settings.
""",
        "results": """
Use only actual project results that are stored in the manuscript or
project evidence. Never invent accuracy, precision, recall, F1, mAP,
loss, counts, percentages, or other numerical results. If results
are unavailable, explicitly say:
"Experimental results are not available in the current project evidence."
""",
        "discussion": """
Interpret actual available project results and compare them with
relevant literature only where the evidence supports that comparison.
If results are unavailable, state what cannot yet be concluded.
""",
        "limitations": """
List limitations supported by the project or literature evidence.
Clearly distinguish project limitations from limitations reported
by prior papers.
""",
        "conclusion": """
Summarize only conclusions supported by the current project evidence.
Do not present planned work or unperformed experiments as completed.
""",
        "future_work": """
Provide clearly labeled recommendations based on evidence-supported
limitations or gaps. Recommendations are not established facts.
""",
        "references": """
List references only from supplied saved-paper metadata. Do not
invent authors, DOI, journals, years, or publication details.
""",
    }

    rules = section_rules.get(
        section_name,
        """
Write this academic section using only the available project
context and evidence.
""",
    )

    paper_blocks = []

    for index, paper in enumerate(
        literature,
        start=1,
    ):
        paper_blocks.append(
            f"""
PAPER {index}
Database Paper ID: {paper["paper_id"]}
Title: {paper["title"]}
Year: {paper["year"] or "Year unavailable"}
Authors: {paper["authors"] or "Authors unavailable"}
DOI: {paper["doi"] or "DOI unavailable"}

ABSTRACT:
{paper["abstract"] or "Abstract unavailable"}

DOCUMENT-DERIVED EVIDENCE:
{
    paper["document_evidence"]
    or "No PDF/document-derived evidence is available."
}

RETRIEVAL NOTE:
{paper["retrieval_note"]}

RELEVANCE SIGNAL:
{paper["relevance_signal"]}
"""
        )

    literature_context = (
        "\n".join(paper_blocks)
        if paper_blocks
        else "No saved literature is available for this project."
    )

    prompt = f"""
You are ResearchMate AI, an academic research-writing assistant.

Generate ONLY the requested manuscript section.

============================================================
SELECTED RESEARCH PROJECT
============================================================

Project ID:
{project["id"]}

Project Title:
{project["title"]}

Research Field:
{project["research_field"] or "Not stored"}

Project Description:
{project["description"] or "Not stored"}

============================================================
TARGET SECTION
============================================================

Section:
{section_name}

Section-specific requirements:
{rules}

============================================================
CURRENT MANUSCRIPT CONTEXT
============================================================

Current title:
{current_title or "Not written"}

Current abstract:
{current_abstract or "Not written"}

Current {section_name} text:
{current_section or "Not written"}

============================================================
SAVED PROJECT LITERATURE
============================================================

{literature_context}

============================================================
USER INSTRUCTION
============================================================

{instruction or "Generate a clear academic draft for this section."}

============================================================
NON-NEGOTIABLE EVIDENCE RULES
============================================================

1. Use ONLY the selected research project and its project-scoped
   literature supplied above.

2. Never use knowledge from another ResearchMate project.

3. Never fabricate papers, authors, DOI, journals, datasets,
   experimental results, numerical values, metrics, sample sizes,
   citations, or publication facts.

4. Database metadata is not experimental evidence.

5. A literature abstract is evidence only for claims actually
   stated in that abstract.

6. Document-derived evidence may be used only for information
   actually present in extracted document text.

7. AI inference must not be presented as a measured research result.

8. Research gaps are candidate/evidence-supported signals,
   never guaranteed novelty.

9. For Results, use only actual stored project results.
   If unavailable, say that experimental results are unavailable.

10. For Methodology, do not invent implementation details.

11. If the database lacks an explicit project field such as
    objectives or research questions, you may derive a PROPOSED
    version from the project description and evidence, but label it
    as proposed rather than completed/approved fact.

12. Prefer concrete, project-specific writing over generic academic
    filler. Use the exact project terminology.

13. Return ONLY the manuscript text. Do not return JSON, markdown
    fences, explanations, or a preface.
"""

    ai_error = None
    try:
        generated = generate_text(
            prompt,
            temperature=0.15,
        )
    except Exception as exc:
        generated = ""
        ai_error = str(exc)

    generated = (generated or "").strip()

    # Never leave the editor blank just because the external LLM is
    # temporarily unavailable. The fallback is deliberately factual:
    # it uses only the stored project fields and supplied literature.
    # It is a draft scaffold, not invented research evidence.
    if not generated:
        title = project["title"] or "the research topic"
        field = project["research_field"] or "the stated research field"
        description = project["description"] or "No detailed project description is stored."
        paper_titles = [item["title"] for item in literature if item.get("title")]

        if section_name == "introduction":
            generated = (
                f"{title} is a research project in {field}. The project description states: {description}. "
                "The study is positioned around the problem and research direction defined by this project. "
                "The available project literature provides the documented background for framing the problem and "
                "identifying areas that require further investigation. "
                "Based on the current stored evidence, the proposed study should focus on addressing the stated "
                "research problem while avoiding claims that have not yet been experimentally established. "
                "The objectives, methodology, and evaluation should therefore be defined and validated as part of "
                "the subsequent research process."
            )
        elif section_name == "problem_statement":
            generated = (
                f"The research problem addressed by the project titled '{title}' is defined by the following stored "
                f"project description: {description}. The available evidence indicates that this problem requires a "
                "systematic research approach within the stated domain. However, the current project record does not "
                "contain experimental results that would justify quantitative performance claims. The problem should "
                "therefore be investigated using a reproducible methodology and evidence-based evaluation."
            )
        elif section_name == "research_objectives":
            generated = (
                "Proposed research objectives:\n"
                f"1. Define the research problem and scope for {title}.\n"
                "2. Review and synthesize relevant existing research identified for the project.\n"
                "3. Develop a research methodology appropriate to the stated problem and available evidence.\n"
                "4. Evaluate the proposed approach using explicitly defined and reproducible criteria.\n"
                "5. Document limitations and evidence-supported directions for future work."
            )
        elif section_name == "research_questions":
            generated = (
                "Proposed research questions:\n"
                f"1. What are the main research challenges associated with {title}?\n"
                "2. What approaches have been reported in the relevant project literature?\n"
                "3. What limitations or unresolved issues are identified by the available evidence?\n"
                "4. How can a reproducible research approach address the identified problem without relying on unsupported claims?"
            )
        elif section_name == "literature_review":
            if paper_titles:
                bullets = "\n".join(f"- {t}" for t in paper_titles)
                generated = (
                    "The literature currently saved for this research project provides the evidence base for the review. "
                    "The relevant papers identified by the project-scoped retrieval process are:\n" + bullets + "\n\n"
                    "These papers should be compared by their problem setting, methods, evidence, and reported limitations. "
                    "The current manuscript should not infer experimental findings beyond the information stored in the "
                    "paper metadata, abstracts, or document-derived analysis."
                )
            else:
                generated = "No project-scoped literature has been saved yet. A literature review should be generated after relevant papers are retrieved and saved under this research project."
        elif section_name == "research_gap":
            generated = (
                "The current project evidence does not by itself establish a novel research gap. The literature should "
                "be compared for repeated limitations, unresolved problems, methodological differences, and missing "
                "evaluation evidence. Any resulting gap should be stated as an evidence-supported research direction "
                "rather than as a guaranteed claim of novelty."
            )
        elif section_name == "methodology":
            generated = (
                f"The methodology for '{title}' should be designed around the stated research problem: {description}. "
                "The current project record does not contain enough validated implementation detail to specify a "
                "complete experimental protocol. Therefore, the final methodology should document the data source, "
                "preprocessing, proposed method, experimental design, evaluation criteria, and reproducibility details "
                "once they are explicitly defined and validated."
            )
        elif section_name == "references":
            if paper_titles:
                generated = "Project-scoped references available from stored metadata:\n" + "\n".join(
                    f"{i}. {t}" for i, t in enumerate(paper_titles, 1)
                )
            else:
                generated = "No project-scoped references are currently available."
        elif section_name == "results":
            generated = "Experimental results are not available in the current project evidence."
        elif section_name == "discussion":
            generated = "A substantive discussion cannot be established until validated experimental results are available. The current evidence can be used to discuss the research problem and prior work, but not to claim measured outcomes."
        elif section_name == "conclusion":
            generated = (
                f"The project '{title}' defines a research direction in {field}. At the current stage, the stored "
                "evidence supports formulation of the research problem and planning of the investigation, but does not "
                "support claims about completed experiments or measured performance."
            )
        elif section_name == "future_work":
            generated = "Future work should validate the proposed methodology experimentally, document reproducible evaluation evidence, compare the approach with relevant baselines, and address limitations identified during the research process."
        elif section_name == "limitations":
            generated = "Current limitations include the information that is explicitly available in the project record and saved literature. Experimental limitations, dataset limitations, and performance limitations should be added only after they are observed and documented."
        else:
            generated = (
                f"Draft for {section_name.replace('_', ' ').title()} based on the stored project context for '{title}'. "
                "The section should be completed using validated project-specific evidence and should not introduce unsupported facts or numerical claims."
            )

    response_note = (
        "AI-generated draft grounded in project-scoped evidence."
        if not ai_error
        else "Deterministic evidence-only fallback draft was used because the configured AI service did not return content. Check the Gemini configuration before final publication."
    )

    return {
        "success": True,
        "project_id": project_id,
        "section_name": section_name,
        "draft": generated,
        "evidence": {
            "literature_count": context["literature_count"],
            "context_literature_count": context[
                "context_literature_count"
            ],
            "analysed_paper_count": context[
                "analysed_paper_count"
            ],
            "paper_ids": [
                item["paper_id"] for item in literature
            ],
            "evidence_note": (
                "Draft generated only from this project's stored "
                "context and deterministically relevant literature."
            ),
        },
        "generation_mode": "ai" if not ai_error else "deterministic_fallback",
        "evidence_note": response_note + " Review all generated text against the underlying evidence before using it in the final manuscript.",
    }


# ============================================================
# AI WRITING ASSISTANCE
# ============================================================

@router.post(
    "/projects/{project_id}/sections/{section_name}/assist",
    response_model=WritingAssistResponse,
)
def writing_assist(
    project_id: int,
    section_name: str,
    payload: WritingAssistRequest,
    db: Session = Depends(get_db),
):

    _project_or_404(
        project_id,
        db,
    )

    content = payload.content.strip()

    if not content:

        raise HTTPException(
            status_code=400,
            detail=(
                "No section content was provided."
            ),
        )

    service = WritingService()

    try:

        improved = service.assist_section(
            section_name=section_name,
            content=content,
            instruction=payload.instruction,
            mode=payload.mode,
        )

    except Exception:

        return {
            "success": False,
            "section_name": section_name,
            "original_text": content,
            "improved_text": content,
            "evidence_note": (
                "AI analysis is temporarily "
                "unavailable. No AI-generated "
                "change was applied."
            ),
        }

    return {
        "success": True,
        "section_name": section_name,
        "original_text": content,
        "improved_text": improved,
        "evidence_note": (
            "AI-generated writing assistance. "
            "Verify all research claims against "
            "the project evidence before use."
        ),
    }


# ============================================================
# DETERMINISTIC WRITING READINESS
# ============================================================

@router.get(
    "/projects/{project_id}/readiness",
    response_model=WritingReadinessResponse,
)
def writing_readiness(
    project_id: int,
    db: Session = Depends(get_db),
):

    _project_or_404(
        project_id,
        db,
    )

    manuscript = (
        db.query(Manuscript)
        .filter(
            Manuscript.project_id == project_id
        )
        .first()
    )

    if not manuscript:

        raise HTTPException(
            status_code=404,
            detail="Manuscript not found.",
        )

    sections = _normalize_sections(
        manuscript.sections
    )

    required_checks = [
        ("title", bool(manuscript.title.strip())),
        ("abstract", bool(manuscript.abstract.strip())),
        (
            "introduction",
            bool(sections["introduction"].strip()),
        ),
        (
            "literature_review",
            bool(sections["literature_review"].strip()),
        ),
        (
            "research_gap",
            bool(sections["research_gap"].strip()),
        ),
        (
            "methodology",
            bool(sections["methodology"].strip()),
        ),
        (
            "results",
            bool(sections["results"].strip()),
        ),
        (
            "discussion",
            bool(sections["discussion"].strip()),
        ),
        (
            "conclusion",
            bool(sections["conclusion"].strip()),
        ),
        (
            "references",
            bool(sections["references"].strip()),
        ),
    ]

    completed = sum(
        1
        for _, complete in required_checks
        if complete
    )

    total = len(required_checks)

    missing_sections = [
        name
        for name, complete in required_checks
        if not complete
    ]

    readiness = round(
        (completed / total) * 100
    ) if total else 0

    word_count = _word_count(
        manuscript.title or "",
        manuscript.abstract or "",
        sections,
    )

    missing_methodology = []

    methodology_text = sections[
        "methodology"
    ].lower()

    for keyword in [
        "dataset",
        "data",
        "preprocessing",
        "model",
        "algorithm",
        "evaluation",
        "metric",
    ]:

        if keyword not in methodology_text:
            missing_methodology.append(
                keyword
            )

    return {
        "project_id": project_id,
        "manuscript_id": manuscript.id,

        "readiness_percentage": readiness,

        "completed_checks": completed,
        "total_checks": total,

        "missing_sections": missing_sections,

        "missing_citations": [],

        "unsupported_claims": [],

        "incomplete_methodology": (
            missing_methodology
        ),

        "missing_results": (
            ["results"]
            if not sections["results"].strip()
            else []
        ),

        "missing_references": (
            not bool(
                sections["references"].strip()
            )
        ),

        "word_count": word_count,
    }


# ============================================================
# EXISTING WRITING ANALYSIS
# ============================================================

@router.post(
    "/projects/{project_id}/papers/{paper_id}/analyze"
)
def analyze_writing(
    project_id: int,
    paper_id: int,
    request: WritingAnalysisRequest,
    db: Session = Depends(get_db),
):

    paper = _paper_or_404(
        project_id,
        paper_id,
        db,
    )

    analysis = (
        db.query(PaperAnalysis)
        .filter(
            PaperAnalysis.literature_paper_id
            == paper_id
        )
        .order_by(
            PaperAnalysis.id.desc()
        )
        .first()
    )

    manuscript = (
        request.manuscript or ""
    ).strip()

    if not manuscript and analysis:
        manuscript = (
            analysis.extracted_text or ""
        )

    if not manuscript:

        raise HTTPException(
            status_code=400,
            detail=(
                "No manuscript text available "
                "for analysis."
            ),
        )

    title = (
        request.title or ""
    ).strip()

    if not title:
        title = paper.title or ""

    abstract = (
        request.abstract or ""
    ).strip()

    manuscript = manuscript[:60000]

    service = WritingService()

    try:

        result = service.analyze_paper(
            title=title,
            abstract=abstract,
            manuscript=manuscript,
        )

    except Exception:

        raise HTTPException(
            status_code=503,
            detail=(
                "AI analysis is temporarily "
                "unavailable."
            ),
        )

    return {
        "project_id": project_id,
        "paper_id": paper_id,
        "paper_title": title,

        **result,
    }