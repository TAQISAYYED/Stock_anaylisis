import "./AnalysisPanel.css";

export default function AnalysisPanel({ portfolios = [], stocks = [] }) {

  const totalStocks = stocks.length;
  const totalPortfolios = portfolios.length;

  return (
    <div className="analysis-container">

      <div className="analysis-card">
        <h3>Total Portfolios</h3>
        <p>{totalPortfolios}</p>
      </div>

      <div className="analysis-card">
        <h3>Total Stocks</h3>
        <p>{totalStocks}</p>
      </div>

      <div className="analysis-card risk-card">
        <h3>Market Status</h3>
        <p className="risk-high">High Volatility</p>
      </div>

    </div>
  );
}