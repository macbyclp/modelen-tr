---
baslik: Reference coordinator
bolum: Connecting your system
sira: 4
ozet: istemci/koordinator.py: setup, all flags, output files, deployment and known limits.
---

# Reference coordinator

`istemci/koordinator.py` is the full implementation of protocol v1, tested with real training (Python standard HTTP server + PyTorch). It is the shortest way to start without writing your own coordinator.

## Requirements

- Python 3.10+, `torch`, `safetensors`, `transformers`, `peft` (to produce the starting adapter)
- Base model: `models/qwen3-0.6b-base` (Qwen/Qwen3-0.6B-Base, Apache-2.0). The coordinator only handles **adapter weights**, but the script that produces the starting adapter needs the model. No GPU needed.
- RAM: a few hundred MB (adapter 40 MB, multiplied by the number of workers).

## Running

```bash
python istemci/baslat.py                                   # produces the round-0 adapter
python istemci/koordinator.py \
    --baslangic istemci/calisma/tur-0.safetensors \
    --tur 20 --en-az 2 --ic-adim 20 --port 8750
```

Status panel: `http://127.0.0.1:8750/` (JSON: `/durum`).

## Flags

| Flag | Default | Meaning |
|---|---|---|
| `--baslangic` | *(required)* | Starting adapter (`baslat.py` output) |
| `--host` | `127.0.0.1` | Address to listen on. Do not use `0.0.0.0` directly on public networks; use a reverse proxy |
| `--port` | `8750` | Port |
| `--tur` | `6` | Total rounds |
| `--en-az` | `2` | Minimum results needed to close a round |
| `--zaman-asimi` | `900` | Seconds; when it expires, the round closes with the results at hand (≥1) |
| `--parca` | `4` | Number of data shards (`n_parca`); assigned to workers in rotation |
| `--ic-adim` | `20` | H: the worker's local steps |
| `--bs` | `4` | Batch size |
| `--seq` | `512` | Sequence length |
| `--lr` | `2e-4` | Peak learning rate (cosine schedule on the worker) |
| `--dis-lr` | `1.0` | Outer-step learning rate |
| `--dis-mom` | `0.5` | Outer-step momentum |
| `--aykiri-kat` | `5.0` | Drop a result whose delta norm exceeds this multiple of the median (with ≥3 results) |
| `--anahtar` | *(empty)* | If set, all requests must carry an `X-Anahtar` header. **Several comma-separated keys** are allowed (one per volunteer; rotate a leaked one by restarting) |
| `--veri` | *(empty)* | Tokenised training data (safetensors); sharded and served to workers at [`/veri`](/en/protokol/#get-veri-parca-i-optional). Produced with `istemci/veri_donustur.py` |
| `--mod` | `cpt` | Training mode announced to workers: `cpt` or `sft` |
| `--sifirdan` | off | Ignore the saved state in the work folder and start from round 0 |
| `--en-cok-isci` | `1000` | Maximum number of distinct worker names tracked (memory bound); new workers beyond it get `503` |
| `--istek-siniri` | `240` | Maximum requests per IP per minute (`0` = unlimited); beyond it `429` |
| `--vekil` | off | Behind a trusted reverse proxy: take the client IP from `X-Forwarded-For` |
| `--calisma` | `istemci/calisma` | Output folder |
| `--tohum` | `0` | Starting-adapter seed |

## Output files

In the `--calisma` folder:

| File | Content |
|---|---|
| `tur-N.safetensors` | Global adapter after round N (round 0 is the start) |
| `durum.json`, `momentum.safetensors` | Persistent state written **at the end of every round** (round, worker-shard assignments, outer-step momentum). After a restart the coordinator resumes where it stopped; `--sifirdan` ignores it |
| `gunluk.json` | Round log (workers used/dropped, delta norms, duration) and traffic |
| `sorular.jsonl` | Community questions arriving via `/soru` (read with `python istemci/sorular.py`) |

## Publishing on the public internet

```text
coordinator.example.org {
    reverse_proxy 127.0.0.1:8750
}
```

(Add `--vekil` so rate limits use the real client IP.) Then run the [conformance test](/en/uyum-testi/) and [verify your address](/en/adres-dogrulama/). A persistent systemd unit:

```text
[Unit]
Description=Modelen coordinator
After=network.target

[Service]
User=modelen
WorkingDirectory=/opt/modelen
ExecStart=/opt/modelen/.venv/bin/python istemci/koordinator.py --baslangic istemci/calisma/tur-0.safetensors --tur 50 --en-az 3 --vekil
Restart=always

[Install]
WantedBy=multi-user.target
```

## Known limits

:::uyari
The reference coordinator is a **prototype**:

- The outer-step momentum is written to disk at the end of every round and restored on restart; results of a round still in progress live in memory and are lost, and workers resubmit that round.
- Authentication is only an optional **shared key(s)**; there are no accounts. There is a per-IP rate limit and a worker-count limit, but this is not a defence against Sybil attacks.
- Poisoning protection is only **simple outlier-norm elimination** (with ≥3 results). It is not enough against a determined attacker; repeated verification (giving the same task to two workers and comparing) is not done.
- No TLS; a reverse proxy is required.
- All workers take the same number of steps; a slow GPU delays the round (the timeout closes it with what is at hand).
:::

More detail: [`istemci/ISTEMCI.md`](https://github.com/macbyclp/modelen-tr/blob/main/istemci/ISTEMCI.md).
