import { useState } from "react";
import "./App.css";

// ======================================================
// BACKEND URL
// ======================================================

const API_URL = (
  import.meta.env.VITE_API_URL ||
  "https://scrapheal-ai-backend.vercel.app"
).trim().replace(/\/+$/, "");

const DEFAULT_URL = "https://books.toscrape.com/";

// ======================================================
// APP
// ======================================================

function App() {
  const [url, setUrl] = useState(DEFAULT_URL);

  const [loading, setLoading] = useState(false);

  const [error, setError] = useState("");

  const [result, setResult] = useState(null);

  // ====================================================
  // CLEAN URL
  // ====================================================

  const cleanUrl = (value) => {
    if (!value) {
      return "";
    }

    return String(value)
      .replace(/[\r\n\t]/g, "")
      .replace(/[\u0000-\u001F\u007F]/g, "")
      .trim();
  };

  // ====================================================
  // ANALYZE WEBSITE
  // ====================================================

  const handleAnalyze = async () => {
    setError("");
    setResult(null);

    const cleanTargetUrl = cleanUrl(url);

    // -----------------------------------------------
    // Validate URL
    // -----------------------------------------------

    if (!cleanTargetUrl) {
      setError("Please enter a website URL.");
      return;
    }

    if (
      !cleanTargetUrl.startsWith("http://") &&
      !cleanTargetUrl.startsWith("https://")
    ) {
      setError(
        "Please enter a valid URL starting with https://"
      );
      return;
    }

    setLoading(true);

    try {
      console.log("Frontend API URL:", API_URL);
      console.log(
        "Target URL:",
        JSON.stringify(cleanTargetUrl)
      );

      // ---------------------------------------------
      // Call FastAPI
      // ---------------------------------------------

      const response = await fetch(
        `${API_URL}/self-heal`,
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },

          body: JSON.stringify({
            url: cleanTargetUrl,
          }),
        }
      );

      // ---------------------------------------------
      // Read response
      // ---------------------------------------------

      const contentType =
        response.headers.get("content-type") || "";

      let data;

      if (contentType.includes("application/json")) {
        data = await response.json();
      } else {
        const text = await response.text();

        data = {
          error: text,
        };
      }

      // ---------------------------------------------
      // Backend error
      // ---------------------------------------------

      if (!response.ok) {
        let message =
          data?.detail?.error ||
          data?.detail ||
          data?.error ||
          `Backend returned HTTP ${response.status}`;

        if (typeof message !== "string") {
          message = JSON.stringify(message);
        }

        throw new Error(message);
      }

      // ---------------------------------------------
      // Success
      // ---------------------------------------------

      console.log(
        "ScrapeHeal response:",
        data
      );

      setResult(data);
    } catch (err) {
      console.error(
        "ScrapeHeal request failed:",
        err
      );

      // ---------------------------------------------
      // Browser connection/CORS error
      // ---------------------------------------------

      if (
        err instanceof TypeError &&
        err.message.toLowerCase().includes("fetch")
      ) {
        setError(
          "Cannot connect to the ScrapeHeal backend. " +
          "Please check the backend URL and CORS configuration."
        );
      } else {
        setError(
          err?.message ||
          "Something went wrong while analyzing the website."
        );
      }
    } finally {
      setLoading(false);
    }
  };

  // ====================================================
  // RENDER
  // ====================================================

  return (
    <div className="app">

      {/* =================================================
          HEADER
      ================================================= */}

      <header className="topbar">

        <div className="brand">

          <div className="brand-icon">
            🛡️
          </div>

          <div>
            <div className="brand-title">
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

      {/* =================================================
          HERO
      ================================================= */}

      <section className="hero">

        <div className="hero-content">

          <div className="hero-label">
            AI-POWERED WEB RELIABILITY
          </div>

          <h1>
            Web extraction
            <br />
            that heals itself.
          </h1>

          <p>
            Detect extraction anomalies, diagnose them
            with AI, recover the extraction workflow,
            and verify the recovered data.
          </p>

          <div className="tech-stack">

            <span>
              Bright Data
            </span>

            <span>
              Gemini AI
            </span>

            <span>
              FastAPI
            </span>

            <span>
              React
            </span>

          </div>

        </div>

        <div className="hero-visual">

          <div className="visual-circle">
            <span>✓</span>
          </div>

          <div className="floating-card">
            🔧 Repair
          </div>

          <div className="floating-card verify-card">
            ✓ Verify
          </div>

        </div>

      </section>

      {/* =================================================
          EXTRACTION CONTROL
      ================================================= */}

      <main className="main-container">

        <section className="extraction-card">

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

          {/* ---------------------------------------------
              URL INPUT
          --------------------------------------------- */}

          <div className="input-row">

            <div className="url-input-wrapper">

              <span className="globe-icon">
                🌐
              </span>

              <input
                type="url"
                value={url}
                onChange={(e) => {
                  setUrl(
                    e.target.value
                      .replace(/[\r\n\t]/g, "")
                  );

                  setError("");
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    handleAnalyze();
                  }
                }}
                placeholder="https://example.com"
                disabled={loading}
              />

            </div>

            <button
              className="analyze-button"
              onClick={handleAnalyze}
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

          {/* ---------------------------------------------
              PIPELINE
          --------------------------------------------- */}

          {loading && (
            <div className="working-card">

              <div className="working-icon">
                ⚡
              </div>

              <h3>
                ScrapeHeal is working...
              </h3>

              <p>
                Running extraction, AI diagnosis,
                repair and verification.
              </p>

              <div className="pipeline">

                <div className="pipeline-step active">
                  <strong>1</strong>
                  <span>Bright Data</span>
                  <small>Extract</small>
                </div>

                <div className="pipeline-line"></div>

                <div className="pipeline-step active">
                  <strong>2</strong>
                  <span>Gemini AI</span>
                  <small>Diagnose</small>
                </div>

                <div className="pipeline-line"></div>

                <div className="pipeline-step active">
                  <strong>3</strong>
                  <span>Repair</span>
                  <small>Recover</small>
                </div>

                <div className="pipeline-line"></div>

                <div className="pipeline-step active">
                  <strong>4</strong>
                  <span>Verify</span>
                  <small>Trust</small>
                </div>

              </div>

            </div>
          )}

          {/* ---------------------------------------------
              ERROR
          --------------------------------------------- */}

          {error && !loading && (
            <div className="error-card">

              <div className="error-title">
                ⚠️ Extraction error
              </div>

              <div className="error-message">
                {error}
              </div>

            </div>
          )}

          {/* ---------------------------------------------
              RESULT
          --------------------------------------------- */}

          {result && !loading && (
            <div className="result-card">

              <div className="result-header">

                <div>

                  <div className="section-label">
                    EXTRACTION RESULT
                  </div>

                  <h3>
                    {result.status === "self_healed"
                      ? "Self-healing successful"
                      : result.status === "success"
                        ? "Extraction verified"
                        : "Analysis completed"}
                  </h3>

                </div>

                <div className="result-status">
                  ✓ Verified
                </div>

              </div>

              {/* -----------------------------------------
                  ANALYSIS
              ----------------------------------------- */}

              {result.analysis && (
                <div className="analysis-grid">

                  <div className="analysis-box">

                    <span>
                      Confidence
                    </span>

                    <strong>
                      {result.analysis.confidence ?? 0}%
                    </strong>

                  </div>

                  <div className="analysis-box">

                    <span>
                      Risk
                    </span>

                    <strong>
                      {result.analysis.risk_level ||
                        "Unknown"}
                    </strong>

                  </div>

                  <div className="analysis-box">

                    <span>
                      Attempts
                    </span>

                    <strong>
                      {result.attempts ?? 1}
                    </strong>

                  </div>

                </div>
              )}

              {/* -----------------------------------------
                  EXPLANATION
              ----------------------------------------- */}

              {result.analysis?.explanation && (
                <div className="explanation">

                  <strong>
                    AI Diagnosis
                  </strong>

                  <p>
                    {result.analysis.explanation}
                  </p>

                </div>
              )}

              {/* -----------------------------------------
                  ISSUES
              ----------------------------------------- */}

              {result.analysis?.issues?.length > 0 && (
                <div className="issues">

                  <strong>
                    Detected Issues
                  </strong>

                  <ul>
                    {result.analysis.issues.map(
                      (issue, index) => (
                        <li key={index}>
                          {issue}
                        </li>
                      )
                    )}
                  </ul>

                </div>
              )}

              {/* -----------------------------------------
                  PIPELINE HISTORY
              ----------------------------------------- */}

              {result.history?.length > 0 && (
                <div className="history">

                  <strong>
                    ScrapeHeal Pipeline
                  </strong>

                  <div className="history-list">

                    {result.history.map(
                      (item, index) => (
                        <div
                          className="history-item"
                          key={index}
                        >

                          <span className="history-number">
                            {item.step}
                          </span>

                          <span className="history-action">
                            {String(
                              item.action || ""
                            ).replaceAll(
                              "_",
                              " "
                            )}
                          </span>

                          <span className="history-status">
                            ✓ {item.status}
                          </span>

                        </div>
                      )
                    )}

                  </div>

                </div>
              )}

              {/* -----------------------------------------
                  DATA
              ----------------------------------------- */}

              {result.final_data && (
                <details className="data-section">

                  <summary>
                    View extracted data
                  </summary>

                  <pre>
                    {JSON.stringify(
                      result.final_data,
                      null,
                      2
                    )}
                  </pre>

                </details>
              )}

            </div>
          )}

        </section>

      </main>

      {/* =================================================
          FOOTER
      ================================================= */}

      <footer className="footer">

        <span>
          ScrapeHeal AI
        </span>

        <span>
          Bright Data • Gemini AI • FastAPI • React
        </span>

      </footer>

    </div>
  );
}

export default App;