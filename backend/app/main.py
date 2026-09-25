from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

# ============================================================
# API MODULES
# ============================================================

from app.api import reviewer
from app.api import improvement
from app.api import writing
from app.api import agents
from app.api import publication

from app.api.conferences.router import (
    router as conference_router
)

from app.api.notifications.router import (
    router as notification_router
)


# ============================================================
# DATABASE
# ============================================================

from app.database.database import engine, Base


# ============================================================
# MODELS
# ============================================================

from app.models.research_project import ResearchProject
from app.models.literature_paper import LiteraturePaper
from app.models.paper_analysis import PaperAnalysis

from app.models.originality_reports import OriginalityReport
from app.models.similarity_match import SimilarityMatch
from app.models.citation_analysis import CitationAnalysis

from app.models.conference import (
    Conference,
    ConferenceSource
)

from app.models.notification import Notification


# ============================================================
# ORIGINALITY ROUTERS
# ============================================================

from app.api.originality.similarity import (
    router as originality_router
)

from app.api.originality.citation import (
    router as citation_router
)

from app.api.originality.uploaded_manuscript import (
    router as uploaded_manuscript_router
)


# ============================================================
# OTHER ROUTERS
# ============================================================

# ------------------------------------------------------------
# Research Projects
# ------------------------------------------------------------

from app.api.projects import (
    router as project_router
)


# ------------------------------------------------------------
# Research Discovery
# ------------------------------------------------------------

from app.api.discovery.topics import (
    router as discovery_router
)


# ------------------------------------------------------------
# Literature Search
# ------------------------------------------------------------

from app.api.literature.papers import (
    router as literature_router
)


# ------------------------------------------------------------
# PDF Analysis
# ------------------------------------------------------------

from app.api.literature.pdf import (
    router as pdf_router
)


# ------------------------------------------------------------
# AI Paper Insights
# ------------------------------------------------------------

from app.api.literature.paper_insights import (
    router as paper_insights_router
)


# ------------------------------------------------------------
# Literature Matrix
# ------------------------------------------------------------

from app.api.literature.literature_matrix import (
    router as literature_matrix_router
)


# ------------------------------------------------------------
# Saved Paper PDF Analysis
# ------------------------------------------------------------

from app.api.literature.paper_analysis import (
    router as paper_analysis_router
)


# ------------------------------------------------------------
# Research Gap Engine
# ------------------------------------------------------------

from app.api.literature.research_gap import (
    router as research_gap_router
)


# ============================================================
# CREATE DATABASE TABLES
# ============================================================

Base.metadata.create_all(
    bind=engine
)


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="ResearchMate AI API",
    description="AI-powered Research Publication Assistant",
    version="1.0.0"
)


# ============================================================
# CORS CONFIGURATION
# ============================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],

    # Vite may move to 5175/5176/... when another dev server is using
    # the default port. Allow localhost development ports without
    # opening cross-origin access to arbitrary external sites.
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1):\d+$",

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# ============================================================
# INCLUDE CORE ROUTERS
# ============================================================

# ------------------------------------------------------------
# Improvement
# ------------------------------------------------------------

app.include_router(
    improvement.router
)


# ------------------------------------------------------------
# AI Agents
# ------------------------------------------------------------

app.include_router(
    agents.router
)


# ------------------------------------------------------------
# Conferences
# ------------------------------------------------------------

app.include_router(
    conference_router
)


# ------------------------------------------------------------
# Notifications
# ------------------------------------------------------------

app.include_router(
    notification_router
)


# ------------------------------------------------------------
# Publication
# ------------------------------------------------------------
# IMPORTANT:
# publication.router is included only ONCE.
# Previously it was included twice, which caused duplicate
# OpenAPI operation IDs in Swagger.

app.include_router(
    publication.router
)


# ------------------------------------------------------------
# Writing
# ------------------------------------------------------------

app.include_router(
    writing.router
)


# ------------------------------------------------------------
# Reviewer
# ------------------------------------------------------------

app.include_router(
    reviewer.router
)


# ============================================================
# ORIGINALITY
# ============================================================

# ------------------------------------------------------------
# Originality - Saved Paper Similarity
# ------------------------------------------------------------

app.include_router(
    originality_router
)


# ------------------------------------------------------------
# Originality - Citation Analysis
# ------------------------------------------------------------

app.include_router(
    citation_router
)


# ------------------------------------------------------------
# Originality - Uploaded Manuscript
# ------------------------------------------------------------

app.include_router(
    uploaded_manuscript_router
)


# ============================================================
# RESEARCH PROJECTS
# ============================================================

app.include_router(
    project_router
)


# ============================================================
# RESEARCH DISCOVERY
# ============================================================

app.include_router(
    discovery_router
)


# ============================================================
# LITERATURE
# ============================================================

# ------------------------------------------------------------
# Literature Search
# ------------------------------------------------------------

app.include_router(
    literature_router
)


# ------------------------------------------------------------
# PDF Analysis
# ------------------------------------------------------------

app.include_router(
    pdf_router
)


# ------------------------------------------------------------
# AI Paper Insights
# ------------------------------------------------------------

app.include_router(
    paper_insights_router
)


# ------------------------------------------------------------
# Saved Paper PDF Analysis
# ------------------------------------------------------------

app.include_router(
    paper_analysis_router
)


# ------------------------------------------------------------
# Literature Matrix
# ------------------------------------------------------------

app.include_router(
    literature_matrix_router
)


# ------------------------------------------------------------
# Research Gap Engine
# ------------------------------------------------------------

app.include_router(
    research_gap_router
)


# ============================================================
# ROOT ENDPOINT
# ============================================================

@app.get("/")
def root():
    return {
        "message": "ResearchMate AI Backend is running!",
        "status": "success"
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "ResearchMate AI API",
        "features": [
            "rag",
            "multi-agent",
            "conference-intelligence",
            "notifications",
            "originality",
            "citation-analysis"
        ]
    }


# ============================================================
# DATABASE TEST
# ============================================================

@app.get("/db-test")
def database_test():

    try:

        with engine.connect() as connection:

            result = connection.execute(
                text("SELECT 1")
            )

            return {
                "database": "connected",
                "result": result.scalar()
            }

    except Exception as e:

        return {
            "database": "connection failed",
            "error": str(e)
        }