import React, {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  CheckCircle2,
  FileText,
  History,
  Loader2,
  PenLine,
  Plus,
  RotateCcw,
  Save,
  Search,
  Sparkles,
  Target,
  TriangleAlert,
  WandSparkles,
  X,
  ExternalLink,
  ChevronDown,
  ChevronRight,
  Circle,
  Check,
  RefreshCw,
  Trash2,
} from "lucide-react";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000";

const EMPTY_SECTIONS = {
  introduction: "",
  background_related_work: "",
  problem_statement: "",
  research_objectives: "",
  research_questions: "",
  literature_review: "",
  research_gap: "",
  methodology: "",
  dataset_data_collection: "",
  proposed_method_system: "",
  experimental_setup: "",
  results: "",
  discussion: "",
  limitations: "",
  conclusion: "",
  future_work: "",
  references: "",
};

const EMPTY_MANUSCRIPT = {
  id: null,
  project_id: null,
  paper_id: null,
  title: "",
  abstract: "",
  keywords: [],
  sections: EMPTY_SECTIONS,
  status: "draft",
  current_version: 1,
  word_count: 0,
  character_count: 0,
};

const SECTION_LABELS = {
  introduction: "Introduction",
  background_related_work: "Background / Related Work",
  problem_statement: "Problem Statement",
  research_objectives: "Research Objectives",
  research_questions: "Research Questions",
  literature_review: "Literature Review",
  research_gap: "Research Gap",
  methodology: "Methodology",
  dataset_data_collection: "Dataset / Data Collection",
  proposed_method_system: "Proposed Method / System",
  experimental_setup: "Experimental Setup",
  results: "Results",
  discussion: "Discussion",
  limitations: "Limitations",
  conclusion: "Conclusion",
  future_work: "Future Work",
  references: "References",
};

const SECTION_GROUPS = [
  {
    key: "foundation",
    number: "01",
    label: "Research Foundation",
    sections: [
      "introduction",
      "background_related_work",
      "problem_statement",
      "research_objectives",
      "research_questions",
    ],
  },
  {
    key: "literature",
    number: "02",
    label: "Literature & Gap",
    sections: [
      "literature_review",
      "research_gap",
      "references",
    ],
  },
  {
    key: "methodology",
    number: "03",
    label: "Methodology",
    sections: [
      "methodology",
      "dataset_data_collection",
      "proposed_method_system",
      "experimental_setup",
    ],
  },
  {
    key: "results",
    number: "04",
    label: "Results & Analysis",
    sections: [
      "results",
      "discussion",
      "limitations",
    ],
  },
  {
    key: "final",
    number: "05",
    label: "Final Manuscript",
    sections: [
      "conclusion",
      "future_work",
    ],
  },
];

const GENERATION_ORDER = [
  "introduction",
  "background_related_work",
  "problem_statement",
  "research_objectives",
  "research_questions",
  "literature_review",
  "research_gap",
  "methodology",
  "dataset_data_collection",
  "proposed_method_system",
  "experimental_setup",
  "results",
  "discussion",
  "limitations",
  "conclusion",
  "future_work",
  "references",
];

const IMPROVE_OPTIONS = [
  {
    key: "academic",
    label: "Improve academic rigor",
    instruction:
      "Improve academic rigor, terminology, precision and scholarly tone without changing factual meaning.",
  },
  {
    key: "specific",
    label: "Make more specific",
    instruction:
      "Make the section more specific to the selected research project and its stored evidence. Do not invent missing facts.",
  },
  {
    key: "objectives",
    label: "Align with research objectives",
    instruction:
      "Improve alignment between this section and the project's stored research objectives. Do not invent objectives.",
  },
  {
    key: "gap",
    label: "Align with research gap",
    instruction:
      "Improve alignment between this section and the project's stored research gap and literature evidence. Do not invent evidence.",
  },
  {
    key: "redundancy",
    label: "Remove redundancy",
    instruction:
      "Remove repetitive statements and improve logical flow while preserving all supported facts.",
  },
  {
    key: "concise",
    label: "Reduce verbosity",
    instruction:
      "Make the section concise and publication-oriented without removing important supported information.",
  },
];

function getError(data, fallback = "Something went wrong.") {
  if (!data) return fallback;
  if (typeof data === "string") return data;

  if (typeof data.detail === "string") return data.detail;

  if (Array.isArray(data.detail)) {
    return data.detail
      .map((item) => item?.msg || item?.message || String(item))
      .join(", ");
  }

  if (data.detail && typeof data.detail === "object") {
    return (
      data.detail.message ||
      data.detail.msg ||
      fallback
    );
  }

  return data.message || data.error || fallback;
}

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

function safeObject(value) {
  return value &&
    typeof value === "object" &&
    !Array.isArray(value)
    ? value
    : {};
}

function wordCount(text) {
  if (!text?.trim()) return 0;
  return text.trim().split(/\s+/).length;
}

function normalizeId(value) {
  if (value === null || value === undefined || value === "") return "";
  return String(value);
}

function paperId(paper) {
  return (
    paper?.id ??
    paper?.paper_id ??
    paper?.provider_paper_id ??
    paper?.doi ??
    paper?.url ??
    paper?.title ??
    ""
  );
}

function paperAuthors(paper) {
  if (Array.isArray(paper?.authors)) {
    return paper.authors
      .map((author) => {
        if (typeof author === "string") return author;
        return author?.name || author?.full_name || "";
      })
      .filter(Boolean)
      .join(", ");
  }

  if (typeof paper?.authors === "string") return paper.authors;
  return "Authors unavailable";
}

function normalizeManuscript(data, projectId) {
  const source = safeObject(data);

  return {
    ...EMPTY_MANUSCRIPT,
    ...source,
    project_id:
      source.project_id ??
      Number(projectId) ??
      null,
    sections: {
      ...EMPTY_SECTIONS,
      ...safeObject(source.sections),
    },
    keywords: Array.isArray(source.keywords)
      ? source.keywords
      : [],
  };
}

function WritingPage() {
  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");

  const [papers, setPapers] = useState([]);
  const [projectContext, setProjectContext] = useState(null);
  const [loadingContext, setLoadingContext] = useState(false);

  const [manuscript, setManuscript] = useState(EMPTY_MANUSCRIPT);
  const [loadingManuscript, setLoadingManuscript] = useState(false);

  const [versions, setVersions] = useState([]);
  const [loadingVersions, setLoadingVersions] = useState(false);
  const [showVersions, setShowVersions] = useState(false);

  const [readiness, setReadiness] = useState(null);
  const [loadingReadiness, setLoadingReadiness] = useState(false);

  const [loadingProjects, setLoadingProjects] = useState(true);
  const [saving, setSaving] = useState(false);

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [activeSection, setActiveSection] = useState("introduction");
  const [collapsedGroups, setCollapsedGroups] = useState({
    foundation: false,
    literature: false,
    methodology: true,
    results: true,
    final: true,
  });

  const [aiLoading, setAiLoading] = useState(false);
  const [generationSection, setGenerationSection] = useState("");
  const [fullGenerationLoading, setFullGenerationLoading] = useState(false);
  const [generationEvidence, setGenerationEvidence] = useState(null);

  const [metadataLoading, setMetadataLoading] = useState(false);

  const [showNewProject, setShowNewProject] = useState(false);
  const [creatingProject, setCreatingProject] = useState(false);

  const [newProject, setNewProject] = useState({
    topic: "",
    field: "",
    problem: "",
    objectives: "",
    keywords: "",
  });

  const [researchTopics, setResearchTopics] = useState([]);
  const [selectedTopicId, setSelectedTopicId] = useState("");

  const [paperSearchQuery, setPaperSearchQuery] = useState("");
  const [savedPaperQuery, setSavedPaperQuery] = useState("");
  const [paperSearchResults, setPaperSearchResults] = useState([]);
  const [paperSearchLoading, setPaperSearchLoading] = useState(false);
  const [paperSaveId, setPaperSaveId] = useState(null);
  const [paperRemoveId, setPaperRemoveId] = useState(null);
  const [showPaperSearch, setShowPaperSearch] = useState(false);

  const [paperFilter, setPaperFilter] = useState("all");
  const [paperPage, setPaperPage] = useState(1);

  const [showImproveModal, setShowImproveModal] = useState(false);
  const [improveMode, setImproveMode] = useState("academic");
  const [improving, setImproving] = useState(false);

  const [dirty, setDirty] = useState(false);
  const [localBackupAvailable, setLocalBackupAvailable] = useState(false);
  const [lastSavedAt, setLastSavedAt] = useState(null);

  const PAPERS_PER_PAGE = 8;

  const selectedProject = useMemo(
    () =>
      projects.find(
        (project) =>
          String(project.id) === String(selectedProjectId)
      ),
    [projects, selectedProjectId]
  );

  const selectedTopic = useMemo(
    () =>
      researchTopics.find(
        (item) =>
          String(item.id) === String(selectedTopicId)
      ),
    [researchTopics, selectedTopicId]
  );

  const selectedTopicText =
    selectedTopic?.topic?.trim() ||
    selectedProject?.title?.trim() ||
    "";

  const currentText =
    manuscript.sections?.[activeSection] || "";

  const currentWordCount = wordCount(currentText);

  const liveManuscriptWordCount = wordCount(
    [
      manuscript.title || "",
      manuscript.abstract || "",
      ...Object.values(manuscript.sections || {}),
    ].join(" ")
  );

  const paperStatus = useMemo(() => {
    const analysedIds = new Set(
      safeArray(projectContext?.analysed_paper_ids).map(normalizeId)
    );

    const contextIds = new Set(
      safeArray(
        projectContext?.context_paper_ids ||
          projectContext?.context_literature_ids
      ).map(normalizeId)
    );

    return {
      analysedIds,
      contextIds,
    };
  }, [projectContext]);

  const filteredPapers = useMemo(() => {
    const query = savedPaperQuery.trim().toLowerCase();

    return papers.filter((paper) => {
      const id = normalizeId(paperId(paper));
      const analysed =
        Boolean(paper?.analysed) ||
        paperStatus.analysedIds.has(id);

      const context =
        Boolean(
          paper?.used_as_context ||
          paper?.is_context ||
          paper?.context
        ) ||
        paperStatus.contextIds.has(id);

      if (paperFilter === "analysed" && !analysed) return false;
      if (paperFilter === "context" && !context) return false;
      if (paperFilter === "not_analysed" && analysed) return false;

      if (!query) return true;

      const haystack = [
        paper?.title,
        paper?.abstract,
        paper?.doi,
        paperAuthors(paper),
        paper?.year,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return haystack.includes(query);
    });
  }, [
    papers,
    savedPaperQuery,
    paperFilter,
    paperStatus,
  ]);

  const paperTotalPages = Math.max(
    1,
    Math.ceil(filteredPapers.length / PAPERS_PER_PAGE)
  );

  const visiblePapers = useMemo(() => {
    const start = (paperPage - 1) * PAPERS_PER_PAGE;
    return filteredPapers.slice(
      start,
      start + PAPERS_PER_PAGE
    );
  }, [filteredPapers, paperPage]);

  const savedPaperCount =
    projectContext?.literature_count ??
    papers.length;

  const contextPaperCount =
    projectContext?.context_literature_count ??
    safeArray(projectContext?.literature).length;

  const analysedPaperCount =
    projectContext?.analysed_paper_count ??
    safeArray(projectContext?.analysed_paper_ids).length;

  const completedSections = GENERATION_ORDER.filter(
    (key) =>
      typeof manuscript.sections?.[key] === "string" &&
      manuscript.sections[key].trim().length > 0
  ).length;

  const manuscriptProgress = Math.round(
    (completedSections / GENERATION_ORDER.length) * 100
  );

  function clearMessages() {
    setError("");
    setSuccess("");
  }

  async function apiJson(url, options = {}) {
    const response = await fetch(url, options);
    const contentType =
      response.headers.get("content-type") || "";

    const data = contentType.includes("application/json")
      ? await response.json()
      : {};

    if (!response.ok) {
      throw new Error(
        getError(
          data,
          `Request failed with status ${response.status}.`
        )
      );
    }

    return data;
  }

  async function loadProjects() {
    setLoadingProjects(true);
    setError("");

    try {
      const data = await apiJson(
        `${API_BASE_URL}/projects/`
      );

      const list = safeArray(data);

      setProjects(list);

      if (list.length) {
        let storedProjectId = "";

        try {
          storedProjectId =
            localStorage.getItem(
              "researchmate:selectedProjectId"
            ) || "";
        } catch {
          // localStorage can be unavailable in private/restricted contexts.
        }

        const valid = list.some(
          (project) =>
            String(project.id) ===
            String(storedProjectId)
        );

        setSelectedProjectId(
          valid
            ? String(storedProjectId)
            : String(list[0].id)
        );
      } else {
        setSelectedProjectId("");
      }
    } catch (err) {
      setError(
        err.message ||
          "Could not load research projects."
      );
    } finally {
      setLoadingProjects(false);
    }
  }

  async function loadResearchTopics(projectId) {
    if (!projectId) {
      setResearchTopics([]);
      setSelectedTopicId("");
      return;
    }

    try {
      const data = await apiJson(
        `${API_BASE_URL}/projects/${projectId}/topics`
      );

      const rawTopics = Array.isArray(data)
        ? data
        : safeArray(
            data?.topics ||
              data?.items ||
              data?.data
          );

      const topics = rawTopics
        .map((item) => ({
          ...safeObject(item),
          id:
            item?.id ??
            item?.topic_id ??
            item?.research_topic_id ??
            item?.value ??
            "",
          topic:
            item?.topic?.trim?.() ||
            item?.title?.trim?.() ||
            item?.name?.trim?.() ||
            "",
        }))
        .filter(
          (item) =>
            String(item.id).trim() &&
            item.topic.trim()
        );

      setResearchTopics(topics);

      let storedTopicId = "";

      try {
        storedTopicId =
          localStorage.getItem(
            `researchmate:selectedTopicId:${projectId}`
          ) || "";
      } catch {
        // Ignore local storage failures.
      }

      const validStored = topics.some(
        (item) =>
          String(item.id) ===
          String(storedTopicId)
      );

      const nextId = validStored
        ? String(storedTopicId)
        : topics[0]?.id
          ? String(topics[0].id)
          : "";

      setSelectedTopicId(nextId);

      const selectedTopic = topics.find(
        (item) =>
          String(item.id) ===
          String(nextId)
      );

      setPaperSearchQuery(
        selectedTopic?.topic?.trim() ||
          selectedProject?.title?.trim() ||
          ""
      );

      try {
        localStorage.setItem(
          `researchmate:selectedTopicId:${projectId}`,
          String(nextId)
        );
      } catch {
        // Ignore local storage failures.
      }
    } catch (err) {
      console.warn(
        "Research topics could not be loaded:",
        err
      );
      setResearchTopics([]);
      setSelectedTopicId("");
      setPaperSearchQuery(
        selectedProject?.title?.trim() || ""
      );
    }
  }

  async function loadProjectContext(projectId) {
    if (!projectId) {
      setProjectContext(null);
      setPapers([]);
      return;
    }

    setLoadingContext(true);

    try {
      const data = await apiJson(
        `${API_BASE_URL}/writing/projects/${projectId}/context`
      );

      setProjectContext(data);

      const literature =
        safeArray(data?.all_literature).length
          ? safeArray(data.all_literature)
          : safeArray(data?.literature);

      setPapers(literature);

      setPaperPage(1);
    } catch (err) {
      setProjectContext(null);
      setPapers([]);
      setError(
        err.message ||
          "Could not load project research context."
      );
    } finally {
      setLoadingContext(false);
    }
  }

  async function loadManuscript(projectId) {
    if (!projectId) return;

    setLoadingManuscript(true);
    setError("");
    setDirty(false);
    setLocalBackupAvailable(false);

    try {
      const response = await fetch(
        `${API_BASE_URL}/writing/projects/${projectId}/manuscript`
      );

      const contentType =
        response.headers.get("content-type") || "";

      const data =
        contentType.includes("application/json")
          ? await response.json()
          : {};

      if (response.status === 404) {
        setManuscript({
          ...EMPTY_MANUSCRIPT,
          project_id: Number(projectId),
        });
        return;
      }

      if (!response.ok) {
        throw new Error(
          getError(
            data,
            "Could not load manuscript."
          )
        );
      }

      const normalized = normalizeManuscript(
        data,
        projectId
      );

      setManuscript(normalized);

      try {
        const raw =
          localStorage.getItem(
            `researchmate:writing-backup:${projectId}`
          );

        if (raw) {
          const backup = JSON.parse(raw);

          if (
            backup?.manuscript &&
            backup?.savedAt &&
            Number(backup.savedAt) >
              Number(
                new Date(
                  data?.updated_at ||
                    data?.created_at ||
                    0
                ).getTime() || 0
              )
          ) {
            setLocalBackupAvailable(true);
          }
        }
      } catch {
        // Ignore malformed local backup.
      }
    } catch (err) {
      setError(
        err.message ||
          "Could not load manuscript."
      );
    } finally {
      setLoadingManuscript(false);
    }
  }

  async function loadVersions() {
    if (!selectedProjectId) return;

    setLoadingVersions(true);

    try {
      const data = await apiJson(
        `${API_BASE_URL}/writing/projects/${selectedProjectId}/versions`
      );

      setVersions(safeArray(data));
    } catch (err) {
      setError(
        err.message ||
          "Could not load manuscript versions."
      );
    } finally {
      setLoadingVersions(false);
    }
  }

  async function loadReadiness() {
    if (!selectedProjectId) return;

    setLoadingReadiness(true);

    try {
      const data = await apiJson(
        `${API_BASE_URL}/writing/projects/${selectedProjectId}/readiness`
      );

      setReadiness(data);
    } catch (err) {
      setError(
        err.message ||
          "Could not calculate writing readiness."
      );
    } finally {
      setLoadingReadiness(false);
    }
  }

  useEffect(() => {
    loadProjects();
  }, []);

  useEffect(() => {
    if (!selectedProjectId) {
      setProjectContext(null);
      setPapers([]);
      setManuscript(EMPTY_MANUSCRIPT);
      setResearchTopics([]);
      setSelectedTopicId("");
      return;
    }

    try {
      localStorage.setItem(
        "researchmate:selectedProjectId",
        String(selectedProjectId)
      );
    } catch {
      // Ignore local storage failures.
    }

    clearMessages();
    setReadiness(null);
    setVersions([]);
    setShowVersions(false);
    setPaperFilter("all");
    setPaperPage(1);
    setShowPaperSearch(false);

    loadProjectContext(selectedProjectId);
    loadResearchTopics(selectedProjectId);
    loadManuscript(selectedProjectId);
  }, [selectedProjectId]);

  useEffect(() => {
    if (!selectedProjectId || !manuscript.id) return;

    loadVersions();
    loadReadiness();
  }, [selectedProjectId, manuscript.id]);

  useEffect(() => {
    setPaperPage(1);
  }, [paperFilter, savedPaperQuery]);

  useEffect(() => {
    if (!selectedProjectId || !dirty) return;

    const timer = window.setTimeout(() => {
      try {
        localStorage.setItem(
          `researchmate:writing-backup:${selectedProjectId}`,
          JSON.stringify({
            savedAt: Date.now(),
            manuscript,
          })
        );
      } catch {
        // Local backup is a convenience; server save remains the source of truth.
      }
    }, 900);

    return () => window.clearTimeout(timer);
  }, [manuscript, selectedProjectId, dirty]);

  useEffect(() => {
    const handleBeforeUnload = (event) => {
      if (!dirty) return;
      event.preventDefault();
      event.returnValue = "";
    };

    window.addEventListener(
      "beforeunload",
      handleBeforeUnload
    );

    return () =>
      window.removeEventListener(
        "beforeunload",
        handleBeforeUnload
      );
  }, [dirty]);

  function updateSection(sectionName, value) {
    setManuscript((current) => ({
      ...current,
      sections: {
        ...current.sections,
        [sectionName]: value,
      },
    }));
    setDirty(true);
    setSuccess("");
  }

  function updateField(field, value) {
    setManuscript((current) => ({
      ...current,
      [field]: value,
    }));
    setDirty(true);
    setSuccess("");
  }

  async function createNewResearchProject() {
    const topic = newProject.topic.trim();

    if (!topic) {
      setError("Research topic is required.");
      return;
    }

    setCreatingProject(true);
    clearMessages();

    try {
      const description = [
        `Research Topic: ${topic}`,
        newProject.problem.trim()
          ? `Research Problem: ${newProject.problem.trim()}`
          : "",
        newProject.objectives.trim()
          ? `Research Objectives: ${newProject.objectives.trim()}`
          : "",
        newProject.keywords.trim()
          ? `Keywords: ${newProject.keywords.trim()}`
          : "",
      ]
        .filter(Boolean)
        .join("\n\n");

      const data = await apiJson(
        `${API_BASE_URL}/projects/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            title: topic,
            description,
            research_field:
              newProject.field.trim() || null,
          }),
        }
      );

      const createdProject =
        data?.project || data;

      if (!createdProject?.id) {
        throw new Error(
          "Project was created but no project ID was returned."
        );
      }

      try {
        await apiJson(
          `${API_BASE_URL}/projects/${createdProject.id}/topics`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              topic,
              source_query: topic,
              description:
                newProject.problem.trim() || null,
            }),
          }
        );
      } catch (topicError) {
        console.warn(
          "Project created, but topic sync failed:",
          topicError
        );
      }

      setProjects((current) => [
        createdProject,
        ...current.filter(
          (item) =>
            item.id !== createdProject.id
        ),
      ]);

      setSelectedProjectId(
        String(createdProject.id)
      );

      setNewProject({
        topic: "",
        field: "",
        problem: "",
        objectives: "",
        keywords: "",
      });

      setShowNewProject(false);

      setSuccess(
        `New research project created: ${createdProject.title}`
      );
    } catch (err) {
      setError(
        err.message ||
          "Could not create the research project."
      );
    } finally {
      setCreatingProject(false);
    }
  }

  function buildRelatedAcademicQueries(topic) {
    const clean = String(topic || "").trim();
    if (!clean) return [];

    const field = String(selectedProject?.research_field || "").trim();
    const description = String(selectedProject?.description || "").trim();

    const baseParts = [
      clean,
      field,
    ].filter(Boolean);

    const queries = [clean];

    if (field && !clean.toLowerCase().includes(field.toLowerCase())) {
      queries.push(`${clean} ${field}`);
    }

    // Derive search terms only from the current project's own stored
    // metadata. No domain-specific words are hardcoded here.
    const tokens = `${clean} ${field} ${description}`
      .toLowerCase()
      .replace(/[^\p{L}\p{N}\s-]/gu, " ")
      .split(/\s+/)
      .filter(Boolean)
      .filter((word) => word.length >= 4)
      .filter(
        (word) =>
          ![
            "research",
            "study",
            "studies",
            "project",
            "using",
            "based",
            "approach",
            "system",
            "analysis",
            "method",
            "methods",
            "proposed",
            "development",
            "identify",
            "identifying",
            "existing",
            "available",
            "current",
          ].includes(word)
      );

    const uniqueTokens = [...new Set(tokens)].slice(0, 8);

    if (uniqueTokens.length >= 2) {
      queries.push(uniqueTokens.join(" "));
    }

    if (uniqueTokens.length >= 3) {
      queries.push(`${uniqueTokens.slice(0, 5).join(" ")} related work`);
    }

    return [...new Set(queries)]
      .map((query) => query.trim())
      .filter(Boolean)
      .slice(0, 4);
  }

  function scoreAcademicPaper(paper, topic) {
    const title = String(paper?.title || "").toLowerCase();
    const abstract = String(
      paper?.abstract || paper?.summary || ""
    ).toLowerCase();

    const field = String(
      selectedProject?.research_field || ""
    ).toLowerCase();

    const description = String(
      selectedProject?.description || ""
    ).toLowerCase();

    const queryText = `${topic || ""} ${field} ${description}`
      .toLowerCase()
      .replace(/[^\p{L}\p{N}\s-]/gu, " ");

    const tokenize = (value) =>
      new Set(
        value
          .split(/\s+/)
          .filter((word) => word.length >= 4)
          .filter(
            (word) =>
              ![
                "research",
                "study",
                "studies",
                "project",
                "using",
                "based",
                "approach",
                "system",
                "analysis",
                "method",
                "methods",
                "proposed",
                "existing",
              ].includes(word)
          )
      );

    const queryTokens = tokenize(queryText);
    const titleTokens = tokenize(title);
    const abstractTokens = tokenize(abstract);

    let score = 0;

    queryTokens.forEach((word) => {
      if (titleTokens.has(word)) score += 10;
      else if (abstractTokens.has(word)) score += 3;
    });

    const cleanTopic = String(topic || "").trim().toLowerCase();
    if (
      cleanTopic.length >= 6 &&
      title.includes(cleanTopic)
    ) {
      score += 25;
    }

    if (
      field &&
      field.length >= 4 &&
      title.includes(field)
    ) {
      score += 8;
    }

    return score;
  }

  async function searchProjectPapers(queryOverride = "") {
    if (!selectedProjectId) {
      setError(
        "Select a research project before searching."
      );
      return;
    }

    const topic =
      queryOverride.trim() ||
      paperSearchQuery.trim() ||
      selectedTopicText.trim() ||
      selectedProject?.title?.trim() ||
      "";

    if (topic.length < 3) {
      setError(
        "Enter at least 3 characters for the literature search."
      );
      return;
    }

    setPaperSearchLoading(true);
    clearMessages();

    try {
      const queries = buildRelatedAcademicQueries(topic);

      const responses = await Promise.allSettled(
        queries.map((query) =>
          apiJson(
            `${API_BASE_URL}/literature/search?query=${encodeURIComponent(
              query
            )}&limit=10&page=1`
          )
        )
      );

      const merged = [];
      const seen = new Set();

      responses.forEach((result) => {
        if (result.status !== "fulfilled") return;

        const papers = safeArray(
          result.value?.papers
        );

        papers.forEach((paper) => {
          const normalized = {
            ...paper,
            authors: safeArray(
              paper?.authors
            ),
          };

          const key =
            String(
              normalized?.doi ||
                normalized?.paper_id ||
                normalized?.title ||
                ""
            )
              .trim()
              .toLowerCase();

          if (!key || seen.has(key)) return;

          seen.add(key);

          merged.push({
            ...normalized,
            _relevanceScore:
              scoreAcademicPaper(
                normalized,
                topic
              ),
          });
        });
      });

      merged.sort(
        (a, b) =>
          b._relevanceScore -
          a._relevanceScore
      );

      const results = merged
        .slice(0, 15)
        .map(
          ({
            _relevanceScore,
            ...paper
          }) => ({
            ...paper,
            relevance_score:
              _relevanceScore,
          })
        );

      setPaperSearchResults(results);

      if (!results.length) {
        setSuccess(
          "No closely related academic papers were returned. Try a more specific research topic."
        );
      }
    } catch (err) {
      setPaperSearchResults([]);
      setError(
        err.message ||
          "Academic paper search failed."
      );
    } finally {
      setPaperSearchLoading(false);
    }
  }

  async function saveProjectPaper(paper) {
    if (!selectedProjectId) {
      setError("Select a project first.");
      return;
    }

    if (!paper?.paper_id) {
      setError(
        "This search result does not contain a provider paper ID."
      );
      return;
    }

    setPaperSaveId(paper.paper_id);
    clearMessages();

    try {
      await apiJson(
        `${API_BASE_URL}/literature/projects/${selectedProjectId}/papers`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            project_id: Number(selectedProjectId),
            paper_id: paper.paper_id,
            title: paper.title,
            abstract: paper.abstract || null,
            year: paper.year || null,
            authors: safeArray(
              paper.authors
            )
              .map(
                (author) =>
                  author?.name ||
                  author?.full_name ||
                  author
              )
              .filter(Boolean),
            citation_count:
              paper.citation_count ?? 0,
            url: paper.url || null,
            doi: paper.doi || null,
          }),
        }
      );

      setPaperSearchResults((current) =>
        current.map((item) =>
          item.paper_id === paper.paper_id
            ? {
                ...item,
                saved: true,
              }
            : item
        )
      );

      setSuccess(
        "Paper saved to this research project."
      );

      await loadProjectContext(
        selectedProjectId
      );
    } catch (err) {
      setError(
        err.message ||
          "Could not save this paper."
      );
    } finally {
      setPaperSaveId(null);
    }
  }

  async function removeSavedPaper(paper) {
    if (!selectedProjectId) {
      setError("Select a project first.");
      return;
    }

    // The DELETE API expects the database LiteraturePaper.id,
    // not the external/provider paper_id.
    // IMPORTANT:
    // /writing/projects/{project_id}/context returns the database
    // LiteraturePaper.id under the field `paper_id`.
    // The academic search result also uses `paper_id`, but there it means
    // the external/provider ID. This handler is called only for saved
    // project literature, so prefer the DB `id` when present and otherwise
    // use the context's `paper_id`.
    const databasePaperId =
      paper?.id ?? paper?.paper_id ?? null;

    if (
      databasePaperId === null ||
      databasePaperId === undefined ||
      databasePaperId === ""
    ) {
      setError(
        "This saved paper does not have a valid database ID, so it cannot be removed safely."
      );
      return;
    }

    const confirmed = window.confirm(
      `Remove "${paper?.title || "this paper"}" from this research project?\n\nThis removes it from the project's saved literature library.`
    );

    if (!confirmed) return;

    setPaperRemoveId(String(databasePaperId));
    clearMessages();

    try {
      await apiJson(
        `${API_BASE_URL}/literature/projects/${selectedProjectId}/papers/${encodeURIComponent(
          databasePaperId
        )}`,
        {
          method: "DELETE",
        }
      );

      // Remove from the local saved-paper list immediately.
      setPapers((current) =>
        current.filter(
          (item) =>
            String(
              item?.id ??
              item?.paper_id ??
              ""
            ) !== String(databasePaperId)
        )
      );

      // If the same paper is currently shown in academic search,
      // mark it as available to save again.
      const providerId =
        paper?.paper_id ??
        paper?.provider_paper_id ??
        null;

      setPaperSearchResults((current) =>
        current.map((item) => {
          const same =
            (providerId &&
              String(item?.paper_id) ===
                String(providerId)) ||
            (paper?.doi &&
              item?.doi &&
              String(item.doi).toLowerCase() ===
                String(paper.doi).toLowerCase()) ||
            (paper?.title &&
              item?.title &&
              String(item.title).trim().toLowerCase() ===
                String(paper.title).trim().toLowerCase());

          return same
            ? {
                ...item,
                saved: false,
              }
            : item;
        })
      );

      // Reload authoritative project context/counts from the backend.
      await loadProjectContext(
        selectedProjectId
      );

      setPaperPage((page) => {
        const nextTotal =
          Math.max(
            1,
            Math.ceil(
              Math.max(
                0,
                filteredPapers.length - 1
              ) / PAPERS_PER_PAGE
            )
          );

        return Math.min(page, nextTotal);
      });

      setSuccess(
        "Paper removed from this research project."
      );
    } catch (err) {
      setError(
        err.message ||
          "Could not remove this paper from the project."
      );
    } finally {
      setPaperRemoveId(null);
    }
  }

  async function generateMetadata({
    throwOnError = false,
  } = {}) {
    if (!selectedProjectId) {
      const message =
        "Select a research project first.";

      setError(message);

      if (throwOnError) {
        throw new Error(message);
      }

      return false;
    }

    setMetadataLoading(true);
    clearMessages();

    try {
      const data = await apiJson(
        `${API_BASE_URL}/writing/projects/${selectedProjectId}/metadata/generate`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            instruction:
              "Generate a publication-ready title and structured abstract for this exact research project. Use only stored project facts and project-scoped literature evidence. Do not invent results, datasets, metrics, citations, DOI, sample sizes, or numerical values.",
          }),
        }
      );

      if (
        !data?.title?.trim() &&
        !data?.abstract?.trim()
      ) {
        throw new Error(
          "The metadata generator returned no title or abstract."
        );
      }

      setManuscript((current) => ({
        ...current,
        title:
          data.title?.trim() ||
          current.title ||
          "",
        abstract:
          data.abstract?.trim() ||
          current.abstract ||
          "",
        sections: {
          ...current.sections,
          title:
            data.title?.trim() ||
            current.sections?.title ||
            "",
          abstract:
            data.abstract?.trim() ||
            current.sections?.abstract ||
            "",
        },
      }));

      setDirty(true);

      setSuccess(
        data.generation_mode === "ai"
          ? "Title and abstract generated from project evidence. Review before saving."
          : "Evidence-only title and abstract scaffold generated."
      );

      return true;
    } catch (err) {
      setError(
        err.message ||
          "Could not generate manuscript metadata."
      );

      if (throwOnError) {
        throw err;
      }

      return false;
    } finally {
      setMetadataLoading(false);
    }
  }

  async function generateDraft(
    sectionOverride = null,
    options = {}
  ) {
    const sectionName =
      sectionOverride || activeSection;

    if (!selectedProjectId) {
      const message = "Select a research project first.";
      setError(message);
      if (options.throwOnError) throw new Error(message);
      return "";
    }

    if (!SECTION_LABELS[sectionName]) {
      const message = "Invalid manuscript section selected.";
      setError(message);
      if (options.throwOnError) throw new Error(message);
      return "";
    }

    const activeProject =
      projects.find(
        (project) =>
          String(project.id) === String(selectedProjectId)
      ) || selectedProject;

    const topicText =
      selectedTopicText ||
      activeProject?.title?.trim() ||
      "";

    if (!topicText) {
      const message =
        "This project has no research topic/title. Add a project topic before generating a manuscript section.";
      setError(message);
      if (options.throwOnError) throw new Error(message);
      return "";
    }

    if (!options.silent) {
      setAiLoading(true);
      setGenerationSection(sectionName);
      clearMessages();
      setGenerationEvidence(null);
    }

    try {
      /*
       * Accuracy rule:
       * The backend is the single source of truth for evidence retrieval.
       * Do NOT send the entire saved-paper library from the browser.
       * This prevents unrelated papers from being injected into generation.
       */
      const sectionRules = {
        introduction:
          "Explain the project problem, motivation, relevant prior work and research need using only project evidence.",
        background_related_work:
          "Summarize only relevant project-scoped literature and distinguish reported facts from synthesis.",
        problem_statement:
          "State only the problem supported by project metadata and evidence. Do not invent statistics.",
        research_objectives:
          "Generate objectives only from stored project information; if not explicitly stored, label them as proposed.",
        research_questions:
          "Generate focused questions from the project problem and evidence; label them proposed when not stored.",
        literature_review:
          "Compare relevant saved papers by methods, themes and reported limitations. Do not invent paper findings.",
        research_gap:
          "State only evidence-supported gap signals. Do not claim proven novelty.",
        methodology:
          "Use only stored methodology information. Do not invent datasets, architectures, hyperparameters or hardware.",
        dataset_data_collection:
          "Use only explicit dataset or data-collection evidence. If absent, state that it is unavailable.",
        proposed_method_system:
          "Describe only the stored/proposed system information. Do not invent implementation details.",
        experimental_setup:
          "Use only actual stored experimental setup information. Do not invent evaluation settings.",
        results:
          "Use only validated stored experimental results. If unavailable, explicitly say results are unavailable.",
        discussion:
          "Interpret only actual available results. Do not infer measured outcomes.",
        limitations:
          "List only supported project or literature limitations and distinguish them.",
        conclusion:
          "Summarize only evidence-supported conclusions. Do not present planned work as completed.",
        future_work:
          "Provide clearly labeled evidence-based recommendations, not completed facts.",
        references:
          "Use only project-scoped saved paper metadata. Never invent citation details.",
      };

      const instruction = [
        `Generate the ${SECTION_LABELS[sectionName]} section for this exact research project.`,
        `Research topic: ${topicText}`,
        activeProject?.research_field
          ? `Research field: ${activeProject.research_field}`
          : "",
        sectionRules[sectionName] || "",
        "Use only this project's stored metadata and project-scoped evidence.",
        "Never use information from another project.",
        "Never invent papers, authors, DOI, journals, datasets, sample sizes, metrics, statistics, experimental results or publication facts.",
        "A literature abstract supports only claims explicitly present in that abstract.",
        "If required evidence is missing, explicitly state that it is unavailable.",
        "Return only the manuscript section text.",
      ]
        .filter(Boolean)
        .join("\n\n");

      const responseData = await apiJson(
        `${API_BASE_URL}/writing/projects/${selectedProjectId}/sections/${encodeURIComponent(
          sectionName
        )}/generate`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            instruction,
          }),
        }
      );

      const draft =
        typeof responseData?.draft === "string"
          ? responseData.draft.trim()
          : "";

      if (!draft) {
        throw new Error(
          responseData?.evidence_note ||
            "The backend returned no manuscript text."
        );
      }

      updateSection(sectionName, draft);

      const evidence =
        safeObject(responseData?.evidence);

      setGenerationEvidence({
        mode:
          responseData?.generation_mode || "ai",
        literatureCount:
          evidence.literature_count ?? null,
        contextCount:
          evidence.context_literature_count ?? null,
        analysedCount:
          evidence.analysed_paper_count ?? null,
        paperIds: safeArray(
          evidence.paper_ids
        ),
        note:
          responseData?.evidence_note ||
          evidence.evidence_note ||
          "Generated from project-scoped evidence.",
      });

      if (!options.silent) {
        setSuccess(
          `${SECTION_LABELS[sectionName]} generated from Project #${selectedProjectId}. Review the evidence before saving.`
        );
      }

      return draft;
    } catch (err) {
      console.error(
        "ResearchMate manuscript generation failed:",
        err
      );

      if (!options.silent) {
        setError(
          err.message ||
            "AI generation failed. No unsupported fallback content was inserted."
        );
      }

      if (options.throwOnError) {
        throw err;
      }

      return "";
    } finally {
      if (!options.silent) {
        setAiLoading(false);
        setGenerationSection("");
      }
    }
  }

  async function generateFullManuscript() {
    if (!selectedProjectId) {
      setError(
        "Select a research project first."
      );
      return;
    }

    if (
      fullGenerationLoading ||
      aiLoading ||
      metadataLoading
    ) {
      return;
    }

    setFullGenerationLoading(true);
    clearMessages();

    try {
      /*
       * Important fix:
       * The previous implementation swallowed metadata errors and then
       * continued. Full generation now stops on a real metadata failure.
       */
      await generateMetadata({
        throwOnError: true,
      });

      for (const sectionName of GENERATION_ORDER) {
        setGenerationSection(sectionName);

        const generated =
          await generateDraft(
            sectionName,
            {
              silent: true,
              throwOnError: true,
            }
          );

        if (!generated) {
          throw new Error(
            `Generation stopped at ${SECTION_LABELS[sectionName]}.`
          );
        }
      }

      setDirty(true);

      setSuccess(
        "Manuscript generation completed section-by-section. Review every section before saving."
      );
    } catch (err) {
      setError(
        err.message ||
          "Could not generate the complete manuscript."
      );
    } finally {
      setGenerationSection("");
      setFullGenerationLoading(false);
    }
  }

  async function saveManuscript() {
    if (!selectedProjectId) {
      setError(
        "Select a research project first."
      );
      return;
    }

    if (saving) return;

    setSaving(true);
    clearMessages();

    try {
      const payload = {
        paper_id:
          manuscript.paper_id ?? null,
        title: manuscript.title || "",
        abstract:
          manuscript.abstract || "",
        keywords: safeArray(
          manuscript.keywords
        ),
        sections: safeObject(
          manuscript.sections
        ),
        status:
          manuscript.status || "draft",
        change_summary:
          "Manual manuscript save.",
      };

      const exists = Boolean(
        manuscript.id
      );

      const data = await apiJson(
        `${API_BASE_URL}/writing/projects/${selectedProjectId}/manuscript`,
        {
          method: exists
            ? "PUT"
            : "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify(payload),
        }
      );

      const normalized =
        normalizeManuscript(
          data,
          selectedProjectId
        );

      setManuscript(normalized);
      setDirty(false);
      setLocalBackupAvailable(false);
      setLastSavedAt(new Date());

      try {
        localStorage.removeItem(
          `researchmate:writing-backup:${selectedProjectId}`
        );
      } catch {
        // Ignore local storage failures.
      }

      setSuccess(
        exists
          ? "Manuscript saved successfully."
          : "Manuscript created successfully."
      );

      await loadVersions();
      await loadReadiness();
    } catch (err) {
      setError(
        err.message ||
          "Could not save manuscript."
      );
    } finally {
      setSaving(false);
    }
  }

  async function restoreVersion(versionId) {
    if (!selectedProjectId) return;

    clearMessages();

    try {
      const data = await apiJson(
        `${API_BASE_URL}/writing/projects/${selectedProjectId}/versions/${versionId}/restore`,
        {
          method: "POST",
        }
      );

      setManuscript(
        normalizeManuscript(
          data,
          selectedProjectId
        )
      );

      setDirty(false);
      setLastSavedAt(new Date());

      setSuccess(
        "Version restored successfully."
      );

      await loadVersions();
      await loadReadiness();
    } catch (err) {
      setError(
        err.message ||
          "Could not restore version."
      );
    }
  }

  async function assistWriting() {
    const content =
      manuscript.sections?.[
        activeSection
      ] || "";

    if (!selectedProjectId) {
      setError(
        "Select a research project first."
      );
      return;
    }

    if (!content.trim()) {
      setError(
        "Generate or write content in this section first."
      );
      return;
    }

    const selectedOption =
      IMPROVE_OPTIONS.find(
        (option) =>
          option.key === improveMode
      ) || IMPROVE_OPTIONS[0];

    setImproving(true);
    clearMessages();

    try {
      const data = await apiJson(
        `${API_BASE_URL}/writing/projects/${selectedProjectId}/sections/${activeSection}/assist`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            instruction: [
              selectedOption.instruction,
              "Do not invent research facts, results, citations, DOI, datasets, metrics or numerical values.",
              "Use only the existing section content and project evidence.",
            ].join(" "),
            section_name:
              activeSection,
            content,
            mode: "improve",
          }),
        }
      );

      if (
        data?.success &&
        typeof data.improved_text ===
          "string" &&
        data.improved_text.trim()
      ) {
        updateSection(
          activeSection,
          data.improved_text.trim()
        );

        setShowImproveModal(false);

        setSuccess(
          "AI improvement generated. Review the changes before saving."
        );
      } else {
        throw new Error(
          data?.evidence_note ||
            "AI improvement returned no usable text."
        );
      }
    } catch (err) {
      setError(
        err.message ||
          "AI writing assistance failed."
      );
    } finally {
      setImproving(false);
    }
  }

  function restoreLocalBackup() {
    if (!selectedProjectId) return;

    try {
      const raw =
        localStorage.getItem(
          `researchmate:writing-backup:${selectedProjectId}`
        );

      if (!raw) {
        setLocalBackupAvailable(false);
        return;
      }

      const backup = JSON.parse(raw);

      if (!backup?.manuscript) {
        setLocalBackupAvailable(false);
        return;
      }

      setManuscript(
        normalizeManuscript(
          backup.manuscript,
          selectedProjectId
        )
      );

      setDirty(true);
      setLocalBackupAvailable(false);
      setSuccess(
        "Local unsaved draft restored. Save it to the server when ready."
      );
    } catch {
      setError(
        "The local draft could not be restored."
      );
    }
  }

  function clearLocalBackup() {
    if (!selectedProjectId) return;

    try {
      localStorage.removeItem(
        `researchmate:writing-backup:${selectedProjectId}`
      );
    } catch {
      // Ignore.
    }

    setLocalBackupAvailable(false);
  }

  function toggleGroup(groupKey) {
    setCollapsedGroups(
      (current) => ({
        ...current,
        [groupKey]:
          !current[groupKey],
      })
    );
  }

  function selectSection(sectionKey) {
    setActiveSection(sectionKey);

    const element =
      document.getElementById(
        `wm-section-${sectionKey}`
      );

    if (element) {
      element.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
  }

  const readinessPercentage = Math.min(
    100,
    Math.max(
      0,
      Number(
        readiness?.readiness_percentage
      ) || 0
    )
  );

  return (
    <div className="wm-page">
      <style>{`
        .wm-page{
          color:#102b45;
          max-width:1500px;
          margin:0 auto;
          padding:20px 0 48px;
        }

        .wm-page *{
          box-sizing:border-box;
        }

        .wm-hero{
          border:1px solid #dfe8ee;
          border-radius:24px;
          padding:28px;
          background:linear-gradient(135deg,#f9fffd,#fff 58%,#f4f8ff);
        }

        .wm-kicker{
          font-size:10px;
          letter-spacing:.16em;
          font-weight:850;
          color:#13906b;
          display:flex;
          gap:7px;
          align-items:center;
        }

        .wm-hero h1{
          font-size:clamp(28px,4vw,42px);
          line-height:1.08;
          letter-spacing:-.04em;
          margin:10px 0 8px;
        }

        .wm-hero p{
          max-width:820px;
          color:#718296;
          line-height:1.65;
          font-size:14px;
          margin:0;
        }

        .wm-top-grid{
          display:grid;
          grid-template-columns:minmax(0,1fr) minmax(280px,390px);
          gap:12px;
          margin-top:18px;
        }

        .wm-control{
          background:#fff;
          border:1px solid #dfe7ed;
          border-radius:13px;
          padding:12px;
        }

        .wm-control label,
        .wm-label{
          display:block;
          font-size:9px;
          font-weight:850;
          letter-spacing:.1em;
          color:#7d8b99;
        }

        .wm-control input,
        .wm-control textarea,
        .wm-control select{
          width:100%;
          margin-top:7px;
          border:1px solid #dfe6eb;
          border-radius:9px;
          padding:10px 11px;
          outline:none;
          font:inherit;
          color:#30465b;
          background:#fff;
        }

        .wm-control textarea{
          resize:vertical;
        }

        .wm-project-select{
          min-height:44px;
          font-size:14px;
        }

        .wm-btn{
          border:0;
          border-radius:10px;
          padding:10px 14px;
          background:#123d55;
          color:#fff;
          font-weight:800;
          display:inline-flex;
          gap:8px;
          align-items:center;
          justify-content:center;
          cursor:pointer;
          transition:.15s ease;
        }

        .wm-btn:hover:not(:disabled){
          transform:translateY(-1px);
        }

        .wm-btn.secondary{
          background:#fff;
          color:#3c556c;
          border:1px solid #dce5eb;
        }

        .wm-btn.ai{
          background:#15906a;
        }

        .wm-btn.danger{
          color:#9a4c4c;
        }

        .wm-btn:disabled{
          opacity:.58;
          cursor:not-allowed;
          transform:none;
        }

        .wm-actions{
          display:flex;
          gap:8px;
          flex-wrap:wrap;
          margin-top:12px;
        }

        .wm-message{
          margin-top:12px;
          border-radius:11px;
          padding:11px 13px;
          font-size:12px;
          line-height:1.5;
          display:flex;
          gap:8px;
          align-items:flex-start;
        }

        .wm-error{
          background:#fff6f0;
          border:1px solid #f3d9c4;
          color:#875b3c;
        }

        .wm-success{
          background:#f0faf5;
          border:1px solid #cfe9dc;
          color:#287254;
        }

        .wm-card{
          background:#fff;
          border:1px solid #e1e8ed;
          border-radius:17px;
          box-shadow:0 7px 24px rgba(16,43,69,.035);
        }

        .wm-evidence{
          margin-top:12px;
          padding:16px;
        }

        .wm-evidence-top{
          display:flex;
          justify-content:space-between;
          gap:16px;
          flex-wrap:wrap;
          align-items:flex-start;
        }

        .wm-evidence-title{
          font-size:16px;
          font-weight:800;
          color:#23445c;
          margin-top:6px;
        }

        .wm-evidence-description{
          margin:7px 0 0;
          font-size:12px;
          line-height:1.55;
          color:#64788a;
          max-width:850px;
        }

        .wm-counts{
          display:grid;
          grid-template-columns:repeat(3,minmax(95px,1fr));
          gap:8px;
          min-width:320px;
        }

        .wm-count{
          padding:10px 11px;
          border:1px solid #e1ebe6;
          border-radius:11px;
          background:#fbfefd;
        }

        .wm-count strong{
          display:block;
          margin-top:5px;
          font-size:20px;
        }

        .wm-progress-wrap{
          margin-top:14px;
          padding-top:13px;
          border-top:1px solid #e7efeb;
        }

        .wm-progress-head{
          display:flex;
          justify-content:space-between;
          gap:10px;
          align-items:center;
          font-size:12px;
          color:#65788a;
        }

        .wm-progress{
          height:8px;
          background:#e8efec;
          border-radius:99px;
          overflow:hidden;
          margin-top:9px;
        }

        .wm-progress > div{
          height:100%;
          background:#15906a;
          transition:width .25s ease;
        }

        .wm-workspace{
          display:grid;
          grid-template-columns:245px minmax(0,1fr) 285px;
          gap:14px;
          align-items:start;
          margin-top:15px;
        }

        .wm-sidebar,
        .wm-rightbar{
          position:sticky;
          top:12px;
          max-height:calc(100vh - 24px);
          overflow:auto;
        }

        .wm-sidebar{
          padding:9px;
        }

        .wm-sidebar-title{
          padding:8px 9px 10px;
          font-size:11px;
          font-weight:850;
          letter-spacing:.08em;
          color:#7d8b99;
        }

        .wm-group{
          border-top:1px solid #eef2f4;
        }

        .wm-group:first-of-type{
          border-top:0;
        }

        .wm-group-head{
          width:100%;
          border:0;
          background:transparent;
          padding:9px;
          display:flex;
          align-items:center;
          gap:7px;
          text-align:left;
          cursor:pointer;
          color:#506579;
          font-weight:800;
          font-size:11px;
        }

        .wm-section-btn{
          width:100%;
          text-align:left;
          border:0;
          background:transparent;
          padding:8px 9px 8px 29px;
          border-radius:8px;
          color:#687b8d;
          cursor:pointer;
          font-size:11px;
          line-height:1.35;
          display:flex;
          align-items:center;
          gap:7px;
        }

        .wm-section-btn:hover{
          background:#f7faf9;
        }

        .wm-section-btn.active{
          background:#eaf7f2;
          color:#137353;
          font-weight:800;
        }

        .wm-section-status{
          margin-left:auto;
          flex-shrink:0;
        }

        .wm-editor-column{
          min-width:0;
        }

        .wm-editor-card{
          padding:19px;
          scroll-margin-top:16px;
        }

        .wm-editor-header{
          display:flex;
          justify-content:space-between;
          gap:12px;
          align-items:flex-start;
          flex-wrap:wrap;
        }

        .wm-editor-header h2{
          margin:4px 0 0;
          font-size:21px;
        }

        .wm-status-line{
          display:flex;
          align-items:center;
          gap:7px;
          flex-wrap:wrap;
          margin-top:7px;
          color:#81909d;
          font-size:11px;
        }

        .wm-status-dot{
          width:7px;
          height:7px;
          border-radius:50%;
          background:#15906a;
        }

        .wm-editor{
          width:100%;
          min-height:460px;
          resize:vertical;
          margin-top:15px;
          border:1px solid #dfe6eb;
          border-radius:13px;
          padding:16px;
          outline:none;
          font:14px/1.8 Arial,sans-serif;
          color:#30465b;
          background:#fff;
        }

        .wm-editor:focus{
          border-color:#78bfa4;
          box-shadow:0 0 0 3px rgba(21,144,106,.08);
        }

        .wm-editor-footer{
          display:flex;
          justify-content:space-between;
          gap:10px;
          color:#8493a1;
          font-size:11px;
          margin-top:9px;
        }

        .wm-source-card{
          padding:18px;
        }

        .wm-source-list{
          display:grid;
          gap:10px;
          margin-top:12px;
        }

        .wm-paper{
          border:1px solid #e2e9ee;
          border-radius:12px;
          padding:13px 14px;
          background:#fff;
          transition:
            border-color .15s ease,
            box-shadow .15s ease,
            transform .15s ease;
        }

        .wm-paper:hover{
          border-color:#cbd9df;
          box-shadow:0 5px 16px rgba(35,59,82,.07);
          transform:translateY(-1px);
        }

        .wm-paper-title{
          font-family:
            Inter,
            ui-sans-serif,
            system-ui,
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            sans-serif;
          font-size:14px;
          font-weight:700;
          color:#193b55;
          line-height:1.48;
          letter-spacing:-.01em;
        }

        .wm-paper-meta{
          margin-top:7px;
          color:#66798a;
          font-size:11px;
          line-height:1.55;
          font-family:
            Inter,
            ui-sans-serif,
            system-ui,
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            sans-serif;
        }

        .wm-paper-abstract{
          margin-top:7px;
          color:#526879;
          font-size:11.5px;
          line-height:1.6;
          display:-webkit-box;
          -webkit-line-clamp:3;
          -webkit-box-orient:vertical;
          overflow:hidden;
        }

        .wm-related-label{
          margin-top:8px;
          font-size:10px;
          font-weight:700;
          color:#14866f;
          letter-spacing:.03em;
        }

        .wm-badge-row{
          display:flex;
          gap:5px;
          flex-wrap:wrap;
          margin-top:7px;
        }

        .wm-badge{
          display:inline-flex;
          align-items:center;
          gap:4px;
          font-size:9px;
          font-weight:800;
          padding:4px 6px;
          border-radius:999px;
          background:#f3f6f8;
          color:#718296;
        }

        .wm-badge.green{
          background:#eaf7f2;
          color:#137353;
        }

        .wm-badge.blue{
          background:#eef4ff;
          color:#45689b;
        }

        .wm-paper-actions{
          display:flex;
          gap:5px;
          margin-top:8px;
        }

        .wm-mini-btn{
          border:1px solid #dce5eb;
          background:#fff;
          color:#3c556c;
          border-radius:7px;
          padding:5px 7px;
          font-size:9px;
          cursor:pointer;
          display:inline-flex;
          align-items:center;
          gap:4px;
        }

        .wm-paper-controls{
          display:grid;
          gap:8px;
          margin-top:10px;
        }

        .wm-search-row{
          display:flex;
          gap:7px;
        }

        .wm-search-row input{
          min-width:0;
          flex:1;
          border:1px solid #dce7e3;
          border-radius:9px;
          padding:9px;
          font:inherit;
          outline:none;
        }

        .wm-filter-row{
          display:flex;
          gap:5px;
          flex-wrap:wrap;
        }

        .wm-filter{
          border:1px solid #dce5eb;
          background:#fff;
          color:#6a7d8f;
          border-radius:999px;
          padding:6px 8px;
          font-size:9px;
          cursor:pointer;
        }

        .wm-filter.active{
          background:#eaf7f2;
          border-color:#cfe8dd;
          color:#137353;
          font-weight:800;
        }

        .wm-pagination{
          display:flex;
          align-items:center;
          justify-content:space-between;
          gap:7px;
          margin-top:9px;
          font-size:9px;
          color:#82919e;
        }

        .wm-pagination button{
          border:1px solid #dce5eb;
          background:#fff;
          border-radius:7px;
          padding:5px 7px;
          cursor:pointer;
          color:#506579;
        }

        .wm-pagination button:disabled{
          opacity:.45;
          cursor:not-allowed;
        }

        .wm-empty{
          text-align:center;
          padding:28px 15px;
          color:#7b8998;
          border:1px dashed #dce4e9;
          border-radius:12px;
        }

        .wm-metadata{
          padding:18px;
          margin-top:14px;
        }

        .wm-metadata input,
        .wm-metadata textarea{
          width:100%;
          border:1px solid #dfe6eb;
          border-radius:10px;
          padding:11px;
          margin-top:9px;
          font:inherit;
          outline:none;
        }

        .wm-metadata textarea{
          min-height:160px;
          resize:vertical;
          line-height:1.6;
        }

        .wm-bottom-actions{
          display:flex;
          justify-content:space-between;
          align-items:center;
          gap:10px;
          flex-wrap:wrap;
          margin-top:14px;
        }

        .wm-save-state{
          font-size:11px;
          color:#7c8d9c;
          display:flex;
          align-items:center;
          gap:7px;
        }

        .wm-stat-grid{
          display:grid;
          grid-template-columns:repeat(4,1fr);
          gap:10px;
          margin-top:14px;
        }

        .wm-stat{
          background:#fff;
          border:1px solid #e1e8ed;
          border-radius:14px;
          padding:13px;
          min-width:0;
        }

        .wm-stat span{
          font-size:9px;
          letter-spacing:.1em;
          color:#8996a3;
          font-weight:850;
        }

        .wm-stat strong{
          font-size:17px;
          display:block;
          margin-top:6px;
          overflow:hidden;
          text-overflow:ellipsis;
          white-space:nowrap;
        }

        .wm-readiness{
          padding:16px;
          margin-top:14px;
        }

        .wm-version{
          display:flex;
          justify-content:space-between;
          gap:10px;
          align-items:center;
          padding:11px 0;
          border-bottom:1px solid #eef1f3;
          font-size:11px;
        }

        .wm-version:last-child{
          border-bottom:0;
        }

        .wm-overlay{
          position:fixed;
          inset:0;
          z-index:2000;
          background:rgba(15,23,42,.42);
          display:flex;
          align-items:center;
          justify-content:center;
          padding:20px;
        }

        .wm-modal{
          width:min(720px,100%);
          max-height:90vh;
          overflow:auto;
          background:#fff;
          border-radius:20px;
          padding:22px;
          box-shadow:0 24px 80px rgba(15,23,42,.22);
          border:1px solid #e4eaf0;
        }

        .wm-option{
          display:flex;
          gap:10px;
          align-items:flex-start;
          padding:11px;
          border:1px solid #e3e9ed;
          border-radius:10px;
          cursor:pointer;
        }

        .wm-option.selected{
          border-color:#b9dfd0;
          background:#f4fbf8;
        }

        .wm-option input{
          margin-top:3px;
        }

        .wm-spin{
          animation:wmspin .9s linear infinite;
        }

        @keyframes wmspin{
          to{transform:rotate(360deg)}
        }

        @media(max-width:1180px){
          .wm-workspace{
            grid-template-columns:220px minmax(0,1fr);
          }

          .wm-rightbar{
            grid-column:1 / -1;
            position:static;
            max-height:none;
          }

          .wm-rightbar-inner{
            display:grid;
            grid-template-columns:1fr 1fr;
            gap:12px;
          }
        }

        @media(max-width:800px){
          .wm-top-grid{
            grid-template-columns:1fr;
          }

          .wm-workspace{
            grid-template-columns:1fr;
          }

          .wm-sidebar{
            position:static;
            max-height:none;
          }

          .wm-sidebar-groups{
            display:grid;
            grid-template-columns:1fr 1fr;
            gap:5px;
          }

          .wm-rightbar-inner{
            grid-template-columns:1fr;
          }

          .wm-counts{
            min-width:0;
            width:100%;
          }

          .wm-stat-grid{
            grid-template-columns:1fr 1fr;
          }
        }

        @media(max-width:560px){
          .wm-page{
            padding-top:8px;
          }

          .wm-hero{
            padding:19px;
            border-radius:18px;
          }

          .wm-search-row{
            flex-direction:column;
          }

          .wm-sidebar-groups{
            grid-template-columns:1fr;
          }

          .wm-stat-grid{
            grid-template-columns:1fr;
          }

          .wm-editor-card{
            padding:13px;
          }

          .wm-editor{
            min-height:390px;
          }
        }
      `}</style>

      <section className="wm-hero">
        <div className="wm-kicker">
          <PenLine size={14} />
          RESEARCH WRITING
        </div>

        <h1>
          Build a publication-ready manuscript.
        </h1>

        <p>
          Work section-by-section using the same
          project literature, research gap and
          research context used by ResearchMate.
          AI content remains editable and must be
          reviewed before saving.
        </p>

        <div className="wm-top-grid">
          <div className="wm-control">
            <label>RESEARCH PROJECT</label>
            <select
              className="wm-project-select"
              value={selectedProjectId}
              onChange={(event) => {
                if (
                  dirty &&
                  !window.confirm(
                    "You have unsaved manuscript changes. Switch projects anyway?"
                  )
                ) {
                  return;
                }

                setSelectedProjectId(
                  event.target.value
                );
              }}
              disabled={loadingProjects}
            >
              <option value="">
                {loadingProjects
                  ? "Loading projects..."
                  : "Select a research project"}
              </option>

              {projects.map((project) => (
                <option
                  key={project.id}
                  value={project.id}
                >
                  {project.title} · Project #
                  {project.id}
                </option>
              ))}
            </select>
          </div>

          <div className="wm-control">
            <label>MANUSCRIPT PROGRESS</label>

            <div
              style={{
                display:"flex",
                justifyContent:"space-between",
                gap:8,
                marginTop:8,
                fontSize:11,
                color:"#718296",
              }}
            >
              <span>
                {completedSections} /{" "}
                {GENERATION_ORDER.length} sections
              </span>
              <strong>
                {manuscriptProgress}%
              </strong>
            </div>

            <div className="wm-progress">
              <div
                style={{
                  width:`${manuscriptProgress}%`,
                }}
              />
            </div>
          </div>
        </div>

        <div className="wm-actions">
          <button
            type="button"
            className="wm-btn secondary"
            onClick={() => {
              clearMessages();
              setShowNewProject(true);
            }}
          >
            <Plus size={15} />
            New Research Project
          </button>

          <button
            type="button"
            className="wm-btn ai"
            onClick={generateFullManuscript}
            disabled={
              fullGenerationLoading ||
              aiLoading ||
              metadataLoading ||
              !selectedProjectId
            }
          >
            {fullGenerationLoading ? (
              <Loader2
                size={15}
                className="wm-spin"
              />
            ) : (
              <WandSparkles size={15} />
            )}

            {fullGenerationLoading
              ? generationSection
                ? `Generating ${SECTION_LABELS[generationSection]}…`
                : "Generating Manuscript…"
              : "Generate Full Manuscript"}
          </button>

          <button
            type="button"
            className="wm-btn secondary"
            onClick={() =>
              generateMetadata()
            }
            disabled={
              metadataLoading ||
              fullGenerationLoading ||
              !selectedProjectId
            }
          >
            {metadataLoading ? (
              <Loader2
                size={15}
                className="wm-spin"
              />
            ) : (
              <Sparkles size={15} />
            )}
            Generate Title & Abstract
          </button>
        </div>

        {selectedProjectId && (
          <div
            className="wm-card"
            style={{
              marginTop:12,
              padding:"13px 15px",
              background:"#fbfefd",
            }}
          >
            <div className="wm-label">
              RESEARCH TOPIC FOR THIS PROJECT
            </div>

            <div
              style={{
                display:"flex",
                gap:8,
                alignItems:"center",
                marginTop:7,
                flexWrap:"wrap",
              }}
            >
              <select
                value={selectedTopicId}
                aria-label="Research topic for this project"
                onChange={(event) => {
                  const nextId =
                    event.target.value;

                  setSelectedTopicId(nextId);

                  const topic =
                    researchTopics.find(
                      (item) =>
                        String(item.id) ===
                        String(nextId)
                    );

                  setPaperSearchQuery(
                    topic?.topic?.trim() ||
                      selectedProject?.title?.trim() ||
                      ""
                  );

                  try {
                    localStorage.setItem(
                      `researchmate:selectedTopicId:${selectedProjectId}`,
                      String(nextId)
                    );
                  } catch {
                    // Ignore.
                  }
                }}
                style={{
                  flex:"1 1 360px",
                  minHeight:40,
                  border:"1px solid #dce7e3",
                  borderRadius:9,
                  padding:"0 11px",
                  background:"#fff",
                  color:"#233b52",
                  fontSize:13,
                }}
              >
                <option value="">
                  {researchTopics.length
                    ? "Select a saved research topic"
                    : selectedProject?.title
                      ? "Use project title as research topic"
                      : "No research topic available"}
                </option>

                {researchTopics.map(
                  (topic) => (
                    <option
                      key={topic.id}
                      value={topic.id}
                    >
                      {topic.topic}
                    </option>
                  )
                )}
              </select>

              {selectedTopicText && (
                <button
                  type="button"
                  className="wm-btn secondary"
                  onClick={async () => {
                    const topicText =
                      selectedTopic?.topic?.trim() ||
                      selectedProject?.title?.trim() ||
                      "";

                    if (!topicText) {
                      setError(
                        "No research topic is available for this project."
                      );
                      return;
                    }

                    setPaperSearchQuery(topicText);
                    setShowPaperSearch(true);
                    await searchProjectPapers(topicText);
                  }}
                >
                  <Search size={14} />
                  Find Related Papers
                </button>
              )}
            </div>

            <div
              style={{
                marginTop:9,
                padding:"8px 10px",
                border:"1px solid #e5eee9",
                borderRadius:9,
                background:"#fff",
                fontSize:11,
                color:"#587082",
              }}
            >
              <strong style={{color:"#2d5369"}}>
                Active topic:
              </strong>{" "}
              {selectedTopicText || "No topic selected"}
              {!selectedTopicId && selectedTopicText
                ? " · using project title"
                : ""}
            </div>

            <div
              style={{
                marginTop:6,
                fontSize:10,
                color:"#7b8997",
                lineHeight:1.5,
              }}
            >
              This topic is used by manuscript generation
              and literature search. Saved topics are scoped
              to this project. If no saved topic exists,
              the selected project's title is used as the
              fallback research topic.
            </div>
          </div>
        )}
      </section>

      {selectedProjectId && (
        <section className="wm-card wm-evidence">
          <div className="wm-evidence-top">
            <div
              style={{
                minWidth:260,
                flex:"1 1 450px",
              }}
            >
              <div className="wm-label">
                PROJECT EVIDENCE
              </div>

              <div className="wm-evidence-title">
                {selectedProject?.title ||
                  "Selected research project"}
              </div>

              <div
                style={{
                  marginTop:5,
                  fontSize:11,
                  color:"#718296",
                }}
              >
                {selectedProject?.research_field ||
                  "Research field not stored"}
                {" · "}
                Project #
                {selectedProject?.id || "—"}
              </div>

              <p className="wm-evidence-description">
                {selectedProject?.description ||
                  "No project description is stored. Missing research facts will not be invented."}
              </p>
            </div>

            <div className="wm-counts">
              <div className="wm-count">
                <div className="wm-label">
                  SAVED PAPERS
                </div>
                <strong>
                  {savedPaperCount}
                </strong>
              </div>

              <div className="wm-count">
                <div className="wm-label">
                  CONTEXT PAPERS
                </div>
                <strong>
                  {contextPaperCount}
                </strong>
              </div>

              <div className="wm-count">
                <div className="wm-label">
                  ANALYSED PAPERS
                </div>
                <strong>
                  {analysedPaperCount}
                </strong>
              </div>
            </div>
          </div>

          <div className="wm-progress-wrap">
            <div className="wm-progress-head">
              <span>
                Manuscript completion
              </span>
              <strong>
                {manuscriptProgress}%
              </strong>
            </div>

            <div className="wm-progress">
              <div
                style={{
                  width:`${manuscriptProgress}%`,
                }}
              />
            </div>
          </div>
        </section>
      )}

      {error && (
        <div className="wm-message wm-error">
          <TriangleAlert
            size={16}
            style={{ flexShrink:0 }}
          />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="wm-message wm-success">
          <CheckCircle2
            size={16}
            style={{ flexShrink:0 }}
          />
          <span>{success}</span>
        </div>
      )}

      {localBackupAvailable && (
        <div className="wm-message wm-success">
          <RefreshCw
            size={16}
            style={{ flexShrink:0 }}
          />
          <span style={{flex:1}}>
            A newer local unsaved draft was found for
            this project.
          </span>

          <button
            type="button"
            className="wm-btn secondary"
            onClick={restoreLocalBackup}
            style={{
              padding:"6px 9px",
              fontSize:10,
            }}
          >
            Restore
          </button>

          <button
            type="button"
            className="wm-btn secondary"
            onClick={clearLocalBackup}
            style={{
              padding:"6px 9px",
              fontSize:10,
            }}
          >
            Dismiss
          </button>
        </div>
      )}

      {!selectedProjectId ? (
        <div
          className="wm-card wm-empty"
          style={{marginTop:15}}
        >
          <FileText size={30} />

          <h3>
            Select a research project
          </h3>

          <div>
            The manuscript, literature and AI
            context remain connected to that project.
          </div>
        </div>
      ) : loadingManuscript ? (
        <div
          className="wm-card wm-empty"
          style={{marginTop:15}}
        >
          <Loader2
            size={30}
            className="wm-spin"
          />

          <h3>
            Loading manuscript...
          </h3>
        </div>
      ) : (
        <>
          <div className="wm-workspace">
            <aside className="wm-card wm-sidebar">
              <div className="wm-sidebar-title">
                MANUSCRIPT SECTIONS
              </div>

              <div className="wm-sidebar-groups">
                {SECTION_GROUPS.map(
                  (group) => {
                    const groupCompleted =
                      group.sections.filter(
                        (key) =>
                          Boolean(
                            manuscript.sections?.[
                              key
                            ]?.trim()
                          )
                      ).length;

                    const collapsed =
                      collapsedGroups[
                        group.key
                      ];

                    return (
                      <div
                        className="wm-group"
                        key={group.key}
                      >
                        <button
                          type="button"
                          className="wm-group-head"
                          onClick={() =>
                            toggleGroup(
                              group.key
                            )
                          }
                          aria-expanded={!collapsed}
                        >
                          {collapsed ? (
                            <ChevronRight
                              size={14}
                            />
                          ) : (
                            <ChevronDown
                              size={14}
                            />
                          )}

                          <span>
                            {group.number}{" "}
                            {group.label}
                          </span>

                          <span
                            style={{
                              marginLeft:"auto",
                              color:"#8a99a6",
                              fontSize:9,
                            }}
                          >
                            {groupCompleted}/
                            {group.sections.length}
                          </span>
                        </button>

                        {!collapsed &&
                          group.sections.map(
                            (sectionKey) => {
                              const complete =
                                Boolean(
                                  manuscript
                                    .sections?.[
                                    sectionKey
                                  ]?.trim()
                                );

                              const generating =
                                generationSection ===
                                sectionKey;

                              return (
                                <button
                                  key={
                                    sectionKey
                                  }
                                  type="button"
                                  className={`wm-section-btn ${
                                    activeSection ===
                                    sectionKey
                                      ? "active"
                                      : ""
                                  }`}
                                  onClick={() =>
                                    selectSection(
                                      sectionKey
                                    )
                                  }
                                >
                                  {complete ? (
                                    <Check
                                      size={12}
                                    />
                                  ) : generating ? (
                                    <Loader2
                                      size={12}
                                      className="wm-spin"
                                    />
                                  ) : (
                                    <Circle
                                      size={9}
                                    />
                                  )}

                                  <span>
                                    {
                                      SECTION_LABELS[
                                        sectionKey
                                      ]
                                    }
                                  </span>
                                </button>
                              );
                            }
                          )}
                      </div>
                    );
                  }
                )}
              </div>
            </aside>

            <main className="wm-editor-column">
              <section
                id={`wm-section-${activeSection}`}
                className="wm-card wm-editor-card"
              >
                <div className="wm-editor-header">
                  <div>
                    <div className="wm-label">
                      CURRENT SECTION
                    </div>

                    <h2>
                      {
                        SECTION_LABELS[
                          activeSection
                        ]
                      }
                    </h2>

                    <div className="wm-status-line">
                      <span
                        className="wm-status-dot"
                        style={{
                          background:
                            dirty
                              ? "#d7953c"
                              : "#15906a",
                        }}
                      />

                      {dirty
                        ? "Unsaved changes"
                        : "Saved"}

                      {generationSection ===
                        activeSection && (
                        <>
                          ·
                          <Loader2
                            size={12}
                            className="wm-spin"
                          />
                          Generating...
                        </>
                      )}
                    </div>
                  </div>

                  <div
                    className="wm-actions"
                    style={{marginTop:0}}
                  >
                    <button
                      type="button"
                      className="wm-btn ai"
                      onClick={() =>
                        generateDraft()
                      }
                      disabled={
                        aiLoading ||
                        fullGenerationLoading ||
                        !selectedProjectId
                      }
                    >
                      {generationSection ===
                      activeSection ? (
                        <Loader2
                          size={15}
                          className="wm-spin"
                        />
                      ) : (
                        <Sparkles size={15} />
                      )}

                      {generationSection ===
                      activeSection
                        ? "Generating..."
                        : "Generate Draft"}
                    </button>

                    <button
                      type="button"
                      className="wm-btn secondary"
                      onClick={() =>
                        setShowImproveModal(
                          true
                        )
                      }
                      disabled={
                        aiLoading ||
                        fullGenerationLoading ||
                        !currentText.trim()
                      }
                    >
                      <Sparkles size={15} />
                      Improve with AI
                    </button>
                  </div>
                </div>

                <textarea
                  className="wm-editor"
                  value={currentText}
                  onChange={(event) =>
                    updateSection(
                      activeSection,
                      event.target.value
                    )
                  }
                  placeholder={`Write or generate the ${SECTION_LABELS[activeSection]} section here...`}
                  aria-label={`${SECTION_LABELS[activeSection]} editor`}
                />

                <div className="wm-editor-footer">
                  <span>
                    {currentWordCount} words
                  </span>

                  <span>
                    {currentText.length} characters
                  </span>
                </div>
              </section>

              <section className="wm-card wm-metadata">
                <div className="wm-label">
                  MANUSCRIPT METADATA
                </div>

                <div
                  style={{
                    display:"flex",
                    justifyContent:"space-between",
                    gap:12,
                    alignItems:"center",
                    flexWrap:"wrap",
                  }}
                >
                  <h2
                    style={{
                      margin:"5px 0 0",
                      fontSize:19,
                    }}
                  >
                    Title & Abstract
                  </h2>

                  <button
                    type="button"
                    className="wm-btn"
                    onClick={() =>
                      generateMetadata()
                    }
                    disabled={
                      metadataLoading ||
                      fullGenerationLoading
                    }
                  >
                    {metadataLoading ? (
                      <Loader2
                        size={15}
                        className="wm-spin"
                      />
                    ) : (
                      <WandSparkles
                        size={15}
                      />
                    )}
                    Generate Metadata
                  </button>
                </div>

                <input
                  value={
                    manuscript.title || ""
                  }
                  onChange={(event) =>
                    updateField(
                      "title",
                      event.target.value
                    )
                  }
                  placeholder="Research paper title"
                />

                <textarea
                  value={
                    manuscript.abstract || ""
                  }
                  onChange={(event) =>
                    updateField(
                      "abstract",
                      event.target.value
                    )
                  }
                  placeholder="Research abstract"
                />

                <div
                  style={{
                    marginTop:7,
                    fontSize:10,
                    color:"#8493a1",
                  }}
                >
                  {wordCount(
                    manuscript.abstract ||
                      ""
                  )}{" "}
                  abstract words
                </div>
              </section>

              <div className="wm-bottom-actions">
                <div className="wm-save-state">
                  {dirty ? (
                    <>
                      <TriangleAlert
                        size={13}
                      />
                      Unsaved changes
                    </>
                  ) : (
                    <>
                      <CheckCircle2
                        size={13}
                      />
                      {lastSavedAt
                        ? `Saved ${lastSavedAt.toLocaleTimeString()}`
                        : "No unsaved changes"}
                    </>
                  )}
                </div>

                <div className="wm-actions" style={{marginTop:0}}>
                  <button
                    type="button"
                    className="wm-btn"
                    onClick={saveManuscript}
                    disabled={
                      saving ||
                      !selectedProjectId ||
                      !dirty
                    }
                  >
                    {saving ? (
                      <Loader2
                        size={15}
                        className="wm-spin"
                      />
                    ) : (
                      <Save size={15} />
                    )}

                    {saving
                      ? "Saving..."
                      : manuscript.id
                        ? "Save Manuscript"
                        : "Create Manuscript"}
                  </button>

                  <button
                    type="button"
                    className="wm-btn secondary"
                    onClick={() =>
                      loadReadiness()
                    }
                    disabled={
                      loadingReadiness ||
                      !manuscript.id
                    }
                  >
                    {loadingReadiness ? (
                      <Loader2
                        size={15}
                        className="wm-spin"
                      />
                    ) : (
                      <Target size={15} />
                    )}
                    Readiness
                  </button>

                  <button
                    type="button"
                    className="wm-btn secondary"
                    onClick={() => {
                      setShowVersions(
                        (value) => !value
                      );

                      if (!showVersions) {
                        loadVersions();
                      }
                    }}
                    disabled={!manuscript.id}
                  >
                    <History size={15} />
                    Versions
                  </button>
                </div>
              </div>
            </main>

            <aside className="wm-rightbar">
              <div className="wm-rightbar-inner">
                <section className="wm-card wm-source-card">
                  <div className="wm-label">
                    PROJECT LITERATURE
                  </div>

                  <div
                    style={{
                      display:"flex",
                      justifyContent:"space-between",
                      gap:8,
                      alignItems:"center",
                      marginTop:5,
                    }}
                  >
                    <strong
                      style={{
                        fontSize:14,
                        color:"#30465b",
                      }}
                    >
                      {savedPaperCount} saved papers
                    </strong>

                    <button
                      type="button"
                      className="wm-mini-btn"
                      onClick={() =>
                        setShowPaperSearch(
                          (value) => !value
                        )
                      }
                    >
                      <Search size={11} />
                      Find
                    </button>
                  </div>

                  {showPaperSearch && (
                    <div className="wm-paper-controls">
                      <div className="wm-search-row">
                        <input
                          value={
                            savedPaperQuery
                          }
                          onChange={(event) =>
                            setSavedPaperQuery(
                              event.target.value
                            )
                          }
                          onKeyDown={(event) => {
                            if (
                              event.key ===
                              "Enter"
                            ) {
                              searchProjectPapers();
                            }
                          }}
                          placeholder="Search saved papers..."
                        />

                        <button
                          type="button"
                          className="wm-mini-btn"
                          onClick={
                            searchProjectPapers
                          }
                          disabled={
                            paperSearchLoading
                          }
                        >
                          {paperSearchLoading ? (
                            <Loader2
                              size={11}
                              className="wm-spin"
                            />
                          ) : (
                            <Search
                              size={11}
                            />
                          )}
                        </button>
                      </div>

                      <div className="wm-filter-row">
                        {[
                          ["all", "All"],
                          [
                            "analysed",
                            "Analysed",
                          ],
                          [
                            "context",
                            "Context",
                          ],
                          [
                            "not_analysed",
                            "Not analysed",
                          ],
                        ].map(
                          ([key, label]) => (
                            <button
                              key={key}
                              type="button"
                              className={`wm-filter ${
                                paperFilter ===
                                key
                                  ? "active"
                                  : ""
                              }`}
                              onClick={() =>
                                setPaperFilter(
                                  key
                                )
                              }
                            >
                              {label}
                            </button>
                          )
                        )}
                      </div>
                    </div>
                  )}

                  {loadingContext ? (
                    <div
                      className="wm-empty"
                      style={{
                        marginTop:9,
                        padding:18,
                      }}
                    >
                      <Loader2
                        size={18}
                        className="wm-spin"
                      />
                      <div
                        style={{
                          marginTop:6,
                          fontSize:10,
                        }}
                      >
                        Loading literature...
                      </div>
                    </div>
                  ) : visiblePapers.length ? (
                    <div className="wm-source-list">
                      {visiblePapers.map(
                        (paper) => {
                          const id =
                            normalizeId(
                              paperId(
                                paper
                              )
                            );

                          const analysed =
                            Boolean(
                              paper?.analysed
                            ) ||
                            paperStatus.analysedIds.has(
                              id
                            );

                          const context =
                            Boolean(
                              paper?.used_as_context ||
                                paper?.is_context ||
                                paper?.context
                            ) ||
                            paperStatus.contextIds.has(
                              id
                            );

                          return (
                            <div
                              className="wm-paper"
                              key={
                                id ||
                                `${paper.title}-${paper.year}`
                              }
                            >
                              <div className="wm-paper-title">
                                {paper.title ||
                                  "Untitled paper"}
                              </div>

                              <div className="wm-paper-meta">
                                {paper.year ||
                                  "Year unavailable"}
                                {" · "}
                                {paperAuthors(
                                  paper
                                )}
                              </div>

                              <div className="wm-badge-row">
                                <span className="wm-badge green">
                                  Saved
                                </span>

                                {analysed && (
                                  <span className="wm-badge blue">
                                    Analysed
                                  </span>
                                )}

                                {context && (
                                  <span className="wm-badge">
                                    Context
                                  </span>
                                )}
                              </div>

                              <div
                                className="wm-paper-actions"
                                style={{
                                  marginTop:9,
                                  display:"flex",
                                  gap:6,
                                  flexWrap:"wrap",
                                }}
                              >
                                {paper.url && (
                                  <a
                                    href={
                                      paper.url
                                    }
                                    target="_blank"
                                    rel="noreferrer"
                                    className="wm-mini-btn"
                                    style={{
                                      textDecoration:
                                        "none",
                                    }}
                                  >
                                    <ExternalLink
                                      size={10}
                                    />
                                    Open
                                  </a>
                                )}

                                <button
                                  type="button"
                                  className="wm-mini-btn"
                                  onClick={() =>
                                    removeSavedPaper(
                                      paper
                                    )
                                  }
                                  disabled={
                                    paperRemoveId ===
                                    String(id)
                                  }
                                  style={{
                                    borderColor:"#f0caca",
                                    color:"#b43b3b",
                                    background:"#fff8f8",
                                  }}
                                >
                                  {paperRemoveId ===
                                  String(id) ? (
                                    <Loader2
                                      size={10}
                                      className="wm-spin"
                                    />
                                  ) : (
                                    <Trash2
                                      size={10}
                                    />
                                  )}
                                  {paperRemoveId ===
                                  String(id)
                                    ? "Removing..."
                                    : "Remove"}
                                </button>
                              </div>
                            </div>
                          );
                        }
                      )}
                    </div>
                  ) : (
                    <div
                      className="wm-empty"
                      style={{
                        marginTop:9,
                        padding:18,
                        fontSize:10,
                      }}
                    >
                      {papers.length
                        ? "No papers match the current filter."
                        : "No saved papers are available for this project."}
                    </div>
                  )}

                  {filteredPapers.length >
                    PAPERS_PER_PAGE && (
                    <div className="wm-pagination">
                      <span>
                        Showing{" "}
                        {(paperPage - 1) *
                          PAPERS_PER_PAGE +
                          1}
                        –
                        {Math.min(
                          paperPage *
                            PAPERS_PER_PAGE,
                          filteredPapers.length
                        )}{" "}
                        of{" "}
                        {filteredPapers.length}
                      </span>

                      <div
                        style={{
                          display:"flex",
                          gap:5,
                        }}
                      >
                        <button
                          type="button"
                          disabled={
                            paperPage === 1
                          }
                          onClick={() =>
                            setPaperPage(
                              (page) =>
                                Math.max(
                                  1,
                                  page - 1
                                )
                            )
                          }
                        >
                          Prev
                        </button>

                        <button
                          type="button"
                          disabled={
                            paperPage >=
                            paperTotalPages
                          }
                          onClick={() =>
                            setPaperPage(
                              (page) =>
                                Math.min(
                                  paperTotalPages,
                                  page + 1
                                )
                            )
                          }
                        >
                          Next
                        </button>
                      </div>
                    </div>
                  )}
                </section>

                {showPaperSearch && (
                  <section className="wm-card wm-source-card">
                    <div
                      style={{
                        display:"flex",
                        alignItems:"center",
                        justifyContent:"space-between",
                        gap:12,
                      }}
                    >
                      <div>
                        <div className="wm-label">
                          RELATED ACADEMIC LITERATURE
                        </div>
                        <div
                          style={{
                            marginTop:4,
                            fontSize:11,
                            color:"#718296",
                            lineHeight:1.5,
                          }}
                        >
                          Papers ranked by relevance to the selected research topic.
                        </div>
                      </div>

                      <span
                        style={{
                          flexShrink:0,
                          fontSize:10,
                          color:"#587082",
                          background:"#f3f8f6",
                          border:"1px solid #dbeae4",
                          borderRadius:999,
                          padding:"5px 8px",
                        }}
                      >
                        {paperSearchResults.length} found
                      </span>
                    </div>

                    {paperSearchLoading ? (
                      <div
                        className="wm-empty"
                        style={{
                          marginTop:9,
                          padding:18,
                        }}
                      >
                        <Loader2
                          size={18}
                          className="wm-spin"
                        />
                      </div>
                    ) : paperSearchResults.length ? (
                      <div className="wm-source-list">
                        {paperSearchResults.map(
                          (paper) => (
                            <div
                              className="wm-paper"
                              key={
                                paper.paper_id ||
                                paper.doi ||
                                paper.title
                              }
                            >
                              <div className="wm-paper-title">
                                {paper.title ||
                                  "Untitled paper"}
                              </div>

                              <div className="wm-paper-meta">
                                {paper.year ||
                                  "Year unavailable"}
                                {paper.doi
                                  ? ` · DOI: ${paper.doi}`
                                  : ""}
                                {safeArray(paper.authors).length
                                  ? ` · ${safeArray(paper.authors)
                                      .slice(0, 3)
                                      .join(", ")}`
                                  : ""}
                              </div>

                              {(paper.abstract ||
                                paper.summary) && (
                                <div className="wm-paper-abstract">
                                  {paper.abstract ||
                                    paper.summary}
                                </div>
                              )}

                              <div className="wm-related-label">
                                RELATED TO YOUR RESEARCH TOPIC
                              </div>

                              <div className="wm-paper-actions">
                                {paper.url && (
                                  <a
                                    href={
                                      paper.url
                                    }
                                    target="_blank"
                                    rel="noreferrer"
                                    className="wm-mini-btn"
                                    style={{
                                      textDecoration:
                                        "none",
                                    }}
                                  >
                                    <ExternalLink
                                      size={10}
                                    />
                                  </a>
                                )}

                                <button
                                  type="button"
                                  className="wm-mini-btn"
                                  onClick={() =>
                                    saveProjectPaper(
                                      paper
                                    )
                                  }
                                  disabled={
                                    paper.saved ||
                                    paperSaveId ===
                                      paper.paper_id
                                  }
                                >
                                  {paperSaveId ===
                                  paper.paper_id ? (
                                    <Loader2
                                      size={10}
                                      className="wm-spin"
                                    />
                                  ) : (
                                    <Plus
                                      size={10}
                                    />
                                  )}

                                  {paper.saved
                                    ? "Saved"
                                    : "Save"}
                                </button>
                              </div>
                            </div>
                          )
                        )}
                      </div>
                    ) : (
                      <div
                        className="wm-empty"
                        style={{
                          marginTop:9,
                          padding:18,
                          fontSize:10,
                        }}
                      >
                        Search for a topic, keyword
                        or paper title to find academic
                        papers.
                      </div>
                    )}
                  </section>
                )}

                <section className="wm-card wm-source-card">
                  <div className="wm-label">
                    WRITING STATUS
                  </div>

                  <div
                    style={{
                      marginTop:8,
                      display:"grid",
                      gap:7,
                    }}
                  >
                    <div
                      style={{
                        display:"flex",
                        justifyContent:"space-between",
                        gap:8,
                        fontSize:11,
                      }}
                    >
                      <span>Current section</span>
                      <strong>
                        {
                          SECTION_LABELS[
                            activeSection
                          ]
                        }
                      </strong>
                    </div>

                    <div
                      style={{
                        display:"flex",
                        justifyContent:"space-between",
                        gap:8,
                        fontSize:11,
                      }}
                    >
                      <span>Words</span>
                      <strong>
                        {liveManuscriptWordCount}
                      </strong>
                    </div>

                    <div
                      style={{
                        display:"flex",
                        justifyContent:"space-between",
                        gap:8,
                        fontSize:11,
                      }}
                    >
                      <span>Status</span>
                      <strong>
                        {dirty
                          ? "Unsaved"
                          : manuscript.status ||
                            "draft"}
                      </strong>
                    </div>
                  </div>
                </section>
              </div>
            </aside>
          </div>

          {readiness && (
            <section className="wm-card wm-readiness">
              <div
                style={{
                  display:"flex",
                  justifyContent:"space-between",
                  gap:10,
                  alignItems:"center",
                }}
              >
                <div>
                  <div className="wm-label">
                    RESEARCH WRITING READINESS
                  </div>

                  <h3
                    style={{
                      margin:"5px 0 0",
                    }}
                  >
                    Deterministic readiness check
                  </h3>
                </div>

                <strong
                  style={{fontSize:24}}
                >
                  {readinessPercentage}%
                </strong>
              </div>

              <div className="wm-progress">
                <div
                  style={{
                    width:`${readinessPercentage}%`,
                  }}
                />
              </div>

              <p
                style={{
                  color:"#728394",
                  fontSize:11,
                  marginBottom:0,
                }}
              >
                {readiness.completed_checks ??
                  0}{" "}
                /{" "}
                {readiness.total_checks ??
                  0} deterministic checks completed.
              </p>
            </section>
          )}

          {showVersions && (
            <section
              className="wm-card"
              style={{
                marginTop:14,
                padding:17,
              }}
            >
              <div className="wm-label">
                VERSION HISTORY
              </div>

              <h3>
                Saved manuscript versions
              </h3>

              {loadingVersions ? (
                <div className="wm-empty">
                  <Loader2
                    size={20}
                    className="wm-spin"
                  />
                  <div
                    style={{
                      marginTop:6,
                    }}
                  >
                    Loading versions...
                  </div>
                </div>
              ) : versions.length ? (
                <div>
                  {versions.map(
                    (version) => (
                      <div
                        className="wm-version"
                        key={version.id}
                      >
                        <div>
                          <strong>
                            Version{" "}
                            {
                              version.version_number
                            }
                          </strong>

                          <div
                            style={{
                              color:"#8493a1",
                              marginTop:3,
                            }}
                          >
                            {
                              version.change_summary ||
                              "No change summary."
                            }
                          </div>
                        </div>

                        <button
                          type="button"
                          className="wm-btn secondary"
                          onClick={() =>
                            restoreVersion(
                              version.id
                            )
                          }
                        >
                          <RotateCcw
                            size={13}
                          />
                          Restore
                        </button>
                      </div>
                    )
                  )}
                </div>
              ) : (
                <div className="wm-empty">
                  No saved versions yet.
                </div>
              )}
            </section>
          )}
        </>
      )}

      {showImproveModal && (
        <div
          className="wm-overlay"
          onMouseDown={(event) => {
            if (
              event.target ===
              event.currentTarget
            ) {
              setShowImproveModal(false);
            }
          }}
        >
          <div className="wm-modal">
            <div
              style={{
                display:"flex",
                justifyContent:"space-between",
                gap:12,
                alignItems:"flex-start",
              }}
            >
              <div>
                <div className="wm-kicker">
                  <Sparkles size={13} />
                  AI WRITING ASSIST
                </div>

                <h2
                  style={{
                    margin:"7px 0 5px",
                  }}
                >
                  Improve{" "}
                  {
                    SECTION_LABELS[
                      activeSection
                    ]
                  }
                </h2>

                <p
                  style={{
                    margin:0,
                    color:"#718296",
                    fontSize:12,
                    lineHeight:1.5,
                  }}
                >
                  Choose the type of improvement.
                  The existing section remains in the
                  editor and the returned text is not
                  saved to the server automatically.
                </p>
              </div>

              <button
                type="button"
                className="wm-btn secondary"
                onClick={() =>
                  setShowImproveModal(false)
                }
                style={{
                  padding:8,
                }}
              >
                <X size={16} />
              </button>
            </div>

            <div
              style={{
                display:"grid",
                gap:8,
                marginTop:17,
              }}
            >
              {IMPROVE_OPTIONS.map(
                (option) => (
                  <label
                    key={option.key}
                    className={`wm-option ${
                      improveMode ===
                      option.key
                        ? "selected"
                        : ""
                    }`}
                  >
                    <input
                      type="radio"
                      name="improveMode"
                      value={option.key}
                      checked={
                        improveMode ===
                        option.key
                      }
                      onChange={() =>
                        setImproveMode(
                          option.key
                        )
                      }
                    />

                    <span>
                      <strong
                        style={{
                          fontSize:12,
                          color:"#30465b",
                        }}
                      >
                        {option.label}
                      </strong>

                      <span
                        style={{
                          display:"block",
                          marginTop:3,
                          fontSize:10,
                          color:"#8493a1",
                          lineHeight:1.45,
                        }}
                      >
                        {option.instruction}
                      </span>
                    </span>
                  </label>
                )
              )}
            </div>

            <div
              className="wm-actions"
              style={{
                justifyContent:"flex-end",
                marginTop:17,
              }}
            >
              <button
                type="button"
                className="wm-btn secondary"
                onClick={() =>
                  setShowImproveModal(false)
                }
                disabled={improving}
              >
                Cancel
              </button>

              <button
                type="button"
                className="wm-btn ai"
                onClick={assistWriting}
                disabled={improving}
              >
                {improving ? (
                  <Loader2
                    size={15}
                    className="wm-spin"
                  />
                ) : (
                  <Sparkles size={15} />
                )}

                {improving
                  ? "Improving..."
                  : "Improve Section"}
              </button>
            </div>
          </div>
        </div>
      )}

      {showNewProject && (
        <div
          className="wm-overlay"
          onMouseDown={(event) => {
            if (
              event.target ===
              event.currentTarget
            ) {
              setShowNewProject(false);
            }
          }}
        >
          <div className="wm-modal">
            <div
              style={{
                display:"flex",
                justifyContent:"space-between",
                gap:16,
                alignItems:"flex-start",
              }}
            >
              <div>
                <div className="wm-kicker">
                  <Sparkles size={13} />
                  NEW RESEARCH WORKSPACE
                </div>

                <h2
                  style={{
                    margin:"6px 0",
                  }}
                >
                  Start a new research topic
                </h2>

                <p
                  style={{
                    margin:0,
                    color:"#718096",
                    fontSize:12,
                    lineHeight:1.55,
                  }}
                >
                  Create the project first. The
                  Literature and Writing modules will
                  use this project as the source of
                  context.
                </p>
              </div>

              <button
                type="button"
                className="wm-btn secondary"
                onClick={() =>
                  setShowNewProject(false)
                }
                disabled={creatingProject}
                style={{
                  padding:8,
                }}
              >
                <X size={16} />
              </button>
            </div>

            <div
              style={{
                display:"grid",
                gap:12,
                marginTop:18,
              }}
            >
              <div className="wm-control">
                <label>
                  RESEARCH TOPIC *
                </label>

                <input
                  value={
                    newProject.topic
                  }
                  onChange={(event) =>
                    setNewProject(
                      (current) => ({
                        ...current,
                        topic:
                          event.target
                            .value,
                      })
                    )
                  }
                  placeholder="e.g. Helmet Violation Detection using YOLO"
                  autoFocus
                />
              </div>

              <div className="wm-control">
                <label>
                  RESEARCH FIELD / DOMAIN
                </label>

                <input
                  value={
                    newProject.field
                  }
                  onChange={(event) =>
                    setNewProject(
                      (current) => ({
                        ...current,
                        field:
                          event.target
                            .value,
                      })
                    )
                  }
                  placeholder="e.g. Computer Vision, AI"
                />
              </div>

              <div className="wm-control">
                <label>
                  RESEARCH PROBLEM
                </label>

                <textarea
                  value={
                    newProject.problem
                  }
                  onChange={(event) =>
                    setNewProject(
                      (current) => ({
                        ...current,
                        problem:
                          event.target
                            .value,
                      })
                    )
                  }
                  placeholder="What problem do you want to investigate?"
                  rows={3}
                />
              </div>

              <div className="wm-control">
                <label>
                  RESEARCH OBJECTIVES
                </label>

                <textarea
                  value={
                    newProject.objectives
                  }
                  onChange={(event) =>
                    setNewProject(
                      (current) => ({
                        ...current,
                        objectives:
                          event.target
                            .value,
                      })
                    )
                  }
                  placeholder="Optional. Add known objectives, one per line."
                  rows={3}
                />
              </div>

              <div className="wm-control">
                <label>
                  KEYWORDS
                </label>

                <input
                  value={
                    newProject.keywords
                  }
                  onChange={(event) =>
                    setNewProject(
                      (current) => ({
                        ...current,
                        keywords:
                          event.target
                            .value,
                      })
                    )
                  }
                  placeholder="e.g. YOLO, helmet, traffic safety, computer vision"
                />
              </div>
            </div>

            <div
              style={{
                marginTop:15,
                padding:12,
                borderRadius:11,
                background:"#f5faf8",
                border:"1px solid #d9eee7",
                color:"#315c50",
                fontSize:11,
                lineHeight:1.5,
              }}
            >
              The project becomes active after
              creation. Add and analyse papers from
              Literature before expecting grounded
              literature-heavy manuscript sections.
            </div>

            <div
              className="wm-actions"
              style={{
                justifyContent:"flex-end",
                marginTop:16,
              }}
            >
              <button
                type="button"
                className="wm-btn secondary"
                onClick={() =>
                  setShowNewProject(false)
                }
                disabled={creatingProject}
              >
                Cancel
              </button>

              <button
                type="button"
                className="wm-btn"
                onClick={
                  createNewResearchProject
                }
                disabled={
                  creatingProject ||
                  !newProject.topic.trim()
                }
              >
                {creatingProject ? (
                  <Loader2
                    size={15}
                    className="wm-spin"
                  />
                ) : (
                  <Plus size={15} />
                )}

                {creatingProject
                  ? "Creating..."
                  : "Create Research Project"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default WritingPage;
