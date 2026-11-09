# Modelen uygulaması (Rust, masaüstü)

Kullanıcı kararı (2026-11-07): VS Code istemiyorum; Rust ile tek bir uygulama olsun, kurulunca gönüllü GPU işini de kod yardımcısını da yapsın. Bu uygulama o yönde ilk sürümdür (`ide/` altındaki VS Code eklentisi bu yüzden artık **kullanılmıyor**; yalnızca sağlayıcı mantığının ilk prototipi olarak duruyor).

## Ne yapar

- **Kolay mod (açılış ekranı):** tek sayfa, büyük AÇIK/KAPALI düğmesi = gönüllü işçi. Açıkken nabız animasyonu, süre ve tamamlanan tur sayısı; hata olursa sade Türkçe mesaj. Adres yerel (127.0.0.1) ve orada koordinatör yoksa önce yerel test koordinatörünü (`--en-az 1`) kendisi açar. Sağ altta "Gelişmiş seçenekler", gelişmişte sağ üstte "Kolay mod". Son seçilen mod hatırlanır. Pencere simgesi ve en küçük boyut tanımlı.

- **Koordinatör seçimi (Kolay mod + Gelişmiş > Gönüllü):** küçük tablo (isim, adres, geliştirdiği); seçilen koordinatöre GPU adanır. Liste siteden (`modelen.tr/koordinatorler.json`, portal tarafından üretilir; yalnızca adresi olan onaylı koordinatörler) çekilir, yalnızca admin onaylı (`onayli: true`) ve https adresli kayıtlar gösterilir; son liste `%APPDATA%\Modelen\dizin.json` olarak önbelleğe alınır, "Yerel test" her zaman listede. Koordinatör olmak isteyenler sitede kayıt olup başvurur; yöneticiler başvuruları ve iletişim adreslerini `portal/` yönetici panelinde görüp onaylar (bkz. `portal/PORTAL.md`). Koordinatör adresi zorunlu değildir. Kolay mod dar (455×863), Gelişmiş geniş pencere açar.
- **Kod sekmesi:** klasör ağacı, metin editörü (Kaydet, Ctrl+S), sağda **Topluluğa sor** paneli: soru koordinatörün `/soru` ucuna gider (`istemci/calisma/sorular.jsonl`, okumak için `istemci/sorular.py`); açık dosya/seçim yalnızca kutu işaretlenirse eklenir.
- **Sağlayıcılar:** Modelen (yerel), Ollama, OpenAI uyumlu herhangi bir uç (OpenRouter, vLLM, llama.cpp…) ve Anthropic. Ayarlardan eklenip düzenlenir. Akışlı cevap, Dur düğmesi.
- **API anahtarları:** yalnızca Windows kimlik kasasında (`keyring`); ayar dosyasına, günlüğe ya da arayüz durumuna yazılmaz.
- **Gönüllü sekmesi:** GPU bilgisi (`nvidia-smi`), koordinatör adresi + takma ad, **Katkıya başla/durdur** (işçi alt süreci), koordinatör durumu (tur, işçi sayısı, trafik; 5 sn'de bir), işçi günlüğü.
- **Yerel model:** `sunucu/modelen_sunucu.py` alt sürecini başlatıp durdurur (adaptör seçilebilir); Kod sekmesindeki "Modelen (yerel)" ona bağlanır.

## Yapı

| Dosya | Görev |
|---|---|
| `src/saglayici.rs` | OpenAI uyumlu + Anthropic akışlı istemci (`ureq`, rustls), bağlam kurma, kod bloğu çıkarma, 7 test + 1 canlı test |
| `src/surec.rs` | Alt süreç yönetimi (konsol penceresiz, ilerleme çubukları dahil günlük), GPU, koordinatör durumu, dosya ağacı, 3 test |
| `src/ayar.rs` | `%APPDATA%\Modelen\ayarlar.json`, kimlik kasası |
| `src/main.rs` | `eframe`/`egui` arayüzü (kırmızı tema) |

Derleme: `cd uygulama && cargo build --release` → `target/release/modelen.exe` (yaklaşık 10 MB, bağımsız tek exe). Test: `cargo test`; yerel model sunucusu açıkken `cargo test canli -- --ignored --nocapture`.

## Doğrulananlar

- Derlendi (debug + release). **11 birim testi geçti**: sahte HTTP sunucularına karşı iki sağlayıcının akışı, başlıklar, hata gövdesi, anahtarsız istek, boş ayar, bozuk SSE, bağlam/kırpma/kod bloğu, süreç başlat-durdur, dosya ağacı, durum özeti.
- **Canlı:** Rust sağlayıcı katmanı çalışan yerel Modelen sunucusundan (Qwen3-0.6B + tur-3 adaptörü) 9 parça akışla cevap aldı.
- Uygulama açıldı; üç sekmeli arayüz ekranda görüldü (Türkçe karakterler, üç bölmeli Kod sekmesi). Çökme yok.

## Doğrulanmayanlar / dürüst eksikler

- **Arayüz etkileşimleri elle tıklanarak denenmedi** (dosya açma, gönder, katkıya başla, anahtar kasası). Bunlar kodla yazıldı ve altındaki mantık testli, ama düğmelerin gerçek davranışını gözle görmedim.
- **Kurulum:** `Modelen-Kurulum.exe` (kök dizindeki `kur.ps1`'i gömer) Python 3.12, PyTorch, taban model ve istemci betiklerini `%LOCALAPPDATA%\Modelen` altına kurar; uygulama bu düzeni kendiliğinden bulur. Eğitim ve yerel model hâlâ Python (`torch`) alt süreci olarak çalışır (Rust'a taşınmadı). Kurulum betikleri GitHub'ın temiz makinelerinde GPU'suz sınanır; GPU'lu uçtan uca kurulum ve imza henüz yok.
- Model kalitesi: 0.6B taban model sohbet asistanı değil (örnek: soruya devam cümlesi yazıyor).
- Ajan özellikleri (araç çağırma, çok dosyalı düzenleme, satır içi tamamlama), söz dizimi renklendirme, dosya oluşturma/silme, sekmeler: yok.
- Koordinatör bağlantısı düz HTTP; genel ağ için TLS + hesap + zehirleme önlemi gerekir (`istemci/ISTEMCI.md`).
- Yalnızca Windows'ta denendi (kimlik kasası özelliği Windows'a göre seçildi).
