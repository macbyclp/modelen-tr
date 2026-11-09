'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');
const { parseSums, sha256File, assetUrl } = require('../lib/indir');

const BIN = path.join(__dirname, '..', 'bin', 'modelen.js');

test('parseSums reads sha256sum output', () => {
  const h = 'a'.repeat(64);
  const m = parseSums(`${h}  kur.sh\r\n${'B'.repeat(64)} *Modelen-Kurulum.exe\nnot a line\n`);
  assert.strictEqual(m['kur.sh'], h);
  assert.strictEqual(m['Modelen-Kurulum.exe'], 'b'.repeat(64));
  assert.strictEqual(Object.keys(m).length, 2);
});

test('sha256File matches a known digest', () => {
  const f = path.join(os.tmpdir(), 'modelen-npm-test.txt');
  fs.writeFileSync(f, 'abc');
  assert.strictEqual(sha256File(f), 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
  fs.rmSync(f);
});

test('assetUrl points at GitHub releases only', () => {
  assert.strictEqual(assetUrl('kur.sh'), 'https://github.com/macbyclp/modelen-tr/releases/latest/download/kur.sh');
  assert.strictEqual(assetUrl('kur.sh', 'v0.5.7'), 'https://github.com/macbyclp/modelen-tr/releases/download/v0.5.7/kur.sh');
});

test('--help, --version, unknown command, bad tag', () => {
  const pkg = require('../package.json');
  assert.match(spawnSync('node', [BIN, '--help'], { encoding: 'utf8' }).stdout, /npx modelen/);
  assert.strictEqual(spawnSync('node', [BIN, '--version'], { encoding: 'utf8' }).stdout.trim(), pkg.version);
  assert.strictEqual(spawnSync('node', [BIN, 'foo'], { encoding: 'utf8' }).status, 2);
  assert.strictEqual(spawnSync('node', [BIN, '--tag', 'main'], { encoding: 'utf8' }).status, 2);
});
