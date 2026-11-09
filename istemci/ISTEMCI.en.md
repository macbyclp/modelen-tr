# Modelen volunteer client (prototype)

[Türkçe](ISTEMCI.md) · **English**

The smallest working system that runs an adapter-DiLoCo round on a volunteer's GPU. Purpose: to have something real behind the "Join" page and to try the protocol end to end. **It is not a production client.**

## Parts

| File | Role |
|---|---|
| `baslat.py` | Produces the initial LoRA adapter from a seed (`calisma/tur-0.safetensors`, 40.4 MB) |
| `koordinator.py` | Round management: hands out tasks, validates results, averages, applies the Nesterov outer step, saves the adapter for each round |
| `isci.py` | Volunteer side: detects the GPU, downloads the adapter, trains H local steps, sends the adapter back |
| `degerlendir.py` | Measures an adapter's Turkish bits/byte |
| `ortak.py` | Shared model setup, safetensors (de)serialisation, learning rate |

## Protocol (HTTP, JSON + safetensors)

```
worker → GET  /gorev?isci=<nickname>   ← {tur, parca, ic_adim, bs, seq, lr, tohum, agirlik_sha256} | {bekle} | {bitti}
worker → GET  /agirlik                 ← global adapter (safetensors), sha256 must match the one in the task
worker → POST /sonuc?isci=..&tur=..    → new adapter (safetensors)       ← {tamam} | 409 stale round | 422 invalid
```

(`gorev` = task, `agirlik` = weights, `sonuc` = result, `bekle` = wait, `bitti` = finished, `tamam` = ok.)

The coordinator closes the round when `--en-az` (minimum) results arrive (or, when `--zaman-asimi` (timeout) expires, with what it has):
`delta = global − mean(worker results)`, `buffer = m·buffer + delta`, `global −= lr_outer · (delta + m·buffer)` (m=0.5, lr_outer=1.0; the best setting in the simulation).

## Security features (existing)

- Weights from the network are read **only with safetensors**; no pickle, no code can be executed.
- Key set, shape and type checks on incoming results; NaN/Inf are rejected.
- A result whose delta norm exceeds 5× the median is eliminated (with ≥3 results). This is a **simple** anti-poisoning measure; it is not enough against a determined attacker.
- A worker can submit one result per round; a result for a stale round is rejected.
- The sha256 digest of each round's adapter is announced in the task (catches download corruption).
- Optional shared key (`--anahtar`); by default it listens on `127.0.0.1` only.
- Volunteers use a nickname; no personal data is collected.

## Known gaps (honest list)

- **No authentication / accounts**: a single shared key. Open to a Sybil attack.
- **Weak anti-poisoning**: the real fix is repeated verification (give the same task to 2 workers and compare) and a loss check on a hidden validation set. Not done.
- **No TLS**: on a public network, HTTPS behind a reverse proxy (Caddy/nginx) is mandatory.
- **Data**: the worker reads the local `data/tok-wiki30.pt` file. In reality a signed data-shard manifest and shard download are needed (license: CC BY-SA data → a question for a lawyer).
- **No UI**: command line. Target: a Tauri (Rust + web UI) shell; it would run the training worker as a subprocess and show GPU/VRAM, progress and pause/stop.
- **Durability**: coordinator state is in memory (rounds are written to disk but the momentum buffer is not → it resets on restart).
- **Unbalanced hardware**: all workers do the same number of steps; a slow GPU delays the round (the timeout closes it with what is available).
- **Signing**: releases are not signed; a release pipeline is needed for the "signed open-source client" decision.
- Tested only on a single machine, two workers on the same GPU.

## Running

```bash
# from the modelen/ folder
.venv/Scripts/python.exe istemci/baslat.py
.venv/Scripts/python.exe istemci/koordinator.py --baslangic istemci/calisma/tur-0.safetensors --tur 3 --en-az 2 --ic-adim 10
.venv/Scripts/python.exe istemci/isci.py --isci gonullu-a      # separate terminal
.venv/Scripts/python.exe istemci/isci.py --isci gonullu-b      # separate terminal
.venv/Scripts/python.exe istemci/degerlendir.py istemci/calisma/tur-0.safetensors istemci/calisma/tur-3.safetensors
```

Status panel: `http://127.0.0.1:8750/` (JSON: `/durum`).

## Next step: IDE

User decision (2026-11-07): after the client, a Cursor / Claude Code-style IDE; it should be able to connect our own models and external APIs. Recommendation: instead of writing an editor from scratch, an open-source VS Code fork or an extension; the provider layer (OpenAI-compatible endpoint, Anthropic, local Ollama/llama.cpp and Modelen) behind a common interface. API keys stay with the user, stored in the operating system's keychain.

## First end-to-end trial (2026-11-07)

2 workers (the same RTX 4060, separate processes), 3 rounds, 10 local steps per round, a single seed, on a 60-second held-out Wikipedia slice:

| adapter | bits/byte |
|---|---|
| round 0 (initial) | 1.2714 |
| round 3 | 1.2613 |

The protocol worked end to end (task → download → training → upload → average → new round, no result rejected). The drop is small, single-seed and only 30 steps of training in total; it is not proof that "the model improved", only a sign that the pipeline works in the right direction. Per-round worker load is 40.4 MB.
