---
baslik: Kendi koordinatörünüzü yazın
bolum: Kendi sistemini bağlamak
sira: 5
ozet: Protokol v1'e uyan en küçük koordinatör örneği (yalnızca standart kütüphane) ve kendi servisinizi yazarken izleyeceğiniz adımlar.
---

# Kendi koordinatörünüzü yazın

Protokol v1'i uygulayan her HTTP servisi koordinatör olabilir. **Çalışan, test edilmiş en küçük örnek** `istemci/ornekler/minimal_koordinator.py` dosyasıdır (~150 satır, yalnızca Python standart kütüphanesi). Her sürümde [uyum testinden](/uyum-testi/) ve tam bir tur döngüsü testinden geçer.

```bash
# başlangıç adaptörü olarak herhangi bir float32 safetensors dosyası yeter (protokolü denemek için)
python istemci/ornekler/minimal_koordinator.py --baslangic tur-0.safetensors --tur 5 --en-az 2 --port 8750
python istemci/uyum_testi.py --url http://127.0.0.1:8750
```

## Örneğin yaptıkları

| Uç nokta | Ne yapar |
|---|---|
| `GET /bilgi` | `protokol: "1"`, tur ve ağırlık özeti |
| `GET /durum` | Tur, bekleyen sonuçlar, işçiler, trafik |
| `GET /gorev` | `isci` yoksa 400; tur bittiyse `bitti`; işçinin bu tur sonucu varsa `bekle`; yoksa görev (işçilere dönüşümlü veri dilimi) |
| `GET /agirlik` | Global adaptör + `X-Tur` + `X-Sha256` |
| `POST /sonuc` | Doğrula → sakla → `en_az` sonuç gelince turu kapat |

**Referans koordinatörden farkları:** düz ortalama (dış adım/momentum yok), aykırı eleme yok, saf Python safetensors (yavaş, yalnızca float32), durum bellekte.

## Kendi servisinizi yazarken adımlar

1. **Başlangıç adaptörünü yükleyin** ve SHA-256'sını hesaplayın (`/gorev.agirlik_sha256` ve `/agirlik` başlığı bunu kullanır).
2. **`GET /gorev`**: `isci` zorunlu; tur bitmişse `{"bitti":true}`; işçi bu tur gönderdiyse `{"bekle":true,"tur":N}`; aksi hâlde görev nesnesi. İşçiye *sabit* bir `parca` verin (tur boyunca aynı kalsın).
3. **`GET /agirlik`**: global adaptör baytları ve `X-Tur`, `X-Sha256` başlıkları.
4. **`POST /sonuc`** için *sırayla* şunları denetleyin:
   - Gövde boş/çok büyükse `413`.
   - safetensors olarak okunamıyorsa `400` (pickle kabul etmeyin).
   - Tur uyuşmuyorsa `409`; aynı işçi ikinci kez gönderdiyse `409`; eğitim bittiyse `409`.
   - Anahtar kümesi, şekil, dtype uyuşmuyorsa ya da NaN/Inf varsa `422`.
   - Geçerliyse sakla ve `{"tamam":true,"tur":N}` dön.
5. **Turu kapatın**: yeterli sonuç (ya da zaman aşımı) gelince birleştirin, `tur += 1`, yeni baytları ve SHA-256'yı yayınlayın.
6. **HTTPS arkasında yayınlayın** ve [uyum testini](/uyum-testi/) çalıştırın.

## Çekirdek mantık

Örnekteki iki asıl parça aşağıdadır. Birincisi, gelen adaptörün **doğrulanması**:

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

İkincisi, turun **kapatılması** (düz ortalama):

```python
def tur_kapat(self):
    for ad in self.glob:
        n = len(self.sonuclar)
        ort = array.array("f", (sum(v) / n for v in zip(*(s[ad] for s in self.sonuclar.values()))))
        self.glob[ad] = ort
    self.sonuclar = {}
    self.tur += 1
    self._baytla()      # yeni baytlar ve SHA-256
```

Gerçek bir sistemde birleştirmeyi NumPy/PyTorch ile yapın (bu saf Python örneği 10 milyon parametrede yavaştır) ve aykırı elemeyi ekleyin.

:::ipucu
Ayrıca portala [nabız](/nabiz/) göndermeyi unutmayın: `python istemci/ornekler/modelen_api.py nabiz-dongusu --koordinator https://adresiniz`.
:::

Dosyanın tamamı: [`istemci/ornekler/minimal_koordinator.py`](https://github.com/macbyclp/modelen-tr/blob/main/istemci/ornekler/minimal_koordinator.py).
