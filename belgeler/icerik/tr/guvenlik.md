---
baslik: Güvenlik
bolum: Güvenlik
sira: 1
ozet: Koordinatör işletirken güvenlik: HTTPS, anahtarlar, pickle yasağı, zehirlenme sınırları ve açık bildirim.
---

# Güvenlik

## Ağ ve veri

- **HTTPS zorunlu.** Genel ağda koordinatörünüzü bir ters vekil (Caddy, nginx) arkasında TLS ile yayınlayın. Yalnızca `127.0.0.1` üzerinde `http` kabul edilir.
- **Pickle yok.** Ağdan yalnızca [safetensors](/adaptor-bicimi/) kabul edin; bu biçim kod çalıştıramaz. `torch.load` ile gelen veriyi açmayın.
- **Gövdeyi sınırlayın.** `/sonuc` için üst sınır koyun (referans: 300 MB) ve belleğe tamamını okumadan önce `Content-Length` denetleyin.
- **Kişisel veri toplamayın.** İşçi kimliği gönüllünün seçtiği takma addır. IP'leri günlüğe yazmayın ya da kısa tutun.

## Anahtarlar

- Portal API anahtarını (`mdl_…`) ortam değişkeninde ya da gizli yöneticisinde saklayın; depoya koymayın.
- Sızdığından şüphelenirseniz panelden iptal edip yenisini oluşturun.
- Koordinatörünüzün `X-Anahtar` değeri ayrı bir şeydir: yalnızca sizin işçilerinizle paylaştığınız anahtardır, portala verilmez.

## Zehirlenme ve kötü niyetli işçi

Protokol v1'de doğrulama **yapısaldır** (şekil, dtype, NaN/Inf) ve referans koordinatör ek olarak aykırı norm elemesi yapar. Bu, hatalı ya da basit kötü niyetli sonuçları yakalar ama **kararlı bir saldırgana karşı yetmez**:

- Tek paylaşılan anahtar Sybil saldırısını (çok sayıda sahte işçi) önlemez.
- Aynı görevi iki işçiye verip sonuçları karşılaştırmak (çift hesaplama) protokolde henüz yoktur ([yol haritası](/yol-haritasi/)).

Pratik öneriler: kapalı bir gruba başlayın, `--en-az` değerini ≥ 3 tutun, delta normlarını günlükten izleyin ve her turdan sonra değerlendirme yapın.

## Portal tarafı korumalar

- API anahtarları yalnızca SHA-256 özetiyle saklanır; hız sınırları ve başarısız deneme engeli vardır.
- Adres doğrulaması SSRF'ye karşı korunur: yalnızca https, 443/8443 portları, yalnızca genel IP'ler, yönlendirme yok, 1 KB sınır, 6 sn zaman aşımı.
- Görseller yüklenirken EXIF verisi silinir; profiller varsayılan olarak özeldir.

## Güvenlik açığı bildirmek

Bir açık bulursanız lütfen herkese açık issue **açmayın**. [info@modelen.tr](mailto:info@modelen.tr) adresine ayrıntıyla yazın; en kısa sürede dönüş yapmaya çalışırız.
