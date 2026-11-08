---
baslik: Volunteer setup
bolum: Getting started
sira: 4
ozet: Windows setup for lending your GPU to a coordinator: requirements, the install script, what gets installed, how to remove it.
---

# Volunteer setup (Windows)

A volunteer lends their own GPU to a coordinator. Training happens locally; only the small LoRA adapter (~40 MB) and the data shard served by the coordinator cross the network.

:::uyari
**Status: the install script is written but has not yet been tested end to end on a clean machine**, and the release packages (`modelen.exe`, `modelen-istemci.zip`) will be produced with the first tagged release. Try the script at your own risk, with `-Dene` first; report problems on [GitHub](https://github.com/macbyclp/modelen-tr/issues).
:::

## Requirements

- Windows 10/11 (64-bit)
- An **NVIDIA GPU** with at least 6 GB VRAM (tested with 8 GB) and a current NVIDIA driver
- ~8 GB free disk (PyTorch about 3 GB, base model 1.2 GB)
- An internet connection (downloads are hundreds of MB; mind metered connections)
- Administrator rights are **not** needed

## Install

Download `kur.ps1` from the [repository](https://github.com/macbyclp/modelen-tr/blob/main/kur.ps1). First see what it would do (installs nothing):

```bash
powershell -ExecutionPolicy Bypass -File kur.ps1 -Dene
```

Then install:

```bash
powershell -ExecutionPolicy Bypass -File kur.ps1
```

| Parameter | Meaning |
|---|---|
| `-Hedef` | Install folder (default `%LOCALAPPDATA%\Modelen`) |
| `-Surum` | GitHub release tag (default: latest) |
| `-CudaSurumu` | PyTorch wheel: `cu124` (default), `cu121`, `cu126`, `cpu` (testing only) |
| `-Kaynak` | Offline/local install: the repository root (containing `istemci\`) |
| `-ModelAtla` | Skip the base model download |
| `-Dene` | Only check prerequisites and print the plan |

## What gets installed?

Everything lives in one folder (`%LOCALAPPDATA%\Modelen`); your system Python is untouched.

| Path | Content |
|---|---|
| `modelen.exe` | Desktop app (Easy mode: become a worker with one button) |
| `istemci\` | Worker scripts |
| `.venv\` | Python 3.12 + PyTorch + `transformers`, `peft`, `safetensors` (installed with [uv](https://github.com/astral-sh/uv)) |
| `models\qwen3-0.6b-base\` | Base model (Qwen3-0.6B-Base, Apache-2.0) |
| `arac\uv.exe` | Install tool |

The script compares the SHA-256 of release assets with `SHA256SUMS`. A **Modelen** shortcut is added to the Start menu.

## Use

1. Open **Modelen** from the Start menu (Easy mode).
2. Choose a **coordinator** ([approved directory](https://modelen.tr/koordinatorler)). The coordinator decides which data and mode to train with; read its description before choosing.
3. Press **ON**. The app takes a task, trains and uploads the result. Press **OFF** to stop.

The worker downloads the coordinator's data shard in the first round and caches it under `%USERPROFILE%\.modelen\veri`; later rounds do not download it again.

## Privacy and security

- Training happens on **your GPU**; only the trained adapter goes to the coordinator. No personal data other than the pseudonym is sent.
- Weights and data from the network are read only as **safetensors** (no pickle, no code execution), and their digests are checked.
- Think about who a coordinator is before trusting it: it chooses the training data. See [Security](/en/guvenlik/).

## Removal

Delete the `%LOCALAPPDATA%\Modelen` folder and the `Modelen.lnk` shortcut in the Start menu. Settings live in `%APPDATA%\Modelen` (API keys are in the Windows credential store).
