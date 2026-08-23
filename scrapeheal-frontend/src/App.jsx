import { useState } from "react";

const apiUrl = import.meta.env.VITE_API_URL || "";
const DEFAULT_URL = "https://books.toscrape.com/";

/* =========================================================
   URL CLEANING & VALIDATION
========================================================= */

function cleanUrl(value) {
  if (!value) return "";
  let cleaned = String(value);
  cleaned = cleaned.replace(/\s+/g, "");
  cleaned = cleaned.replace(/[\u0000-\u001F\u007F]/g, "");
  cleaned = cleaned.replace(/^["']+|["']+$/g, "");
  return cleaned.trim();
}

function validateUrl(value) {
  try {
    const parsed = new URL(value);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

function formatText(value) {
  if (!value) return "Unknown";
  return String(value)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

/* =========================================================
   MAIN APP
========================================================= */

export default function App() {
  const [url, setUrl] = useState(DEFAULT_URL);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const handleUrlChange = (event) => {
    const value = event.target.value;
    let cleaned = value
      .replace(/[\s\n\r\t]+/g, "")
      .replace(/[\u0000-\u001F\u007F]/g, "");

    setUrl(cleaned);

    if (error) {
      setError("");
    }
  };

  const handleAnalyze = async () => {
    setError("");
    setResult(null);

    const targetUrl = cleanUrl(url);

    if (!targetUrl) {
      setError("Please enter a website URL.");
      return;
    }

    if (!validateUrl(targetUrl)) {
      setError("Please enter a valid URL beginning with http:// or https://");
      return;
    }

    setLoading(true);

    try {
      const backendUrl = apiUrl.replace(/\/+$/, "");
      const endpoint = `${backendUrl}/self-heal`;

      const response = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({ url: targetUrl }),
      });

      const contentType = response.headers.get("content-type") || "";
      let data;

      if (contentType.includes("application/json")) {
        data = await response.json();
      } else {
        const text = await response.text();
        throw new Error(text || `Backend returned HTTP ${response.status}`);
      }

      if (!response.ok) {
        let message = `Request failed with status ${response.status}.`;
        if (typeof data?.detail === "string") {
          message = data.detail;
        } else if (data?.detail && typeof data.detail === "object") {
          message =
            data.detail.error ||
            data.detail.message ||
            JSON.stringify(data.detail);
        } else if (data?.error) {
          message = data.error;
        }
        throw new Error(message);
      }

      setResult(data);
    } catch (err) {
      console.error("ScrapeHeal error:", err);
      setError(err?.message || "Failed to connect to ScrapeHeal backend.");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !loading) {
      event.preventDefault();
      handleAnalyze();
    }
  };

  const analysis = result?.analysis || {};
  const history = Array.isArray(result?.history) ? result.history : [];
  const confidence = typeof analysis.confidence === "number" ? analysis.confidence : 0;
  const risk = formatText(analysis.risk_level);
  const action = formatText(analysis.recommended_action || result?.action || "Completed");
  const issues = Array.isArray(analysis.issues) ? analysis.issues : [];
  const isValid = analysis.is_valid === true;
  const isSelfHealed = result?.status === "self_healed";

  // Extracted raw JSON dataset returned by Bright Data scraper
  const extractedData = result?.data || result?.extracted_data || result?.items || result;

  const statusLabel = isSelfHealed
    ? "SELF-HEALED"
    : isValid
      ? "VERIFIED"
      : result
        ? "REVIEW"
        : "";

  return (
    <div className="app">
      <style>{`
        * { box-sizing: border-box; }
        html { scroll-behavior: smooth; }
        body {
          margin: 0;
          font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          color: #101828;
          background: linear-gradient(135deg, #f8f9ff 0%, #eef3ff 100%);
        }
        button, input { font: inherit; }
        .app { min-height: 100vh; }
        .header {
          height: 78px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0 7%;
          background: rgba(255,255,255,.96);
          border-bottom: 1px solid #e4e7ec;
        }
        .brand { display: flex; align-items: center; gap: 12px; }
        .brand-icon {
          width: 42px; height: 42px; display: grid; place-items: center;
          border-radius: 13px; background: linear-gradient(135deg, #6747ee, #5034d5);
          color: white; font-size: 21px;
        }
        .brand-name { font-size: 21px; font-weight: 800; }
        .brand-subtitle { color: #667085; font-size: 13px; margin-top: 2px; }
        .online { display: flex; align-items: center; gap: 8px; color: #087443; font-size: 13px; font-weight: 700; }
        .online-dot { width: 9px; height: 9px; border-radius: 50%; background: #12b76a; }
        .hero {
          max-width: 1200px; margin: auto; min-height: 370px;
          padding: 70px 35px; display: grid; grid-template-columns: 1fr 400px;
          align-items: center; gap: 40px;
        }
        .eyebrow { color: #6246e8; font-size: 12px; font-weight: 800; letter-spacing: 3px; margin-bottom: 15px; }
        .hero h1 { margin: 0; font-size: clamp(42px, 5vw, 64px); line-height: 1.02; letter-spacing: -2px; }
        .hero-description { max-width: 700px; color: #667085; font-size: 19px; line-height: 1.6; margin: 25px 0; }
        .technologies { display: flex; gap: 10px; flex-wrap: wrap; }
        .technology { padding: 9px 15px; border: 1px solid #d9e1f2; background: white; border-radius: 999px; font-size: 13px; font-weight: 700; color: #344054; }
        .visual { height: 320px; position: relative; display: grid; place-items: center; }
        .circle { width: 230px; height: 230px; border-radius: 50%; display: grid; place-items: center; background: linear-gradient(135deg, #6950ed, #533ddc); box-shadow: 0 35px 80px rgba(88,68,225,.25); }
        .shield { width: 90px; height: 90px; border-radius: 22px; display: grid; place-items: center; background: white; font-size: 36px; box-shadow: 0 15px 35px rgba(16,24,40,.15); }
        .floating { position: absolute; padding: 13px 18px; border-radius: 15px; background: white; border: 1px solid #e4e7ec; box-shadow: 0 15px 35px rgba(16,24,40,.10); font-weight: 750; }
        .detect { top: 20px; left: 0; }
        .diagnose { top: 100px; right: 0; }
        .repair { bottom: 20px; left: 30px; }
        .container { max-width: 1200px; margin: auto; padding: 0 35px 70px; }
        .card { background: white; border: 1px solid #e1e7f0; border-radius: 25px; padding: 40px; box-shadow: 0 18px 50px rgba(16,24,40,.06); margin-bottom: 25px; }
        .label { color: #6246e8; font-size: 12px; font-weight: 800; letter-spacing: 3px; margin-bottom: 14px; }
        .card h2 { margin: 0 0 12px; font-size: 32px; letter-spacing: -.8px; }
        .description { color: #667085; font-size: 17px; margin-bottom: 27px; }
        .url-row { width: 100%; min-height: 76px; display: flex; align-items: center; gap: 12px; padding: 7px; border: 1px solid #d5def0; border-radius: 18px; background: #f9fbff; }
        .globe { font-size: 27px; margin-left: 15px; }
        .url-input { flex: 1; min-width: 0; border: none; outline: none; background: transparent; padding: 15px 5px; font-size: 17px; color: #101828; }
        .analyze { min-width: 155px; height: 60px; border: none; border-radius: 14px; color: white; background: linear-gradient(135deg, #6847ee, #5435d8); font-weight: 800; font-size: 16px; cursor: pointer; box-shadow: 0 10px 25px rgba(84,53,216,.25); }
        .analyze:hover { transform: translateY(-1px); }
        .analyze:disabled { opacity: .65; cursor: not-allowed; }
        .error { margin-top: 20px; padding: 17px 20px; border: 1px solid #fecaca; border-radius: 15px; background: #fff5f5; color: #c5221f; font-size: 15px; line-height: 1.5; }
        .working { text-align: center; padding: 45px 30px; }
        .spinner { width: 48px; height: 48px; margin: 0 auto 18px; border: 4px solid #e4e7ec; border-top-color: #6246e8; border-radius: 50%; animation: spin .8s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .pipeline { display: grid; grid-template-columns: repeat(4,1fr); gap: 15px; margin-top: 30px; }
        .pipeline-step { padding: 20px; border: 1px solid #eaecf0; border-radius: 16px; background: #fafbff; }
        .pipeline-number { width: 38px; height: 38px; margin: 0 auto 10px; display: grid; place-items: center; border-radius: 50%; background: #6246e8; color: white; font-weight: 800; }
        .pipeline-step strong { display: block; font-size: 14px; }
        .pipeline-step span { display: block; margin-top: 5px; color: #667085; font-size: 13px; }
        .result-header { display: flex; justify-content: space-between; gap: 20px; }
        .result-title { margin: 0 0 7px; font-size: 31px; font-weight: 800; }
        .result-url { color: #667085; word-break: break-all; }
        .status { height: fit-content; padding: 12px 18px; border-radius: 999px; font-size: 12px; font-weight: 900; }
        .status-success { background: #ecfdf3; color: #087443; }
        .status-review { background: #fff1f3; color: #b42318; }
        .stats { display: grid; grid-template-columns: repeat(4,1fr); gap: 18px; margin-bottom: 25px; }
        .stat { padding: 24px; background: white; border: 1px solid #e4e7ec; border-radius: 20px; box-shadow: 0 12px 35px rgba(16,24,40,.05); }
        .stat-icon { width: 42px; height: 42px; display: grid; place-items: center; border-radius: 12px; background: #eeeaff; margin-bottom: 13px; }
        .stat-label { color: #667085; font-size: 13px; }
        .stat-value { margin-top: 5px; font-size: 24px; font-weight: 850; }
        .analysis { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .analysis-box { padding: 25px; border: 1px solid #eaecf0; border-radius: 18px; background: #fcfcfd; }
        .analysis-box h3 { margin: 0 0 12px; font-size: 18px; }
        .analysis-box p { margin: 0; color: #475467; line-height: 1.6; }
        .issues { margin: 0; padding-left: 20px; color: #475467; line-height: 1.7; }
        .no-issues { color: #087443; font-weight: 700; }
        .json-container {
          background: #0f172a;
          border: 1px solid #1e293b;
          border-radius: 16px;
          padding: 24px;
          max-height: 480px;
          overflow-y: auto;
          color: #e2e8f0;
          font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
          font-size: 14px;
          line-height: 1.6;
          text-align: left;
        }
        .json-container pre {
          margin: 0;
          white-space: pre-wrap;
          word-break: break-all;
        }
        .history-row { display: grid; grid-template-columns: 45px 1fr auto; align-items: center; gap: 15px; padding: 17px 0; border-bottom: 1px solid #eaecf0; }
        .history-row:last-child { border-bottom: none; }
        .history-number { width: 34px; height: 34px; display: grid; place-items: center; border-radius: 10px; background: #eeeaff; color: #573de0; font-weight: 800; }
        .history-title { font-weight: 700; }
        .history-status { color: #079455; font-size: 12px; font-weight: 800; text-transform: uppercase; }
        @media (max-width: 850px) {
          .hero { grid-template-columns: 1fr; }
          .visual { display: none; }
          .pipeline, .stats { grid-template-columns: 1fr 1fr; }
          .analysis { grid-template-columns: 1fr; }
        }
        @media (max-width: 600px) {
          .header { padding: 0 20px; }
          .online { display: none; }
          .hero { padding: 50px 20px; }
          .container { padding: 0 15px 50px; }
          .card { padding: 25px; }
          .url-row { flex-wrap: wrap; padding: 10px; }
          .url-input { width: 70%; }
          .analyze { width: 100%; }
          .pipeline, .stats { grid-template-columns: 1fr; }
          .result-header { flex-direction: column; }
        }
      `}</style>

      <header className="header">
        <div className="brand">
          <div className="brand-icon">🛡️</div>
          <div>
            <div className="brand-name">ScrapeHeal AI</div>
            <div className="brand-subtitle">Self-healing web extraction</div>
          </div>
        </div>
        <div className="online">
          <span className="online-dot" />
          SYSTEM ONLINE
        </div>
      </header>

      <section className="hero">
        <div>
          <div className="eyebrow">AUTONOMOUS WEB DATA RELIABILITY</div>
          <h1>Web extraction<br />that heals itself.</h1>
          <p className="hero-description">
            Detect extraction anomalies, diagnose them with AI, recover the extraction workflow, and verify the recovered data.
          </p>
          <div className="technologies">
            <span className="technology">Bright Data</span>
            <span className="technology">Gemini AI</span>
            <span className="technology">FastAPI</span>
            <span className="technology">React</span>
          </div>
        </div>
        <div className="visual">
          <div className="floating detect">🔎 Detect</div>
          <div className="floating diagnose">🤖 Diagnose</div>
          <div className="floating repair">🔧 Repair</div>
          <div className="circle">
            <div className="shield">🛡️</div>
          </div>
        </div>
      </section>

      <main className="container">
        <section className="card">
          <div className="label">EXTRACTION CONTROL</div>
          <h2>Analyze a public website</h2>
          <p className="description">Enter a public website and let ScrapeHeal extract and validate its data.</p>
          <div className="url-row">
            <span className="globe">🌐</span>
            <input
              className="url-input"
              type="text"
              value={url}
              onChange={handleUrlChange}
              onKeyDown={handleKeyDown}
              placeholder="https://example.com"
              disabled={loading}
              spellCheck={false}
              autoComplete="off"
            />
            <button className="analyze" onClick={handleAnalyze} disabled={loading}>
              {loading ? "Analyzing..." : "🚀 Analyze"}
            </button>
          </div>
          {error && <div className="error">⚠️ {error}</div>}
        </section>

        {loading && (
          <section className="card working">
            <div className="spinner" />
            <h2>ScrapeHeal is working...</h2>
            <p className="description">Running extraction, AI diagnosis, repair and verification.</p>
            <div className="pipeline">
              <div className="pipeline-step">
                <div className="pipeline-number">1</div>
                <strong>Bright Data</strong>
                <span>Extract</span>
              </div>
              <div className="pipeline-step">
                <div className="pipeline-number">2</div>
                <strong>Gemini AI</strong>
                <span>Diagnose</span>
              </div>
              <div className="pipeline-step">
                <div className="pipeline-number">3</div>
                <strong>Repair</strong>
                <span>Recover</span>
              </div>
              <div className="pipeline-step">
                <div className="pipeline-number">4</div>
                <strong>Verify</strong>
                <span>Trust</span>
              </div>
            </div>
          </section>
        )}

        {result && !loading && (
          <>
            <section className="card">
              <div className="result-header">
                <div>
                  <div className="label">SCRAPING RESULT</div>
                  <h2 className="result-title">
                    {isSelfHealed ? "Extraction self-healed" : isValid ? "Extraction verified" : "Extraction requires review"}
                  </h2>
                  <div className="result-url">{cleanUrl(result.url || url)}</div>
                </div>
                <div className={isValid ? "status status-success" : "status status-review"}>
                  {isValid ? "✓ " : "⚠ "}{statusLabel}
                </div>
              </div>
            </section>

            <div className="stats">
              <div className="stat">
                <div className="stat-icon">🔄</div>
                <div className="stat-label">Pipeline Steps</div>
                <div className="stat-value">{history.length}</div>
              </div>
              <div className="stat">
                <div className="stat-icon">🎯</div>
                <div className="stat-label">Confidence</div>
                <div className="stat-value">{confidence}%</div>
              </div>
              <div className="stat">
                <div className="stat-icon">🛡️</div>
                <div className="stat-label">Risk</div>
                <div className="stat-value">{risk}</div>
              </div>
              <div className="stat">
                <div className="stat-icon">⚡</div>
                <div className="stat-label">Action</div>
                <div className="stat-value">{action}</div>
              </div>
            </div>

            {/* EXTRACTED DATA CARD (DARK JSON VIEWER) */}
            <section className="card">
              <div className="label">📦 EXTRACTED DATA</div>
              <p className="description">The final data returned by the extraction pipeline.</p>
              <div className="json-container">
                <pre>
                  <code>{JSON.stringify(extractedData, null, 2)}</code>
                </pre>
              </div>
            </section>

            <section className="card">
              <div className="label">AI VALIDATION</div>
              <div className="analysis">
                <div className="analysis-box">
                  <h3>Diagnosis</h3>
                  <p>{analysis.explanation || "The AI validation engine completed the analysis."}</p>
                </div>
                <div className="analysis-box">
                  <h3>Issues detected</h3>
                  {issues.length > 0 ? (
                    <ul className="issues">
                      {issues.map((issue, index) => (
                        <li key={index}>{String(issue)}</li>
                      ))}
                    </ul>
                  ) : (
                    <div className="no-issues">✓ No extraction anomalies detected.</div>
                  )}
                </div>
              </div>

              {analysis.repair_instruction && (
                <div className="analysis-box" style={{ marginTop: "20px" }}>
                  <h3>Repair strategy</h3>
                  <p>{analysis.repair_instruction}</p>
                </div>
              )}
            </section>

            {history.length > 0 && (
              <section className="card">
                <div className="label">EXECUTION PIPELINE</div>
                <h2>What ScrapeHeal did</h2>
                {history.map((step, index) => (
                  <div className="history-row" key={index}>
                    <div className="history-number">{step.step || index + 1}</div>
                    <div>
                      <div className="history-title">
                        {formatText(step.action || "Pipeline Step")}
                      </div>
                      {step.issues && Array.isArray(step.issues) && step.issues.length > 0 && (
                        <div style={{ color: "#667085", fontSize: "13px", marginTop: "4px" }}>
                          {step.issues.join(", ")}
                        </div>
                      )}
                    </div>
                    <div className="history-status">{step.status || "COMPLETED"}</div>
                  </div>
                ))}
              </section>
            )}
          </>
        )}
      </main>
    </div>
  );
}