import React, { useCallback, useEffect, useState } from 'react';
import BootSequence from './BootSequence';
import {
  playDegauss,
  playPowerClunk,
  stopAllAudio,
  unlockAudio,
} from './retroAudio';
import './RetroShell.css';

function prefersReducedMotion() {
  return (
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );
}

// Void backdrop -> "enter" button -> dial-in boot -> title card (waits for a
// key or tap) -> the game terminal. The terminal stays mounted underneath the
// boot overlay so the socket connects and the login prompt is ready.
export default function RetroShell({ children, onLit }) {
  const [phase, setPhase] = useState('landing'); // landing | booting | on
  const [fullscreen, setFullscreen] = useState(
    () => localStorage.getItem('retroFullscreen') === '1'
  );

  useEffect(() => {
    localStorage.setItem('retroFullscreen', fullscreen ? '1' : '0');
  }, [fullscreen]);

  const finishBoot = useCallback(() => {
    stopAllAudio();
    setPhase('on');
    if (onLit) onLit();
  }, [onLit]);

  const enterRealm = () => {
    // This click is the user gesture that unlocks WebAudio.
    unlockAudio();
    playPowerClunk();
    playDegauss();
    setPhase('booting');
  };

  useEffect(() => {
    if (phase !== 'booting') return undefined;
    const onKey = (e) => {
      if (e.key === 'Escape') finishBoot();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [phase, finishBoot]);

  const toggleFullscreen = () => {
    setFullscreen((f) => !f);
    // Hand focus straight back to the game input.
    if (onLit) onLit();
  };

  return (
    <div
      className={`retro-stage retro-phase--${phase}${
        fullscreen ? ' retro-mode--full' : ''
      }`}
    >
      <div className="retro-glow" aria-hidden="true" />

      {phase === 'landing' && (
        <button type="button" className="retro-enter" onClick={enterRealm}>
          ENTER MOURNVALE
        </button>
      )}

      {phase === 'on' && (
        <button
          type="button"
          className="term-mode-toggle"
          onClick={toggleFullscreen}
          aria-label="Toggle fullscreen"
        >
          {fullscreen ? 'WINDOWED' : 'FULLSCREEN'}
        </button>
      )}

      <div className="term-shell">
        <div className="term-content">{children}</div>
        {phase === 'booting' && (
          <div className="term-overlay">
            <BootSequence
              reduced={prefersReducedMotion()}
              onDone={finishBoot}
            />
            <button type="button" className="boot-skip" onClick={finishBoot}>
              ESC &middot; SKIP
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
