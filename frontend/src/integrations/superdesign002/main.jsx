import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';

// Render App directly into root div - App returns a Fragment so no extra wrapper
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
