import { useEffect, useState } from "react";
import api from "../services/api";
import Navbar from "../components/Navbar";
import "./GoldSilver.css";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ScatterChart, Scatter,
  ResponsiveContainer
} from "recharts";

const USD_TO_INR = 83.5;
const OUNCE_TO_GRAM = 31.1035;

// Convert USD per ounce → INR per 10 grams
const convertToINR10g = (usdPerOunce) =>
  ((usdPerOunce * USD_TO_INR) / OUNCE_TO_GRAM) * 10;

const formatINR = (value) =>
  `₹${value.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;

export default function GoldSilver() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const res = await api.get("http://127.0.0.1:8000/api/goldsilver/");
      setData(res.data);
    } catch (err) {
      setError("Failed to load data. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  if (loading) return (
    <div className="gs-loading">
      <div className="gs-spinner"></div>
      <p>Loading Gold & Silver Analysis...</p>
    </div>
  );

  if (error) return (
    <div className="gs-error">
      <span>⚠️</span>
      <p>{error}</p>
    </div>
  );

  // Convert price history
  const priceHistoryINR = data.price_history.map(d => ({
    ...d,
    gold: +convertToINR10g(d.gold).toFixed(0),
    silver: +convertToINR10g(d.silver).toFixed(0),
  }));

  // Convert regression data
  const regressionINR = data.regression_data.map(d => ({
    gold: +convertToINR10g(d.gold).toFixed(0),
    silver_actual: +convertToINR10g(d.silver_actual).toFixed(0),
    silver_predicted: +convertToINR10g(d.silver_predicted).toFixed(0),
  }));

  // Convert future predictions
  const predictionsINR = data.predictions.map(d => ({
    ...d,
    gold: +convertToINR10g(d.gold).toFixed(0),
    silver_predicted: +convertToINR10g(d.silver_predicted).toFixed(0),
  }));

  return (
    <div className="gs-page">

      <div className="gs-container">

        <div className="gs-header">
          <h1>🥇 Gold & Silver Analysis</h1>
          <p>5 Year Historical Data · Linear Regression · Prices in INR per 10g</p>
        </div>

        <div className="gs-cards">
          <div className="gs-card gold">
            <div className="gs-card-icon">📈</div>
            <div className="gs-card-value">{data.correlation}</div>
            <div className="gs-card-label">Correlation</div>
          </div>
          <div className="gs-card silver">
            <div className="gs-card-icon">📊</div>
            <div className="gs-card-value">{data.r2_score}</div>
            <div className="gs-card-label">R² Score</div>
          </div>
          <div className="gs-card blue">
            <div className="gs-card-icon">📉</div>
            <div className="gs-card-value">{data.slope}</div>
            <div className="gs-card-label">Regression Slope</div>
          </div>
          <div className="gs-card green">
            <div className="gs-card-icon">💰</div>
            <div className="gs-card-value">
              {formatINR(convertToINR10g(data.price_history.at(-1)?.gold || 0))}
            </div>
            <div className="gs-card-label">Latest Gold Price (₹ per 10g)</div>
          </div>
        </div>

        <div className="gs-chart-box">
          <h2>📈 Price History — Last 5 Years (INR per 10g)</h2>
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={priceHistoryINR}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3e" />
              <XAxis dataKey="date" stroke="#888" tick={{ fontSize: 11 }}
                tickFormatter={(v) => v.slice(0, 7)} interval={5} />
              <YAxis stroke="#888" tickFormatter={(v) => `₹${(v/1000).toFixed(0)}k`} />
              <Tooltip
                contentStyle={{ backgroundColor: "#1a1a2e", border: "1px solid #FFD700", borderRadius: "8px" }}
                formatter={(value, name) => [`₹${value.toLocaleString("en-IN")}`, name]}
              />
              <Legend />
              <Line type="monotone" dataKey="gold" stroke="#FFD700" dot={false} strokeWidth={2.5} name="Gold" />
              <Line type="monotone" dataKey="silver" stroke="#C0C0C0" dot={false} strokeWidth={2.5} name="Silver" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="gs-chart-box">
          <h2>📊 Linear Regression — Gold vs Silver (INR per 10g)</h2>
          <ResponsiveContainer width="100%" height={320}>
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3e" />
              <XAxis dataKey="gold" stroke="#888"
                tickFormatter={(v) => `₹${(v/1000).toFixed(0)}k`} />
              <YAxis dataKey="silver_actual" stroke="#888"
                tickFormatter={(v) => `₹${(v/1000).toFixed(1)}k`} />
              <Tooltip
                contentStyle={{ backgroundColor: "#1a1a2e", border: "1px solid #FFD700", borderRadius: "8px" }}
                formatter={(value) => [`₹${value.toLocaleString("en-IN")}`]}
              />
              <Legend />
              <Scatter name="Actual Silver" data={regressionINR} fill="#C0C0C0" />
              <Scatter
                name="Predicted Silver"
                data={regressionINR.map(d => ({
                  gold: d.gold,
                  silver_actual: d.silver_predicted
                }))}
                fill="#FFD700"
                line
              />
            </ScatterChart>
          </ResponsiveContainer>
        </div>

        <div className="gs-chart-box">
          <h2>🔮 Future Price Predictions — Next 6 Months (INR per 10g)</h2>
          <table className="gs-table">
            <thead>
              <tr>
                <th>Period</th>
                <th>Gold (₹ per 10g)</th>
                <th>Silver (₹ per 10g)</th>
                <th>Trend</th>
              </tr>
            </thead>
            <tbody>
              {predictionsINR.map((p, i) => (
                <tr key={i}>
                  <td>{p.month}</td>
                  <td className="gold-text">₹{p.gold.toLocaleString("en-IN")}</td>
                  <td className="silver-text">₹{p.silver_predicted.toLocaleString("en-IN")}</td>
                  <td>
                    <span className={`gs-badge ${i === 0 ? "neutral" : "up"}`}>
                      {i === 0 ? "→ Base" : "↑ Rising"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

      </div>
    </div>
  );
}