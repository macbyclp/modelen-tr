---
baslik: Conformance test
bolum: Connecting your system
sira: 3
ozet: A stdlib-only tool that checks whether a coordinator follows protocol v1.
---

# Conformance test

`istemci/uyum_testi.py` checks a running coordinator against [protocol v1](/en/protokol/). It needs only the Python standard library and works against coordinators written in any language.

```bash
python istemci/uyum_testi.py --url https://coordinator.example.org
python istemci/uyum_testi.py --url http://127.0.0.1:8750 --anahtar SECRET --json
```

| Flag | Meaning |
|---|---|
| `--url` | Coordinator address (required) |
| `--anahtar` | Shared key, if the coordinator requires `X-Anahtar` |
| `--isci` | Probe worker name (default `uyum-testi`) |
| `--json` | Machine-readable output |

Exit code `0` when every required check passes, `1` otherwise.

:::uyari
The test registers a probe worker (via `/gorev`) and sends deliberately invalid data to `/sonuc`. Run it against a test instance rather than in the middle of a live training run.
:::

## What is checked

| Check | Level | Detail |
|---|---|---|
| TLS | warning | Non-local `http://` |
| `/bilgi` | warning | JSON with `protokol: "1"` |
| `/durum` | required | `tur`, `toplam_tur`, `bekleyen_sonuc`, `isciler`, `trafik` with correct types |
| `/gorev` | required | `bekle`/`bitti` or full task + 64-hex `agirlik_sha256`; `400` without `isci` (warning) |
| `/veri` | required (if the task has `veri_sha256`) | `/veri?parca=` is served, the body digest equals `veri_sha256`, valid safetensors |
| `/agirlik` | required | `X-Sha256` matches body, integer `X-Tur`, valid safetensors, same digest as the task |
| `/agirlik` dtype | warning | non-`F32` |
| `/sonuc` | required | corrupt body → 400/422, stale round → 400/409/422, empty body → 400/413/422 (never 200/500) |
| unknown path | warning | `404` |

Example CI step:

```yaml
- run: python istemci/uyum_testi.py --url http://127.0.0.1:8750 --json
```
