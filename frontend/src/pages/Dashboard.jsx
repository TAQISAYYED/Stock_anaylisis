import { useEffect, useState } from "react";
import api from "../services/api";
import AnalysisPanel from "../components/AnalysisPanel";
import PortfolioChart from "../components/PortfolioChart";
import StocksCard from "../components/StocksCard";
import "./Dashboard.css";

export default function Dashboard() {
  const [portfolios, setPortfolios] = useState([]);
  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [portfolioRes, stockRes] = await Promise.all([
        api.get("/api/portfolio/portfolios/"),
        api.get("/api/stocks/"),
      ]);
      setPortfolios(portfolioRes.data.results ?? portfolioRes.data);
      setStocks(stockRes.data.results ?? stockRes.data);
    } catch (error) {
      console.error("Dashboard fetch error:", error);
    } finally {
      setLoading(false);
    }
  };

  const totalPortfolios = portfolios.length;
  const totalStocks = stocks.length;
  const priced = stocks.filter((s) => s.current_price);
  const gainers = stocks.filter((s) => s.day_change_pct > 0).length;
  const losers  = stocks.filter((s) => s.day_change_pct < 0).length;

  return (
    <div className="db-root">
      <div className="db-bg-glow" />

      <div className="db-inner">

        {/* ── Page header ── */}
        <div className="db-header">
          <div>
            <p className="db-label">OVERVIEW</p>
            <h1 className="db-title">Investment Dashboard</h1>
          </div>
          <span className="db-live-badge">
            <span className="db-live-dot" /> NSE Live
          </span>
        </div>

        {/* ── Top stats ── */}
        {!loading && (
          <div className="db-stats-row">
            <div className="db-stat">
              <p className="db-stat-label">Portfolios</p>
              <p className="db-stat-value">{totalPortfolios}</p>
            </div>
            <div className="db-stat">
              <p className="db-stat-label">Total Stocks</p>
              <p className="db-stat-value">{totalStocks}</p>
            </div>
            <div className="db-stat">
              <p className="db-stat-label">With Live Price</p>
              <p className="db-stat-value">{priced.length}</p>
            </div>
            <div className="db-stat green">
              <p className="db-stat-label">Gainers</p>
              <p className="db-stat-value" style={{ color: "var(--db-green)" }}>
                {gainers}↑
              </p>
            </div>
            <div className="db-stat red">
              <p className="db-stat-label">Losers</p>
              <p className="db-stat-value" style={{ color: "var(--db-red)" }}>
                {losers}↓
              </p>
            </div>
          </div>
        )}

        {/* ── Loading state ── */}
        {loading ? (
          <div className="db-loading">
            <div className="db-spinner" />
            <p>Loading dashboard…</p>
          </div>
        ) : (
          <div className="db-sections">
            <div className="db-section">
              <AnalysisPanel portfolios={portfolios} stocks={stocks} />
            </div>
            <div className="db-section">
              <PortfolioChart portfolios={portfolios} />
            </div>
            <div className="db-section">
              <StocksCard stocks={stocks} portfolioId={null} refreshStocks={fetchData} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
