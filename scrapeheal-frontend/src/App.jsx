import { useState } from "react";
import "./App.css";

const API_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const DEFAULT_URL = "https://books.toscrape.com/";

function App() {
  const [url, setUrl] = useState(DEFAULT_URL);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const runScraper = async () => {
    if (!url.trim()) {
      setError("Please enter a website URL.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch(`${API_URL}/self-heal`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url: url.trim(),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        const message =
          data?.detail?.error ||
          data?.detail?.message ||
          data?.detail ||
          data?.message ||
          "The extraction request failed.";

        throw new Error(
          typeof message === "string"
            ? message
            : JSON.stringify(message)
        );
      }

      setResult(data);
    } catch (err) {
      console.error("ScrapeHeal error:", err);

      setError(
        err.message ||
        "Unable to connect to the ScrapeHeal backend."
      );
    } finally {
      setLoading(false);
    }
  };

  const history = Array.isArray(result?.history)
    ? result.history
    : [];

  const analysis = result?.analysis || {};

  const issues = Array.isArray(analysis?.issues)
    ? analysis.issues
    : [];

  const status = result?.status || "";

  const isVerified =
    status === "success" || status === "self_healed";

  const isSelfHealed = status === "self_healed";

  const isFailed =
    status === "failed_verification" ||
    status === "failed";

  const confidence =
    analysis?.confidence !== undefined
      ? analysis.confidence
      : null;

  const risk = getRisk(analysis, status);

  const action = getAction(
    status,
    analysis,
    isVerified
  );

  const attempts = calculateAttempts(history, status);

  const finalData = result?.final_data;

  return (
    <div className="app">

      {/* ================= HEADER ================= */}

      <header className="topbar">
        <div className="brand">
          <div className="brand-icon">🛡️</div>

          <div>
            <div className="brand-name">
              ScrapeHeal AI
            </div>

            <div className="brand-subtitle">
              Self-healing web extraction
            </div>
          </div>
        </div>

        <div className="system-status">
          <span className="status-dot"></span>
          SYSTEM ONLINE
        </div>
      </header>

      {/* ================= HERO ================= */}

      <main>

        <section className="hero">

          <div className="hero-content">

            <div className="eyebrow">
              AUTONOMOUS WEB DATA RELIABILITY
            </div>

            <h1>
              Web extraction
              <br />
              <span>that heals itself.</span>
            </h1>

            <p>
              Detect extraction anomalies, diagnose them
              with AI, recover the extraction workflow,
              and verify the recovered data.
            </p>

            <div className="technology-row">
              <span>Bright Data</span>
              <span>Gemini AI</span>
              <span>FastAPI</span>
              <span>React</span>
            </div>

          </div>

          <div className="hero-visual">

            <div className="hero-circle">
              🛡️
            </div>

            <div className="floating-card detect">
              🔎 Detect
            </div>

            <div className="floating-card diagnose">
              🤖 Diagnose
            </div>

            <div className="floating-card repair">
              🔧 Repair
            </div>

            <div className="floating-card verify">
              ✓ Verify
            </div>

          </div>

        </section>

        {/* ================= EXTRACTION CONTROL ================= */}

        <section className="card extraction-card">

          <div className="section-label">
            EXTRACTION CONTROL
          </div>

          <h2>
            Analyze a public website
          </h2>

          <p className="section-description">
            Enter a public website and let ScrapeHeal
            extract and validate its data.
          </p>

          <div className="url-row">

            <div className="url-input-wrapper">
              <span className="url-icon">
                🌐
              </span>

              <input
                type="url"
                value={url}
                onChange={(e) =>
                  setUrl(e.target.value)
                }
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !loading) {
                    runScraper();
                  }
                }}
                placeholder="https://example.com"
                disabled={loading}
              />
            </div>

            <button
              className="analyze-button"
              onClick={runScraper}
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="spinner"></span>
                  Analyzing...
                </>
              ) : (
                <>
                  🚀 Analyze
                </>
              )}
            </button>

          </div>

          <div className="endpoint-info">
            Backend: {API_URL}
          </div>

          {error && (
            <div className="error-box">
              <strong>⚠️ Extraction error</strong>
              <p>{error}</p>
            </div>
          )}

        </section>

        {/* ================= WORKING PIPELINE ================= */}

        {loading && (
          <section className="card working-card">

            <div className="working-icon">
              ⚡
            </div>

            <h2>
              ScrapeHeal is working...
            </h2>

            <p>
              Running extraction, AI diagnosis,
              recovery and verification.
            </p>

            <div className="pipeline">

              <PipelineStep
                number="1"
                title="Bright Data"
                subtitle="Extract"
                active
              />

              <PipelineLine />

              <PipelineStep
                number="2"
                title="Gemini AI"
                subtitle="Diagnose"
                active
              />

              <PipelineLine />

              <PipelineStep
                number="3"
                title="Repair"
                subtitle="Recover"
                active
              />

              <PipelineLine />

              <PipelineStep
                number="4"
                title="Verify"
                subtitle="Trust"
                active
              />

            </div>

          </section>
        )}

        {/* ================= RESULT ================= */}

        {result && !loading && (
          <>
            <section className="card result-card">

              <div className="result-header">

                <div>

                  <div className="section-label">
                    SCRAPING RESULT
                  </div>

                  <h2>
                    {isSelfHealed
                      ? "Extraction self-healed"
                      : isVerified
                        ? "Extraction verified"
                        : "Extraction requires review"}
                  </h2>

                  <p className="result-url">
                    {url}
                  </p>

                </div>

                <StatusBadge
                  verified={isVerified}
                  selfHealed={isSelfHealed}
                  failed={isFailed}
                />

              </div>

            </section>

            {/* ================= METRICS ================= */}

            <section className="metrics-grid">

              <MetricCard
                icon="🔄"
                title="Attempts"
                value={attempts}
                description={
                  attempts === 1
                    ? "Initial extraction"
                    : "Extraction attempts"
                }
              />

              <MetricCard
                icon="🎯"
                title="Confidence"
                value={
                  confidence !== null
                    ? `${confidence}%`
                    : "—"
                }
                description="AI assessment"
              />

              <MetricCard
                icon="🛡️"
                title="Risk"
                value={risk}
                description="Data reliability"
              />

              <MetricCard
                icon="⚡"
                title="Action"
                value={action}
                description="Recommended state"
              />

            </section>

            {/* ================= AI ANALYSIS ================= */}

            <section className="card analysis-card">

              <div className="section-label">
                AI RELIABILITY ANALYSIS
              </div>

              <h2>
                🤖 Gemini Analysis
              </h2>

              <div className="analysis-status">

                <div
                  className={
                    analysis?.is_valid
                      ? "analysis-icon success"
                      : "analysis-icon warning"
                  }
                >
                  {analysis?.is_valid
                    ? "✓"
                    : "!"}
                </div>

                <div>

                  <h3>
                    {analysis?.is_valid
                      ? "Data appears reliable"
                      : "Potential extraction anomaly detected"}
                  </h3>

                  <p>
                    {analysis?.is_valid
                      ? "The extracted output passed the AI reliability checks."
                      : "Gemini identified one or more conditions that require attention."}
                  </p>

                </div>

              </div>

              {/* Issues */}

              {issues.length > 0 && (
                <div className="issues-section">

                  <h3>
                    Detected issues
                  </h3>

                  <div className="issues-list">

                    {issues.map((issue, index) => (
                      <div
                        className="issue-item"
                        key={index}
                      >
                        <span>⚠️</span>
                        <span>
                          {String(issue)}
                        </span>
                      </div>
                    ))}

                  </div>

                </div>
              )}

              {/* Repair strategy */}

              {analysis?.repair_instruction && (
                <div className="repair-box">

                  <div className="repair-title">
                    🔧 Repair strategy
                  </div>

                  <p>
                    {analysis.repair_instruction}
                  </p>

                </div>
              )}

            </section>

            {/* ================= PIPELINE ================= */}

            <section className="card pipeline-result-card">

              <div className="section-label">
                RECOVERY PIPELINE
              </div>

              <h2>
                Extraction workflow
              </h2>

              <div className="result-pipeline">

                <PipelineResultStep
                  number="1"
                  title="Bright Data"
                  subtitle="Extracted"
                  done
                />

                <PipelineLine />

                <PipelineResultStep
                  number="2"
                  title="Gemini AI"
                  subtitle="Analyzed"
                  done
                />

                <PipelineLine />

                <PipelineResultStep
                  number="3"
                  title="Repair"
                  subtitle={
                    isSelfHealed
                      ? "Applied"
                      : analysis?.is_valid
                        ? "Not required"
                        : "Evaluated"
                  }
                  done={
                    isSelfHealed ||
                    analysis?.is_valid
                  }
                />

                <PipelineLine />

                <PipelineResultStep
                  number="4"
                  title="Verify"
                  subtitle={
                    isVerified
                      ? "Verified"
                      : "Review"
                  }
                  done={isVerified}
                />

              </div>

            </section>

            {/* ================= RECOVERY HISTORY ================= */}

            {history.length > 0 && (
              <section className="card history-card">

                <div className="section-label">
                  AUDIT TRAIL
                </div>

                <h2>
                  Recovery History
                </h2>

                <p className="section-description">
                  A step-by-step record of what happened
                  during the extraction reliability workflow.
                </p>

                <div className="history-list">

                  {history.map((item, index) => (

                    <div
                      className="history-item"
                      key={index}
                    >

                      <div className="history-number">
                        {index + 1}
                      </div>

                      <div className="history-content">

                        <div className="history-title">
                          {formatAction(
                            item?.action
                          )}
                        </div>

                        {item?.issues &&
                          Array.isArray(item.issues) &&
                          item.issues.length > 0 && (
                            <div className="history-detail">
                              {item.issues.join(
                                " • "
                              )}
                            </div>
                          )}

                        {item?.message && (
                          <div className="history-detail">
                            {item.message}
                          </div>
                        )}

                      </div>

                      <div className="history-check">
                        ✓
                      </div>

                    </div>

                  ))}

                </div>

              </section>
            )}

            {/* ================= FINAL DATA ================= */}

            <section className="card data-card">

              <div className="section-label">
                VERIFIED OUTPUT
              </div>

              <h2>
                Extracted Data
              </h2>

              <p className="section-description">
                Structured output returned by the
                extraction reliability pipeline.
              </p>

              <pre className="json-output">
                {formatJSON(finalData)}
              </pre>

            </section>

          </>
        )}

        {/* ================= FOOTER ================= */}

        <footer>

          <div>
            🛡️ <strong>ScrapeHeal AI</strong>
          </div>

          <div>
            Bright Data × Gemini AI × FastAPI × React
          </div>

        </footer>

      </main>
    </div>
  );
}

/* =========================================================
   COMPONENTS
========================================================= */

function PipelineStep({
  number,
  title,
  subtitle,
  active,
}) {
  return (
    <div
      className={`pipeline-step ${active ? "active" : ""
        }`}
    >
      <div className="pipeline-number">
        {number}
      </div>

      <strong>{title}</strong>

      <span>{subtitle}</span>
    </div>
  );
}

function PipelineResultStep({
  number,
  title,
  subtitle,
  done,
}) {
  return (
    <div className="pipeline-step">

      <div
        className={`pipeline-number ${done ? "completed" : ""
          }`}
      >
        {done ? "✓" : number}
      </div>

      <strong>{title}</strong>

      <span>{subtitle}</span>

    </div>
  );
}

function PipelineLine() {
  return (
    <div className="pipeline-line"></div>
  );
}

function MetricCard({
  icon,
  title,
  value,
  description,
}) {
  return (
    <div className="metric-card">

      <div className="metric-icon">
        {icon}
      </div>

      <div className="metric-content">

        <div className="metric-title">
          {title}
        </div>

        <div className="metric-value">
          {value}
        </div>

        <div className="metric-description">
          {description}
        </div>

      </div>

    </div>
  );
}

function StatusBadge({
  verified,
  selfHealed,
  failed,
}) {
  if (selfHealed) {
    return (
      <div className="status-badge healed">
        ✓ SELF-HEALED
      </div>
    );
  }

  if (verified) {
    return (
      <div className="status-badge verified">
        ✓ VERIFIED
      </div>
    );
  }

  if (failed) {
    return (
      <div className="status-badge failed">
        ⚠ REVIEW
      </div>
    );
  }

  return (
    <div className="status-badge failed">
      ⚠ REVIEW
    </div>
  );
}

/* =========================================================
   HELPERS
========================================================= */

function calculateAttempts(history, status) {
  if (!history.length) {
    return status === "success" ||
      status === "self_healed"
      ? 1
      : 1;
  }

  const scrapeEvents = history.filter(
    (item) => {
      const action = String(
        item?.action || ""
      ).toLowerCase();

      return (
        action.includes("scrape") ||
        action.includes("extraction") ||
        action.includes("re-run") ||
        action.includes("rerun") ||
        action.includes("re_extract")
      );
    }
  );

  return Math.max(
    1,
    scrapeEvents.length
  );
}

function getRisk(analysis, status) {
  if (analysis?.is_valid === true) {
    return "Low";
  }

  if (status === "self_healed") {
    return "Low";
  }

  if (analysis?.issues?.length >= 3) {
    return "High";
  }

  if (analysis?.issues?.length > 0) {
    return "Medium";
  }

  return "—";
}

function getAction(
  status,
  analysis,
  verified
) {
  if (status === "self_healed") {
    return "Verified";
  }

  if (verified) {
    return "Accept";
  }

  if (
    analysis?.is_valid === false
  ) {
    return "Review";
  }

  return "Review";
}

function formatAction(action) {
  if (!action) {
    return "Pipeline step completed";
  }

  return String(action)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) =>
      letter.toUpperCase()
    );
}

function formatJSON(data) {
  if (data === undefined) {
    return "No extracted data returned.";
  }

  try {
    return JSON.stringify(
      data,
      null,
      2
    );
  } catch {
    return String(data);
  }
}

export default App;