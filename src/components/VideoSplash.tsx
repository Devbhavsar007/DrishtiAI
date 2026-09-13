import React, { useState, useRef, useEffect, useCallback } from 'react';

/**
 * VideoSplash — Cinematic full-screen intro that plays the DrishtiAI
 * promo video once before revealing the main application.
 *
 * Behaviour:
 *  • Auto-plays (muted first to satisfy browser autoplay policies, then
 *    unmutes after the first user gesture).
 *  • Fades out gracefully when the video ends.
 *  • Stores a sessionStorage flag so the splash only shows once per session.
 *  • On mobile / reduced-motion preference the splash is skipped entirely.
 */

interface VideoSplashProps {
  onComplete: () => void;
  /** When true, the skip button is hidden and the video must play to completion. */
  unskippable?: boolean;
}

export const VideoSplash: React.FC<VideoSplashProps> = ({ onComplete, unskippable = false }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [fadeOut, setFadeOut] = useState(false);
  const [progress, setProgress] = useState(0);
  const [showSkip, setShowSkip] = useState(false);
  const [isMuted, setIsMuted] = useState(true);

  // Show skip button after 2 seconds (only if skippable)
  useEffect(() => {
    if (unskippable) return;
    const timer = setTimeout(() => setShowSkip(true), 2000);
    return () => clearTimeout(timer);
  }, [unskippable]);

  // Try to unmute on first click/tap anywhere
  useEffect(() => {
    const tryUnmute = () => {
      if (videoRef.current && videoRef.current.muted) {
        videoRef.current.muted = false;
        setIsMuted(false);
      }
      document.removeEventListener('click', tryUnmute);
      document.removeEventListener('touchstart', tryUnmute);
    };
    document.addEventListener('click', tryUnmute, { once: true });
    document.addEventListener('touchstart', tryUnmute, { once: true });
    return () => {
      document.removeEventListener('click', tryUnmute);
      document.removeEventListener('touchstart', tryUnmute);
    };
  }, []);

  const handleEnd = useCallback(() => {
    setFadeOut(true);
    setTimeout(() => {
      sessionStorage.setItem('drishti_splash_seen', '1');
      onComplete();
    }, 800);
  }, [onComplete]);

  const handleSkip = useCallback(() => {
    if (videoRef.current) {
      videoRef.current.pause();
    }
    handleEnd();
  }, [handleEnd]);

  const handleTimeUpdate = useCallback(() => {
    if (videoRef.current && videoRef.current.duration) {
      setProgress((videoRef.current.currentTime / videoRef.current.duration) * 100);
    }
  }, []);

  return (
    <div
      className={`fixed inset-0 z-[9999] bg-black flex items-center justify-center transition-opacity duration-700 ${
        fadeOut ? 'opacity-0 pointer-events-none' : 'opacity-100'
      }`}
      role="dialog"
      aria-label="DrishtiAI intro"
    >
      {/* Video */}
      <video
        ref={videoRef}
        src="/intro.mp4"
        autoPlay
        muted
        playsInline
        onEnded={handleEnd}
        onTimeUpdate={handleTimeUpdate}
        className="w-full h-full object-contain"
        style={{ background: '#000' }}
      />

      {/* Bottom gradient overlay for controls */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-black/80 to-transparent pointer-events-none" />

      {/* Progress bar */}
      <div className="absolute bottom-0 left-0 right-0 h-1 bg-white/10">
        <div
          className="h-full bg-[#E1FA4A] transition-all duration-200 ease-linear"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Bottom controls */}
      <div className="absolute bottom-6 left-0 right-0 flex items-center justify-between px-8">
        {/* Brand badge */}
        <div className="flex items-center gap-3 select-none">
          <div className="w-10 h-10 rounded-2xl bg-[#619FE8] flex items-center justify-center shadow-lg">
            <svg viewBox="0 0 24 24" className="w-5 h-5 text-white" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          </div>
          <div>
            <div className="text-white font-bold text-sm tracking-tight" style={{ fontFamily: "'Inter', sans-serif" }}>
              DrishtiAI
            </div>
            <div className="text-white/50 text-[10px] font-medium tracking-wider uppercase">
              Clinical Retinal Intelligence
            </div>
          </div>
        </div>

        {/* Skip button — hidden when unskippable (app / PWA mode) */}
        {!unskippable && (
          <button
            onClick={handleSkip}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-full text-xs font-bold bg-white/10 hover:bg-white/20 text-white border border-white/20 backdrop-blur-xl transition-all cursor-pointer shadow-lg ${
              showSkip ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4 pointer-events-none'
            }`}
            style={{ transition: 'opacity 0.5s ease, transform 0.5s ease, background 0.2s ease' }}
          >
            <span>Skip Intro</span>
            <svg viewBox="0 0 24 24" className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M5 4l10 8-10 8V4Z" />
              <line x1="19" y1="5" x2="19" y2="19" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
};
