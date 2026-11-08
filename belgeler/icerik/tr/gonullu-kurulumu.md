---
baslik: Gönüllü kurulumu
bolum: Başlarken
sira: 4
ozet: GPU'nuzu bir koordinatöre adamak için Windows kurulumu: gereksinimler, kurulum betiği, ne kurulur, nasıl kaldırılır.
---

# Gönüllü kurulumu (Windows)

Gönüllü, kendi GPU'sunu bir koordinatöre adayan kişidir. Eğitim yerelde yapılır; ağdan yalnızca küçük LoRA adaptörü (~40 MB) ve koordinatörün sunduğu veri dilimi geçer.

:::uyari
**Durum: kurulum betiği yazıldı ama henüz temiz bir makinede uçtan uca denenmedi**, sürüm paketleri (`modelen.exe`, `modelen-istemci.zip`) ise ilk etiketli sürümle birlikte üretilecek. Betiği kendi sorumluluğunuzda ve önce `-Dene` ile deneyin; sorun yaşarsanız [GitHub'da](https://github.com/macbyclp/modelen-tr/issues) bildirin.
:::

## Gereksinimler

- Windows 10/11 (64 bit)
- **NVIDIA GPU**, en az 6 GB VRAM (8 GB ile denendi) ve güncel NVIDIA sürücüsü
- ~8 GB boş disk (PyTorch yaklaşık 3 GB, taban model 1,2 GB)
- İnternet bağlantısı (indirmeler yüzlerce MB'tır; sınırlı kotalı bağlantıda dikkat edin)
- Yönetici yetkisi **gerekmez**

## Kurulum

`kur.ps1` dosyasını [depodan](https://github.com/macbyclp/modelen-tr/blob/main/kur.ps1) indirin. Önce ne yapacağına bakın (hiçbir şey kurmaz):

```bash
powershell -ExecutionPolicy Bypass -File kur.ps1 -Dene
```

Sonra kurun:

```bash
powershell -ExecutionPolicy Bypass -File kur.ps1
```

| Parametre | Anlamı |
|---|---|
| `-Hedef` | Kurulum klasörü (varsayılan `%LOCALAPPDATA%\Modelen`) |
| `-Surum` | GitHub sürüm etiketi (varsayılan: en son) |
| `-CudaSurumu` | PyTorch tekeri: `cu124` (varsayılan), `cu121`, `cu126`, `cpu` (yalnızca deneme) |
| `-Kaynak` | Çevrimdışı/yerel kurulum: depo kökü (içinde `istemci\`) |
| `-ModelAtla` | Taban modeli indirme |
| `-Dene` | Yalnızca ön koşulları denetle ve planı yaz |

## Ne kurulur?

Her şey tek klasördedir (`%LOCALAPPDATA%\Modelen`); sistem Python'unuza dokunulmaz.

| Yol | İçerik |
|---|---|
| `modelen.exe` | Masaüstü uygulaması (Kolay mod: tek düğmeyle işçi ol) |
| `istemci\` | İşçi betikleri |
| `.venv\` | Python 3.12 + PyTorch + `transformers`, `peft`, `safetensors` ([uv](https://github.com/astral-sh/uv) ile kurulur) |
| `models\qwen3-0.6b-base\` | Taban model (Qwen3-0.6B-Base, Apache-2.0) |
| `arac\uv.exe` | Kurulum aracı |

Betik, sürüm varlıklarının SHA-256 özetini `SHA256SUMS` ile karşılaştırır. Başlat menüsüne **Modelen** kısayolu eklenir.

## Kullanım

1. Başlat menüsünden **Modelen**'i açın (Kolay mod).
2. Bir **koordinatör** seçin ([onaylı dizin](https://modelen.tr/koordinatorler)). Hangi veriyle ve hangi modda eğitileceğini koordinatör belirler; seçmeden önce açıklamasını okuyun.
3. **AÇIK** düğmesine basın. Uygulama görev alır, eğitir, sonucu yükler. Durdurmak için **KAPALI**.

İşçi, koordinatörün sunduğu veri dilimini ilk turda indirip `%USERPROFILE%\.modelen\veri` altında önbelleğe alır; sonraki turlarda yeniden indirmez.

## Gizlilik ve güvenlik

- Eğitim **sizin GPU'nuzda** olur; yalnızca eğitilmiş adaptör koordinatöre gider. Takma ad dışında kişisel veri gönderilmez.
- Ağdan gelen ağırlık ve veri yalnızca **safetensors** olarak okunur (pickle yok, kod çalıştırmaz); özetleri doğrulanır.
- Koordinatöre güvenmeden önce kim olduğunu düşünün: eğitim verisini o seçer. Bkz. [Güvenlik](/guvenlik/).

## Kaldırma

`%LOCALAPPDATA%\Modelen` klasörünü ve Başlat menüsündeki `Modelen.lnk` kısayolunu silin. Ayarlar `%APPDATA%\Modelen`'dedir (API anahtarları Windows kimlik kasasında).
