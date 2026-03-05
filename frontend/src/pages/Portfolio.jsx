import { useEffect, useState } from "react";
import api from "../services/api";
import StocksCard from "../components/StocksCard";
import "./Portfolio.css";

export default function Portfolio() {
  const [portfolios, setPortfolios] = useState([]);
  const [selectedPortfolio, setSelectedPortfolio] = useState(null);
  const [stocks, setStocks] = useState([]);
  const [stocksLoading, setStocksLoading] = useState(false);

  const [showCreate, setShowCreate] = useState(false);
  const [newPortfolioName, setNewPortfolioName] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");

  useEffect(() => {
    fetchPortfolios();
  }, []);

  const fetchPortfolios = async () => {
    try {
      const res = await api.get("/api/portfolio/portfolios/");
      console.log("RAW RESPONSE:", res.data);
      const data = res.data.results ?? res.data; // ✅ handles pagination
      setPortfolios(data);
      if (data.length > 0) {
        setSelectedPortfolio(data[0]);
        fetchStocks(data[0].id);
      }
    } catch (err) {
      console.error("Portfolio fetch error:", err);
    }
  };

  const fetchStocks = async (portfolioId) => {
    setStocksLoading(true);
    try {
      const res = await api.get(`/api/stocks/?portfolio=${portfolioId}`);
      setStocks(res.data.results ?? res.data); // ✅ handles pagination
    } catch (err) {
      console.error("Stock fetch error:", err);
    } finally {
      setStocksLoading(false);
    }
  };

  const handleSelectPortfolio = (portfolio) => {
    setSelectedPortfolio(portfolio);
    fetchStocks(portfolio.id);
  };

  const handleCreatePortfolio = async () => {
    if (!newPortfolioName.trim()) return;
    setCreating(true);
    setCreateError("");
    try {
      const res = await api.post("/api/portfolio/portfolios/", {
        name: newPortfolioName.trim(),
      });
      const created = res.data;
      setPortfolios((prev) => [...prev, created]);
      setSelectedPortfolio(created);
      setStocks([]);
      setNewPortfolioName("");
      setShowCreate(false);
    } catch (err) {
      console.error("Create portfolio error:", err.response?.data || err);
      setCreateError(
        err.response?.data?.name?.[0] ||
        err.response?.data?.detail ||
        "Failed to create portfolio. Try a different name."
      );
    } finally {
      setCreating(false);
    }
  };

  const priced = stocks.filter((s) => s.current_price);
  const highestStock = priced.length
    ? priced.reduce((a, b) => (a.current_price > b.current_price ? a : b))
    : null;
  const lowestStock = priced.length
    ? priced.reduce((a, b) => (a.current_price < b.current_price ? a : b))
    : null;
  const gainers = stocks.filter((s) => s.day_change_pct > 0).length;
  const losers  = stocks.filter((s) => s.day_change_pct < 0).length;

  return (
    <div className="pf-root">
      <div className="pf-bg-glow" />

      {/* ── Sidebar ── */}
      <aside className="pf-sidebar">
        <div className="pf-sidebar-header">
          <span className="pf-sidebar-title">Portfolios</span>
          <button
            className="pf-create-btn"
            onClick={() => setShowCreate(true)}
            title="New Portfolio"
          >
            +
          </button>
        </div>

        <nav className="pf-nav">
          {portfolios.length === 0 && (
            <p className="pf-empty-nav">No portfolios yet.</p>
          )}
          {portfolios.map((p) => (
            <button
              key={p.id}
              className={`pf-nav-item ${selectedPortfolio?.id === p.id ? "active" : ""}`}
              onClick={() => handleSelectPortfolio(p)}
            >
              <span className="pf-nav-icon">◈</span>
              <span className="pf-nav-name">{p.name}</span>
              {selectedPortfolio?.id === p.id && <span className="pf-nav-dot" />}
            </button>
          ))}
        </nav>

        <button
          className="pf-new-portfolio-full"
          onClick={() => setShowCreate(true)}
        >
          <span>＋</span> New Portfolio
        </button>
      </aside>

      {/* ── Main content ── */}
      <main className="pf-main">
        {!selectedPortfolio ? (
          <div className="pf-empty-state">
            <div className="pf-empty-icon">◈</div>
            <h2>No Portfolio Selected</h2>
            <p>Create a portfolio to start tracking Indian stocks.</p>
            <button className="pf-empty-cta" onClick={() => setShowCreate(true)}>
              Create Your First Portfolio
            </button>
          </div>
        ) : (
          <>
            <div className="pf-page-header">
              <div>
                <p className="pf-page-label">ACTIVE PORTFOLIO</p>
                <h1 className="pf-page-title">{selectedPortfolio.name}</h1>
              </div>
              <div className="pf-header-meta">
                <span className="pf-live-badge">
                  <span className="pf-live-dot" /> NSE Live
                </span>
              </div>
            </div>

            {priced.length > 0 && (
              <div className="pf-stats-row">
                <div className="pf-stat-card">
                  <p className="pf-stat-label">Total Stocks</p>
                  <p className="pf-stat-value">{stocks.length}</p>
                </div>
                <div className="pf-stat-card green">
                  <p className="pf-stat-label">Highest Price</p>
                  <p className="pf-stat-value">
                    ₹{highestStock?.current_price?.toLocaleString("en-IN")}
                  </p>
                  <p className="pf-stat-sub">{highestStock?.ticker}</p>
                </div>
                <div className="pf-stat-card red">
                  <p className="pf-stat-label">Lowest Price</p>
                  <p className="pf-stat-value">
                    ₹{lowestStock?.current_price?.toLocaleString("en-IN")}
                  </p>
                  <p className="pf-stat-sub">{lowestStock?.ticker}</p>
                </div>
                <div className="pf-stat-card">
                  <p className="pf-stat-label">Gainers / Losers</p>
                  <p className="pf-stat-value">
                    <span style={{ color: "var(--green)" }}>{gainers}↑</span>
                    {" / "}
                    <span style={{ color: "var(--red)" }}>{losers}↓</span>
                  </p>
                </div>
              </div>
            )}

            {stocksLoading ? (
              <div className="pf-loading">
                <div className="pf-spinner" />
                <p>Fetching live market data…</p>
              </div>
            ) : (
              <StocksCard
                stocks={stocks}
                portfolioId={selectedPortfolio.id}
                refreshStocks={() => fetchStocks(selectedPortfolio.id)}
              />
            )}
          </>
        )}
      </main>

      {/* ── Create Portfolio Modal ── */}
      {showCreate && (
        <div className="pf-modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="pf-modal" onClick={(e) => e.stopPropagation()}>
            <div className="pf-modal-header">
              <h3>New Portfolio</h3>
              <button className="pf-modal-close" onClick={() => setShowCreate(false)}>
                ✕
              </button>
            </div>
            <p className="pf-modal-sub">
              Give your portfolio a name to start tracking stocks.
            </p>
            <input
              className="pf-modal-input"
              type="text"
              placeholder="e.g. Tech Stocks, Blue Chip, Long Term…"
              value={newPortfolioName}
              onChange={(e) => setNewPortfolioName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCreatePortfolio()}
              autoFocus
            />
            {createError && <p className="pf-modal-error">{createError}</p>}
            <div className="pf-modal-actions">
              <button
                className="pf-modal-cancel"
                onClick={() => {
                  setShowCreate(false);
                  setCreateError("");
                  setNewPortfolioName("");
                }}
              >
                Cancel
              </button>
              <button
                className="pf-modal-confirm"
                onClick={handleCreatePortfolio}
                disabled={creating || !newPortfolioName.trim()}
              >
                {creating ? "Creating…" : "Create Portfolio"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}