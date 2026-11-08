---
baslik: Write your own coordinator
bolum: Connecting your system
sira: 5
ozet: The smallest protocol-v1 coordinator example (standard library only) and the steps for writing your own.
---

# Write your own coordinator

Any HTTP service implementing protocol v1 can be a coordinator. The **smallest working, tested example** is `istemci/ornekler/minimal_koordinator.py` (~150 lines, Python standard library only). It passes the [conformance test](/en/uyum-testi/) and a full round-cycle test on every release.

```bash
# any float32 safetensors file works as the starting adapter (to try the protocol)
python istemci/ornekler/minimal_koordinator.py --baslangic tur-0.safetensors --tur 5 --en-az 2 --port 8750
python istemci/uyum_testi.py --url http://127.0.0.1:8750
```

## What the example does

| Endpoint | What it does |
|---|---|
| `GET /bilgi` | `protokol: "1"`, round and weight summary |
| `GET /durum` | Round, pending results, workers, traffic |
| `GET /gorev` | 400 without `isci`; `bitti` if finished; `bekle` if the worker already submitted this round; otherwise a task (rotating data shard) |
| `GET /agirlik` | Global adapter + `X-Tur` + `X-Sha256` |
| `POST /sonuc` | Validate → store → close the round once `en_az` results arrive |

**Differences from the reference coordinator:** plain average (no outer step/momentum), no outlier elimination, pure-Python safetensors (slow, float32 only), state in memory only.

## Steps for your own service

1. **Load the starting adapter** and compute its SHA-256 (`/gorev.agirlik_sha256` and the `/agirlik` header use it).
2. **`GET /gorev`**: `isci` required; `{"bitti":true}` if finished; `{"bekle":true,"tur":N}` if this worker already submitted; otherwise the task object. Give the worker a *stable* `parca` (constant within a round).
3. **`GET /agirlik`**: global adapter bytes with `X-Tur` and `X-Sha256` headers.
4. **`POST /sonuc`**: check, in order:
   - empty/too large body → `413`;
   - not readable as safetensors → `400` (never accept pickle);
   - wrong round → `409`; same worker twice → `409`; training finished → `409`;
   - key set, shape or dtype mismatch, or NaN/Inf → `422`;
   - otherwise store and return `{"tamam":true,"tur":N}`.
5. **Close the round**: when enough results (or a timeout) arrive, merge, `tur += 1`, publish the new bytes and SHA-256.
6. **Publish over HTTPS** and run the [conformance test](/en/uyum-testi/).

## Core logic

First, **validating** an incoming adapter:

```python
def dogrula(self, tensorler):
    if set(tensorler) != set(self.glob):
        return "anahtar kümesi uyuşmuyor"
    for ad, t in tensorler.items():
        if len(t) != len(self.glob[ad]):
            return f"şekil uyuşmuyor: {ad}"
        if not math.isfinite(sum(t)):
            return f"sonlu olmayan değer: {ad}"
    return None
```

Second, **closing the round** (plain average):

```python
def tur_kapat(self):
    for ad in self.glob:
        n = len(self.sonuclar)
        ort = array.array("f", (sum(v) / n for v in zip(*(s[ad] for s in self.sonuclar.values()))))
        self.glob[ad] = ort
    self.sonuclar = {}
    self.tur += 1
    self._baytla()      # new bytes and SHA-256
```

In a real system do the merge with NumPy/PyTorch (this pure-Python example is slow at 10 million parameters) and add outlier elimination.

:::ipucu
Do not forget to send the portal a [heartbeat](/en/nabiz/): `python istemci/ornekler/modelen_api.py nabiz-dongusu --koordinator https://your-address`.
:::

The full file: [`istemci/ornekler/minimal_koordinator.py`](https://github.com/macbyclp/modelen-tr/blob/main/istemci/ornekler/minimal_koordinator.py).
