// WebAudio-synthesized retro hardware sounds. Every function no-ops when
// audio is unavailable (jsdom, autoplay-blocked, etc). The AudioContext is
// created on the power-switch click, which doubles as the browser's required
// user gesture for audio.
let ctx = null;
let master = null;

function ensureContext() {
  if (typeof window === 'undefined') return null;
  const AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return null;
  try {
    if (!ctx) {
      ctx = new AC();
    }
    if (ctx.state === 'suspended') {
      ctx.resume();
    }
    if (!master) {
      master = ctx.createGain();
      master.gain.value = 0.22;
      master.connect(ctx.destination);
    }
    return ctx;
  } catch (err) {
    return null;
  }
}

export function unlockAudio() {
  ensureContext();
}

export function stopAllAudio() {
  if (!ctx || !master) return;
  try {
    master.disconnect();
  } catch (err) {
    /* already disconnected */
  }
  master = null;
  ensureContext();
}

function noiseBuffer(c, seconds) {
  const buffer = c.createBuffer(
    1,
    Math.max(1, Math.floor(c.sampleRate * seconds)),
    c.sampleRate
  );
  const data = buffer.getChannelData(0);
  for (let i = 0; i < data.length; i += 1) {
    data[i] = Math.random() * 2 - 1;
  }
  return buffer;
}

function playNoise(c, opts) {
  const {
    at = 0,
    duration = 0.1,
    gain = 0.4,
    filterType = 'lowpass',
    frequency = 1000,
  } = opts;
  const src = c.createBufferSource();
  src.buffer = noiseBuffer(c, duration);
  const filter = c.createBiquadFilter();
  filter.type = filterType;
  filter.frequency.value = frequency;
  const g = c.createGain();
  const t = c.currentTime + at;
  g.gain.setValueAtTime(gain, t);
  g.gain.exponentialRampToValueAtTime(0.001, t + duration);
  src.connect(filter);
  filter.connect(g);
  g.connect(master);
  src.start(t);
  src.stop(t + duration + 0.02);
}

function playTone(c, opts) {
  const {
    at = 0,
    duration = 0.1,
    gain = 0.2,
    frequency = 440,
    type = 'sine',
    endFrequency = null,
  } = opts;
  const osc = c.createOscillator();
  osc.type = type;
  const t = c.currentTime + at;
  osc.frequency.setValueAtTime(frequency, t);
  if (endFrequency) {
    osc.frequency.exponentialRampToValueAtTime(endFrequency, t + duration);
  }
  const g = c.createGain();
  g.gain.setValueAtTime(gain, t);
  g.gain.exponentialRampToValueAtTime(0.001, t + duration);
  osc.connect(g);
  g.connect(master);
  osc.start(t);
  osc.stop(t + duration + 0.02);
}

export function playPowerClunk() {
  const c = ensureContext();
  if (!c) return;
  try {
    playNoise(c, { duration: 0.05, gain: 0.5, frequency: 900 });
    playTone(c, { duration: 0.14, gain: 0.5, frequency: 80, endFrequency: 40 });
  } catch (err) {
    /* audio unavailable */
  }
}

export function playDegauss() {
  const c = ensureContext();
  if (!c) return;
  try {
    playTone(c, { duration: 0.55, gain: 0.35, frequency: 130, endFrequency: 35 });
    playNoise(c, { duration: 0.3, gain: 0.1, frequency: 420 });
  } catch (err) {
    /* audio unavailable */
  }
}

export function playBeep() {
  const c = ensureContext();
  if (!c) return;
  try {
    playTone(c, { duration: 0.12, gain: 0.16, frequency: 880, type: 'square' });
  } catch (err) {
    /* audio unavailable */
  }
}

export function playKeyTick() {
  const c = ensureContext();
  if (!c) return;
  try {
    playNoise(c, {
      duration: 0.014,
      gain: 0.07,
      filterType: 'highpass',
      frequency: 2500,
    });
  } catch (err) {
    /* audio unavailable */
  }
}

export function playModemHandshake() {
  const c = ensureContext();
  if (!c) return;
  try {
    const dtmf = [
      [941, 1336],
      [697, 1209],
      [852, 1336],
      [770, 1477],
      [697, 1336],
      [941, 1209],
      [852, 1209],
      [770, 1336],
    ];
    dtmf.forEach((pair, i) => {
      const at = 0.12 + i * 0.11;
      playTone(c, { at, duration: 0.08, gain: 0.1, frequency: pair[0] });
      playTone(c, { at, duration: 0.08, gain: 0.1, frequency: pair[1] });
    });
    playTone(c, { at: 1.15, duration: 0.5, gain: 0.13, frequency: 2100 });
    playTone(c, { at: 1.75, duration: 0.4, gain: 0.11, frequency: 1300, type: 'square' });
    playTone(c, { at: 2.05, duration: 0.4, gain: 0.09, frequency: 2250, type: 'square' });
    playNoise(c, {
      at: 2.45,
      duration: 1.2,
      gain: 0.15,
      filterType: 'bandpass',
      frequency: 1800,
    });
  } catch (err) {
    /* audio unavailable */
  }
}
