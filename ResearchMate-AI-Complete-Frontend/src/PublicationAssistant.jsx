import React, { useMemo, useState } from "react";
import {
  ArrowUpRight,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  CircleAlert,
  ClipboardCheck,
  ExternalLink,
  FileCheck2,
  Filter,
  Globe2,
  Info,
  LayoutGrid,
  Loader2,
  Rocket,
  Search,
  ShieldCheck,
  Sparkles,
  Target,
  XCircle,
} from "lucide-react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8001";

const initialResult = {
  paper_title: "Research manuscript",
  field: "Computer Science / AI & ML",
  readiness_score: null,
  venues: [],
  checklist: [],
  missing_items: [],
  requirements: [],
  deadlines: [],
  risks: [],
  plan: [],
  notes: [],
};

function normalizeArray(value) {
  if (!Array.isArray(value)) return [];
  return value;
}

function scoreTone(score) {
  if (score == null) return "neutral";
  if (score >= 80) return "good";
  if (score >= 60) return "medium";
  return "low";
}

export default function PublicationAssistant() {
  const [activeTab, setActiveTab] = useState("overview");
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("All");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [source, setSource] = useState("local");
  const [result, setResult] = useState(initialResult);
  const [hasAnalyzed, setHasAnalyzed] = useState(false);
  const [projects, setProjects] = useState([]);
  const [papers, setPapers] = useState([]);
  const [projectId, setProjectId] = useState(() => Number(localStorage.getItem("researchmate_project_id")) || 0);
  const [paperId, setPaperId] = useState(() => Number(localStorage.getItem("researchmate_paper_id")) || 0);

  React.useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API_BASE_URL}/projects/`);
        if (!r.ok) throw new Error("Unable to load projects");
        const data = await r.json();
        setProjects(data);
        const pid = projectId || data[0]?.id || 0;
        if (pid) setProjectId(pid);
      } catch (e) { setError(e.message); }
    })();
  }, []);

  React.useEffect(() => {
    if (!projectId) return;
    localStorage.setItem("researchmate_project_id", String(projectId));
    (async () => {
      try {
        const r = await fetch(`${API_BASE_URL}/literature/projects/${projectId}/papers`);
        if (!r.ok) throw new Error("Unable to load papers for this project");
        const data = await r.json();
        setPapers(data);
        const selected = paperId && data.some(p => p.id === paperId) ? paperId : (data[0]?.id || 0);
        setPaperId(selected);
        if (selected) localStorage.setItem("researchmate_paper_id", String(selected));
      } catch (e) { setError(e.message); }
    })();
  }, [projectId]);

  const analyzePublication = async () => {
    setLoading(true);
    setError("");
    if (!projectId || !paperId) { setError("Select a project and paper before running publication analysis."); setLoading(false); return; }

    try {
      const response = await fetch(
        `${API_BASE_URL}/publication/projects/${projectId}/papers/${paperId}/analyze`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        }
      );

      const contentType = response.headers.get("content-type") || "";
      const data = contentType.includes("application/json")
        ? await response.json()
        : { detail: await response.text() };

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Publication analysis endpoint is not available yet."
        );
      }

      setResult({
        ...initialResult,
        ...data,
        venues: normalizeArray(data.venues),
        checklist: normalizeArray(data.checklist),
        missing_items: normalizeArray(data.missing_items),
        requirements: normalizeArray(data.requirements),
        deadlines: normalizeArray(data.deadlines),
        risks: normalizeArray(data.risks),
        plan: normalizeArray(data.plan),
        notes: normalizeArray(data.notes),
      });
      setSource("backend");
      setHasAnalyzed(true);
    } catch (err) {
      console.error(err);
      setError(err.message || "Publication analysis failed. Please check the backend and try again.");
      setSource("error");
      setHasAnalyzed(false);
    } finally {
      setLoading(false);
    }
  };

  const venues = useMemo(() => {
    const q = search.trim().toLowerCase();

    return (result.venues || []).filter((venue) => {
      const matchesType =
        typeFilter === "All" ||
        String(venue.type || "").toLowerCase() === typeFilter.toLowerCase();

      const haystack = [
        venue.name,
        venue.publisher,
        venue.scope,
        venue.fit,
        venue.open_access,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return matchesType && (!q || haystack.includes(q));
    });
  }, [result.venues, search, typeFilter]);

  const readiness = result.readiness_score;
  const readinessClass = scoreTone(readiness);

  const checklist = result.checklist || [];
  const completeCount = checklist.filter(
    (item) => item.complete || item.status === "complete" || item.status === "ready"
  ).length;
  const checklistPercent = checklist.length
    ? Math.round((completeCount / checklist.length) * 100)
    : 0;

  const tabs = [
    { id: "overview", label: "Overview", icon: LayoutGrid },
    { id: "venues", label: "Find Venues", icon: Globe2 },
    { id: "checklist", label: "Submission Checklist", icon: ClipboardCheck },
    { id: "risks", label: "Risk & Gaps", icon: ShieldCheck },
    { id: "plan", label: "Publication Plan", icon: Rocket },
  ];

  return (
    <div className="publication-page">
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr auto",gap:12,alignItems:"end",marginBottom:16}}>
        <label><small>ACTIVE PROJECT</small><select value={projectId} onChange={e=>setProjectId(Number(e.target.value))} style={{width:"100%",padding:10,borderRadius:10,border:"1px solid #dfe5ec"}}><option value={0}>Select project</option>{projects.map(p=><option key={p.id} value={p.id}>{p.title}</option>)}</select></label>
        <label><small>MANUSCRIPT</small><select value={paperId} onChange={e=>{setPaperId(Number(e.target.value));localStorage.setItem("researchmate_paper_id",e.target.value)}} style={{width:"100%",padding:10,borderRadius:10,border:"1px solid #dfe5ec"}}><option value={0}>Select paper</option>{papers.map(p=><option key={p.id} value={p.id}>{p.title}</option>)}</select></label>
        <button onClick={analyzePublication} disabled={loading || !projectId || !paperId} style={{padding:"11px 16px",border:0,borderRadius:10,background:"#16855b",color:"white",fontWeight:700}}>{loading ? "Analyzing…" : "Run AI Analysis"}</button>
      </div>

      <style>{`
        .publication-page {
          --pub-ink: #102033;
          --pub-muted: #68788a;
          --pub-line: #e5eaf0;
          --pub-soft: #f6f9fc;
          --pub-card: #ffffff;
          --pub-green: #16855b;
          --pub-green-soft: #eaf8f1;
          --pub-blue: #2877d5;
          --pub-blue-soft: #edf5ff;
          --pub-amber: #b7791f;
          --pub-amber-soft: #fff7e8;
          --pub-red: #c84b4b;
          --pub-red-soft: #fff0f0;
          color: var(--pub-ink);
          max-width: 1500px;
          margin: 0 auto;
          padding-bottom: 48px;
        }
        .pub-hero {
          position: relative;
          overflow: hidden;
          border: 1px solid #dfe8e4;
          border-radius: 26px;
          padding: 34px;
          margin-bottom: 20px;
          background:
            radial-gradient(circle at 92% 12%, rgba(48, 163, 117, .16), transparent 28%),
            linear-gradient(135deg, #f8fffc 0%, #ffffff 54%, #f4f9ff 100%);
        }
        .pub-hero-grid {
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto;
          gap: 28px;
          align-items: center;
        }
        .pub-eyebrow {
          display: inline-flex;
          align-items: center;
          gap: 7px;
          font-size: 11px;
          font-weight: 800;
          letter-spacing: .14em;
          color: var(--pub-green);
          margin-bottom: 10px;
        }
        .pub-title {
          margin: 0;
          font-size: clamp(30px, 4vw, 46px);
          line-height: 1.06;
          letter-spacing: -.04em;
        }
        .pub-subtitle {
          max-width: 760px;
          margin: 13px 0 0;
          color: var(--pub-muted);
          font-size: 15px;
          line-height: 1.7;
        }
        .pub-paper-pill {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          margin-top: 18px;
          padding: 10px 13px;
          border: 1px solid #dfe8e4;
          border-radius: 12px;
          background: rgba(255,255,255,.82);
          font-size: 12px;
          color: #536477;
        }
        .pub-hero-action {
          min-width: 190px;
          border: 0;
          border-radius: 14px;
          padding: 14px 17px;
          background: #123d32;
          color: white;
          font-weight: 750;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 9px;
          box-shadow: 0 12px 28px rgba(18,61,50,.18);
        }
        .pub-hero-action:disabled { opacity: .65; cursor: wait; }
        .pub-tabs {
          display: flex;
          gap: 7px;
          padding: 7px;
          margin-bottom: 20px;
          overflow-x: auto;
          border: 1px solid var(--pub-line);
          background: white;
          border-radius: 16px;
          position: sticky;
          top: 8px;
          z-index: 5;
          box-shadow: 0 8px 28px rgba(16,32,51,.05);
        }
        .pub-tab {
          white-space: nowrap;
          border: 0;
          background: transparent;
          color: #718092;
          padding: 11px 15px;
          border-radius: 11px;
          font-weight: 700;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          gap: 8px;
        }
        .pub-tab.active {
          background: #eef8f3;
          color: #116247;
        }
        .pub-grid-4 {
          display: grid;
          grid-template-columns: repeat(4, minmax(0,1fr));
          gap: 13px;
          margin-bottom: 20px;
        }
        .pub-stat {
          background: var(--pub-card);
          border: 1px solid var(--pub-line);
          border-radius: 17px;
          padding: 18px;
          min-height: 115px;
        }
        .pub-stat-label {
          display: block;
          color: #788797;
          font-size: 10px;
          letter-spacing: .1em;
          font-weight: 800;
        }
        .pub-stat-value {
          display: block;
          font-size: 29px;
          letter-spacing: -.03em;
          margin: 10px 0 3px;
        }
        .pub-stat-note {
          color: #738294;
          font-size: 12px;
        }
        .pub-card {
          background: white;
          border: 1px solid var(--pub-line);
          border-radius: 20px;
          padding: 22px;
          box-shadow: 0 7px 24px rgba(20,40,60,.035);
        }
        .pub-card + .pub-card { margin-top: 16px; }
        .pub-card-head {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 15px;
          margin-bottom: 18px;
        }
        .pub-card-head h2, .pub-card-head h3 {
          margin: 4px 0 0;
          letter-spacing: -.02em;
        }
        .pub-card-head p {
          margin: 6px 0 0;
          color: var(--pub-muted);
          font-size: 13px;
          line-height: 1.55;
        }
        .pub-label {
          font-size: 10px;
          font-weight: 850;
          letter-spacing: .12em;
          color: #82909f;
        }
        .pub-overview {
          display: grid;
          grid-template-columns: 1.35fr .65fr;
          gap: 16px;
        }
        .pub-readiness {
          display: flex;
          align-items: center;
          gap: 20px;
        }
        .pub-ring {
          width: 112px;
          height: 112px;
          border-radius: 50%;
          display: grid;
          place-items: center;
          background: conic-gradient(#19936a calc(var(--score) * 1%), #eaf0ed 0);
          position: relative;
          flex: 0 0 auto;
        }
        .pub-ring:after {
          content: "";
          position: absolute;
          inset: 10px;
          border-radius: 50%;
          background: white;
        }
        .pub-ring-inner {
          position: relative;
          z-index: 1;
          text-align: center;
        }
        .pub-ring-inner strong { display: block; font-size: 25px; }
        .pub-ring-inner span { font-size: 9px; color: #7b8895; }
        .pub-readiness h3 { margin: 0 0 7px; }
        .pub-readiness p { margin: 0; color: var(--pub-muted); line-height: 1.55; font-size: 13px; }
        .pub-score-badge {
          display: inline-flex;
          padding: 6px 9px;
          border-radius: 999px;
          font-size: 10px;
          font-weight: 800;
          margin-top: 10px;
        }
        .pub-score-badge.good { background: var(--pub-green-soft); color: var(--pub-green); }
        .pub-score-badge.medium { background: var(--pub-amber-soft); color: var(--pub-amber); }
        .pub-score-badge.low { background: var(--pub-red-soft); color: var(--pub-red); }
        .pub-score-badge.neutral { background: #f1f4f7; color: #657485; }
        .pub-mini-list { display: grid; gap: 10px; }
        .pub-mini-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 12px;
          padding: 11px 0;
          border-bottom: 1px solid #eef1f4;
          font-size: 13px;
        }
        .pub-mini-row:last-child { border-bottom: 0; }
        .pub-mini-row span { color: #738294; }
        .pub-mini-row strong { color: #213246; }
        .pub-two-col {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 16px;
        }
        .pub-list {
          display: grid;
          gap: 10px;
          margin: 0;
          padding: 0;
          list-style: none;
        }
        .pub-list li {
          display: flex;
          gap: 10px;
          align-items: flex-start;
          padding: 11px 12px;
          border-radius: 12px;
          background: #f8fafc;
          color: #516173;
          font-size: 13px;
          line-height: 1.5;
        }
        .pub-list li svg { flex: 0 0 auto; margin-top: 2px; color: #1c8c66; }
        .pub-venue-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0,1fr));
          gap: 14px;
        }
        .pub-venue {
          border: 1px solid var(--pub-line);
          border-radius: 17px;
          padding: 18px;
          background: linear-gradient(180deg,#fff,#fbfcfd);
          transition: transform .18s ease, box-shadow .18s ease;
        }
        .pub-venue:hover { transform: translateY(-2px); box-shadow: 0 12px 28px rgba(16,32,51,.07); }
        .pub-venue-top { display: flex; justify-content: space-between; gap: 10px; }
        .pub-venue h3 { margin: 9px 0 5px; font-size: 17px; }
        .pub-venue-publisher { font-size: 11px; color: #84909d; }
        .pub-fit {
          padding: 6px 8px;
          height: fit-content;
          border-radius: 8px;
          background: var(--pub-green-soft);
          color: var(--pub-green);
          font-size: 9px;
          font-weight: 850;
          text-transform: uppercase;
        }
        .pub-venue-scope { color: #657587; font-size: 12px; line-height: 1.55; min-height: 58px; margin: 13px 0; }
        .pub-tags { display: flex; flex-wrap: wrap; gap: 6px; }
        .pub-tag { padding: 5px 8px; border-radius: 7px; background: #f0f4f7; color: #667585; font-size: 10px; }
        .pub-venue-actions { display: flex; gap: 8px; margin-top: 15px; }
        .pub-link {
          flex: 1;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 7px;
          text-decoration: none;
          border: 1px solid #dfe5ea;
          border-radius: 9px;
          padding: 9px 10px;
          color: #385064;
          font-size: 11px;
          font-weight: 750;
          background: white;
        }
        .pub-search-row { display: flex; gap: 10px; margin-bottom: 17px; }
        .pub-search {
          flex: 1;
          position: relative;
        }
        .pub-search svg { position: absolute; left: 13px; top: 12px; color: #93a0ad; }
        .pub-search input {
          width: 100%;
          box-sizing: border-box;
          border: 1px solid #dfe5ea;
          border-radius: 11px;
          padding: 11px 12px 11px 38px;
          outline: none;
          font: inherit;
        }
        .pub-filter {
          border: 1px solid #dfe5ea;
          border-radius: 11px;
          padding: 0 11px;
          background: white;
          color: #526274;
          font-weight: 650;
        }
        .pub-checklist {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
        }
        .pub-check {
          display: flex;
          gap: 11px;
          padding: 13px;
          border: 1px solid var(--pub-line);
          border-radius: 13px;
          background: #fff;
        }
        .pub-check-icon.complete { color: var(--pub-green); }
        .pub-check-icon.pending { color: #c0c8d0; }
        .pub-check strong { display: block; font-size: 13px; }
        .pub-check p { margin: 4px 0 0; color: #788695; font-size: 11px; line-height: 1.45; }
        .pub-progress {
          height: 8px;
          background: #edf1f3;
          border-radius: 99px;
          overflow: hidden;
          margin: 9px 0 4px;
        }
        .pub-progress > div { height: 100%; background: #1b9369; border-radius: inherit; }
        .pub-risk-list { display: grid; gap: 11px; }
        .pub-risk {
          display: grid;
          grid-template-columns: auto 1fr;
          gap: 11px;
          padding: 14px;
          border-radius: 13px;
          border: 1px solid var(--pub-line);
        }
        .pub-risk-icon {
          width: 32px; height: 32px; border-radius: 9px;
          display: grid; place-items: center;
        }
        .pub-risk-icon.high { background: var(--pub-red-soft); color: var(--pub-red); }
        .pub-risk-icon.medium { background: var(--pub-amber-soft); color: var(--pub-amber); }
        .pub-risk-icon.low { background: var(--pub-green-soft); color: var(--pub-green); }
        .pub-risk strong { font-size: 13px; }
        .pub-risk p { margin: 4px 0 0; color: #687889; font-size: 12px; line-height: 1.5; }
        .pub-plan { counter-reset: plan; display: grid; gap: 11px; }
        .pub-plan-item {
          display: grid;
          grid-template-columns: 38px 1fr;
          gap: 12px;
          align-items: start;
          padding: 14px;
          border-radius: 14px;
          background: #f8fafc;
        }
        .pub-plan-number {
          width: 38px; height: 38px; border-radius: 11px;
          display: grid; place-items: center;
          background: #eaf6f1; color: #137453; font-weight: 850;
        }
        .pub-plan-item strong { display: block; font-size: 13px; margin: 2px 0 4px; }
        .pub-plan-item p { margin: 0; color: #718092; font-size: 12px; line-height: 1.5; }
        .pub-alert {
          display: flex;
          gap: 10px;
          align-items: flex-start;
          padding: 13px 15px;
          border-radius: 13px;
          margin-bottom: 16px;
          background: #fff8e9;
          border: 1px solid #f5dfaf;
          color: #765719;
          font-size: 12px;
          line-height: 1.5;
        }
        .pub-source {
          display: inline-flex;
          align-items: center;
          gap: 7px;
          font-size: 10px;
          color: #748394;
          margin-top: 10px;
        }
        .pub-empty {
          padding: 35px;
          text-align: center;
          color: #778696;
          border: 1px dashed #dce3e8;
          border-radius: 14px;
        }
        @media (max-width: 1050px) {
          .pub-venue-grid { grid-template-columns: 1fr 1fr; }
          .pub-grid-4 { grid-template-columns: 1fr 1fr; }
        }
        @media (max-width: 760px) {
          .pub-hero { padding: 23px; border-radius: 19px; }
          .pub-hero-grid, .pub-overview, .pub-two-col { grid-template-columns: 1fr; }
          .pub-grid-4, .pub-venue-grid, .pub-checklist { grid-template-columns: 1fr; }
          .pub-readiness { align-items: flex-start; }
          .pub-search-row { flex-direction: column; }
          .pub-filter { height: 43px; }
        }
      `}</style>

      <section className="pub-hero">
        <div className="pub-hero-grid">
          <div>
            <div className="pub-eyebrow">
              <Rocket size={14} />
              PUBLICATION ASSISTANT
            </div>
            <h1 className="pub-title">From research-ready to submission-ready.</h1>
            <p className="pub-subtitle">
              Evaluate manuscript readiness, identify publication requirements,
              explore potential venues, detect submission gaps and prepare a
              practical publication plan.
            </p>
            <div className="pub-paper-pill">
              <FileCheck2 size={15} />
              {result.paper_title}
            </div>
            <div className="pub-source">
              <Info size={13} />
              {source === "backend"
                ? "Analysis generated from the ResearchMate backend."
                : "Prepared workspace preview. Connect the Publication API for live venue data."}
            </div>
          </div>

          <button
            className="pub-hero-action"
            onClick={analyzePublication}
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader2 size={17} className="spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Sparkles size={17} />
                Analyze Publication Fit
              </>
            )}
          </button>
        </div>
      </section>

      {error && (
        <div className="pub-alert">
          <CircleAlert size={17} />
          <div>
            <strong>Publication API notice</strong>
            <div>{error}</div>
            <div style={{ marginTop: 4 }}>
              The interface is still usable as a publication-preparation
              workspace. Venue and deadline facts must be verified from the
              official publisher / conference source before submission.
            </div>
          </div>
        </div>
      )}

      <nav className="pub-tabs">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            className={`pub-tab ${activeTab === id ? "active" : ""}`}
            onClick={() => setActiveTab(id)}
          >
            <Icon size={15} />
            {label}
          </button>
        ))}
      </nav>

      {!hasAnalyzed && (
        <div className="pub-card" style={{ marginBottom: 16 }}>
          <div className="pub-card-head">
            <div>
              <span className="pub-label">READY TO ANALYZE</span>
              <h2>Publication workspace</h2>
              <p>
                Run the analysis to connect this workspace to your manuscript,
                reviewer findings and publication-preparation data.
              </p>
            </div>
            <Target size={22} color="#17825b" />
          </div>
          <div className="pub-two-col">
            <ul className="pub-list">
              <li><CheckCircle2 size={16} />Venue scope and publication-fit screening</li>
              <li><CheckCircle2 size={16} />Required manuscript components</li>
              <li><CheckCircle2 size={16} />Missing submission items</li>
            </ul>
            <ul className="pub-list">
              <li><CheckCircle2 size={16} />Publisher / conference risk checks</li>
              <li><CheckCircle2 size={16} />Current CFP and deadline verification workflow</li>
              <li><CheckCircle2 size={16} />Step-by-step publication preparation plan</li>
            </ul>
          </div>
        </div>
      )}

      {activeTab === "overview" && (
        <>
          <div className="pub-grid-4">
            <div className="pub-stat">
              <span className="pub-stat-label">PUBLICATION READINESS</span>
              <strong className="pub-stat-value">
                {readiness == null ? "—" : `${readiness}%`}
              </strong>
              <span className="pub-stat-note">Preparation screening</span>
            </div>
            <div className="pub-stat">
              <span className="pub-stat-label">VENUES</span>
              <strong className="pub-stat-value">{result.venues.length}</strong>
              <span className="pub-stat-note">Potentially relevant venues</span>
            </div>
            <div className="pub-stat">
              <span className="pub-stat-label">CHECKLIST</span>
              <strong className="pub-stat-value">{checklistPercent}%</strong>
              <span className="pub-stat-note">
                {completeCount}/{checklist.length || 0} items prepared
              </span>
            </div>
            <div className="pub-stat">
              <span className="pub-stat-label">OPEN ITEMS</span>
              <strong className="pub-stat-value">{result.missing_items.length}</strong>
              <span className="pub-stat-note">Need attention before submission</span>
            </div>
          </div>

          <div className="pub-overview">
            <section className="pub-card">
              <div className="pub-card-head">
                <div>
                  <span className="pub-label">MANUSCRIPT STATUS</span>
                  <h2>Publication readiness</h2>
                </div>
                <ClipboardCheck size={21} color="#17825b" />
              </div>

              <div className="pub-readiness">
                <div
                  className="pub-ring"
                  style={{ "--score": readiness == null ? 0 : readiness }}
                >
                  <div className="pub-ring-inner">
                    <strong>{readiness == null ? "—" : readiness}</strong>
                    <span>/ 100</span>
                  </div>
                </div>
                <div>
                  <h3>
                    {readiness == null
                      ? "Run analysis"
                      : readiness >= 80
                      ? "Strong preparation"
                      : readiness >= 60
                      ? "Needs refinement"
                      : "Several gaps remain"}
                  </h3>
                  <p>
                    This is a preparation indicator, not an acceptance
                    probability or prediction.
                  </p>
                  <span className={`pub-score-badge ${readinessClass}`}>
                    {readiness == null ? "Not analyzed" : "Preparation screening"}
                  </span>
                </div>
              </div>
            </section>

            <section className="pub-card">
              <div className="pub-card-head">
                <div>
                  <span className="pub-label">NEXT ACTIONS</span>
                  <h2>Before submission</h2>
                </div>
              </div>
              <div className="pub-mini-list">
                <div className="pub-mini-row">
                  <span>Missing items</span>
                  <strong>{result.missing_items.length}</strong>
                </div>
                <div className="pub-mini-row">
                  <span>Potential venues</span>
                  <strong>{result.venues.length}</strong>
                </div>
                <div className="pub-mini-row">
                  <span>Checklist progress</span>
                  <strong>{checklistPercent}%</strong>
                </div>
              </div>
            </section>
          </div>

          <div className="pub-two-col" style={{ marginTop: 16 }}>
            <section className="pub-card">
              <div className="pub-card-head">
                <div>
                  <span className="pub-label">MISSING SUBMISSION ITEMS</span>
                  <h2>What still needs attention?</h2>
                </div>
                <CircleAlert size={20} color="#b7791f" />
              </div>
              {result.missing_items.length ? (
                <ul className="pub-list">
                  {result.missing_items.map((item, index) => (
                    <li key={index}>
                      <CircleAlert size={16} />
                      {typeof item === "string" ? item : item.text || item.title}
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="pub-empty">Run the publication analysis to populate this section.</div>
              )}
            </section>

            <section className="pub-card">
              <div className="pub-card-head">
                <div>
                  <span className="pub-label">REQUIRED COMPONENTS</span>
                  <h2>Submission package</h2>
                </div>
                <FileCheck2 size={20} color="#2877d5" />
              </div>
              <ul className="pub-list">
                {(result.requirements.length
                  ? result.requirements
                  : [
                      "Final manuscript in the target venue template",
                      "Author and affiliation information",
                      "Figures and tables",
                      "Verified references",
                      "Declarations required by the target venue",
                    ]
                ).map((item, index) => (
                  <li key={index}>
                    <CheckCircle2 size={16} />
                    {typeof item === "string" ? item : item.text || item.title}
                  </li>
                ))}
              </ul>
            </section>
          </div>
        </>
      )}

      {activeTab === "venues" && (
        <section className="pub-card">
          <div className="pub-card-head">
            <div>
              <span className="pub-label">PUBLICATION DISCOVERY</span>
              <h2>Potential publication venues</h2>
              <p>
                Compare scope and documented requirements. Always verify current
                author guidelines, fees, indexing and deadlines from the official venue.
              </p>
            </div>
            <Globe2 size={22} color="#2877d5" />
          </div>

          <div className="pub-search-row">
            <div className="pub-search">
              <Search size={17} />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search venue, publisher, scope..."
              />
            </div>
            <select
              className="pub-filter"
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
            >
              <option>All</option>
              <option>Journal</option>
              <option>Conference</option>
            </select>
          </div>

          {venues.length ? (
            <div className="pub-venue-grid">
              {venues.map((venue, index) => (
                <article className="pub-venue" key={venue.name || index}>
                  <div className="pub-venue-top">
                    <div>
                      <span className="pub-label">{venue.type || "Venue"}</span>
                      <h3>{venue.name}</h3>
                      <div className="pub-venue-publisher">
                        {venue.publisher || "Publisher not specified"}
                      </div>
                    </div>
                    <span className="pub-fit">{venue.fit || "Potential fit"}</span>
                  </div>
                  <p className="pub-venue-scope">{venue.scope}</p>
                  <div className="pub-tags">
                    {venue.open_access && <span className="pub-tag">{venue.open_access}</span>}
                    {(venue.requirements || []).slice(0, 3).map((req, i) => (
                      <span className="pub-tag" key={i}>{req}</span>
                    ))}
                  </div>
                  <div className="pub-venue-actions">
                    {venue.url && (
                      <a
                        className="pub-link"
                        href={venue.url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Official site
                        <ExternalLink size={13} />
                      </a>
                    )}
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="pub-empty">
              No venues match the current search.
            </div>
          )}

          <div className="pub-source">
            <Info size={13} />
            Venue cards describe potential fit only; they are not rankings or acceptance predictions.
          </div>
        </section>
      )}

      {activeTab === "checklist" && (
        <section className="pub-card">
          <div className="pub-card-head">
            <div>
              <span className="pub-label">SUBMISSION READINESS</span>
              <h2>Final submission checklist</h2>
              <p>
                Complete the target venue's exact checklist before uploading the manuscript.
              </p>
            </div>
            <ClipboardCheck size={22} color="#16855b" />
          </div>

          <div style={{ marginBottom: 18 }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
              <strong>{completeCount} of {checklist.length} prepared</strong>
              <span>{checklistPercent}%</span>
            </div>
            <div className="pub-progress">
              <div style={{ width: `${checklistPercent}%` }} />
            </div>
          </div>

          {checklist.length ? (
            <div className="pub-checklist">
              {checklist.map((item, index) => {
                const complete =
                  item.complete || item.status === "complete" || item.status === "ready";
                return (
                  <div className="pub-check" key={index}>
                    {complete ? (
                      <CheckCircle2 className="pub-check-icon complete" size={19} />
                    ) : (
                      <XCircle className="pub-check-icon pending" size={19} />
                    )}
                    <div>
                      <strong>{item.item || item.title || `Requirement ${index + 1}`}</strong>
                      <p>{item.note || item.description || (complete ? "Prepared" : "Needs verification")}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="pub-empty">Run analysis to generate the manuscript checklist.</div>
          )}
        </section>
      )}

      {activeTab === "risks" && (
        <section className="pub-card">
          <div className="pub-card-head">
            <div>
              <span className="pub-label">PUBLICATION RISK CHECK</span>
              <h2>Issues to resolve before submission</h2>
              <p>
                These are preparation risks and verification points, not a prediction of acceptance.
              </p>
            </div>
            <ShieldCheck size={22} color="#b7791f" />
          </div>

          {result.risks.length ? (
            <div className="pub-risk-list">
              {result.risks.map((risk, index) => {
                const level = String(risk.level || "medium").toLowerCase();
                return (
                  <div className="pub-risk" key={index}>
                    <div className={`pub-risk-icon ${level}`}>
                      {level === "high" ? <CircleAlert size={17} /> : <ShieldCheck size={17} />}
                    </div>
                    <div>
                      <strong>{risk.title || "Verification point"}</strong>
                      <p>{risk.text || risk.description || String(risk)}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="pub-empty">No publication risks are loaded yet.</div>
          )}
        </section>
      )}

      {activeTab === "plan" && (
        <section className="pub-card">
          <div className="pub-card-head">
            <div>
              <span className="pub-label">PUBLICATION WORKFLOW</span>
              <h2>Recommended preparation sequence</h2>
              <p>
                A practical order for moving from manuscript refinement to submission.
              </p>
            </div>
            <Rocket size={22} color="#16855b" />
          </div>

          {result.plan.length ? (
            <div className="pub-plan">
              {result.plan.map((item, index) => (
                <div className="pub-plan-item" key={index}>
                  <div className="pub-plan-number">
                    {String(index + 1).padStart(2, "0")}
                  </div>
                  <div>
                    <strong>
                      {typeof item === "string" ? item : item.title || item.action || "Publication action"}
                    </strong>
                    {typeof item !== "string" && (
                      <p>{item.description || item.note || ""}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="pub-empty">
              Run the publication analysis to generate the plan.
            </div>
          )}

          {result.notes.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <ul className="pub-list">
                {result.notes.map((note, index) => (
                  <li key={index}>
                    <Info size={16} />
                    {typeof note === "string" ? note : note.text || JSON.stringify(note)}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      <div className="pub-card" style={{ marginTop: 16, background: "#f7fbf9" }}>
        <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
          <div
            style={{
              width: 34,
              height: 34,
              borderRadius: 10,
              display: "grid",
              placeItems: "center",
              background: "#e5f6ee",
              color: "#147655",
              flex: "0 0 auto",
            }}
          >
            <Info size={17} />
          </div>
          <div>
            <strong>ResearchMate publication note</strong>
            <p style={{ margin: "5px 0 0", color: "#647688", fontSize: 12, lineHeight: 1.6 }}>
              Publication fit is an evidence-based preparation aid. It does not
              guarantee acceptance. Current scope, author guidelines, fees,
              indexing, submission windows and CFP deadlines should be verified
              on the official publication venue before submission.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
