---
baslik: Sık sorulan sorular
bolum: Kaynaklar
sira: 1
ozet: Koordinatörlük, protokol, API ve uyum testi hakkında kısa cevaplar.
---

# Sık sorulan sorular

## Koordinatör olmak için ne gerekir?
Bir HTTPS adresi, protokol v1'i uygulayan bir servis ([referans](/referans-koordinator/) veya [kendi yazdığınız](/minimal-koordinator/)) ve portalda hesap. GPU gerekmez; GPU işçilerdedir.

## Kendi eğitim sistemimi (PyTorch dışı, başka dilde) bağlayabilir miyim?
Evet. Koordinatör yalnızca HTTP + safetensors konuşur. Adaptör biçimine ([392 tensör, F32](/adaptor-bicimi/)) uyduğunuz ve [uyum testini](/uyum-testi/) geçtiğiniz sürece iç mimariniz size kalmış.

## Farklı bir taban model kullanabilir miyim?
Protokol v1 yalnızca `Qwen/Qwen3-0.6B-Base` + belirtilen LoRA ayarını destekler. Başka model için manifest gerekir; bu planlı bir iştir ([yol haritası](/yol-haritasi/)).

## Başvurum ne zaman onaylanır?
Başvurular yönetici tarafından elle incelenir. Durumu panelde ya da `GET /api/v1/koordinator` ile görürsünüz; sonuç e-postayla da bildirilir.

## Onaylı profilimi güncelledim ama değişiklik görünmüyor.
Onaylı profildeki değişiklikler `taslak` olarak kaydedilir (API `202` döner) ve yönetici onayından sonra yayına girer.

## "Çevrimiçi" rozeti neden görünmüyor?
Onaylı olmalı ve en geç 15 dakikada bir [nabız](/nabiz/) göndermelisiniz.

## Adres doğrulaması neden başarısız oluyor?
En sık nedenler: dosya `https://adres/.well-known/modelen-dogrulama.txt` yolunda yok, içerik tam olarak beklenen tek satır değil, adres yönlendirme yapıyor (yönlendirmeler izlenmez) ya da port 443/8443 dışında. Ayrıntı: [Adres doğrulama](/adres-dogrulama/).

## API anahtarımı kaybettim.
Geri getirilemez. Panelden iptal edip yenisini oluşturun.

## `429` alıyorum.
[Hız sınırlarına](/api/#hiz-sinirlari) takıldınız. `Retry-After` kadar bekleyin; nabızı dakikada 6'dan sık göndermeyin.

## Uyum testi hangi hataları yakalamaz?
Birleştirmenin matematiksel doğruluğunu, performansı ve güvenliği (zehirlenme direnci) denetlemez; yalnızca sözleşmeye uyumu denetler.

## Kod açık mı, lisans nedir?
Evet; depo: [github.com/macbyclp/modelen-tr](https://github.com/macbyclp/modelen-tr).
