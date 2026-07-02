"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import styles from "./page.module.css";

const BACKEND_URL = "http://127.0.0.1:8000";

// --- Beautiful SVG Icon Components ---
const SearchIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8"></circle>
    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
  </svg>
);

const TrashIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6"></polyline>
    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
    <line x1="10" y1="11" x2="10" y2="17"></line>
    <line x1="14" y1="11" x2="14" y2="17"></line>
  </svg>
);

const LogoIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="url(#logo-grad)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ filter: "drop-shadow(0 0 8px rgba(99, 102, 241, 0.45))" }}>
    <defs>
      <linearGradient id="logo-grad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#818cf8" />
        <stop offset="100%" stopColor="#4f46e5" />
      </linearGradient>
    </defs>
    <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
    <path d="M2 17l10 5 10-5"></path>
    <path d="M2 12l10 5 10-5"></path>
  </svg>
);

const LoaderIcon = () => (
  <svg className="spin" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="2" x2="12" y2="6"></line>
    <line x1="12" y1="18" x2="12" y2="22"></line>
    <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line>
    <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line>
    <line x1="2" y1="12" x2="6" y2="12"></line>
    <line x1="18" y1="12" x2="22" y2="12"></line>
    <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line>
    <line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line>
  </svg>
);

const AlertIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"></circle>
    <line x1="12" y1="8" x2="12" y2="12"></line>
    <line x1="12" y1="16" x2="12.01" y2="16"></line>
  </svg>
);

const FolderIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
  </svg>
);

export default function Home() {
  const router = useRouter();
  const [topic, setTopic] = useState("");
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [error, setError] = useState("");
  const [backendStatus, setBackendStatus] = useState("unknown"); // unknown | online | offline

  // 1. Check backend health
  const checkBackendHealth = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/health`, { signal: AbortSignal.timeout(3000) });
      if (res.ok) {
        setBackendStatus("online");
        return true;
      }
    } catch (e) {
      setBackendStatus("offline");
    }
    return false;
  };

  // 2. Fetch recent projects
  const fetchProjects = async () => {
    try {
      const isUp = await checkBackendHealth();
      if (!isUp) {
        setFetching(false);
        return;
      }
      const res = await fetch(`${BACKEND_URL}/api/v1/projects/`);
      if (res.ok) {
        const data = await res.json();
        setProjects(data);
      } else {
        setError("Failed to load projects list.");
      }
    } catch (err) {
      setError("Error communicating with backend.");
    } finally {
      setFetching(false);
    }
  };

  useEffect(() => {
    fetchProjects();
    const interval = setInterval(fetchProjects, 5000);
    return () => clearInterval(interval);
  }, []);

  // 3. Submit new research topic
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!topic.trim()) return;

    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/projects/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: topic.trim() }),
      });

      if (res.ok) {
        const project = await res.json();
        router.push(`/research/${project.id}`);
      } else {
        const errData = await res.json();
        setError(errData.detail || "Failed to create project.");
        setLoading(false);
      }
    } catch (err) {
      setError("Could not connect to backend server. Make sure it's running.");
      setLoading(false);
    }
  };

  // 4. Delete project
  const handleDelete = async (e, projectId) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this project?")) return;

    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/projects/${projectId}`, {
        method: "DELETE",
      });
      if (res.ok) {
        setProjects(projects.filter((p) => p.id !== projectId));
      } else {
        alert("Failed to delete project.");
      }
    } catch (err) {
      alert("Error connecting to backend to delete project.");
    }
  };

  const getStatusBadgeClass = (status) => {
    return `badge badge-${status.toLowerCase()}`;
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.logoGlow}>
          <LogoIcon />
          <span>ResearchMind AI</span>
        </div>
        <p className={styles.subtitle}>
          Autonomous multi-agent intelligence orchestrator. Scours search networks, validates literature, compiles findings, and structures presentation-ready decks.
        </p>
      </header>

      {backendStatus === "offline" && (
        <div className={styles.errorBanner} style={{ width: "100%", maxWidth: "700px", marginBottom: "24px" }}>
          <AlertIcon />
          <span><strong>Server Offline:</strong> Cannot reach the background agent API. Please ensure the backend is running.</span>
        </div>
      )}

      <main className={styles.mainContent}>
        {/* Input box */}
        <section className={`${styles.inputSection} glass`}>
          <h2 className={styles.sectionTitle}>Start New Research</h2>
          <p className={styles.descriptionText}>
            Provide a query, question, or research statement. A network of agents will map the topic, run searches, identify contradictions, and build a full report.
          </p>

          <form onSubmit={handleSubmit} className={styles.formGroup}>
            <label className={styles.inputLabel}>Research Scope</label>
            <div className={styles.inputWrapper}>
              <span className={styles.inputIcon}>
                <SearchIcon />
              </span>
              <input
                type="text"
                className={styles.textInput}
                placeholder="e.g., Deep learning applications in oncology diagnostics..."
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                disabled={loading || backendStatus === "offline"}
                required
              />
            </div>
            
            <div className={styles.featurePills}>
              <span className={styles.pill}>✓ Multi-Agent Critique</span>
              <span className={styles.pill}>✓ Tavily Web Integration</span>
              <span className={styles.pill}>✓ Contradiction Spotting</span>
              <span className={styles.pill}>✓ PPTX Generation</span>
            </div>

            {error && <div className={styles.errorBanner} style={{ marginTop: "12px" }}>{error}</div>}
            
            <button
              type="submit"
              className="btn-primary"
              style={{ marginTop: "16px", width: "100%" }}
              disabled={loading || !topic.trim() || backendStatus === "offline"}
            >
              {loading ? (
                <>
                  <LoaderIcon />
                  <span>Launching Agent Squad...</span>
                </>
              ) : (
                "Initialize Autonomous Agent"
              )}
            </button>
          </form>
        </section>

        {/* Recent projects */}
        <section className={`${styles.recentSection} glass`}>
          <h2 className={styles.sectionTitle}>Recent Research</h2>
          
          {fetching ? (
            <div className={styles.emptyState}>
              <div className="spin" style={{ color: "var(--text-muted)", display: "flex" }}>
                <LoaderIcon />
              </div>
              <p>Loading projects...</p>
            </div>
          ) : projects.length === 0 ? (
            <div className={styles.emptyState}>
              <div className={styles.emptyIcon}>
                <FolderIcon />
              </div>
              <p>No active projects found.</p>
            </div>
          ) : (
            <div className={styles.projectList}>
              {projects.map((project) => (
                <div
                  key={project.id}
                  className={styles.projectCard}
                  onClick={() => router.push(`/research/${project.id}`)}
                >
                  <div className={styles.projectInfo}>
                    <div className={styles.projectTopic} title={project.topic}>
                      {project.topic}
                    </div>
                    <div className={styles.projectMeta}>
                      <span className={getStatusBadgeClass(project.status)}>
                        {project.status}
                      </span>
                      <span>
                        {new Date(project.created_at).toLocaleDateString(undefined, {
                          month: "short",
                          day: "numeric",
                        })}
                      </span>
                    </div>
                  </div>
                  <button
                    className={styles.deleteBtn}
                    onClick={(e) => handleDelete(e, project.id)}
                    title="Delete Project"
                  >
                    <TrashIcon />
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
