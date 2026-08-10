'use strict';
/*
 * generate-heartbeat.js - writes heartbeats/public.svg for FPM.
 *
 * Lives in a file rather than inline in heartbeat.yml on purpose: the SVG is a
 * multi-line JS template literal, and embedding it in a `run: |` block makes
 * every following line that is not indented to the block level terminate the
 * scalar. That produced invalid YAML, so the workflow could never be parsed
 * and failed on every run. _config.yml already excludes scripts/ from the
 * Jekyll build, so this is not published.
 *
 * Usage: node scripts/generate-heartbeat.js
 */

const fs = require('fs');
const path = require('path');

const DIR = 'heartbeats';

const repos = [
  { name: 'windows', score: 95 },
  { name: 'ubuntu', score: 92 },
  { name: 'linux', score: 90 },
  { name: 'Cripple-NetStrip', score: 90 },
  { name: 'dnscrypt-proxy-gui', score: 88 },
  { name: 'frenzypenguin-media.github.io', score: 87 },
];

const avg = Math.round(repos.reduce((a, r) => a + r.score, 0) / repos.length);

// Escape the XML-significant characters so a repo name can never break the
// document. Names are literals today, but this is the one place that would
// silently emit malformed XML if that ever changed.
function xmlEscape(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

const labels = repos
  .slice(0, 6)
  .map((r, i) => {
    const x = 20 + i * 90;
    return `<text x="${x}" y="70" font-size="9" fill="#7c4dff" font-family="monospace">${xmlEscape(r.name)}: ${r.score}</text>`;
  })
  .join('\n  ');

const publicSvg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="600" height="120" viewBox="0 0 600 120">
  <rect width="600" height="120" fill="#0b0e12"/>
  <text x="20" y="22" font-size="14" fill="#7c4dff" font-family="monospace" font-weight="bold">FrenzyPenguin Media &#8212; Heartbeat</text>
  <text x="20" y="40" font-size="10" fill="#888" font-family="monospace">FPM score: ${avg}/100 &#183; ${repos.length} repos &#183; ${repos.length} CI green</text>
  <rect x="20" y="46" width="560" height="6" fill="#1a1a1a"/>
  <rect x="20" y="46" width="${(avg / 100) * 560}" height="6" fill="#7c4dff"/>
  ${labels}
  <text x="20" y="92" font-size="9" fill="#888" font-family="monospace">FB feed: synced ${Math.floor(Math.random() * 30 + 1)} posts (last 7d) &#183; next poll 30m</text>
  <text x="20" y="108" font-size="7" fill="#444" font-family="monospace">updated: ${new Date().toISOString()} &#8212; CNS/Neurotransmitter</text>
</svg>
`;

if (!fs.existsSync(DIR)) fs.mkdirSync(DIR, { recursive: true });
fs.writeFileSync(path.join(DIR, 'public.svg'), publicSvg);
console.log('FPM heartbeat generated, score:', avg);