"""
One-time cleanup for polluted Project #4 literature.

Run from:
D:\myproject\ResearchMate-AI\backend

IMPORTANT:
- Stop FastAPI before running.
- Targets ONLY project_id = 4.
- A backup table is created first.
- The previous version of this script stopped before deleting anything
  because citation_analysis uses report_id, not paper_id. This version
  uses the actual schema used by the Originality routers.
"""

from datetime import datetime
from sqlalchemy import text
from app.database.database import engine

PROJECT_ID = 4

REMOVE_IDS = [
    10, 12, 13, 14, 15, 16,
    19, 20, 21, 22, 23, 24, 25,
    26, 27, 28, 29, 30, 31, 32, 33, 34, 35,
    49, 50,
]

with engine.begin() as conn:
    backup_table = f"literature_papers_project4_backup_{datetime.now():%Y%m%d_%H%M%S}"

    # 1. Backup the exact literature rows first.
    conn.execute(
        text(f"""
            CREATE TABLE "{backup_table}" AS
            SELECT *
            FROM literature_papers
            WHERE project_id = :project_id
              AND id = ANY(:paper_ids)
        """),
        {"project_id": PROJECT_ID, "paper_ids": REMOVE_IDS},
    )

    # 2. Remove citation findings through their actual parent report_id.
    conn.execute(
        text("""
            DELETE FROM citation_analysis
            WHERE report_id IN (
                SELECT id
                FROM originality_reports
                WHERE project_id = :project_id
                  AND paper_id = ANY(:paper_ids)
            )
        """),
        {"project_id": PROJECT_ID, "paper_ids": REMOVE_IDS},
    )

    # 3. Remove similarity matches through their actual report_id.
    conn.execute(
        text("""
            DELETE FROM similarity_matches
            WHERE report_id IN (
                SELECT id
                FROM originality_reports
                WHERE project_id = :project_id
                  AND paper_id = ANY(:paper_ids)
            )
        """),
        {"project_id": PROJECT_ID, "paper_ids": REMOVE_IDS},
    )

    # 4. Remove originality reports for those papers.
    conn.execute(
        text("""
            DELETE FROM originality_reports
            WHERE project_id = :project_id
              AND paper_id = ANY(:paper_ids)
        """),
        {"project_id": PROJECT_ID, "paper_ids": REMOVE_IDS},
    )

    # 5. Remove PDF analysis rows belonging to the same project/papers.
    conn.execute(
        text("""
            DELETE FROM paper_analyses
            WHERE project_id = :project_id
              AND literature_paper_id = ANY(:paper_ids)
        """),
        {"project_id": PROJECT_ID, "paper_ids": REMOVE_IDS},
    )

    # 6. Finally remove the clearly unrelated literature rows.
    deleted = conn.execute(
        text("""
            DELETE FROM literature_papers
            WHERE project_id = :project_id
              AND id = ANY(:paper_ids)
        """),
        {"project_id": PROJECT_ID, "paper_ids": REMOVE_IDS},
    )

    print("Cleanup completed successfully.")
    print(f"Project ID: {PROJECT_ID}")
    print(f"Requested paper IDs: {REMOVE_IDS}")
    print(f"Literature rows deleted: {deleted.rowcount}")
    print(f"Backup table: {backup_table}")
    print("Other projects were not modified.")
