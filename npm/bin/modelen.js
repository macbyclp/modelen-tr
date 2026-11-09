#!/usr/bin/env node
'use strict';
const { spawnSync } = require('child_process');
const { indirDogrula } = require('../lib/indir');
const pkg = require('../package.json');

const YARDIM = `modelen ${pkg.version}: install Modelen, the community-trained open AI volunteer client

Usage:
  npx modelen [install] [options]     download, verify (SHA-256) and run the volunteer installer
  npx modelen coordinator [options]   set up a coordinator on a Linux server (no GPU needed)
  npx modelen --version | --help

Options after the command are passed to the installer (Linux: kur.sh, e.g. --dene installs nothing).
  --tag vX.Y.Z   install a specific release instead of the latest

Windows 10/11 (Modelen-Kurulum.exe) and Linux x86_64 (kur.sh) are supported. macOS has no NVIDIA GPUs.
Docs: https://docs.modelen.tr/en/   Source: https://github.com/macbyclp/modelen-tr`;

function parse(argv) {
  const out = { komut: 'install', gecir: [], tag: undefined };
  const a = [...argv];
  if (a[0] && !a[0].startsWith('-')) {
    const k = a.shift();
    if (['install', 'kur'].includes(k)) out.komut = 'install';
    else if (['coordinator', 'koordinator'].includes(k)) out.komut = 'coordinator';
    else { out.komut = 'bilinmeyen'; out.ad = k; return out; }
  }
  for (let i = 0; i < a.length; i++) {
    if (a[i] === '--tag') out.tag = a[++i];
    else out.gecir.push(a[i]);
  }
  if (out.tag && !/^v\d+\.\d+\.\d+$/.test(out.tag)) { out.komut = 'gecersiz-tag'; }
  return out;
}

async function main() {
  const argv = process.argv.slice(2);
  if (argv.includes('--help') || argv.includes('-h')) return console.log(YARDIM);
  if (argv.includes('--version') || argv.includes('-v')) return console.log(pkg.version);
  const o = parse(argv);
  if (o.komut === 'bilinmeyen') { console.error(`Unknown command: ${o.ad}\n\n${YARDIM}`); process.exit(2); }
  if (o.komut === 'gecersiz-tag') { console.error('--tag must look like v0.5.7'); process.exit(2); }

  const platform = process.platform;
  let dosya, calistir;
  if (o.komut === 'coordinator') {
    if (platform !== 'linux') { console.error('The coordinator installer runs on a Linux server only.'); process.exit(1); }
    dosya = 'koordinator-kur.sh'; calistir = (p) => ['bash', [p, ...o.gecir]];
  } else if (platform === 'win32') {
    dosya = 'Modelen-Kurulum.exe'; calistir = (p) => [p, o.gecir];
  } else if (platform === 'linux') {
    if (process.arch !== 'x64') { console.error('Only x86_64 Linux is supported.'); process.exit(1); }
    dosya = 'kur.sh'; calistir = (p) => ['bash', [p, ...o.gecir]];
  } else {
    console.error('Modelen needs an NVIDIA GPU, so only Windows and Linux are supported (macOS is not).');
    process.exit(1);
  }

  console.log(`Downloading ${dosya}${o.tag ? ' (' + o.tag + ')' : ''} from GitHub and verifying SHA-256 ...`);
  const yol = await indirDogrula(dosya, { tag: o.tag });
  console.log('Checksum OK. Starting the installer ...');
  const [cmd, args] = calistir(yol);
  const r = spawnSync(cmd, args, { stdio: 'inherit' });
  if (r.error) { console.error(r.error.message); process.exit(1); }
  process.exit(r.status === null ? 1 : r.status);
}

main().catch((e) => { console.error('Error: ' + e.message); process.exit(1); });
