import "./Navbar.css";
import { Link } from "react-router-dom";

export default function Navbar() {
  return (
    <nav className="navbar">
      <div className="logo">
        💰 WealthyTrade
      </div>

      <div className="nav-links">
        <Link to="/" className="nav-item">Dashboard</Link>
        <Link to="/portfolio" className="nav-item">Portfolio</Link>
        <span className="nav-item">Markets</span>
      </div>
    </nav>
  );
}