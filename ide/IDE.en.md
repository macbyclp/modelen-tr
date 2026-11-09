# Modelen Code (IDE, first version)

[Türkçe](IDE.md) · **English**

> Note: this prototype is **no longer used**; see `uygulama/UYGULAMA.en.md`.

Decision (user, 2026-11-07): after the client, a Cursor / Claude Code-style IDE; both our own models and external APIs. Instead of writing an editor from scratch I made a **VS Code extension** (this is the cheapest first step toward a "VS Code fork"; the same core can later be moved to a fork).

## Parts

| Path | Role |
|---|---|
| `ide/modelen-kod/src/saglayici.js` | Provider layer: `openai` (Modelen server, Ollama, llama.cpp, OpenRouter, OpenAI…) and `anthropic`. SSE streaming, cancellation, errors. No dependencies |
| `ide/modelen-kod/src/baglam.js` | Message building (selection/file context, truncation), extracting the first code block from the answer |
| `ide/modelen-kod/src/extension.js` | VS Code commands, chat panel, key vault (SecretStorage) |
| `ide/modelen-kod/src/arayuz.js` | Chat panel HTML (CSP + nonce; model output only via `textContent`) |
| `ide/modelen-kod/test/test.js` | 9 tests (with fake OpenAI/Anthropic servers) |
| `sunucu/modelen_sunucu.py` | Serves Qwen3-0.6B-Base + the Modelen adapter on an OpenAI-compatible endpoint (`127.0.0.1:8760`) |

## Features

- Provider selector (setting: `modelen.saglayicilar`); local Modelen and Ollama need no key, cloud providers need a key.
- **The API key is not written to settings**; with the `Modelen: Set API key` command it goes to the operating system's key vault, never reaches the panel/webview, and is not written to the log.
- Streamed answers, a **Stop** button, new chat, open file/selection context (truncated at 12,000 characters).
- **Replace selection**: writes the first code block in the answer to the selected region only when the user presses the button. There is no automatic file editing.
- Shortcut: `Ctrl+Alt+M` (ask about the selection).

## Verified

- 9/9 unit tests (`node --test test/`): stream parsing of both providers (including chunks split mid-line), headers, errors, cancellation, context building, the extension activating with a mock `vscode`, an error when there is no key, the syntax of the script in the panel.
- **Real end to end**: the JS provider layer → `modelen_sunucu.py` (Qwen3-0.6B-Base + round-3 adapter) received 8 chunks by streaming (~3 s).

## Honest notes / gaps

- **The extension was not run inside a real VS Code** (VS Code is not installed on this machine). It was tried only with a mock `vscode` module and unit tests; I did not see the panel. First job: open an "Extension Development Host" with F5 in VS Code and try it.
- No calls were made to the real Anthropic/OpenAI endpoints (no key); it was tried only with fake servers and the documented format.
- **The model quality is not that of a chat assistant**: the 0.6B base model is not instruction-tuned; on a sample request it nearly repeated the question verbatim. The pipeline works; a useful answer needs an instruction-tuned (SFT) Turkish model or a larger base.
- Not there yet: file editing/tool calling (agent), multi-file context, inline completion, training with Turkish code data. Cursor/Claude Code-level agent features are a separate, large job.
- Packaging (`vsce`) and a Marketplace release were not done; they need an identity/publisher name.

## Running

```bash
# Serve the Modelen model (separate terminal; from the modelen/ folder)
.venv/Scripts/python.exe sunucu/modelen_sunucu.py --adaptor istemci/calisma/tur-3.safetensors
# Tests
cd ide/modelen-kod && node --test test/
# In VS Code: open the folder -> F5 -> command palette "Modelen: Sohbeti aç" (Open chat)
```
