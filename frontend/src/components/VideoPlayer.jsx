import React, { useEffect, useRef, useState } from 'react';
import Hls from 'hls.js';

/**
 * Video player with HLS adaptive bitrate support.
 * 
 * What is HLS?
 * HLS = HTTP Live Streaming. The video is split into small chunks.
 * This player downloads chunks on the fly. If your internet is slow,
 * it automatically switches to a lower quality. If it's fast, it
 * switches to higher quality. This is exactly how YouTube/Netflix works.
 */
export default function VideoPlayer({ streamUrl }) {
  const videoRef = useRef(null);
  const hlsRef = useRef(null);
  const [qualities, setQualities] = useState([]);
  const [currentQuality, setCurrentQuality] = useState('Auto');
  const [playerReady, setPlayerReady] = useState(false);

  useEffect(() => {
    if (!streamUrl || !videoRef.current) return;

    // Destroy any existing HLS instance before creating new one
    if (hlsRef.current) {
      hlsRef.current.destroy();
    }

    if (Hls.isSupported()) {
      // Most browsers need hls.js to play HLS
      const hls = new Hls({
        startLevel: -1,              // -1 = auto quality on start
        capLevelToPlayerSize: true,  // don't load 1080p for a small player window
      });

      hlsRef.current = hls;
      hls.loadSource(streamUrl);
      hls.attachMedia(videoRef.current);

      // When the master playlist is parsed, we know what qualities exist
      hls.on(Hls.Events.MANIFEST_PARSED, (event, data) => {
        const availableQualities = data.levels.map((level, index) => ({
          index,
          label: `${level.height}p`,
          bitrate: level.bitrate,
        }));
        setQualities([{ index: -1, label: 'Auto' }, ...availableQualities]);
        setPlayerReady(true);
        videoRef.current.play().catch(() => {}); // auto-play (may be blocked by browser)
      });

      // Track live quality switches — this is the adaptive bitrate in action!
      hls.on(Hls.Events.LEVEL_SWITCHED, (_, data) => {
        const level = hls.levels[data.level];
        setCurrentQuality(level?.height ? `${level.height}p` : 'Auto');
      });

    } else if (videoRef.current.canPlayType('application/vnd.apple.mpegurl')) {
      // Safari has native HLS support — just set the src directly
      videoRef.current.src = streamUrl;
      setPlayerReady(true);
    }

    return () => {
      // Cleanup when component unmounts
      if (hlsRef.current) {
        hlsRef.current.destroy();
      }
    };
  }, [streamUrl]);

  const switchQuality = (index) => {
    if (hlsRef.current) {
      hlsRef.current.currentLevel = index;
    }
  };

  return (
    <div style={{ background: '#000', borderRadius: '8px', overflow: 'hidden' }}>
      
      {/* HTML5 Video Element */}
      <video
        ref={videoRef}
        controls
        style={{ width: '100%', maxHeight: '65vh', display: 'block' }}
      />
      
      {/* Quality Controls — shown below the video */}
      {playerReady && qualities.length > 0 && (
        <div style={{
          background: '#111',
          padding: '10px 16px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          flexWrap: 'wrap',
        }}>
          <span style={{ color: '#888', fontSize: '13px' }}>Quality:</span>
          {qualities.map(q => (
            <button
              key={q.index}
              onClick={() => switchQuality(q.index)}
              style={{
                padding: '4px 12px',
                fontSize: '12px',
                border: 'none',
                borderRadius: '20px',
                cursor: 'pointer',
                background: currentQuality === q.label ? '#ff4444' : '#333',
                color: 'white',
                fontWeight: currentQuality === q.label ? 'bold' : 'normal',
              }}
            >
              {q.label}
            </button>
          ))}
          <span style={{ marginLeft: 'auto', color: '#555', fontSize: '12px' }}>
            Currently: {currentQuality} · switches automatically with your connection
          </span>
        </div>
      )}
    </div>
  );
}