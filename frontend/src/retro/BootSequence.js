import React, { useEffect, useRef, useState } from 'react';
import { playBeep, playKeyTick, playModemHandshake } from './retroAudio';

function TitleCard() {
  return (
    <div className="boot-title">
      <div className="boot-title__frame">
        <p className="boot-title__over">CHRONOS ONLINE SERVICE PRESENTS</p>
        <h1>THE FORGOTTEN REALMS</h1>
        <p className="boot-title__sub">A MULTI-USER DUNGEON &middot; EST. 1987</p>
        <p className="boot-title__conn">CONNECT 2400 &middot; 8-N-1</p>
        <p className="boot-title__press">PRESS ANY KEY</p>
      </div>
    </div>
  );
}

// Plays the dial-in boot ritual, then holds on the title card until the user
// presses a key (or taps, on touch devices) before calling onDone.
// Cancellation: cleanup clears all pending timers, so the async runner simply
// never resumes after unmount.
export default function BootSequence({ reduced, onDone }) {
  const [lines, setLines] = useState([]);
  const [typing, setTyping] = useState('');
  const [showTitle, setShowTitle] = useState(false);
  const doneRef = useRef(onDone);
  doneRef.current = onDone;

  useEffect(() => {
    if (!showTitle) return undefined;
    const enter = () => doneRef.current();
    window.addEventListener('keydown', enter);
    window.addEventListener('pointerdown', enter);
    return () => {
      window.removeEventListener('keydown', enter);
      window.removeEventListener('pointerdown', enter);
    };
  }, [showTitle]);

  useEffect(() => {
    const speed = reduced ? 0.12 : 1;
    const timers = [];
    let alive = true;

    const wait = (ms) =>
      new Promise((resolve) => {
        timers.push(setTimeout(resolve, Math.max(1, ms * speed)));
      });

    const pushLine = (text) => {
      if (!alive) return;
      setLines((prev) => [...prev, text]);
      setTyping('');
    };

    const println = async (text, pause = 120) => {
      pushLine(text);
      await wait(pause);
    };

    const typeLine = async (text, prefix = '') => {
      let acc = prefix;
      setTyping(acc);
      await wait(220);
      for (const ch of text) {
        if (!alive) return;
        acc += ch;
        setTyping(acc);
        if (ch !== ' ') playKeyTick();
        await wait(26 + Math.random() * 34);
      }
      await wait(260);
      pushLine(acc);
    };

    const countUp = async (format, from, to, step, ms) => {
      for (let v = from; v <= to; v += step) {
        if (!alive) return;
        setTyping(format(v));
        await wait(ms);
      }
      pushLine(format(to));
    };

    const run = async () => {
      await wait(820); // warm-up bloom plays over this pause
      await println('CHRONOS SYSTEMS PC BIOS v2.3', 240);
      await println('CPU: 8086-2 @ 4.77 MHZ', 170);
      await countUp((v) => `RAM CHECK: ${v}K`, 64, 640, 64, 70);
      playBeep();
      await println('FLOPPY A: OK   RTC: OK   CGA: OK', 420);
      await println('', 140);
      await typeLine('REALMS.EXE', 'C:\\> ');
      await wait(420);
      await println('CHRONOS ONLINE SERVICE LOADER v1.1', 220);
      await println('MODEM FOUND ON COM1', 300);
      await typeLine('ATDT 1-800-CHRONOS');
      playModemHandshake();
      for (let i = 0; i < 11; i += 1) {
        if (!alive) return;
        setTyping(`NEGOTIATING CARRIER${'.'.repeat(i % 4)}`);
        await wait(300);
      }
      pushLine('CONNECT 2400');
      await wait(750);
      if (!alive) return;
      setShowTitle(true);
      playBeep();
    };

    run();

    return () => {
      alive = false;
      timers.forEach(clearTimeout);
    };
  }, [reduced]);

  return (
    <div className="boot-screen">
      <div className="boot-bloom" />
      {showTitle ? (
        <TitleCard />
      ) : (
        <div className="boot-lines">
          {lines.map((line, i) => (
            <pre key={i}>{line || ' '}</pre>
          ))}
          <pre>
            {typing}
            <span className="boot-cursor">▮</span>
          </pre>
        </div>
      )}
    </div>
  );
}
