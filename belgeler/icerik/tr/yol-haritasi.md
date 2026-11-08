---
baslik: Yol haritası
bolum: Kaynaklar
sira: 3
ozet: Protokol v2 için planlanan işler. Burada yazanlar henüz uygulanmış değildir.
---

# Yol haritası

:::uyari
Bu sayfadakiler **planlanmıştır, uygulanmış değildir**. Tarih sözü verilmez.
:::

## Protokol v2 adayları

- **Zengin `/bilgi`**: taban model ve adaptör ayarının tam manifesti; farklı model/LoRA ayarlarını destekleme.
- **İmzalı veri manifestosu**: koordinatörün hangi veri dilimlerini ve lisansları kullandığının makine okunur, imzalı beyanı. (Düz dilim dağıtımı artık var: [`/veri`](/protokol/#get-veri-parca-i-istege-bagli).)
- **Gönüllü başına anahtar**: tek paylaşılan anahtar yerine işçi başına kimlik; Sybil direnci için ilk adım.
- **Çift hesaplama**: aynı görevin iki işçiye verilip sonuçların karşılaştırılması (zehirlenme direnci).
- **Eş zamansız / yavaş işçi toleransı**: farklı hızdaki GPU'lar için değişken adım sayısı.
- **Daha küçük aktarımlar**: gerçek ağ testinde adaptör indirmesi baskın çıktı (~1 MB/sn bağlantıda 40 MB ≈ 38 sn); sıkıştırma, düşük hassasiyet ya da delta aktarımı yardımcı olur.

## Portal API

- Webhook ile bildirimler (başvuru durumu).
- Koordinatörler için salt-okunur istatistik uç noktaları.

Önerileriniz için [GitHub](https://github.com/macbyclp/modelen-tr/issues) üzerinden issue açabilirsiniz.
