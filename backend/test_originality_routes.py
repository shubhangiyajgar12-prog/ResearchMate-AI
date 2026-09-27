"""Read-only structural smoke test for the Originality & Citations module."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]

checks = {
    "similarity router": ROOT / "similarity_router.py",
    "citation router": ROOT / "citation_router.py",
    "frontend": ROOT / "OriginalityPage_FIXED.jsx",
}

for name, path in checks.items():
    assert path.exists(), f"Missing {name}: {path}"

similarity = checks["similarity router"].read_text(encoding="utf-8")
citation = checks["citation router"].read_text(encoding="utf-8")
frontend = checks["frontend"].read_text(encoding="utf-8")

required_similarity = [
    'LiteraturePaper.project_id == project_id',
    'PaperAnalysis.project_id\n                == project_id',
    '"/projects/{project_id}/analyze"',
    '"/projects/{project_id}/analysis"',
    '"/projects/{project_id}/similarity"',
]
required_citation = [
    'LiteraturePaper.project_id == project_id',
    '"/projects/{project_id}/citation-analysis"',
    '"/projects/{project_id}/citations"',
    'CitationAnalysis.report_id == report.id',
]
required_frontend = [
    '/originality/projects/${projectId}/analyze',
    '/originality/projects/${projectId}/citation-analysis',
    '/originality/projects/${projectId}/check-upload',
    '/originality/projects/${projectId}/analysis?paper_id=${paperId}',
    '/originality/projects/${projectId}/citations?paper_id=${paperId}',
]

for item in required_similarity:
    assert item in similarity, f"Similarity requirement missing: {item}"
for item in required_citation:
    assert item in citation, f"Citation requirement missing: {item}"
for item in required_frontend:
    assert item in frontend, f"Frontend requirement missing: {item}"

print('Originality module structural smoke test: PASS')
