# Modelen · Topluluk profili ve yayın öncesi notlar

Durum: şirket kurulmuyor. Ad **Modelen Alternatif Eğitim Topluluğu** (kullanıcı kararı, 2026-11-07). Aşağıdaki bilgiler kullanıcı beyanlarına dayanır; hukuki tavsiye değildir, avukat doğrulaması gerekir.

## Kimlik

| Alan | Değer | Kaynak |
|---|---|---|
| Ad | Modelen Alternatif Eğitim Topluluğu | kullanıcı beyanı |
| Marka / kısa ad | Modelen | kullanıcı beyanı |
| Alan adı | modelen.tr | kullanıcı beyanı |
| İletişim e-postası | iletisim@modelen.tr (varsayım, posta kutusu açılacak) | benim varsayımım |

## Karar özeti

- Kitle: Türkçe kullanan geliştiriciler ve kurumlar; ürün biçimi API ve yerel çalışan model.
- Farklılaştırıcı: topluluk sahipliği, şeffaf katkı kaydı. Başlangıçta para/kripto yok.
- Lisans: kod Apache-2.0, model Apache-2.0 (eğitim verisi lisansı hukuki incelemeye tabi).
- Site: Türkçe + İngilizce, çok sayfalı, statik, çerezsiz (`site/`).
- Kişi adı kullanılmaz; yalnızca iletişim e-postası.

## Yayın öncesi kontrol

- Alan adı, barındırma ve e-posta kutusu belirlenir; `site/build.py` içindeki `PLACEHOLDERS` sözlüğü doldurulur.
- Avukat incelemesinden sonra `DRAFT = False` yapılır ve site yeniden derlenir.
- Barındırma sağlayıcısı seçilince `[BARINDIRMA SAĞLAYICISI]` alanı doldurulur; gizlilik ve aydınlatma metinleri sağlayıcıya göre güncellenir.
- Alan adı, DNS, TLS (HTTPS) ve e-posta kutuları kullanıcıdadır; bunlar açılmadı ve yayına alınmadı.
- Üçüncü taraf betik, yazı tipi ya da analiz aracı **eklenmez**; eklenirse çerez ve gizlilik metinleri değişmek zorunda kalır.

## Açık kalanlar

- Topluluğun hukuki statüsü (dernek, vakıf ya da tüzel kişiliksiz yapı) ve buna bağlı yasal metin düzeni avukatla netleştirilecek.
- Barındırma sağlayıcısı.
- Yetkili mahkeme ve icra daireleri.
