import React, { useMemo, useState } from "react";
import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  FileCheck2,
  FileText,
  Info,
  Loader2,
  PenLine,
  RefreshCw,
  Sparkles,
  Target,
  TriangleAlert,
} from "lucide-react";

const API_BASE_URL = "http://127.0.0.1:8001";
const PROJECT_ID = 4;
const PAPER_ID = 17;

const getError = (data) => {
  if (!data) return "Something went wrong.";
  if (typeof data === "string") return data;
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) {
    return data.detail.map((x) => x?.msg || x?.message || String(x)).join(", ");
  }
  return data.message || "The writing analysis could not be completed.";
};

const asList = (value) => {
  if (Array.isArray(value)) return value;
  if (value == null || value === "") return [];
  return [value];
};

const textOf = (item) => {
  if (typeof item === "string" || typeof item === "number") return String(item);
  if (!item || typeof item !== "object") return "";
  return item.text || item.message || item.feedback || item.action || item.title || JSON.stringify(item);
};

function WritingPage() {
  const [manuscript, setManuscript] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [active, setActive] = useState("overview");

  const analyze = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/writing/projects/${PROJECT_ID}/papers/${PAPER_ID}/analyze`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: "",
            abstract: "",
            manuscript: manuscript.trim(),
          }),
        }
      );

      const type = response.headers.get("content-type") || "";
      const data = type.includes("application/json")
        ? await response.json()
        : { detail: await response.text() };

      if (!response.ok) throw new Error(getError(data));
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const sections = asList(result?.detected_sections);
  const titles = asList(result?.title_suggestions);
  const recommendations = asList(result?.overall_recommendations);
  const strengths = asList(result?.strengths);
  const improvements = asList(result?.improvement_areas);

  const nav = [
    ["overview", "Overview"],
    ["structure", "Structure"],
    ["writing", "Academic Writing"],
    ["citations", "Citations"],
    ["formatting", "Formatting"],
  ];

  return (
    <div className="wm-page">
      <style>{`
        .wm-page{color:#102b45;max-width:1500px;margin:0 auto;padding-bottom:44px}
        .wm-hero{border:1px solid #dfe8ee;border-radius:25px;padding:31px 34px;background:linear-gradient(135deg,#f9fffd,#fff 58%,#f4f8ff);position:relative;overflow:hidden}
        .wm-hero:after{content:"";position:absolute;width:250px;height:250px;border-radius:50%;right:-100px;top:-110px;background:rgba(23,154,115,.10)}
        .wm-kicker{font-size:10px;letter-spacing:.16em;font-weight:850;color:#13906b;display:flex;gap:7px;align-items:center}
        .wm-hero h1{font-size:clamp(30px,4vw,45px);line-height:1.06;letter-spacing:-.04em;margin:10px 0 10px}
        .wm-hero p{max-width:760px;color:#718296;line-height:1.65;margin:0;font-size:14px}
        .wm-actions{display:flex;gap:10px;margin-top:20px;flex-wrap:wrap}
        .wm-btn{border:0;border-radius:11px;padding:12px 16px;background:#123d55;color:#fff;font-weight:800;display:inline-flex;gap:8px;align-items:center;cursor:pointer}
        .wm-btn.secondary{background:#fff;color:#3c556c;border:1px solid #dce5eb}
        .wm-btn:disabled{opacity:.6;cursor:wait}
        .wm-input{margin-top:18px;background:#fff;border:1px solid #dfe7ed;border-radius:18px;padding:17px}
        .wm-input label{font-size:10px;font-weight:850;letter-spacing:.11em;color:#7d8b99}
        .wm-input textarea{width:100%;box-sizing:border-box;margin-top:9px;min-height:100px;resize:vertical;border:1px solid #e0e6eb;border-radius:11px;padding:12px;font:inherit;outline:none;color:#30465b}
        .wm-tabs{display:flex;gap:6px;overflow:auto;padding:6px;background:#fff;border:1px solid #e1e8ed;border-radius:15px;margin:17px 0;position:sticky;top:8px;z-index:4}
        .wm-tab{white-space:nowrap;border:0;background:transparent;padding:10px 13px;border-radius:9px;color:#788899;font-weight:750;cursor:pointer}
        .wm-tab.active{background:#eaf7f2;color:#137353}
        .wm-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:15px}
        .wm-stat,.wm-card{background:#fff;border:1px solid #e1e8ed;border-radius:18px;padding:19px;box-shadow:0 7px 24px rgba(16,43,69,.035)}
        .wm-stat span{font-size:9px;letter-spacing:.12em;color:#8996a3;font-weight:850}
        .wm-stat strong{font-size:28px;display:block;margin:8px 0 2px;letter-spacing:-.03em}
        .wm-stat small{color:#7c8b99}
        .wm-grid{display:grid;grid-template-columns:1.2fr .8fr;gap:15px}
        .wm-grid2{display:grid;grid-template-columns:1fr 1fr;gap:15px}
        .wm-card h2{font-size:19px;margin:4px 0 6px;letter-spacing:-.02em}
        .wm-card h3{font-size:14px;margin:0 0 9px}
        .wm-label{font-size:9px;letter-spacing:.12em;color:#8795a3;font-weight:850}
        .wm-muted{color:#748597;font-size:12px;line-height:1.6}
        .wm-list{display:grid;gap:9px;margin:13px 0 0;padding:0;list-style:none}
        .wm-list li{display:flex;gap:9px;padding:10px 11px;border-radius:11px;background:#f7fafb;color:#5d7082;font-size:12px;line-height:1.5}
        .wm-list svg{flex:0 0 auto;color:#1a916a;margin-top:1px}
        .wm-score{display:flex;align-items:center;gap:18px}
        .wm-score-circle{width:92px;height:92px;border-radius:50%;display:grid;place-items:center;background:conic-gradient(#1a936a calc(var(--score)*1%),#e8efec 0);position:relative}
        .wm-score-circle:after{content:"";position:absolute;inset:9px;border-radius:50%;background:#fff}
        .wm-score-circle b{position:relative;z-index:1;font-size:22px}
        .wm-section-row{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:11px 0;border-bottom:1px solid #eef1f3;font-size:12px}
        .wm-section-row:last-child{border-bottom:0}
        .wm-pill{padding:5px 8px;border-radius:999px;background:#eef7f3;color:#167553;font-size:9px;font-weight:850}
        .wm-callout{display:flex;gap:10px;background:#f3f8ff;border:1px solid #dce9f7;color:#587087;border-radius:12px;padding:12px;font-size:12px;line-height:1.55}
        .wm-title-card{border:1px solid #e2e8ed;border-radius:13px;padding:13px;background:#fbfcfd;margin-top:9px}
        .wm-title-card strong{font-size:13px}
        .wm-empty{text-align:center;padding:35px;color:#7b8998;border:1px dashed #dce4e9;border-radius:13px}
        @media(max-width:950px){.wm-stats{grid-template-columns:1fr 1fr}.wm-grid,.wm-grid2{grid-template-columns:1fr}}
        @media(max-width:620px){.wm-hero{padding:23px}.wm-stats{grid-template-columns:1fr}.wm-tabs{position:static}}
      `}</style>

      <section className="wm-hero">
        <div className="wm-kicker"><PenLine size={14}/> RESEARCH WRITING</div>
        <h1>Build a publication-ready manuscript.</h1>
        <p>
          Analyze structure, academic language, title and abstract quality,
          citation handling and formatting readiness using the shared research paper context.
        </p>

        <div className="wm-input">
          <label>OPTIONAL MANUSCRIPT INPUT</label>
          <textarea
            value={manuscript}
            onChange={(e) => setManuscript(e.target.value)}
            placeholder="Leave empty to analyze the latest extracted manuscript for Project 4 / Paper 17."
          />
          <div className="wm-actions">
            <button className="wm-btn" onClick={analyze} disabled={loading}>
              {loading ? <Loader2 size={16}/> : <Sparkles size={16}/>}
              {loading ? "Analyzing manuscript..." : "Analyze Writing"}
            </button>
            {result && (
              <button className="wm-btn secondary" onClick={() => setResult(null)}>
                <RefreshCw size={15}/> Reset
              </button>
            )}
          </div>
        </div>
      </section>

      {error && (
        <div className="wm-callout" style={{marginTop:15,background:"#fff6f0",borderColor:"#f3d9c4",color:"#875b3c"}}>
          <TriangleAlert size={17}/><span>{error}</span>
        </div>
      )}

      <div className="wm-tabs">
        {nav.map(([id,label]) => (
          <button key={id} className={`wm-tab ${active===id?"active":""}`} onClick={()=>setActive(id)}>
            {label}
          </button>
        ))}
      </div>

      {!result ? (
        <div className="wm-card wm-empty">
          <FileText size={30} color="#15906a"/>
          <h3>Writing analysis starts here</h3>
          <div>Click <b>Analyze Writing</b> to inspect the current manuscript.</div>
        </div>
      ) : (
        <>
          <div className="wm-stats">
            <div className="wm-stat">
              <span>STRUCTURE SCORE</span>
              <strong>{result.structure_score ?? "—"}</strong>
              <small>out of 10</small>
            </div>
            <div className="wm-stat">
              <span>SECTIONS DETECTED</span>
              <strong>{sections.length}</strong>
              <small>manuscript sections</small>
            </div>
            <div className="wm-stat">
              <span>TITLE OPTIONS</span>
              <strong>{titles.length}</strong>
              <small>generated suggestions</small>
            </div>
            <div className="wm-stat">
              <span>IMPROVEMENT AREAS</span>
              <strong>{improvements.length}</strong>
              <small>identified by analysis</small>
            </div>
          </div>

          {active === "overview" && (
            <div className="wm-grid">
              <section className="wm-card">
                <span className="wm-label">MANUSCRIPT STRUCTURE</span>
                <h2>Detected sections</h2>
                <p className="wm-muted">The writing engine identified these structural components.</p>
                <div style={{marginTop:12}}>
                  {sections.length ? sections.map((section,i)=>(
                    <div className="wm-section-row" key={i}>
                      <span>{textOf(section)}</span>
                      <span className="wm-pill">Detected</span>
                    </div>
                  )) : <div className="wm-empty">No section list returned.</div>}
                </div>
              </section>

              <section className="wm-card">
                <span className="wm-label">STRUCTURE QUALITY</span>
                <h2>Readiness snapshot</h2>
                <div className="wm-score" style={{marginTop:18}}>
                  <div className="wm-score-circle" style={{"--score":Math.min(100,Math.max(0,(Number(result.structure_score)||0)*10))}}>
                    <b>{result.structure_score ?? "—"}</b>
                  </div>
                  <div className="wm-muted">
                    <b style={{color:"#18344d"}}>Structure score</b>
                    <br/>A separate methodology/system section may need strengthening if it is not clearly distinguished.
                  </div>
                </div>
              </section>

              <section className="wm-card">
                <span className="wm-label">STRENGTHS</span>
                <h2>What is working</h2>
                {strengths.length ? <ul className="wm-list">{strengths.map((x,i)=><li key={i}><CheckCircle2 size={15}/>{textOf(x)}</li>)}</ul> : <div className="wm-empty">No strengths returned.</div>}
              </section>

              <section className="wm-card">
                <span className="wm-label">NEXT IMPROVEMENTS</span>
                <h2>What to refine</h2>
                {improvements.length ? <ul className="wm-list">{improvements.map((x,i)=><li key={i}><Target size={15}/>{textOf(x)}</li>)}</ul> : <div className="wm-empty">No improvement areas returned.</div>}
              </section>
            </div>
          )}

          {active === "structure" && (
            <div className="wm-grid2">
              <section className="wm-card">
                <span className="wm-label">TITLE OPTIMIZATION</span>
                <h2>Suggested titles</h2>
                {titles.length ? titles.map((x,i)=><div className="wm-title-card" key={i}><strong>{textOf(x)}</strong></div>) : <div className="wm-empty">No title suggestions returned.</div>}
              </section>
              <section className="wm-card">
                <span className="wm-label">OVERALL RECOMMENDATIONS</span>
                <h2>Writing plan</h2>
                {recommendations.length ? <ul className="wm-list">{recommendations.map((x,i)=><li key={i}><ArrowRight size={15}/>{textOf(x)}</li>)}</ul> : <div className="wm-empty">No recommendations returned.</div>}
              </section>
            </div>
          )}

          {active === "writing" && (
            <section className="wm-card">
              <span className="wm-label">ACADEMIC WRITING FEEDBACK</span>
              <h2>Improve clarity, tone and scholarly expression</h2>
              <ul className="wm-list">
                {asList(result.academic_writing_feedback).map((x,i)=><li key={i}><BookOpen size={15}/>{textOf(x)}</li>)}
              </ul>
              {!asList(result.academic_writing_feedback).length && <div className="wm-empty">No academic writing feedback returned.</div>}
            </section>
          )}

          {active === "citations" && (
            <section className="wm-card">
              <span className="wm-label">CITATION & REFERENCE FEEDBACK</span>
              <h2>Reference integrity</h2>
              <div className="wm-callout" style={{marginTop:15}}>
                <Info size={16}/>
                <span>Verify every model, dataset and external-method citation against the actual source before submission.</span>
              </div>
              <ul className="wm-list">
                {asList(result.citation_reference_feedback).map((x,i)=><li key={i}><FileCheck2 size={15}/>{textOf(x)}</li>)}
              </ul>
              {!asList(result.citation_reference_feedback).length && <div className="wm-empty">No citation feedback returned.</div>}
            </section>
          )}

          {active === "formatting" && (
            <section className="wm-card">
              <span className="wm-label">FORMATTING FEEDBACK</span>
              <h2>Prepare the manuscript for a venue template</h2>
              <ul className="wm-list">
                {asList(result.formatting_feedback).map((x,i)=><li key={i}><FileText size={15}/>{textOf(x)}</li>)}
              </ul>
              {!asList(result.formatting_feedback).length && <div className="wm-empty">No formatting feedback returned.</div>}
            </section>
          )}
        </>
      )}
    </div>
  );
}

export default WritingPage;
