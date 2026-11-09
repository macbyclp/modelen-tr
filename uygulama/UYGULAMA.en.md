# Modelen app (Rust, desktop)

[Türkçe](UYGULAMA.md) · **English**

User decision (2026-11-07): I don't want VS Code; I want a single Rust application that, once installed, does both the volunteer GPU work and the code assistant. This app is the first version in that direction (that is why the VS Code extension under `ide/` is now **unused**; it remains only as the first prototype of the provider logic).

## What it does

- **Easy mode (opening screen):** one page, a big ON/OFF button = volunteer worker. While on: a pulse animation, elapsed time and the number of completed rounds; plain-language messages on errors (in Turkish). If the address is local (127.0.0.1) and no coordinator is there, it first starts the local test coordinator (`--en-az 1`) itself. "Advanced options" at the bottom right; in Advanced, "Easy mode" at the top right. The last chosen mode is remembered. A window icon and a minimum size are defined.

- **Coordinator selection (Easy mode + Advanced > Volunteer):** a small table (name, address, what they develop); your GPU is dedicated to the selected coordinator. The list is fetched from the site (`modelen.tr/koordinatorler.json`, produced by the portal; only approved coordinators that have an address); only admin-approved (`onayli: true`) entries with an https address are shown; the latest list is cached as `%APPDATA%\Modelen\dizin.json`, and "Local test" is always in the list. Those who want to become coordinators sign up on the site and apply; admins view the applications and contact addresses in the `portal/` admin panel and approve them (see `portal/PORTAL.md`). A coordinator address is not mandatory. Easy mode opens a narrow window (455×863), Advanced a wide one.
- **Code tab:** a folder tree, a text editor (Save, Ctrl+S), and on the right an **Ask the community** panel: the question goes to the coordinator's `/soru` endpoint (`istemci/calisma/sorular.jsonl`, read with `istemci/sorular.py`); the open file/selection is attached only if the box is ticked.
- **Providers:** Modelen (local), Ollama, any OpenAI-compatible endpoint (OpenRouter, vLLM, llama.cpp…) and Anthropic. Added and edited from settings. Streamed answers, a Stop button.
- **API keys:** only in the Windows credential vault (`keyring`); not written to the settings file, the log or the UI state.
- **Volunteer tab:** GPU info (`nvidia-smi`), coordinator address + nickname, **Start/stop contributing** (worker subprocess), coordinator status (round, worker count, traffic; every 5 s), worker log.
- **Local model:** starts and stops the `sunucu/modelen_sunucu.py` subprocess (an adapter can be chosen); "Modelen (local)" in the Code tab connects to it.

## Structure

| File | Role |
|---|---|
| `src/saglayici.rs` | OpenAI-compatible + Anthropic streaming client (`ureq`, rustls), context building, code-block extraction, 7 tests + 1 live test |
| `src/surec.rs` | Subprocess management (no console window, log including progress bars), GPU, coordinator status, file tree, 3 tests |
| `src/ayar.rs` | `%APPDATA%\Modelen\ayarlar.json`, credential vault |
| `src/main.rs` | `eframe`/`egui` UI (red theme) |

Build: `cd uygulama && cargo build --release` → `target/release/modelen.exe` (about 10 MB, a standalone single exe). Test: `cargo test`; with the local model server running, `cargo test canli -- --ignored --nocapture`.

## Verified

- Built (debug + release). **11 unit tests passed**: streaming of both providers against fake HTTP servers, headers, error body, requests without a key, empty settings, broken SSE, context/truncation/code block, process start-stop, file tree, status summary.
- **Live:** the Rust provider layer got an answer in 9 streamed chunks from a running local Modelen server (Qwen3-0.6B + round-3 adapter).
- The app opened; the three-tab UI was seen on screen (Turkish characters, the three-pane Code tab). No crashes.

## Not verified / honest gaps

- **UI interactions were not tried by clicking** (opening a file, send, start contributing, key vault). They were written in code and the logic underneath is tested, but I did not see the buttons actually behave.
- **Installation:** `Modelen-Kurulum.exe` (embeds `kur.ps1` from the root directory) installs Python 3.12, PyTorch, the base model and the client scripts under `%LOCALAPPDATA%\Modelen`; the app finds this layout by itself. Training and the local model still run as a Python (`torch`) subprocess (not moved to Rust). The install scripts are tested on GitHub's clean machines without a GPU; a GPU end-to-end install and signing are not there yet.
- Model quality: the 0.6B base model is not a chat assistant (example: it writes a continuation sentence to a question).
- Agent features (tool calling, multi-file editing, inline completion), syntax highlighting, file create/delete, tabs: not there.
- The coordinator connection is plain HTTP; for a public network TLS + accounts + anti-poisoning are needed (`istemci/ISTEMCI.md`).
- Tried on Windows only (the credential vault feature was chosen for Windows).
