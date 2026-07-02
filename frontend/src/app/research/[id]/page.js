"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter, useParams } from "next/navigation";
import styles from "./page.module.css";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
const WS_URL = BACKEND_URL.replace(/^http/, "ws");

// --- Beautiful SVG Icon Components ---
const ArrowLeftIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <line x1="19" y1="12" x2="5" y2="12"></line>
    <polyline points="12 19 5 12 12 5"></polyline>
  </svg>
);

const DownloadIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
    <polyline points="7 10 12 15 17 10"></polyline>
    <line x1="12" y1="15" x2="12" y2="3"></line>
  </svg>
);

const DocIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
    <polyline points="14 2 14 8 20 8"></polyline>
    <line x1="16" y1="13" x2="8" y2="13"></line>
    <line x1="16" y1="17" x2="8" y2="17"></line>
  </svg>
);

const BookIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
  </svg>
);

const WarningIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
    <line x1="12" y1="9" x2="12" y2="13"></line>
    <line x1="12" y1="17" x2="12.01" y2="17"></line>
  </svg>
);

const SearchIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8"></circle>
    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
  </svg>
);

const GraphIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="6" y1="3" x2="6" y2="15"></line>
    <circle cx="18" cy="6" r="3"></circle>
    <circle cx="6" cy="18" r="3"></circle>
    <path d="M18 9a9 9 0 0 1-9 9"></path>
  </svg>
);

const UploadIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
    <polyline points="17 8 12 3 7 8"></polyline>
    <line x1="12" y1="3" x2="12" y2="15"></line>
  </svg>
);

const StarIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="currentColor" style={{ color: "var(--warning)" }}>
    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
  </svg>
);

const LoaderIcon = () => (
  <svg className="spin" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
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

const CheckIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12"></polyline>
  </svg>
);

export default function ResearchDashboard() {
  const router = useRouter();
  const { id } = useParams();

  const [project, setProject] = useState(null);
  const [sources, setSources] = useState([]);
  const [contradictions, setContradictions] = useState([]);
  const [gaps, setGaps] = useState([]);
  const [report, setReport] = useState(null);
  
  const [activeTab, setActiveTab] = useState("report");
  const [timelineEvents, setTimelineEvents] = useState([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [wsError, setWsError] = useState("");

  // PDF Upload state
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadSuccess, setUploadSuccess] = useState("");
  const [uploadError, setUploadError] = useState("");

  const wsRef = useRef(null);
  const timelineEndRef = useRef(null);

  // 1. Fetch all project related data
  const fetchData = async () => {
    try {
      const projRes = await fetch(`${BACKEND_URL}/api/v1/projects/${id}`);
      if (projRes.ok) {
        const projData = await projRes.json();
        setProject(projData);
      }

      const srcRes = await fetch(`${BACKEND_URL}/api/v1/projects/${id}/sources`);
      if (srcRes.ok) {
        const srcData = await srcRes.json();
        setSources(srcData);
      }

      const conRes = await fetch(`${BACKEND_URL}/api/v1/projects/${id}/contradictions`);
      if (conRes.ok) {
        const conData = await conRes.json();
        setContradictions(conData);
      }

      const gapRes = await fetch(`${BACKEND_URL}/api/v1/projects/${id}/gaps`);
      if (gapRes.ok) {
        const gapData = await gapRes.json();
        setGaps(gapData);
      }

      const repRes = await fetch(`${BACKEND_URL}/api/v1/reports/${id}`);
      if (repRes.ok) {
        const repData = await repRes.json();
        setReport(repData);
      } else {
        setReport(null);
      }
    } catch (e) {
      console.warn("Error fetching project details:", e);
    }
  };

  // 2. Initialize WebSocket & Page Mount
  useEffect(() => {
    if (!id || id === "undefined" || id === "[id]") return;

    fetchData();

    let reconnectTimer = null;
    let ws = null;

    const connectWS = () => {
      const uri = `${WS_URL}/api/v1/ws/${id}`;
      console.log("[WS] Connecting to:", uri, "| ID type:", typeof id, "| ID value:", id);
      ws = new WebSocket(uri);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsConnected(true);
        setWsError("");
        console.log("[WS] Connected");
      };

      ws.onmessage = (event) => {
        if (event.data === "pong") return;
        try {
          const data = JSON.parse(event.data);
          setTimelineEvents((prev) => {
            const exists = prev.some(
              (e) => e.agent === data.agent && e.status === data.status && e.message === data.message
            );
            if (exists) return prev;
            return [...prev, { ...data, timestamp: new Date() }];
          });

          if (data.status === "completed" || data.status === "failed") {
            fetchData();
          }
        } catch (e) {
          console.warn("WS parse error:", e);
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        console.log("[WS] Closed. Retrying in 3s...");
        reconnectTimer = setTimeout(connectWS, 3000);
      };

      ws.onerror = (err) => {
        console.warn("[WS] Error details:", err);
        setWsError("Handshake failed or connection dropped. Retrying...");
      };
    };

    connectWS();

    return () => {
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.onerror = null;
        wsRef.current.close();
      }
    };
  }, [id]);

  // Keep WebSocket alive
  useEffect(() => {
    const pingInterval = setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send("ping");
      }
    }, 15000);
    return () => clearInterval(pingInterval);
  }, []);

  // Scroll timeline to bottom on new event
  useEffect(() => {
    if (timelineEndRef.current) {
      timelineEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [timelineEvents]);

  // 3. Handle PDF Upload
  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setUploadSuccess("");
      setUploadError("");
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!selectedFile) return;

    setUploading(true);
    setUploadProgress(20);
    setUploadError("");
    setUploadSuccess("");

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      setUploadProgress(50);
      const res = await fetch(`${BACKEND_URL}/api/v1/uploads/${id}`, {
        method: "POST",
        body: formData,
      });

      setUploadProgress(80);
      if (res.ok) {
        setUploadSuccess(`Indexed successfully: ${selectedFile.name}`);
        setSelectedFile(null);
        setUploadProgress(100);
        fetchData();
      } else {
        const data = await res.json();
        setUploadError(data.detail || "Upload failed.");
      }
    } catch (err) {
      setUploadError("Network error uploading document.");
    } finally {
      setUploading(false);
      setTimeout(() => setUploadProgress(0), 2000);
    }
  };

  // Simple Markdown Parser to HTML
  const parseMarkdown = (md) => {
    if (!md) return "";
    
    let text = md
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    text = text.replace(/^#\s+(.+)$/gm, "<h1>$1</h1>");
    text = text.replace(/^##\s+(.+)$/gm, "<h2>$1</h2>");
    text = text.replace(/^###\s+(.+)$/gm, "<h3>$1</h3>");
    text = text.replace(/^\-\-\-$/gm, "<hr />");
    text = text.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    text = text.replace(/\*(.+?)\*/g, "<em>$1</em>");
    text = text.replace(/^\-\s+(.+)$/gm, "<li>$1</li>");
    text = text.replace(/^\*\s+(.+)$/gm, "<li>$1</li>");
    
    text = text.split("\n\n").map(paragraph => {
      if (paragraph.trim().startsWith("<h") || paragraph.trim().startsWith("<hr") || paragraph.trim().startsWith("<li>")) {
        return paragraph;
      }
      return `<p>${paragraph.replace(/\n/g, "<br/>")}</p>`;
    }).join("\n");

    text = text.replace(/\[(\d+)\]/g, '<span class="citation-badge" style="background: rgba(99,102,241,0.12); color: #818cf8; border-radius: 4px; padding: 2px 6px; font-size: 0.75rem; font-weight: 700; margin: 0 2px; border: 1px solid rgba(99,102,241,0.25)">$1</span>');

    return text;
  };

  const getStatusBadgeClass = (status) => {
    return `badge badge-${status?.toLowerCase() || "pending"}`;
  };

  const getReliabilityColor = (score) => {
    if (score >= 0.8) return "#10b981"; // green
    if (score >= 0.5) return "#f59e0b"; // yellow
    return "#ef4444"; // red
  };

  if (!project) {
    return (
      <div className={styles.container} style={{ alignItems: "center", justifyContent: "center", minHeight: "80vh" }}>
        <LoaderIcon />
        <p style={{ marginTop: "12px", color: "var(--text-secondary)" }}>Loading workspace...</p>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {/* Top Bar */}
      <header className={styles.topBar}>
        <div className={styles.titleArea}>
          <a href="/" className={styles.backBtn}>
            <ArrowLeftIcon /> Back to Projects
          </a>
          <h1 className={styles.title}>{project.topic}</h1>
          <div className={styles.metaRow}>
            <span>Status: <span className={getStatusBadgeClass(project.status)}>{project.status}</span></span>
            {project.confidence_score && (
              <span className={styles.confidenceDisplay}>
                <CheckIcon /> Confidence Score: {(project.confidence_score * 100).toFixed(0)}%
              </span>
            )}
            <span>Created: {new Date(project.created_at).toLocaleDateString()}</span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className={styles.actionArea}>
          <a
            href={`${BACKEND_URL}/api/v1/reports/${id}/markdown`}
            target="_blank"
            download
            className="btn-secondary"
            style={{ pointerEvents: report ? "auto" : "none", opacity: report ? 1 : 0.5 }}
          >
            <DownloadIcon /> Report Markdown
          </a>
          <a
            href={`${BACKEND_URL}/api/v1/reports/${id}/pptx`}
            target="_blank"
            download
            className="btn-primary"
            style={{ pointerEvents: report ? "auto" : "none", opacity: report ? 1 : 0.5 }}
          >
            <DownloadIcon /> Download Deck
          </a>
        </div>
      </header>

      {/* Stats Cards */}
      <section className={styles.statsGrid}>
        <div className={`${styles.statCard} glass`}>
          <span className={styles.statVal}>{sources.length}</span>
          <span className={styles.statLabel}>Sources Indexed</span>
        </div>
        <div className={`${styles.statCard} glass`}>
          <span className={styles.statVal}>{contradictions.length}</span>
          <span className={styles.statLabel}>Contradictions</span>
        </div>
        <div className={`${styles.statCard} glass`}>
          <span className={styles.statVal}>{gaps.length}</span>
          <span className={styles.statLabel}>Research Gaps</span>
        </div>
        <div className={`${styles.statCard} glass`}>
          <span className={styles.statVal}>
            {project.confidence_score ? `${(project.confidence_score * 100).toFixed(0)}%` : "N/A"}
          </span>
          <span className={styles.statLabel}>Confidence Score</span>
        </div>
      </section>

      {/* Main Grid */}
      <div className={styles.dashboardLayout}>
        
        {/* Left Column - Tabs and Workspace */}
        <main className={`${styles.mainPanel} glass`}>
          <nav className={styles.tabsContainer}>
            <button
              className={`${styles.tab} ${activeTab === "report" ? styles.activeTab : ""}`}
              onClick={() => setActiveTab("report")}
            >
              <DocIcon /> Research Report
            </button>
            <button
              className={`${styles.tab} ${activeTab === "sources" ? styles.activeTab : ""}`}
              onClick={() => setActiveTab("sources")}
            >
              <BookIcon /> Sources ({sources.length})
            </button>
            <button
              className={`${styles.tab} ${activeTab === "contradictions" ? styles.activeTab : ""}`}
              onClick={() => setActiveTab("contradictions")}
            >
              <WarningIcon /> Contradictions ({contradictions.length})
            </button>
            <button
              className={`${styles.tab} ${activeTab === "gaps" ? styles.activeTab : ""}`}
              onClick={() => setActiveTab("gaps")}
            >
              <SearchIcon /> Gaps ({gaps.length})
            </button>
            <button
              className={`${styles.tab} ${activeTab === "graph" ? styles.activeTab : ""}`}
              onClick={() => setActiveTab("graph")}
            >
              <GraphIcon /> Research Graph
            </button>
          </nav>

          <div className={styles.tabContent}>
            
            {/* Report Tab */}
            {activeTab === "report" && (
              <div className={styles.reportContainer}>
                {report ? (
                  <div dangerouslySetInnerHTML={{ __html: parseMarkdown(report.markdown_content) }} />
                ) : (
                  <div style={{ textAlign: "center", padding: "80px 20px", color: "var(--text-secondary)" }}>
                    <div style={{ display: "flex", justifyContent: "center", marginBottom: "16px", color: "var(--primary-light)" }}>
                      <LoaderIcon />
                    </div>
                    <p style={{ fontSize: "1.1rem", fontWeight: "600", marginBottom: "6px", color: "#fff" }}>Agent squad is research scoping...</p>
                    <p style={{ fontSize: "0.9rem" }}>The multi-agent fact check and drafting pipeline runs in the background. The full report will mount here when completed.</p>
                  </div>
                )}
              </div>
            )}

            {/* Sources Tab */}
            {activeTab === "sources" && (
              <div className={styles.sourcesGrid}>
                {sources.length === 0 ? (
                  <p style={{ gridColumn: "1/-1", textAlign: "center", padding: "60px", color: "var(--text-muted)", fontSize: "0.95rem" }}>
                    No research literature or web sources gathered yet.
                  </p>
                ) : (
                  sources.map((src) => (
                    <div key={src.id} className={styles.sourceCard}>
                      <div className={styles.sourceCardHeader}>
                        <a href={src.url || "#"} target="_blank" rel="noreferrer" className={styles.sourceTitle}>
                          {src.title}
                        </a>
                        <span className={styles.reliabilityBadge}>
                          <StarIcon /> 
                          <span style={{ color: getReliabilityColor(src.reliability_score), fontWeight: "bold" }}>
                            {(src.reliability_score * 100).toFixed(0)}%
                          </span>
                        </span>
                      </div>
                      {src.justification && (
                        <p className={styles.sourceJustification}>{src.justification}</p>
                      )}
                      <div className={styles.sourceFooter}>
                        <span>Type: {src.source_type}</span>
                        <span>Fetched: {new Date(src.fetched_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Contradictions Tab */}
            {activeTab === "contradictions" && (
              <div className={styles.contradictionsList}>
                {contradictions.length === 0 ? (
                  <p style={{ textAlign: "center", padding: "60px", color: "var(--text-muted)", fontSize: "0.95rem" }}>
                    No contradictions or conflicting information identified in the literature.
                  </p>
                ) : (
                  contradictions.map((con) => (
                    <div key={con.id} className={styles.contradictionCard}>
                      <div className={styles.contradictionHeader}>
                        <WarningIcon /> Factual Discrepancy Found
                      </div>
                      <div className={styles.contradictionGrid}>
                        <div className={styles.claimBox}>
                          <span className={styles.claimLabel}>Source Argument A</span>
                          <p className={styles.claimText}>{con.claim_a}</p>
                        </div>
                        <div className={styles.claimBox}>
                          <span className={styles.claimLabel}>Source Argument B</span>
                          <p className={styles.claimText}>{con.claim_b}</p>
                        </div>
                      </div>
                      {con.explanation && (
                        <div className={styles.contradictionResolution}>
                          <div className={styles.resolutionLabel}>Reconciliation Analysis</div>
                          <p style={{ color: "var(--text-primary)" }}>{con.explanation}</p>
                          {con.resolution_tip && (
                            <p style={{ marginTop: "10px", color: "var(--text-secondary)", fontSize: "0.85rem" }}>
                              <strong>Guidance:</strong> {con.resolution_tip}
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Gaps Tab */}
            {activeTab === "gaps" && (
              <div className={styles.gapsGrid}>
                {gaps.length === 0 ? (
                  <p style={{ textAlign: "center", padding: "60px", color: "var(--text-muted)", fontSize: "0.95rem" }}>
                    No literary or data gaps detected by reviewers.
                  </p>
                ) : (
                  gaps.map((gap) => (
                    <div key={gap.id} className={styles.gapCard}>
                      <div className={styles.gapHeader}>
                        <SearchIcon /> {gap.gap_title}
                      </div>
                      {gap.description && <p className={styles.gapDesc}>{gap.description}</p>}
                      {gap.evidence && (
                        <div className={styles.gapEvidence}>
                          <strong>Evidence of Lack:</strong> {gap.evidence}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Graph Tab */}
            {activeTab === "graph" && (
              <div className={styles.graphWrapper}>
                <div className={styles.graphRoot}>
                  <div className={styles.graphNode}>
                    {project.topic}
                  </div>
                  
                  {project.subtopics && project.subtopics.length > 0 ? (
                    <div className={styles.graphRow}>
                      {project.subtopics.map((subtopic, index) => {
                        const relatedQuestions = project.research_questions
                          ? project.research_questions.filter((_, qIdx) => qIdx % project.subtopics.length === index)
                          : [];

                        return (
                          <div key={index} className={styles.subtopicNode}>
                            <div style={{ paddingBottom: "8px", fontWeight: "700" }}>{subtopic}</div>
                            {relatedQuestions.length > 0 && (
                              <div className={styles.questionList}>
                                {relatedQuestions.map((q, qKey) => (
                                  <div key={qKey} className={styles.questionItem}>
                                    {q}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <p style={{ color: "var(--text-secondary)", padding: "40px" }}>
                      Mapping subtopic nodes. Waiting for agent planner node...
                    </p>
                  )}
                </div>
              </div>
            )}

          </div>
        </main>

        {/* Right Column - Timeline + Doc Upload */}
        <aside style={{ display: "flex", flexDirection: "column", gap: "32px" }}>
          
          {/* Live Agent Timeline */}
          <div className={`${styles.timelinePanel} glass`}>
            <div className={styles.timelineTitle}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span>Agent Activity Log</span>
                <span className={getStatusBadgeClass(wsConnected ? "done" : "failed")}>
                  {wsConnected ? "Online" : "Offline"}
                </span>
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: "normal", marginTop: "6px" }}>
                URL: {WS_URL}
              </div>
              {wsError && (
                <div style={{ fontSize: "0.8rem", color: "var(--danger)", fontWeight: "normal", marginTop: "4px" }}>
                  {wsError}
                </div>
              )}
            </div>
            
            <div className={styles.timelineEventsList}>
              {timelineEvents.length === 0 ? (
                <div className={styles.timelineEvent} style={{ borderLeft: "none", paddingLeft: 0 }}>
                  <p style={{ color: "var(--text-muted)", fontSize: "0.88rem" }}>
                    Connecting to feed...
                  </p>
                </div>
              ) : (
                timelineEvents.map((evt, idx) => {
                  const isActive = idx === timelineEvents.length - 1 && project.status !== "done" && project.status !== "failed";
                  return (
                    <div
                      key={idx}
                      className={`${styles.timelineEvent} ${isActive ? styles.eventActive : styles.eventSuccess}`}
                    >
                      <div className={styles.eventMeta}>
                        <span className={styles.eventAgent}>{evt.agent}</span>
                        <span>{evt.timestamp ? new Date(evt.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : ""}</span>
                      </div>
                      <p className={styles.eventMessage}>{evt.message}</p>
                    </div>
                  );
                })
              )}
              <div ref={timelineEndRef} />
            </div>
          </div>

          {/* Reference Docs Upload */}
          <div className={`${styles.uploadSection} glass`}>
            <div className={styles.timelineTitle} style={{ borderBottom: "none", paddingBottom: 0 }}>
              Add Reference Materials
            </div>
            <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", lineHeight: "1.5" }}>
              Index local PDF sources (whitepapers, studies). They will be parsed, chunked, and embedded into pgvector database to enrich local RAG retrieval.
            </p>
            
            <form onSubmit={handleUpload} className={styles.uploadForm}>
              <label className={styles.fileInputLabel}>
                <UploadIcon />
                <span style={{ fontSize: "0.9rem", fontWeight: "600", color: "#fff" }}>
                  {selectedFile ? "Replace Selected PDF" : "Browse PDF Literature"}
                </span>
                <input
                  type="file"
                  accept=".pdf"
                  className={styles.hiddenInput}
                  onChange={handleFileChange}
                  disabled={uploading}
                />
              </label>

              {selectedFile && (
                <div className={styles.selectedFile}>
                  {selectedFile.name}
                </div>
              )}

              {uploadProgress > 0 && (
                <div className={styles.uploadProgress}>
                  <div className={styles.progressBar} style={{ width: `${uploadProgress}%` }} />
                </div>
              )}

              {uploadSuccess && <div className={styles.uploadSuccess}>{uploadSuccess}</div>}
              {uploadError && <div className={styles.errorBanner}>{uploadError}</div>}

              <button
                type="submit"
                className="btn-primary"
                style={{ width: "100%", padding: "12px" }}
                disabled={!selectedFile || uploading}
              >
                {uploading ? (
                  <>
                    <LoaderIcon />
                    <span>Indexing Content...</span>
                  </>
                ) : (
                  "Process Literature"
                )}
              </button>
            </form>
          </div>

        </aside>

      </div>
    </div>
  );
}
