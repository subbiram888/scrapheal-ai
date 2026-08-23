import { useState } from "react";

const API_URL =
  import.meta.env.VITE_API_URL ||
  "https://scrapheal-ai-backend.vercel.app";

const DEFAULT_URL = "https://books.toscrape.com/";

function formatAction(action = "") {
  return action
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function getStatus(result) {
  if (!result) return null;

  const valid = result.analysis?.is_valid === true;

  if (
    valid &&
    (result.status === "success" ||
      result.status === "self_healed")
  ) {
    return {
      label: result.status === "self_healed"
        ? "SELF-HEALED"
        : "VERIFIED",
      className: "success",
    };
  }

  return {
    label: "REVIEW",
    className: "review",
  };
}

export default function App() {
  const [url, setUrl] = useState(DEFAULT_URL);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const analyzeWebsite = async () => {
    const targetUrl = url.trim();

    if (!targetUrl) {
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
          url: targetUrl,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        const detail =
          typeof data.detail === "object"
            ? data.detail?.error
            : data.detail;

        throw new Error(
          detail || data.error || `Request failed with ${response.status}`
        );
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

  const status = getStatus(result);

  const analysis = result?.analysis || {};
  const history = result?.history || [];

  const confidence =
    typeof analysis.confidence === "number"
      ? analysis.confidence
      : 0;

  const risk =
    analysis.risk_level
      ? analysis.risk_level.charAt(0).toUpperCase() +
        analysis.risk_level.slice(1)
      : "Unknown";

  const action =
    analysis.recommended_action || "review";

  return (
    <div className="app">
      <style>{`
        * {
          box-sizing: border-box;
        }

        body {
          margin: 0;
          font-family:
            Inter,
            ui-sans-serif,
            system-ui,
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            sans-serif;
          background:
            linear-gradient(135deg, #f7f8ff 0%, #eef3ff 100%);
          color: #101828;
        }

        button,
        input {
          font: inherit;
        }

        .app {
          min-height: 100vh;
        }

        .topbar {
          height: 76px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 7%;
          background: rgba(255,255,255,.92);
          border-bottom: 1px solid #e4e7ec;
        }

        .brand {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .brand-icon {
          width: 42px;
          height: 42px;
          border-radius: 13px;
          display: grid;
          place-items: center;
          background: linear-gradient(135deg,#6046e8,#3f2dcc);
          color: white;
          font-size: 21px;
        }

        .brand-title {
          font-size: 21px;
          font-weight: 800;
        }

        .brand-subtitle {
          font-size: 13px;
          color: #667085;
          margin-top: 2px;
        }

        .online {
          display: flex;
          align-items: center;
          gap: 8px;
          color: #087443;
          font-size: 13px;
          font-weight: 700;
          background: #ecfdf3;
          padding: 9px 14px;
          border-radius: 999px;
        }

        .online-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #12b76a;
        }

        .hero {
          max-width: 1180px;
          margin: 0 auto;
          padding: 70px 28px 55px;
          display: grid;
          grid-template-columns: 1fr 380px;
          gap: 50px;
          align-items: center;
        }

        .eyebrow {
          color: #6246e8;
          font-size: 12px;
          font-weight: 800;
          letter-spacing: 3px;
          margin-bottom: 15px;
        }

        .hero h1 {
          font-size: clamp(40px,5vw,62px);
          line-height: 1.02;
          margin: 0;
          max-width: 650px;
          letter-spacing: -2px;
        }

        .hero p {
          color: #667085;
          font-size: 18px;
          line-height: 1.65;
          max-width: 680px;
          margin: 24px 0;
        }

        .tech {
          display: flex;
          flex-wrap: wrap;
          gap: 9px;
        }

        .tech span {
          background: white;
          border: 1px solid #d9def0;
          padding: 8px 13px;
          border-radius: 999px;
          font-size: 13px;
          font-weight: 700;
          color: #344054;
        }

        .hero-visual {
          position: relative;
          height: 310px;
          display: grid;
          place-items: center;
        }

        .core {
          width: 220px;
          height: 220px;
          border-radius: 50%;
          background: linear-gradient(145deg,#6754f3,#4d36dc);
          display: grid;
          place-items: center;
          box-shadow: 0 30px 70px rgba(83,65,225,.25);
        }

        .core-inner {
          width: 92px;
          height: 92px;
          background: white;
          border-radius: 28px;
          display: grid;
          place-items: center;
          font-size: 38px;
          box-shadow: 0 15px 30px rgba(0,0,0,.12);
        }

        .floating {
          position: absolute;
          background: white;
          border: 1px solid #e4e7ec;
          padding: 13px 17px;
          border-radius: 14px;
          font-weight: 700;
          box-shadow: 0 15px 35px rgba(16,24,40,.09);
        }

        .float-one {
          top: 25px;
          left: 5px;
        }

        .float-two {
          right: 0;
          top: 90px;
        }

        .float-three {
          bottom: 25px;
          left: 30px;
        }

        .container {
          max-width: 1180px;
          margin: 0 auto;
          padding: 0 28px 70px;
        }

        .card {
          background: white;
          border: 1px solid #e4e7ec;
          border-radius: 25px;
          padding: 38px;
          box-shadow: 0 15px 45px rgba(16,24,40,.06);
          margin-bottom: 25px;
        }

        .section-label {
          color: #6246e8;
          font-size: 12px;
          font-weight: 800;
          letter-spacing: 3px;
          margin-bottom: 12px;
        }

        .card h2 {
          margin: 0 0 10px;
          font-size: 31px;
          letter-spacing: -.8px;
        }

        .muted {
          color: #667085;
          margin: 0 0 25px;
        }

        .url-row {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 7px;
          background: #f8faff;
          border: 1px solid #d9e1f2;
          border-radius: 17px;
        }

        .globe {
          font-size: 24px;
          margin-left: 12px;
        }

        .url-input {
          flex: 1;
          min-width: 0;
          border: none;
          outline: none;
          background: transparent;
          padding: 15px 5px;
          color: #101828;
          font-size: 16px;
        }

        .analyze-btn {
          border: none;
          background: linear-gradient(135deg,#6747ee,#5134d7);
          color: white;
          padding: 15px 27px;
          border-radius: 13px;
          font-weight: 800;
          cursor: pointer;
          min-width: 125px;
          box-shadow: 0 10px 25px rgba(83,57,220,.22);
        }

        .analyze-btn:disabled {
          opacity: .65;
          cursor: not-allowed;
        }

        .error {
          margin-top: 18px;
          padding: 14px 16px;
          border-radius: 12px;
          background: #fff1f3;
          border: 1px solid #fecdd3;
          color: #b42318;
          font-size: 14px;
        }

        .working {
          text-align: center;
          padding: 45px 20px;
        }

        .spinner {
          width: 48px;
          height: 48px;
          margin: 0 auto 18px;
          border-radius: 50%;
          border: 4px solid #e4e0ff;
          border-top-color: #6046e8;
          animation: spin .8s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        .working h2 {
          margin-bottom: 8px;
        }

        .working p {
          color: #667085;
        }

        .pipeline {
          display: grid;
          grid-template-columns: repeat(4,1fr);
          gap: 15px;
          margin-top: 30px;
        }

        .pipeline-step {
          padding: 22px;
          border: 1px solid #e4e7ec;
          border-radius: 16px;
          background: #fafbff;
        }

        .number {
          width: 35px;
          height: 35px;
          display: grid;
          place-items: center;
          background: #eeeaff;
          color: #573de0;
          border-radius: 10px;
          font-weight: 800;
          margin-bottom: 12px;
        }

        .pipeline-step strong {
          display: block;
          margin-bottom: 5px;
        }

        .pipeline-step small {
          color: #667085;
        }

        .result-header {
          display: flex;
          justify-content: space-between;
          gap: 20px;
          align-items: center;
        }

        .result-url {
          color: #667085;
          word-break: break-all;
        }

        .badge {
          padding: 11px 18px;
          border-radius: 999px;
          font-weight: 800;
          font-size: 13px;
          white-space: nowrap;
        }

        .badge.success {
          background: #ecfdf3;
          color: #067647;
        }

        .badge.review {
          background: #fff1f3;
          color: #b42318;
        }

        .stats {
          display: grid;
          grid-template-columns: repeat(4,1fr);
          gap: 16px;
          margin-top: 22px;
        }

        .stat {
          border: 1px solid #e4e7ec;
          border-radius: 18px;
          padding: 22px;
          background: white;
        }

        .stat-label {
          color: #667085;
          font-size: 13px;
          margin-bottom: 8px;
        }

        .stat-value {
          font-size: 24px;
          font-weight: 800;
        }

        .analysis {
          margin-top: 25px;
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 18px;
        }

        .analysis-box {
          padding: 22px;
          border-radius: 17px;
          background: #f8f9fd;
          border: 1px solid #e4e7ec;
        }

        .analysis-box h3 {
          margin: 0 0 10px;
          font-size: 16px;
        }

        .analysis-box p {
          margin: 0;
          color: #667085;
          line-height: 1.6;
        }

        .issues {
          margin: 0;
          padding-left: 20px;
          color: #667085;
        }

        .issues li {
          margin-bottom: 7px;
        }

        .history {
          margin-top: 25px;
        }

        .history-row {
          display: grid;
          grid-template-columns: 45px 1fr auto;
          gap: 15px;
          align-items: center;
          padding: 17px 0;
          border-bottom: 1px solid #eaecf0;
        }

        .history-row:last-child {
          border-bottom: none;
        }

        .history-number {
          width: 34px;
          height: 34px;
          border-radius: 10px;
          display: grid;
          place-items: center;
          background: #eeeaff;
          color: #573de0;
          font-weight: 800;
        }

        .history-title {
          font-weight: 700;
        }

        .history-status {
          font-size: 12px;
          font-weight: 800;
          text-transform: uppercase;
        }

        .completed {
          color: #079455;
        }

        .failed {
          color: #d92d20;
        }

        .detected {
          color: #b54708;
        }

        .data-box {
          margin-top: 25px;
        }

        .data-preview {
          max-height: 350px;
          overflow: auto;
          background: #101828;
          color: #d0d5dd;
          padding: 20px;
          border-radius: 15px;
          font-size: 13px;
          line-height: 1.55;
          white-space: pre-wrap;
          word-break: break-word;
        }

        @media (max-width: 850px) {
          .hero {
            grid-template-columns: 1fr;
          }

          .hero-visual {
            display: none;
          }

          .pipeline,
          .stats {
            grid-template-columns: 1fr 1fr;
          }

          .analysis {
            grid-template-columns: 1fr;
          }

          .url-row {
            flex-wrap: wrap;
          }

          .url-input {
            flex-basis: 70%;
          }

          .analyze-btn {
            width: 100%;
          }
        }

        @media (max-width: 560px) {
          .topbar {
            padding: 0 20px;
          }

          .online {
            display: none;
          }

          .hero {
            padding-top: 45px;
          }

          .card {
            padding: 24px;
          }

          .pipeline,
          .stats {
            grid-template-columns: 1fr;
          }
        }
      `}</style>

      {/* HEADER */}
      <header className="topbar">
        <div className="brand">
          <div className="brand-icon">🛡️</div>

          <div>
            <div className="brand-title">
              ScrapeHeal AI
            </div>

            <div className="brand-subtitle">
              Self-healing web extraction
            </div>
          </div>
        </div>

        <div className="online">
          <span className="online-dot" />
          SYSTEM ONLINE
        </div>
      </header>

      {/* HERO */}
      <section className="hero">
        <div>
          <div className="eyebrow">
            AUTONOMOUS WEB DATA RELIABILITY
          </div>

          <h1>
            Web extraction
            <br />
            that heals itself.
          </h1>

          <p>
            Detect extraction anomalies, diagnose them with AI,
            recover the extraction workflow, and verify the
            recovered data.
          </p>

          <div className="tech">
            <span>Bright Data</span>
            <span>Gemini AI</span>
            <span>FastAPI</span>
            <span>React</span>
          </div>
        </div>

        <div className="hero-visual">
          <div className="floating float-one">
            🔎 Detect
          </div>

          <div className="floating float-two">
            🤖 Diagnose
          </div>

          <div className="floating float-three">
            🔧 Repair
          </div>

          <div className="core">
            <div className="core-inner">
              ✓
            </div>
          </div>
        </div>
      </section>

      <main className="container">

        {/* EXTRACTION CONTROL */}
        <section className="card">
          <div className="section-label">
            EXTRACTION CONTROL
          </div>

          <h2>Analyze a public website</h2>

          <p className="muted">
            Enter a public website and let ScrapeHeal extract
            and validate its data.
          </p>

          <div className="url-row">
            <span className="globe">🌐</span>

            <input
              className="url-input"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !loading) {
                  analyzeWebsite();
                }
              }}
              placeholder="https://example.com"
              disabled={loading}
            />

            <button
              className="analyze-btn"
              onClick={analyzeWebsite}
              disabled={loading}
            >
              {loading ? "Analyzing..." : "🚀 Analyze"}
            </button>
          </div>

          {error && (
            <div className="error">
              ⚠️ {error}
            </div>
          )}
        </section>

        {/* LOADING */}
        {loading && (
          <section className="card working">
            <div className="spinner" />

            <h2>ScrapeHeal is working...</h2>

            <p>
              Running extraction, AI diagnosis, repair and
              verification.
            </p>

            <div className="pipeline">
              <div className="pipeline-step">
                <div className="number">1</div>
                <strong>Bright Data</strong>
                <small>Extract</small>
              </div>

              <div className="pipeline-step">
                <div className="number">2</div>
                <strong>Gemini AI</strong>
                <small>Diagnose</small>
              </div>

              <div className="pipeline-step">
                <div className="number">3</div>
                <strong>Repair</strong>
                <small>Recover</small>
              </div>

              <div className="pipeline-step">
                <div className="number">4</div>
                <strong>Verify</strong>
                <small>Trust</small>
              </div>
            </div>
          </section>
        )}

        {/* RESULT */}
        {result && !loading && (
          <>
            <section className="card">
              <div className="section-label">
                SCRAPING RESULT
              </div>

              <div className="result-header">
                <div>
                  <h2>
                    {status?.label === "VERIFIED"
                      ? "Extraction verified"
                      : status?.label === "SELF-HEALED"
                      ? "Extraction self-healed"
                      : "Extraction requires review"}
                  </h2>

                  <div className="result-url">
                    {result.url || url}
                  </div>
                </div>

                <div
                  className={`badge ${status?.className}`}
                >
                  {status?.className === "success"
                    ? "✓ "
                    : "✕ "}
                  {status?.label}
                </div>
              </div>
            </section>

            {/* STATS */}
            <section className="stats">
              <div className="stat">
                <div className="stat-label">
                  Pipeline Events
                </div>

                <div className="stat-value">
                  {history.length}
                </div>
              </div>

              <div className="stat">
                <div className="stat-label">
                  Confidence
                </div>

                <div className="stat-value">
                  {confidence}%
                </div>
              </div>

              <div className="stat">
                <div className="stat-label">
                  Risk
                </div>

                <div className="stat-value">
                  {risk}
                </div>
              </div>

              <div className="stat">
                <div className="stat-label">
                  Action
                </div>

                <div className="stat-value">
                  {formatAction(action)}
                </div>
              </div>
            </section>

            {/* AI ANALYSIS */}
            <section className="card" style={{ marginTop: 25 }}>
              <div className="section-label">
                AI DIAGNOSIS
              </div>

              <h2>Extraction analysis</h2>

              <div className="analysis">
                <div className="analysis-box">
                  <h3>Explanation</h3>

                  <p>
                    {analysis.explanation ||
                      "No additional explanation was returned."}
                  </p>
                </div>

                <div className="analysis-box">
                  <h3>Repair instruction</h3>

                  <p>
                    {analysis.repair_instruction ||
                      "No repair was required."}
                  </p>
                </div>
              </div>

              {analysis.issues &&
                analysis.issues.length > 0 && (
                  <div
                    className="analysis-box"
                    style={{ marginTop: 18 }}
                  >
                    <h3>Detected issues</h3>

                    <ul className="issues">
                      {analysis.issues.map(
                        (issue, index) => (
                          <li key={index}>{issue}</li>
                        )
                      )}
                    </ul>
                  </div>
                )}
            </section>

            {/* RECOVERY HISTORY */}
            <section className="card history">
              <div className="section-label">
                AUDIT TRAIL
              </div>

              <h2>Recovery History</h2>

              <p className="muted">
                Every important extraction and recovery event
                is recorded for transparency.
              </p>

              {history.length === 0 ? (
                <p className="muted">
                  No pipeline events returned.
                </p>
              ) : (
                history.map((item, index) => {
                  const itemStatus =
                    item.status || "completed";

                  return (
                    <div
                      className="history-row"
                      key={index}
                    >
                      <div className="history-number">
                        {item.step || index + 1}
                      </div>

                      <div>
                        <div className="history-title">
                          {formatAction(item.action)}
                        </div>

                        {item.issues?.length > 0 && (
                          <div
                            style={{
                              color: "#667085",
                              fontSize: 13,
                              marginTop: 4,
                            }}
                          >
                            {item.issues.join(", ")}
                          </div>
                        )}
                      </div>

                      <div
                        className={`history-status ${
                          itemStatus === "failed"
                            ? "failed"
                            : itemStatus === "detected"
                            ? "detected"
                            : "completed"
                        }`}
                      >
                        {itemStatus === "verified"
                          ? "✓ Verified"
                          : itemStatus === "failed"
                          ? "✕ Failed"
                          : itemStatus === "detected"
                          ? "⚠ Detected"
                          : "✓ Completed"}
                      </div>
                    </div>
                  );
                })
              )}
            </section>

            {/* FINAL DATA */}
            <section className="card data-box">
              <div className="section-label">
                EXTRACTED DATA
              </div>

              <h2>Recovered data</h2>

              <p className="muted">
                Data returned by the final extraction attempt.
              </p>

              <pre className="data-preview">
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
    </div>
  );
}