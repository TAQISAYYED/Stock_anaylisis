import { useState } from "react";
import api from "../services/api";
import "./StocksCard.css";

export default function StocksCard({ stocks, portfolioId, refreshStocks, onDeleteStock }) {
  const [newSymbol, setNewSymbol] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [deletingId, setDeletingId] = useState(null);

  const handleAddStock = async () => {
    if (!newSymbol.trim() || !portfolioId) return;
    setLoading(true);
    setError("");
    try {
      await api.post("/api/stocks/", {
        ticker: newSymbol.trim().toUpperCase(),
        company_name: newSymbol.trim().toUpperCase(),
        portfolio: portfolioId,
      });
      setNewSymbol("");
      refreshStocks();
    } catch (err) {
      console.error(err);
      setError("Invalid symbol or already added. Try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (stockId) => {
    setDeletingId(stockId);
    try {
      await api.delete(`/api/stocks/${stockId}/`);
      refreshStocks();
    } catch (err) {
      console.error("Delete error:", err);
    } finally {
      setDeletingId(null);
    }
  };

  const fmt = (val) =>
    val != null ? `₹${Number(val).toLocaleString("en-IN")}` : "—";

  const fmtPct = (val) => {
    if (val == null) return "—";
    const sign = val > 0 ? "+" : "";
    return `${sign}${val.toFixed(2)}%`;
  };

  const fmtMktCap = (val) => {
    if (!val) return "—";
    if (val >= 1e12) return `₹${(val / 1e12).toFixed(2)}T`;
    if (val >= 1e9)  return `₹${(val / 1e9).toFixed(2)}B`;
    if (val >= 1e7)  return `₹${(val / 1e7).toFixed(2)}Cr`;
    return `₹${val.toLocaleString("en-IN")}`;
  };

  return (
    <div className="sc-wrap">

      {/* ── Add stock bar ── */}
      <div className="sc-add-bar">
        <div className="sc-add-left">
          <span className="sc-add-label">ADD STOCK</span>
          <div className="sc-input-wrap">
            <span className="sc-input-prefix">NSE:</span>
            <input
              className="sc-input"
              type="text"
              placeholder="TCS, INFY, RELIANCE…"
              value={newSymbol}
              onChange={(e) => setNewSymbol(e.target.value.toUpperCase())}
              onKeyDown={(e) => e.key === "Enter" && handleAddStock()}
              maxLength={20}
            />
          </div>
          {error && <span className="sc-error">{error}</span>}
        </div>
        <button
          className="sc-add-btn"
          onClick={handleAddStock}
          disabled={loading || !newSymbol.trim()}
        >
          {loading ? (
            <span className="sc-btn-spinner" />
          ) : (
            <>＋ Add Stock</>
          )}
        </button>
      </div>

      {/* ── Table ── */}
      <div className="sc-table-wrap">
        {stocks.length === 0 ? (
          <div className="sc-empty">
            <p className="sc-empty-icon">◈</p>
            <p>No stocks in this portfolio yet.</p>
            <p className="sc-empty-sub">Add a stock symbol above to get started.</p>
          </div>
        ) : (
          <table className="sc-table">
            <thead>
              <tr>
                <th>SYMBOL</th>
                <th>PRICE</th>
                <th>DAY CHG</th>
                <th>DAY HIGH</th>
                <th>DAY LOW</th>
                <th>52W HIGH</th>
                <th>52W LOW</th>
                <th>P/E</th>
                <th>MKT CAP</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {stocks.map((stock, i) => {
                const positive = stock.day_change_pct > 0;
                const negative = stock.day_change_pct < 0;
                return (
                  <tr
                    key={stock.id}
                    style={{ animationDelay: `${i * 40}ms` }}
                    className="sc-row"
                  >
                    {/* Symbol */}
                    <td>
                      <div className="sc-symbol-cell">
                        <span className="sc-ticker">{stock.ticker}</span>
                        <span className="sc-company">
                          {stock.company_name !== stock.ticker
                            ? stock.company_name
                            : stock.ticker + ".NS"}
                        </span>
                      </div>
                    </td>

                    {/* Price */}
                    <td>
                      <span
                        className={`sc-price ${
                          stock.current_price
                            ? positive
                              ? "green"
                              : negative
                              ? "red"
                              : ""
                            : "na"
                        }`}
                      >
                        {stock.current_price ? fmt(stock.current_price) : "N/A"}
                      </span>
                    </td>

                    {/* Day change % */}
                    <td>
                      <span
                        className={`sc-change ${
                          positive ? "green" : negative ? "red" : "na"
                        }`}
                      >
                        {fmtPct(stock.day_change_pct)}
                      </span>
                    </td>

                    {/* Day High */}
                    <td className="sc-num">{fmt(stock.day_high)}</td>

                    {/* Day Low */}
                    <td className="sc-num">{fmt(stock.day_low)}</td>

                    {/* 52W High */}
                    <td className="sc-num green-soft">{fmt(stock.week_52_high)}</td>

                    {/* 52W Low */}
                    <td className="sc-num red-soft">{fmt(stock.week_52_low)}</td>

                    {/* PE */}
                    <td className="sc-num">
                      {stock.pe_ratio != null ? stock.pe_ratio : "—"}
                    </td>

                    {/* Market Cap */}
                    <td className="sc-num">{fmtMktCap(stock.market_cap)}</td>

                    {/* Delete */}
                    <td>
                      <button
                        className="sc-delete-btn"
                        onClick={() => handleDelete(stock.id)}
                        disabled={deletingId === stock.id}
                        title="Remove stock"
                      >
                        {deletingId === stock.id ? "…" : "✕"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      <div className="sc-footer">
        <span>{stocks.length} stock{stocks.length !== 1 ? "s" : ""} · NSE data via yfinance</span>
        <span className="sc-footer-suffix">.NS suffix applied automatically</span>
      </div>
    </div>
  );
}
