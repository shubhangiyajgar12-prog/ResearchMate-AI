import React, { useEffect, useState } from "react";
import "./originality_module.css";
import {
  ShieldCheck,
  FileText,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  Search,
  Quote,
  RefreshCw,
} from "lucide-react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8001";

async function apiJson(url, options = {}) {
  const response = await fetch(url, options);
  const type = response.headers.get("content-type") || "";
  const data = type.includes("application/json")
    ? await response.json()
    : { detail: await response.text() };

  if (!response.ok) {
    const message =
      typeof data?.detail === "string"
        ? data.detail
        : Array.isArray(data?.detail)
        ? data.detail.map((x) => x.msg || String(x)).join(", ")
        : "Request failed.";
    throw new Error(message);
  }
  return data;
}

function StatCard({ label, value, hint, tone = "blue" }) {
  return (
    <div className={`om-stat om-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{hint}</small>
    </div>
  );
}

function FindingsList({ findings = [], mode }) {
  const visible = findings.filter((f) => {
    if (mode === "missing") return f.citation_needed === "yes" && f.citation_present === "no";
    if (mode === "cited") return f.citation_present === "yes";
    return true;
  });

  if (!visible.length) {
    return <div className="om-empty">No findings in this category.</div>;
  }

  return (
    <div className="om-findings">
      {visible.slice(0, 80).map((finding, index) => (
        <div className="om-finding" key={finding.id || index}>
          <div className="om-finding-top">
            <span className={finding.citation_needed === "yes" ? "om-badge warn" : "om-badge good"}>
              {finding.citation_needed === "yes" ? "Citation needed" : "No citation needed"}
            </span>
            <span className="om-confidence">
              {Math.round((finding.confidence || 0) * 100)}% confidence
            </span>
          </div>
          <p>{finding.claim_text}</p>
          <div className="om-finding-meta">
            <span>{finding.suggestion_reason || "Analyzed claim"}</span>
            {finding.suggested_source_id && (
              <span>Suggested source #{finding.suggested_source_id}</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function OriginalityPage() {
  const [papers, setPapers] = useState([]);
  const [projectId, setProjectId] = useState(() => Number(localStorage.getItem("researchmate_project_id")) || 0);
  const [paperId, setPaperId] = useState(() => Number(localStorage.getItem("researchmate_paper_id")) || 0);
  const [loadingPapers, setLoadingPapers] = useState(true);
  const [similarity, setSimilarity] = useState(null);
  const [citation, setCitation] = useState(null);
  const [running, setRunning] = useState("");
  const [error, setError] = useState("");
  const [projects, setProjects] = useState([]);
  useEffect(() => { fetch(`${API_BASE_URL}/projects/`).then(r=>r.json()).then(d=>{setProjects(d); if(!projectId && d[0]) setProjectId(d[0].id)}).catch(()=>{}); }, []);

  const loadPapers = async () => {
    setLoadingPapers(true);
    setError("");
    try {
      const data = await apiJson(
        `${API_BASE_URL}/literature/projects/${projectId}/papers`
      );
      const list = Array.isArray(data) ? data : [];
      setPapers(list);
      if (list.length && !list.some((p) => p.id === paperId)) {
        setPaperId(list[0].id);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoadingPapers(false);
    }
  };

  useEffect(() => {
    if (projectId) { localStorage.setItem("researchmate_project_id", String(projectId)); loadPapers(); }
  }, [projectId]);

  const runSimilarity = async () => {
    setRunning("similarity");
    setError("");
    try {
      const data = await apiJson(
        `${API_BASE_URL}/originality/projects/${projectId}/analyze`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            project_id: projectId,
            paper_id: Number(paperId),
          }),
        }
      );
      setSimilarity(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning("");
    }
  };

  const runCitation = async () => {
    setRunning("citation");
    setError("");
    try {
      const data = await apiJson(
        `${API_BASE_URL}/originality/projects/${projectId}/citation-analysis`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            project_id: projectId,
            paper_id: Number(paperId),
          }),
        }
      );
      setCitation(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning("");
    }
  };

  const runBoth = async () => {
    setRunning("both");
    setError("");
    try {
      const [sim, cite] = await Promise.all([
        apiJson(`${API_BASE_URL}/originality/projects/${projectId}/analyze`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ project_id: projectId, paper_id: Number(paperId) }),
        }),
        apiJson(
          `${API_BASE_URL}/originality/projects/${projectId}/citation-analysis`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ project_id: projectId, paper_id: Number(paperId) }),
          }
        ),
      ]);
      setSimilarity(sim);
      setCitation(cite);
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning("");
    }
  };

  const selectedPaper = papers.find((p) => p.id === Number(paperId));
  const similarityScore = similarity?.overall_similarity ?? 0;
  const citationCoverage = citation?.citation_coverage ?? 0;
  const missing = citation?.potential_missing_citations ?? 0;
  const matches = similarity?.total_matches ?? 0;

  return (
    <div className="workspace-page originality-page">
      <div className="om-page-title">
        <div>
          <div className="eyebrow">ORIGINALITY & CITATIONS</div>
          <h1>Check originality and citation integrity.</h1>
          <p>
            Analyze textual similarity and identify claims that may need
            supporting citations before submission.
          </p>
        </div>
        <div className="om-live"><span /> Backend connected</div>
      </div>

      <section className="om-control-card">
        <div className="om-control-icon"><ShieldCheck size={24} /></div>
        <div className="om-control-main">
          <span className="om-label">ACTIVE PROJECT</span><select value={projectId} onChange={e=>setProjectId(Number(e.target.value))} style={{marginBottom:8}}>{projects.map(p=><option key={p.id} value={p.id}>{p.title}</option>)}</select>
          <span className="om-label">TARGET RESEARCH PAPER</span>
          <h2>{selectedPaper?.title || "Select an analyzed paper"}</h2>
          <select
            value={paperId}
            onChange={(e) => {
              setPaperId(Number(e.target.value));
              setSimilarity(null);
              setCitation(null);
            }}
            disabled={loadingPapers || !papers.length}
          >
            {papers.map((paper) => (
              <option value={paper.id} key={paper.id}>
                #{paper.id} — {paper.title}
              </option>
            ))}
          </select>
        </div>
        <button className="om-refresh" onClick={loadPapers} title="Refresh papers">
          <RefreshCw size={17} />
        </button>
      </section>

      {error && (
        <div className="om-error">
          <AlertTriangle size={17} />
          <span>{error}</span>
        </div>
      )}

      <div className="om-action-grid">
        <button className="om-action" onClick={runSimilarity} disabled={!!running || !paperId}>
          <Search size={19} />
          <div>
            <strong>{running === "similarity" ? "Analyzing..." : "Run Similarity Analysis"}</strong>
            <span>Textual overlap across analyzed project papers</span>
          </div>
        </button>
        <button className="om-action" onClick={runCitation} disabled={!!running || !paperId}>
          <Quote size={19} />
          <div>
            <strong>{running === "citation" ? "Analyzing..." : "Run Citation Analysis"}</strong>
            <span>Find claims that may need supporting citations</span>
          </div>
        </button>
        <button className="om-action primary" onClick={runBoth} disabled={!!running || !paperId}>
          <Sparkles size={19} />
          <div>
            <strong>{running === "both" ? "Running both..." : "Run Full Originality Check"}</strong>
            <span>Similarity + citation integrity in one pass</span>
          </div>
        </button>
      </div>

      {(similarity || citation) && (
        <div className="om-stats-grid">
          <StatCard label="Textual similarity" value={`${similarityScore}%`} hint={similarity ? "Lexical similarity result" : "Run similarity analysis"} tone="blue" />
          <StatCard label="Potential matches" value={matches} hint="Matched passages detected" tone="amber" />
          <StatCard label="Citation coverage" value={`${citationCoverage}%`} hint={citation ? "Required claims already cited" : "Run citation analysis"} tone="teal" />
          <StatCard label="Missing citation signals" value={missing} hint="Potential claims to review" tone="red" />
        </div>
      )}

      {similarity && (
        <section className="om-result-card">
          <div className="om-result-header">
            <div>
              <span className="om-label">SIMILARITY REPORT #{similarity.report_id}</span>
              <h2>Textual similarity findings</h2>
            </div>
            <span className={`om-risk ${similarity.risk_level || "minimal"}`}>
              {similarity.risk_level || "reported"}
            </span>
          </div>

          <div className="om-result-note">
            <ShieldCheck size={18} />
            <span>
              Similarity is an evidence signal, not a plagiarism verdict.
              Review matched passages and their sources before drawing conclusions.
            </span>
          </div>

          <div className="om-mini-grid">
            <div><span>Exact similarity</span><strong>{similarity.exact_similarity ?? 0}%</strong></div>
            <div><span>Semantic similarity</span><strong>{similarity.semantic_similarity ?? 0}%</strong></div>
            <div><span>Total matches</span><strong>{similarity.total_matches ?? 0}</strong></div>
          </div>

          {similarity.matches?.length > 0 ? (
            <div className="om-findings">
              {similarity.matches.map((match, index) => (
                <div className="om-finding" key={match.id || index}>
                  <div className="om-finding-top">
                    <span className="om-badge warn">{match.match_type || "Match"}</span>
                    <span>{match.similarity_score ?? 0}%</span>
                  </div>
                  <p>{match.matched_text || "Matched passage"}</p>
                  <div className="om-finding-meta">
                    <span>{match.source_title || "Source paper"}</span>
                    {match.source_doi && <span>{match.source_doi}</span>}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="om-empty"><CheckCircle2 size={18} /> No similarity matches were returned.</div>
          )}
        </section>
      )}

      {citation && (
        <section className="om-result-card">
          <div className="om-result-header">
            <div>
              <span className="om-label">CITATION REPORT #{citation.report_id}</span>
              <h2>Citation integrity findings</h2>
            </div>
            <span className="om-coverage">{citation.citation_coverage}% coverage</span>
          </div>

          <div className="om-mini-grid">
            <div><span>Claims analyzed</span><strong>{citation.total_claims ?? 0}</strong></div>
            <div><span>Citations detected</span><strong>{citation.citations_present ?? 0}</strong></div>
            <div><span>Potentially missing</span><strong>{citation.potential_missing_citations ?? 0}</strong></div>
          </div>

          <div className="om-tabs">
            <div className="om-tab-title"><AlertTriangle size={16} /> Claims needing citation review</div>
            <FindingsList findings={citation.findings} mode="missing" />
          </div>

          <div className="om-tabs">
            <div className="om-tab-title"><CheckCircle2 size={16} /> Claims where a citation was detected</div>
            <FindingsList findings={citation.findings} mode="cited" />
          </div>
        </section>
      )}

      {!similarity && !citation && !running && (
        <div className="om-empty-start">
          <div className="om-empty-icon"><FileText size={28} /></div>
          <h2>Choose a paper and run an analysis</h2>
          <p>
            Start with the full check to populate this workspace with real
            backend results from your ResearchMate project.
          </p>
          <div className="om-pipeline">
            <span><CheckCircle2 size={14} /> Select paper</span>
            <span>→</span>
            <span><CheckCircle2 size={14} /> Analyze similarity</span>
            <span>→</span>
            <span><CheckCircle2 size={14} /> Check citations</span>
            <span>→</span>
            <span><CheckCircle2 size={14} /> Review evidence</span>
          </div>
        </div>
      )}

      <div className="om-disclaimer">
        <ShieldCheck size={16} />
        <span>
          ResearchMate reports similarity and citation-risk signals for
          academic review. It does not certify plagiarism status or guarantee
          publication outcomes.
        </span>
      </div>
    </div>
  );
}
