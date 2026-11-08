---
baslik: Nabız
bolum: Portal API
sira: 2
ozet: Koordinatörünüzün portalda çevrimiçi görünmesi için nabız göndermek: alanlar, durum hesabı ve döngü örneği.
---

# Nabız (heartbeat)

Onaylı bir koordinatör, çalıştığını portala **nabız** göndererek bildirir. Herkese açık koordinatör sayfasında ve dizinde "çevrimiçi / gecikmeli" rozetini bu belirler. Nabız göndermek zorunlu değildir, ama gönüllüler canlı bir koordinatörü seçmek ister.

```bash
curl -s -X POST https://modelen.tr/api/v1/koordinator/nabiz \
  -H "Authorization: Bearer $MODELEN_API_ANAHTARI" -H "Content-Type: application/json" \
  -d '{"durum":"calisiyor","tur":3,"toplam_tur":20,"aktif_isci":7,"protokol":"1","surum":"0.4.0"}'
```

## Alanlar

| Alan | Tür | Zorunlu | Anlamı |
|---|---|---|---|
| `durum` | metin | **evet** | `calisiyor`, `bekliyor`, `bakimda` ya da `durdu` |
| `tur` | tamsayı ≥ 0 | hayır | Şu anki tur |
| `toplam_tur` | tamsayı ≥ 0 | hayır | Planlanan tur sayısı |
| `aktif_isci` | tamsayı ≥ 0 | hayır | Son zamanlarda görülen işçi sayısı |
| `protokol` | metin ≤ 10 | hayır | Örn. `"1"` |
| `surum` | metin ≤ 30 | hayır | Koordinatör yazılımınızın sürümü |
| `mesaj` | metin ≤ 120 | hayır | Kısa not (ör. bakım zamanı) |

Başka alan göndermek `400 bilinmeyen_alan`, hatalı değer `400 gecersiz_*` döner. Yalnızca **onaylı** koordinatör nabız gönderebilir (`403 onayli_degil`). Sınır: dakikada 6.

## Herkese açık durum nasıl hesaplanır?

Gönderdiğiniz `durum` ve son nabızdan geçen süre birleşerek şu değeri verir:

| Görünen durum | Koşul |
|---|---|
| `cevrimici` | `calisiyor`/`bekliyor` ve son nabız ≤ 15 dakika önce |
| `gecikmeli` | `calisiyor`/`bekliyor` ve son nabız ≤ 24 saat önce |
| `bakimda` | Son nabızda `bakimda` bildirildi (24 saat içinde) |
| `durdu` | Son nabızda `durdu` bildirildi (24 saat içinde) |
| `bilinmiyor` | Hiç nabız yok ya da 24 saatten eski |

Bu yüzden **en geç 15 dakikada bir** göndermelisiniz; 5 dakika iyi bir aralıktır.

## Döngü örneği

Hazır istemciyle:

```bash
export MODELEN_API_ANAHTARI=mdl_...
python istemci/ornekler/modelen_api.py nabiz-dongusu --koordinator http://127.0.0.1:8750 --aralik 300
```

Bu komut koordinatörünüzün `/durum` ve `/bilgi` uç noktalarından tur ve işçi sayısını okuyup portala iletir. Kendi kodunuzda:

```python
import json, time, urllib.request

def nabiz(anahtar, durum="calisiyor", **alanlar):
    govde = json.dumps({"durum": durum, **alanlar}).encode()
    istek = urllib.request.Request("https://modelen.tr/api/v1/koordinator/nabiz", govde, method="POST",
        headers={"Authorization": f"Bearer {anahtar}", "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(istek, timeout=15))

while True:
    d = json.load(urllib.request.urlopen("http://127.0.0.1:8750/durum"))
    nabiz(ANAHTAR, tur=d["tur"], toplam_tur=d["toplam_tur"], aktif_isci=len(d["isciler"]), protokol="1")
    time.sleep(300)
```

:::ipucu
Planlı bakımda `durum: "bakimda"` ve `mesaj` gönderin; sayfanız "bilinmiyor" yerine "bakımda" görünür.
:::
