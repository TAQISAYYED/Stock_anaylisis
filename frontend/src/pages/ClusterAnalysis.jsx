import { useEffect, useState } from "react";
import api from "../services/api";
import "./ClusterAnalysis.css";

const SUB_BADGE = ["ca-sub-badge-0", "ca-sub-badge-1", "ca-sub-badge-2", "ca-sub-badge-3"];

export default function ClusterAnalysis() {
  const [portfolios,    setPortfolios]    = useState([]);
  const [portfolioId,   setPortfolioId]   = useState("");
  const [nClusters,     setNClusters]     = useState(3);

  const [s1Loading,     setS1Loading]     = useState(false);
  const [s1Error,       setS1Error]       = useState("");
  const [s1Result,      setS1Result]      = useState(null);

  const [chosenCluster, setChosenCluster] = useState(0);
  const [nSub,          setNSub]          = useState(3);
  const [s2Loading,     setS2Loading]     = useState(false);
  const [s2Error,       setS2Error]       = useState("");
  const [s2Result,      setS2Result]      = useState(null);

  useEffect(() => {
    api.get("/api/analysis/portfolios/")
      .then(res => {
        const data = res.data.results ?? res.data;
        setPortfolios(data);
        if (data.length > 0) setPortfolioId(data[0].id);
      })
      .catch(() => setS1Error("Could not load portfolios."));
  }, []);

  const runStage1 = async () => {
    if (!portfolioId) return;
    setS1Loading(true); setS1Error(""); setS1Result(null); setS2Result(null);
    try {
      const res = await api.post("/api/analysis/stage1/", { portfolio_id: portfolioId, n_clusters: nClusters });
      setS1Result(res.data); setChosenCluster(0);
    } catch (err) { setS1Error(err.response?.data?.error || "Stage 1 failed."); }
    finally { setS1Loading(false); }
  };

  const runStage2 = async () => {
    setS2Loading(true); setS2Error(""); setS2Result(null);
    try {
      const res = await api.post("/api/analysis/stage2/", {
        portfolio_id: portfolioId, n_clusters: nClusters,
        chosen_cluster: chosenCluster, n_sub: nSub,
      });
      setS2Result(res.data);
    } catch (err) { setS2Error(err.response?.data?.error || "Stage 2 failed."); }
    finally { setS2Loading(false); }
  };

  const fmtINR = v => v != null ? `₹${Number(v).toLocaleString("en-IN")}` : "—";
  const fmtN   = (v, d = 2) => v != null ? Number(v).toFixed(d) : "—";

  return (
    <div className="ca-page">

      {/* Header */}
      <div className="ca-page-header">
        <h1>PCA + KMeans Cluster Analysis</h1>
        <p>Stage 1 — PCA on full portfolio &nbsp;|&nbsp; Stage 2 — Sub-cluster by PE Ratio &amp; 52W Discount</p>
      </div>

      {/* Stage 1 control */}
      <div className="ca-control-card">
        <h3>Stage 1 — PCA + KMeans Configuration</h3>
        <div className="ca-control-row">
          <div className="ca-field">
            <label>Select Portfolio</label>
            <select className="ca-select" value={portfolioId} onChange={e => setPortfolioId(e.target.value)}>
              {portfolios.length === 0 && <option value="">Loading portfolios…</option>}
              {portfolios.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
          <div className="ca-field">
            <label>Number of Clusters</label>
            <input type="number" className="ca-input" min={2} max={8} value={nClusters}
              onChange={e => setNClusters(Number(e.target.value))} />
          </div>
          <button className="ca-btn-primary" onClick={runStage1} disabled={s1Loading || !portfolioId}>
            {s1Loading ? "Running…" : "Run Stage 1"}
          </button>
        </div>
      </div>

      {s1Error && <div className="ca-error">{s1Error}</div>}
      {s1Loading && <div className="ca-loading"><div className="ca-spinner" />Running PCA + KMeans on portfolio…</div>}

      {/* Stage 1 results */}
      {s1Result && !s1Loading && (
        <>
          <div className="ca-result-card">
            <div className="ca-result-card-header">
              <h3>Stage 1 — PCA Scatter Plot</h3>
              <span className="ca-badge">{s1Result.n_clusters} Clusters</span>
            </div>
            <div className="ca-chart-wrap">
              <img src={s1Result.chart} alt="Stage 1 PCA KMeans cluster chart" />
            </div>
            <div className="ca-variance-row">
              <div className="ca-variance-pill">PC1 Variance: <span>{s1Result.variance[0]}%</span></div>
              <div className="ca-variance-pill">PC2 Variance: <span>{s1Result.variance[1]}%</span></div>
              <div className="ca-variance-pill">Total Explained: <span>{(s1Result.variance[0] + s1Result.variance[1]).toFixed(1)}%</span></div>
            </div>
          </div>

          <div className="ca-result-card">
            <div className="ca-result-card-header">
              <h3>Cluster Summary</h3>
              <span className="ca-badge ca-badge-blue">{s1Result.stocks.length} Stocks</span>
            </div>
            <div className="ca-cluster-grid">
              {s1Result.cluster_summary.map(c => (
                <div className="ca-cluster-card" key={c.cluster}>
                  <p className="ca-cluster-card-title">{c.label}</p>
                  <div className="ca-ticker-row">
                    {c.tickers.map(t => <span className="ca-ticker-pill" key={t}>{t}</span>)}
                  </div>
                  <div className="ca-stat-row">
                    <div className="ca-stat"><span className="ca-stat-label">Avg PE</span><span className="ca-stat-value">{fmtN(c.avg_pe)}</span></div>
                    <div className="ca-stat"><span className="ca-stat-label">Avg Price</span><span className="ca-stat-value">{fmtINR(c.avg_price)}</span></div>
                    <div className="ca-stat"><span className="ca-stat-label">Stocks</span><span className="ca-stat-value">{c.count}</span></div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="ca-divider" />

          {/* Stage 2 control */}
          <div className="ca-control-card">
            <h3>Stage 2 — Sub-Cluster Drill-Down</h3>
            <div className="ca-control-row">
              <div className="ca-field">
                <label>Select Cluster to Drill Into</label>
                <select className="ca-select" value={chosenCluster} onChange={e => setChosenCluster(Number(e.target.value))}>
                  {s1Result.cluster_summary.map(c => (
                    <option key={c.cluster} value={c.cluster}>{c.label} ({c.count} stocks)</option>
                  ))}
                </select>
              </div>
              <div className="ca-field">
                <label>Number of Sub-Clusters</label>
                <input type="number" className="ca-input" min={2} max={6} value={nSub}
                  onChange={e => setNSub(Number(e.target.value))} />
              </div>
              <button className="ca-btn-secondary" onClick={runStage2} disabled={s2Loading}>
                {s2Loading ? "Running…" : "Run Stage 2"}
              </button>
            </div>
          </div>
        </>
      )}

      {s2Error && <div className="ca-error">{s2Error}</div>}
      {s2Loading && <div className="ca-loading"><div className="ca-spinner" />Running PE Ratio vs 52W Discount sub-clustering…</div>}

      {/* Stage 2 results */}
      {s2Result && !s2Loading && (
        <>
          <div className="ca-result-card">
            <div className="ca-result-card-header">
              <h3>Stage 2 — {s2Result.parent_label}</h3>
              <span className="ca-badge">PE Ratio vs 52W Discount</span>
            </div>
            <div className="ca-chart-wrap">
              <img src={s2Result.chart} alt="Stage 2 sub-cluster scatter chart" />
            </div>
          </div>

          <div className="ca-result-card">
            <div className="ca-result-card-header">
              <h3>Sub-Cluster Summary</h3>
              <span className="ca-badge ca-badge-blue">{s2Result.stocks.length} Stocks</span>
            </div>
            <div className="ca-cluster-grid">
              {s2Result.sub_summary.map(s => (
                <div className="ca-cluster-card" key={s.sub_cluster}>
                  <p className="ca-cluster-card-title">Sub-{s.sub_cluster}: {s.label}</p>
                  <div className="ca-ticker-row">
                    {s.tickers.map(t => <span className="ca-ticker-pill" key={t}>{t}</span>)}
                  </div>
                  <div className="ca-stat-row">
                    <div className="ca-stat"><span className="ca-stat-label">Avg Discount</span><span className="ca-stat-value">{fmtN(s.avg_discount)}%</span></div>
                    <div className="ca-stat"><span className="ca-stat-label">Avg PE</span><span className="ca-stat-value">{fmtN(s.avg_pe)}</span></div>
                    <div className="ca-stat"><span className="ca-stat-label">Avg Price</span><span className="ca-stat-value">{fmtINR(s.avg_price)}</span></div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="ca-result-card">
            <div className="ca-result-card-header">
              <h3>Stock Details — {s2Result.parent_label}</h3>
              <span className="ca-badge ca-badge-blue">{s2Result.stocks.length} Records</span>
            </div>
            <div className="ca-table-wrap">
              <table className="ca-table">
                <thead>
                  <tr>
                    <th>Ticker</th><th>Company</th><th>Current Price</th>
                    <th>52W High</th><th>52W Low</th><th>Discount %</th>
                    <th>PE Ratio</th><th>Sub-Cluster</th>
                  </tr>
                </thead>
                <tbody>
                  {s2Result.stocks.map((s, i) => (
                    <tr key={i}>
                      <td><span className="ca-ticker-pill">{s.ticker}</span></td>
                      <td>{s.company_name || "—"}</td>
                      <td className="ca-val-green">{fmtINR(s.current_price)}</td>
                      <td>{fmtINR(s.week_52_high)}</td>
                      <td>{fmtINR(s.week_52_low)}</td>
                      <td className={s.discount_pct > 30 ? "ca-val-red" : "ca-val-green"}>{fmtN(s.discount_pct)}%</td>
                      <td>{fmtN(s.pe_ratio)}</td>
                      <td>
                        <span className={`ca-sub-badge ${SUB_BADGE[s.sub_cluster] || "ca-sub-badge-0"}`}>
                          Sub-{s.sub_cluster} · {s.sub_label}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {!s1Result && !s1Loading && !s1Error && (
        <div className="ca-empty">
          <div className="ca-empty-icon">📊</div>
          <h3>No Analysis Run Yet</h3>
          <p>Select a portfolio above and click Run Stage 1 to begin.</p>
        </div>
      )}
    </div>
  );
}
