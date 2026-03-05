import { useEffect, useState } from "react";
import api from "../services/api";
import "./portfoliochart.css";

export default function PortfolioChart() {
  const [portfolios, setPortfolios] = useState([]);
  const [selectedPortfolio, setSelectedPortfolio] = useState("");
  const [selectedName, setSelectedName] = useState("");
  const [stocks, setStocks] = useState([]);
  const [loadingStocks, setLoadingStocks] = useState(false);

  useEffect(() => {
    fetchPortfolios();
  }, []);

  const fetchPortfolios = async () => {
    try {
      const res = await api.get("/api/portfolio/portfolios/");
      const data = res.data.results ?? res.data;
      setPortfolios(data);
    } catch (error) {
      console.error("Portfolio fetch error:", error);
    }
  };

  const handlePortfolioChange = async (portfolioId) => {
    setSelectedPortfolio(portfolioId);
    const found = portfolios.find((p) => String(p.id) === String(portfolioId));
    setSelectedName(found?.name || "");
    if (!portfolioId) { setStocks([]); return; }
    setLoadingStocks(true);
    try {
      const res = await api.get(`/api/stocks/?portfolio=${portfolioId}`);
      const data = res.data.results ?? res.data;
      setStocks(data);
    } catch (error) {
      console.error("Stock fetch error:", error);
    } finally {
      setLoadingStocks(false);
    }
  };

  const priced = stocks.filter((s) => s.current_price);
  const highestStock = priced.length
    ? priced.reduce((a, b) => (a.current_price > b.current_price ? a : b))
    : null;
  const lowestStock = priced.length
    ? priced.reduce((a, b) => (a.current_price < b.current_price ? a : b))
    : null;

  return (
    <div className="pc-root">
      <div className="pc-bg-glow" />

      <div className="pc-inner">

        {/* ── Header ── */}
        <div className="pc-header">
          <div>
            <p className="pc-label">PORTFOLIO OVERVIEW</p>
            <h1 className="pc-title">
              {selectedName ? selectedName : "Select a Portfolio"}
            </h1>
          </div>
          {selectedPortfolio && (
            <span className="pc-live-badge">
              <span className="pc-live-dot" /> NSE Live
            </span>
          )}
        </div>

        {/* ── Dropdown ── */}
        <div className="pc-select-wrap">
          <span className="pc-select-label">PORTFOLIO</span>
          <div className="pc-select-box">
            <select
              className="pc-dropdown"
              value={selectedPortfolio}
              onChange={(e) => handlePortfolioChange(e.target.value)}
            >
              <option value="">— Select Portfolio —</option>
              {portfolios.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
            <span className="pc-select-arrow">▾</span>
          </div>
        </div>

        {/* ── Stats ── */}
        {selectedPortfolio && priced.length > 0 && (
          <div className="pc-stats-row">
            <div className="pc-stat">
              <p className="pc-stat-label">Total Stocks</p>
              <p className="pc-stat-value">{stocks.length}</p>
            </div>
            <div className="pc-stat green">
              <p className="pc-stat-label">Highest Price</p>
              <p className="pc-stat-value">
                ₹{highestStock?.current_price?.toLocaleString("en-IN")}
              </p>
              <p className="pc-stat-sub">{highestStock?.ticker}</p>
            </div>
            <div className="pc-stat red">
              <p className="pc-stat-label">Lowest Price</p>
              <p className="pc-stat-value">
                ₹{lowestStock?.current_price?.toLocaleString("en-IN")}
              </p>
              <p className="pc-stat-sub">{lowestStock?.ticker}</p>
            </div>
            <div className="pc-stat">
              <p className="pc-stat-label">With Live Price</p>
              <p className="pc-stat-value">{priced.length} / {stocks.length}</p>
            </div>
          </div>
        )}

        {/* ── Table ── */}
        {selectedPortfolio && (
          <div className="pc-table-wrap">
            <div className="pc-table-header">
              <span className="pc-table-title">Indian Stocks in Portfolio</span>
              <span className="pc-table-badge">{stocks.length} stocks</span>
            </div>

            {loadingStocks ? (
              <div className="pc-loading">
                <div className="pc-spinner" />
                <p>Fetching live market data…</p>
              </div>
            ) : stocks.length === 0 ? (
              <div className="pc-empty">
                <p className="pc-empty-icon">◈</p>
                <p>No stocks in this portfolio.</p>
              </div>
            ) : (
              <table className="pc-table">
                <thead>
                  <tr>
                    <th>SYMBOL</th>
                    <th>COMPANY</th>
                    <th>PRICE</th>
                    <th>DAY CHG</th>
                    <th>DAY HIGH</th>
                    <th>DAY LOW</th>
                    <th>52W HIGH</th>
                    <th>52W LOW</th>
                    <th>P/E</th>
                  </tr>
                </thead>
                <tbody>
                  {stocks.map((stock, i) => {
                    const pos = stock.day_change_pct > 0;
                    const neg = stock.day_change_pct < 0;
                    return (
                      <tr
                        key={stock.id}
                        className="pc-row"
                        style={{ animationDelay: `${i * 40}ms` }}
                      >
                        <td>
                          <span className="pc-ticker">{stock.ticker}</span>
                        </td>
                        <td className="pc-company">
                          {stock.company_name !== stock.ticker
                            ? stock.company_name
                            : "—"}
                        </td>
                        <td>
                          <span className={`pc-price ${pos ? "green" : neg ? "red" : ""}`}>
                            {stock.current_price
                              ? `₹${stock.current_price.toLocaleString("en-IN")}`
                              : "N/A"}
                          </span>
                        </td>
                        <td>
                          <span className={`pc-change ${pos ? "green" : neg ? "red" : "na"}`}>
                            {stock.day_change_pct != null
                              ? `${pos ? "+" : ""}${stock.day_change_pct.toFixed(2)}%`
                              : "—"}
                          </span>
                        </td>
                        <td className="pc-num">
                          {stock.day_high ? `₹${stock.day_high.toLocaleString("en-IN")}` : "—"}
                        </td>
                        <td className="pc-num">
                          {stock.day_low ? `₹${stock.day_low.toLocaleString("en-IN")}` : "—"}
                        </td>
                        <td className="pc-num green-soft">
                          {stock.week_52_high ? `₹${stock.week_52_high.toLocaleString("en-IN")}` : "—"}
                        </td>
                        <td className="pc-num red-soft">
                          {stock.week_52_low ? `₹${stock.week_52_low.toLocaleString("en-IN")}` : "—"}
                        </td>
                        <td className="pc-num">
                          {stock.pe_ratio ?? "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}

            <div className="pc-footer">
              <span>{stocks.length} stock{stocks.length !== 1 ? "s" : ""} · NSE data via yfinance</span>
              <span className="pc-footer-accent">.NS suffix applied automatically</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
