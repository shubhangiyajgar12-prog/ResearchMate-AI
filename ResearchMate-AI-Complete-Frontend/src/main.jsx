import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  BrowserRouter,
  NavLink,
  Routes,
  Route,
  useNavigate,
} from "react-router-dom";

import {
  Search,
  Bell,
  ChevronDown,
  ChevronRight,
  ArrowUpRight,
  BookOpen,
  Compass,
  PenLine,
  ShieldCheck,
  MessageSquare,
  Rocket,
  Bot,
  Plus,
  CalendarDays,
  FileText,
  Target,
  BarChart3,
  Clock3,
  CheckCircle2,
  Sparkles,
  Activity,
  Menu,
  X,
} from "lucide-react";

import "./index.css";
import "./literature_clean_ui.css";
import OriginalityPage from "./OriginalityPage";
import WritingPage from "./WritingPage";
import ReviewPage from "./ReviewPage";
import PublicationAssistant from "./PublicationAssistant";
import ConferencePage from "./ConferencePage";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8001";

/* -------------------------------------------------------
   API ERROR HELPERS
   Convert FastAPI/Pydantic error objects into readable text.
------------------------------------------------------- */

const getApiErrorMessage = (data, fallback = "Something went wrong.") => {
  if (!data) return fallback;

  if (typeof data === "string") {
    return data;
  }

  if (typeof data.detail === "string") {
    return data.detail;
  }

  if (Array.isArray(data.detail)) {
    return data.detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item?.msg) return item.msg;
        if (item?.message) return item.message;
        return JSON.stringify(item);
      })
      .join(", ");
  }

  if (data.detail && typeof data.detail === "object") {
    if (data.detail.msg) return data.detail.msg;
    if (data.detail.message) return data.detail.message;
    return JSON.stringify(data.detail);
  }

  if (typeof data.message === "string") {
    return data.message;
  }

  return fallback;
};

const normalizeAuthors = (authors) => {
  if (Array.isArray(authors)) {
    return authors
      .map((author) => {
        if (typeof author === "string") return author;
        if (author?.name) return author.name;
        if (author?.display_name) return author.display_name;
        if (author?.author?.name) return author.author.name;
        if (author?.author?.display_name) return author.author.display_name;
        return null;
      })
      .filter(Boolean);
  }

  if (typeof authors === "string") {
    return authors
      .split(",")
      .map((author) => author.trim())
      .filter(Boolean);
  }

  if (authors && typeof authors === "object") {
    const nested = authors.authors || authors.items || authors.data;
    if (Array.isArray(nested)) return normalizeAuthors(nested);

    const name =
      authors.name ||
      authors.display_name ||
      authors.author?.name ||
      authors.author?.display_name;

    return name ? [name] : [];
  }

  return [];
};

const parseApiResponse = async (response) => {
  // Some FastAPI/proxy configurations can return JSON without a strict
  // application/json content-type. Always read the body once and attempt
  // JSON parsing before falling back to plain text.
  const text = await response.text();
  if (!text) return {};

  try {
    return JSON.parse(text);
  } catch {
    return { detail: text };
  }
};

/* -------------------------------------------------------
   NAVIGATION
------------------------------------------------------- */

const navigation = [
  {
    label: "Dashboard",
    path: "/",
    icon: BarChart3,
  },
  {
    label: "Research Discovery",
    path: "/discovery",
    icon: Compass,
  },
  {
    label: "Literature Intelligence",
    path: "/literature",
    icon: BookOpen,
  },
  {
    label: "Research Writing",
    path: "/writing",
    icon: PenLine,
  },
  {
    label: "Originality & Citations",
    path: "/originality",
    icon: ShieldCheck,
  },
  {
    label: "AI Review & Improvement",
    path: "/review",
    icon: MessageSquare,
  },
  {
    label: "Publication Assistant",
    path: "/publication",
    icon: Rocket,
  },
  {
    label: "Conference Intelligence",
    path: "/conferences",
    icon: CalendarDays,
  },
];

/* -------------------------------------------------------
   MODULES
------------------------------------------------------- */

const modules = [
  {
    number: "01",
    title: "Research Discovery",
    description:
      "Validate your idea, discover gaps and shape a strong research direction.",
    icon: Compass,
    color: "teal",
    capabilities: "5 capabilities",
    path: "/discovery",
  },
  {
    number: "02",
    title: "Literature Intelligence",
    description:
      "Find, understand and compare the literature behind your research.",
    icon: BookOpen,
    color: "blue",
    capabilities: "5 capabilities",
    path: "/literature",
  },
  {
    number: "03",
    title: "Research Writing",
    description:
      "Build a strong academic manuscript with contextual writing tools.",
    icon: PenLine,
    color: "purple",
    capabilities: "5 capabilities",
    path: "/writing",
  },
  {
    number: "04",
    title: "Originality & Citations",
    description:
      "Check similarity, plagiarism risk and citation quality.",
    icon: ShieldCheck,
    color: "amber",
    capabilities: "5 capabilities",
    path: "/originality",
  },
  {
    number: "05",
    title: "AI Review & Improvement",
    description:
      "Simulate peer review, understand feedback and improve your paper.",
    icon: MessageSquare,
    color: "red",
    capabilities: "5 capabilities",
    path: "/review",
  },
  {
    number: "06",
    title: "Publication Assistant",
    description:
      "Find suitable venues and manage the path to publication.",
    icon: Rocket,
    color: "green",
    capabilities: "5 capabilities",
    path: "/publication",
  },
];

/* -------------------------------------------------------
   SIDEBAR
------------------------------------------------------- */

function Sidebar({ mobileOpen, setMobileOpen }) {
  return (
    <>
      {mobileOpen && (
        <div
          className="sidebar-overlay"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside className={`sidebar ${mobileOpen ? "sidebar-open" : ""}`}>
        <div className="brand">
          <div className="brand-logo">
            <Sparkles size={22} />
          </div>

          <div>
            <div className="brand-name">
              ResearchMate <span>AI</span>
            </div>

            <div className="brand-subtitle">
              RESEARCH PUBLICATION
              <br />
              ASSISTANT
            </div>
          </div>

          <button
            className="mobile-close"
            onClick={() => setMobileOpen(false)}
          >
            <X size={20} />
          </button>
        </div>

        <div className="sidebar-section-label">MAIN</div>

        <nav className="sidebar-nav">
          {navigation.map((item) => {
            const Icon = item.icon;

            return (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === "/"}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  `sidebar-link ${isActive ? "active" : ""}`
                }
              >
                <Icon size={18} strokeWidth={1.8} />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        <div className="sidebar-divider" />

        <div className="sidebar-section-label">TOOLS</div>

        <div className="mentor-sidebar-link">
          <div className="mentor-sidebar-icon">
            <Bot size={18} />
          </div>

          <div className="mentor-sidebar-text">
            <span>Research Mentor</span>
            <small>Beta</small>
          </div>

          <span className="online-dot" />
        </div>

        <div className="sidebar-bottom">
          <div className="sidebar-project">
            <div className="sidebar-project-icon">
              <FileText size={17} />
            </div>

            <div className="sidebar-project-info">
              <span>ACTIVE PROJECT</span>
              <strong>Explainable AI for Rural...</strong>

              <div className="mini-progress">
                <div style={{ width: "68%" }} />
              </div>
            </div>

            <b>68%</b>
          </div>

          <div className="sidebar-user">
            <div className="user-avatar">R</div>

            <div>
              <strong>Researcher</strong>
              <span>Student Workspace</span>
            </div>

            <ChevronDown size={15} />
          </div>
        </div>
      </aside>
    </>
  );
}

/* -------------------------------------------------------
   TOPBAR
------------------------------------------------------- */

function Topbar({ setMobileOpen }) {
  const [notificationCount, setNotificationCount] = React.useState(0);
  React.useEffect(() => { fetch(`${API_BASE_URL}/notifications`).then(r=>r.json()).then(d=>setNotificationCount((d||[]).filter(n=>!n.is_read).length)).catch(()=>{}); }, []);
  return (
    <header className="topbar">
      <div className="topbar-left">
        <button
          className="mobile-menu"
          onClick={() => setMobileOpen(true)}
        >
          <Menu size={21} />
        </button>

        <div className="breadcrumb">
          <span>ResearchMate</span>
          <ChevronRight size={14} />
          <strong>Research Workspace</strong>
        </div>
      </div>

      <div className="topbar-actions">
        <div className="global-search">
          <Search size={17} />
          <input
            placeholder="Search papers, topics, or ask your research question..."
          />
          <kbd>Ctrl K</kbd>
        </div>

        <button className="notification-btn" title={`${notificationCount} unread notifications`} onClick={() => window.location.assign("/conferences")}>
          <Bell size={19} />
          {notificationCount > 0 && <span>{notificationCount > 9 ? "9+" : notificationCount}</span>}
        </button>

        <button className="profile-button">
          <div className="profile-avatar">R</div>

          <span>Researcher</span>

          <ChevronDown size={15} />
        </button>
      </div>
    </header>
  );
}

/* -------------------------------------------------------
   PROGRESS
------------------------------------------------------- */

function ResearchJourney() {
  const steps = [
    "Discovery",
    "Literature",
    "Writing",
    "Originality",
    "AI Review",
    "Publication",
  ];

  return (
    <div className="research-journey">
      <div className="journey-header">
        <span>Research journey</span>
        <small>4 of 6 modules active</small>
      </div>

      <div className="journey-line">
        {steps.map((step, index) => {
          const completed = index < 4;

          return (
            <div className="journey-step" key={step}>
              <div
                className={`journey-circle ${
                  completed ? "completed" : ""
                }`}
              >
                {completed ? (
                  <CheckCircle2 size={16} />
                ) : (
                  index + 1
                )}
              </div>

              <span>{step}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* -------------------------------------------------------
   ACTIVE PROJECT
------------------------------------------------------- */

function ActiveProjectCard() {
  return (
    <div className="active-project-card">
      <div className="project-top">
        <div>
          <div className="eyebrow green">
            <span className="status-dot" />
            ACTIVE PROJECT
          </div>

          <h2>Explainable AI for Rural Healthcare Diagnosis</h2>

          <p className="project-category">
            Literature & Methodology
          </p>
        </div>

        <div className="completion-ring">
          <div className="completion-inner">
            <strong>68%</strong>
            <span>Complete</span>
          </div>
        </div>
      </div>

      <p className="project-description">
        Developing interpretable deep learning models for early
        disease detection in resource-constrained rural healthcare
        settings.
      </p>

      <ResearchJourney />
    </div>
  );
}

/* -------------------------------------------------------
   MENTOR CARD
------------------------------------------------------- */

function MentorCard() {
  const navigate = useNavigate();

  return (
    <div className="mentor-card">
      <div className="mentor-visual">
        <div className="mentor-orb">
          <Bot size={30} />
        </div>

        <div className="mentor-orb-small one" />
        <div className="mentor-orb-small two" />
      </div>

      <div className="eyebrow">
        AI RESEARCH MENTOR
      </div>

      <h3>Your research, guided by AI.</h3>

      <p>
        Get guidance, clarify concepts and improve your research
        workflow with AI.
      </p>

      <button
        className="light-button"
        onClick={() => navigate("/discovery")}
      >
        Start a conversation
        <ArrowUpRight size={16} />
      </button>
    </div>
  );
}

/* -------------------------------------------------------
   METRIC CARD
------------------------------------------------------- */

function MetricCard({
  icon: Icon,
  value,
  label,
  trend,
  color,
}) {
  return (
    <div className={`metric-card ${color}`}>
      <div className="metric-top">
        <div className="metric-icon">
          <Icon size={20} />
        </div>

        <div className="metric-chart">
          <span />
          <span />
          <span />
          <span />
          <span />
          <span />
        </div>
      </div>

      <strong>{value}</strong>

      <span className="metric-label">{label}</span>

      <div className="metric-trend">
        <ArrowUpRight size={12} />
        {trend}
      </div>
    </div>
  );
}

/* -------------------------------------------------------
   MODULE CARD
------------------------------------------------------- */

function ModuleCard({ module }) {
  const Icon = module.icon;
  const navigate = useNavigate();

  return (
    <button
      className={`module-card module-${module.color}`}
      onClick={() => navigate(module.path)}
    >
      <div className="module-header">
        <div className="module-icon">
          <Icon size={19} />
        </div>

        <span>{module.number}</span>
      </div>

      <h3>{module.title}</h3>

      <p>{module.description}</p>

      <div className="module-footer">
        <span>{module.capabilities}</span>

        <div className="module-arrow">
          <ArrowUpRight size={16} />
        </div>
      </div>
    </button>
  );
}

/* -------------------------------------------------------
   ACTIVITY
------------------------------------------------------- */

function BottomDashboard() {
  return (
    <div className="bottom-dashboard">
      <div className="bottom-card">
        <div className="section-card-header">
          <div>
            <span className="small-label">
              <Activity size={14} />
              RECENT ACTIVITY
            </span>

            <h3>What you've been working on</h3>
          </div>

          <button>View all →</button>
        </div>

        <div className="activity-list">
          <div className="activity-row">
            <div className="activity-icon blue">
              <Search size={16} />
            </div>

            <div>
              <strong>Analyzed research gap</strong>
              <span>
                Explainable AI for Rural Healthcare Diagnosis
              </span>
            </div>

            <small>2 hours ago</small>
          </div>

          <div className="activity-row">
            <div className="activity-icon purple">
              <BookOpen size={16} />
            </div>

            <div>
              <strong>Reviewed 8 research papers</strong>
              <span>Literature Intelligence</span>
            </div>

            <small>Yesterday</small>
          </div>

          <div className="activity-row">
            <div className="activity-icon green">
              <PenLine size={16} />
            </div>

            <div>
              <strong>Updated methodology section</strong>
              <span>Research Writing</span>
            </div>

            <small>2 days ago</small>
          </div>
        </div>
      </div>

      <div className="bottom-card">
        <div className="section-card-header">
          <div>
            <span className="small-label">
              <CalendarDays size={14} />
              UPCOMING DEADLINES
            </span>

            <h3>Stay ahead of submissions</h3>
          </div>

          <button>View all →</button>
        </div>

        <div className="deadline-list">
          <div className="deadline-row">
            <div className="calendar-box">
              <span>OCT</span>
              <strong>15</strong>
            </div>

            <div>
              <strong>ICML 2026 Submission</strong>
              <span>Full paper submission</span>
            </div>

            <b>30 days</b>
          </div>

          <div className="deadline-row">
            <div className="calendar-box">
              <span>NOV</span>
              <strong>02</strong>
            </div>

            <div>
              <strong>Research Progress Review</strong>
              <span>Internal review</span>
            </div>

            <b>48 days</b>
          </div>
        </div>
      </div>

      <div className="bottom-card insight-card">
        <div className="section-card-header">
          <div>
            <span className="small-label">
              <Sparkles size={14} />
              RESEARCH INSIGHTS
            </span>

            <h3>Ideas worth exploring</h3>
          </div>

          <button>View all →</button>
        </div>

        <div className="insight-content">
          <div className="insight-icon">
            <Target size={20} />
          </div>

          <div>
            <strong>
              Focus on recent papers from 2024–2026
            </strong>

            <p>
              Recent literature may help strengthen your
              methodology and research gap.
            </p>
          </div>
        </div>

        <div className="insight-link">
          Explore Literature Intelligence
          <ArrowUpRight size={15} />
        </div>
      </div>
    </div>
  );
}

/* -------------------------------------------------------
   DASHBOARD
------------------------------------------------------- */

function Dashboard() {
  const navigate = useNavigate();

  return (
    <div className="dashboard-page">
      <div className="dashboard-heading">
        <div>
          <div className="eyebrow">
            TURN IDEAS INTO IMPACT
          </div>

          <h1>
            Good afternoon, <span>Researcher</span>
          </h1>

          <p>
            Your AI-powered workspace for smarter research and
            faster publication.
          </p>
        </div>

        <div className="heading-right">
          <span>Saturday, 20 September 2026</span>
          <small>Keep exploring. Great research takes time.</small>
        </div>
      </div>

      <div className="hero-grid">
        <div className="quote-card">
          <div className="quote-overlay">
            <span>“</span>

            <h2>
              Research
              <br />
              today,
              <br />
              better
              <br />
              tomorrow.
            </h2>

            <div className="quote-line" />

            <small>ResearchMate AI</small>
          </div>
        </div>

        <ActiveProjectCard />

        <MentorCard />
      </div>

      <div className="metrics-grid">
        <MetricCard
          icon={BookOpen}
          value="42"
          label="Relevant papers"
          trend="+8 this week"
          color="blue"
        />

        <MetricCard
          icon={Target}
          value="84%"
          label="Novelty indicator"
          trend="Evidence-backed"
          color="teal"
        />

        <MetricCard
          icon={FileText}
          value="72%"
          label="Paper readiness"
          trend="+12% this month"
          color="purple"
        />

        <MetricCard
          icon={CalendarDays}
          value="30 days"
          label="Next deadline"
          trend="1 tracked CFP"
          color="amber"
        />
      </div>

      <section className="modules-section">
        <div className="section-heading">
          <div>
            <h2>Research Modules</h2>
            <p>
              Six focused workspaces to support your
              research-to-publication journey.
            </p>
          </div>

          <button onClick={() => navigate("/discovery")}>
            View all modules
            <ArrowUpRight size={15} />
          </button>
        </div>

        <div className="modules-grid">
          {modules.map((module) => (
            <ModuleCard key={module.number} module={module} />
          ))}
        </div>
      </section>

      <BottomDashboard />
    </div>
  );
}

/* -------------------------------------------------------
   DISCOVERY PAGE
------------------------------------------------------- */

function Discovery() {
  const [topic, setTopic] = useState(
    "Explainable AI for Rural Healthcare Diagnosis"
  );
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState("");

  async function analyzeResearch() {
    if (!topic.trim()) {
      setError("Please enter a research topic.");
      return;
    }

    setLoading(true);
    setError("");
    setResults(null);

    try {
      const post = async (endpoint, body) => {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });

        if (!response.ok) throw new Error(`${endpoint} failed`);
        return response.json();
      };

      const cleanTopic = topic.trim();
      const topicData = await post("/discovery/topic-validation", {
        topic: cleanTopic,
      });
      const noveltyData = await post("/discovery/novelty-analysis", {
        topic: cleanTopic,
      });
      const gapData = await post("/discovery/research-gap", {
        topic: cleanTopic,
      });
      const questionsData = await post("/discovery/research-questions", {
        topic: cleanTopic,
        research_gaps: gapData.identified_gaps || [],
      });
      const feasibilityData = await post("/discovery/feasibility", {
        topic: cleanTopic,
      });

      setResults({
        topic: topicData,
        novelty: noveltyData,
        gap: gapData,
        questions: questionsData,
        feasibility: feasibilityData,
      });
    } catch (err) {
      console.error(err);
      setError(
        "Backend connection failed. Make sure FastAPI is running on port 8001."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="workspace-page discovery-page">
      <div className="page-title discovery-title">
        <div>
          <div className="eyebrow">RESEARCH DISCOVERY</div>
          <h1>Discover a stronger research direction.</h1>
          <p>
            Validate your idea, identify research gaps and transform
            your topic into a researchable direction.
          </p>
        </div>
        <div className="discovery-status">
          <span className="status-dot" />
          AI Discovery Engine
        </div>
      </div>

      <div className="topic-input-card">
        <div className="topic-input-header">
          <div className="large-icon teal">
            <Compass size={22} />
          </div>
          <div>
            <h2>Start with your research idea</h2>
            <p>
              Analyze your topic across specificity, novelty, gaps,
              questions and feasibility.
            </p>
          </div>
        </div>

        <label>Research Topic</label>
        <textarea
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="Example: Explainable AI for rural healthcare diagnosis"
          rows={4}
        />

        <div className="topic-input-footer">
          <span>{topic.trim().length} characters</span>
          <button
            className="primary-button analyze-button"
            onClick={analyzeResearch}
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="button-spinner" />
                Analyzing Research...
              </>
            ) : (
              <>
                Analyze Research
                <ArrowUpRight size={17} />
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="discovery-error">
          <ShieldCheck size={17} />
          {error}
        </div>
      )}

      {!results && !loading && !error && (
        <div className="discovery-empty-state">
          <div className="discovery-empty-icon">
            <Sparkles size={27} />
          </div>
          <h2>Your research analysis starts here</h2>
          <p>
            ResearchMate will evaluate specificity, novelty, research
            gaps, research questions and feasibility.
          </p>
          <div className="analysis-pipeline">
            {["Topic", "Novelty", "Research Gap", "Questions", "Feasibility"].map(
              (item, index) => (
                <React.Fragment key={item}>
                  <span>
                    <CheckCircle2 size={14} />
                    {item}
                  </span>
                  {index < 4 && <ChevronRight size={15} />}
                </React.Fragment>
              )
            )}
          </div>
        </div>
      )}

      {loading && (
        <div className="discovery-loading">
          <div className="loading-orb">
            <Bot size={25} />
          </div>
          <h3>ResearchMate is analyzing your topic...</h3>
          <p>
            Checking topic structure, novelty, gaps, research questions
            and feasibility.
          </p>
          <div className="loading-bar">
            <div />
          </div>
        </div>
      )}

      {results && !loading && (
        <div className="discovery-results">
          <div className="analysis-summary-card">
            <div>
              <span className="small-label">
                <CheckCircle2 size={14} />
                ANALYSIS COMPLETE
              </span>
              <h2>Research direction overview</h2>
              <p>{results.topic.validation_summary}</p>
              <div className="plain-meaning">
                <strong>In simple words:</strong>
                <span>
                  This is a preliminary AI screening. It does not prove
                  that your topic is novel; the next step is evidence from
                  real academic papers.
                </span>
              </div>
            </div>
            <div className="research-area-badge">
              {results.topic.research_field}
            </div>
          </div>

          <div className="discovery-overview-grid">
            <div className="discovery-stat-card">
              <span>SPECIFICITY</span>
              <strong>{results.topic.specificity}</strong>
              <p>Topic definition quality</p>
            </div>
            <div className="discovery-stat-card">
              <span>NOVELTY</span>
              <strong>{results.novelty.novelty_score}%</strong>
              <p>{results.novelty.novelty_level}</p>
            </div>
            <div className="discovery-stat-card">
              <span>FEASIBILITY</span>
              <strong>{results.feasibility.feasibility_score}%</strong>
              <p>{results.feasibility.overall_feasibility}</p>
            </div>
          </div>

          <div className="analysis-two-column">
            <div className="analysis-panel">
              <div className="analysis-panel-header">
                <div className="analysis-panel-icon purple">
                  <Target size={19} />
                </div>
                <div>
                  <span>NOVELTY ANALYSIS</span>
                  <h3>What does the novelty result mean?</h3>
                </div>
              </div>

              <div className="novelty-score-row">
                <div className="novelty-score">
                  {results.novelty.novelty_score}
                  <small>/100</small>
                </div>
                <div>
                  <strong>{results.novelty.novelty_level}</strong>
                  <p>{results.novelty.research_area}</p>
                </div>
              </div>

              <div className="analysis-text-box">
                <span>POTENTIAL GAP</span>
                <p>{results.novelty.potential_gap}</p>
                <div className="meaning-note">
                  <strong>What you should do:</strong>
                  <span>
                    Compare recent papers, methods, datasets and limitations
                    before making a novelty claim.
                  </span>
                </div>
              </div>

              <div className="recommendation-box">
                <Sparkles size={15} />
                <p>{results.novelty.recommendation}</p>
              </div>
            </div>

            <div className="analysis-panel">
              <div className="analysis-panel-header">
                <div className="analysis-panel-icon amber">
                  <Activity size={19} />
                </div>
                <div>
                  <span>FEASIBILITY</span>
                  <h3>What does the feasibility result mean?</h3>
                </div>
              </div>

              <div className="feasibility-score">
                <div
                  className="feasibility-progress"
                  style={{
                    "--progress": `${results.feasibility.feasibility_score}%`,
                  }}
                >
                  <strong>{results.feasibility.feasibility_score}%</strong>
                </div>
                <div>
                  <strong>{results.feasibility.overall_feasibility}</strong>
                  <p>Overall implementation screening</p>
                </div>
              </div>

              <div className="feasibility-grid">
                <div>
                  <span>Dataset</span>
                  <strong>{results.feasibility.dataset_feasibility}</strong>
                </div>
                <div>
                  <span>Computation</span>
                  <strong>
                    {results.feasibility.computational_feasibility}
                  </strong>
                </div>
                <div>
                  <span>Implementation</span>
                  <strong>
                    {results.feasibility.implementation_complexity}
                  </strong>
                </div>
                <div>
                  <span>Evaluation</span>
                  <strong>
                    {results.feasibility.evaluation_feasibility}
                  </strong>
                </div>
              </div>
            </div>
          </div>

          <div className="analysis-panel gap-panel">
            <div className="analysis-panel-header">
              <div className="analysis-panel-icon blue">
                <Search size={19} />
              </div>
              <div>
                <span>RESEARCH GAP</span>
                <h3>Potential gaps to investigate</h3>
              </div>
            </div>

            <p className="panel-description">
              These are preliminary possibilities generated from your topic.
              They are not confirmed research gaps yet. RAG will later
              validate them against actual papers and evidence.
            </p>

            <div className="gap-list">
              {results.gap.identified_gaps.map((gap, index) => (
                <div className="gap-item" key={index}>
                  <div className="gap-number">
                    {String(index + 1).padStart(2, "0")}
                  </div>
                  <p>{gap}</p>
                  <ArrowUpRight size={15} />
                </div>
              ))}
            </div>

            <div className="research-direction-box">
              <div>
                <Sparkles size={17} />
              </div>
              <div>
                <span>SUGGESTED RESEARCH DIRECTION</span>
                <p>{results.gap.research_direction}</p>
              </div>
            </div>
          </div>

          <div className="analysis-two-column">
            <div className="analysis-panel">
              <div className="analysis-panel-header">
                <div className="analysis-panel-icon teal">
                  <MessageSquare size={19} />
                </div>
                <div>
                  <span>RESEARCH QUESTIONS</span>
                  <h3>Questions your research should answer</h3>
                </div>
              </div>

              <div className="question-list">
                {results.questions.research_questions.map(
                  (question, index) => (
                    <div className="question-item" key={index}>
                      <span>RQ{index + 1}</span>
                      <p>{question}</p>
                    </div>
                  )
                )}
              </div>
            </div>

            <div className="analysis-panel">
              <div className="analysis-panel-header">
                <div className="analysis-panel-icon purple">
                  <Target size={19} />
                </div>
                <div>
                  <span>HYPOTHESIS</span>
                  <h3>What are you trying to prove?</h3>
                </div>
              </div>

              <div className="hypothesis-box">
                <div className="hypothesis-mark">H</div>
                <p>{results.questions.hypothesis}</p>
              </div>

              <div className="variables-section">
                <span>KEY VARIABLES</span>
                <div>
                  {results.questions.variables.map((variable, index) => (
                    <div className="variable-item" key={index}>
                      <CheckCircle2 size={13} />
                      {variable}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="analysis-panel keywords-panel">
            <div className="analysis-panel-header">
              <div className="analysis-panel-icon teal">
                <Search size={19} />
              </div>
              <div>
                <span>RESEARCH KEYWORDS</span>
                <h3>Keywords for the next literature search</h3>
              </div>
            </div>

            <div className="research-keywords">
              {results.topic.keywords.map((keyword, index) => (
                <span key={index}>{keyword}</span>
              ))}
            </div>
          </div>

          <div className="result-interpretation-card">
            <div className="result-interpretation-icon">
              <Sparkles size={21} />
            </div>
            <div>
              <span>HOW TO READ THIS ANALYSIS</span>
              <h3>Use this page to decide what to investigate next.</h3>
              <p>
                Topic validation checks whether the idea is clearly defined.
                Novelty is only a preliminary screening. Research gaps are
                hypotheses that need evidence. Research questions define what
                your study should answer, while feasibility checks whether the
                study appears practical.
              </p>
            </div>
          </div>

          <div className="next-action-card">
            <div className="next-action-icon">
              <Bot size={23} />
            </div>
            <div>
              <span>AI RESEARCH MENTOR</span>
              <h3>
                Next step: validate these findings against real
                academic literature.
              </h3>
              <p>
                The next phase will connect academic search, document
                retrieval, embeddings, RAG and agentic research analysis.
              </p>
            </div>
            <button onClick={() => (window.location.href = "/literature")}>
              Continue to Literature
              <ArrowUpRight size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}


/* -------------------------------------------------------
   PDF ANALYSIS
------------------------------------------------------- */

function PDFAnalysisSection() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [insights, setInsights] = useState(null);
  const [insightsLoading, setInsightsLoading] = useState(false);
  const [insightsError, setInsightsError] = useState("");

  const analyzePDF = async () => {
    if (!selectedFile) {
      setError("Please select a PDF research paper first.");
      return;
    }

    if (!selectedFile.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF files are supported.");
      return;
    }

    if (selectedFile.size > 10 * 1024 * 1024) {
      setError("PDF file size must be less than 10 MB.");
      return;
    }

    setLoading(true);
    setError("");
    setAnalysis(null);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const controller = new AbortController();
      const timeoutId = window.setTimeout(() => controller.abort(), 120000);

      let response;
      try {
        response = await fetch(
          `${API_BASE_URL}/literature/analyze-pdf`,
          {
            method: "POST",
            body: formData,
            signal: controller.signal,
          }
        );
      } finally {
        window.clearTimeout(timeoutId);
      }

      const data = await parseApiResponse(response);

      if (!response.ok) {
        throw new Error(
          getApiErrorMessage(data, "Unable to analyze the PDF.")
        );
      }

      setAnalysis(data);
    } catch (err) {
      console.error("PDF analysis request failed:", err);

      if (err?.name === "AbortError") {
        setError(
          "PDF analysis timed out after 2 minutes. Check that FastAPI is running on port 8001 and try again."
        );
      } else if (err instanceof TypeError && err.message === "Failed to fetch") {
        setError(
          `Cannot reach the ResearchMate backend at ${API_BASE_URL}. Make sure uvicorn is running on port 8001 and the browser page is opened from localhost/127.0.0.1.`
        );
      } else {
        setError(
          err.message ||
            "Something went wrong while analyzing the PDF."
        );
      }
    } finally {
      setLoading(false);
    }
  };

  const generateAIInsights = async () => {
    if (!analysis) {
      setInsightsError("Analyze the PDF first.");
      return;
    }

    setInsightsLoading(true);
    setInsightsError("");
    setInsights(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/literature/paper-insights`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            filename: analysis.filename || selectedFile?.name || "research-paper.pdf",
            title: analysis.title || null,
            abstract: analysis.abstract || null,
            methodology: analysis.methodology
              ? JSON.stringify(analysis.methodology)
              : null,
            dataset: analysis.dataset
              ? JSON.stringify(analysis.dataset)
              : null,
            results: analysis.results
              ? JSON.stringify(analysis.results)
              : null,
            key_findings: analysis.key_findings || [],
            limitations: analysis.limitations || null,
            future_work: analysis.future_work || null,
          }),
        }
      );

      const data = await parseApiResponse(response);

      if (!response.ok) {
        throw new Error(
          getApiErrorMessage(
            data,
            "Unable to generate AI research insights."
          )
        );
      }

      setInsights(data);
    } catch (err) {
      console.error(err);
      setInsightsError(
        err.message ||
          "Something went wrong while generating AI research insights."
      );
    } finally {
      setInsightsLoading(false);
    }
  };

  const renderInsightList = (items, emptyText) => {
    if (!items?.length) {
      return <p className="ai-mentor-empty">{emptyText}</p>;
    }

    return (
      <div className="ai-mentor-list">
        {items.map((item, index) => (
          <div className="ai-mentor-list-item" key={index}>
            <span>{index + 1}</span>
            <p>{item}</p>
          </div>
        ))}
      </div>
    );
  };

  const renderSimpleSection = (label, value) => {
    if (!value) return null;

    return (
      <div className="pdf-clean-card pdf-full-width-section">
        <div className="pdf-clean-card-header">
          <span>{label}</span>
        </div>
        <p>{String(value)}</p>
      </div>
    );
  };

  const renderMethodology = (methodology) => {
    if (!methodology) return null;

    const training = methodology.training || {};

    return (
      <section className="pdf-structured-card pdf-methodology-card pdf-full-width-section">
        <div className="pdf-structured-card-header">
          <div className="pdf-section-icon purple">
            <Activity size={18} />
          </div>
          <div>
            <span>METHODOLOGY</span>
            <h3>How the research was conducted</h3>
          </div>
        </div>

        <div className="pdf-method-top-grid">
          <div className="pdf-info-panel">
            <span>MODELS</span>
            <div className="pdf-tag-list">
              {(methodology.models || []).map((model, index) => (
                <span key={index}>{model}</span>
              ))}
            </div>
          </div>

          <div className="pdf-info-panel">
            <span>TEST TIME AUGMENTATION</span>
            <strong>
              {methodology.test_time_augmentation ? "Enabled" : "Not reported"}
            </strong>
          </div>
        </div>

        <div className="pdf-training-grid">
          <div className="pdf-training-item">
            <span>Epochs</span>
            <strong>{training.epochs || "—"}</strong>
            <small>How many complete passes the model made through the training data.</small>
          </div>
          <div className="pdf-training-item">
            <span>Batch Size</span>
            <strong>{training.batch_size || "—"}</strong>
            <small>How many training samples were processed together in one step.</small>
          </div>
          <div className="pdf-training-item">
            <span>Image Size</span>
            <strong>{training.image_size || "—"}</strong>
            <small>The image resolution used as input while training the model.</small>
          </div>
          <div className="pdf-training-item">
            <span>Optimizer</span>
            <strong>{training.optimizer || "—"}</strong>
            <small>The method used to update model weights during training.</small>
          </div>
        </div>

        {methodology.subsections?.length > 0 && (
          <div className="pdf-subsections">
            <div className="pdf-subsections-title">
              Methodology details
            </div>
            <div className="pdf-subsections-list">
              {methodology.subsections.map((section, index) => (
                <div className="pdf-subsection-item" key={index}>
                  <div className="pdf-subsection-number">
                    {section.number}
                  </div>
                  <div>
                    <h4>{section.title}</h4>
                    <p>{section.text}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>
    );
  };

  const renderDataset = (dataset) => {
    if (!dataset) return null;

    const datasetStats = [
      ["Training Videos", dataset.training_videos],
      ["Testing Videos", dataset.testing_videos],
      ["Video Duration", dataset.video_duration],
      ["Frame Rate", dataset.frame_rate],
      ["Resolution", dataset.resolution],
      ["Training Examples", dataset.training_examples],
      ["Train Split", dataset.train_split],
      ["Validation Split", dataset.validation_split],
    ];

    return (
      <section className="pdf-structured-card pdf-full-width-section">
        <div className="pdf-structured-card-header">
          <div className="pdf-section-icon blue">
            <BarChart3 size={18} />
          </div>
          <div>
            <span>DATASET / DATA</span>
            <h3>Dataset characteristics</h3>
          </div>
        </div>

        <div className="pdf-dataset-grid">
          {datasetStats.map(([label, value]) => (
            <div className="pdf-dataset-item" key={label}>
              <span>{label}</span>
              <strong>{value || "—"}</strong>
            </div>
          ))}
        </div>

        <div className="pdf-dataset-bottom">
          <div>
            <span>Augmentation</span>
            <div className="pdf-tag-list">
              {(dataset.augmentation || []).map((item, index) => (
                <span key={index}>{item}</span>
              ))}
            </div>
          </div>

          <div>
            <span>Processing</span>
            <div className="pdf-tag-list">
              {(dataset.processing || []).map((item, index) => (
                <span key={index}>{item}</span>
              ))}
            </div>
          </div>
        </div>
      </section>
    );
  };

  const renderResults = (results) => {
    if (!results) return null;

    const validation = results.validation || {};
    const test = results.test || {};

    const metricCards = [
      {
        label: "mAP @ 0.5",
        value: validation.map_50 ?? "—",
        meaning: "How accurately the model detects and locates objects when a 0.5 overlap threshold is used."
      },
      {
        label: "mAP @ 0.5–0.95",
        value: validation.map_50_95 ?? "—",
        meaning: "A stricter overall detection score measured across multiple overlap thresholds."
      },
      {
        label: "Precision",
        value: validation.precision ?? "—",
        meaning: "How many of the detections predicted by the model were correct."
      },
      {
        label: "Recall",
        value: validation.recall ?? "—",
        meaning: "How many of the actual target objects were successfully detected."
      },
      {
        label: "Test mAP",
        value: test.map ?? "—",
        meaning: "Detection performance reported on the separate test dataset."
      },
      {
        label: "Test speed",
        value: test.fps != null ? `${test.fps} FPS` : "—",
        meaning: "Approximately how many video frames the model processed per second."
      }
    ];

    return (
      <section className="pdf-structured-card pdf-full-width-section pdf-results-modern">
        <div className="pdf-structured-card-header">
          <div className="pdf-section-icon green">
            <Target size={18} />
          </div>
          <div>
            <span>RESULTS</span>
            <h3>What did the researchers achieve?</h3>
          </div>
        </div>

        <div className="pdf-results-intro">
          <strong>Quick explanation</strong>
          <p>
            The numbers below describe two things: <b>how accurately</b> the
            model detects objects and <b>how quickly</b> it processes video.
            The values are reported results from the paper.
          </p>
        </div>

        <div className="pdf-modern-metric-grid">
          {metricCards.map((metric, index) => (
            <div className="pdf-modern-metric-card" key={index}>
              <span className="pdf-modern-metric-label">{metric.label}</span>
              <strong>{metric.value}</strong>
              <p>{metric.meaning}</p>
            </div>
          ))}
        </div>

        {(results.best_model || results.challenge_rank) && (
          <div className="pdf-result-highlights">
            {results.best_model && (
              <div className="pdf-result-highlight">
                <span>REPORTED MODEL</span>
                <strong>{results.best_model}</strong>
                <p>Model identified by the extracted paper analysis as the reported best model.</p>
              </div>
            )}
            {results.challenge_rank && (
              <div className="pdf-result-highlight">
                <span>CHALLENGE POSITION</span>
                <strong>#{results.challenge_rank}</strong>
                <p>Position reported by the paper in the referenced challenge.</p>
              </div>
            )}
          </div>
        )}

        <div className="pdf-result-interpretation">
          <div className="pdf-result-interpretation-icon">💡</div>
          <div>
            <strong>How should a researcher read this?</strong>
            <ul>
              <li><b>mAP, precision and recall</b> describe detection quality.</li>
              <li><b>FPS</b> describes processing speed, which matters for real-time video applications.</li>
              <li>Validation and test values should be read separately because they come from different evaluation data.</li>
              <li>A metric by itself does not prove that a method is suitable for every real-world setting; the dataset and experimental setup also matter.</li>
            </ul>
          </div>
        </div>

        {results.validation_models?.length > 0 && (
          <div className="pdf-table-section pdf-modern-table-section">
            <div className="pdf-table-title">
              <strong>Validation model comparison</strong>
              <span>Reported performance on the validation dataset.</span>
            </div>
            <div className="pdf-results-table-wrap">
              <table className="pdf-results-table">
                <thead>
                  <tr>
                    <th>Model</th>
                    <th>mAP @ 0.5</th>
                    <th>mAP @ 0.5–0.95</th>
                    <th>Precision</th>
                    <th>Recall</th>
                  </tr>
                </thead>
                <tbody>
                  {results.validation_models.map((row, index) => (
                    <tr key={index}>
                      <td>{row.model}</td>
                      <td>{row.values?.[0] ?? "—"}</td>
                      <td>{row.values?.[1] ?? "—"}</td>
                      <td>{row.values?.[2] ?? "—"}</td>
                      <td>{row.values?.[3] ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="pdf-table-guide">
              <b>Reading the table:</b> mAP = detection quality · Precision = correctness of positive predictions · Recall = coverage of actual targets.
            </div>
          </div>
        )}

        {results.test_models?.length > 0 && (
          <div className="pdf-table-section pdf-modern-table-section">
            <div className="pdf-table-title">
              <strong>Test model comparison</strong>
              <span>Reported performance on unseen test data and processing speed.</span>
            </div>
            <div className="pdf-results-table-wrap">
              <table className="pdf-results-table">
                <thead>
                  <tr>
                    <th>Model</th>
                    <th>Test mAP</th>
                    <th>Speed (FPS)</th>
                  </tr>
                </thead>
                <tbody>
                  {results.test_models.map((row, index) => (
                    <tr key={index}>
                      <td>{row.model}</td>
                      <td>{row.values?.[0] ?? "—"}</td>
                      <td>{row.values?.[1] ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="pdf-table-guide">
              <b>Reading the table:</b> Test mAP shows detection performance; FPS shows how quickly video frames were processed.
            </div>
          </div>
        )}
      </section>
    );
  };

  return (
    <div className="pdf-analysis-area">
      <div className="pdf-analysis-heading">
        <div>
          <span className="small-label">
            <FileText size={14} />
            PAPER ANALYSIS
          </span>
          <h2>Analyze a Research Paper</h2>
          <p>
            Upload a research paper PDF to extract its structure,
            methodology, dataset, results and key findings.
          </p>
        </div>

        <div className="pdf-analysis-badge">
          <span className="status-dot" />
          PDF Analyzer
        </div>
      </div>

      <div className="pdf-upload-card">
        <div className="pdf-upload-content">
          <div className="pdf-upload-icon">
            <FileText size={28} />
          </div>

          <div>
            <h3>Upload your research paper</h3>
            <p>
              PDF only · Maximum file size 10 MB
            </p>
          </div>
        </div>

        <label className="pdf-file-picker">
          <input
            type="file"
            accept=".pdf,application/pdf"
            onChange={(event) => {
              const file = event.target.files?.[0] || null;
              setSelectedFile(file);
              setAnalysis(null);
              setInsights(null);
              setInsightsError("");
              setError("");
            }}
          />
          <span>
            {selectedFile
              ? selectedFile.name
              : "Choose PDF"}
          </span>
        </label>

        {selectedFile && (
          <div className="pdf-selected-file">
            <FileText size={15} />
            <span>{selectedFile.name}</span>
            <small>
              {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
            </small>
          </div>
        )}

        <button
          className="primary-button pdf-analyze-button"
          onClick={analyzePDF}
          disabled={loading}
        >
          {loading ? (
            <>
              <span className="button-spinner" />
              Analyzing PDF...
            </>
          ) : (
            <>
              Analyze Paper
              <ArrowUpRight size={16} />
            </>
          )}
        </button>

        {error && (
          <div className="discovery-error pdf-analysis-error">
            <ShieldCheck size={17} />
            {error}
          </div>
        )}
      </div>

      {loading && (
        <div className="discovery-loading literature-loading">
          <div className="loading-orb">
            <FileText size={25} />
          </div>
          <h3>ResearchMate is analyzing your paper...</h3>
          <p>
            Extracting text and identifying the paper's
            abstract, methodology, dataset, results and limitations.
          </p>
          <div className="loading-bar">
            <div />
          </div>
        </div>
      )}

      {analysis && !loading && (
        <div className="pdf-analysis-results">
          <div className="pdf-analysis-summary">
            <div>
              <span className="small-label">
                <CheckCircle2 size={14} />
                ANALYSIS COMPLETE
              </span>

              <h2>
                {analysis.title || analysis.filename}
              </h2>

              <p>
                {analysis.filename}
              </p>
            </div>

            <div className="pdf-analysis-stats">
              <div>
                <strong>{analysis.page_count}</strong>
                <span>Pages</span>
              </div>

              <div>
                <strong>
                  {analysis.extracted_text_length.toLocaleString()}
                </strong>
                <span>Characters</span>
              </div>
            </div>
          </div>

          <div className="pdf-analysis-grid">
            {renderSimpleSection("ABSTRACT", analysis.abstract)}
            {renderMethodology(analysis.methodology)}
            {renderDataset(analysis.dataset)}
            {renderResults(analysis.results)}
            {renderSimpleSection("LIMITATIONS", analysis.limitations)}
            {renderSimpleSection("FUTURE WORK", analysis.future_work)}
          </div>

          <div className="pdf-findings-card pdf-key-findings-modern">
            <div className="analysis-panel-header">
              <div className="analysis-panel-icon teal">
                <Sparkles size={19} />
              </div>
              <div>
                <span>KEY FINDINGS</span>
                <h3>What the paper reports</h3>
              </div>
            </div>

            {analysis.key_findings?.length > 0 ? (
              <div className="pdf-modern-findings-grid">
                {analysis.key_findings.map((finding, index) => {
                  const text = String(finding || "");
                  let meaning = "This is a result explicitly extracted from the paper.";

                  if (/mAP@0\.5:0\.95/i.test(text)) {
                    meaning = "A broader detection score measured across several overlap thresholds.";
                  } else if (/mAP@0\.5/i.test(text)) {
                    meaning = "Measures detection and localization accuracy at a 0.5 overlap threshold.";
                  } else if (/precision/i.test(text)) {
                    meaning = "Shows how many predicted detections were correct.";
                  } else if (/recall/i.test(text)) {
                    meaning = "Shows how many actual target objects were detected.";
                  } else if (/fps/i.test(text)) {
                    meaning = "Shows how many video frames were processed per second.";
                  } else if (/test time augmentation|\btta\b/i.test(text)) {
                    meaning = "TTA means Test Time Augmentation, where transformed test inputs are also evaluated.";
                  } else if (/ranked|challenge/i.test(text)) {
                    meaning = "Reports the position achieved in the challenge referenced by the paper.";
                  }

                  return (
                    <article className="pdf-modern-finding-card" key={index}>
                      <div className="pdf-modern-finding-top">
                        <span>{String(index + 1).padStart(2, "0")}</span>
                        <small>REPORTED FINDING</small>
                      </div>
                      <p className="pdf-modern-finding-result">{text}</p>
                      <div className="pdf-modern-finding-meaning">
                        <b>In simple words</b>
                        <p>{meaning}</p>
                      </div>
                    </article>
                  );
                })}
              </div>
            ) : (
              <p className="pdf-no-data">No clear findings could be extracted automatically.</p>
            )}
          </div>

          <div className="pdf-keywords-card">
            <div className="analysis-panel-header">
              <div className="analysis-panel-icon blue">
                <Search size={19} />
              </div>
              <div>
                <span>RESEARCH KEYWORDS</span>
                <h3>Keywords detected in the paper</h3>
              </div>
            </div>

            {analysis.keywords?.length > 0 ? (
              <div className="research-keywords">
                {analysis.keywords.map((keyword, index) => (
                  <span key={index}>{keyword}</span>
                ))}
              </div>
            ) : (
              <p className="pdf-no-data">
                No explicit keywords were detected.
              </p>
            )}
          </div>

          <div className="pdf-analysis-note">
            <Sparkles size={18} />
            <div>
              <strong>Preliminary automated analysis</strong>
              <p>
                These sections are extracted from the PDF text and may
                require researcher verification. Later, this module can
                be connected to an LLM/RAG pipeline for deeper semantic
                analysis.
              </p>
            </div>
          </div>
        </div>
      )}

      {analysis && !loading && (
        <section className="ai-research-mentor">
          <div className="ai-mentor-header">
            <div className="ai-mentor-title">
              <div className="ai-mentor-icon">
                <Bot size={23} />
              </div>
              <div>
                <span>AI RESEARCH MENTOR</span>
                <h2>Understand the paper like a researcher.</h2>
                <p>
                  Gemini analyzes the extracted paper evidence and turns it
                  into research-oriented insights.
                </p>
              </div>
            </div>

            <button
              className="ai-mentor-button"
              onClick={generateAIInsights}
              disabled={insightsLoading}
            >
              {insightsLoading ? (
                <>
                  <span className="button-spinner" />
                  Generating...
                </>
              ) : (
                <>
                  <Sparkles size={16} />
                  Generate AI Insights
                </>
              )}
            </button>
          </div>

          {insightsError && (
            <div className="ai-mentor-error">
              <ShieldCheck size={17} />
              {insightsError}
            </div>
          )}

          {insightsLoading && (
            <div className="ai-mentor-loading">
              <div className="loading-orb">
                <Bot size={25} />
              </div>
              <div>
                <h3>AI Research Mentor is analyzing the paper...</h3>
                <p>
                  Identifying the research problem, objective, gaps,
                  contributions and possible future directions.
                </p>
              </div>
            </div>
          )}

          {insights && !insightsLoading && (
            <div className="ai-mentor-results">
              <div className="ai-mentor-hero-card">
                <div className="ai-mentor-hero-icon">
                  <Sparkles size={22} />
                </div>
                <div>
                  <span>AI-GENERATED RESEARCH INTERPRETATION</span>
                  <h3>Research Mentor Analysis</h3>
                  <p>
                    These insights are derived from the extracted paper
                    content and should be verified against the original paper.
                  </p>
                </div>
              </div>

              <div className="ai-mentor-two-column">
                <div className="ai-mentor-content-card">
                  <div className="ai-mentor-card-heading">
                    <div className="ai-mentor-card-icon teal">
                      <Target size={18} />
                    </div>
                    <div>
                      <span>RESEARCH PROBLEM</span>
                      <h3>What problem does this paper address?</h3>
                    </div>
                  </div>
                  <p className="ai-mentor-main-text">
                    {insights.research_problem ||
                      "No clear research problem was identified."}
                  </p>
                </div>

                <div className="ai-mentor-content-card">
                  <div className="ai-mentor-card-heading">
                    <div className="ai-mentor-card-icon blue">
                      <Target size={18} />
                    </div>
                    <div>
                      <span>RESEARCH OBJECTIVE</span>
                      <h3>What is the study trying to achieve?</h3>
                    </div>
                  </div>
                  <p className="ai-mentor-main-text">
                    {insights.research_objective ||
                      "No clear research objective was identified."}
                  </p>
                </div>
              </div>

              <div className="ai-mentor-content-card">
                <div className="ai-mentor-card-heading">
                  <div className="ai-mentor-card-icon purple">
                    <FileText size={18} />
                  </div>
                  <div>
                    <span>METHODOLOGY SUMMARY</span>
                    <h3>How the research was carried out</h3>
                  </div>
                </div>
                <p className="ai-mentor-main-text">
                  {insights.methodology_summary ||
                    "No methodology summary was generated."}
                </p>
              </div>

              <div className="ai-mentor-two-column">
                <div className="ai-mentor-content-card">
                  <div className="ai-mentor-card-heading">
                    <div className="ai-mentor-card-icon green">
                      <CheckCircle2 size={18} />
                    </div>
                    <div>
                      <span>KEY CONTRIBUTIONS</span>
                      <h3>What this paper contributes</h3>
                    </div>
                  </div>
                  {renderInsightList(
                    insights.key_contributions,
                    "No clear contributions were identified."
                  )}
                </div>

                <div className="ai-mentor-content-card">
                  <div className="ai-mentor-card-heading">
                    <div className="ai-mentor-card-icon amber">
                      <Search size={18} />
                    </div>
                    <div>
                      <span>RESEARCH GAPS</span>
                      <h3>Potential areas that remain open</h3>
                    </div>
                  </div>
                  {renderInsightList(
                    insights.research_gap,
                    "No specific research gaps were generated."
                  )}
                </div>
              </div>

              <div className="ai-mentor-two-column">
                <div className="ai-mentor-content-card">
                  <div className="ai-mentor-card-heading">
                    <div className="ai-mentor-card-icon red">
                      <ShieldCheck size={18} />
                    </div>
                    <div>
                      <span>LIMITATIONS</span>
                      <h3>Reported or potential limitations</h3>
                    </div>
                  </div>
                  {renderInsightList(
                    insights.limitations,
                    "No limitations were identified from the supplied content."
                  )}
                </div>

                <div className="ai-mentor-content-card">
                  <div className="ai-mentor-card-heading">
                    <div className="ai-mentor-card-icon purple">
                      <Sparkles size={18} />
                    </div>
                    <div>
                      <span>NOVELTY INDICATORS</span>
                      <h3>What may distinguish the work</h3>
                    </div>
                  </div>
                  {renderInsightList(
                    insights.novelty_indicators,
                    "No strong novelty indicators were identified."
                  )}
                </div>
              </div>

              <div className="ai-mentor-content-card">
                <div className="ai-mentor-card-heading">
                  <div className="ai-mentor-card-icon blue">
                    <Activity size={18} />
                  </div>
                  <div>
                    <span>POSSIBLE IMPROVEMENTS</span>
                    <h3>How the research could be strengthened</h3>
                  </div>
                </div>
                {renderInsightList(
                  insights.possible_improvements,
                  "No specific improvements were generated."
                )}
              </div>

              <div className="ai-mentor-content-card ai-mentor-future-card">
                <div className="ai-mentor-card-heading">
                  <div className="ai-mentor-card-icon teal">
                    <Rocket size={18} />
                  </div>
                  <div>
                    <span>FUTURE RESEARCH DIRECTIONS</span>
                    <h3>What could be explored next</h3>
                  </div>
                </div>
                {renderInsightList(
                  insights.future_research_directions,
                  "No future research directions were generated."
                )}
              </div>

              <div className="ai-mentor-evidence-note">
                <ShieldCheck size={17} />
                <div>
                  <strong>Research verification note</strong>
                  <p>
                    {insights.evidence_note ||
                      "Verify AI-generated interpretations against the original paper before using them in academic work."}
                  </p>
                </div>
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
}


/* -------------------------------------------------------
   LITERATURE INTELLIGENCE
------------------------------------------------------- */

function LiteraturePage() {
  const PROJECT_ID = 4;

  const [query, setQuery] = useState("");
  const [papers, setPapers] = useState([]);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const PAPERS_PER_PAGE = 10;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [savedPapers, setSavedPapers] = useState([]);
  const [savedLoading, setSavedLoading] = useState(false);
  const [savingPaperId, setSavingPaperId] = useState(null);

  const [selectedPaperIds, setSelectedPaperIds] = useState([]);
  const [matrix, setMatrix] = useState(null);
  const [matrixLoading, setMatrixLoading] = useState(false);
  const [matrixError, setMatrixError] = useState("");

  const [researchGap, setResearchGap] = useState(null);
  const [researchGapLoading, setResearchGapLoading] = useState(false);
  const [researchGapError, setResearchGapError] = useState("");


  const loadSavedPapers = async () => {
    setSavedLoading(true);

    try {
      const response = await fetch(
        `${API_BASE_URL}/literature/projects/${PROJECT_ID}/papers`
      );

      const data = await parseApiResponse(response);

      if (!response.ok) {
        throw new Error(
          getApiErrorMessage(data, "Unable to load saved papers.")
        );
      }

      const papers = Array.isArray(data)
        ? data
        : Array.isArray(data?.papers)
        ? data.papers
        : Array.isArray(data?.saved_papers)
        ? data.saved_papers
        : Array.isArray(data?.items)
        ? data.items
        : Array.isArray(data?.results)
        ? data.results
        : Array.isArray(data?.data)
        ? data.data
        : Array.isArray(data?.data?.papers)
        ? data.data.papers
        : Array.isArray(data?.data?.saved_papers)
        ? data.data.saved_papers
        : Array.isArray(data?.data?.items)
        ? data.data.items
        : [];

      const normalizedPapers = papers
        .filter(Boolean)
        .map((paper) => ({
          ...paper,
          id: paper.id ?? paper.paper_id ?? paper.paperId,
          paper_id: paper.paper_id ?? paper.id ?? paper.paperId,
          title: paper.title || paper.name || "Untitled paper",
          authors: normalizeAuthors(paper.authors),
        }));

      setSavedPapers((prev) => {
        const refreshed = normalizedPapers.map((saved) => {
          const localMatch = prev.find((item) =>
            (saved.id && item.id && String(saved.id) === String(item.id)) ||
            (saved.paper_id && item.paper_id && String(saved.paper_id) === String(item.paper_id)) ||
            (saved.doi && item.doi && normalizePaperKey(saved.doi) === normalizePaperKey(item.doi)) ||
            (saved.title && item.title && normalizePaperKey(saved.title) === normalizePaperKey(item.title))
          );

          return {
            ...(localMatch || {}),
            ...saved,
            paper_id: saved.paper_id || localMatch?.paper_id || null,
          };
        });

        for (const localPaper of prev) {
          const alreadyPresent = refreshed.some((saved) =>
            (saved.id && localPaper.id && String(saved.id) === String(localPaper.id)) ||
            (saved.paper_id && localPaper.paper_id && String(saved.paper_id) === String(localPaper.paper_id)) ||
            (saved.doi && localPaper.doi && normalizePaperKey(saved.doi) === normalizePaperKey(localPaper.doi)) ||
            (saved.title && localPaper.title && normalizePaperKey(saved.title) === normalizePaperKey(localPaper.title))
          );

          if (!alreadyPresent) refreshed.push(localPaper);
        }

        return refreshed;
      });

      console.info(`[Literature] Loaded ${normalizedPapers.length} saved papers for project ${PROJECT_ID}.`);
    } catch (err) {
      console.error(err);
    } finally {
      setSavedLoading(false);
    }
  };

  useEffect(() => {
    loadSavedPapers();
  }, []);

  const searchPapers = async (page = 1) => {
    const trimmedQuery = query.trim();

    if (!trimmedQuery) {
      setError("Please enter a research topic or keyword.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/literature/search?query=${encodeURIComponent(
          trimmedQuery
        )}&limit=${PAPERS_PER_PAGE}&page=${page}`
      );

      const data = await parseApiResponse(response);

      if (!response.ok) {
        throw new Error(
          getApiErrorMessage(data, "Unable to search academic papers.")
        );
      }

      setPapers(data.papers || []);
      setTotal(data.total || 0);
      setCurrentPage(data.page || page);
    } catch (err) {
      console.error("Literature search failed:", err);

      // Keep the last successful results visible.
      // Temporary/network errors must not erase valid results.
      setError(
        err.message || "Something went wrong while searching papers."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter") {
      searchPapers(1);
    }
  };

  const normalizePaperKey = (value) =>
    String(value || "")
      .trim()
      .toLowerCase();

  const isSamePaper = (saved, paper) => {
    if (!saved || !paper) return false;

    if (saved.paper_id && paper.paper_id &&
        String(saved.paper_id) === String(paper.paper_id)) {
      return true;
    }

    const savedDoi = normalizePaperKey(saved.doi);
    const paperDoi = normalizePaperKey(paper.doi);
    if (savedDoi && paperDoi && savedDoi === paperDoi) return true;

    const savedTitle = normalizePaperKey(saved.title);
    const paperTitle = normalizePaperKey(paper.title);
    return Boolean(savedTitle && paperTitle && savedTitle === paperTitle);
  };

  const isPaperSaved = (paper) =>
    savedPapers.some((saved) => isSamePaper(saved, paper));

  const savePaperToProject = async (paper) => {
    if (!paper?.paper_id) {
      setError("This paper does not have a valid paper ID.");
      return;
    }

    if (isPaperSaved(paper)) return;

    try {
      setSavingPaperId(paper.paper_id);
      setError("");

      const response = await fetch(
        `${API_BASE_URL}/literature/projects/${PROJECT_ID}/papers`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            project_id: PROJECT_ID,
            paper_id: paper.paper_id,
            title: paper.title,
            abstract: paper.abstract || null,
            year: paper.year || null,
            authors: normalizeAuthors(paper.authors),
            citation_count: paper.citation_count ?? 0,
            url: paper.url || null,
            doi: paper.doi || null,
          }),
        }
      );

      const data = await parseApiResponse(response);

      if (!response.ok) {
        throw new Error(
          getApiErrorMessage(data, "Failed to save paper.")
        );
      }

      // The save API returns the canonical saved-paper record.
      // Update local state immediately so the clicked card changes to
      // "Saved" even if the legacy GET endpoint does not yet return
      // the external paper_id field.
      setSavedPapers((prev) => {
        const savedRecord = {
          ...(data || {}),
          paper_id: data?.paper_id || paper.paper_id,
          title: data?.title || paper.title,
          abstract: data?.abstract ?? paper.abstract ?? null,
          year: data?.year ?? paper.year ?? null,
          authors: data?.authors ?? normalizeAuthors(paper.authors),
        };

        const exists = prev.some((saved) => isSamePaper(saved, savedRecord));

        return exists
          ? prev.map((saved) =>
              isSamePaper(saved, savedRecord)
                ? { ...saved, ...savedRecord }
                : saved
            )
          : [savedRecord, ...prev];
      });

      // Refresh other saved-paper data without allowing an older GET
      // response to erase the just-saved paper from the UI.
      try {
        const refreshResponse = await fetch(
          `${API_BASE_URL}/literature/projects/${PROJECT_ID}/papers`
        );
        const refreshData = await parseApiResponse(refreshResponse);

        if (refreshResponse.ok) {
          const refreshedPayload = Array.isArray(refreshData)
            ? refreshData
            : Array.isArray(refreshData?.papers)
            ? refreshData.papers
            : Array.isArray(refreshData?.saved_papers)
            ? refreshData.saved_papers
            : Array.isArray(refreshData?.items)
            ? refreshData.items
            : Array.isArray(refreshData?.results)
            ? refreshData.results
            : Array.isArray(refreshData?.data)
            ? refreshData.data
            : Array.isArray(refreshData?.data?.papers)
            ? refreshData.data.papers
            : Array.isArray(refreshData?.data?.items)
            ? refreshData.data.items
            : [];

          if (refreshedPayload.length > 0) {
          setSavedPapers((prev) => {
            const refreshed = refreshedPayload.map((item) => {
              const localMatch = prev.find((saved) => isSamePaper(saved, item));
              return {
                ...(localMatch || {}),
                ...item,
                // Preserve the academic provider paper_id when the legacy
                // GET response omits it.
                paper_id: item.paper_id || localMatch?.paper_id || null,
              };
            });

            for (const localPaper of prev) {
              if (!refreshed.some((saved) => isSamePaper(saved, localPaper))) {
                refreshed.push(localPaper);
              }
            }

            return refreshed;
          });
          }
        }
      } catch (refreshError) {
        console.warn("Saved papers refresh failed:", refreshError);
      }
    } catch (err) {
      console.error(err);
      setError(
        err.message || "Unable to save the paper to the project."
      );
    } finally {
      setSavingPaperId(null);
    }
  };

  const removeSavedPaper = async (paperId) => {
    try {
      const response = await fetch(
        `${API_BASE_URL}/literature/projects/${PROJECT_ID}/papers/${paperId}`,
        {
          method: "DELETE",
        }
      );

      const data = await parseApiResponse(response);

      if (!response.ok) {
        throw new Error(
          getApiErrorMessage(data, "Unable to remove paper.")
        );
      }

      setSavedPapers((prev) =>
        prev.filter((paper) => paper.id !== paperId)
      );

      setSelectedPaperIds((prev) =>
        prev.filter((id) => id !== paperId)
      );

      setMatrix(null);
    } catch (err) {
      console.error(err);
      setError(err.message || "Unable to remove saved paper.");
    }
  };

  const toggleMatrixPaper = (paperId) => {
    setSelectedPaperIds((prev) =>
      prev.includes(paperId)
        ? prev.filter((id) => id !== paperId)
        : [...prev, paperId]
    );

    setMatrix(null);
    setMatrixError("");
    setResearchGap(null);
    setResearchGapError("");
  };

  const generateLiteratureMatrix = async () => {
    if (selectedPaperIds.length === 0) {
      setMatrixError("Select at least one saved paper first.");
      return;
    }

    setMatrixLoading(true);
    setMatrixError("");
    setMatrix(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/literature/literature-matrix`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            project_id: PROJECT_ID,
            paper_ids: selectedPaperIds,
          }),
        }
      );

      const data = await parseApiResponse(response);

      if (!response.ok) {
        throw new Error(
          getApiErrorMessage(
            data,
            "Unable to generate literature matrix."
          )
        );
      }

      setMatrix(data);
    } catch (err) {
      console.error(err);
      setMatrixError(
        err.message ||
          "Something went wrong while generating the literature matrix."
      );
    } finally {
      setMatrixLoading(false);
    }
  };

  const generateResearchGap = async () => {
    if (selectedPaperIds.length < 2) {
      setResearchGapError(
        "Select at least 2 saved papers to generate a cross-paper research gap."
      );
      return;
    }

    setResearchGapLoading(true);
    setResearchGapError("");
    setResearchGap(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/literature/research-gap?project_id=${PROJECT_ID}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            paper_ids: selectedPaperIds,
          }),
        }
      );

      const data = await parseApiResponse(response);

      if (!response.ok) {
        throw new Error(
          getApiErrorMessage(
            data,
            "Unable to generate cross-paper research gaps."
          )
        );
      }

      setResearchGap(data);
    } catch (err) {
      console.error(err);
      setResearchGapError(
        err.message ||
          "Something went wrong while generating the research gap."
      );
    } finally {
      setResearchGapLoading(false);
    }
  };

  const renderResearchGapEvidence = (evidence) => {
    if (!evidence) return null;

    const items = Array.isArray(evidence) ? evidence : [evidence];

    return (
      <ul className="research-gap-evidence-list">
        {items.map((item, index) => {
          if (item && typeof item === "object") {
            const title = item.title || item.paper_title;
            const statement = item.statement || item.evidence || item.text;
            return (
              <li key={index}>
                {title ? <strong>{title}: </strong> : null}
                {statement ? String(statement) : JSON.stringify(item)}
              </li>
            );
          }
          return <li key={index}>{String(item)}</li>;
        })}
      </ul>
    );
  };

  const renderResearchGapPattern = (item) => {
    if (!item) return null;

    if (typeof item === "string") {
      return <li>{item}</li>;
    }

    const label = item.label || item.pattern || "Cross-paper pattern";
    const evidence = item.evidence;
    const basis = item.basis;

    return (
      <li>
        <strong>{label}</strong>
        {Array.isArray(evidence) ? (
          <ul className="research-gap-pattern-details">
            {evidence.map((entry, index) => (
              <li key={index}>
                {entry && typeof entry === "object"
                  ? `${entry.title || "Paper"}${entry.category ? ` — ${entry.category}` : ""}`
                  : String(entry)}
              </li>
            ))}
          </ul>
        ) : evidence ? (
          <p>{String(evidence)}</p>
        ) : null}
        {basis ? <small>{String(basis)}</small> : null}
      </li>
    );
  };

  const renderResearchGapResults = () => {
    if (!researchGap) return null;

    const gaps = Array.isArray(researchGap.gaps)
      ? researchGap.gaps
      : Array.isArray(researchGap.research_gaps)
        ? researchGap.research_gaps
        : [];

    const crossPaperPatterns = Array.isArray(researchGap.cross_paper_patterns)
      ? researchGap.cross_paper_patterns
      : Array.isArray(researchGap.cross_paper_findings)
        ? researchGap.cross_paper_findings
        : [];

    const summary =
      researchGap.overall_summary ||
      researchGap.research_gap_summary ||
      "";

    const gapCount = Number.isFinite(Number(researchGap.gap_count))
      ? Number(researchGap.gap_count)
      : gaps.length;

    return (
      <section className="literature-matrix-results research-gap-results">
        <div className="literature-matrix-header">
          <div>
            <span className="small-label">
              EVIDENCE-BASED RESEARCH GAP ANALYSIS
            </span>
            <h2>Cross-paper Research Gaps</h2>
            <p>
              ResearchMate checks the selected saved abstracts for explicit,
              repeated limitation evidence. It does not treat missing
              information as a research gap.
            </p>
          </div>

          <div className="literature-result-count">
            <strong>{gapCount}</strong>
            <span>potential gaps</span>
          </div>
        </div>

        {summary && (
          <div className="research-gap-summary-card">
            <div>
              <span>OVERALL SYNTHESIS</span>
              <p>{summary}</p>
            </div>
          </div>
        )}

        {crossPaperPatterns.length > 0 && (
          <div className="matrix-insight-card research-gap-patterns-card">
            <span>CROSS-PAPER PATTERNS</span>
            <ul>
              {crossPaperPatterns.map((item, index) => (
                <React.Fragment key={index}>
                  {renderResearchGapPattern(item)}
                </React.Fragment>
              ))}
            </ul>
          </div>
        )}

        {gaps.length === 0 ? (
          <div className="pdf-no-data">
            <strong>No explicit cross-paper research gap established.</strong>
            <p>
              The selected saved abstracts do not contain the repeated,
              explicit evidence required to support a cross-paper gap claim.
              This is different from saying that no gap exists in the
              literature.
            </p>
          </div>
        ) : (
          <div className="research-gap-list">
            {gaps.map((item, index) => {
              const gapText =
                item?.gap ||
                item?.research_gap ||
                item?.title ||
                "Potential research gap";

              const evidence = item?.evidence || item?.evidence_points;
              const affectedPapers = Array.isArray(item?.affected_papers)
                ? item.affected_papers
                : Array.isArray(item?.paper_ids)
                  ? item.paper_ids
                  : [];
              const evidenceStrength =
                item?.evidence_strength || item?.strength || "Not specified";
              const researchOpportunity =
                item?.research_opportunity ||
                item?.opportunity ||
                item?.suggested_direction ||
                "";

              return (
                <article className="research-gap-card" key={index}>
                  <div className="research-gap-card-top">
                    <div className="research-gap-number">
                      {String(index + 1).padStart(2, "0")}
                    </div>

                    <div className="research-gap-card-title">
                      <span>POTENTIAL RESEARCH GAP</span>
                      <h3>{gapText}</h3>
                    </div>

                    <div className="research-gap-strength">
                      <span>Evidence</span>
                      <strong>{evidenceStrength}</strong>
                    </div>
                  </div>

                  {evidence && (
                    <div className="research-gap-section">
                      <span>EVIDENCE FROM SELECTED PAPERS</span>
                      {renderResearchGapEvidence(evidence)}
                    </div>
                  )}

                  {affectedPapers.length > 0 && (
                    <div className="research-gap-section">
                      <span>AFFECTED PAPERS</span>
                      <div className="research-gap-paper-tags">
                        {affectedPapers.map((paperRef, paperIndex) => {
                          const id =
                            typeof paperRef === "object"
                              ? paperRef?.id || paperRef?.paper_id
                              : paperRef;
                          const title =
                            typeof paperRef === "object"
                              ? paperRef?.title || `Paper ${id}`
                              : `Paper ${paperRef}`;

                          return (
                            <span key={paperIndex} title={id ? `Saved paper ID: ${id}` : undefined}>
                              {title}
                            </span>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {researchOpportunity && (
                    <div className="research-gap-opportunity">
                        <div>
                        <span>RESEARCH OPPORTUNITY</span>
                        <p>{researchOpportunity}</p>
                      </div>
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        )}

        <div className="pdf-analysis-note">
          <div>
            <strong>Research verification note</strong>
            <p>
              {researchGap.evidence_note ||
                "Verify the original papers and broader recent literature before making a formal research-gap or novelty claim."}
            </p>
          </div>
        </div>
      </section>
    );
  };


  return (
    <div className="workspace-page literature-page">
      <div className="page-title literature-title">
        <div>
          <div className="eyebrow">LITERATURE INTELLIGENCE</div>
          <h1>Academic Literature Search</h1>
          <p>
            Find relevant research papers, save them to your project
            and compare them using an AI-powered literature matrix.
          </p>
        </div>

        <div className="discovery-status">
          <span className="status-dot" />
          Academic Search Engine
        </div>
      </div>

      <div className="literature-search-card">
        <div className="literature-search-label">
          <Search size={16} />
          SEARCH ACADEMIC PAPERS
        </div>

        <div className="literature-search-row">
          <input
            type="text"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="e.g. Explainable AI for healthcare"
          />

          <button
            className="primary-button literature-search-button"
            onClick={() => searchPapers(1)}
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="button-spinner" />
                Searching...
              </>
            ) : (
              <>
                Search Papers
                <Search size={16} />
              </>
            )}
          </button>
        </div>

        <small>
          Search is powered by academic literature retrieval through
          the ResearchMate backend.
        </small>
      </div>

      {error && (
        <div className="discovery-error literature-error">
          <ShieldCheck size={17} />
          {error}
        </div>
      )}

      {!loading && papers.length > 0 && (
        <div className="literature-results-header">
          <div>
            <span className="small-label">
              <CheckCircle2 size={14} />
              SEARCH COMPLETE
            </span>
            <h2>Relevant Research Papers</h2>
            <p>
              Showing {papers.length} papers for "{query}"
            </p>
          </div>

          <div className="literature-result-count">
            <strong>{total}</strong>
            <span>papers found</span>
          </div>
        </div>
      )}

      {loading && (
        <div className="discovery-loading literature-loading">
          <div className="loading-orb">
            <BookOpen size={25} />
          </div>
          <h3>Searching academic literature...</h3>
          <p>
            ResearchMate is finding relevant papers for your research topic.
          </p>
          <div className="loading-bar">
            <div />
          </div>
        </div>
      )}

      {!loading && papers.length > 0 && (
        <div className="literature-results">
          {papers.map((paper, index) => {
            const saved = isPaperSaved(paper);
            const saving = savingPaperId === paper.paper_id;

            return (
              <article
                className="literature-paper-card"
                key={paper.paper_id || index}
              >
                <div className="literature-paper-top">
                  <div className="literature-paper-index">
                    {String(index + 1).padStart(2, "0")}
                  </div>

                  <div className="literature-paper-year">
                    {paper.year || "Year unavailable"}
                  </div>
                </div>

                <h3>{paper.title}</h3>

                <div className="literature-authors">
                  <strong>Authors</strong>
                  <span>
                    {normalizeAuthors(paper.authors).join(", ") ||
                      "Authors unavailable"}
                  </span>
                </div>

                {paper.abstract && (
                  <p className="literature-abstract">
                    {paper.abstract}
                  </p>
                )}

                <div className="literature-paper-footer">
                  <div className="literature-paper-meta">
                    <span>
                      <BookOpen size={14} />
                      {paper.citation_count ?? 0} citations
                    </span>

                    {paper.doi && <span>DOI: {paper.doi}</span>}
                  </div>

                  <div className="literature-paper-actions">
                    {paper.url && (
                      <a
                        href={paper.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="literature-view-button"
                      >
                        View Paper
                        <ArrowUpRight size={15} />
                      </a>
                    )}

                    <button
                      className={`literature-save-button ${
                        saved ? "saved" : ""
                      }`}
                      onClick={() => savePaperToProject(paper)}
                      disabled={saved || saving}
                    >
                      {saving ? (
                        <>
                          <span className="button-spinner" />
                          Saving...
                        </>
                      ) : saved ? (
                        <>
                          <CheckCircle2 size={15} />
                          Saved
                        </>
                      ) : (
                        <>
                          <Plus size={15} />
                          Save to Project
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}

      {!loading && papers.length > 0 && total > PAPERS_PER_PAGE && (
        <div className="literature-pagination">
          <button
            className="literature-page-button"
            onClick={() => searchPapers(currentPage - 1)}
            disabled={currentPage === 1}
          >
            ← Previous
          </button>

          <div className="literature-page-info">
            <strong>Page {currentPage}</strong>
            <span>
              Showing {(currentPage - 1) * PAPERS_PER_PAGE + 1}–
              {Math.min(currentPage * PAPERS_PER_PAGE, total)} of{" "}
              {total.toLocaleString()} papers
            </span>
          </div>

          <button
            className="literature-page-button"
            onClick={() => searchPapers(currentPage + 1)}
            disabled={currentPage * PAPERS_PER_PAGE >= total}
          >
            Next →
          </button>
        </div>
      )}

      <section className="literature-library-section">
        <div className="literature-library-card">
          <div className="literature-results-header">
          <div>
            <span className="small-label">
              <BookOpen size={14} />
              PROJECT LITERATURE LIBRARY
            </span>
            <h2>Saved Papers</h2>
            <p>
              Papers saved to Research Project #{PROJECT_ID}.
              Select papers to generate a literature matrix.
            </p>
          </div>

          <div className="literature-result-count">
            <strong>{savedPapers.length}</strong>
            <span>saved papers</span>
          </div>
        </div>

        {savedLoading ? (
          <div className="discovery-loading literature-loading">
            <div className="loading-orb">
              <BookOpen size={25} />
            </div>
            <h3>Loading saved papers...</h3>
          </div>
        ) : savedPapers.length === 0 ? (
          <div className="discovery-empty-state literature-empty-state">
            <div className="discovery-empty-icon">
              <BookOpen size={27} />
            </div>
            <h2>No papers saved yet</h2>
            <p>
              Search above and use "Save to Project" to build your
              research literature library.
            </p>
          </div>
        ) : (
          <>
            <div className="saved-papers-list">
              {savedPapers.map((paper) => {
                const selected = selectedPaperIds.includes(paper.id);

                return (
                  <>
                  <div
                    className={`saved-paper-row ${
                      selected ? "selected" : ""
                    }`}
                    key={paper.id}
                  >
                    <label className="saved-paper-select">
                      <input
                        type="checkbox"
                        checked={selected}
                        onChange={() => toggleMatrixPaper(paper.id)}
                      />

                      <span>
                        <strong>{paper.title}</strong>
                        <small>
                          {paper.year || "Year unavailable"} ·{" "}
                          {normalizeAuthors(paper.authors).join(", ") ||
                            "Authors unavailable"}
                        </small>
                      </span>
                    </label>

                    <div className="saved-paper-actions">
                      <button
                        className="saved-paper-remove"
                        onClick={() => removeSavedPaper(paper.id)}
                      >
                        Remove
                      </button>
                    </div>
                  </div>

                  </>
                );
              })}
            </div>

            <div className="matrix-action-bar">
              <div>
                <strong>
                  {selectedPaperIds.length} paper
                  {selectedPaperIds.length === 1 ? "" : "s"} selected
                </strong>
                <span>
                  Select multiple papers for a stronger cross-paper comparison.
                </span>
              </div>

              <button
                className="primary-button"
                onClick={generateLiteratureMatrix}
                disabled={
                  matrixLoading || selectedPaperIds.length === 0
                }
              >
                {matrixLoading ? (
                  <>
                    <span className="button-spinner" />
                    Generating Matrix...
                  </>
                ) : (
                  <>
                    Generate Evidence-Based Literature Matrix
                  </>
                )}
              </button>
            </div>

            {matrixError && (
              <div className="discovery-error literature-error">
                {matrixError}
              </div>
            )}

            {matrix && !matrixLoading && (
              <div className="literature-matrix-results">
                <div className="literature-matrix-header">
                  <div>
                    <span className="small-label">
                      EVIDENCE-BASED LITERATURE MATRIX
                    </span>
                    <h2>Cross-paper Research Comparison</h2>
                    <p>
                      ResearchMate compared the selected papers using only the
                      information available in their saved records. Missing
                      evidence is shown as unavailable instead of being inferred.
                    </p>
                  </div>
                </div>

                <div className="literature-matrix-table-wrap">
                  <table className="literature-matrix-table">
                    <thead>
                      <tr>
                        <th>Paper</th>
                        <th>Research Problem</th>
                        <th>Methodology</th>
                        <th>Dataset</th>
                        <th>Key Results</th>
                        <th>Limitations</th>
                        <th>Research Gap</th>
                      </tr>
                    </thead>

                    <tbody>
                      {(matrix.papers || []).map((row) => (
                        <tr key={row.paper_id}>
                          <td>
                            <strong>{row.title}</strong>
                            <small>{row.year || "Year unavailable"}</small>
                          </td>
                          <td>{row.research_problem || "—"}</td>
                          <td>{row.methodology || "—"}</td>
                          <td>{row.dataset || "—"}</td>
                          <td>{row.key_results || "—"}</td>
                          <td>{row.limitations || "—"}</td>
                          <td>{row.research_gap || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="matrix-insights-grid">
                  <div className="matrix-insight-card">
                    <span>COMMON METHODS</span>
                    {matrix.common_methods?.length ? (
                      <ul>
                        {matrix.common_methods.map((item, index) => (
                          <li key={index}>{item}</li>
                        ))}
                      </ul>
                    ) : (
                      <p>No common methods identified.</p>
                    )}
                  </div>

                  <div className="matrix-insight-card">
                    <span>COMMON LIMITATIONS</span>
                    {matrix.common_limitations?.length ? (
                      <ul>
                        {matrix.common_limitations.map((item, index) => (
                          <li key={index}>{item}</li>
                        ))}
                      </ul>
                    ) : (
                      <p>No common limitations identified.</p>
                    )}
                  </div>

                  <div className="matrix-insight-card">
                    <span>CROSS-PAPER FINDINGS</span>
                    {matrix.cross_paper_findings?.length ? (
                      <ul>
                        {matrix.cross_paper_findings.map((item, index) => (
                          <li key={index}>
                            {typeof item === "object"
                              ? (item.text || item.evidence || item.label || JSON.stringify(item))
                              : String(item)}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p>No cross-paper findings identified.</p>
                    )}
                  </div>

                  <div className="matrix-insight-card">
                    <span>POTENTIAL RESEARCH GAPS</span>
                    {matrix.potential_research_gaps?.length ? (
                      <ul>
                        {matrix.potential_research_gaps.map((item, index) => (
                          <li key={index}>
                            {typeof item === "object"
                              ? (
                                  <>
                                    <strong>{item.title || item.type || "Potential gap signal"}</strong>
                                    <p>{item.description || "Potential gap signal based on the selected abstract evidence."}</p>
                                  </>
                                )
                              : String(item)}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p>No potential research gaps identified.</p>
                    )}
                  </div>
                </div>

                <div className="pdf-analysis-note">
                  <div>
                    <strong>Research verification note</strong>
                    <p>
                      {matrix.evidence_note ||
                        "Verify the extracted evidence against the original papers before using it in academic work."}
                    </p>
                  </div>
                </div>
              </div>
            )}

            <div className="research-gap-action-bar">
              <div>
                <strong>Research Gap Analysis</strong>
                <span>
                  Compare the selected papers to identify cross-paper patterns,
                  evidence and potential research opportunities.
                </span>
              </div>

              <button
                className="primary-button"
                onClick={generateResearchGap}
                disabled={
                  researchGapLoading || selectedPaperIds.length < 2
                }
              >
                {researchGapLoading ? (
                  <>
                    <span className="button-spinner" />
                    Finding Research Gaps...
                  </>
                ) : (
                  <>
                    Generate Evidence-Based Research Gap
                  </>
                )}
              </button>
            </div>

            {researchGapError && (
              <div className="discovery-error literature-error">
                {researchGapError}
              </div>
            )}

            {researchGap && !researchGapLoading && renderResearchGapResults()}
          </>
        )}
        </div>
      </section>

      {!loading &&
        !error &&
        papers.length === 0 &&
        savedPapers.length === 0 && (
          <div className="discovery-empty-state literature-empty-state">
            <div className="discovery-empty-icon">
              <BookOpen size={27} />
            </div>

            <h2>Start exploring the literature</h2>

            <p>
              Enter your research topic above to discover relevant academic
              papers.
            </p>

            <div className="analysis-pipeline">
              {["Search", "Papers", "Save", "Compare"].map(
                (item, index, array) => (
                  <React.Fragment key={item}>
                    <span>
                      <CheckCircle2 size={14} />
                      {item}
                    </span>

                    {index < array.length - 1 && (
                      <ChevronRight size={15} />
                    )}
                  </React.Fragment>
                )
              )}
            </div>
          </div>
        )}

      <PDFAnalysisSection />
    </div>
  );
}

/* -------------------------------------------------------
   GENERIC MODULE PAGE
------------------------------------------------------- */

function ModulePage({ title, eyebrow, description, icon: Icon }) {
  return (
    <div className="workspace-page">
      <div className="page-title">
        <div>
          <div className="eyebrow">{eyebrow}</div>

          <h1>{title}</h1>

          <p>{description}</p>
        </div>
      </div>

      <div className="coming-soon-card">
        <div className="coming-icon">
          <Icon size={28} />
        </div>

        <h2>Workspace ready</h2>

        <p>
          This module is part of the ResearchMate AI
          research-to-publication workflow.
        </p>

        <span>
          Features will be connected to the shared research
          project context.
        </span>
      </div>
    </div>
  );
}

/* -------------------------------------------------------
   APP
------------------------------------------------------- */

function App() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="app-shell">
      <Sidebar
        mobileOpen={mobileOpen}
        setMobileOpen={setMobileOpen}
      />

      <div className="main-shell">
        <Topbar setMobileOpen={setMobileOpen} />

        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />

            <Route path="/discovery" element={<Discovery />} />

            <Route
              path="/literature"
              element={<LiteraturePage />}
            />

            <Route
              path="/writing"
              element={<WritingPage />}
            />

            <Route
              path="/originality"
              element={<OriginalityPage />}
            />

            <Route
              path="/review"
              element={<ReviewPage />}
            />

            <Route
              path="/publication"
              element={<PublicationAssistant />}
            />
            <Route path="/conferences" element={<ConferencePage />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

/* -------------------------------------------------------
   RENDER
------------------------------------------------------- */

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);