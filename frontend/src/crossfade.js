const STEPS = 128;

export function crossfadeCurves() {
  const fadeIn = new Float32Array(STEPS);
  const fadeOut = new Float32Array(STEPS);
  for (let i = 0; i < STEPS; i++) {
    const angle = (i / (STEPS - 1)) * Math.PI / 2;
    fadeIn[i] = Math.sin(angle);
    fadeOut[i] = Math.cos(angle);
  }
  return { fadeIn, fadeOut };
}
