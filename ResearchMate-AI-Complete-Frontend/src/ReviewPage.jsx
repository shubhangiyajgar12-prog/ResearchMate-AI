import React, { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ChevronRight,
  ClipboardList,
  FileText,
  Flag,
  Info,
  Loader2,
  MessageSquare,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Target,
  Wrench,
} from "lucide-react";

const API = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8001";

const asList = (value) => Array.isArray(value) ? value : value == null || value === "" ? [] : [value];
const textOf = (value) => {
  if (typeof value === "string" || typeof value === "number") return String(value);
  if (!value || typeof value !== "object") return "";
  return value.text || value.message || value.issue || value.action || value.recommended_action ||
    value.description || value.title || value.why_it_matters || JSON.stringify(value);
};
const errorMessage = (data, fallback) => {
  if (!data) return fallback;
  if (typeof data.detail === "string") return data.detail;
  if (data.detail?.message) return data.detail.message;
  if (Array.isArray(data.detail)) return data.detail.map(x => x.msg || x.message || String(x)).join(", ");
  return data.message || fallback;
};

function Field({ label, value, onChange, children }) {
  return (
    <label className="rv-field">
      <span>{label}</span>
      {children || <select value={value} onChange={onChange}>{/* caller supplies options */}</select>}
    </label>
  );
}

export default function ReviewPage() {
  const [projects, setProjects] = useState([]);
  const [papers, setPapers] = useState([]);
  const [projectId, setProjectId] = useState(Number(localStorage.getItem("researchmate_project_id")) || 0);
  const [paperId, setPaperId] = useState(Number(localStorage.getItem("researchmate_paper_id")) || 0);
  const [manuscript, setManuscript] = useState("");
  const [review, setReview] = useState(null);
  const [plan, setPlan] = useState(null);
  const [tab, setTab] = useState("overview");
  const [loading, setLoading] = useState(false);
  const [planning, setPlanning] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`${API}/projects/`)
      .then(async r => {
        const data = await r.json();
        if (!r.ok) throw new Error(errorMessage(data, "Unable to load projects."));
        setProjects(Array.isArray(data) ? data : []);
        if (!projectId && data?.[0]?.id) setProjectId(data[0].id);
      })
      .catch(e => setError(e.message));
  }, []);

  useEffect(() => {
    if (!projectId) return;
    localStorage.setItem("researchmate_project_id", String(projectId));
    setReview(null); setPlan(null);
    fetch(`${API}/literature/projects/${projectId}/papers`)
      .then(async r => {
        const data = await r.json();
        if (!r.ok) throw new Error(errorMessage(data, "Unable to load papers."));
        setPapers(Array.isArray(data) ? data : []);
        const valid = data.some(p => p.id === paperId) ? paperId : (data[0]?.id || 0);
        setPaperId(valid);
        if (valid) localStorage.setItem("researchmate_paper_id", String(valid));
      })
      .catch(e => setError(e.message));
  }, [projectId]);

  const selectedPaper = useMemo(() => papers.find(p => p.id === paperId), [papers, paperId]);

  const runReview = async () => {
    if (!projectId || !paperId) return setError("Select a project and manuscript first.");
    setLoading(true); setError("");
    try {
      const r = await fetch(`${API}/reviewer/projects/${projectId}/papers/${paperId}/review`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ manuscript: manuscript.trim() }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(errorMessage(data, "AI reviewer could not complete the analysis."));
      setReview(data); setPlan(null); setTab("overview");
    } catch (e) {
      setError(e.message || "Review failed.");
    } finally { setLoading(false); }
  };

  const runPlan = async () => {
    if (!projectId || !paperId) return;
    setPlanning(true); setError("");
    try {
      const r = await fetch(`${API}/improvement/projects/${projectId}/papers/${paperId}/plan`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          manuscript: manuscript.trim(),
          review_context: review ? {
            overall_review: review.overall_review,
            title_review: review.title_review,
            major_concerns: review.major_concerns,
            improvement_priorities: review.improvement_priorities,
          } : {},
        }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(errorMessage(data, "Improvement planning could not be completed."));
      setPlan(data); setTab("improvement");
    } catch (e) {
      setError(e.message || "Improvement planning failed.");
    } finally { setPlanning(false); }
  };

  const concerns = asList(review?.major_concerns);
  const minor = asList(review?.minor_concerns);
  const technical = asList(review?.technical_issues);
  const questions = asList(review?.reviewer_questions);
  const strengths = asList(review?.strengths);
  const priorities = asList(review?.improvement_priorities);
  const titleSuggestions = asList(review?.title_suggestions);
  const planActions = asList(plan?.priority_actions);
  const sectionImprovements = asList(plan?.section_improvements);

  const sectionCards = [
    ["Novelty", review?.novelty_review, Target],
    ["Methodology", review?.methodology_review, Wrench],
    ["Dataset", review?.dataset_review, FileText],
    ["Experiments", review?.experiment_review, ClipboardList],
    ["Results", review?.results_review, CheckCircle2],
    ["Discussion", review?.discussion_review, MessageSquare],
    ["Citations", review?.citation_review, ShieldCheck],
  ];

  return (
    <div className="rv-page">
      <style>{`
        .rv-page{max-width:1500px;margin:0 auto;color:#102b45;padding-bottom:55px}
        .rv-hero{border:1px solid #dfe8ee;border-radius:26px;padding:30px 32px;background:linear-gradient(135deg,#f7fffc,#fff 56%,#f5f7ff);margin-bottom:16px}
        .rv-kicker{font-size:11px;font-weight:900;letter-spacing:.14em;color:#167b5a;display:flex;gap:7px;align-items:center}
        .rv-hero h1{font-size:clamp(28px,4vw,44px);line-height:1.06;letter-spacing:-.04em;margin:9px 0}
        .rv-hero p{max-width:850px;color:#66788a;line-height:1.65;margin:0}
        .rv-controls{display:grid;grid-template-columns:1fr 1fr auto;gap:12px;align-items:end;margin-top:22px}
        .rv-field span{display:block;font-size:10px;font-weight:850;letter-spacing:.12em;color:#7a8998;margin-bottom:7px}
        .rv-field select{width:100%;border:1px solid #dce4ea;border-radius:11px;padding:11px;background:#fff;color:#102b45}
        .rv-button{border:0;border-radius:12px;padding:12px 17px;background:#123d32;color:#fff;font-weight:800;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:8px}
        .rv-button:disabled{opacity:.55;cursor:wait}
        .rv-button.secondary{background:#eef5f2;color:#145b46}
        .rv-tabs{display:flex;gap:7px;overflow:auto;padding:7px;border:1px solid #e3e9ee;background:#fff;border-radius:16px;margin-bottom:16px;position:sticky;top:8px;z-index:4}
        .rv-tab{border:0;background:transparent;border-radius:10px;padding:10px 14px;color:#718092;font-weight:750;white-space:nowrap;cursor:pointer}
        .rv-tab.active{background:#eef8f3;color:#126449}
        .rv-error{border:1px solid #f1caca;background:#fff3f3;color:#a33b3b;border-radius:13px;padding:12px 14px;margin-bottom:15px;display:flex;gap:9px;align-items:flex-start}
        .rv-empty{border:1px dashed #d7e1e7;border-radius:20px;background:#fff;text-align:center;padding:65px 20px;color:#708092}
        .rv-card{border:1px solid #e2e8ed;border-radius:19px;background:#fff;padding:21px;box-shadow:0 7px 24px rgba(16,38,58,.035)}
        .rv-card+.rv-card{margin-top:15px}
        .rv-card h2,.rv-card h3{margin:4px 0 7px;letter-spacing:-.02em}
        .rv-muted{color:#718092;line-height:1.65;font-size:13px}
        .rv-label{font-size:10px;letter-spacing:.12em;font-weight:900;color:#7e8d9c}
        .rv-title-box{display:grid;grid-template-columns:1.15fr .85fr;gap:15px;margin-bottom:15px}
        .rv-current-title{font-size:22px;font-weight:850;line-height:1.25}
        .rv-chip{display:inline-flex;align-items:center;gap:6px;border:1px solid #dfe7ed;border-radius:999px;padding:5px 9px;font-size:10px;font-weight:800;color:#647486;background:#fbfcfd}
        .rv-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px}
        .rv-section-card{border:1px solid #e5eaf0;border-radius:16px;padding:18px;background:#fff}
        .rv-section-head{display:flex;align-items:center;gap:10px}
        .rv-icon{width:35px;height:35px;border-radius:10px;background:#eef7f3;color:#157555;display:grid;place-items:center}
        .rv-list{margin:10px 0 0;padding-left:18px;color:#526579;font-size:13px;line-height:1.65}
        .rv-list li+li{margin-top:6px}
        .rv-callout{border:1px solid #dce8f2;background:#f6faff;border-radius:14px;padding:14px;color:#526579;line-height:1.65;font-size:13px}
        .rv-callout.warn{background:#fff9ef;border-color:#f0dfbc}
        .rv-callout.good{background:#f2fbf6;border-color:#d3ecdd}
        .rv-columns{display:grid;grid-template-columns:1fr 1fr;gap:15px}
        .rv-item{border:1px solid #e5eaf0;border-radius:14px;padding:14px;background:#fcfdfe}
        .rv-item strong{display:block;font-size:13px;margin-bottom:6px}
        .rv-item p{margin:0;color:#617286;font-size:12px;line-height:1.6}
        .rv-priority{display:flex;gap:12px;align-items:flex-start;padding:13px 0;border-bottom:1px solid #edf0f3}
        .rv-priority:last-child{border-bottom:0}
        .rv-num{min-width:29px;height:29px;border-radius:9px;background:#123d32;color:#fff;display:grid;place-items:center;font-weight:900;font-size:12px}
        .rv-suggestion{border:1px solid #dfe7ec;border-radius:14px;padding:14px;background:#fbfcfd}
        .rv-suggestion strong{display:block;font-size:15px;line-height:1.4}
        .rv-suggestion span{display:block;color:#68798b;font-size:12px;line-height:1.55;margin-top:6px}
        .rv-profile{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
        .rv-stat{border:1px solid #e3e9ee;border-radius:13px;padding:13px;background:#fff}
        .rv-stat small{display:block;color:#7a8997;font-size:10px;font-weight:800;letter-spacing:.08em}
        .rv-stat b{display:block;font-size:21px;margin-top:6px}
        .rv-textarea{width:100%;min-height:105px;border:1px solid #dce4ea;border-radius:13px;padding:12px;resize:vertical;font:inherit;color:#102b45}
        @media(max-width:900px){.rv-controls,.rv-title-box,.rv-columns,.rv-grid{grid-template-columns:1fr}.rv-profile{grid-template-columns:1fr 1fr}}
        @media(max-width:560px){.rv-profile{grid-template-columns:1fr}.rv-hero{padding:22px}.rv-controls{grid-template-columns:1fr}}
      `}</style>

      <section className="rv-hero">
        <div className="rv-kicker"><Sparkles size={14}/> AI PEER REVIEW & IMPROVEMENT</div>
        <h1>Review the paper. Then improve the paper.</h1>
        <p>
          ResearchMate reads the selected manuscript, checks its actual title, sections,
          methodology, experiments, evidence and presentation, and then converts the findings
          into a prioritized improvement plan. It does not show generic demo feedback.
        </p>

        <div className="rv-controls">
          <label className="rv-field">
            <span>ACTIVE PROJECT</span>
            <select value={projectId} onChange={e => setProjectId(Number(e.target.value))}>
              <option value={0}>Select project</option>
              {projects.map(p => <option key={p.id} value={p.id}>{p.title}</option>)}
            </select>
          </label>
          <label className="rv-field">
            <span>MANUSCRIPT / PAPER</span>
            <select value={paperId} onChange={e => {
              const id = Number(e.target.value); setPaperId(id); localStorage.setItem("researchmate_paper_id", String(id));
              setReview(null); setPlan(null);
            }}>
              <option value={0}>Select manuscript</option>
              {papers.map(p => <option key={p.id} value={p.id}>{p.title}</option>)}
            </select>
          </label>
          <button className="rv-button" onClick={runReview} disabled={loading || !projectId || !paperId}>
            {loading ? <Loader2 size={17} className="rv-spin"/> : <Sparkles size={17}/>}
            {loading ? "Reviewing paper…" : "Run Paper Review"}
          </button>
        </div>

        {selectedPaper && (
          <div style={{marginTop:13,display:"flex",gap:8,alignItems:"center",flexWrap:"wrap"}}>
            <span className="rv-chip"><FileText size={12}/> {selectedPaper.title}</span>
            <span className="rv-chip"><ShieldCheck size={12}/> Selected project context</span>
          </div>
        )}
      </section>

      {error && <div className="rv-error"><AlertTriangle size={17}/><div>{error}<div style={{marginTop:5,fontSize:11}}>Check that the backend is running and Gemini is configured, then retry.</div></div></div>}

      {review && (
        <div className="rv-tabs">
          {[
            ["overview","Overview"],["title","Title & Novelty"],["review","Section Review"],
            ["concerns","Major Concerns"],["questions","Reviewer Questions"],["improvement","Improvement Plan"]
          ].map(([id,label]) => (
            <button key={id} className={`rv-tab ${tab===id?"active":""}`} onClick={() => setTab(id)}>{label}</button>
          ))}
        </div>
      )}

      {!review ? (
        <div className="rv-empty">
          <div style={{width:52,height:52,borderRadius:16,background:"#eef8f3",color:"#157555",display:"grid",placeItems:"center",margin:"0 auto 13px"}}>
            <Target size={26}/>
          </div>
          <h2 style={{color:"#102b45"}}>Paper-specific review starts here</h2>
          <p>Choose the real project and manuscript. Leave the text box empty to review the latest extracted PDF analysis.</p>
        </div>
      ) : (
        <>
          {tab === "overview" && (
            <>
              <div className="rv-profile" style={{marginBottom:15}}>
                <div className="rv-stat"><small>WORDS REVIEWED</small><b>{review.paper_profile?.word_count?.toLocaleString() || "—"}</b></div>
                <div className="rv-stat"><small>SECTIONS FOUND</small><b>{review.paper_profile?.sections_present?.length ?? "—"}</b></div>
                <div className="rv-stat"><small>CITATION MARKERS</small><b>{review.paper_profile?.citation_marker_count ?? "—"}</b></div>
                <div className="rv-stat"><small>FIGURES / TABLES</small><b>{review.paper_profile?.figure_reference_count ?? 0} / {review.paper_profile?.table_reference_count ?? 0}</b></div>
              </div>

              <div className="rv-card">
                <span className="rv-label">SENIOR REVIEW SUMMARY</span>
                <h2>{review.paper_title}</h2>
                <p className="rv-muted">{review.overall_review || "No overall summary was returned."}</p>
                <div className="rv-callout" style={{marginTop:14}}>
                  <ShieldCheck size={16} style={{verticalAlign:"middle",marginRight:7}}/>
                  <strong>Grounded review:</strong> {review.review_metadata?.note || "Findings are based on the selected manuscript."}
                </div>
              </div>

              <div className="rv-card">
                <div className="rv-label">WHAT IS WORKING</div>
                <h2>Strengths found in this paper</h2>
                {strengths.length ? <ul className="rv-list">{strengths.map((x,i)=><li key={i}>{textOf(x)}</li>)}</ul> : <p className="rv-muted">No explicit strengths were returned.</p>}
              </div>

              <div className="rv-card">
                <div className="rv-label">TOP PRIORITIES</div>
                <h2>What should be fixed first</h2>
                {priorities.length ? priorities.map((x,i)=>
                  <div className="rv-priority" key={i}><span className="rv-num">{x.priority || i+1}</span><div><strong>{x.section || "Paper"} — {x.action || textOf(x)}</strong><div className="rv-muted">{x.reason || ""}</div></div></div>
                ) : <p className="rv-muted">No priority actions were returned.</p>}
              </div>
            </>
          )}

          {tab === "title" && (
            <div className="rv-columns">
              <section className="rv-card">
                <span className="rv-label">TITLE DIAGNOSTICS</span>
                <h2>Does the title match the actual paper?</h2>
                <div className="rv-callout" style={{marginTop:10}}>
                  <strong>Current title</strong><br/>{review.paper_title}
                </div>
                <p className="rv-muted">{review.title_review?.assessment || review.deterministic_title_diagnostics?.issues?.join(" ")}</p>
                {asList(review.title_review?.problems).length > 0 && <ul className="rv-list">{asList(review.title_review.problems).map((x,i)=><li key={i}>{textOf(x)}</li>)}</ul>}
                {review.title_review?.recommended_title_direction && <div className="rv-callout good" style={{marginTop:12}}><strong>Direction:</strong> {review.title_review.recommended_title_direction}</div>}
              </section>
              <section className="rv-card">
                <span className="rv-label">TITLE OPTIONS GENERATED FROM THIS PAPER</span>
                <h2>More precise title directions</h2>
                <div style={{display:"grid",gap:10,marginTop:12}}>
                  {titleSuggestions.length ? titleSuggestions.map((x,i)=><div className="rv-suggestion" key={i}><strong>{x.title || textOf(x)}</strong><span>{x.why_it_fits_this_paper || x.why || ""}</span></div>) : <p className="rv-muted">No title alternatives returned.</p>}
                </div>
              </section>
            </div>
          )}

          {tab === "review" && (
            <div className="rv-grid">
              {sectionCards.map(([label,data,Icon]) => (
                <section className="rv-section-card" key={label}>
                  <div className="rv-section-head"><div className="rv-icon"><Icon size={18}/></div><div><span className="rv-label">{label.toUpperCase()}</span><div style={{fontWeight:850}}>{data?.assessment || "Section-specific review"}</div></div></div>
                  {asList(data?.strengths).length>0 && <><div className="rv-label" style={{display:"block",marginTop:14}}>STRENGTHS</div><ul className="rv-list">{asList(data.strengths).slice(0,5).map((x,i)=><li key={i}>{textOf(x)}</li>)}</ul></>}
                  {asList(data?.concerns).length>0 && <><div className="rv-label" style={{display:"block",marginTop:13}}>CONCERNS</div><ul className="rv-list">{asList(data.concerns).slice(0,6).map((x,i)=><li key={i}>{textOf(x)}</li>)}</ul></>}
                  {asList(data?.missing_details || data?.missing_analysis || data?.missing_discussion_points).length>0 && <div className="rv-callout warn" style={{marginTop:12}}><strong>Missing / under-specified:</strong><br/>{asList(data.missing_details || data.missing_analysis || data.missing_discussion_points).slice(0,5).map(textOf).join(" • ")}</div>}
                </section>
              ))}
            </div>
          )}

          {tab === "concerns" && (
            <>
              <div className="rv-columns">
                <section className="rv-card">
                  <span className="rv-label">MAJOR CONCERNS</span><h2>Issues that affect scientific strength</h2>
                  {concerns.length ? concerns.map((x,i)=><div className="rv-item" style={{marginTop:10}} key={i}><strong>{x.section || "Major concern"} — {x.issue || textOf(x)}</strong><p>{x.evidence || ""}</p><p><b>Why it matters:</b> {x.why_it_matters || ""}</p><p><b>Revision:</b> {x.recommended_revision || ""}</p></div>) : <p className="rv-muted">No major concerns returned.</p>}
                </section>
                <section className="rv-card">
                  <span className="rv-label">TECHNICAL ISSUES</span><h2>Technical and reproducibility checks</h2>
                  {technical.length ? technical.map((x,i)=><div className="rv-item" style={{marginTop:10}} key={i}><strong>{x.section || "Technical issue"} <span className="rv-chip">{x.severity || "review"}</span></strong><p>{x.issue || textOf(x)}</p><p><b>Fix:</b> {x.fix || ""}</p></div>) : <p className="rv-muted">No technical issues returned.</p>}
                </section>
              </div>
              <section className="rv-card">
                <span className="rv-label">MINOR CONCERNS</span>
                {minor.length ? <ul className="rv-list">{minor.map((x,i)=><li key={i}>{textOf(x)}</li>)}</ul> : <p className="rv-muted">No minor concerns returned.</p>}
              </section>
            </>
          )}

          {tab === "questions" && (
            <section className="rv-card">
              <span className="rv-label">QUESTIONS AN AUTHOR SHOULD BE READY TO ANSWER</span>
              <h2>Reviewer questions</h2>
              {questions.length ? questions.map((x,i)=><div className="rv-priority" key={i}><span className="rv-num">Q{i+1}</span><div>{textOf(x)}</div></div>) : <p className="rv-muted">No reviewer questions returned.</p>}
              <div className="rv-callout" style={{marginTop:15}}><Info size={16} style={{verticalAlign:"middle",marginRight:7}}/> These are simulated research-review questions generated from the selected manuscript, not comments from an actual venue.</div>
            </section>
          )}

          {tab === "improvement" && (
            <>
              <section className="rv-card">
                <div style={{display:"flex",justifyContent:"space-between",gap:12,alignItems:"flex-start"}}>
                  <div><span className="rv-label">PAPER-SPECIFIC IMPROVEMENT ENGINE</span><h2>Turn reviewer findings into an implementation plan</h2><p className="rv-muted">{plan?.overall_plan || "Generate a plan from the actual manuscript and current review."}</p></div>
                  <button className="rv-button" onClick={runPlan} disabled={planning}>{planning?<Loader2 size={16}/>:<Sparkles size={16}/>} {planning?"Building plan…":"Generate Improvement Plan"}</button>
                </div>
              </section>

              {plan && (
                <>
                  <section className="rv-card">
                    <span className="rv-label">TITLE IMPROVEMENT</span><h2>{plan.title_improvement?.assessment || "Title analysis"}</h2>
                    <div className="rv-callout" style={{marginTop:10}}><strong>Current:</strong> {plan.title_improvement?.current_title || review.paper_title}<br/><strong>Direction:</strong> {plan.title_improvement?.recommended_direction || "—"}</div>
                    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(250px,1fr))",gap:10,marginTop:12}}>
                      {asList(plan.title_improvement?.title_suggestions).map((x,i)=><div className="rv-suggestion" key={i}><strong>{x.title || textOf(x)}</strong><span>{x.why || ""}</span></div>)}
                    </div>
                  </section>
                  <section className="rv-card">
                    <span className="rv-label">PRIORITY ACTIONS</span><h2>What to implement first</h2>
                    {planActions.length ? planActions.map((x,i)=><div className="rv-item" style={{marginTop:10}} key={i}><div style={{display:"flex",justifyContent:"space-between",gap:10}}><strong>{x.section || "Paper"} · {x.problem || textOf(x)}</strong><span className="rv-chip">{x.priority || "MEDIUM"}</span></div><p>{x.evidence || ""}</p><p><b>Why:</b> {x.why_it_matters || ""}</p><p><b>Action:</b> {x.recommended_action || ""}</p></div>) : <p className="rv-muted">Click Generate Improvement Plan.</p>}
                  </section>
                  <section className="rv-card">
                    <span className="rv-label">SECTION-BY-SECTION</span><h2>Specific manuscript changes</h2>
                    {sectionImprovements.length ? sectionImprovements.map((x,i)=><div className="rv-priority" key={i}><span className="rv-num">{i+1}</span><div><strong>{x.section || "Section"} — {x.current_issue || ""}</strong><div className="rv-muted">{x.recommended_change || textOf(x)}</div>{x.example_of_change && <div className="rv-callout" style={{marginTop:7}}><b>Example:</b> {x.example_of_change}</div>}</div></div>) : <p className="rv-muted">No section-specific actions returned.</p>}
                  </section>
                  <div className="rv-columns">
                    <section className="rv-card"><span className="rv-label">QUICK FIXES</span><ul className="rv-list">{asList(plan.quick_fixes).map((x,i)=><li key={i}>{textOf(x)}</li>)}</ul></section>
                    <section className="rv-card"><span className="rv-label">LONG-TERM IMPROVEMENTS</span><ul className="rv-list">{asList(plan.long_term_improvements).map((x,i)=><li key={i}>{textOf(x)}</li>)}</ul></section>
                  </div>
                </>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
