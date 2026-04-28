import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const STATUS_COLORS = {
  processing: '#ff9800',
  ready: '#4caf50',
  failed: '#f44336',
};

export default function HomePage() {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchVideos = () => {
      axios.get(`${API_URL}/api/videos/`)
        .then(r => { setVideos(r.data); setLoading(false); })
        .catch(() => setLoading(false));
    };

    fetchVideos();
    // Poll every 10 seconds to pick up newly processed videos
    const interval = setInterval(fetchVideos, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return <div style={{ color: '#888', padding: '40px', textAlign: 'center' }}>Loading...</div>;
  }

  return (
    <div style={{ padding: '32px 28px', maxWidth: '1200px', margin: '0 auto' }}>
      <h2 style={{ color: 'white', marginBottom: '24px' }}>
        {videos.length > 0 ? `${videos.length} Videos` : 'No Videos Yet'}
      </h2>

      {videos.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '60px', color: '#555' }}>
          <p style={{ fontSize: '48px', margin: '0 0 16px' }}>📹</p>
          <p>No videos uploaded yet. <Link to="/upload" style={{ color: '#ff4444' }}>Upload the first one!</Link></p>
        </div>
      ) : (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
          gap: '20px',
        }}>
          {videos.map(video => (
            <Link
              key={video.id}
              to={`/watch/${video.id}`}
              style={{ textDecoration: 'none', color: 'white' }}
            >
              <div style={{
                background: '#1a1a1a',
                borderRadius: '8px',
                overflow: 'hidden',
                transition: 'transform 0.2s',
                cursor: 'pointer',
                border: '1px solid #2a2a2a',
              }}
              onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-2px)'}
              onMouseLeave={e => e.currentTarget.style.transform = 'translateY(0)'}
              >
                {/* Thumbnail */}
                <div style={{
                  height: '158px',
                  background: '#222',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '36px',
                }}>
                  {video.status === 'ready' ? '▶' : video.status === 'failed' ? '❌' : '⏳'}
                </div>

                {/* Info */}
                <div style={{ padding: '12px' }}>
                  <div style={{ fontWeight: '600', marginBottom: '4px', lineHeight: '1.3' }}>
                    {video.title}
                  </div>
                  <div style={{ fontSize: '12px', color: '#888' }}>
                    Status:{' '}
                    <span style={{ color: STATUS_COLORS[video.status] || '#888' }}>
                      {video.status}
                    </span>
                    {video.duration_seconds && (
                      <span style={{ marginLeft: '8px' }}>
                        · {Math.floor(video.duration_seconds / 60)}:{String(video.duration_seconds % 60).padStart(2, '0')}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}