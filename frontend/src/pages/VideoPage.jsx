import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import VideoPlayer from '../components/VideoPlayer';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function VideoPage() {
  const { id } = useParams();
  const [video, setVideo] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchVideo = () => {
      axios.get(`${API_URL}/api/videos/${id}`)
        .then(r => setVideo(r.data))
        .catch(() => setError('Video not found'));
    };

    fetchVideo();

    // Poll every 5 seconds while processing
    const interval = setInterval(() => {
      if (!video || video.status !== 'ready') {
        fetchVideo();
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [id]);

  if (error) return <div style={{ color: '#f88', padding: '40px' }}>❌ {error}</div>;
  if (!video) return <div style={{ color: '#888', padding: '40px' }}>Loading...</div>;

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '24px 20px' }}>
      
      {/* Video Player or Processing State */}
      {video.status === 'ready' ? (
        <VideoPlayer streamUrl={video.stream_url} />
      ) : video.status === 'failed' ? (
        <div style={{
          height: '400px', background: '#1a0000', borderRadius: '8px',
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column',
        }}>
          <div style={{ fontSize: '48px' }}>❌</div>
          <p style={{ color: '#f88' }}>Processing failed</p>
        </div>
      ) : (
        <div style={{
          height: '400px', background: '#111', borderRadius: '8px',
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column',
          border: '1px solid #222',
        }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>⏳</div>
          <p style={{ color: '#aaa', margin: '0 0 8px', fontSize: '18px' }}>Processing your video...</p>
          <p style={{ color: '#666', margin: 0, fontSize: '13px' }}>
            FFmpeg is transcoding to 360p, 720p, and 1080p. Usually takes 1-5 minutes.
          </p>
          <p style={{ color: '#555', margin: '8px 0 0', fontSize: '12px' }}>
            This page auto-refreshes every 5 seconds.
          </p>
        </div>
      )}

      {/* Video Info */}
      <div style={{ marginTop: '20px' }}>
        <h1 style={{ color: 'white', margin: '0 0 8px', fontSize: '22px' }}>
          {video.title}
        </h1>
        {video.description && (
          <p style={{ color: '#999', margin: '0 0 16px', lineHeight: '1.5' }}>
            {video.description}
          </p>
        )}
        <div style={{ color: '#555', fontSize: '13px' }}>
          Video ID: {video.id}
          {video.duration_seconds && ` · Duration: ${Math.floor(video.duration_seconds / 60)}:${String(video.duration_seconds % 60).padStart(2, '0')}`}
        </div>
      </div>

      <Link to="/" style={{ display: 'inline-block', marginTop: '16px', color: '#888', fontSize: '14px' }}>
        ← Back to all videos
      </Link>
    </div>
  );
}