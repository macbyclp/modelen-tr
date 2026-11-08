---
baslik: Modelen dokümantasyonu
bolum: Başlarken
sira: 1
ozet: Modelen'e koordinatör olarak katılmak, kendi eğitim sisteminizi bağlamak ve Portal API'sini kullanmak için rehber.
---

# Modelen dokümantasyonu

**Modelen**, açık dil modellerini gönüllülerin boştaki GPU'larıyla birlikte eğitmeyi hedefleyen bir topluluk girişimidir. Bu site; **koordinatör** olmak, **kendi eğitim sisteminizi** Modelen'e bağlamak ve **Portal API**'sini kullanmak isteyenler içindir.

:::uyari
**Dürüst durum:** Modelen araştırma aşamasındadır. Şu an tek bir taban model ve tek bir adaptör biçimi desteklenir (Qwen3-0.6B-Base + LoRA r=16). Bu dokümantasyon *bugün gerçekten çalışan* şeyi anlatır; planlananlar [yol haritasında](/yol-haritasi/) ayrıca ve açıkça "planlanan" diye işaretlidir.
:::

## Büyük resim

Eğitim şöyle işler: bir **koordinatör**, küçük bir **LoRA adaptörünü** (~40 MB) tutar ve **tur** tur ilerletir. Gönüllünün bilgisayarındaki uygulama (**işçi**) koordinatörden görev ve adaptörü alır, kendi verisiyle birkaç yüz adım eğitir, sonucu geri yollar. Koordinatör sonuçları ortalar ve yeni adaptörü yayınlar. Taban model ve eğitim verisi gönüllünün bilgisayarında kalır; ağdan yalnızca adaptör geçer.

![Modelen büyük resim: işçi, koordinatör ve portal arasındaki akış](/assets/buyuk-resim.svg)

## Modelen ne tür bir eğitim yapar?

Modelen bir **ince ayar (fine-tuning)** sistemidir. Taban modeli sıfırdan eğitmiyoruz; açık bir modelin (şimdilik Qwen3-0.6B-Base) üzerine **LoRA** denen küçük bir adaptör eğitiyoruz. LoRA, ince ayarın *parametre-verimli* (PEFT) yöntemidir: taban ağırlıklar donuk kalır, yalnızca yaklaşık 10 milyon parametrelik adaptör öğrenilir. Ağdan yalnızca bu 40 MB geçer ve 8 GB'lık bir gönüllü kartı yeter. Dokümantasyonda LoRA'nın sık geçmesinin nedeni budur: Modelen'de "ince ayar" demek, LoRA adaptörünü dağıtık olarak eğitmek demektir.

| Soru | Cevap |
|---|---|
| LoRA ile ince ayar | **Evet.** Protokol v1'in sabit biçimi |
| Tam ağırlık ince ayarı (tüm parametreler) | Hayır (v1'de desteklenmez) |
| Sıfırdan model eğitimi | Hayır |
| Hangi veriyle eğitilir? | **Koordinatörün seçimi.** Modelen veri sağlamaz ve seçmez |
| Eğitim türü | Görevdeki isteğe bağlı `mod` alanı: `cpt` (ham metinde devam eden ön eğitim, varsayılan) ya da `sft` (talimat ince ayarı). İkisi de aynı adaptör biçimini kullanır; [protokole](/protokol/) bakın |

:::not
Hangi veriyle ve hangi modda eğiteceğiniz, koordinatör olarak sizin kararınızdır. Verinin lisansı ve kaynağı da sizin sorumluluğunuzdadır.
:::

Üç parça birlikte çalışır:

| Parça | Ne yapar | Nerede |
|---|---|---|
| **Gönüllü uygulaması** | GPU'yu bir koordinatöre adar, yerelde eğitir | Masaüstü uygulaması (Rust) |
| **Koordinatör** | Turları yönetir, sonuçları doğrular ve ortalar | Sizin sunucunuz (referans uygulama: `istemci/koordinator.py`) |
| **Portal** | Kayıt, başvuru, onay, herkese açık dizin, API | `modelen.tr` |

## Neye başlamalı?

| Amacınız | Sayfa |
|---|---|
| Koordinatör olmak istiyorum | [Hızlı başlangıç](/hizli-baslangic/) → [Koordinatör olmak](/koordinator-olmak/) |
| Kendi eğitim sistemimi bağlayacağım | [Entegrasyon seçenekleri](/entegrasyon/) → [Koordinatör protokolü](/protokol/) |
| Protokole uyduğumu denetlemek istiyorum | [Uyum testi](/uyum-testi/) |
| Programdan başvuru/nabız yönetmek istiyorum | [Portal API](/api/) |
| Güvenlik gereksinimleri | [Güvenlik](/guvenlik/) |
| Terimler | [Kavramlar](/kavramlar/) |

## Kod ve kaynaklar

Her şey açık kaynaktır (Apache-2.0): <https://github.com/macbyclp/modelen-tr>. Bu dokümantasyondaki tüm örnek kodlar depodaki testlerle denetlenir: örnek koordinatör ve Python API istemcisi `istemci/ornekler/` altındadır.
