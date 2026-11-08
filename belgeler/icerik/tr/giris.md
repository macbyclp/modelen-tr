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

```text
 Gönüllü uygulaması (işçi)            Koordinatör (sizin sunucunuz, HTTPS)
        |  GET  /gorev, /agirlik  ------------>  |   adaptörü tutar, turları yönetir
        |  POST /sonuc            ------------>  |   sonuçları doğrular, ortalar
        v                                        ^
   LoRA eğitimi (yerel GPU)                      |  nabız, başvuru, adres doğrulama
                                                 |
                                       modelen.tr Portal API  (/api/v1)
                                       onaylı koordinatör dizini -> uygulamada görünür
```

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
