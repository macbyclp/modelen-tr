---
baslik: Adapter format
bolum: Connecting your system
sira: 2
ozet: The safetensors layout of the LoRA adapter that travels over the wire in protocol v1.
---

# Adapter format

The only weights on the wire in protocol v1 are a **LoRA adapter for Qwen3-0.6B-Base**. The layout is fixed.

| Property | Value |
|---|---|
| Base model | `Qwen/Qwen3-0.6B-Base` (28 layers, hidden size 1024) |
| Method | LoRA (PEFT), `r = 16`, `alpha = 32`, dropout 0 |
| Target modules | `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj` in every layer |
| File format | safetensors |
| dtype | **float32** (`F32`) |
| Tensors | **392** (28 layers × 7 modules × A and B) |
| Size | ≈ 10.09 M parameters / ≈ 40.4 MB |
| Metadata | none |

## Tensor names

```text
base_model.model.model.layers.{L}.self_attn.{q|k|v|o}_proj.lora_{A|B}.default.weight
base_model.model.model.layers.{L}.mlp.{gate|up|down}_proj.lora_{A|B}.default.weight
```

`L` = 0…27.

## Shapes

`lora_A` is `[16, in]`, `lora_B` is `[out, 16]`:

| Module | `lora_A` | `lora_B` |
|---|---|---|
| `q_proj` | `[16, 1024]` | `[2048, 16]` |
| `k_proj`, `v_proj` | `[16, 1024]` | `[1024, 16]` |
| `o_proj` | `[16, 2048]` | `[1024, 16]` |
| `gate_proj`, `up_proj` | `[16, 1024]` | `[3072, 16]` |
| `down_proj` | `[16, 3072]` | `[1024, 16]` |

## Validation (coordinator side)

Reject with `422` unless the upload has exactly the same key set as the global adapter, identical shape and dtype per tensor, only finite values, and is valid safetensors (pickle or other formats are rejected).

The safetensors header is plain JSON, so you can inspect a file without PyTorch:

```python
import json, struct
f = open("tur-3.safetensors", "rb")
n = struct.unpack("<Q", f.read(8))[0]
baslik = json.loads(f.read(n))
adlar = [k for k in baslik if k != "__metadata__"]
print(len(adlar))   # 392
```
