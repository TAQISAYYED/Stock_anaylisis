import { useContext } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { AuthContext } from "../context/AuthContext";
import "./Navbar.css";

export default function Navbar() {
  const { user, logout } = useContext(AuthContext);
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const isActive = (path) => location.pathname === path;

  return (
    <nav className="nb-root">
      <div className="nb-logo">
        <span className="nb-logo-dot" />
        Wealthy<span className="nb-logo-accent">Trade</span>
      </div>

      
      <div className="nb-links">
        <Link to="/"                 className={`nb-link ${isActive("/")                  ? "active" : ""}`}>Dashboard</Link>
        <Link to="/portfolio"        className={`nb-link ${isActive("/portfolio")         ? "active" : ""}`}>Portfolio</Link>
        <Link to="/goldsilver"       className={`nb-link ${isActive("/goldsilver")        ? "active" : ""}`}>Gold &amp; Silver</Link>
        <Link to="/cluster-analysis" className={`nb-link ${isActive("/cluster-analysis")  ? "active" : ""}`}>Cluster Analysis</Link>
        <Link to="/forecasting"      className={`nb-link ${isActive("/forecasting")       ? "active" : ""}`}>Forecasting</Link>
      </div>

    
      <div className="nb-right">
        {user && (
          <span className="nb-user">
            <span className="nb-user-dot" />
            {user}
          </span>
        )}
        <button className="nb-logout-btn" onClick={handleLogout}>
          Logout
        </button>
      </div>
    </nav>
  );
}
