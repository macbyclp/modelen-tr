'use strict';
// Downloads release assets from GitHub and verifies them against the release's SHA256SUMS. No dependencies.
const https = require('https');
const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');

const REPO = 'macbyclp/modelen-tr';

function assetUrl(name, tag) {
  return tag
    ? `https://github.com/${REPO}/releases/download/${tag}/${name}`
    : `https://github.com/${REPO}/releases/latest/download/${name}`;
}

function get(url, redirects = 5) {
  return new Promise((resolve, reject) => {
    const u = new URL(url);
    if (u.protocol !== 'https:') return reject(new Error('only https downloads are allowed: ' + url));
    https.get(u, { headers: { 'User-Agent': 'modelen-npm' } }, (res) => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        res.resume();
        if (redirects <= 0) return reject(new Error('too many redirects'));
        return resolve(get(new URL(res.headers.location, url).toString(), redirects - 1));
      }
      if (res.statusCode !== 200) {
        res.resume();
        return reject(new Error(`HTTP ${res.statusCode} for ${url}`));
      }
      resolve(res);
    }).on('error', reject);
  });
}

async function fetchText(url) {
  const res = await get(url);
  const parts = [];
  for await (const c of res) parts.push(c);
  return Buffer.concat(parts).toString('utf8');
}

// "<sha256>  <name>" lines -> { name: sha256 }
function parseSums(text) {
  const out = {};
  for (const line of text.split(/\r?\n/)) {
    const m = line.trim().match(/^([0-9a-fA-F]{64})\s+\*?(.+)$/);
    if (m) out[m[2].trim()] = m[1].toLowerCase();
  }
  return out;
}

function sha256File(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

// Downloads `name`, verifies its SHA-256 and returns the local path. Throws on any mismatch.
async function indirDogrula(name, { tag, dir } = {}) {
  const hedefDizin = dir || fs.mkdtempSync(path.join(os.tmpdir(), 'modelen-'));
  const sums = parseSums(await fetchText(assetUrl('SHA256SUMS', tag)));
  const beklenen = sums[name];
  if (!beklenen) throw new Error(`${name} is not listed in SHA256SUMS; refusing to run it`);
  const hedef = path.join(hedefDizin, name);
  const res = await get(assetUrl(name, tag));
  await new Promise((resolve, reject) => {
    const f = fs.createWriteStream(hedef, { mode: 0o700 });
    res.pipe(f);
    f.on('finish', resolve);
    f.on('error', reject);
    res.on('error', reject);
  });
  const gercek = sha256File(hedef);
  if (gercek !== beklenen) {
    fs.rmSync(hedef, { force: true });
    throw new Error(`SHA-256 mismatch for ${name}: expected ${beklenen}, got ${gercek}`);
  }
  return hedef;
}

module.exports = { assetUrl, parseSums, sha256File, indirDogrula };
