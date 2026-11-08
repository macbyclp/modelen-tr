---
baslik: Quick start
bolum: Getting started
sira: 2
ozet: Run a coordinator locally, check it with the conformance test and query the Portal API.
---

# Quick start

Everything below runs locally and needs only Python 3.10+ for the minimal path.

## 1. Get the code

```bash
git clone https://github.com/macbyclp/modelen-tr
cd modelen-tr
```

## 2. Run the minimal coordinator

Any float32 safetensors file with the [adapter layout](/en/adaptor-bicimi/) works as a starting adapter. The reference script `istemci/baslat.py` generates a real one (needs PyTorch + PEFT).

```bash
python istemci/ornekler/minimal_koordinator.py --baslangic tur-0.safetensors --tur 5 --en-az 2 --port 8750
```

## 3. Run the conformance test

```bash
python istemci/uyum_testi.py --url http://127.0.0.1:8750
```

A passing run ends with `UYUMLU` (compliant) and exit code 0. See [Conformance test](/en/uyum-testi/).

## 4. Query the Portal API

```bash
curl -s https://modelen.tr/api/v1/saglik
curl -s https://modelen.tr/api/v1/koordinatorler
```

To act on your own account you need an [API key](/en/api/#creating-an-api-key).

## Next

- Go public: [Becoming a coordinator](/en/koordinator-olmak/)
- Understand the wire format: [Protocol v1](/en/protokol/)
