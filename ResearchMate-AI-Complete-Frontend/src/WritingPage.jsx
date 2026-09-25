import React, {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  FileCheck2,
  FileText,
  Loader2,
  PenLine,
  RefreshCw,
  Save,
  Sparkles,
  Target,
  TriangleAlert,
  History,
  RotateCcw,
  Plus,
  X,
  Search,
  ExternalLink,
  WandSparkles,
} from "lucide-react";


const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8001";


const EMPTY_MANUSCRIPT = {
  id: null,
  project_id: null,
  paper_id: null,

  title: "",
  abstract: "",

  keywords: [],

  sections: {
    title: "",
    abstract: "",
    keywords: "",
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
  },

  status: "draft",

  current_version: 1,

  word_count: 0,

  character_count: 0,
};


const SECTION_LABELS = {
  introduction: "Introduction",

  background_related_work:
    "Background / Related Work",

  problem_statement:
    "Problem Statement",

  research_objectives:
    "Research Objectives",

  research_questions:
    "Research Questions",

  literature_review:
    "Literature Review",

  research_gap:
    "Research Gap",

  methodology:
    "Methodology",

  dataset_data_collection:
    "Dataset / Data Collection",

  proposed_method_system:
    "Proposed Method / System",

  experimental_setup:
    "Experimental Setup",

  results:
    "Results",

  discussion:
    "Discussion",

  limitations:
    "Limitations",

  conclusion:
    "Conclusion",

  future_work:
    "Future Work",

  references:
    "References",
};


const getError = (
  data,
  fallback = "Something went wrong."
) => {

  if (!data) {
    return fallback;
  }

  if (typeof data === "string") {
    return data;
  }

  if (typeof data.detail === "string") {
    return data.detail;
  }

  if (Array.isArray(data.detail)) {

    return data.detail
      .map(
        (item) =>
          item?.msg ||
          item?.message ||
          String(item)
      )
      .join(", ");
  }

  if (
    data.detail &&
    typeof data.detail === "object"
  ) {

    return (
      data.detail.message ||
      data.detail.msg ||
      fallback
    );
  }

  return (
    data.message ||
    fallback
  );
};


const safeArray = (value) => {

  if (!Array.isArray(value)) {
    return [];
  }

  return value;
};


const safeObject = (value) => {

  if (
    !value ||
    typeof value !== "object" ||
    Array.isArray(value)
  ) {

    return {};
  }

  return value;
};


const wordCount = (text) => {

  if (!text?.trim()) {
    return 0;
  }

  return text
    .trim()
    .split(/\s+/)
    .length;
};


function WritingPage() {

  const [
    projects,
    setProjects,
  ] = useState([]);

  const [
    selectedProjectId,
    setSelectedProjectId,
  ] = useState("");

  const [
    papers,
    setPapers,
  ] = useState([]);

  const [
    projectContext,
    setProjectContext,
  ] = useState(null);

  const [
    loadingContext,
    setLoadingContext,
  ] = useState(false);

  const [
    manuscript,
    setManuscript,
  ] = useState(
    EMPTY_MANUSCRIPT
  );

  const [
    versions,
    setVersions,
  ] = useState([]);

  const [
    readiness,
    setReadiness,
  ] = useState(null);

  const [
    loadingProjects,
    setLoadingProjects,
  ] = useState(true);

  const [
    loadingManuscript,
    setLoadingManuscript,
  ] = useState(false);

  const [
    saving,
    setSaving,
  ] = useState(false);

  const [
    loadingVersions,
    setLoadingVersions,
  ] = useState(false);

  const [
    loadingReadiness,
    setLoadingReadiness,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState("");

  const [
    success,
    setSuccess,
  ] = useState("");

  const [
    activeSection,
    setActiveSection,
  ] = useState(
    "introduction"
  );

  const [
    showVersions,
    setShowVersions,
  ] = useState(false);

  const [
    aiLoading,
    setAiLoading,
  ] = useState(false);

  const [
    showNewProject,
    setShowNewProject,
  ] = useState(false);

  const [
    creatingProject,
    setCreatingProject,
  ] = useState(false);

  const [
    newProject,
    setNewProject,
  ] = useState({
    topic: "",
    field: "",
    problem: "",
    objectives: "",
    keywords: "",
  });


  const [
    paperSearchQuery,
    setPaperSearchQuery,
  ] = useState("");

  const [
    paperSearchResults,
    setPaperSearchResults,
  ] = useState([]);

  const [
    paperSearchLoading,
    setPaperSearchLoading,
  ] = useState(false);

  const [
    paperSaveId,
    setPaperSaveId,
  ] = useState(null);

  const [
    metadataLoading,
    setMetadataLoading,
  ] = useState(false);

  const [
    fullGenerationLoading,
    setFullGenerationLoading,
  ] = useState(false);


  // ==========================================================
  // CREATE NEW RESEARCH PROJECT
  // ==========================================================

  async function createNewResearchProject() {

    const topic = newProject.topic.trim();

    if (!topic) {
      setError("Research topic is required.");
      return;
    }

    setCreatingProject(true);
    setError("");
    setSuccess("");

    try {

      // The current Projects API stores the core project fields.
      // Keep the additional research context inside the project
      // description so the existing database/API architecture remains intact.
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

      const response = await fetch(
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

      const type =
        response.headers.get("content-type") || "";

      const data =
        type.includes("application/json")
          ? await response.json()
          : {};

      if (!response.ok) {
        throw new Error(
          getError(
            data,
            "Could not create the research project."
          )
        );
      }

      const createdProject =
        data?.project || data;

      if (!createdProject?.id) {
        throw new Error(
          "Project was created but the API did not return its project ID."
        );
      }

      setProjects((current) => [
        createdProject,
        ...current.filter(
          (item) => item.id !== createdProject.id
        ),
      ]);

      setSelectedProjectId(
        String(createdProject.id)
      );

      setManuscript({
        ...EMPTY_MANUSCRIPT,
        project_id: Number(createdProject.id),
      });

      setReadiness(null);
      setVersions([]);
      setShowVersions(false);

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


  // ==========================================================
  // PROJECT LITERATURE SEARCH
  // ==========================================================

  const searchProjectPapers = async () => {
    if (!selectedProjectId) {
      setError("Select a research project before searching papers.");
      return;
    }

    const query = (
      paperSearchQuery.trim() ||
      selectedProject?.title?.trim() ||
      ""
    );

    if (query.length < 3) {
      setError("Enter at least 3 characters for the literature search.");
      return;
    }

    setPaperSearchLoading(true);
    setError("");
    setSuccess("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/literature/search?query=${encodeURIComponent(query)}&limit=10&page=1`
      );

      const type = response.headers.get("content-type") || "";
      const data = type.includes("application/json")
        ? await response.json()
        : {};

      if (!response.ok) {
        throw new Error(
          getError(data, "Academic paper search failed.")
        );
      }

      setPaperSearchResults(
        safeArray(data?.papers).map((paper) => ({
          ...paper,
          authors: safeArray(paper?.authors),
        }))
      );

      if (!safeArray(data?.papers).length) {
        setSuccess("No academic papers were returned for this query.");
      }
    } catch (err) {
      setPaperSearchResults([]);
      setError(err.message || "Academic paper search failed.");
    } finally {
      setPaperSearchLoading(false);
    }
  };


  const saveProjectPaper = async (paper) => {
    if (!selectedProjectId || !paper?.paper_id) {
      setError("This paper does not have a valid provider paper ID.");
      return;
    }

    setPaperSaveId(paper.paper_id);
    setError("");
    setSuccess("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/literature/projects/${selectedProjectId}/papers`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            project_id: Number(selectedProjectId),
            paper_id: paper.paper_id,
            title: paper.title,
            abstract: paper.abstract || null,
            year: paper.year || null,
            authors: safeArray(paper.authors)
              .map((author) => author?.name || author)
              .filter(Boolean),
            citation_count: paper.citation_count ?? 0,
            url: paper.url || null,
            doi: paper.doi || null,
          }),
        }
      );

      const type = response.headers.get("content-type") || "";
      const data = type.includes("application/json")
        ? await response.json()
        : {};

      if (!response.ok) {
        throw new Error(
          getError(data, "Could not save this paper to the project.")
        );
      }

      setSuccess("Paper saved to this research project.");
      setPaperSearchResults((current) =>
        current.map((item) =>
          item.paper_id === paper.paper_id
            ? { ...item, saved: true }
            : item
        )
      );

      // Refresh the project evidence so counts and manuscript context are current.
      const contextResponse = await fetch(
        `${API_BASE_URL}/writing/projects/${selectedProjectId}/context`
      );
      const contextType =
        contextResponse.headers.get("content-type") || "";
      const contextData = contextType.includes("application/json")
        ? await contextResponse.json()
        : {};

      if (contextResponse.ok) {
        setProjectContext(contextData);
        setPapers(
          safeArray(contextData.all_literature || contextData.literature)
        );
      }
    } catch (err) {
      setError(
        err.message || "Could not save this paper to the project."
      );
    } finally {
      setPaperSaveId(null);
    }
  };


  // ==========================================================
  // MANUSCRIPT TITLE + ABSTRACT GENERATION
  // ==========================================================

  const generateMetadata = async () => {
    if (!selectedProjectId) {
      setError("Select a research project first.");
      return;
    }

    setMetadataLoading(true);
    setError("");
    setSuccess("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/writing/projects/${selectedProjectId}/metadata/generate`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            instruction:
              "Generate a publication-ready title and structured abstract for this exact research project. Use only stored project facts and project-scoped literature evidence. Do not invent results, datasets, metrics, citations, DOI, sample sizes, or numerical values.",
          }),
        }
      );

      const type = response.headers.get("content-type") || "";
      const data = type.includes("application/json")
        ? await response.json()
        : {};

      if (!response.ok) {
        throw new Error(
          getError(data, "Could not generate manuscript metadata.")
        );
      }

      if (!data?.title?.trim() && !data?.abstract?.trim()) {
        throw new Error("The metadata generator returned no title or abstract.");
      }

      setManuscript((current) => ({
        ...current,
        title: data.title?.trim() || current.title || "",
        abstract: data.abstract?.trim() || current.abstract || "",
        sections: {
          ...current.sections,
          title: data.title?.trim() || current.sections?.title || "",
          abstract: data.abstract?.trim() || current.sections?.abstract || "",
        },
      }));

      setSuccess(
        data.generation_mode === "ai"
          ? "Title and abstract generated from the project evidence. Review them before saving."
          : "Evidence-only title and abstract scaffold generated because AI did not return content."
      );
    } catch (err) {
      setError(
        err.message || "Could not generate manuscript metadata."
      );
    } finally {
      setMetadataLoading(false);
    }
  };


  // ==========================================================
  // LOAD PROJECTS
  // ==========================================================

  useEffect(() => {

    let cancelled = false;

    async function loadProjects() {

      setLoadingProjects(true);
      setError("");

      try {

        const response =
          await fetch(
            `${API_BASE_URL}/projects/`
          );

        const type =
          response.headers.get(
            "content-type"
          ) || "";

        const data =
          type.includes(
            "application/json"
          )
            ? await response.json()
            : [];

        if (!response.ok) {

          throw new Error(
            getError(
              data,
              "Could not load projects."
            )
          );
        }

        if (!cancelled) {

          const list =
            safeArray(data);

          setProjects(list);

          if (list.length) {

            setSelectedProjectId(
              String(list[0].id)
            );
          }
        }

      } catch (err) {

        if (!cancelled) {

          setError(
            err.message ||
            "Could not load projects."
          );
        }

      } finally {

        if (!cancelled) {
          setLoadingProjects(false);
        }
      }
    }

    loadProjects();

    return () => {
      cancelled = true;
    };

  }, []);


  // ==========================================================
  // LOAD PROJECT WRITING CONTEXT
  // ==========================================================

  useEffect(() => {

    if (!selectedProjectId) {

      setPapers([]);
      setProjectContext(null);

      return;
    }

    let cancelled = false;

    async function loadProjectContext() {

      setLoadingContext(true);
      setError("");

      try {

        const response =
          await fetch(
            `${API_BASE_URL}/writing/projects/${selectedProjectId}/context`
          );

        const type =
          response.headers.get(
            "content-type"
          ) || "";

        const data =
          type.includes(
            "application/json"
          )
            ? await response.json()
            : {};

        if (!response.ok) {

          throw new Error(
            getError(
              data,
              "Could not load project research context."
            )
          );
        }

        if (!cancelled) {

          setProjectContext(data);
          setPapers(
            safeArray(
              data.all_literature || data.literature
            )
          );

        }

      } catch (err) {

        if (!cancelled) {

          setProjectContext(null);
          setPapers([]);

          setError(
            err.message ||
            "Could not load project research context."
          );
        }

      } finally {

        if (!cancelled) {
          setLoadingContext(false);
        }
      }
    }

    loadProjectContext();

    return () => {
      cancelled = true;
    };

  }, [selectedProjectId]);


  // ==========================================================
  // LOAD MANUSCRIPT
  // ==========================================================

  useEffect(() => {

    if (!selectedProjectId) {
      return;
    }

    let cancelled = false;

    async function loadManuscript() {

      setLoadingManuscript(true);
      setError("");
      setSuccess("");

      try {

        const response =
          await fetch(
            `${API_BASE_URL}/writing/projects/${selectedProjectId}/manuscript`
          );

        const type =
          response.headers.get(
            "content-type"
          ) || "";

        const data =
          type.includes(
            "application/json"
          )
            ? await response.json()
            : {};

        if (
          response.status === 404
        ) {

          if (!cancelled) {

            setManuscript({
              ...EMPTY_MANUSCRIPT,
              project_id:
                Number(
                  selectedProjectId
                ),
            });
          }

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

        if (!cancelled) {

          setManuscript({
            ...EMPTY_MANUSCRIPT,
            ...data,

            sections: {
              ...EMPTY_MANUSCRIPT.sections,
              ...safeObject(
                data.sections
              ),
            },
          });
        }

      } catch (err) {

        if (!cancelled) {

          setError(
            err.message ||
            "Could not load manuscript."
          );
        }

      } finally {

        if (!cancelled) {
          setLoadingManuscript(false);
        }
      }
    }

    loadManuscript();

    return () => {
      cancelled = true;
    };

  }, [selectedProjectId]);


  // ==========================================================
  // SAVE MANUSCRIPT
  // ==========================================================

  const saveManuscript =
    async () => {

      if (!selectedProjectId) {

        setError(
          "Select a research project first."
        );

        return;
      }

      setSaving(true);
      setError("");
      setSuccess("");

      try {

        const payload = {

          // Paper selection is intentionally not part of the
          // Writing workspace. The project is the source of truth.
          paper_id:
            manuscript.paper_id ?? null,

          title:
            manuscript.title ||
            "",

          abstract:
            manuscript.abstract ||
            "",

          keywords:
            safeArray(
              manuscript.keywords
            ),

          sections:
            safeObject(
              manuscript.sections
            ),

          status:
            manuscript.status ||
            "draft",

          change_summary:
            "Manual manuscript save.",
        };

        const exists =
          Boolean(
            manuscript.id
          );

        const url = exists
          ? `${API_BASE_URL}/writing/projects/${selectedProjectId}/manuscript`
          : `${API_BASE_URL}/writing/projects/${selectedProjectId}/manuscript`;

        const response =
          await fetch(
            url,
            {
              method:
                exists
                  ? "PUT"
                  : "POST",

              headers: {
                "Content-Type":
                  "application/json",
              },

              body:
                JSON.stringify(
                  payload
                ),
            }
          );

        const type =
          response.headers.get(
            "content-type"
          ) || "";

        const data =
          type.includes(
            "application/json"
          )
            ? await response.json()
            : {};

        if (!response.ok) {

          throw new Error(
            getError(
              data,
              "Could not save manuscript."
            )
          );
        }

        setManuscript({
          ...EMPTY_MANUSCRIPT,
          ...data,

          sections: {
            ...EMPTY_MANUSCRIPT.sections,
            ...safeObject(
              data.sections
            ),
          },
        });

        setSuccess(
          exists
            ? "Manuscript saved and new version created."
            : "Manuscript created successfully."
        );

        await loadVersions();

      } catch (err) {

        setError(
          err.message ||
          "Could not save manuscript."
        );

      } finally {

        setSaving(false);
      }
    };


  // ==========================================================
  // LOAD VERSIONS
  // ==========================================================

  const loadVersions =
    async () => {

      if (!selectedProjectId) {
        return;
      }

      setLoadingVersions(true);

      try {

        const response =
          await fetch(
            `${API_BASE_URL}/writing/projects/${selectedProjectId}/versions`
          );

        const type =
          response.headers.get(
            "content-type"
          ) || "";

        const data =
          type.includes(
            "application/json"
          )
            ? await response.json()
            : [];

        if (!response.ok) {

          throw new Error(
            getError(
              data,
              "Could not load versions."
            )
          );
        }

        setVersions(
          safeArray(data)
        );

      } catch (err) {

        setError(
          err.message ||
          "Could not load versions."
        );

      } finally {

        setLoadingVersions(false);
      }
    };


  // ==========================================================
  // READINESS
  // ==========================================================

  const loadReadiness =
    async () => {

      if (!selectedProjectId) {
        return;
      }

      setLoadingReadiness(true);

      try {

        const response =
          await fetch(
            `${API_BASE_URL}/writing/projects/${selectedProjectId}/readiness`
          );

        const type =
          response.headers.get(
            "content-type"
          ) || "";

        const data =
          type.includes(
            "application/json"
          )
            ? await response.json()
            : {};

        if (!response.ok) {

          throw new Error(
            getError(
              data,
              "Could not calculate readiness."
            )
          );
        }

        setReadiness(
          data
        );

      } catch (err) {

        setError(
          err.message ||
          "Could not calculate readiness."
        );

      } finally {

        setLoadingReadiness(false);
      }
    };


  // ==========================================================
  // VERSION RESTORE
  // ==========================================================

  const restoreVersion =
    async (versionId) => {

      if (!selectedProjectId) {
        return;
      }

      setError("");
      setSuccess("");

      try {

        const response =
          await fetch(
            `${API_BASE_URL}/writing/projects/${selectedProjectId}/versions/${versionId}/restore`,
            {
              method:
                "POST",
            }
          );

        const type =
          response.headers.get(
            "content-type"
          ) || "";

        const data =
          type.includes(
            "application/json"
          )
            ? await response.json()
            : {};

        if (!response.ok) {

          throw new Error(
            getError(
              data,
              "Could not restore version."
            )
          );
        }

        setManuscript({
          ...EMPTY_MANUSCRIPT,
          ...data,

          sections: {
            ...EMPTY_MANUSCRIPT.sections,
            ...safeObject(
              data.sections
            ),
          },
        });

        setSuccess(
          "Version restored successfully."
        );

        await loadVersions();

      } catch (err) {

        setError(
          err.message ||
          "Could not restore version."
        );
      }
    };


  // ==========================================================
  // AI ASSIST
  // ==========================================================

  const assistWriting =
    async () => {

      const content =
        manuscript.sections?.[
          activeSection
        ] || "";

      if (!content.trim()) {

        setError(
          "Write some content in this section first."
        );

        return;
      }

      setAiLoading(true);
      setError("");
      setSuccess("");

      try {

        const response =
          await fetch(
            `${API_BASE_URL}/writing/projects/${selectedProjectId}/sections/${activeSection}/assist`,
            {
              method:
                "POST",

              headers: {
                "Content-Type":
                  "application/json",
              },

              body:
                JSON.stringify({
                  instruction:
                    "Improve the academic clarity, logical flow, precision and scholarly style without inventing research facts, results, citations or numerical values.",

                  section_name:
                    activeSection,

                  content,

                  mode:
                    "improve",
                }),
            }
          );

        const type =
          response.headers.get(
            "content-type"
          ) || "";

        const data =
          type.includes(
            "application/json"
          )
            ? await response.json()
            : {};

        if (!response.ok) {

          throw new Error(
            getError(
              data,
              "AI writing assistance failed."
            )
          );
        }

        if (
          data.success &&
          typeof data.improved_text ===
            "string"
        ) {

          updateSection(
            activeSection,
            data.improved_text
          );

          setSuccess(
            "AI improvement generated. Review it before saving."
          );

        } else {

          setError(
            data.evidence_note ||
            "AI analysis is temporarily unavailable."
          );
        }

      } catch (err) {

        setError(
          err.message ||
          "AI analysis is temporarily unavailable."
        );

      } finally {

        setAiLoading(false);
      }
    };


  // ==========================================================
  // PROJECT-AWARE AI DRAFT GENERATION
  // ==========================================================

  const generateDraft = async (sectionOverride = null) => {
    const sectionName = sectionOverride || activeSection;

    if (!selectedProjectId) {
      setError("Select a research project first.");
      return "";
    }

    setAiLoading(true);
    setError("");
    setSuccess("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/writing/projects/${selectedProjectId}/sections/${sectionName}/generate`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            instruction:
              `Write the ${SECTION_LABELS[sectionName] || sectionName} section as a publication-ready academic section for this exact research project. Use the project's stored title, description, field and project-scoped literature. Be specific to the project. Do not invent citations, DOI, datasets, sample sizes, results, metrics, statistics or completed experiments. For objectives/questions, clearly label proposed items when they are not stored facts. Return only the manuscript section text.`,
          }),
        }
      );

      const type = response.headers.get("content-type") || "";
      const data = type.includes("application/json") ? await response.json() : {};

      if (!response.ok) {
        throw new Error(getError(data, `Generation failed for ${SECTION_LABELS[sectionName] || sectionName}.`));
      }

      const draft = typeof data.draft === "string" ? data.draft.trim() : "";
      if (!draft) throw new Error("Backend returned an empty draft.");

      updateSection(sectionName, draft);
      return draft;
    } catch (err) {
      // Last-resort UI fallback: never leave the editor blank when the backend
      // is temporarily unavailable. This is explicitly a scaffold, not a claim
      // of research evidence.
      const projectTitle = selectedProject?.title || "this research project";
      const description = projectSelectedDescription(projectContext);
      let fallback = "";
      if (sectionName === "introduction") {
        fallback = `${projectTitle} addresses the research direction defined by the project context. ${description || "The project requires a systematic investigation of the stated research problem."} The available research literature should be used to establish the background, identify limitations, and position the proposed study. The present manuscript should distinguish documented evidence from proposed research decisions and should not report experimental outcomes until they have been measured and recorded.`;
      } else if (sectionName === "problem_statement") {
        fallback = `The problem addressed by ${projectTitle} is defined by the project context as follows: ${description || "A specific research problem is recorded for this project."} The problem requires systematic investigation and evidence-based evaluation. Any quantitative performance claim, dataset detail, or experimental result should be added only after it is explicitly validated and stored.`;
      } else if (sectionName === "research_objectives") {
        fallback = `Proposed research objectives:\n1. Clearly define the scope and research problem of ${projectTitle}.\n2. Review relevant project-scoped literature and identify documented limitations.\n3. Develop a reproducible methodology appropriate to the research problem.\n4. Evaluate the proposed approach using predefined and reproducible criteria.\n5. Document limitations and evidence-supported future directions.`;
      } else if (sectionName === "research_questions") {
        fallback = `Proposed research questions:\n1. What are the principal challenges associated with ${projectTitle}?\n2. What approaches have been reported in the project-scoped literature?\n3. What limitations or unresolved issues are supported by the available evidence?\n4. How can a reproducible research approach address the identified problem?`;
      } else if (sectionName === "research_gap") {
        fallback = `The current project record does not by itself prove a novel research gap. The saved literature should be compared for repeated limitations, unresolved problems, methodological differences, and missing evaluation evidence. Any final research gap should be stated only when supported by multiple relevant sources.`;
      } else if (sectionName === "results") {
        fallback = "Experimental results are not yet available in the stored project evidence. Add this section only after validated experiments have been completed and measured results have been recorded.";
      } else {
        fallback = `${SECTION_LABELS[sectionName] || sectionName} for ${projectTitle}. This section should be completed using the project's stored evidence and validated research decisions. Unsupported facts, citations, datasets, numerical values, and experimental results must not be introduced.`;
      }
      updateSection(sectionName, fallback);
      setError(`AI generation was unavailable, so an evidence-safe draft scaffold was inserted. ${err.message || ""}`.trim());
      return fallback;
    } finally {
      setAiLoading(false);
    }
  };

  const projectSelectedDescription = (context) => {
    return context?.project?.description || selectedProject?.description || "";
  };

  const generateFullManuscript = async () => {
    if (!selectedProjectId) {
      setError("Select a research project first.");
      return;
    }

    setFullGenerationLoading(true);
    setError("");
    setSuccess("");

    try {
      // Metadata first.
      await generateMetadata();

      const generationOrder = [
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

      for (const sectionName of generationOrder) {
        await generateDraft(sectionName);
      }

      setSuccess("Manuscript content generated section-by-section from the selected research project. Review every section before saving.");
    } catch (err) {
      setError(err.message || "Could not generate the manuscript.");
    } finally {
      setFullGenerationLoading(false);
    }
  };

  // ==========================================================
  // INITIAL VERSION LOAD
  // ==========================================================

  useEffect(() => {

    if (
      selectedProjectId &&
      manuscript.id
    ) {

      loadVersions();
      loadReadiness();
    }

  }, [
    selectedProjectId,
    manuscript.id,
  ]);


  // ==========================================================
  // UPDATE SECTION
  // ==========================================================

  const updateSection =
    (
      sectionName,
      value
    ) => {

      setManuscript(
        (current) => ({
          ...current,

          sections: {
            ...current.sections,

            [sectionName]:
              value,
          },
        })
      );
    };


  const updateField =
    (
      field,
      value
    ) => {

      setManuscript(
        (current) => ({
          ...current,
          [field]: value,
        })
      );
    };


  const selectedProject =
    useMemo(
      () =>
        projects.find(
          (project) =>
            String(
              project.id
            ) ===
            String(
              selectedProjectId
            )
        ),

      [
        projects,
        selectedProjectId,
      ]
    );


  const currentText =
    manuscript.sections?.[
      activeSection
    ] || "";


  const currentWordCount =
    wordCount(
      currentText
    );


  const liveManuscriptWordCount =
    wordCount(
      [
        manuscript.title || "",
        manuscript.abstract || "",
        ...Object.values(
          manuscript.sections || {}
        ),
      ].join(" ")
    );


  return (
    <div className="wm-page">

      <style>{`

        .wm-page{
          color:#102b45;
          max-width:1500px;
          margin:0 auto;
          padding-bottom:44px;
        }

        .wm-hero{
          border:1px solid #dfe8ee;
          border-radius:25px;
          padding:31px 34px;
          background:
            linear-gradient(
              135deg,
              #f9fffd,
              #fff 58%,
              #f4f8ff
            );
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
          font-size:clamp(30px,4vw,45px);
          line-height:1.06;
          letter-spacing:-.04em;
          margin:10px 0;
        }

        .wm-hero p{
          max-width:760px;
          color:#718296;
          line-height:1.65;
          font-size:14px;
        }

        .wm-toolbar{
          display:grid;
          grid-template-columns:
            1fr 1fr;
          gap:12px;
          margin-top:22px;
        }

        .wm-toolbar-single{
          grid-template-columns:minmax(0,1fr);
        }

        .wm-control{
          background:#fff;
          border:1px solid #dfe7ed;
          border-radius:13px;
          padding:12px;
        }

        .wm-control label{
          display:block;
          font-size:9px;
          font-weight:850;
          letter-spacing:.1em;
          color:#7d8b99;
          margin-bottom:7px;
        }

        .wm-control select{
          width:100%;
          border:0;
          outline:none;
          font:inherit;
          color:#30465b;
          background:#fff;
        }

        .wm-actions{
          display:flex;
          gap:9px;
          flex-wrap:wrap;
          margin-top:15px;
        }

        .wm-btn{
          border:0;
          border-radius:11px;
          padding:12px 16px;
          background:#123d55;
          color:#fff;
          font-weight:800;
          display:inline-flex;
          gap:8px;
          align-items:center;
          cursor:pointer;
        }

        .wm-btn.secondary{
          background:#fff;
          color:#3c556c;
          border:1px solid #dce5eb;
        }

        .wm-btn.ai{
          background:#15906a;
        }

        .wm-btn:disabled{
          opacity:.6;
          cursor:wait;
        }

        .wm-message{
          margin-top:14px;
          border-radius:12px;
          padding:12px 14px;
          font-size:12px;
          line-height:1.5;
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

        .wm-layout{
          display:grid;
          grid-template-columns:
            250px minmax(0,1fr);
          gap:15px;
          margin-top:16px;
        }

        .wm-sidebar,
        .wm-card{
          background:#fff;
          border:1px solid #e1e8ed;
          border-radius:18px;
          box-shadow:
            0 7px 24px
            rgba(16,43,69,.035);
        }

        .wm-sidebar{
          padding:10px;
          align-self:start;
          position:sticky;
          top:10px;
        }

        .wm-section-btn{
          width:100%;
          text-align:left;
          border:0;
          background:transparent;
          padding:10px;
          border-radius:9px;
          color:#687b8d;
          cursor:pointer;
          font-size:12px;
        }

        .wm-section-btn.active{
          background:#eaf7f2;
          color:#137353;
          font-weight:800;
        }

        .wm-card{
          padding:19px;
        }

        .wm-editor-header{
          display:flex;
          justify-content:space-between;
          gap:12px;
          align-items:flex-start;
          flex-wrap:wrap;
        }

        .wm-editor-header h2{
          margin:3px 0;
          font-size:20px;
        }

        .wm-label{
          font-size:9px;
          letter-spacing:.12em;
          color:#8795a3;
          font-weight:850;
        }

        .wm-editor{
          width:100%;
          min-height:430px;
          resize:vertical;
          margin-top:15px;
          box-sizing:border-box;
          border:1px solid #dfe6eb;
          border-radius:13px;
          padding:16px;
          outline:none;
          font:14px/1.8 Arial,sans-serif;
          color:#30465b;
        }

        .wm-editor:focus{
          border-color:#78bfa4;
          box-shadow:
            0 0 0 3px
            rgba(21,144,106,.08);
        }

        .wm-editor-footer{
          display:flex;
          justify-content:space-between;
          gap:10px;
          color:#8493a1;
          font-size:11px;
          margin-top:9px;
        }

        .wm-stats{
          display:grid;
          grid-template-columns:
            repeat(4,1fr);
          gap:12px;
          margin-top:15px;
        }

        .wm-stat{
          background:#fff;
          border:1px solid #e1e8ed;
          border-radius:15px;
          padding:15px;
        }

        .wm-stat span{
          font-size:9px;
          letter-spacing:.12em;
          color:#8996a3;
          font-weight:850;
        }

        .wm-stat strong{
          font-size:25px;
          display:block;
          margin-top:7px;
        }

        .wm-readiness{
          margin-top:15px;
          padding:18px;
        }

        .wm-progress{
          height:8px;
          background:#e8efec;
          border-radius:99px;
          overflow:hidden;
          margin-top:12px;
        }

        .wm-progress > div{
          height:100%;
          background:#15906a;
        }

        .wm-version{
          display:flex;
          justify-content:space-between;
          gap:10px;
          padding:12px;
          border-bottom:1px solid #eef1f3;
          font-size:12px;
        }

        .wm-version:last-child{
          border-bottom:0;
        }

        .wm-empty{
          text-align:center;
          padding:35px;
          color:#7b8998;
          border:1px dashed #dce4e9;
          border-radius:13px;
        }

        @media(max-width:900px){
          .wm-layout{
            grid-template-columns:1fr;
          }

          .wm-sidebar{
            position:static;
          }

          .wm-stats{
            grid-template-columns:1fr 1fr;
          }
        }

        @media(max-width:620px){
          .wm-toolbar,
          .wm-stats{
            grid-template-columns:1fr;
          }
        }

      `}</style>


      {/* ====================================================
          HERO
      ==================================================== */}

      <section className="wm-hero">

        <div className="wm-kicker">
          <PenLine size={14}/>
          RESEARCH WRITING
        </div>

        <h1>
          Build a publication-ready manuscript.
        </h1>

        <p>
          Write, save, version and improve the
          manuscript using the same research
          project context used by the other modules.
        </p>


        <div
          className="wm-toolbar wm-toolbar-single"
          style={{
            alignItems: "flex-end",
          }}
        >

          <div
            className="wm-control"
            style={{ flex: 1 }}
          >

            <label>
              RESEARCH PROJECT
            </label>

            <select
              value={selectedProjectId}
              onChange={(event) => {

                const nextProjectId =
                  event.target.value;

                setSelectedProjectId(nextProjectId);

                setProjectContext(null);
                setPapers([]);

                setManuscript({
                  ...EMPTY_MANUSCRIPT,
                  project_id:
                    nextProjectId
                      ? Number(nextProjectId)
                      : null,
                });

                setReadiness(null);
                setVersions([]);
                setShowVersions(false);
                setError("");
                setSuccess("");

              }}
              disabled={loadingProjects}
            >

              <option value="">
                {loadingProjects
                  ? "Loading projects..."
                  : "Select research project"}
              </option>

              {projects.map((project) => (

                <option
                  key={project.id}
                  value={project.id}
                >
                  {project.title} · Project #{project.id}
                </option>

              ))}

            </select>

          </div>

          <button
            type="button"
            className="wm-btn secondary"
            onClick={() => {
              setShowNewProject(true);
              setError("");
              setSuccess("");
            }}
            style={{
              minWidth: 210,
              marginBottom: 0,
            }}
          >
            <Plus size={16}/>
            New Research Project
          </button>

          <button
            type="button"
            className="wm-btn primary"
            onClick={generateFullManuscript}
            disabled={fullGenerationLoading || !selectedProjectId}
            style={{ minWidth: 230, marginBottom: 0 }}
          >
            {fullGenerationLoading ? <Loader2 size={16} className="spin" /> : <WandSparkles size={16} />}
            {fullGenerationLoading ? "Generating Manuscript…" : "Generate Full Manuscript"}
          </button>

        </div>


              <div
          className="wm-card"
          style={{
            marginTop:12,
            padding:"16px 18px",
            background:"#fbfefd",
          }}
        >

          <div
            style={{
              display:"flex",
              justifyContent:"space-between",
              gap:16,
              flexWrap:"wrap",
              alignItems:"flex-start",
            }}
          >

            <div style={{minWidth:260,flex:"1 1 420px"}}>

              <div className="wm-label">
                PROJECT EVIDENCE
              </div>

              <strong
                style={{
                  display:"block",
                  marginTop:6,
                  fontSize:16,
                  color:"#23445c",
                }}
              >
                {selectedProject
                  ? selectedProject.title
                  : "Select a research project"}
              </strong>

              <div
                style={{
                  marginTop:6,
                  fontSize:12,
                  lineHeight:1.55,
                  color:"#718296",
                }}
              >
                {selectedProject?.research_field
                  ? selectedProject.research_field
                  : "Research field not stored"}
                {" · "}
                Project #{selectedProject?.id || "—"}
              </div>

              <p
                style={{
                  margin:"9px 0 0",
                  fontSize:12,
                  lineHeight:1.6,
                  color:"#64788a",
                }}
              >
                {selectedProject?.description ||
                  "No project description is stored yet. Missing research facts will not be invented."}
              </p>

            </div>


            <div
              style={{
                display:"grid",
                gridTemplateColumns:"repeat(3,minmax(100px,1fr))",
                gap:8,
                minWidth:330,
              }}
            >

              <div style={{
                padding:"11px 12px",
                border:"1px solid #e1ebe6",
                borderRadius:11,
                background:"#fff",
              }}>
                <div className="wm-label">
                  SAVED PAPERS
                </div>
                <strong style={{display:"block",marginTop:5,fontSize:20}}>
                  {projectContext?.literature_count ?? papers.length}
                </strong>
              </div>

              <div style={{
                padding:"11px 12px",
                border:"1px solid #e1ebe6",
                borderRadius:11,
                background:"#fff",
              }}>
                <div className="wm-label">
                  USED AS CONTEXT
                </div>
                <strong style={{display:"block",marginTop:5,fontSize:20}}>
                  {projectContext?.context_literature_count ?? 0}
                </strong>
              </div>

              <div style={{
                padding:"11px 12px",
                border:"1px solid #e1ebe6",
                borderRadius:11,
                background:"#fff",
              }}>
                <div className="wm-label">
                  ANALYSED PAPERS
                </div>
                <strong style={{display:"block",marginTop:5,fontSize:20}}>
                  {projectContext?.analysed_paper_count ?? 0}
                </strong>
              </div>

            </div>

          </div>


          <div
            style={{
              marginTop:14,
              paddingTop:13,
              borderTop:"1px solid #e7efeb",
            }}
          >

            <div
              style={{
                display:"flex",
                justifyContent:"space-between",
                gap:10,
                alignItems:"center",
                flexWrap:"wrap",
              }}
            >

              <div className="wm-label">
                RELEVANT PROJECT LITERATURE
              </div>

              {loadingContext && (
                <span
                  style={{
                    display:"inline-flex",
                    alignItems:"center",
                    gap:6,
                    color:"#728394",
                    fontSize:11,
                  }}
                >
                  <Loader2 size={13} className="spin"/>
                  Loading evidence...
                </span>
              )}

            </div>


            {!loadingContext && papers.length === 0 ? (

              <div
                style={{
                  marginTop:9,
                  padding:"11px 12px",
                  border:"1px dashed #d8e4df",
                  borderRadius:10,
                  color:"#718296",
                  fontSize:12,
                  lineHeight:1.55,
                }}
              >
                No papers are saved under this project yet. Use the
                <strong> Find Papers for This Project </strong> search below
                to retrieve academic papers and save them directly here.
              </div>

            ) : (

              <div
                style={{
                  display:"grid",
                  gap:7,
                  marginTop:9,
                }}
              >

                {papers.map(
                  (paper) => {

                    const analysedIds =
                      safeArray(
                        projectContext?.analysed_paper_ids
                      );

                    const analysed =
                      Boolean(paper.analysed) ||
                      analysedIds.includes(
                        paper.paper_id
                      );

                    return (
                      <div
                        key={paper.paper_id}
                        style={{
                          display:"flex",
                          justifyContent:"space-between",
                          gap:10,
                          alignItems:"center",
                          padding:"9px 11px",
                          border:"1px solid #e6ecef",
                          borderRadius:10,
                          background:"#fff",
                        }}
                      >

                        <div
                          style={{
                            minWidth:0,
                            flex:1,
                          }}
                        >
                          <div
                            style={{
                              fontSize:12,
                              fontWeight:750,
                              color:"#30465b",
                              whiteSpace:"nowrap",
                              overflow:"hidden",
                              textOverflow:"ellipsis",
                            }}
                            title={paper.title || ""}
                          >
                            {paper.title || "Untitled paper"}
                          </div>

                          <div
                            style={{
                              marginTop:3,
                              color:"#8996a3",
                              fontSize:10,
                            }}
                          >
                            {paper.year || "Year unavailable"}
                            {" · "}
                            {paper.relevance_signal || "Project literature"}
                          </div>

                        </div>

                        <span
                          style={{
                            flexShrink:0,
                            fontSize:10,
                            fontWeight:750,
                            padding:"5px 7px",
                            borderRadius:999,
                            background: analysed
                              ? "#eaf7f2"
                              : "#f3f6f8",
                            color: analysed
                              ? "#137353"
                              : "#718296",
                          }}
                        >
                          {analysed
                            ? "Analysed"
                            : "Metadata"}
                        </span>

                      </div>
                    );

                  }
                )}


              </div>

            )}

            <div
              style={{
                marginTop:14,
                paddingTop:14,
                borderTop:"1px solid #e7efeb",
              }}
            >
              <div className="wm-label">FIND PAPERS FOR THIS PROJECT</div>
              <div
                style={{
                  display:"flex",
                  gap:8,
                  marginTop:8,
                  flexWrap:"wrap",
                }}
              >
                <input
                  value={paperSearchQuery}
                  onChange={(event) => setPaperSearchQuery(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") searchProjectPapers();
                  }}
                  placeholder={
                    selectedProject?.title ||
                    "Search topic, keyword, DOI, or paper title"
                  }
                  style={{
                    flex:"1 1 360px",
                    minWidth:0,
                    padding:"11px 12px",
                    border:"1px solid #dce7e3",
                    borderRadius:10,
                    font:"inherit",
                    outline:"none",
                  }}
                />
                <button
                  type="button"
                  className="wm-btn secondary"
                  onClick={searchProjectPapers}
                  disabled={paperSearchLoading || !selectedProjectId}
                >
                  {paperSearchLoading ? (
                    <Loader2 size={15} className="spin" />
                  ) : (
                    <Search size={15} />
                  )}
                  Search Papers
                </button>
              </div>

              {paperSearchResults.length > 0 && (
                <div
                  style={{
                    display:"grid",
                    gap:7,
                    marginTop:10,
                  }}
                >
                  {paperSearchResults.map((paper) => (
                    <div
                      key={paper.paper_id || paper.title}
                      style={{
                        display:"flex",
                        gap:10,
                        justifyContent:"space-between",
                        alignItems:"center",
                        padding:"10px 11px",
                        border:"1px solid #e3ebe8",
                        borderRadius:10,
                        background:"#fff",
                      }}
                    >
                      <div style={{minWidth:0,flex:1}}>
                        <div
                          style={{
                            fontSize:12,
                            fontWeight:750,
                            color:"#30465b",
                            lineHeight:1.4,
                          }}
                        >
                          {paper.title || "Untitled paper"}
                        </div>
                        <div
                          style={{
                            marginTop:3,
                            color:"#8795a3",
                            fontSize:10,
                          }}
                        >
                          {paper.year || "Year unavailable"}
                          {paper.doi ? ` · DOI: ${paper.doi}` : ""}
                        </div>
                      </div>

                      <div style={{display:"flex",gap:6,flexShrink:0}}>
                        {paper.url && (
                          <a
                            href={paper.url}
                            target="_blank"
                            rel="noreferrer"
                            className="wm-btn secondary"
                            style={{textDecoration:"none",padding:"8px 10px"}}
                            title="Open paper"
                          >
                            <ExternalLink size={14}/>
                          </a>
                        )}
                        <button
                          type="button"
                          className="wm-btn"
                          onClick={() => saveProjectPaper(paper)}
                          disabled={paperSaveId === paper.paper_id || paper.saved}
                          style={{padding:"8px 12px"}}
                        >
                          {paperSaveId === paper.paper_id ? (
                            <Loader2 size={14} className="spin"/>
                          ) : (
                            <Plus size={14}/>
                          )}
                          {paper.saved ? "Saved" : "Save to Project"}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {projectContext?.evidence_note && (
              <div
                style={{
                  marginTop:9,
                  fontSize:10,
                  lineHeight:1.5,
                  color:"#8996a3",
                }}
              >
                {projectContext.evidence_note}
              </div>
            )}

          </div>

        </div>


        <div className="wm-actions">

          <button
            className="wm-btn"
            onClick={saveManuscript}
            disabled={
              saving ||
              loadingManuscript ||
              !selectedProjectId
            }
          >

            {saving
              ? <Loader2
                  size={16}
                  className="spin"
                />
              : <Save size={16}/>}

            {saving
              ? "Saving..."
              : manuscript.id
                ? "Save Manuscript"
                : "Create Manuscript"}

          </button>


          <button
            className="wm-btn secondary"
            onClick={
              loadReadiness
            }
            disabled={
              loadingReadiness ||
              !manuscript.id
            }
          >

            {loadingReadiness
              ? <Loader2 size={16}/>
              : <Target size={16}/>}

            Readiness

          </button>


          <button
            className="wm-btn secondary"
            onClick={() =>
              setShowVersions(
                (value) => !value
              )
            }
            disabled={
              !manuscript.id
            }
          >

            <History size={16}/>

            Version History

          </button>

        </div>

      </section>


      {/* ====================================================
          NEW RESEARCH PROJECT MODAL
      ==================================================== */}

      {showNewProject && (

        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 1000,
            background: "rgba(15, 23, 42, 0.42)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 20,
          }}
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setShowNewProject(false);
            }
          }}
        >

          <div
            style={{
              width: "min(720px, 100%)",
              maxHeight: "90vh",
              overflowY: "auto",
              background: "#ffffff",
              borderRadius: 20,
              padding: 24,
              boxShadow: "0 24px 80px rgba(15,23,42,.22)",
              border: "1px solid #e4eaf0",
            }}
          >

            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                gap: 16,
                marginBottom: 20,
              }}
            >

              <div>
                <div className="wm-kicker">
                  <Sparkles size={14}/>
                  NEW RESEARCH WORKSPACE
                </div>

                <h2
                  style={{
                    margin: "6px 0 6px",
                    fontSize: 26,
                  }}
                >
                  Start a new research topic
                </h2>

                <p
                  style={{
                    margin: 0,
                    color: "#718096",
                    lineHeight: 1.6,
                  }}
                >
                  Create a project first. Then use Discovery,
                  Literature and Writing with the same project context.
                </p>
              </div>

              <button
                type="button"
                onClick={() => setShowNewProject(false)}
                style={{
                  border: "1px solid #dbe4ec",
                  background: "#fff",
                  borderRadius: 10,
                  width: 38,
                  height: 38,
                  display: "grid",
                  placeItems: "center",
                  cursor: "pointer",
                }}
              >
                <X size={18}/>
              </button>

            </div>


            <div
              style={{
                display: "grid",
                gap: 14,
              }}
            >

              <div className="wm-control">
                <label>
                  RESEARCH TOPIC *
                </label>

                <input
                  value={newProject.topic}
                  onChange={(event) =>
                    setNewProject((current) => ({
                      ...current,
                      topic: event.target.value,
                    }))
                  }
                  placeholder="e.g. AI-Based Early Detection of Crop Diseases Using Drone Images"
                  autoFocus
                />
              </div>


              <div className="wm-control">
                <label>
                  RESEARCH FIELD / DOMAIN
                </label>

                <input
                  value={newProject.field}
                  onChange={(event) =>
                    setNewProject((current) => ({
                      ...current,
                      field: event.target.value,
                    }))
                  }
                  placeholder="e.g. Computer Vision, AI, Healthcare"
                />
              </div>


              <div className="wm-control">
                <label>
                  RESEARCH PROBLEM
                </label>

                <textarea
                  value={newProject.problem}
                  onChange={(event) =>
                    setNewProject((current) => ({
                      ...current,
                      problem: event.target.value,
                    }))
                  }
                  placeholder="What problem do you want to investigate?"
                  rows={3}
                  style={{
                    width: "100%",
                    boxSizing: "border-box",
                    resize: "vertical",
                  }}
                />
              </div>


              <div className="wm-control">
                <label>
                  RESEARCH OBJECTIVES
                </label>

                <textarea
                  value={newProject.objectives}
                  onChange={(event) =>
                    setNewProject((current) => ({
                      ...current,
                      objectives: event.target.value,
                    }))
                  }
                  placeholder="Optional. Add known objectives, one per line."
                  rows={3}
                  style={{
                    width: "100%",
                    boxSizing: "border-box",
                    resize: "vertical",
                  }}
                />
              </div>


              <div className="wm-control">
                <label>
                  KEYWORDS
                </label>

                <input
                  value={newProject.keywords}
                  onChange={(event) =>
                    setNewProject((current) => ({
                      ...current,
                      keywords: event.target.value,
                    }))
                  }
                  placeholder="e.g. YOLO, crop disease, drone imagery, CNN"
                />
              </div>

            </div>


            <div
              style={{
                marginTop: 20,
                padding: 14,
                borderRadius: 12,
                background: "#f5faf8",
                border: "1px solid #d9eee7",
                color: "#315c50",
                fontSize: 13,
                lineHeight: 1.55,
              }}
            >
              After creation, the new project becomes active automatically.
              Save papers from the Literature module under this project,
              then return here to generate the manuscript from its evidence.
            </div>


            <div
              style={{
                display: "flex",
                justifyContent: "flex-end",
                gap: 10,
                marginTop: 20,
              }}
            >

              <button
                type="button"
                className="wm-btn secondary"
                onClick={() => setShowNewProject(false)}
                disabled={creatingProject}
              >
                Cancel
              </button>

              <button
                type="button"
                className="wm-btn"
                onClick={createNewResearchProject}
                disabled={
                  creatingProject ||
                  !newProject.topic.trim()
                }
              >
                {creatingProject
                  ? <Loader2 size={16} className="spin"/>
                  : <Plus size={16}/>}
                {creatingProject
                  ? "Creating..."
                  : "Create Research Project"}
              </button>

            </div>

          </div>

        </div>

      )}


      {/* ====================================================
          MESSAGES
      ==================================================== */}

      {error && (

        <div className="wm-message wm-error">

          <TriangleAlert
            size={16}
            style={{
              verticalAlign:
                "middle",
              marginRight:7,
            }}
          />

          {error}

        </div>

      )}


      {success && (

        <div className="wm-message wm-success">

          <CheckCircle2
            size={16}
            style={{
              verticalAlign:
                "middle",
              marginRight:7,
            }}
          />

          {success}

        </div>

      )}


      {/* ====================================================
          STATS
      ==================================================== */}

      <div className="wm-stats">

        <div className="wm-stat">
          <span>PROJECT</span>
          <strong>
            {selectedProject
              ? selectedProject.title
              : "—"}
          </strong>
        </div>

        <div className="wm-stat">
          <span>VERSION</span>
          <strong>
            {manuscript.current_version ||
              "—"}
          </strong>
        </div>

        <div className="wm-stat">
          <span>WORDS</span>
          <strong>
            {liveManuscriptWordCount}
          </strong>
        </div>

        <div className="wm-stat">
          <span>STATUS</span>
          <strong
            style={{
              fontSize:18,
            }}
          >
            {manuscript.status ||
              "draft"}
          </strong>
        </div>

      </div>


      {/* ====================================================
          READINESS
      ==================================================== */}

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

              <h2
                style={{
                  margin:"5px 0",
                }}
              >
                Deterministic readiness check
              </h2>

            </div>

            <strong
              style={{
                fontSize:26,
              }}
            >
              {
                readiness.readiness_percentage
              }%
            </strong>

          </div>

          <div className="wm-progress">

            <div
              style={{
                width:
                  `${Math.min(
                    100,
                    Math.max(
                      0,
                      Number(
                        readiness.readiness_percentage
                      ) || 0
                    )
                  )}%`,
              }}
            />

          </div>

          <p
            style={{
              color:"#728394",
              fontSize:12,
            }}
          >
            {
              readiness.completed_checks
            } / {
              readiness.total_checks
            } deterministic checks completed.
          </p>

        </section>

      )}


      {/* ====================================================
          VERSION HISTORY
      ==================================================== */}

      {showVersions && (

        <section
          className="wm-card"
          style={{
            marginTop:15,
          }}
        >

          <div className="wm-label">
            VERSION HISTORY
          </div>

          <h2>
            Saved manuscript versions
          </h2>

          {loadingVersions ? (

            <div className="wm-empty">
              <Loader2
                size={24}
              />
              <br/>
              Loading versions...
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
                        Version {
                          version.version_number
                        }
                      </strong>

                      <div
                        style={{
                          color:"#8493a1",
                          marginTop:4,
                        }}
                      >
                        {
                          version.change_summary ||
                          "No change summary."
                        }
                      </div>

                    </div>

                    <button
                      className="wm-btn secondary"
                      onClick={() =>
                        restoreVersion(
                          version.id
                        )
                      }
                    >
                      <RotateCcw
                        size={14}
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


      {/* ====================================================
          MAIN EDITOR
      ==================================================== */}

      {!selectedProjectId ? (

        <div
          className="wm-card wm-empty"
          style={{
            marginTop:15,
          }}
        >

          <FileText
            size={30}
          />

          <h3>
            Select a research project
          </h3>

          <div>
            Your manuscript will remain
            connected to that project.
          </div>

        </div>

      ) : loadingManuscript ? (

        <div
          className="wm-card wm-empty"
          style={{
            marginTop:15,
          }}
        >

          <Loader2
            size={30}
          />

          <h3>
            Loading manuscript...
          </h3>

        </div>

      ) : (

        <div className="wm-layout">

          {/* SIDEBAR */}

          <aside className="wm-sidebar">

            <div
              className="wm-label"
              style={{
                padding:"8px",
                display:"block",
              }}
            >
              MANUSCRIPT SECTIONS
            </div>

            {Object.entries(
              SECTION_LABELS
            ).map(
              ([
                key,
                label,
              ]) => (

                <button
                  key={key}
                  className={
                    `wm-section-btn ${
                      activeSection === key
                        ? "active"
                        : ""
                    }`
                  }
                  onClick={() =>
                    setActiveSection(
                      key
                    )
                  }
                >
                  {label}
                </button>

              )
            )}

          </aside>


          {/* EDITOR */}

          <main>

            <section className="wm-card">

              <div
                className="wm-editor-header"
              >

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

                </div>


                <div
                  style={{
                    display:"flex",
                    gap:8,
                    flexWrap:"wrap",
                  }}
                >

                  <button
                    className="wm-btn ai"
                    onClick={
                      generateDraft
                    }
                    disabled={
                      aiLoading ||
                      !selectedProjectId
                    }
                  >

                    {aiLoading
                      ? <Loader2 size={15}/>
                      : <Sparkles size={15}/>}

                    {aiLoading
                      ? "Generating..."
                      : "Generate Draft"}

                  </button>


                  <button
                    className="wm-btn secondary"
                    onClick={
                      assistWriting
                    }
                    disabled={
                      aiLoading ||
                      !currentText.trim()
                    }
                  >

                    <Sparkles size={15}/>

                    Improve with AI

                  </button>

                </div>

              </div>


              <textarea
                className="wm-editor"
                value={
                  currentText
                }
                onChange={(event) =>
                  updateSection(
                    activeSection,
                    event.target.value
                  )
                }
                placeholder={
                  `Write the ${
                    SECTION_LABELS[
                      activeSection
                    ]
                  } section here...`
                }
              />


              <div
                className="wm-editor-footer"
              >

                <span>
                  {currentWordCount}
                  {" "}
                  words
                </span>

                <span>
                  {currentText.length}
                  {" "}
                  characters
                </span>

              </div>

            </section>


            {/* TITLE + ABSTRACT */}

            <section
              className="wm-card"
              style={{
                marginTop:15,
              }}
            >

              <div className="wm-label">
                MANUSCRIPT METADATA
              </div>

              <div
                style={{
                  display:"flex",
                  justifyContent:"space-between",
                  alignItems:"center",
                  gap:12,
                  flexWrap:"wrap",
                }}
              >
                <h2 style={{margin:0}}>
                  Title & Abstract
                </h2>

                <button
                  type="button"
                  className="wm-btn"
                  onClick={generateMetadata}
                  disabled={metadataLoading || !selectedProjectId}
                >
                  {metadataLoading ? (
                    <Loader2 size={15} className="spin"/>
                  ) : (
                    <WandSparkles size={15}/>
                  )}
                  Generate Title & Abstract
                </button>
              </div>

              <input
                value={
                  manuscript.title ||
                  ""
                }
                onChange={(event) =>
                  updateField(
                    "title",
                    event.target.value
                  )
                }
                placeholder="Research paper title"
                style={{
                  width:"100%",
                  boxSizing:"border-box",
                  padding:12,
                  border:"1px solid #dfe6eb",
                  borderRadius:10,
                  marginTop:10,
                  font:"inherit",
                }}
              />

              <textarea
                value={
                  manuscript.abstract ||
                  ""
                }
                onChange={(event) =>
                  updateField(
                    "abstract",
                    event.target.value
                  )
                }
                placeholder="Research abstract"
                style={{
                  width:"100%",
                  minHeight:150,
                  boxSizing:"border-box",
                  padding:12,
                  border:"1px solid #dfe6eb",
                  borderRadius:10,
                  marginTop:10,
                  font:"inherit",
                  resize:"vertical",
                }}
              />

            </section>

          </main>

        </div>

      )}

    </div>
  );
}


export default WritingPage;