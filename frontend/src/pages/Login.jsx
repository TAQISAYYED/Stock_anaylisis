
import { useState, useContext } from "react";
import { AuthContext } from "../context/AuthContext";
import { useNavigate, Link } from "react-router-dom";
import "./Login.css";

const Login = () => {
  const { login } = useContext(AuthContext);
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await login(form);
      navigate("/");
    } catch (err) {
      setError("Invalid username or password.");
      console.log("Login error:", err.response?.data);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ln-root">
      <div className="ln-bg-glow" />

      <div className="ln-card">
        {/* Logo */}
        <div className="ln-logo">
          <span className="ln-logo-dot" />
          WealthyTrade
        </div>

        <h1 className="ln-title">Welcome back</h1>
        <p className="ln-sub">Sign in to your account to continue</p>

        {error && (
          <div className="ln-error">
            <span>⚠</span> {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="ln-form">
          <div className="ln-field">
            <label className="ln-label">USERNAME</label>
            <input
              type="text"
              className="ln-input"
              placeholder="Enter your username"
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              autoComplete="username"
              required
            />
          </div>

          <div className="ln-field">
            <label className="ln-label">PASSWORD</label>
            <input
              type="password"
              className="ln-input"
              placeholder="Enter your password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              autoComplete="current-password"
              required
            />
          </div>

          <button
            type="submit"
            className="ln-btn"
            disabled={loading}
          >
            {loading ? (
              <span className="ln-spinner" />
            ) : (
              "Sign In"
            )}
          </button>
        </form>

        <p className="ln-register">
          No account?{" "}
          <Link to="/register" className="ln-register-link">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
};

export default Login;
