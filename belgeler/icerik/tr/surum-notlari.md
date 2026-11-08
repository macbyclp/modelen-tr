---
baslik: Sürüm notları
bolum: Kaynaklar
sira: 2
ozet: Protokol ve Portal API sürümleri; geriye uyumluluk ilkeleri.
---

# Sürüm notları

Tam geçmiş için [GitHub sürümleri](https://github.com/macbyclp/modelen-tr/releases).

## Yayınlanmamış (v0.5.0 sonrası)

- **Veri dağıtımı:** koordinatör belirteçlenmiş eğitim verisini dilimleyip kendisi sunabilir (`--veri`, `GET /veri`); işçi SHA-256'yı doğrulayıp önbelleğe alır. Artık yerel veri dosyası gerekmez. Protokolde isteğe bağlı `veri_sha256` / `veri_belirtec` alanları.
- **Eğitim modu:** görevde isteğe bağlı `mod` alanı (`cpt` / `sft`).
- **Referans koordinatör sertleştirme:** durum ve dış adım momentumu her tur diske yazılır, yeniden başlatınca geri yüklenir; işçi adı doğrulama (`400`); IP başına hız sınırı (`429`); işçi sayısı sınırı (`503`); bağlantı zaman aşımı; virgülle birden çok anahtar; ters vekil için `--vekil`. Koordinatör sürümü `0.5.0`.
- **İşçi:** işçi adını URL'ye kodlar.
- **Gönüllü kurulum betiği** `kur.ps1` ve imzalı sürüm hattı (CI + attestation): **ikisi de henüz uçtan uca denenmedi**.
- **Sunucu izleme** (portal, docs, sertifika, disk, bellek, yedek yaşı) ve portalın otomatik yeniden başlatılması.
- **docs:** ince ayar bölümü, SVG genel şema, gönüllü kurulum sayfası, daha çok İngilizce sayfa.

## v0.5.0 (geliştirici arayüzleri)

- **Portal API v1**: API anahtarları, koordinatör başvurusu/güncelleme, nabız, adres doğrulama, herkese açık dizin, OpenAPI şeması.
- **`GET /bilgi`** (koordinatör protokolüne isteğe bağlı ekleme): keşif ve uyum denetimi için.
- **Uyum testi** (`istemci/uyum_testi.py`) ve **örnek koordinatör** (`istemci/ornekler/`).
- **Bu dokümantasyon sitesi** (docs.modelen.tr).

## v0.4.0

Referans koordinatör ve gönüllü uygulamasının uçtan uca turu; topluluk soruları (`/soru`).

## Geriye uyumluluk ilkesi

- **Protokol v1**: mevcut uç noktalar ve alanlar değişmez. Yeni isteğe bağlı alanlar eklenebilir; istemciler bilmediği alanları yok saymalıdır.
- **Portal API v1**: aynı ilke. Kırıcı değişiklik `/api/v2` altında gelir.
