import React, { useState } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function UploadPage() {
  const [file, setFile] = useState(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [status, setStatus] = useState('idle');  // idle | uploading | done | error
  const [videoId, setVideoId] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!file) {
      alert('Please select a video file');
      return;
    }
    if (!title.trim()) {
      alert('Please enter a title');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', title);
    formData.append('description', description);

    setStatus('uploading');
    setErrorMessage('');

    try {
      const response = await axios.post(`${API_URL}/api/upload/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          const percent = Math.round((progressEvent.loaded / progressEvent.total) * 100);
          setUploadProgress(percent);
        },
      });

      setVideoId(response.data.video_id);
      setStatus('done');

    } catch (error) {
      setStatus('error');
      setErrorMessage(error.response?.data?.detail || 'Upload failed. Please try again.');
    }
  };

  const inputStyle = {
    width: '100%',
    padding: '12px',
    background: '#1a1a1a',
    color: 'white',
    border: '1px solid #333',
    borderRadius: '6px',
    fontSize: '15px',
    boxSizing: 'border-box',
  };

  return (
    <div style={{ maxWidth: '600px', margin: '40px auto', padding: '0 20px' }}>
      <h2 style={{ color: 'white', marginBottom: '24px' }}>Upload Video</h2>

      {status === 'done' ? (
        <div style={{ background: '#1a3a1a', border: '1px solid #4caf50', borderRadius: '8px', padding: '24px' }}>
          <h3 style={{ color: '#4caf50', margin: '0 0 12px 0' }}>✓ Upload Successful!</h3>
          <p style={{ color: '#ccc', margin: '0 0 16px 0' }}>
            Your video is now being processed. This takes 1-5 minutes depending on file size.
          </p>
          <a
            href={`/watch/${videoId}`}
            style={{
              display: 'inline-block',
              padding: '10px 20px',
              background: '#ff4444',
              color: 'white',
              textDecoration: 'none',
              borderRadius: '6px',
            }}
          >
            Watch Video (refreshes automatically)
          </a>
        </div>
      ) : (
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          
          {/* File Input */}
          <div>
            <label style={{ color: '#aaa', display: 'block', marginBottom: '6px', fontSize: '14px' }}>
              Video File
            </label>
            <input
              type="file"
              accept="video/*"
              onChange={(e) => setFile(e.target.files[0])}
              style={{ ...inputStyle, cursor: 'pointer' }}
              required
            />
            {file && (
              <p style={{ color: '#888', fontSize: '12px', margin: '4px 0 0 0' }}>
                Selected: {file.name} ({(file.size / 1024 / 1024).toFixed(1)} MB)
              </p>
            )}
          </div>

          {/* Title */}
          <div>
            <label style={{ color: '#aaa', display: 'block', marginBottom: '6px', fontSize: '14px' }}>
              Title *
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Enter video title"
              style={inputStyle}
              required
            />
          </div>

          {/* Description */}
          <div>
            <label style={{ color: '#aaa', display: 'block', marginBottom: '6px', fontSize: '14px' }}>
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe your video..."
              rows={4}
              style={{ ...inputStyle, resize: 'vertical' }}
            />
          </div>

          {/* Upload Progress Bar */}
          {status === 'uploading' && (
            <div>
              <div style={{ background: '#333', borderRadius: '4px', overflow: 'hidden', height: '8px' }}>
                <div style={{
                  width: `${uploadProgress}%`,
                  height: '100%',
                  background: '#ff4444',
                  transition: 'width 0.3s ease',
                }} />
              </div>
              <p style={{ color: '#888', fontSize: '13px', margin: '6px 0 0 0', textAlign: 'center' }}>
                Uploading: {uploadProgress}%
              </p>
            </div>
          )}

          {/* Error Message */}
          {status === 'error' && (
            <div style={{ background: '#3a1a1a', border: '1px solid #f44', borderRadius: '6px', padding: '12px' }}>
              <p style={{ color: '#f88', margin: 0 }}>❌ {errorMessage}</p>
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={status === 'uploading'}
            style={{
              padding: '14px',
              background: status === 'uploading' ? '#666' : '#ff4444',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              fontSize: '16px',
              cursor: status === 'uploading' ? 'not-allowed' : 'pointer',
              fontWeight: 'bold',
            }}
          >
            {status === 'uploading' ? `Uploading ${uploadProgress}%...` : 'Upload Video'}
          </button>
        </form>
      )}
    </div>
  );
}