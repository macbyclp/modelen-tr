---
baslik: Gönüllü kurulumu
bolum: Başlarken
sira: 4
ozet: GPU'nuzu bir koordinatöre adamak için Windows kurulumu: gereksinimler, kurulum betiği, ne kurulur, nasıl kaldırılır.
---

# Gönüllü kurulumu

Gönüllü, kendi GPU'sunu bir koordinatöre adayan kişidir. Eğitim yerelde yapılır; ağdan yalnızca küçük LoRA adaptörü (~40 MB) ve koordinatörün sunduğu veri dilimi geçer.

:::uyari
**Durum: kurulum betiği yazıldı ama henüz temiz bir makinede uçtan uca denenmedi**, sürüm paketleri (`modelen.exe`, `modelen-istemci.zip`) ise ilk etiketli sürümle birlikte üretilecek. Betiği kendi sorumluluğunuzda ve önce `-Dene` ile deneyin; sorun yaşarsanız [GitHub'da](https://github.com/macbyclp/modelen-tr/issues) bildirin.
:::

## Gereksinimler (Windows)

- Windows 10/11 (64 bit)
- **NVIDIA GPU**, en az 6 GB VRAM (8 GB ile denendi) ve güncel NVIDIA sürücüsü
- ~8 GB boş disk (PyTorch yaklaşık 3 GB, taban model 1,2 GB)
- İnternet bağlantısı (indirmeler yüzlerce MB'tır; sınırlı kotalı bağlantıda dikkat edin)
- Yönetici yetkisi **gerekmez**

## Kurulum (Windows)

### En kolay yol: Modelen-Kurulum.exe

[Sürümler sayfasından](https://github.com/macbyclp/modelen-tr/releases/latest) **`Modelen-Kurulum.exe`** dosyasını indirip çift tıklayın. Bir pencere açılır, aşağıdaki adımları sizin yerinize yapar ve bitince Enter ister. (Aşağıdaki `kur.ps1` betiğinin tek dosyaya gömülmüş halidir; aynı parametreleri alır, örn. `Modelen-Kurulum.exe -Dene`.)

:::not
Program henüz **dijital olarak imzalı değil**; bu yüzden Windows SmartScreen "Windows bilgisayarınızı korudu" uyarısı gösterebilir. Kaynağı doğruladıktan sonra **Daha fazla bilgi → Yine de çalıştır** diyebilirsiniz. Doğrulama: sürüm sayfasındaki `SHA256SUMS` ile dosyanın özetini karşılaştırın (`Get-FileHash Modelen-Kurulum.exe`) ya da `gh attestation verify Modelen-Kurulum.exe --repo macbyclp/modelen-tr` çalıştırın.
:::

### PowerShell betiğiyle

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

## Ne kurulur? (Windows)

Her şey tek klasördedir (`%LOCALAPPDATA%\Modelen`); sistem Python'unuza dokunulmaz.

| Yol | İçerik |
|---|---|
| `modelen.exe` | Masaüstü uygulaması (Kolay mod: tek düğmeyle işçi ol) |
| `istemci\` | İşçi betikleri |
| `.venv\` | Python 3.12 + PyTorch + `transformers`, `peft`, `safetensors` ([uv](https://github.com/astral-sh/uv) ile kurulur) |
| `models\qwen3-0.6b-base\` | Taban model (Qwen3-0.6B-Base, Apache-2.0) |
| `arac\uv.exe` | Kurulum aracı |

Betik, sürüm varlıklarının SHA-256 özetini `SHA256SUMS` ile karşılaştırır. Başlat menüsüne **Modelen** kısayolu eklenir.

## Kullanım (Windows)

1. Başlat menüsünden **Modelen**'i açın (Kolay mod).
2. Bir **koordinatör** seçin ([onaylı dizin](https://modelen.tr/koordinatorler)). Hangi veriyle ve hangi modda eğitileceğini koordinatör belirler; seçmeden önce açıklamasını okuyun.
3. **AÇIK** düğmesine basın. Uygulama görev alır, eğitir, sonucu yükler. Durdurmak için **KAPALI**.

İşçi, koordinatörün sunduğu veri dilimini ilk turda indirip `%USERPROFILE%\.modelen\veri` altında önbelleğe alır; sonraki turlarda yeniden indirmez.

## Ubuntu / Linux

Linux'ta grafik arayüz yoktur; işçi komut satırından çalışır. `kur.sh` aynı şeyi (Python, PyTorch, taban model) sudo gerektirmeden `~/.local/share/modelen` altına kurar.

```bash
curl -fsSL https://raw.githubusercontent.com/macbyclp/modelen-tr/main/kur.sh -o kur.sh
bash kur.sh --dene     # önce ne yapacağına bak (hiçbir şey kurmaz)
bash kur.sh
```

Sonra işçiyi başlatın:

```bash
modelen-isci --koordinator https://koordinator.ornek.org --isci takma-adiniz
```

| Seçenek | Anlamı |
|---|---|
| `--hedef` | Kurulum klasörü (varsayılan `~/.local/share/modelen`) |
| `--surum` | GitHub sürüm etiketi (varsayılan: en son) |
| `--cuda` | PyTorch tekeri: `cu124` (varsayılan), `cu121`, `cu126`, `cpu` (yalnızca deneme) |
| `--model-atla` | Taban modeli indirme |
| `--dene` | Yalnızca ön koşulları denetle ve planı yaz |

Gereksinimler: x86_64 Linux, NVIDIA GPU (en az 6 GB) ve güncel sürücü (`cu124` için ≥ 550; Ubuntu'da `sudo ubuntu-drivers install`), ~8 GB boş disk, `curl`. Kaldırmak için `rm -rf ~/.local/share/modelen ~/.local/bin/modelen-isci`.

:::not
`kur.sh`, GitHub'ın temiz bir Ubuntu makinesinde (GPU'suz, `--cuda cpu`, modelsiz) otomatik olarak sınanır; GPU'lu eğitim bu testin kapsamında değildir.
:::

## macOS

**Desteklenmiyor.** İşçi bugün NVIDIA/CUDA gerektirir; Mac'lerde NVIDIA ekran kartı yoktur. Apple Silicon (MPS) desteği planlanabilir ama henüz yoktur.

## Gizlilik ve güvenlik

- Eğitim **sizin GPU'nuzda** olur; yalnızca eğitilmiş adaptör koordinatöre gider. Takma ad dışında kişisel veri gönderilmez.
- Ağdan gelen ağırlık ve veri yalnızca **safetensors** olarak okunur (pickle yok, kod çalıştırmaz); özetleri doğrulanır.
- Koordinatöre güvenmeden önce kim olduğunu düşünün: eğitim verisini o seçer. Bkz. [Güvenlik](/guvenlik/).

## Kaldırma (Windows)

`%LOCALAPPDATA%\Modelen` klasörünü ve Başlat menüsündeki `Modelen.lnk` kısayolunu silin. Ayarlar `%APPDATA%\Modelen`'dedir (API anahtarları Windows kimlik kasasında).
