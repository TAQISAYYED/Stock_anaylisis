import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';

import './index.css';
import App from './App';
import "./styles/theme.css";
import { AuthProvider } from './context/AuthContext';  // ← add this

const root = ReactDOM.createRoot(document.getElementById('root'));

root.render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>        {/* ← add this */}
        <App />
      </AuthProvider>       {/* ← add this */}
    </BrowserRouter>
  </React.StrictMode>
);