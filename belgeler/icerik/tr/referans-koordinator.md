---
baslik: Referans koordinatör
bolum: Kendi sistemini bağlamak
sira: 4
ozet: istemci/koordinator.py: kurulum, tüm bayraklar, çıktı dosyaları, dağıtım ve bilinen sınırlar.
---

# Referans koordinatör

`istemci/koordinator.py`, protokol v1'in tam ve gerçek eğitimle denenmiş uygulamasıdır (Python standart HTTP sunucusu + PyTorch). Kendi koordinatörünüzü yazmadan başlamak için en kısa yol budur.

## Gereksinimler

- Python 3.10+, `torch`, `safetensors`, `transformers`, `peft` (başlangıç adaptörünü üretmek için)
- Taban model: `models/qwen3-0.6b-base` (Qwen/Qwen3-0.6B-Base, Apache-2.0). Koordinatör yalnızca **adaptör ağırlıklarını** işler; ama başlangıç adaptörünü üreten betik modele ihtiyaç duyar. GPU gerekmez.
- RAM: birkaç yüz MB (adaptör 40 MB, işçi sayısıyla çarpılır).

## Çalıştırma

```bash
python istemci/baslat.py                                   # tur-0 adaptörünü üretir
python istemci/koordinator.py \
    --baslangic istemci/calisma/tur-0.safetensors \
    --tur 20 --en-az 2 --ic-adim 20 --port 8750
```

Durum paneli: `http://127.0.0.1:8750/` (JSON: `/durum`).

## Bayraklar

| Bayrak | Varsayılan | Anlamı |
|---|---|---|
| `--baslangic` | *(zorunlu)* | Başlangıç adaptörü (`baslat.py` çıktısı) |
| `--host` | `127.0.0.1` | Dinlenecek adres. Genel ağda doğrudan `0.0.0.0` yapmayın; ters vekil kullanın |
| `--port` | `8750` | Port |
| `--tur` | `6` | Toplam tur sayısı |
| `--en-az` | `2` | Turu kapatmak için gereken en az sonuç |
| `--zaman-asimi` | `900` | Saniye; dolunca eldeki (≥1) sonuçla tur kapanır |
| `--parca` | `4` | Veri dilimi sayısı (`n_parca`); işçilere dönüşümlü atanır |
| `--ic-adim` | `20` | H: işçinin yerel adım sayısı |
| `--bs` | `4` | Yığın büyüklüğü |
| `--seq` | `512` | Dizi uzunluğu |
| `--lr` | `2e-4` | Tepe öğrenme oranı (işçide kosinüs çizelgesi) |
| `--dis-lr` | `1.0` | Dış adım öğrenme oranı |
| `--dis-mom` | `0.5` | Dış adım momentumu |
| `--aykiri-kat` | `5.0` | Delta normu medyanın bu katını aşan sonucu ele (≥3 sonuçta) |
| `--anahtar` | *(boş)* | Doluysa tüm istekler `X-Anahtar` başlığı taşımalı |
| `--calisma` | `istemci/calisma` | Çıktı klasörü |
| `--tohum` | `0` | Başlangıç adaptörü tohumu |

## Çıktı dosyaları

`--calisma` klasöründe:

| Dosya | İçerik |
|---|---|
| `tur-N.safetensors` | N. turun sonunda global adaptör (tur-0 başlangıçtır) |
| `gunluk.json` | Tur günlüğü (kullanılan/elenen işçiler, delta normları, süre) ve trafik |
| `sorular.jsonl` | `/soru` ile gelen topluluk soruları (`python istemci/sorular.py` ile okunur) |

## Genel ağda yayınlama

```text
koordinator.ornek.org {
    reverse_proxy 127.0.0.1:8750
}
```

Sonra [uyum testini](/uyum-testi/) çalıştırın ve [adresinizi doğrulayın](/adres-dogrulama/). Systemd ile kalıcı çalıştırma:

```text
[Unit]
Description=Modelen koordinatoru
After=network.target

[Service]
User=modelen
WorkingDirectory=/opt/modelen
ExecStart=/opt/modelen/.venv/bin/python istemci/koordinator.py --baslangic istemci/calisma/tur-0.safetensors --tur 50 --en-az 3
Restart=always

[Install]
WantedBy=multi-user.target
```

## Bilinen sınırlar

:::uyari
Referans koordinatör bir **prototiptir**:

- Dış adım momentum tamponu **bellekte** durur; yeniden başlatınca sıfırlanır (turlar diske yazılır).
- Kimlik doğrulama yalnızca isteğe bağlı **tek paylaşılan anahtardır**; hesap/hız sınırı yoktur. Sybil saldırısına açıktır.
- Zehirlenme koruması yalnızca **basit aykırı norm elemesidir** (≥3 sonuçta). Kararlı bir saldırgana karşı yetmez; tekrarlı doğrulama (aynı görevi iki işçiye verip karşılaştırma) yapılmaz.
- TLS yoktur; ters vekil gerekir.
- Tüm işçiler aynı adım sayısını yapar; yavaş bir GPU turu geciktirir (zaman aşımı eldekilerle kapatır).
:::

Ayrıntılı liste: [`istemci/ISTEMCI.md`](https://github.com/macbyclp/modelen-tr/blob/main/istemci/ISTEMCI.md).
