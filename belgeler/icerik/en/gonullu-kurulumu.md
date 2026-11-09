---
baslik: Volunteer setup
bolum: Getting started
sira: 4
ozet: Windows setup for lending your GPU to a coordinator: requirements, the install script, what gets installed, how to remove it.
---

# Volunteer setup

A volunteer lends their own GPU to a coordinator. Training happens locally; only the small LoRA adapter (~40 MB) and the data shard served by the coordinator cross the network.

:::not
**Status (alpha):** The install scripts are tested automatically on clean GitHub Windows and Ubuntu machines (no GPU, no model). Real GPU training and the model download are outside that test; if you run into problems, report them on [GitHub](https://github.com/macbyclp/modelen-tr/issues). The coordinators volunteers connect to are run by the community; see the [approved directory](https://modelen.tr/koordinatorler).
:::

## Requirements (Windows)

- Windows 10/11 (64-bit)
- An **NVIDIA GPU** with at least 6 GB VRAM (tested with 8 GB) and a current NVIDIA driver
- ~8 GB free disk (PyTorch about 3 GB, base model 1.2 GB)
- An internet connection (downloads are hundreds of MB; mind metered connections)
- Administrator rights are **not** needed

## Install (Windows)

### Easiest: Modelen-Kurulum.exe

From the [releases page](https://github.com/macbyclp/modelen-tr/releases/latest) download **`Modelen-Kurulum.exe`** and double-click it. A window opens, performs the steps below for you and waits for Enter at the end. (It is the `kur.ps1` script below embedded in a single file and accepts the same parameters, e.g. `Modelen-Kurulum.exe -Dene`.)

:::not
The program is **not digitally signed yet**, so Windows SmartScreen may show "Windows protected your PC". After verifying the source you can choose **More info → Run anyway**. To verify: compare the file digest with `SHA256SUMS` on the release page (`Get-FileHash Modelen-Kurulum.exe`) or run `gh attestation verify Modelen-Kurulum.exe --repo macbyclp/modelen-tr`.
:::

### With the PowerShell script

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

## What gets installed? (Windows)

Everything lives in one folder (`%LOCALAPPDATA%\Modelen`); your system Python is untouched.

| Path | Content |
|---|---|
| `modelen.exe` | Desktop app (Easy mode: become a worker with one button) |
| `istemci\` | Worker scripts |
| `.venv\` | Python 3.12 + PyTorch + `transformers`, `peft`, `safetensors` (installed with [uv](https://github.com/astral-sh/uv)) |
| `models\qwen3-0.6b-base\` | Base model (Qwen3-0.6B-Base, Apache-2.0) |
| `arac\uv.exe` | Install tool |

The script compares the SHA-256 of release assets with `SHA256SUMS`. A **Modelen** shortcut is added to the Start menu.

## Use (Windows)

1. Open **Modelen** from the Start menu (Easy mode).
2. Choose a **coordinator** ([approved directory](https://modelen.tr/koordinatorler)). The coordinator decides which data and mode to train with; read its description before choosing.
3. Press **ON**. The app takes a task, trains and uploads the result. Press **OFF** to stop.

The worker downloads the coordinator's data shard in the first round and caches it under `%USERPROFILE%\.modelen\veri`; later rounds do not download it again.

## Linux (Ubuntu, Arch and others)

There is no graphical app on Linux; the worker runs from the command line. `kur.sh` is published with every release on the [releases page](https://github.com/macbyclp/modelen-tr/releases/latest) with a SHA-256 digest (`SHA256SUMS`) and build-provenance attestation (`gh attestation verify kur.sh --repo macbyclp/modelen-tr`). `kur.sh` installs the same things (Python, PyTorch, the base model) without sudo under `~/.local/share/modelen`.

```bash
curl -fsSL https://github.com/macbyclp/modelen-tr/releases/latest/download/kur.sh -o kur.sh
bash kur.sh --dene     # see what it would do first (installs nothing)
bash kur.sh
```

Then start the worker:

```bash
modelen-isci --koordinator https://coordinator.example.org --isci your-pseudonym
```

| Option | Meaning |
|---|---|
| `--hedef` | Install folder (default `~/.local/share/modelen`) |
| `--surum` | GitHub release tag (default: latest) |
| `--cuda` | PyTorch wheel: `cu124` (default), `cu121`, `cu126`, `cpu` (testing only) |
| `--model-atla` | Skip the base model download |
| `--dene` | Only check prerequisites and print the plan |

Requirements: x86_64 Linux (glibc), an NVIDIA GPU (at least 6 GB) and a current driver (≥ 550 for `cu124`), ~8 GB free disk, `curl`. Driver install: `sudo ubuntu-drivers install` on Ubuntu, `sudo pacman -S nvidia-open nvidia-utils` on Arch, RPM Fusion `akmod-nvidia` on Fedora; if no GPU is found the script prints the matching hint for your distribution. To remove: `rm -rf ~/.local/share/modelen ~/.local/bin/modelen-isci`.

:::not
`kur.sh` is tested automatically on a clean GitHub **Ubuntu** machine and an **Arch Linux** container (no GPU, `--cuda cpu`, no model); GPU training is outside that test. Other glibc-based distributions such as Debian or Fedora will most likely work but are untested. musl-based distributions (Alpine) are not supported.
:::

## macOS

**Not supported.** The worker needs NVIDIA/CUDA today, and Macs have no NVIDIA graphics cards. Apple Silicon (MPS) support could be planned but does not exist yet.

## Privacy and security

- Training happens on **your GPU**; only the trained adapter goes to the coordinator. No personal data other than the pseudonym is sent.
- Weights and data from the network are read only as **safetensors** (no pickle, no code execution), and their digests are checked.
- Think about who a coordinator is before trusting it: it chooses the training data. See [Security](/en/guvenlik/).

## Removal (Windows)

Delete the `%LOCALAPPDATA%\Modelen` folder and the `Modelen.lnk` shortcut in the Start menu. Settings live in `%APPDATA%\Modelen` (API keys are in the Windows credential store).
