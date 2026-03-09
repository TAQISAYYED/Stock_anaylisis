import { useState } from "react";
import api from "../services/api";
import "./Forecasting.css";

const ALGORITHMS = [
  { key: "all",      label: "All 3",      desc: "Run all algorithms" },
  { key: "arima",    label: "ARIMA",      desc: "Classical time-series" },
  { key: "cnn_lstm", label: "CNN-LSTM",   desc: "Deep learning" },
  { key: "linear",   label: "Linear Reg", desc: "Ridge regression" },
];

const HORIZONS = [
  { value: 7,  label: "7D",  desc: "1 Week" },
  { value: 30, label: "30D", desc: "1 Month" },
  { value: 90, label: "90D", desc: "3 Months" },
];

const QUICK_TICKERS = [
  "BTC-USD", "ETH-USD", "AAPL", "MSFT", "GOOGL",
  "TSLA", "NVDA", "RELIANCE.NS", "TCS.NS", "INFY.NS",
  "HDFCBANK.NS", "NIFTY50.NS",
];

const CHART_TABS = [
  { key: "combined",        label: "All Forecasts" },
  { key: "test_vs_actual",  label: "Test vs Actual" },
  { key: "algo_comparison", label: "Per Algorithm" },
  { key: "metrics_bar",     label: "Accuracy Chart" },
];

const ALGO_NAMES = { arima: "ARIMA", cnn_lstm: "CNN-LSTM", linear: "Linear Reg" };
const DOT_CLASS  = { arima: "fc-dot-arima", cnn_lstm: "fc-dot-cnn", linear: "fc-dot-linear" };
const CARD_CLASS = { arima: "card-arima",   cnn_lstm: "card-cnn",   linear: "card-linear" };

const fmt$ = v => v != null
  ? `$${Number(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  : "—";

const fmtN = (v, d = 2) => v != null ? Number(v).toFixed(d) : "—";

export default function Forecasting() {
  const [ticker,       setTicker]       = useState("BTC-USD");
  const [customTicker, setCustomTicker] = useState("");
  const [horizon,      setHorizon]      = useState(7);
  const [algorithm,    setAlgorithm]    = useState("all");
  const [loading,      setLoading]      = useState(false);
  const [error,        setError]        = useState("");
  const [result,       setResult]       = useState(null);
  const [activeChart,  setActiveChart]  = useState("combined");

  const effectiveTicker = (customTicker.trim() || ticker).toUpperCase();

  const runForecast = async () => {
    setLoading(true); setError(""); setResult(null); setActiveChart("combined");
    try {
      const res = await api.post("/api/Forecasting/forecast/", {
        ticker: effectiveTicker, horizon, algorithm,
      });
      setResult(res.data);
    } catch (err) {
      setError(
        err.response?.data?.error ||
        err.response?.data?.detail ||
        "Forecast failed. Check the ticker symbol and try again."
      );
    } finally { setLoading(false); }
  };

  const shownAlgos = result ? Object.keys(result.metrics || {}) : [];

  return (
    <div className="fc-page">

      {/* Header */}
      <div className="fc-header">
        <div className="fc-header-top">
          <h1>Price Forecasting</h1>
          <span className="fc-header-tag">ML Powered</span>
        </div>
        <p>
          Train on 60 days of hourly data · Forecast 7 / 30 / 90 days ahead ·
          ARIMA · CNN-LSTM · Linear Regression
        </p>
      </div>

      {/* Config */}
      <div className="fc-config-card">
        <p className="fc-config-title">Forecast Configuration</p>
        <div className="fc-config-grid">

          <div className="fc-field">
            <label className="fc-label">Ticker Symbol</label>
            <select
              className="fc-select"
              value={customTicker ? "__custom__" : ticker}
              onChange={e => { if (e.target.value === "__custom__") return; setTicker(e.target.value); setCustomTicker(""); }}
            >
              {QUICK_TICKERS.map(t => <option key={t} value={t}>{t}</option>)}
              <option disabled value="__custom__">── Custom below ──</option>
            </select>
            <input
              type="text"
              className="fc-input"
              style={{ marginTop: 6, height: 38 }}
              placeholder="Or type: NVDA, WIPRO.NS, SOL-USD…"
              value={customTicker}
              onChange={e => setCustomTicker(e.target.value)}
              onKeyDown={e => e.key === "Enter" && runForecast()}
            />
          </div>

          <div className="fc-algo-group">
            <label className="fc-label">Algorithm</label>
            <div className="fc-algo-pills">
              {ALGORITHMS.map(a => (
                <button
                  key={a.key}
                  className={`fc-algo-pill${algorithm === a.key ? ` active-${a.key}` : ""}`}
                  onClick={() => setAlgorithm(a.key)}
                  title={a.desc}
                >
                  {a.label}
                </button>
              ))}
            </div>
          </div>

          <div className="fc-horizon-group">
            <label className="fc-label">Forecast Horizon</label>
            <div className="fc-horizon-pills">
              {HORIZONS.map(h => (
                <button
                  key={h.value}
                  className={`fc-horizon-pill${horizon === h.value ? " active" : ""}`}
                  onClick={() => setHorizon(h.value)}
                  title={h.desc}
                >
                  {h.label}
                </button>
              ))}
            </div>
          </div>

          <button className="fc-run-btn" onClick={runForecast} disabled={loading}>
            {loading ? "Training…" : "Run Forecast"}
          </button>

        </div>
      </div>

      {error && <div className="fc-error"><span>⚠</span> {error}</div>}

      {loading && (
        <div className="fc-loading">
          <div className="fc-spinner" />
          <div className="fc-loading-title">Training models on {effectiveTicker}…</div>
          <div className="fc-loading-sub">
            Fetching 60 days hourly data → resampling to daily →
            training {algorithm === "all" ? "ARIMA + CNN-LSTM + Linear Reg" : ALGO_NAMES[algorithm] || algorithm}
            <br />CNN-LSTM may take 30–60 seconds
          </div>
        </div>
      )}

      {result && !loading && (
        <>
          {/* Summary cards */}
          <div className="fc-summary-bar">
            <div className="fc-summary-card card-current">
              <div className="fc-summary-algo">Current Price</div>
              <div className="fc-summary-price">{fmt$(result.summary?.current_price)}</div>
              <div className="fc-summary-algo" style={{ marginTop: 6 }}>{result.ticker} · Live</div>
            </div>
            {shownAlgos.map(algo => {
              const s = result.summary?.[algo];
              const isB = algo === result.best_model;
              return (
                <div className={`fc-summary-card ${CARD_CLASS[algo] || ""}`} key={algo}>
                  <div className="fc-summary-algo">{ALGO_NAMES[algo] || algo} · {result.horizon_days}d</div>
                  <div className="fc-summary-price">{fmt$(s?.end_price)}</div>
                  {s && (
                    <div className={`fc-summary-change ${s.direction === "UP" ? "fc-up" : "fc-down"}`}>
                      {s.direction === "UP" ? "▲" : "▼"}&nbsp;{Math.abs(s.change_pct).toFixed(2)}%
                    </div>
                  )}
                  {isB && <div className="fc-best-tag">★ Best MAPE</div>}
                </div>
              );
            })}
          </div>

          {result.algo_errors && Object.keys(result.algo_errors).length > 0 && (
            <div className="fc-warn">
              ⚠ &nbsp;
              {Object.entries(result.algo_errors).map(([k,v]) => `${ALGO_NAMES[k]||k}: ${v}`).join("  ·  ")}
            </div>
          )}

          {/* Charts */}
          <div className="fc-section">
            <div className="fc-section-header">
              <h3>Forecast Charts</h3>
              <span className="fc-chip fc-chip-green">{result.ticker}</span>
              <span className="fc-chip fc-chip-blue">{result.horizon_days}-Day Horizon</span>
              <span className="fc-chip fc-chip-gold">60 Days Training</span>
            </div>
            <div className="fc-chart-nav">
              {CHART_TABS.map(ct => (
                <button
                  key={ct.key}
                  className={`fc-chart-btn${activeChart === ct.key ? " active" : ""}`}
                  onClick={() => setActiveChart(ct.key)}
                >
                  {ct.label}
                </button>
              ))}
            </div>
            <div className="fc-chart-img-wrap">
              {result.charts?.[activeChart]
                ? <img src={result.charts[activeChart]} alt={activeChart} />
                : <div style={{ color: "#94a3b8", padding: 32, fontSize: 13 }}>Chart not available</div>
              }
            </div>
          </div>

          {/* Metrics table */}
          <div className="fc-section">
            <div className="fc-section-header">
              <h3>Model Accuracy — Test Set</h3>
              <span className="fc-chip fc-chip-purple">Lower MAE / MAPE = Better</span>
            </div>
            <div className="fc-table-wrap">
              <table className="fc-table">
                <thead>
                  <tr><th>Algorithm</th><th>MAE ($)</th><th>RMSE ($)</th><th>MAPE (%)</th><th>R²</th></tr>
                </thead>
                <tbody>
                  {shownAlgos.map(algo => {
                    const m = result.metrics[algo];
                    const isB = algo === result.best_model;
                    return (
                      <tr key={algo}>
                        <td>
                          <span className={`fc-dot ${DOT_CLASS[algo] || ""}`} />
                          <strong>{ALGO_NAMES[algo] || algo}</strong>
                          {isB && <span className="fc-best-badge">Best</span>}
                        </td>
                        <td>{fmtN(m.mae)}</td>
                        <td>{fmtN(m.rmse)}</td>
                        <td className={m.mape < 1 ? "fc-good" : m.mape > 5 ? "fc-bad" : ""}>{fmtN(m.mape, 4)}%</td>
                        <td className={m.r2 > 0.9 ? "fc-good" : m.r2 < 0.5 ? "fc-bad" : ""}>{fmtN(m.r2, 5)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Daily forecast table */}
          <div className="fc-section">
            <div className="fc-section-header">
              <h3>Daily Forecast Prices</h3>
              <span className="fc-chip fc-chip-blue">{result.horizon_days} days · {result.ticker}</span>
            </div>
            <div className="fc-data-table-wrap">
              <table className="fc-data-table">
                <thead>
                  <tr>
                    <th>Date</th><th>Day</th>
                    {shownAlgos.map(algo => (
                      <th key={algo}>
                        <span className={`fc-dot ${DOT_CLASS[algo] || ""}`} />
                        {ALGO_NAMES[algo] || algo}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(result.forecasts?.[shownAlgos[0]] || []).map((row, i) => {
                    const cur = result.summary?.current_price;
                    return (
                      <tr key={i}>
                        <td><strong>{row.date}</strong></td>
                        <td className="fc-row-day">Day {i + 1}</td>
                        {shownAlgos.map(algo => {
                          const entry = result.forecasts[algo]?.[i];
                          const prev  = i > 0 ? result.forecasts[algo]?.[i - 1]?.price : cur;
                          const up    = entry && prev != null && entry.price >= prev;
                          return (
                            <td key={algo} className={up ? "fc-up" : "fc-down"}>
                              {entry ? fmt$(entry.price) : "—"}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {!result && !loading && !error && (
        <div className="fc-empty">
          <div className="fc-empty-icon">📈</div>
          <h3>Ready to Forecast</h3>
          <p>Select a ticker and horizon above, choose your algorithm, then click Run Forecast to get predictions.</p>
          <div className="fc-steps">
            {["Pick a ticker","Choose algorithm","Set horizon","Run Forecast"].map((s,i) => (
              <div className="fc-step" key={i}>
                <span className="fc-step-num">{i+1}</span>{s}
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
}
