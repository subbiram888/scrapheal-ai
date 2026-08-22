import { useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

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
    setResult(null);
    setError("");

    try {
      const response = await fetch(
        `${API_URL}/self-heal`,
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
          },

          body: JSON.stringify({
            url: url.trim(),
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        const message =
          data?.detail?.error ||
          data?.detail ||
          "Scraping failed.";

        throw new Error(
          typeof message === "string"
            ? message
            : "Scraping failed."
        );
      }

      setResult(data);

    } catch (err) {
      console.error(err);

      setError(
        err.message ||
        "Unable to connect to the backend."
      );

    } finally {
      setLoading(false);
    }
  };


  /* =======================================================
     RESULT STATE
  ======================================================= */

  const analysis = result?.analysis || {};

  const history = result?.history || [];

  /*
     IMPORTANT:
     Verified is TRUE only when the backend actually
     reports success/self-healed AND Gemini's final
     analysis says the data is valid.
  */

  const verified =
    (
      result?.status === "success" ||
      result?.status === "self_healed"
    ) &&
    analysis?.is_valid === true;


  const selfHealed =
    result?.status === "self_healed";


  const failed =
    result?.status === "failed";


  const action = verified
    ? selfHealed
      ? "Repaired"
      : "Accept"
    : failed
      ? "Failed"
      : "Review";


  const statusTitle = verified
    ? selfHealed
      ? "Extraction self-healed"
      : "Extraction verified"
    : failed
      ? "Extraction failed"
      : "Extraction requires review";


  return (
    <div className="app">

      {/* =================================================
          HEADER
      ================================================= */}

      <header className="topbar">

        <div className="brand">

          <div className="brand-logo">
            🛡️
          </div>

          <div>

            <h1>
              ScrapeHeal <span>AI</span>
            </h1>

            <p>
              Self-healing web extraction
            </p>

          </div>

        </div>


        <div className="online-status">

          <span className="online-dot"></span>

          SYSTEM ONLINE

        </div>

      </header>


      {/* =================================================
          HERO
      ================================================= */}

      <section className="hero">

        <div className="hero-content">

          <div className="hero-label">
            AUTONOMOUS WEB DATA RELIABILITY
          </div>

          <h2>
            Web extraction
            <br />
            <span>that heals itself.</span>
          </h2>

          <p>
            Detect extraction anomalies, diagnose them
            with AI, repair the Bright Data scraper and
            verify the recovered data.
          </p>


          <div className="technology-pills">

            <span>Bright Data</span>

            <span>Gemini AI</span>

            <span>FastAPI</span>

            <span>React</span>

          </div>

        </div>


        <div className="hero-visual">

          <div className="orb">
            🛡️
          </div>

          <div className="floating-card card-one">
            🔍 Detect
          </div>

          <div className="floating-card card-two">
            🤖 Diagnose
          </div>

          <div className="floating-card card-three">
            🔧 Repair
          </div>

          <div className="floating-card card-four">
            ✓ Verify
          </div>

        </div>

      </section>


      {/* =================================================
          MAIN
      ================================================= */}

      <main className="container">


        {/* EXTRACTION */}

        <section className="main-card control-card">

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


          <div className="url-container">

            <div className="url-icon">
              🌐
            </div>


            <input
              type="text"
              value={url}
              onChange={(e) =>
                setUrl(e.target.value)
              }
              placeholder={DEFAULT_URL}
              disabled={loading}
            />


            <button
              className="analyze-button"
              onClick={runScraper}
              disabled={loading}
            >

              {loading ? (
                <>
                  <span className="button-spinner"></span>
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

              <span>⚠️</span>

              <div>

                <strong>
                  Extraction error
                </strong>

                <p>
                  {error}
                </p>

              </div>

            </div>

          )}

        </section>


        {/* =================================================
            LOADING
        ================================================= */}

        {loading && (

          <section className="main-card loading-section">

            <div className="loading-icon">
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
              />

              <div className="pipeline-line"></div>

              <PipelineStep
                number="2"
                title="Gemini AI"
                subtitle="Diagnose"
              />

              <div className="pipeline-line"></div>

              <PipelineStep
                number="3"
                title="Repair"
                subtitle="Recover"
              />

              <div className="pipeline-line"></div>

              <PipelineStep
                number="4"
                title="Verify"
                subtitle="Trust"
              />

            </div>

          </section>

        )}


        {/* =================================================
            RESULT
        ================================================= */}

        {result && !loading && (

          <>

            {/* STATUS */}

            <section className="result-header">

              <div>

                <div className="section-label">
                  SCRAPING RESULT
                </div>

                <h2>
                  {statusTitle}
                </h2>

                <p>
                  {url}
                </p>

              </div>


              <div
                className={
                  verified
                    ? "verification-badge"
                    : "failure-badge"
                }
              >

                {verified
                  ? selfHealed
                    ? "✓ SELF-HEALED"
                    : "✓ VERIFIED"
                  : "✕ REVIEW"}

              </div>

            </section>


            {/* METRICS */}

            <section className="metrics-grid">

              <Metric
                icon="🔄"
                title="Attempts"
                value={result.attempts ?? 0}
              />


              <Metric
                icon="🎯"
                title="Confidence"
                value={
                  `${analysis.confidence ?? 0}%`
                }
              />


              <Metric
                icon="🛡️"
                title="Risk"
                value={
                  capitalize(
                    analysis.risk_level ||
                    "unknown"
                  )
                }
              />


              <Metric
                icon="⚡"
                title="Action"
                value={action}
              />

            </section>


            {/* AI DIAGNOSTICS */}

            <section className="main-card">

              <div className="section-label">
                AI DIAGNOSTICS
              </div>

              <h2>
                🤖 AI Reliability Analysis
              </h2>


              <div
                className={
                  verified
                    ? "analysis-good"
                    : "analysis-warning"
                }
              >

                <div className="analysis-icon">

                  {verified
                    ? "✓"
                    : "⚠️"}

                </div>


                <div>

                  <h3>

                    {verified
                      ? selfHealed
                        ? "Data successfully recovered"
                        : "Data appears reliable"
                      : failed
                        ? "Extraction could not be verified"
                        : "Extraction requires attention"}

                  </h3>


                  <p>

                    {analysis.explanation ||
                      "No AI explanation was returned."}

                  </p>

                </div>

              </div>


              {/* ISSUES */}

              {analysis.issues?.length > 0 && (

                <div className="issues-section">

                  <h3>
                    Detected anomalies
                  </h3>


                  <div className="issues-list">

                    {analysis.issues.map(
                      (issue, index) => (

                        <div
                          className="issue-item"
                          key={index}
                        >

                          <span className="issue-number">
                            {index + 1}
                          </span>

                          <span>
                            {issue}
                          </span>

                        </div>

                      )
                    )}

                  </div>

                </div>

              )}


              {/* REPAIR */}

              {analysis.repair_instruction && (

                <div className="repair-strategy">

                  <div className="repair-heading">
                    🔧 Repair Strategy
                  </div>

                  <p>
                    {analysis.repair_instruction}
                  </p>

                </div>

              )}

            </section>


            {/* =================================================
                HISTORY
            ================================================= */}

            <section className="main-card">

              <div className="section-label">
                AUDIT TRAIL
              </div>

              <h2>
                Recovery History
              </h2>

              <p className="section-description">
                A transparent record of every action
                performed by the extraction pipeline.
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


                      <div className="history-info">

                        <strong>
                          {formatAction(
                            item.action
                          )}
                        </strong>


                        {item.issues?.length > 0 && (

                          <div className="history-issues">

                            {item.issues.map(
                              (issue, i) => (

                                <span key={i}>
                                  {issue}
                                </span>

                              )
                            )}

                          </div>

                        )}

                      </div>


                      <div
                        className={
                          item.status === "failed"
                            ? "history-failed"
                            : "history-status"
                        }
                      >

                        {item.status === "failed"
                          ? "✕"
                          : "✓"}

                      </div>

                    </div>

                  )
                )}

              </div>

            </section>


            {/* =================================================
                FINAL DATA
            ================================================= */}

            <section className="main-card">

              <div className="section-label">
                VERIFIED OUTPUT
              </div>

              <h2>
                📦 Extracted Data
              </h2>

              <p className="section-description">
                The final data returned by the extraction
                pipeline.
              </p>


              <pre className="json-output">

                {JSON.stringify(
                  result.final_data,
                  null,
                  2
                )}

              </pre>

            </section>

          </>

        )}

      </main>


      {/* FOOTER */}

      <footer>

        <div>

          <strong>
            ScrapeHeal AI
          </strong>

          <span>
            Autonomous web data reliability
          </span>

        </div>


        <div>
          Powered by
          <strong>
            {" "}Bright Data + Gemini AI
          </strong>
        </div>

      </footer>

    </div>
  );
}


/* =========================================================
   COMPONENTS
========================================================= */

function Metric({
  icon,
  title,
  value,
}) {

  return (

    <div className="metric-card">

      <div className="metric-icon">
        {icon}
      </div>

      <div className="metric-info">

        <span>
          {title}
        </span>

        <strong>
          {value}
        </strong>

      </div>

    </div>

  );
}


function PipelineStep({
  number,
  title,
  subtitle,
}) {

  return (

    <div className="pipeline-step active">

      <span>
        {number}
      </span>

      <strong>
        {title}
      </strong>

      <small>
        {subtitle}
      </small>

    </div>

  );
}


/* =========================================================
   HELPERS
========================================================= */

function capitalize(value) {

  if (!value) {
    return "";
  }

  return (
    value.charAt(0).toUpperCase() +
    value.slice(1)
  );
}


function formatAction(action) {

  if (!action) {
    return "Processing step";
  }

  return action
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) =>
      letter.toUpperCase()
    );
}


export default App;