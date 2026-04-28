import React from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import HomePage from './pages/HomePage';
import UploadPage from './pages/UploadPage';
import VideoPage from './pages/VideoPage';

function App() {
  return (
    <BrowserRouter>
      <div style={{ minHeight: '100vh', background: '#0f0f0f', color: 'white' }}>
        
        {/* Navigation Bar */}
        <nav style={{
          background: '#1a1a1a',
          padding: '14px 28px',
          display: 'flex',
          alignItems: 'center',
          gap: '28px',
          borderBottom: '1px solid #333',
        }}>
          <Link to="/" style={{ color: 'white', fontSize: '22px', fontWeight: 'bold', textDecoration: 'none' }}>
            ▶ StreamFlow
          </Link>
          <Link to="/upload" style={{ color: '#aaa', textDecoration: 'none', fontSize: '15px' }}>
            Upload Video
          </Link>
        </nav>

        {/* Page Content */}
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/watch/:id" element={<VideoPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;