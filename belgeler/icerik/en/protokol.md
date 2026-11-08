---
baslik: Coordinator protocol v1
bolum: Connecting your system
sira: 1
ozet: The HTTP contract between the volunteer app and a coordinator.
---

# Coordinator protocol v1

This is the contract between the **volunteer app (worker)** and a **coordinator**. "Required" means the worker breaks without it; "recommended" means the conformance test warns.

## General rules

- HTTP/1.1, UTF-8 JSON responses, **safetensors** for weights. **No pickle**: nothing from the network is ever interpreted as code.
- **HTTPS is mandatory** on public networks; plain `http` only on `127.0.0.1`.
- The worker id (`isci`) is a pseudonym chosen by the volunteer; keep it free of personal data (≤ 60 chars recommended).
- Optional shared key: if set, every request carries `X-Anahtar: <key>`; wrong key → `401`. `/bilgi` may be called without it.
- Errors: `{"hata": "<message>"}`.

## Round lifecycle

```text
worker                                    coordinator
 |-- GET /gorev?isci=ali -------------->|  {tur:0, parca:0, ic_adim:20, agirlik_sha256:...}
 |-- GET /agirlik ---------------------->|  X-Tur: 0, X-Sha256: ...  (safetensors)
 |   (verify sha256; train H steps)     |
 |-- POST /sonuc?isci=ali&tur=0 ------->|  validate -> {tamam:true, tur:0}
 |-- GET /gorev?isci=ali -------------->|  {bekle:true, tur:0}
 |         ...other workers...          |  enough results -> round closes
 |-- GET /gorev?isci=ali -------------->|  {tur:1, ...}
 |-- GET /gorev?isci=ali -------------->|  {bitti:true}
```

A worker may send **at most one** result per round.

## Endpoints

| Endpoint | Status | Purpose |
|---|---|---|
| `GET /bilgi` | recommended | Discovery: `protokol: "1"`, round, base model, adapter info |
| `GET /durum` | required | Live state: `tur`, `toplam_tur`, `bekleyen_sonuc` (list), `isciler` (object), `trafik` (object) |
| `GET /gorev?isci=` | required | Task for this worker; `400` without `isci` |
| `GET /agirlik` | required | Global adapter, headers `X-Tur` and `X-Sha256` |
| `POST /sonuc?isci=&tur=` | required | Upload the trained adapter |
| `POST /soru` | optional | Community questions from the app |

### `GET /gorev`

```json
{"tur": 3, "toplam_tur": 20, "parca": 1, "n_parca": 4, "ic_adim": 20, "bs": 4, "seq": 512,
 "lr": 0.0002, "tohum": 0, "agirlik_sha256": "<64 lowercase hex>"}
```

Other replies: `{"bekle": true, "tur": N}` (this worker already submitted this round) and `{"bitti": true}` (training finished).

### `GET /agirlik`

Returns the global adapter as `application/octet-stream`. `X-Sha256` must equal the real SHA-256 of the body; `X-Tur` is the round the weights belong to. The worker compares the digest with the task's `agirlik_sha256` and re-requests a task on mismatch, so `/gorev` and `/agirlik` must be consistent within a round.

### `POST /sonuc`

| Status | Body | When |
|---|---|---|
| 200 | `{"tamam": true, "tur": 3}` | Accepted |
| 400 | `{"hata": "..."}` | Not valid safetensors |
| 409 | `{"hata": "..."}` | Stale round, duplicate from the same worker, or training finished |
| 413 | `{"hata": "boyut"}` | Empty or too large body |
| 422 | `{"hata": "..."}` | Key set, shape or dtype mismatch; NaN/Inf |

:::uyari
Never accept an invalid upload with `200`, and never answer `500` for bad input. The conformance test checks both.
:::

## What the coordinator must do

1. **Validate** each upload against the global adapter (keys, shapes, dtype, finite values).
2. **Collect** until `en_az` results arrive or a timeout (≥ 1 result).
3. **Merge** — the protocol does not mandate how. The reference uses an outer Nesterov step (lr 1.0, momentum 0.5) with outlier elimination (≥ 3 results, 5× median delta norm). Plain averaging is also compliant.
4. **Publish**: increment the round, recompute the SHA-256, serve the new weights.
