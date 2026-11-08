---
baslik: Sürüm notları
bolum: Kaynaklar
sira: 2
ozet: Protokol ve Portal API sürümleri; geriye uyumluluk ilkeleri.
---

# Sürüm notları

Tam geçmiş için [GitHub sürümleri](https://github.com/macbyclp/modelen-tr/releases).

## Bu sürüm (geliştirici arayüzleri)

- **Portal API v1**: API anahtarları, koordinatör başvurusu/güncelleme, nabız, adres doğrulama, herkese açık dizin, OpenAPI şeması.
- **`GET /bilgi`** (koordinatör protokolüne isteğe bağlı ekleme): keşif ve uyum denetimi için.
- **Uyum testi** (`istemci/uyum_testi.py`) ve **örnek koordinatör** (`istemci/ornekler/`).
- **Bu dokümantasyon sitesi** (docs.modelen.tr).

## v0.4.0

Referans koordinatör ve gönüllü uygulamasının uçtan uca turu; topluluk soruları (`/soru`).

## Geriye uyumluluk ilkesi

- **Protokol v1**: mevcut uç noktalar ve alanlar değişmez. Yeni isteğe bağlı alanlar eklenebilir; istemciler bilmediği alanları yok saymalıdır.
- **Portal API v1**: aynı ilke. Kırıcı değişiklik `/api/v2` altında gelir.
