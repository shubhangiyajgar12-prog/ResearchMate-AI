import React, { useEffect, useMemo, useState } from "react";
import "./originality_module.css";
import {
  AlertTriangle,
  CheckCircle2,
  Database,
  ExternalLink,
  FileText,
  Info,
  Quote,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Upload,
} from "lucide-react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function apiJson(url, options = {}) {
  let response;
  try {
    response = await fetch(url, options);
  } catch {
    throw new Error(`Cannot reach ResearchMate backend at ${API_BASE_URL}. Start FastAPI on port 8000.`);
  }
  const type = response.headers.get("content-type") || "";
  const data = type.includes("application/json") ? await response.json() : { detail: await response.text() };
  if (!response.ok) {
    const detail = data?.detail;
    const message = typeof detail === "string"
      ? detail
      : Array.isArray(detail) ? detail.map((x) => x?.msg || String(x)).join(", ") : "Request failed.";
    throw new Error(message);
  }
  return data;
}

function safeNumber(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function SimilarityReport({ report }) {
  if (!report) return null;
  const matches = Array.isArray(report.matches) ? report.matches : [];
  return (
    <section className="om-result-card">
      <div className="om-result-header">
        <div>
          <span className="om-label">TEXTUAL SIMILARITY</span>
          <h2>{safeNumber(report.overall_similarity).toFixed(2)}% manuscript-word overlap</h2>
          <p>This percentage is the share of manuscript words contained in chunks with a meaningful textual match. It is not a plagiarism or originality verdict.</p>
        </div>
      </div>
      <div className="om-stat-grid">
        <div className="om-stat om-blue"><span>Potential matches</span><strong>{safeNumber(report.total_matches)}</strong><small>Matched target chunks</small></div>
        <div className="om-stat om-blue"><span>Sources compared</span><strong>{safeNumber(report.sources_checked)}</strong><small>Same-project full-text evidence</small></div>
        <div className="om-stat om-blue"><span>Manuscript words</span><strong>{safeNumber(report.target_word_count)}</strong><small>After text validation</small></div>
      </div>
      {matches.length ? (
        <div className="om-findings" style={{ marginTop: 14 }}>
          {matches.slice(0, 50).map((match, index) => (
            <div className="om-finding" key={`${match.source_paper_id}-${match.paper_chunk_id}-${index}`}>
              <div className="om-finding-top">
                <span className="om-badge warn">{safeNumber(match.similarity_score).toFixed(2)}%</span>
                <span className="om-confidence">{match.match_type || "textual match"}</span>
              </div>
              <p><strong>Your manuscript:</strong> {match.matched_text || "No passage returned."}</p>
              <details className="om-match-source">
                <summary>Show source passage</summary>
                <p>{match.source_text || "No source passage returned."}</p>
              </details>
              <div className="om-finding-meta">
                <span>{match.source_title || `Paper #${match.source_paper_id}`}</span>
                {match.source_doi ? <span>DOI: {match.source_doi}</span> : null}
                {match.source_url ? <a href={match.source_url} target="_blank" rel="noreferrer">Open source <ExternalLink size={12} /></a> : null}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="om-empty" style={{ marginTop: 14 }}><CheckCircle2 size={18} /> No meaningful textual overlap was detected in the available project evidence.</div>
      )}
      <div className="om-result-note" style={{ marginTop: 14 }}><Info size={17} /><div>{(report.limitations || []).map((x, i) => <div key={i}>{x}</div>)}</div></div>
    </section>
  );
}

function CitationReport({ report }) {
  if (!report) return null;
  const findings = Array.isArray(report.findings) ? report.findings : [];
  const missing = findings.filter((f) => f.citation_needed === "yes" && f.citation_present === "no");
  return (
    <section className="om-result-card">
      <span className="om-label">CITATION REVIEW</span>
      <h2>{safeNumber(report.potential_missing_citations)} potential citation review flags</h2>
      <div className="om-stat-grid">
        <div className="om-stat om-blue"><span>Claims analyzed</span><strong>{safeNumber(report.total_claims)}</strong><small>Detected research claims</small></div>
        <div className="om-stat om-blue"><span>Required claims</span><strong>{safeNumber(report.citation_required_claims)}</strong><small>Heuristic citation candidates</small></div>
        <div className="om-stat om-green"><span>Required-claim coverage</span><strong>{safeNumber(report.citation_coverage).toFixed(2)}%</strong><small>Cited required claims / required claims</small></div>
      </div>
      {missing.length ? (
        <div className="om-findings" style={{ marginTop: 14 }}>
          {missing.slice(0, 80).map((finding, index) => (
            <div className="om-finding" key={index}>
              <div className="om-finding-top"><span className="om-badge warn">Citation needed</span><span className="om-confidence">{Math.round(safeNumber(finding.confidence) * 100)}% confidence</span></div>
              <p>{finding.claim_text}</p>
              <div className="om-finding-meta"><span>{finding.claim_type || "External / prior research claim"}</span></div>
              {Array.isArray(finding.suggested_sources) && finding.suggested_sources.length ? (
                <div style={{ marginTop: 9 }}><strong>Project evidence candidates</strong>{finding.suggested_sources.slice(0, 3).map((s, i) => <div key={i} style={{ marginTop: 4 }}>• {typeof s === "string" ? s : (s.title || s.source_title || `Paper #${s.paper_id || s.id || "?"}`)}</div>)}</div>
              ) : null}
            </div>
          ))}
        </div>
      ) : (
        <div className="om-empty" style={{ marginTop: 14 }}><CheckCircle2 size={18} /> No citation issues were detected by the current analysis. Review borderline claims manually before submission.</div>
      )}
      <div className="om-result-note" style={{ marginTop: 14 }}><Info size={17} /><div>{(report.limitations || []).map((x, i) => <div key={i}>{x}</div>)}</div></div>
    </section>
  );
}

export default function OriginalityPage() {
  const [projects, setProjects] = useState([]);
  const [projectId, setProjectId] = useState(() => Number(localStorage.getItem("researchmate_project_id")) || 0);
  const [manuscript, setManuscript] = useState(null);
  const [papers, setPapers] = useState([]);
  const [similarity, setSimilarity] = useState(null);
  const [citation, setCitation] = useState(null);
  const [uploadedReport, setUploadedReport] = useState(null);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState("");
  const [error, setError] = useState("");

  const selectedProject = useMemo(() => projects.find((p) => Number(p.id) === Number(projectId)), [projects, projectId]);
  const analyzedPapers = papers.filter((p) => p.analysis_available || p.text_available || p.analyzed || p.analysed);
  const usablePapers = analyzedPapers.length;

  async function loadProjects() {
    const data = await apiJson(`${API_BASE_URL}/projects/`);
    const list = Array.isArray(data) ? data : Array.isArray(data?.projects) ? data.projects : [];
    setProjects(list);
    const valid = list.some((p) => Number(p.id) === Number(projectId));
    if (!valid && list.length) setProjectId(Number(list[0].id));
  }

  async function loadProjectData(id = projectId) {
    if (!id) return;
    setLoading(true);
    setError("");
    setManuscript(null);
    setPapers([]);
    setSimilarity(null);
    setCitation(null);
    setUploadedReport(null);
    setUploadedFile(null);
    localStorage.setItem("researchmate_project_id", String(id));
    localStorage.removeItem("researchmate_paper_id");
    try {
      const [manuscriptData, paperData] = await Promise.all([
        apiJson(`${API_BASE_URL}/writing/projects/${id}/manuscript`).catch((e) => e),
        apiJson(`${API_BASE_URL}/literature/projects/${id}/papers`),
      ]);
      if (manuscriptData instanceof Error) {
        if (!String(manuscriptData.message).toLowerCase().includes("manuscript not found")) throw manuscriptData;
        setManuscript(null);
      } else {
        if (Number(manuscriptData.project_id) !== Number(id)) throw new Error("Backend returned a manuscript from another project.");
        setManuscript(manuscriptData);
      }
      const list = Array.isArray(paperData) ? paperData : Array.isArray(paperData?.papers) ? paperData.papers : [];
      const scoped = list.filter((p) => p.project_id == null || Number(p.project_id) === Number(id));
      setPapers(scoped);
    } catch (e) {
      setError(e.message || "Could not load this project's originality context.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadProjects().catch((e) => setError(e.message)); }, []);
  useEffect(() => { if (projectId) loadProjectData(projectId); }, [projectId]);

  async function runSimilarity() {
    if (!manuscript?.id) return setError("No manuscript is available for this project. Open Research Writing first.");
    setRunning("similarity"); setError("");
    try { setSimilarity(await apiJson(`${API_BASE_URL}/originality/projects/${projectId}/manuscript-similarity`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ project_id: Number(projectId) }) })); }
    catch (e) { setError(e.message); } finally { setRunning(""); }
  }

  async function runCitation() {
    if (!manuscript?.id) return setError("No manuscript is available for this project. Open Research Writing first.");
    setRunning("citation"); setError("");
    try { setCitation(await apiJson(`${API_BASE_URL}/originality/projects/${projectId}/manuscript-citation-analysis`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ project_id: Number(projectId) }) })); }
    catch (e) { setError(e.message); } finally { setRunning(""); }
  }

  async function runFull() {
    if (!manuscript?.id) return setError("No manuscript is available for this project. Open Research Writing first.");
    setRunning("full"); setError("");
    try {
      const data = await apiJson(`${API_BASE_URL}/originality/projects/${projectId}/manuscript-full-check`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ project_id: Number(projectId) }) });
      setSimilarity(data.similarity); setCitation(data.citation);
    } catch (e) { setError(e.message); } finally { setRunning(""); }
  }

  async function runUpload() {
    if (!uploadedFile) return setError("Choose a PDF first.");
    if (!projectId) return setError("Select a project first.");
    setRunning("upload"); setError("");
    try {
      const form = new FormData(); form.append("file", uploadedFile);
      setUploadedReport(await apiJson(`${API_BASE_URL}/originality/projects/${projectId}/check-upload`, { method: "POST", body: form }));
    } catch (e) { setError(e.message); } finally { setRunning(""); }
  }

  return (
    <div className="om-page">
      <section className="om-hero">
        <div className="om-hero-icon"><ShieldCheck size={28} /></div>
        <div><span className="om-label">ORIGINALITY & CITATIONS</span><h1>Evidence-based manuscript verification</h1><p>The manuscript from the active Research Writing project is the target. Saved literature is reference evidence only.</p></div>
      </section>

      <section className="om-control-card" style={{ marginTop: 16 }}>
        <div className="om-control-icon"><Database size={23} /></div>
        <div className="om-control-main">
          <span className="om-label">ACTIVE RESEARCH PROJECT</span>
          <select value={projectId} onChange={(e) => setProjectId(Number(e.target.value))} disabled={!projects.length || loading}>
            {!projects.length ? <option value={0}>No projects available</option> : projects.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
          </select>
          <div style={{ marginTop: 8, opacity: .75 }}>{selectedProject?.research_field || "Project-scoped research context"}</div>
        </div>
        <button className="om-refresh" onClick={() => loadProjectData()} disabled={loading} title="Refresh project context"><RefreshCw size={17} className={loading ? "om-spin" : ""} /></button>
      </section>

      {error ? <div className="om-error"><AlertTriangle size={17} /><span>{error}</span></div> : null}

      <section className="om-control-card" style={{ marginTop: 16 }}>
        <div className="om-control-icon"><FileText size={23} /></div>
        <div className="om-control-main">
          <span className="om-label">CURRENT MANUSCRIPT</span>
          {manuscript ? (
            <><h2>{manuscript.title || "Untitled manuscript"}</h2><p>✓ Project-owned manuscript · ✓ Stored text available · Version {manuscript.current_version || 1} · {safeNumber(manuscript.word_count)} words</p><button type="button" className="om-action" style={{ marginTop: 8 }} onClick={() => { window.location.href = "/writing"; }}><FileText size={17} /><div><strong>Open Writing Workspace</strong><span>Edit or generate the manuscript for this project</span></div></button></>
          ) : (
            <><h2>No manuscript available yet</h2><p>Write or generate the manuscript before running originality analysis.</p><button type="button" className="om-action" style={{ marginTop: 8 }} onClick={() => { window.location.href = "/writing"; }}><FileText size={17} /><div><strong>Go to Research Writing</strong><span>Create the target manuscript for this project</span></div></button></>
          )}
        </div>
      </section>

      <section className="om-control-card" style={{ marginTop: 16 }}>
        <div className="om-control-icon"><Database size={23} /></div>
        <div className="om-control-main">
          <span className="om-label">REFERENCE EVIDENCE</span>
          <h2>{papers.length} saved papers · {analyzedPapers.length} analyzed · {usablePapers} usable full-text sources</h2>
          <p>Only literature belonging to the active project can become evidence. Metadata-only papers are never used for textual similarity.</p>
          {papers.length ? <div className="om-findings" style={{ marginTop: 10 }}>{papers.slice(0, 12).map((p) => <div className="om-finding" key={p.id}><div className="om-finding-top"><span className={`om-badge ${p.analysis_available || p.text_available ? "good" : "warn"}`}>{p.analysis_available || p.text_available ? "Analyzed" : "Saved"}</span><span>Project #{p.project_id ?? projectId}</span></div><p>{p.title}</p></div>)}</div> : <div className="om-empty" style={{ marginTop: 10 }}>No reference literature saved for this project. <button type="button" className="om-link-button" onClick={() => { window.location.href = "/literature"; }}>Go to Literature</button></div>}
        </div>
      </section>

      <div className="om-action-grid" style={{ marginTop: 16 }}>
        <button className="om-action" onClick={runSimilarity} disabled={!!running || !manuscript?.id || !usablePapers}><Search size={19} /><div><strong>{running === "similarity" ? "Analyzing..." : "Run Similarity Analysis"}</strong><span>{usablePapers ? "Compare manuscript text with relevant same-project full text" : "No usable analyzed evidence is available"}</span></div></button>
        <button className="om-action" onClick={runCitation} disabled={!!running || !manuscript?.id}><Quote size={19} /><div><strong>{running === "citation" ? "Analyzing..." : "Run Citation Analysis"}</strong><span>Review claims and citation requirements</span></div></button>
        <button className="om-action primary" onClick={runFull} disabled={!!running || !manuscript?.id}><Sparkles size={19} /><div><strong>{running === "full" ? "Running full check..." : "Run Full Originality Check"}</strong><span>Similarity + citation review against project evidence</span></div></button>
      </div>

      {similarity ? <SimilarityReport report={similarity} /> : null}
      {citation ? <CitationReport report={citation} /> : null}

      <section className="om-control-card" style={{ marginTop: 16 }}>
        <div className="om-control-icon"><Upload size={23} /></div>
        <div className="om-control-main">
          <span className="om-label">FINAL MANUSCRIPT CHECK</span>
          <h2>Upload a final PDF when the Writing manuscript is not the target</h2>
          <p>This upload is temporary. It does not overwrite the saved Writing manuscript.</p>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 10 }}>
            <label className="om-action" style={{ margin: 0, cursor: "pointer" }}><Upload size={17} /><div><strong>Choose PDF</strong><span>{uploadedFile ? uploadedFile.name : "PDF only, max 25 MB"}</span></div><input type="file" accept="application/pdf,.pdf" hidden onChange={(e) => { const f = e.target.files?.[0]; if (!f) return; if ((!f.type || f.type !== "application/pdf") && !f.name.toLowerCase().endsWith(".pdf")) return setError("Only PDF files are supported."); if (f.size > 25 * 1024 * 1024) return setError("PDF is too large. Maximum allowed size is 25 MB."); setUploadedFile(f); setError(""); }} /></label>
            <button className="om-action primary" onClick={runUpload} disabled={!!running || !uploadedFile}><Upload size={17} /><div><strong>{running === "upload" ? "Checking..." : "Run Final Check"}</strong><span>Compare uploaded PDF with project evidence</span></div></button>
          </div>
          {uploadedReport ? <div className="om-result-note" style={{ marginTop: 14 }}><Info size={17} /><div><strong>Uploaded manuscript result</strong><div>{safeNumber(uploadedReport.overall_similarity).toFixed(2)}% textual similarity · {safeNumber(uploadedReport.total_matches)} matches · {safeNumber(uploadedReport.saved_project_sources_checked)} project sources checked</div><div style={{ marginTop: 4 }}>External metadata-only sources are not counted as textual similarity evidence.</div></div></div> : null}
        </div>
      </section>

      <section className="om-result-note" style={{ marginTop: 16 }}><Info size={18} /><div><strong>Important interpretation</strong><div>ResearchMate reports similarity and citation-review evidence. It does not certify plagiarism status, originality, novelty, or publication outcome. Review every highlighted passage and citation before submission.</div></div></section>
    </div>
  );
}
