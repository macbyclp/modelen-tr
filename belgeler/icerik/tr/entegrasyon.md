---
baslik: Entegrasyon seçenekleri
bolum: Kendi sistemini bağlamak
sira: 1
ozet: Kendi eğitim sisteminizi Modelen'e bağlamanın bugünkü yolları, neleri özelleştirebileceğiniz ve sınırlar.
---

# Entegrasyon seçenekleri

"Kendi eğitim sistemimi Modelen'e nasıl bağlarım?" sorusunun bugünkü dürüst cevabı: **koordinatör tarafını** istediğiniz gibi yazabilirsiniz, ama gönüllünün bilgisayarında çalışan **eğitim betiği ve model Modelen'in sabit tanımıdır**. Bunun nedeni güvenliktir: gönüllü, sizin kodunuzu çalıştırmaz.

## Üç yol

### A. Referans koordinatörü kullanın (önerilen başlangıç)

`istemci/koordinator.py` hazır çalışır: görev dağıtır, sonuçları doğrular, aykırı sonuçları eler, Nesterov dış adımını uygular, her turu diske yazar. Yalnızca ayarlarını (tur sayısı, H, öğrenme oranları…) seçersiniz. Bkz. [Referans koordinatör](/referans-koordinator/).

### B. Kendi koordinatörünüzü yazın

Protokol v1'i uygulayan herhangi bir HTTP servisi koordinatör olabilir: farklı dil, farklı birleştirme yöntemi, kendi veritabanınız, kendi kimlik doğrulamanız, kendi gözlemlenebilirlik altyapınız. Gönüllü uygulaması yalnızca protokolü bilir. Bkz. [Koordinatör protokolü](/protokol/), [Kendi koordinatörünüzü yazın](/minimal-koordinator/) ve doğrulamak için [Uyum testi](/uyum-testi/).

### C. Kendi model/veri/eğitim betiğiniz (planlanan, henüz yok)

Farklı taban model ve farklı adaptör biçimi için gerekenler: model **manifesti**, imzalı veri/model dağıtımı ve işçi tarafında sandbox. Bunlar [yol haritasında](/yol-haritasi/) *planlanan* maddelerdir; bugün uygulanmış değildir. (Aynı model ve biçimle **kendi verinizi** dağıtmak ise bugün mümkündür: aşağıdaki tabloya bakın.)

## Bugün neleri değiştirebilirsiniz?

| Konu | Serbest mi? | Not |
|---|---|---|
| Koordinatör yazılımı / dili / altyapısı | Evet | Protokol v1'e uyduğu sürece |
| Tur sayısı, H (`ic_adim`), `bs`, `seq`, `lr`, `tohum` | Evet | Görev yanıtıyla işçiye iletilir |
| Birleştirme yöntemi (ortalama, momentum, ağırlıklı, elemeli…) | Evet | Tamamen sizin tarafınızda |
| Aykırı/zehirli sonuç savunması | Evet | Sizin sorumluluğunuzda ([Güvenlik](/guvenlik/)) |
| Hangi işçinin hangi veri dilimini alacağı | Evet | `parca` / `n_parca` değerleriyle |
| Taban model | **Hayır** | Qwen3-0.6B-Base |
| Adaptör biçimi | **Hayır** | LoRA r=16, 7 hedef modül, float32, 392 tensör ([ayrıntı](/adaptor-bicimi/)) |
| Eğitim betiği (kayıp, optimizer, veri yükleme) | **Hayır** | `istemci/isci.py`; AdamW, kosinüs çizelgesi, klip 1,0 |
| Eğitim verisi | **Evet** | `--veri` ile belirteçlenmiş veriyi (safetensors) sunarsınız; koordinatör onu dilimleyip işçilere [`/veri`](/protokol/#get-veri-parca-i-istege-bagli) ile dağıtır. Belirteçleme **taban modelin** belirteçleyicisiyle yapılmalıdır. Verinin kaynağı ve lisansı sizin sorumluluğunuzdadır |
| Eğitim türü (`mod`) | **Evet** | `cpt` (ham metinde devam eden ön eğitim) ya da `sft` (talimat ince ayarı) |

:::uyari
Bu sınırlar yüzünden bugün "başka bir modeli Modelen'e bağlamak" mümkün değildir. Ama aynı model ve biçimle **kendi koordinatörünüzü, kendi gönüllü topluluğunuzla** çalıştırabilirsiniz; portalda listelenmek istemezseniz yalnızca adresinizi gönüllülere verebilirsiniz (uygulamada özel adres girilebilir).
:::

## Karar rehberi

- *"Sadece denemek ve gönüllülere açmak istiyorum"* → **A**.
- *"Kendi altyapıma/izlemeye/kimlik sistemime uydurmalıyım"* → **B**.
- *"Başka bir model eğitmek istiyorum"* → henüz **C** yok; [yol haritasına](/yol-haritasi/) bakın ve [GitHub'da](https://github.com/macbyclp/modelen-tr/issues) ihtiyacınızı yazın.
