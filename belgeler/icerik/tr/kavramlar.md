---
baslik: Kavramlar
bolum: Başlarken
sira: 3
ozet: Modelen'de kullanılan terimler: koordinatör, işçi, tur, adaptör, LoRA, DiLoCo ve diğerleri.
---

# Kavramlar

| Terim | Anlamı |
|---|---|
| **Gönüllü** | GPU'sunu eğitime veren kişi. Masaüstü uygulamasını çalıştırır; takma adla katılır, kişisel veri girmez. |
| **İşçi** | Gönüllünün bilgisayarında çalışan eğitim süreci (`istemci/isci.py`, uygulama bunu alt süreç olarak başlatır). |
| **Koordinatör** | Turları yönetip adaptörü tutan sunucu. Görev dağıtır, işçilerin sonuçlarını doğrular ve ortalar. |
| **Portal** | `modelen.tr`: kayıt, koordinatör başvurusu ve onayı, herkese açık dizin, Portal API'si. |
| **Taban model** | Dondurulmuş, açık bir dil modeli. Şu an yalnızca **Qwen3-0.6B-Base** (Apache-2.0). Gönüllünün diskinde durur; ağdan geçmez. |
| **LoRA adaptörü** | Taban modelin yanına eklenen küçük, eğitilebilir ağırlıklar. Burada r=16, tüm doğrusal katmanlarda; 392 tensör, ~10,1 milyon parametre, **~40,4 MB** (float32). |
| **Tur** | Koordinatörün bir eğitim döngüsü: görev ver → işçiler eğitir → sonuçlar toplanır → ortalama + dış adım → yeni adaptör. |
| **H (iç adım)** | Bir işçinin turda yerelde yaptığı adım sayısı (`ic_adim`, varsayılan 20). Senkronizasyon her adımda değil her H adımda olur. |
| **DiLoCo** | Seyrek senkronizasyonla dağıtık eğitim yöntemi: işçiler yerelde çok adım atar, sonra koordinatörle birleşir. |
| **Dış adım** | Koordinatörün, işçi ortalamasına uyguladığı optimizer adımı (referans: Nesterov, lr 1,0, momentum 0,5). |
| **Veri dilimi (parça)** | Eğitim verisinin `n_parca` eşit parçasından biri; her işçiye bir parça atanır. |
| **Nabız** | Koordinatörün portala "çalışıyorum" bildirimi (bkz. [Nabız](/nabiz/)). |
| **Adres doğrulama** | Koordinatör adresinin sizin olduğunu kanıtlayan, `.well-known` dosyasına dayalı denetim. |
| **API anahtarı** | `mdl_...` ile başlayan, Portal API'sine erişim anahtarı. Panelden oluşturulur, bir kez gösterilir. |
| **Protokol v1** | Gönüllü uygulamasıyla koordinatör arasındaki HTTP sözleşmesi ([ayrıntı](/protokol/)). |
| **API v1** | Portalın koordinatörlere açtığı JSON arayüzü ([ayrıntı](/api/)). |

:::not
**Protokol** ile **API** farklı şeylerdir. *Protokol*, gönüllü uygulaması ile **sizin koordinatörünüz** arasındadır. *Portal API*'si ise **siz ile Modelen portalı** arasındadır (başvuru, nabız, dizin).
:::
