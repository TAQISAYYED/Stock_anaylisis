import { useEffect, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from "recharts";
// ✅ ScatterChart REMOVED — it crashes because <Scatter> doesn't accept dataKey
// Replaced with a LineChart scatter-style + table for regression tab
import api from "../services/api";
import "./GoldSilver.css";

// ── Custom tooltip ──────────────────────────────────
const ChartTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="gs-tooltip">
      <p className="gs-tooltip-label">{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color, margin: "2px 0", fontSize: 12 }}>
          {p.name}:{" "}
          <strong>
            {typeof p.value === "number" ? p.value.toFixed(2) : p.value}
          </strong>
        </p>
      ))}
    </div>
  );
};

// ── Feature importance bar ──────────────────────────
const ImportanceBar = ({ label, value, maxVal, color }) => {
  const pct = maxVal > 0 ? (value / maxVal) * 100 : 0;
  return (
    <div className="gs-imp-row">
      <div className="gs-imp-label" title={label}>{label}</div>
      <div className="gs-imp-bar-wrap">
        <div className="gs-imp-bar" style={{ width: `${pct}%`, background: color }} />
      </div>
      <div className="gs-imp-val">{value.toFixed(4)}</div>
    </div>
  );
};

// ── LIME diverging bar ──────────────────────────────
const LimeRow = ({ label, weight, maxAbs }) => {
  const pct   = maxAbs > 0 ? (Math.abs(weight) / maxAbs) * 50 : 0;
  const isPos = weight >= 0;
  return (
    <div className="gs-lime-row">
      <div className="gs-lime-label" title={label}>{label}</div>
      <div className="gs-lime-bar-wrap">
        {isPos ? (
          <>
            <div className="gs-lime-half" />
            <div className="gs-lime-bar pos" style={{ width: `${pct}%` }} />
          </>
        ) : (
          <>
            <div
              className="gs-lime-bar neg"
              style={{ width: `${pct}%`, marginLeft: `${50 - pct}%` }}
            />
            <div className="gs-lime-half" />
          </>
        )}
      </div>
      <div className={`gs-lime-val ${isPos ? "pos" : "neg"}`}>
        {isPos ? "+" : ""}{weight.toFixed(4)}
      </div>
    </div>
  );
};

// ── Matplotlib base64 chart ─────────────────────────
const ChartImage = ({ src, alt }) => {
  if (!src) return (
    <div className="gs-chart-empty">
      Chart unavailable — run <code>pip install shap lime</code> in your Django venv
    </div>
  );
  return (
    <div className="gs-chart-img-wrap">
      <img src={src} alt={alt} />
    </div>
  );
};

// ── Regression table (replaces broken ScatterChart) ─
const RegressionTable = ({ data }) => (
  <div className="gs-table-wrap">
    <table className="gs-table">
      <thead>
        <tr>
          <th>Gold ($)</th>
          <th>Silver Actual ($)</th>
          <th>Silver Predicted ($)</th>
          <th>Error ($)</th>
        </tr>
      </thead>
      <tbody>
        {data.map((row, i) => {
          const err = row.silver_actual - row.silver_predicted;
          return (
            <tr key={i}>
              <td className="gs-val-gold">${row.gold.toLocaleString()}</td>
              <td className="gs-val-silver">${row.silver_actual.toFixed(2)}</td>
              <td style={{ color: "#6366f1", fontWeight: 600 }}>
                ${row.silver_predicted.toFixed(2)}
              </td>
              <td className={err >= 0 ? "gs-val-green" : "gs-val-red"}>
                {err >= 0 ? "+" : ""}{err.toFixed(2)}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  </div>
);

// ── Safe stat formatter ─────────────────────────────
const fmt = (val, prefix = "", suffix = "", decimals = 4) => {
  if (val === null || val === undefined) return "—";
  const n = Number(val);
  if (isNaN(n)) return "—";
  return `${prefix}${n.toFixed(decimals)}${suffix}`;
};

// ══════════════════════════════════════════════════
export default function GoldSilver() {
  const [data,      setData]      = useState(null);
  const [loading,   setLoading]   = useState(true);
  const [error,     setError]     = useState("");
  const [activeTab, setActiveTab] = useState("price");
  const [xaiTab,    setXaiTab]    = useState("shap_bar");

  useEffect(() => {
    api.get("/api/goldsilver/analysis/")
      .then(res => { setData(res.data); setLoading(false); })
      .catch(err => {
        const msg = err.response?.data?.error || "Failed to load market data.";
        setError(msg);
        setLoading(false);
      });
  }, []);

  // ── Loading state ─────────────────────────────────
  if (loading) return (
    <div className="gs-page">
      <div className="gs-loading">
        <div className="gs-spinner" />
        <p>Fetching gold &amp; silver market data…</p>
      </div>
    </div>
  );

  // ── Error state ───────────────────────────────────
  if (error) return (
    <div className="gs-page">
      <div className="gs-page-header">
        <div>
          <p className="gs-page-label">Market Intelligence</p>
          <h1 className="gs-page-title">Gold &amp; Silver Analysis</h1>
        </div>
      </div>
      <div className="gs-error">⚠ {error}</div>
    </div>
  );

  if (!data) return null;

  // ── Safe arrays ───────────────────────────────────
  const topFeatures    = Array.isArray(data.top_features)    ? data.top_features    : [];
  const limeFeatures   = Array.isArray(data.lime_features)   ? data.lime_features   : [];
  const gbmImportances = Array.isArray(data.gbm_importances) ? data.gbm_importances : [];

  const maxShap = topFeatures.length    ? topFeatures[0].importance                              : 1;
  const maxGbm  = gbmImportances.length ? gbmImportances[0].importance                           : 1;
  const maxLime = limeFeatures.length
    ? Math.max(...limeFeatures.map(f => Math.abs(f.weight ?? 0)))
    : 1;

  const MAIN_TABS = [
    { key: "price",      label: "📈 Price History" },
    { key: "regression", label: "📉 Regression" },
    { key: "predict",    label: "🔮 6M Forecast" },
    { key: "xai",        label: "🧠 SHAP / LIME" },
    { key: "features",   label: "📊 Feature Rank" },
  ];

  const XAI_TABS = [
    { key: "shap_bar",            label: "SHAP Global" },
    { key: "shap_waterfall",      label: "SHAP Waterfall" },
    { key: "lime_bar",            label: "LIME Local" },
    { key: "top_feature_scatter", label: "Top Feature" },
  ];

  return (
    <div className="gs-page">

      {/* ── Header ──────────────────────────────────── */}
      <div className="gs-page-header">
        <div>
          <p className="gs-page-label">Market Intelligence</p>
          <h1 className="gs-page-title">Gold &amp; Silver Analysis</h1>
        </div>
        <div className="gs-header-badges">
          <span className="gs-badge gold">Gold (GC=F)</span>
          <span className="gs-badge silver">Silver (SI=F)</span>
          <span className="gs-badge indigo">5Y Monthly</span>
          {data.xai_available === false && (
            <span className="gs-badge warn">⚠ XAI unavailable</span>
          )}
        </div>
      </div>

      {/* ── Stat cards ──────────────────────────────── */}
      <div className="gs-stat-row">
        {[
          { label: "Correlation",     value: fmt(data.correlation),       sub: "Gold ↔ Silver (Pearson)", cls: "indigo" },
          { label: "Linear R²",       value: fmt(data.r2_score),          sub: "Linear regression fit",   cls: "" },
          { label: "GBM R² (CV)",     value: fmt(data.gbm_r2_cv),         sub: "Cross-validated GBM",     cls: "green" },
          { label: "Slope",           value: fmt(data.slope),             sub: "Silver / $1 Gold change", cls: "" },
          { label: "GBM Pred (Now)",  value: fmt(data.gbm_pred_latest, "$", "", 2), sub: "Silver estimate", cls: "gold" },
          { label: "SHAP Base Value", value: fmt(data.shap_base_value, "$", "", 2), sub: "Model baseline",  cls: "purple" },
        ].map((c, i) => (
          <div key={i} className="gs-stat-card">
            <p className="gs-stat-label">{c.label}</p>
            <p className={`gs-stat-value ${c.cls}`}>{c.value}</p>
            <p className="gs-stat-sub">{c.sub}</p>
          </div>
        ))}
      </div>

      {/* ── Main tabs ───────────────────────────────── */}
      <div className="gs-section-tabs">
        {MAIN_TABS.map(t => (
          <button
            key={t.key}
            className={`gs-tab ${activeTab === t.key ? "active" : ""}`}
            onClick={() => setActiveTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ═══ PRICE HISTORY ════════════════════════════ */}
      {activeTab === "price" && (
        <div className="gs-card">
          <div className="gs-card-header">
            <h3>5-Year Monthly Price History</h3>
            <span className="gs-chip indigo">{data.price_history?.length ?? 0} data points</span>
          </div>
          <ResponsiveContainer width="100%" height={320}>
            <LineChart
              data={data.price_history}
              margin={{ top: 10, right: 24, left: 10, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e8eaf2" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10, fill: "#6b7280" }}
                tickFormatter={v => v.slice(0, 7)}
                interval={3}
              />
              <YAxis yAxisId="g" orientation="left"
                tick={{ fontSize: 10, fill: "#d97706" }}
                tickFormatter={v => `$${Number(v).toLocaleString()}`}
              />
              <YAxis yAxisId="s" orientation="right"
                tick={{ fontSize: 10, fill: "#94a3b8" }}
                tickFormatter={v => `$${Number(v).toFixed(0)}`}
              />
              <Tooltip content={<ChartTooltip />} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line yAxisId="g" type="monotone" dataKey="gold"
                stroke="#d97706" strokeWidth={2} dot={false} name="Gold ($)" />
              <Line yAxisId="s" type="monotone" dataKey="silver"
                stroke="#94a3b8" strokeWidth={2} dot={false} name="Silver ($)" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ═══ REGRESSION ═══════════════════════════════ */}
      {activeTab === "regression" && (
        <div className="gs-card">
          <div className="gs-card-header">
            <h3>Linear Regression — Gold vs Silver</h3>
            <div style={{ display: "flex", gap: 8 }}>
              <span className="gs-chip indigo">R² = {fmt(data.r2_score)}</span>
              <span className="gs-chip gold">Slope = {fmt(data.slope)}</span>
            </div>
          </div>

          {/* ✅ Line chart showing actual vs predicted silver over time */}
          <ResponsiveContainer width="100%" height={300}>
            <LineChart
              data={data.regression_data}
              margin={{ top: 10, right: 24, left: 10, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e8eaf2" />
              <XAxis
                dataKey="gold"
                tick={{ fontSize: 9, fill: "#6b7280" }}
                tickFormatter={v => `$${Number(v).toLocaleString()}`}
                label={{ value: "Gold Price ($)", position: "insideBottom", offset: -2, fill: "#6b7280", fontSize: 10 }}
              />
              <YAxis
                tick={{ fontSize: 10, fill: "#6b7280" }}
                tickFormatter={v => `$${Number(v).toFixed(0)}`}
              />
              <Tooltip content={<ChartTooltip />} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="silver_actual"
                stroke="#94a3b8" strokeWidth={0}
                dot={{ r: 4, fill: "#94a3b8", opacity: 0.75 }}
                activeDot={{ r: 5 }} name="Silver Actual ($)" />
              <Line type="monotone" dataKey="silver_predicted"
                stroke="#6366f1" strokeWidth={2} dot={false}
                name="Silver Predicted ($)" />
            </LineChart>
          </ResponsiveContainer>

          <div style={{ marginTop: 20 }}>
            <p className="gs-section-label" style={{ marginBottom: 10, color: "#6b7280", fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em" }}>
              All Data Points
            </p>
            <RegressionTable data={data.regression_data} />
          </div>
        </div>
      )}

      {/* ═══ 6M FORECAST ══════════════════════════════ */}
      {activeTab === "predict" && (
        <div className="gs-card">
          <div className="gs-card-header">
            <h3>6-Month Linear Forecast</h3>
            <span className="gs-chip gold">+2%/mo gold assumption</span>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart
              data={data.predictions}
              margin={{ top: 10, right: 24, left: 10, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e8eaf2" />
              <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#6b7280" }} />
              <YAxis yAxisId="g" orientation="left"
                tick={{ fontSize: 10, fill: "#d97706" }}
                tickFormatter={v => `$${Number(v).toLocaleString()}`}
              />
              <YAxis yAxisId="s" orientation="right"
                tick={{ fontSize: 10, fill: "#94a3b8" }}
                tickFormatter={v => `$${Number(v).toFixed(1)}`}
              />
              <Tooltip content={<ChartTooltip />} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line yAxisId="g" type="monotone" dataKey="gold"
                stroke="#d97706" strokeWidth={2.5} dot={{ r: 5 }} name="Gold Forecast ($)" />
              <Line yAxisId="s" type="monotone" dataKey="silver_predicted"
                stroke="#94a3b8" strokeWidth={2.5} dot={{ r: 5 }} name="Silver Forecast ($)" />
            </LineChart>
          </ResponsiveContainer>
          <div className="gs-table-wrap" style={{ marginTop: 20 }}>
            <table className="gs-table">
              <thead>
                <tr><th>Period</th><th>Gold ($)</th><th>Silver Predicted ($)</th></tr>
              </thead>
              <tbody>
                {data.predictions.map((p, i) => (
                  <tr key={i}>
                    <td>{p.month}</td>
                    <td className="gs-val-gold">${p.gold.toLocaleString()}</td>
                    <td className="gs-val-silver">${p.silver_predicted.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ═══ SHAP / LIME ══════════════════════════════ */}
      {activeTab === "xai" && (
        <div className="gs-card">
          <div className="gs-card-header">
            <h3>Model Explainability — SHAP &amp; LIME</h3>
            <span className="gs-chip indigo">GradientBoosting → Silver Price</span>
          </div>

          <div className="gs-xai-info-row">
            <div className="gs-xai-info-block">
              <span className="gs-xai-badge shap">SHAP</span>
              <p>
                <strong>SHapley Additive exPlanations</strong> — measures each
                feature's average contribution across ALL predictions. Global view
                shows which features drive the model most, consistently.
              </p>
            </div>
            <div className="gs-xai-info-block">
              <span className="gs-xai-badge lime">LIME</span>
              <p>
                <strong>Local Interpretable Model-agnostic Explanations</strong> —
                explains why the model made the <em>most recent</em> prediction by
                perturbing inputs locally and fitting a simple linear surrogate.
              </p>
            </div>
          </div>

          {data.xai_available === false && (
            <div className="gs-error" style={{ marginBottom: 16 }}>
              ⚠ &nbsp;SHAP / LIME charts require:{" "}
              <code>pip install shap lime</code> in your Django venv.
              GBM feature importances are still shown below.
            </div>
          )}

          <div className="gs-xai-tabs">
            {XAI_TABS.map(t => (
              <button
                key={t.key}
                className={`gs-xai-tab ${xaiTab === t.key ? "active" : ""}`}
                onClick={() => setXaiTab(t.key)}
              >
                {t.label}
              </button>
            ))}
          </div>

          <ChartImage src={data.charts?.[xaiTab]} alt={xaiTab} />

          {/* SHAP table */}
          {xaiTab === "shap_bar" && topFeatures.length > 0 && (
            <div className="gs-xai-table-wrap">
              <p className="gs-xai-table-title">Top Features by Mean |SHAP Value|</p>
              <div className="gs-table-wrap">
                <table className="gs-table">
                  <thead>
                    <tr>
                      <th>#</th><th>Feature</th><th>Mean |SHAP|</th>
                      <th>Latest SHAP</th><th>Impact</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topFeatures.map((f, i) => (
                      <tr key={i}>
                        <td className="gs-rank">#{i + 1}</td>
                        <td><strong>{f.label}</strong></td>
                        <td>{Number(f.importance).toFixed(5)}</td>
                        <td className={f.shap_latest >= 0 ? "gs-val-green" : "gs-val-red"}>
                          {f.shap_latest >= 0 ? "+" : ""}{Number(f.shap_latest).toFixed(5)}
                        </td>
                        <td>
                          <span className={`gs-dir-badge ${f.direction}`}>
                            {f.direction === "positive" ? "↑ Bullish" : "↓ Bearish"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* LIME table */}
          {xaiTab === "lime_bar" && limeFeatures.length > 0 && (
            <div className="gs-xai-table-wrap">
              <p className="gs-xai-table-title">LIME Weights — Latest Prediction</p>
              <div className="gs-table-wrap">
                <table className="gs-table">
                  <thead>
                    <tr><th>#</th><th>Feature</th><th>Weight</th><th>Direction</th></tr>
                  </thead>
                  <tbody>
                    {limeFeatures.map((f, i) => (
                      <tr key={i}>
                        <td className="gs-rank">#{i + 1}</td>
                        <td><strong>{f.feature}</strong></td>
                        <td className={f.weight >= 0 ? "gs-val-green" : "gs-val-red"}>
                          {f.weight >= 0 ? "+" : ""}{Number(f.weight).toFixed(5)}
                        </td>
                        <td>
                          <span className={`gs-dir-badge ${f.direction}`}>
                            {f.direction === "positive" ? "↑ Push Up" : "↓ Push Down"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {xaiTab === "shap_waterfall" && (
            <div className="gs-waterfall-key">
              <span className="gs-wf-dot green" /> Positive contribution (raises silver price)
              <span className="gs-wf-dot red" style={{ marginLeft: 16 }} /> Negative contribution
              <span className="gs-wf-dot gold" style={{ marginLeft: 16 }} /> Base value (model average)
            </div>
          )}
        </div>
      )}

      {/* ═══ FEATURE RANK ═════════════════════════════ */}
      {activeTab === "features" && (
        <div className="gs-card">
          <div className="gs-card-header">
            <h3>Feature Importance — 3 Methods Compared</h3>
            <span className="gs-chip indigo">SHAP · GBM Split · LIME</span>
          </div>

          <div className="gs-feat-grid">

            {/* SHAP */}
            <div className="gs-feat-panel">
              <div className="gs-feat-panel-hd">
                <span className="gs-xai-badge shap">SHAP</span>
                <p>Mean |SHAP| — global importance across all samples</p>
              </div>
              {topFeatures.length === 0 ? (
                <p style={{ color: "#9ca3af", fontSize: "0.8rem" }}>
                  Install <code>shap</code> to see this panel
                </p>
              ) : (
                <div className="gs-imp-list">
                  {topFeatures.map((f, i) => (
                    <ImportanceBar key={i} label={f.label} value={f.importance}
                      maxVal={maxShap}
                      color={f.direction === "positive" ? "#10b981" : "#ef4444"} />
                  ))}
                </div>
              )}
            </div>

            {/* GBM */}
            <div className="gs-feat-panel">
              <div className="gs-feat-panel-hd">
                <span className="gs-xai-badge gbm">GBM Split</span>
                <p>sklearn feature_importances_ (impurity reduction)</p>
              </div>
              {gbmImportances.length === 0 ? (
                <p style={{ color: "#9ca3af", fontSize: "0.8rem" }}>No GBM data available</p>
              ) : (
                <div className="gs-imp-list">
                  {gbmImportances.slice(0, 10).map((f, i) => (
                    <ImportanceBar key={i} label={f.feature} value={f.importance}
                      maxVal={maxGbm} color="#6366f1" />
                  ))}
                </div>
              )}
            </div>

            {/* LIME */}
            <div className="gs-feat-panel">
              <div className="gs-feat-panel-hd">
                <span className="gs-xai-badge lime">LIME Local</span>
                <p>Contribution weights — latest prediction only</p>
              </div>
              {limeFeatures.length === 0 ? (
                <p style={{ color: "#9ca3af", fontSize: "0.8rem" }}>
                  Install <code>lime</code> to see this panel
                </p>
              ) : (
                <div className="gs-imp-list">
                  {limeFeatures.map((f, i) => (
                    <LimeRow key={i} label={f.feature} weight={f.weight} maxAbs={maxLime} />
                  ))}
                </div>
              )}
            </div>

          </div>
        </div>
      )}

    </div>
  );
}
