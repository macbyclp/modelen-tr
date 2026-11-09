# modelen

Install **Modelen**, the community-trained open AI volunteer client, with one command:

```bash
npx modelen
```

It downloads the official installer from the [GitHub release](https://github.com/macbyclp/modelen-tr/releases/latest), **verifies its SHA-256 against the release's `SHA256SUMS`**, and runs it. Nothing else is installed by this package.

| Platform | What runs |
|---|---|
| Windows 10/11 (64-bit) | `Modelen-Kurulum.exe` (installs Python, PyTorch, the base model and the app under `%LOCALAPPDATA%\Modelen`; no admin rights) |
| Linux x86_64 | `kur.sh` (use `npx modelen --dene` to install nothing and just check) |
| Linux server, no GPU | `npx modelen coordinator` runs `koordinator-kur.sh` to set up a coordinator |

macOS is not supported (no NVIDIA GPUs). An NVIDIA GPU with at least 6 GB of memory is needed to contribute.

Options: `--tag v0.5.7` installs a specific release; everything else is passed to the installer.

Alpha software, research stage. See [modelen.tr](https://modelen.tr), the [docs](https://docs.modelen.tr/en/) and the [source](https://github.com/macbyclp/modelen-tr). Apache-2.0.
