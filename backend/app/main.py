from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.models.paper_analysis import PaperAnalysis
from app.api.literature.paper_analysis import router as paper_analysis_router
from app.database.database import engine, Base

# Models
from app.models.research_project import ResearchProject
from app.models.literature_paper import LiteraturePaper

# Routers
from app.api.projects import router as project_router
from app.api.discovery.topics import router as discovery_router
from app.api.literature.papers import router as literature_router
from app.api.literature.pdf import router as pdf_router
from app.api.literature.paper_insights import router as paper_insights_router
from app.api.literature.literature_matrix import (
    router as literature_matrix_router
)


# --------------------------------------------------
# Create Database Tables
# --------------------------------------------------

Base.metadata.create_all(bind=engine)


# --------------------------------------------------
# FastAPI Application
# --------------------------------------------------

app = FastAPI(
    title="ResearchMate AI API",
    description="AI-powered Research Publication Assistant",
    version="1.0.0"
)
app.include_router(paper_analysis_router)

# --------------------------------------------------
# CORS Configuration
# --------------------------------------------------

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


# --------------------------------------------------
# Include Routers
# --------------------------------------------------

app.include_router(project_router)

app.include_router(discovery_router)

app.include_router(literature_router)

app.include_router(pdf_router)

app.include_router(paper_insights_router)

# Literature Matrix Router
app.include_router(literature_matrix_router)


# --------------------------------------------------
# Root Endpoint
# --------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "ResearchMate AI Backend is running!",
        "status": "success"
    }


# --------------------------------------------------
# Health Check
# --------------------------------------------------

@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }


# --------------------------------------------------
# Database Test
# --------------------------------------------------

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