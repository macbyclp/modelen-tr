---
baslik: Hızlı başlangıç
bolum: Başlarken
sira: 2
ozet: Hesap açmaktan koordinatörünüzü portala bağlamaya kadar adım adım hızlı başlangıç.
---

# Hızlı başlangıç

Bu sayfa, sıfırdan **onaylı bir koordinatöre** giden en kısa yolu gösterir. Her adımın ayrıntısı ilgili sayfada.

:::not
Gönüllülerin GPU'sunu kullanabilmek için üç şey gerekir: portalda **onaylı bir başvuru**, herkese açık bir **https adresi** ve protokole uyan bir **koordinatör**. Adresi olmayan onaylı koordinatörler sitede görünür ama gönüllü uygulamasındaki listede görünmez.
:::

## 1. Hesap açın ve e-postanızı doğrulayın

1. <https://modelen.tr/kayit> adresinden kayıt olun.
2. Gelen e-postadaki bağlantıya tıklayarak adresinizi doğrulayın. Doğrulanmamış hesap başvuru yapamaz ve API anahtarı oluşturamaz.

## 2. API anahtarı oluşturun

Panelde **API anahtarları** sayfasına gidin (<https://modelen.tr/panel/api>) ve bir anahtar oluşturun. Anahtar `mdl_` ile başlar ve **yalnızca bir kez** gösterilir; parola gibi saklayın.

```bash
export MODELEN_API_ANAHTARI=mdl_xxxxxxxxxxxxxxxxxxxxxxxx
curl -s https://modelen.tr/api/v1/ben -H "Authorization: Bearer $MODELEN_API_ANAHTARI"
```

## 3. Başvurunuzu oluşturun

Panelden ya da API ile. API ile:

```bash
curl -s -X POST https://modelen.tr/api/v1/koordinator \
  -H "Authorization: Bearer $MODELEN_API_ANAHTARI" -H "Content-Type: application/json" \
  -d '{"ad": "Örnek Lab", "kisa": "Türkçe LoRA denemeleri için koordinatör", "adres": "https://koordinator.ornek.org"}'
```

Başvuru yönetici incelemesine düşer; sonuç e-postayla bildirilir. Adres alanını sonradan da ekleyebilirsiniz (`PATCH /koordinator`).

## 4. Koordinatörünüzü çalıştırın

İki seçeneğiniz var (ayrıntı: [Entegrasyon seçenekleri](/entegrasyon/)):

**A. Referans koordinatör** (gerçek eğitim; PyTorch ve taban model gerekir):

```bash
python istemci/baslat.py                       # başlangıç adaptörünü üretir
python istemci/koordinator.py --baslangic istemci/calisma/tur-0.safetensors \
    --tur 20 --en-az 2 --host 127.0.0.1 --port 8750
```

**B. Kendi koordinatörünüz.** Protokol v1'i uygulayan herhangi bir HTTP sunucusu olabilir. En küçük çalışan örnek (yalnızca standart kütüphane) `istemci/ornekler/minimal_koordinator.py` dosyasıdır; ayrıntı: [Kendi koordinatörünüzü yazın](/minimal-koordinator/).

## 5. HTTPS ile yayınlayın

Koordinatörü doğrudan internete açmayın; ters vekil arkasında HTTPS ile yayınlayın. Caddy ile tek blok yeter (sertifikayı kendisi alır):

```text
koordinator.ornek.org {
    reverse_proxy 127.0.0.1:8750
}
```

## 6. Uyum testini çalıştırın

```bash
python istemci/uyum_testi.py --url https://koordinator.ornek.org
```

Tüm zorunlu maddeler geçmeli ("UYUMLU"). Ayrıntı: [Uyum testi](/uyum-testi/).

## 7. Adresinizi doğrulayın

Adresin gerçekten sizin olduğunu kanıtlayın (başkasının sunucusunu kendinizinki gibi gösterememeniz için):

```bash
curl -s -X POST https://modelen.tr/api/v1/koordinator/adres-dogrula -H "Authorization: Bearer $MODELEN_API_ANAHTARI"
# {"adres":"...","dosya":"https://koordinator.ornek.org/.well-known/modelen-dogrulama.txt","icerik":"modelen-dogrulama-..."}
```

Dönen `icerik` değerini `dosya` adresinde yayınlayın, sonra kontrol edin:

```bash
curl -s -X POST https://modelen.tr/api/v1/koordinator/adres-dogrula/kontrol -H "Authorization: Bearer $MODELEN_API_ANAHTARI"
```

Ayrıntı ve sorun giderme: [Adres doğrulama](/adres-dogrulama/).

## 8. Nabız gönderin

Koordinatörünüz çalışırken portala düzenli olarak "çalışıyorum" deyin; herkese açık sayfanızda **çevrimiçi** görünürsünüz.

```bash
python istemci/ornekler/modelen_api.py nabiz-dongusu --koordinator https://koordinator.ornek.org --aralik 300
```

Ayrıntı: [Nabız](/nabiz/).

## Sonra

Başvurunuz onaylanınca sayfanız [Koordinatörler](https://modelen.tr/koordinatorler) listesinde yayınlanır. Adresiniz varsa gönüllüler masaüstü uygulamasından sizi seçip GPU'larını size adayabilir.
