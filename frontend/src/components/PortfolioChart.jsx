import { useEffect, useState } from "react";
import axios from "axios";
import Navbar from "../components/Navbar";
import "./PortfolioChart.css";

export default function Portfolio() {

  const [portfolios, setPortfolios] = useState([]);
  const [selectedPortfolio, setSelectedPortfolio] = useState("");
  const [stocks, setStocks] = useState([]);

  const API = "http://127.0.0.1:8000/api";

  useEffect(() => {
    fetchPortfolios();
  }, []);

  const fetchPortfolios = async () => {
    try {
      const res = await axios.get(`${API}/portfolio/`);
      setPortfolios(res.data);
    } catch (error) {
      console.error("Portfolio fetch error:", error);
    }
  };

  const handlePortfolioChange = async (portfolioId) => {
    setSelectedPortfolio(portfolioId);

    if (!portfolioId) return;

    try {
      const res = await axios.get(`${API}/stocks/?portfolio=${portfolioId}`);
      setStocks(res.data);
    } catch (error) {
      console.error("Stock fetch error:", error);
    }
  };

  return (
    <>
      <Navbar />

      <div className="portfolio-container">
        <h1 className="portfolio-title">
          Select Portfolio
        </h1>

        {/* DROPDOWN */}
        <select
          className="portfolio-dropdown"
          value={selectedPortfolio}
          onChange={(e) => handlePortfolioChange(e.target.value)}
        >
          <option value="">-- Select Portfolio --</option>
          {portfolios.map((portfolio) => (
            <option key={portfolio.id} value={portfolio.id}>
              {portfolio.name}
            </option>
          ))}
        </select>

        {/* STOCK LIST */}
        {selectedPortfolio && (
          <div className="portfolio-stocks">
            <h2>Indian Stocks in Portfolio</h2>

            {stocks.length === 0 ? (
              <p>No stocks available.</p>
            ) : (
              <table className="stocks-table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Price</th>
                    <th>PE Ratio</th>
                  </tr>
                </thead>
                <tbody>
                  {stocks.map((stock) => (
                    <tr key={stock.id}>
                      <td>{stock.symbol}</td>
                      <td className="price-green">
                        ₹ {stock.price}
                      </td>
                      <td>{stock.pe_ratio}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

          </div>
        )}
      </div>
    </>
  );
}