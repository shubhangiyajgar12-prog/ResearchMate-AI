import React, { useEffect, useMemo, useState } from "react";
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
  Upload,
  ExternalLink,
  Database,
  Info,
} from "lucide-react";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8001";

async function apiJson(url, options = {}) {
  let response;

  try {
    response = await fetch(url, options);
  } catch (error) {
    throw new Error(
      `Cannot reach ResearchMate backend at ${API_BASE_URL}. Start FastAPI on port 8001.`,
    );
  }

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
  const visible = findings.filter((finding) => {
    if (mode === "missing") {
      return (
        finding.citation_needed === "yes" &&
        finding.citation_present === "no"
      );
    }

    if (mode === "cited") {
      return finding.citation_present === "yes";
    }

    if (mode === "not-required") {
      return finding.citation_needed === "no";
    }

    return true;
  });

  if (!visible.length) {
    return <div className="om-empty">No findings in this category.</div>;
  }

  return (
    <div className="om-findings">
      {visible.slice(0, 80).map((finding, index) => {
        const citationNeeded = finding.citation_needed === "yes";

        return (
          <div className="om-finding" key={finding.id || index}>
            <div className="om-finding-top">
              <span
                className={
                  citationNeeded ? "om-badge warn" : "om-badge good"
                }
              >
                {citationNeeded ? "Citation needed" : "No citation needed"}
              </span>

              <span className="om-confidence">
                {Math.round((finding.confidence || 0) * 100)}% confidence
              </span>
            </div>

            <p>{finding.claim_text}</p>

            <div className="om-finding-meta">
              <span>
                {finding.claim_type || finding.suggestion_reason || "Analyzed claim"}
              </span>

              {finding.citation_status ? (
                <span>{finding.citation_status}</span>
              ) : null}

              {finding.suggested_source_id ? (
                <span>Suggested source #{finding.suggested_source_id}</span>
              ) : null}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function SourceCard({ source }) {
  const title =
    source.source_title ||
    source.title ||
    "External source";

  const url =
    source.source_url ||
    source.url ||
    source.pdf_url ||
    null;

  const doi =
    source.source_doi ||
    source.doi ||
    null;

  const matches =
    typeof source.total_matches === "number"
      ? source.total_matches
      : null;

  return (
    <div className="om-finding">
      <div className="om-finding-top">
        <span className="om-badge good">
          {source.source_type === "external_full_text"
            ? "Full-text source"
            : source.source_type === "external_metadata"
              ? "Metadata only"
              : source.source_type === "saved_project_paper"
                ? "Saved project paper"
                : "Source"}
        </span>

        {matches !== null ? (
          <span>{matches} textual matches</span>
        ) : null}
      </div>

      <p>{title}</p>

      <div className="om-finding-meta">
        {source.source_provider ? (
          <span>{source.source_provider}</span>
        ) : null}

        {source.source_year || source.year ? (
          <span>{source.source_year || source.year}</span>
        ) : null}

        {doi ? <span>{doi}</span> : null}

        {url ? (
          <a href={url} target="_blank" rel="noreferrer">
            Open source <ExternalLink size={13} />
          </a>
        ) : (
          <span>Source URL unavailable</span>
        )}
      </div>
    </div>
  );
}

function UploadedReport({ report }) {
  const matches = Array.isArray(report?.matches) ? report.matches : [];
  const sources = Array.isArray(report?.sources) ? report.sources : [];

  return (
    <section className="om-result-card">
      <div className="om-result-header">
        <div>
          <span className="om-label">UPLOADED MANUSCRIPT REPORT</span>
          <h2>{report.filename || "Uploaded manuscript"}</h2>
        </div>

        <span className={`om-risk ${report.risk_level || "minimal"}`}>
          {report.risk_level || "reported"}
        </span>
      </div>

      <div className="om-result-note">
        <Info size={18} />
        <span>
          This is an evidence signal from textual comparison. It is not a
          plagiarism verdict. Metadata-only sources are shown for discovery but
          are not used for textual similarity.
        </span>
      </div>

      <div className="om-mini-grid">
        <div>
          <span>Overall textual similarity</span>
          <strong>{report.overall_similarity ?? 0}%</strong>
        </div>

        <div>
          <span>Exact similarity</span>
          <strong>{report.exact_similarity ?? 0}%</strong>
        </div>

        <div>
          <span>Lexical similarity</span>
          <strong>{report.lexical_similarity ?? 0}%</strong>
        </div>

        <div>
          <span>Target chunks</span>
          <strong>{report.target_chunks ?? 0}</strong>
        </div>
      </div>

      <div className="om-mini-grid">
        <div>
          <span>Saved project sources checked</span>
          <strong>{report.saved_project_sources_checked ?? 0}</strong>
        </div>

        <div>
          <span>External candidates</span>
          <strong>{report.external_candidates_found ?? 0}</strong>
        </div>

        <div>
          <span>External full-text sources</span>
          <strong>{report.external_full_text_sources ?? 0}</strong>
        </div>

        <div>
          <span>Metadata-only sources</span>
          <strong>{report.external_metadata_only_sources ?? 0}</strong>
        </div>
      </div>

      {matches.length > 0 ? (
        <>
          <div className="om-tabs">
            <div className="om-tab-title">
              <Search size={16} />
              Matched passages
            </div>

            <div className="om-findings">
              {matches.slice(0, 80).map((match, index) => (
                <div className="om-finding" key={match.id || index}>
                  <div className="om-finding-top">
                    <span className="om-badge warn">
                      {match.match_type || "match"}
                    </span>

                    <span>{match.similarity_score ?? 0}%</span>
                  </div>

                  <p>
                    {match.matched_text || "Matched passage unavailable."}
                  </p>

                  <div className="om-finding-meta">
                    <span>
                      {match.source_title ||
                        match.source_provider ||
                        "Source paper"}
                    </span>

                    {match.source_doi ? (
                      <span>{match.source_doi}</span>
                    ) : null}

                    {match.source_url ? (
                      <a
                        href={match.source_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open source <ExternalLink size={13} />
                      </a>
                    ) : null}
                  </div>

                  {match.source_text ? (
                    <details className="om-match-source">
                      <summary>Show source-side passage</summary>
                      <p>{match.source_text}</p>
                    </details>
                  ) : null}
                </div>
              ))}
            </div>
          </div>
        </>
      ) : (
        <div className="om-empty">
          <CheckCircle2 size={18} />
          No textual matches were returned from the checked sources.
        </div>
      )}

      {sources.length > 0 ? (
        <div className="om-tabs">
          <div className="om-tab-title">
            <Database size={16} />
            Sources used for the evidence check
          </div>

          <div className="om-findings">
            {sources.slice(0, 50).map((source, index) => (
              <SourceCard
                source={source}
                key={
                  source.source_provider_id ||
                  source.source_paper_id ||
                  source.source_url ||
                  index
                }
              />
            ))}
          </div>
        </div>
      ) : null}

      {Array.isArray(report.limitations) && report.limitations.length ? (
        <div className="om-result-note">
          <Info size={18} />
          <div>
            {report.limitations.map((item, index) => (
              <div key={index} style={{ marginBottom: 4 }}>
                {item}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}

export default function OriginalityPage() {
  const [papers, setPapers] = useState([]);

  const [projectId, setProjectId] = useState(
    () => Number(localStorage.getItem("researchmate_project_id")) || 0,
  );

  const [paperId, setPaperId] = useState(
    () => Number(localStorage.getItem("researchmate_paper_id")) || 0,
  );

  const [projects, setProjects] = useState([]);
  const [loadingPapers, setLoadingPapers] = useState(true);

  const [similarity, setSimilarity] = useState(null);
  const [citation, setCitation] = useState(null);

  const [uploadedReport, setUploadedReport] = useState(null);
  const [uploadedFile, setUploadedFile] = useState(null);

  const [running, setRunning] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    const loadProjects = async () => {
      try {
        const data = await apiJson(`${API_BASE_URL}/projects/`);
        const list = Array.isArray(data)
          ? data
          : Array.isArray(data?.projects)
            ? data.projects
            : [];

        if (cancelled) return;

        setProjects(list);

        if (!projectId && list.length) {
          setProjectId(Number(list[0].id));
        }
      } catch {
        // Project selector will remain empty; paper loading reports the
        // actionable backend error once a project ID is selected.
      }
    };

    loadProjects();

    return () => {
      cancelled = true;
    };
  }, []);

  const loadPapers = async () => {
    if (!projectId) {
      setPapers([]);
      setLoadingPapers(false);
      return;
    }

    setLoadingPapers(true);
    setError("");

    try {
      const data = await apiJson(
        `${API_BASE_URL}/literature/projects/${projectId}/papers`,
      );

      const list = Array.isArray(data)
        ? data
        : Array.isArray(data?.papers)
          ? data.papers
          : [];

      setPapers(list);

      const selectedIdStillExists = list.some(
        (paper) => Number(paper.id) === Number(paperId),
      );

      if (list.length && !selectedIdStillExists) {
        setPaperId(Number(list[0].id));
      }

      if (!list.length) {
        setPaperId(0);
      }
    } catch (e) {
      setError(e.message);
      setPapers([]);
      setPaperId(0);
    } finally {
      setLoadingPapers(false);
    }
  };

  useEffect(() => {
    if (!projectId) return;

    localStorage.setItem(
      "researchmate_project_id",
      String(projectId),
    );

    setSimilarity(null);
    setCitation(null);
    setUploadedReport(null);

    loadPapers();
  }, [projectId]);

  useEffect(() => {
    if (paperId) {
      localStorage.setItem(
        "researchmate_paper_id",
        String(paperId),
      );
    }
  }, [paperId]);

  const runSimilarity = async () => {
    if (!projectId || !paperId) {
      setError("Select a project and target paper first.");
      return;
    }

    setRunning("similarity");
    setError("");

    try {
      const data = await apiJson(
        `${API_BASE_URL}/originality/projects/${projectId}/analyze`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            project_id: Number(projectId),
            paper_id: Number(paperId),
          }),
        },
      );

      setSimilarity(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning("");
    }
  };

  const runCitation = async () => {
    if (!projectId || !paperId) {
      setError("Select a project and target paper first.");
      return;
    }

    setRunning("citation");
    setError("");

    try {
      const data = await apiJson(
        `${API_BASE_URL}/originality/projects/${projectId}/citation-analysis`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            project_id: Number(projectId),
            paper_id: Number(paperId),
          }),
        },
      );

      setCitation(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning("");
    }
  };

  const runBoth = async () => {
    if (!projectId || !paperId) {
      setError("Select a project and target paper first.");
      return;
    }

    setRunning("both");
    setError("");

    try {
      // Keep these sequential. Both operations touch the originality/citation
      // report tables and sequential execution avoids transaction collisions.
      const sim = await apiJson(
        `${API_BASE_URL}/originality/projects/${projectId}/analyze`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            project_id: Number(projectId),
            paper_id: Number(paperId),
          }),
        },
      );

      const cite = await apiJson(
        `${API_BASE_URL}/originality/projects/${projectId}/citation-analysis`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            project_id: Number(projectId),
            paper_id: Number(paperId),
          }),
        },
      );

      setSimilarity(sim);
      setCitation(cite);
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning("");
    }
  };

  const runUploadedCheck = async () => {
    if (!projectId) {
      setError("Select a project before checking an uploaded manuscript.");
      return;
    }

    if (!uploadedFile) {
      setError("Choose a PDF manuscript before running the uploaded check.");
      return;
    }

    if (uploadedFile.type && uploadedFile.type !== "application/pdf") {
      setError("Only PDF manuscripts are supported.");
      return;
    }

    if (uploadedFile.size > 25 * 1024 * 1024) {
      setError("PDF is too large. Maximum allowed size is 25 MB.");
      return;
    }

    setRunning("upload");
    setError("");
    setUploadedReport(null);

    try {
      const formData = new FormData();
      formData.append("file", uploadedFile);

      const data = await apiJson(
        `${API_BASE_URL}/originality/projects/${projectId}/check-upload`,
        {
          method: "POST",
          body: formData,
        },
      );

      setUploadedReport(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning("");
    }
  };

  const selectedPaper = useMemo(
    () =>
      papers.find(
        (paper) => Number(paper.id) === Number(paperId),
      ),
    [papers, paperId],
  );

  const similarityScore = Number(
    similarity?.overall_similarity ?? 0,
  );

  const citationCoverage = Number(
    citation?.citation_coverage ?? 0,
  );

  const missing = Number(
    citation?.potential_missing_citations ?? 0,
  );

  const matches = Number(
    similarity?.total_matches ?? 0,
  );

  const similarityReportId =
    similarity?.id ?? similarity?.report_id ?? "—";

  const citationReportId =
    citation?.report_id ?? citation?.id ?? "—";

  return (
    <div className="workspace-page originality-page">
      <div className="om-page-title">
        <div>
          <div className="eyebrow">ORIGINALITY & CITATIONS</div>

          <h1>Check originality and citation integrity.</h1>

          <p>
            Analyze textual similarity, classify claims, and identify
            citations that may need review before submission.
          </p>
        </div>

        <div className="om-live">
          <span />
          Backend connected
        </div>
      </div>

      <section className="om-control-card">
        <div className="om-control-icon">
          <ShieldCheck size={24} />
        </div>

        <div className="om-control-main">
          <span className="om-label">ACTIVE PROJECT</span>

          <select
            value={projectId}
            onChange={(event) => {
              const nextProjectId = Number(event.target.value);
              setProjectId(nextProjectId);
              setPaperId(0);
            }}
            style={{ marginBottom: 8 }}
          >
            {!projects.length ? (
              <option value={0}>No projects available</option>
            ) : null}

            {projects.map((project) => (
              <option
                key={project.id}
                value={project.id}
              >
                {project.title || `Project #${project.id}`}
              </option>
            ))}
          </select>

          <span className="om-label">TARGET RESEARCH PAPER</span>

          <h2>
            {selectedPaper?.title || "Select an analyzed paper"}
          </h2>

          <select
            value={paperId}
            onChange={(event) => {
              const nextPaperId = Number(event.target.value);
              setPaperId(nextPaperId);
              setSimilarity(null);
              setCitation(null);
              setError("");
            }}
            disabled={loadingPapers || !papers.length}
          >
            {!papers.length ? (
              <option value={0}>
                {loadingPapers
                  ? "Loading analyzed papers..."
                  : "No analyzed papers available"}
              </option>
            ) : null}

            {papers.map((paper) => (
              <option
                value={paper.id}
                key={paper.id}
              >
                #{paper.id} — {paper.title}
              </option>
            ))}
          </select>
        </div>

        <button
          className="om-refresh"
          onClick={loadPapers}
          title="Refresh papers"
          disabled={loadingPapers}
        >
          <RefreshCw
            size={17}
            className={loadingPapers ? "om-spin" : ""}
          />
        </button>
      </section>

      {error ? (
        <div className="om-error">
          <AlertTriangle size={17} />
          <span>{error}</span>
        </div>
      ) : null}

      <div className="om-action-grid">
        <button
          className="om-action"
          onClick={runSimilarity}
          disabled={!!running || !paperId}
        >
          <Search size={19} />

          <div>
            <strong>
              {running === "similarity"
                ? "Analyzing..."
                : "Run Similarity Analysis"}
            </strong>

            <span>
              Textual overlap across analyzed project papers
            </span>
          </div>
        </button>

        <button
          className="om-action"
          onClick={runCitation}
          disabled={!!running || !paperId}
        >
          <Quote size={19} />

          <div>
            <strong>
              {running === "citation"
                ? "Analyzing..."
                : "Run Citation Analysis"}
            </strong>

            <span>
              Classify external claims, own research, and citation needs
            </span>
          </div>
        </button>

        <button
          className="om-action primary"
          onClick={runBoth}
          disabled={!!running || !paperId}
        >
          <Sparkles size={19} />

          <div>
            <strong>
              {running === "both"
                ? "Running both..."
                : "Run Full Originality Check"}
            </strong>

            <span>
              Similarity + citation integrity in one sequential pass
            </span>
          </div>
        </button>
      </div>

      <section
        className="om-control-card"
        style={{ marginTop: 16 }}
      >
        <div className="om-control-icon">
          <Upload size={24} />
        </div>

        <div className="om-control-main">
          <span className="om-label">
            UPLOADED MANUSCRIPT CHECK
          </span>

          <h2>Check a PDF against project + external evidence</h2>

          <p>
            The manuscript is processed as an upload. Discovered external
            sources are separated into full-text and metadata-only evidence.
            Metadata-only sources are not used to calculate textual similarity.
          </p>

          <input
            type="file"
            accept="application/pdf,.pdf"
            onChange={(event) => {
              const file = event.target.files?.[0] || null;
              setUploadedFile(file);
              setUploadedReport(null);
              setError("");
            }}
          />

          {uploadedFile ? (
            <div
              className="om-file-meta"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                marginTop: 10,
                flexWrap: "wrap",
              }}
            >
              <FileText size={16} />

              <span>{uploadedFile.name}</span>

              <span style={{ opacity: 0.65 }}>
                {(uploadedFile.size / 1024 / 1024).toFixed(2)} MB
              </span>
            </div>
          ) : null}
        </div>

        <button
          className="om-refresh"
          onClick={runUploadedCheck}
          disabled={!!running || !uploadedFile || !projectId}
          title="Analyze uploaded manuscript"
        >
          {running === "upload" ? (
            <RefreshCw
              size={17}
              className="om-spin"
            />
          ) : (
            <Upload size={17} />
          )}
        </button>
      </section>

      {(similarity || citation) ? (
        <div className="om-stats-grid">
          <StatCard
            label="Textual similarity"
            value={`${similarityScore}%`}
            hint={
              similarity
                ? "Evidence-based textual result"
                : "Run similarity analysis"
            }
            tone="blue"
          />

          <StatCard
            label="Potential matches"
            value={matches}
            hint="Matched passages detected"
            tone="amber"
          />

          <StatCard
            label="Citation coverage"
            value={`${citationCoverage}%`}
            hint={
              citation
                ? "Required external claims already cited"
                : "Run citation analysis"
            }
            tone="teal"
          />

          <StatCard
            label="Missing citation signals"
            value={missing}
            hint="Potential external claims to review"
            tone="red"
          />
        </div>
      ) : null}

      {similarity ? (
        <section className="om-result-card">
          <div className="om-result-header">
            <div>
              <span className="om-label">
                SIMILARITY REPORT #{similarityReportId}
              </span>

              <h2>Textual similarity findings</h2>
            </div>

            <span
              className={`om-risk ${similarity.risk_level || "minimal"}`}
            >
              {similarity.risk_level || "reported"}
            </span>
          </div>

          <div className="om-result-note">
            <ShieldCheck size={18} />

            <span>
              Similarity is an evidence signal, not a plagiarism verdict.
              Review matched passages and their sources before drawing
              conclusions.
            </span>
          </div>

          <div className="om-mini-grid">
            <div>
              <span>Exact similarity</span>
              <strong>{similarity.exact_similarity ?? 0}%</strong>
            </div>

            <div>
              <span>Lexical similarity</span>
              <strong>{similarity.lexical_similarity ?? 0}%</strong>
            </div>

            <div>
              <span>Sources checked</span>
              <strong>{similarity.sources_checked ?? 0}</strong>
            </div>

            <div>
              <span>Duplicate sources excluded</span>
              <strong>
                {similarity.duplicate_sources_excluded_count ?? 0}
              </strong>
            </div>
          </div>

          <div className="om-result-note">
            <Info size={18} />

            <span>
              Semantic embedding similarity is not available in this build,
              so a semantic score is not presented as an embedding result.
            </span>
          </div>

          {similarity.matches?.length > 0 ? (
            <div className="om-findings">
              {similarity.matches.map((match, index) => (
                <div
                  className="om-finding"
                  key={match.id || index}
                >
                  <div className="om-finding-top">
                    <span className="om-badge warn">
                      {match.match_type || "Match"}
                    </span>

                    <span>
                      {match.similarity_score ?? 0}%
                    </span>
                  </div>

                  <p>
                    {match.matched_text ||
                      "Matched passage unavailable."}
                  </p>

                  <div className="om-finding-meta">
                    <span>
                      {match.source_title ||
                        "Source paper"}
                    </span>

                    {match.source_doi ? (
                      <span>{match.source_doi}</span>
                    ) : null}

                    {match.source_url ? (
                      <a
                        href={match.source_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open source <ExternalLink size={13} />
                      </a>
                    ) : null}
                  </div>

                  {match.source_text ? (
                    <details className="om-match-source">
                      <summary>
                        Show source-side passage
                      </summary>

                      <p>{match.source_text}</p>
                    </details>
                  ) : null}
                </div>
              ))}
            </div>
          ) : (
            <div className="om-empty">
              <CheckCircle2 size={18} />
              No similarity matches were returned.
            </div>
          )}
        </section>
      ) : null}

      {citation ? (
        <section className="om-result-card">
          <div className="om-result-header">
            <div>
              <span className="om-label">
                CITATION REPORT #{citationReportId}
              </span>

              <h2>Citation integrity findings</h2>
            </div>

            <span className="om-coverage">
              {citation.citation_coverage ?? 0}% coverage
            </span>
          </div>

          <div className="om-result-note">
            <Quote size={18} />

            <span>
              Citation coverage counts genuinely citation-required external
              claims. Authors' own methodology/results and inherited technical
              context are not treated as missing external citations.
            </span>
          </div>

          <div className="om-mini-grid">
            <div>
              <span>Claims analyzed</span>
              <strong>{citation.total_claims ?? 0}</strong>
            </div>

            <div>
              <span>Citations detected</span>
              <strong>{citation.citations_present ?? 0}</strong>
            </div>

            <div>
              <span>Required external claims</span>
              <strong>
                {citation.citation_required_claims ?? 0}
              </strong>
            </div>

            <div>
              <span>Own research claims</span>
              <strong>{citation.own_research_claims ?? 0}</strong>
            </div>
          </div>

          <div className="om-mini-grid">
            <div>
              <span>Cited required claims</span>
              <strong>{citation.cited_required_claims ?? 0}</strong>
            </div>

            <div>
              <span>Inherited-context claims</span>
              <strong>
                {citation.inherited_context_claims ?? 0}
              </strong>
            </div>

            <div>
              <span>Ignored artifacts</span>
              <strong>{citation.ignored_artifacts ?? 0}</strong>
            </div>

            <div>
              <span>Risk level</span>
              <strong>{citation.risk_level || "reported"}</strong>
            </div>
          </div>

          <div className="om-tabs">
            <div className="om-tab-title">
              <AlertTriangle size={16} />
              Claims needing citation review
            </div>

            <FindingsList
              findings={citation.findings}
              mode="missing"
            />
          </div>

          <div className="om-tabs">
            <div className="om-tab-title">
              <CheckCircle2 size={16} />
              Claims where a citation was detected
            </div>

            <FindingsList
              findings={citation.findings}
              mode="cited"
            />
          </div>

          <div className="om-tabs">
            <div className="om-tab-title">
              <Info size={16} />
              Claims not independently requiring a citation
            </div>

            <FindingsList
              findings={citation.findings}
              mode="not-required"
            />
          </div>
        </section>
      ) : null}

      {uploadedReport ? (
        <UploadedReport report={uploadedReport} />
      ) : null}

      {!similarity && !citation && !uploadedReport && !running ? (
        <div className="om-empty-start">
          <div className="om-empty-icon">
            <FileText size={28} />
          </div>

          <h2>Choose a paper and run an analysis</h2>

          <p>
            Start with the full check to populate this workspace with real
            backend results from your ResearchMate project.
          </p>

          <div className="om-pipeline">
            <span>
              <CheckCircle2 size={14} />
              Select paper
            </span>

            <span>→</span>

            <span>
              <CheckCircle2 size={14} />
              Analyze similarity
            </span>

            <span>→</span>

            <span>
              <CheckCircle2 size={14} />
              Classify citations
            </span>

            <span>→</span>

            <span>
              <CheckCircle2 size={14} />
              Review evidence
            </span>
          </div>
        </div>
      ) : null}

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
