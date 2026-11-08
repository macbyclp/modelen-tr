---
baslik: Adaptör biçimi
bolum: Kendi sistemini bağlamak
sira: 3
ozet: Protokol v1'de ağdan geçen LoRA adaptörünün safetensors düzeni: tensör adları, şekiller, boyut ve doğrulama kuralları.
---

# Adaptör biçimi

Protokol v1'de ağdan geçen tek ağırlık, **Qwen3-0.6B-Base** için **LoRA adaptörüdür**. Biçim sabittir; farklı bir biçim gönüllü uygulamasıyla uyumsuzdur.

## Özet

| Özellik | Değer |
|---|---|
| Taban model | `Qwen/Qwen3-0.6B-Base` (28 katman, gizli boyut 1024) |
| Yöntem | LoRA (PEFT), `r = 16`, `alfa = 32`, bırakma (dropout) 0 |
| Hedef modüller | `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj` (her katmanda) |
| Dosya biçimi | [safetensors](https://github.com/huggingface/safetensors) |
| Tür | **float32** (`F32`) |
| Tensör sayısı | **392** (28 katman × 7 modül × A ve B) |
| Parametre / boyut | ≈ 10,09 milyon / ≈ **40,4 MB** |
| Üst veri | Yok (`__metadata__` kullanılmaz) |

## Tensör adları

```text
base_model.model.model.layers.{L}.self_attn.{q|k|v|o}_proj.lora_{A|B}.default.weight
base_model.model.model.layers.{L}.mlp.{gate|up|down}_proj.lora_{A|B}.default.weight
```

`L` = 0…27. Örnek: `base_model.model.model.layers.0.mlp.down_proj.lora_A.default.weight`.

## Şekiller

`lora_A` şekli `[16, giriş]`, `lora_B` şekli `[çıkış, 16]`:

| Modül | `lora_A` | `lora_B` |
|---|---|---|
| `q_proj` | `[16, 1024]` | `[2048, 16]` |
| `k_proj` | `[16, 1024]` | `[1024, 16]` |
| `v_proj` | `[16, 1024]` | `[1024, 16]` |
| `o_proj` | `[16, 2048]` | `[1024, 16]` |
| `gate_proj` | `[16, 1024]` | `[3072, 16]` |
| `up_proj` | `[16, 1024]` | `[3072, 16]` |
| `down_proj` | `[16, 3072]` | `[1024, 16]` |

## Doğrulama kuralları (koordinatör tarafı)

Gelen her adaptör şunları sağlamalıdır; aksi hâlde `422` ile reddedilir ([protokol](/protokol/#post-sonuc-isci-ad-tur-n-zorunlu)):

1. **Anahtar kümesi** global adaptörle birebir aynı (eksik ya da fazla tensör yok).
2. Her tensörün **şekli** ve **dtype**'ı global olanla aynı.
3. Tüm değerler **sonlu** (NaN/Inf yok).
4. Gövde geçerli **safetensors** (başlık JSON, veri aralıkları dosya içinde). Pickle ya da başka biçim reddedilir.

Bu kuralların hepsini [uyum testi](/uyum-testi/) ve [örnek koordinatör](/minimal-koordinator/) uygular.

## Başlangıç adaptörü (`tur-0`)

Başlangıç adaptörünü referans betik üretir:

```bash
python istemci/baslat.py --model models/qwen3-0.6b-base --tohum 0 --cikti istemci/calisma/tur-0.safetensors
```

`--tohum` aynı olduğunda aynı başlangıç adaptörü çıkar. İşçi, modeli görevdeki `tohum` ile kurup üzerine koordinatörün adaptörünü yazar; bu yüzden tüm işçilerde LoRA başlangıç düzeni aynıdır.

## Dosyayı incelemek

safetensors başlığı düz JSON'dur; PyTorch olmadan da okunabilir:

```python
import json, struct
f = open("tur-3.safetensors", "rb")
n = struct.unpack("<Q", f.read(8))[0]          # başlık uzunluğu
baslik = json.loads(f.read(n))
adlar = [k for k in baslik if k != "__metadata__"]
print(len(adlar), "tensör")                      # 392
print(adlar[0], baslik[adlar[0]]["dtype"], baslik[adlar[0]]["shape"])
```

:::not
Farklı bir taban model ya da farklı LoRA ayarı (r, hedef modüller) için *yeni bir adaptör biçimi ve manifest* gerekir; bu planlanan işlerdendir ([yol haritası](/yol-haritasi/)).
:::
