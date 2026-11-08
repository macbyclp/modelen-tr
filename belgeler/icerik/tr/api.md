---
baslik: API'ye giriş
bolum: Portal API
sira: 1
ozet: Modelen Portal API v1: anahtar oluşturma, kimlik doğrulama, hata kodları, hız sınırları, CORS ve curl / Python / JavaScript örnekleri.
---

# Portal API'ye giriş

Portal API, koordinatörlerin Modelen portalını **programla** yönetmesini sağlar: başvuru ve profil güncelleme, [nabız](/nabiz/) gönderme, [adres doğrulama](/adres-dogrulama/) ve herkese açık koordinatör dizinini okuma.

- **Taban adres:** `https://modelen.tr/api/v1`
- **Biçim:** JSON (UTF-8). İstek gövdesi `Content-Type: application/json`.
- **Şema:** [`/api/v1/openapi.json`](https://modelen.tr/api/v1/openapi.json) (OpenAPI 3.0) ve [uç nokta başvurusu](/api-referans/).

## Herkese açık uç noktalar

Anahtar gerekmez; CORS açıktır (tarayıcıdan çağrılabilir).

```bash
curl -s https://modelen.tr/api/v1/saglik
curl -s https://modelen.tr/api/v1/koordinatorler
```

## API anahtarı oluşturmak

1. [modelen.tr](https://modelen.tr) üzerinde hesap açın ve e-postanızı doğrulayın.
2. **Panel → Geliştiriciler için → API anahtarları** (`/panel/api`) sayfasına gidin.
3. Anahtara bir ad verip oluşturun. `mdl_` ile başlayan anahtar **yalnızca bir kez** gösterilir; hemen kaydedin.

:::uyari
Anahtar parolanız gibidir. Sunucuda yalnızca SHA-256 özeti saklanır; kaybederseniz geri getirilemez, yenisini oluşturup eskisini iptal edersiniz. Anahtarı depoya, istemci tarafı koda ya da herkese açık günlüklere koymayın.
:::

Hesap başına **en çok 5 etkin anahtar** vardır. Anahtarlar panelden istediğiniz an iptal edilir.

## Kimlik doğrulama

Anahtarı `Authorization: Bearer` başlığıyla gönderin:

```bash
curl -s https://modelen.tr/api/v1/ben -H "Authorization: Bearer $MODELEN_API_ANAHTARI"
```

```python
import json, os, urllib.request
istek = urllib.request.Request("https://modelen.tr/api/v1/ben",
    headers={"Authorization": "Bearer " + os.environ["MODELEN_API_ANAHTARI"]})
print(json.load(urllib.request.urlopen(istek)))
```

```javascript
const yanit = await fetch("https://modelen.tr/api/v1/ben", {
  headers: { Authorization: `Bearer ${process.env.MODELEN_API_ANAHTARI}` },
});
console.log(await yanit.json());
```

:::ipucu
Python için hazır bir istemci var: `istemci/ornekler/modelen_api.py` (yalnızca standart kütüphane). `python modelen_api.py ben` ile denersiniz.
:::

## Koordinatör başvurusu ve güncelleme

```bash
# başvuru oluştur (e-posta doğrulanmış olmalı)
curl -s -X POST https://modelen.tr/api/v1/koordinator \
  -H "Authorization: Bearer $MODELEN_API_ANAHTARI" -H "Content-Type: application/json" \
  -d '{"ad":"Örnek Lab","kisa":"Açık modeller için gönüllü eğitim koordinatörü","adres":"https://koordinator.ornek.org"}'

# alan güncelle (yalnızca gönderilen alanlar değişir)
curl -s -X PATCH https://modelen.tr/api/v1/koordinator \
  -H "Authorization: Bearer $MODELEN_API_ANAHTARI" -H "Content-Type: application/json" \
  -d '{"ayrinti":"Hedefimiz ..."}'
```

İzin verilen alanlar: `ad`, `kisa`, `ayrinti`, `baglanti`, `adres`, `hf`, `iletisim`. Başka alan göndermek `400 bilinmeyen_alan` döner.

| Durum | Anlamı |
|---|---|
| `201` | Başvuru oluşturuldu, yönetici onayına düştü |
| `200` | Güncellendi (henüz onaylanmamış başvuru) |
| `202` | **Onaylı** profilde değişiklik taslak olarak kaydedildi; yönetici onayından sonra yayına girer |

Adresi değiştirirseniz doğrulama sıfırlanır; yeniden [doğrulamanız](/adres-dogrulama/) gerekir.

## Hata biçimi

Tüm hatalar aynı biçimdedir; `kod` makine tarafından, `hata` insan tarafından okunur:

```json
{"hata": "Anahtar başına dakikada en çok 120 istek.", "kod": "hiz_siniri"}
```

| HTTP | `kod` | Ne zaman |
|---|---|---|
| 400 | `gecersiz_istek` | Gövde geçerli JSON nesnesi değil |
| 400 | `bilinmeyen_alan` | İzin verilmeyen alan |
| 400 | `dogrulama` | Alan değeri geçersiz (uzunluk, bağlantı biçimi vb.) |
| 400 | `gecersiz_tur` / `gecersiz_durum` / `gecersiz_sayi` / `gecersiz_metin` | Nabız alanı geçersiz |
| 400 | `adres_yok` / `baslatilmadi` | Adres doğrulaması için adres yok / doğrulama başlatılmadı |
| 401 | `yetkisiz` | Anahtar yok, yanlış ya da iptal edilmiş |
| 403 | `eposta_dogrulanmadi` | E-postanızı doğrulamadan başvuru yapılamaz |
| 403 | `onayli_degil` | Bu işlem yalnızca onaylı koordinatörlere açık (ör. nabız) |
| 404 | `yok` / `basvuru_yok` | Kaynak ya da başvurunuz yok |
| 405 | `yontem` | Bu yol için yöntem desteklenmiyor |
| 409 | `basvuru_var` / `askida` | Zaten başvuru var / başvurunuz askıda |
| 422 | `okunamadi` / `icerik_uyusmuyor` | Adres doğrulama dosyası okunamadı / içerik uyuşmuyor |
| 429 | `hiz_siniri` | Hız sınırı; `Retry-After` başlığındaki saniye kadar bekleyin |

## Hız sınırları

| Sınır | Değer |
|---|---|
| Anahtar başına | 120 istek / dakika |
| IP başına (tüm istekler) | 240 istek / dakika |
| Geçersiz anahtar denemesi | 10 dakikada 30 (aşılırsa 10 dk engel) |
| [Nabız](/nabiz/) | 6 istek / dakika |
| Adres doğrulama kontrolü | 10 dakikada 10 deneme |

`429` yanıtı `Retry-After` başlığı taşır. Azalan aralıkla (üstel geri çekilme) yeniden deneyin.

## CORS

Herkese açık uç noktalar (`/saglik`, `/koordinatorler`, `/koordinatorler/{slug}`) her kaynaktan çağrılabilir. Anahtarlı uç noktalar da `OPTIONS` ön denetimine yanıt verir, ama **anahtarı tarayıcı kodunda kullanmayın**; anahtarlı çağrıları sunucunuzdan yapın.

## Sürümleme

Yol `/api/v1`. Geriye uyumlu eklemeler (yeni alan, yeni uç nokta) aynı sürümde yapılır; kırıcı değişiklik `/api/v2` olarak gelir. Yanıtlarda bilmediğiniz alanları yok sayın.
