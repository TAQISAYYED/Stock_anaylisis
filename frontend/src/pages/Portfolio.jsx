import { useState, useEffect } from "react";
import axios from "axios";
import Navbar from "../components/Navbar";

import "./Portfolio.css";

export default function Portfolio() {

  const [portfolios, setPortfolios] = useState([]);
  const [name, setName] = useState("");

  const API = "http://127.0.0.1:8000/api";

  useEffect(() => {
    fetchPortfolio();
  }, []);

  const fetchPortfolio = async () => {
    const res = await axios.get(`${API}/portfolio/`);
    setPortfolios(res.data);
  };

  const createPortfolio = async () => {
    if (!name) return;

    await axios.post(`${API}/portfolio/`, { name });
    setName("");
    fetchPortfolio();
  };

  return (
    <div>

      <Navbar />

      <div className="portfolio-container">

        <h1 className="portfolio-title">
          Manage Your Investment Portfolios
        </h1>

        <div className="portfolio-form">
          <input
            type="text"
            placeholder="Enter Portfolio Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />

          <button onClick={createPortfolio}>
            Create Portfolio
          </button>
        </div>

        <ul className="portfolio-list">
          {portfolios.map((p) => (
            <li key={p.id}>
              {p.name}
            </li>
          ))}
        </ul>

      </div>

    </div>
  );
}