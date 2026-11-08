---
baslik: Koordinatör olmak
bolum: Koordinatör olmak
sira: 1
ozet: Başvuru süreci, alanlar, onay durumları, düzenleme akışı ve listelenme koşulları.
---

# Koordinatör olmak

Koordinatör, gönüllülerin GPU'larını kendi eğitim projesi için kullanan, yöneticilerin onayladığı kişi ya da ekiptir. Onaylanınca sayfanız herkese açık dizinde yayınlanır.

## Süreç

1. **Kayıt ve e-posta doğrulama.** Hesap açın, doğrulama bağlantısına tıklayın.
2. **Başvuru.** Panelden ([modelen.tr/panel](https://modelen.tr/panel)) ya da [API](/api/) ile.
3. **İnceleme.** Yöneticiler başvuruyu kendi panelinde görür; onaylar, reddeder, askıya alır ya da not düşer. Her karar size e-postayla bildirilir.
4. **Yayın.** Onaylanınca sayfanız `modelen.tr/koordinator/<ad>` adresinde ve [Koordinatörler](https://modelen.tr/koordinatorler) listesinde görünür.
5. **Gönüllüler seçer.** Adresiniz (https) varsa masaüstü uygulamasındaki listeye girersiniz; gönüllü sizi seçip GPU'sunu size adar.

## Başvuru alanları

| Alan | Zorunlu | Kural |
|---|---|---|
| `ad` | evet | 2-60 karakter. Sayfa adresi (`slug`) bundan üretilir ve sonradan değişmez. |
| `kisa` | evet | 10-200 karakter; listelerde görünür. |
| `ayrinti` | hayır | En çok 5000 karakter, düz metin; herkese açık sayfada "Neler yapıyor?" bölümünde görünür. Ne yaptığınızı, hangi veri ve lisansla, GPU'ları nasıl kullanacağınızı yazın. |
| `baglanti` | hayır | Web sitesi ya da depo (`http://` veya `https://`). |
| `adres` | hayır | Koordinatör adresi; **https** olmalı. Boş bırakılabilir ama adres yoksa gönüllüler GPU adayamaz. |
| `hf` | hayır | Hugging Face bağlantısı (`huggingface.co` ya da `hf.co`). |
| `iletisim` | hayır | Yalnızca yöneticilerin gördüğü e-posta; boşsa hesap e-postanız kullanılır. |

Görseller (en çok 4, PNG/JPEG/WebP, her biri ≤ 2 MB) şimdilik yalnızca **panelden** yüklenir; EXIF/konum bilgisi otomatik silinir.

## Durumlar

| Durum | Anlamı |
|---|---|
| `beklemede` | İncelemede. Alanları serbestçe değiştirebilirsiniz. |
| `onaylandi` | Yayında. Değişiklikler [taslak](#onayli-profili-duzenlemek) olarak onaya düşer. |
| `reddedildi` | Yönetici notunu okuyup düzeltin ve yeniden gönderin; yeniden `beklemede` olur. |
| `askida` | Yöneticiler sayfanızı yayından kaldırdı. Değişiklik yapılamaz. |

## Onaylı profili düzenlemek

Onaylı bir profilde yaptığınız değişiklik **hemen yayına girmez**: taslak olarak kaydedilir ve yönetici onaylayana kadar yayındaki sayfa değişmez. Onaylanınca uygulanır, reddedilirse yayındaki sayfa olduğu gibi kalır. Yeni görseller de onaya kadar gizlidir. API'de bu durum `202` ve `taslak_var: true` ile görülür.

Adres değişirse **adres doğrulaması sıfırlanır** ve yeniden doğrulamanız gerekir ([Adres doğrulama](/adres-dogrulama/)).

## E-posta bildirimleri

`info@modelen.tr` adresinden şu durumlarda e-posta alırsınız: başvuru alındı, onaylandı, reddedildi (notuyla), askıya alındı, düzenleme onaylandı/onaylanmadı. Reklam ya da pazarlama e-postası gönderilmez.

## Koşullar

Koordinatör olarak şunları kabul etmiş olursunuz ([tam metin](https://modelen.tr/koordinator-ol.html)):

- Gönüllünün bilgisayarında yalnızca Modelen'in yayımladığı eğitim betiği çalışır; **keyfi kod gönderemezsiniz**.
- Adresiniz https ile erişilebilir olmalı.
- Neyin, hangi veriyle ve hangi lisansla eğitildiğini ve çıktıların nasıl kullanılacağını açıkça yazarsınız.
- Gönüllülerin kişisel verisini toplamazsınız; takma ad dışında bilgi istemezsiniz.
- Koşullara aykırılıkta yöneticiler sizi listeden çıkarabilir.

:::uyari
Koordinatör yazılımı hâlâ prototip: kimlik doğrulama ve zehirlenme koruması sınırlıdır ([Güvenlik](/guvenlik/)). Bu yüzden liste yalnızca yöneticilerin elle onayladığı koordinatörlerden oluşur.
:::
