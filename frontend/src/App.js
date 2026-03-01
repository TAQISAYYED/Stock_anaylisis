import { Routes, Route } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Portfolio from "./pages/Portfolio";

function App() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/portfolio" element={<Portfolio />} />
    </Routes>
  );
}

export default App;