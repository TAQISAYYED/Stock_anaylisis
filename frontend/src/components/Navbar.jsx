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
      {/* Logo */}
      <div className="nb-logo">
        <span className="nb-logo-dot" />
        WealthyTrade
      </div>

      {/* Nav links */}
      <div className="nb-links">
        <Link
          to="/"
          className={`nb-link ${isActive("/") ? "active" : ""}`}
        >
          Dashboard
        </Link>
        <Link
          to="/portfolio"
          className={`nb-link ${isActive("/portfolio") ? "active" : ""}`}
        >
          Portfolio
        </Link>
        <Link
          to="/goldsilver"
          className={`nb-link ${isActive("/goldsilver") ? "active" : ""}`}
        >
          Gold &amp; Silver
        </Link>
      </div>

      {/* Right side — user + logout */}
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
