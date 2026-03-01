import { useEffect, useState } from "react";
import axios from "axios";

import Navbar from "../components/Navbar";
import AnalysisPanel from "../components/AnalysisPanel";
import PortfolioChart from "../components/PortfolioChart";
import StocksCard from "../components/StocksCard";

import "./Dashboard.css";

export default function Dashboard() {

  const [portfolios, setPortfolios] = useState([]);
  const [stocks, setStocks] = useState([]);

  const API = "http://127.0.0.1:8000/api";

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const portfolioRes = await axios.get(`${API}/portfolio/`);
      const stockRes = await axios.get(`${API}/stocks/`);

      setPortfolios(portfolioRes.data);
      setStocks(stockRes.data);

    } catch (error) {
      console.error("API Error:", error);
    }
  };

  return (
    <div className="dashboard-page">

      <Navbar />

      <div className="dashboard-container">

        <h1 className="dashboard-title">
          Corporate Investment Dashboard
        </h1>

        <AnalysisPanel portfolios={portfolios} stocks={stocks} />

        <PortfolioChart portfolios={portfolios} />

        <StocksCard stocks={stocks} />

      </div>

    </div>
  );
}