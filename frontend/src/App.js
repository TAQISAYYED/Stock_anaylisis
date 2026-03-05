import { useContext } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { AuthContext } from "./context/AuthContext";
import Navbar from "./components/Navbar";
import Dashboard from "./pages/Dashboard";
import Portfolio from "./pages/Portfolio";
import Login from "./pages/Login";
import Register from "./pages/Register";
import GoldSilver from "./pages/GoldSilver";

// Protects routes — redirects to /login if not authenticated
function PrivateRoute({ children }) {
  const { user } = useContext(AuthContext);
  const token = localStorage.getItem("access");
  if (!user && !token) return <Navigate to="/login" replace />;
  return children;
}

// Redirects logged-in users away from login/register
function PublicRoute({ children }) {
  const { user } = useContext(AuthContext);
  const token = localStorage.getItem("access");
  if (user || token) return <Navigate to="/" replace />;
  return children;
}

function App() {
  const { user } = useContext(AuthContext);
  const token = localStorage.getItem("access");
  const isLoggedIn = !!(user || token);

  return (
    <>
      {/* Only show Navbar when logged in */}
      {isLoggedIn && <Navbar />}

      <Routes>
        {/* Public routes */}
        <Route
          path="/login"
          element={
            <PublicRoute>
              <Login />
            </PublicRoute>
          }
        />
        <Route
          path="/register"
          element={
            <PublicRoute>
              <Register />
            </PublicRoute>
          }
        />

        {/* Protected routes */}
        <Route
          path="/"
          element={
            <PrivateRoute>
              <Dashboard />
            </PrivateRoute>
          }
        />
        <Route
          path="/portfolio"
          element={
            <PrivateRoute>
              <Portfolio />
            </PrivateRoute>
          }
        />
        <Route
          path="/goldsilver"
          element={
            <PrivateRoute>
              <GoldSilver />
            </PrivateRoute>
          }
        />

        {/* Catch all — redirect to login */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </>
  );
}

export default App;