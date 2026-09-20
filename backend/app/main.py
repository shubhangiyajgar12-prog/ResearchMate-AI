from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text


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


# ============================================================
# ROUTERS
# ============================================================

# Research Projects
from app.api.projects import (
    router as project_router
)

# Research Discovery
from app.api.discovery.topics import (
    router as discovery_router
)

# Literature Search
from app.api.literature.papers import (
    router as literature_router
)

# PDF Analysis
from app.api.literature.pdf import (
    router as pdf_router
)

# AI Paper Insights
from app.api.literature.paper_insights import (
    router as paper_insights_router
)

# Literature Matrix
from app.api.literature.literature_matrix import (
    router as literature_matrix_router
)

# Saved Paper PDF Analysis
from app.api.literature.paper_analysis import (
    router as paper_analysis_router
)

# Research Gap Engine
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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# INCLUDE ROUTERS
# ============================================================

# ------------------------------------------------------------
# Research Projects
# ------------------------------------------------------------

app.include_router(
    project_router
)


# ------------------------------------------------------------
# Research Discovery
# ------------------------------------------------------------

app.include_router(
    discovery_router
)


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
        "status": "healthy"
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