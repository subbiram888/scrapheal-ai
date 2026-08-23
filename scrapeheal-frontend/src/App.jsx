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

  const analyzeWebsite = async () => {
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
        let message = "Extraction failed.";

        if (typeof data?.detail === "string") {
          message = data.detail;
        } else if (data?.detail?.error) {
          message = data.detail.error;
        }

        throw new Error(message);
      }

      setResult(data);
    } catch (err) {
      console.error(err);
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

  const issues = Array.isArray(analysis.issues)
    ? analysis.issues
    : [];

  const status = result?.status || "";

  const verified =
    status === "success" ||
    status === "self_healed";

  const healed =
    status === "self_healed";

  return (
    <div className="app">

      {/* HEADER */}

      <header className="header">
        <div className="header-inner">

          <div className="brand">
            <div className="brand-logo">
              🛡️
            </div>

            <div>
              <div className="brand-name">
                ScrapeHeal AI
              </div>

              <div className="brand-tagline">
                Self-healing web extraction
              </div>
            </div>
          </div>

          <div className="online">
            <span className="online-dot"></span>
            SYSTEM ONLINE
          </div>

        </div>
      </header>


      {/* HERO */}

      <section className="hero">

        <div className="hero-inner">

          <div className="hero-left">

            <div className="hero-label">
              AUTONOMOUS WEB DATA RELIABILITY
            </div>

            <h1>
              Web extraction
              <br />
              <span>that heals itself.</span>
            </h1>

            <p>
              Detect extraction anomalies, diagnose them
              with AI, repair the extraction workflow,
              and verify the recovered data.
            </p>

            <div className="tech-stack">

              <span>Bright Data</span>
              <span>Gemini AI</span>
              <span>FastAPI</span>
              <span>React</span>

            </div>

          </div>


          <div className="hero-right">

            <div className="hero-orbit">

              <div className="orbit-circle">
                🛡️
              </div>

              <div className="hero-pill pill-detect">
                🔎 Detect
              </div>

              <div className="hero-pill pill-diagnose">
                🤖 Diagnose
              </div>

              <div className="hero-pill pill-repair">
                🔧 Repair
              </div>

              <div className="hero-pill pill-verify">
                ✓ Verify
              </div>

            </div>

          </div>

        </div>

      </section>


      <main className="main">


        {/* EXTRACTION CONTROL */}

        <section className="main-card extraction-card">

          <div className="card-label">
            EXTRACTION CONTROL
          </div>

          <h2>
            Analyze a public website
          </h2>

          <p className="card-description">
            Enter a public website and let ScrapeHeal
            extract and validate its data.
          </p>


          <div className="url-container">

            <div className="url-box">

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
                  if (
                    e.key === "Enter" &&
                    !loading
                  ) {
                    analyzeWebsite();
                  }
                }}
                disabled={loading}
                placeholder="https://example.com"
              />

            </div>

            <button
              className="analyze-btn"
              onClick={analyzeWebsite}
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


          {error && (
            <div className="error-message">
              <strong>⚠️ Extraction error</strong>
              <span>{error}</span>
            </div>
          )}

        </section>


        {/* LOADING PIPELINE */}

        {loading && (

          <section className="main-card processing-card">

            <div className="processing-icon">
              ⚡
            </div>

            <h2>
              ScrapeHeal is working...
            </h2>

            <p>
              Running extraction, AI diagnosis,
              repair and verification.
            </p>


            <div className="pipeline">

              <PipelineStep
                number="1"
                title="Bright Data"
                subtitle="Extract"
                active
              />

              <div className="pipeline-line"></div>

              <PipelineStep
                number="2"
                title="Gemini AI"
                subtitle="Diagnose"
                active
              />

              <div className="pipeline-line"></div>

              <PipelineStep
                number="3"
                title="Repair"
                subtitle="Recover"
                active
              />

              <div className="pipeline-line"></div>

              <PipelineStep
                number="4"
                title="Verify"
                subtitle="Trust"
                active
              />

            </div>

          </section>

        )}


        {/* RESULT */}

        {result && !loading && (

          <>

            <section className="main-card result-card">

              <div>

                <div className="card-label">
                  SCRAPING RESULT
                </div>

                <h2>
                  {healed
                    ? "Extraction self-healed"
                    : verified
                      ? "Extraction verified"
                      : "Extraction requires review"}
                </h2>

                <p className="result-url">
                  {url}
                </p>

              </div>


              <div
                className={`result-badge ${healed
                    ? "healed"
                    : verified
                      ? "verified"
                      : "review"
                  }`}
              >

                {healed
                  ? "✓ SELF-HEALED"
                  : verified
                    ? "✓ VERIFIED"
                    : "⚠ REVIEW"}

              </div>

            </section>


            {/* METRICS */}

            <section className="metrics">

              <Metric
                icon="🔄"
                title="Pipeline"
                value="4 Steps"
                text="Extract → Diagnose → Repair → Verify"
              />

              <Metric
                icon="🎯"
                title="Confidence"
                value={
                  analysis.confidence !== undefined
                    ? `${analysis.confidence}%`
                    : "—"
                }
                text="AI reliability assessment"
              />

              <Metric
                icon="🛡️"
                title="Risk"
                value={
                  analysis.is_valid
                    ? "Low"
                    : issues.length
                      ? "Review"
                      : "—"
                }
                text="Data reliability"
              />

              <Metric
                icon="⚡"
                title="Action"
                value={
                  healed
                    ? "Recovered"
                    : verified
                      ? "Accept"
                      : "Review"
                }
                text="Recommended state"
              />

            </section>


            {/* AI ANALYSIS */}

            <section className="main-card">

              <div className="card-label">
                AI RELIABILITY ANALYSIS
              </div>

              <h2>
                🤖 Gemini AI Diagnosis
              </h2>

              <div className="diagnosis">

                <div
                  className={`diagnosis-icon ${analysis.is_valid
                      ? "good"
                      : "warning"
                    }`}
                >
                  {analysis.is_valid
                    ? "✓"
                    : "!"}
                </div>

                <div>

                  <h3>
                    {analysis.is_valid
                      ? "Data passed reliability checks"
                      : "Extraction anomaly detected"}
                  </h3>

                  <p>
                    {analysis.is_valid
                      ? "Gemini found the extracted data to be structurally reliable."
                      : "Gemini identified one or more conditions that may affect data reliability."}
                  </p>

                </div>

              </div>


              {issues.length > 0 && (

                <div className="issues">

                  <h3>
                    Detected issues
                  </h3>

                  {issues.map(
                    (issue, index) => (

                      <div
                        className="issue"
                        key={index}
                      >
                        <span>⚠️</span>
                        <span>
                          {String(issue)}
                        </span>
                      </div>

                    )
                  )}

                </div>

              )}


              {analysis.repair_instruction && (

                <div className="repair-box">

                  <strong>
                    🔧 Repair strategy
                  </strong>

                  <p>
                    {analysis.repair_instruction}
                  </p>

                </div>

              )}

            </section>


            {/* FOUR STEP PIPELINE */}

            <section className="main-card">

              <div className="card-label">
                RECOVERY PIPELINE
              </div>

              <h2>
                How ScrapeHeal handled this extraction
              </h2>

              <div className="pipeline result-pipeline">

                <PipelineResult
                  number="1"
                  title="Bright Data"
                  subtitle="Extract"
                  done
                />

                <div className="pipeline-line"></div>

                <PipelineResult
                  number="2"
                  title="Gemini AI"
                  subtitle="Diagnose"
                  done
                />

                <div className="pipeline-line"></div>

                <PipelineResult
                  number="3"
                  title="Repair"
                  subtitle={
                    healed
                      ? "Recovered"
                      : analysis.is_valid
                        ? "Not required"
                        : "Evaluated"
                  }
                  done={
                    healed ||
                    analysis.is_valid
                  }
                />

                <div className="pipeline-line"></div>

                <PipelineResult
                  number="4"
                  title="Verify"
                  subtitle={
                    verified
                      ? "Verified"
                      : "Review"
                  }
                  done={verified}
                />

              </div>

            </section>


            {/* HISTORY */}

            {history.length > 0 && (

              <section className="main-card history-card">

                <div className="card-label">
                  AUDIT TRAIL
                </div>

                <h2>
                  Recovery History
                </h2>

                <p className="card-description">
                  A transparent record of the actions
                  performed during the extraction workflow.
                </p>


                <div className="history">

                  {history.map(
                    (item, index) => (

                      <div
                        className="history-row"
                        key={index}
                      >

                        <div className="history-number">
                          {index + 1}
                        </div>

                        <div className="history-content">

                          <strong>
                            {formatAction(
                              item.action
                            )}
                          </strong>

                          {item.issues &&
                            Array.isArray(
                              item.issues
                            ) && (
                              <p>
                                {item.issues.join(
                                  " • "
                                )}
                              </p>
                            )}

                        </div>

                        <div className="history-status">
                          ✓
                        </div>

                      </div>

                    )
                  )}

                </div>

              </section>

            )}


            {/* OUTPUT */}

            <section className="main-card">

              <div className="card-label">
                EXTRACTED OUTPUT
              </div>

              <h2>
                Structured Data
              </h2>

              <p className="card-description">
                Data returned by the extraction pipeline.
              </p>

              <pre className="json">
                {formatJSON(result.final_data)}
              </pre>

            </section>

          </>

        )}

      </main>


      <footer className="footer">

        <div>
          🛡️ <strong>ScrapeHeal AI</strong>
        </div>

        <div>
          Bright Data × Gemini AI × FastAPI × React
        </div>

      </footer>

    </div>
  );
}


/* COMPONENTS */

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


function PipelineResult({
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


function Metric({
  icon,
  title,
  value,
  text,
}) {
  return (
    <div className="metric">

      <div className="metric-icon">
        {icon}
      </div>

      <div>

        <div className="metric-title">
          {title}
        </div>

        <div className="metric-value">
          {value}
        </div>

        <div className="metric-text">
          {text}
        </div>

      </div>

    </div>
  );
}


/* HELPERS */

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