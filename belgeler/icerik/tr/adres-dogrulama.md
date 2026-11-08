---
baslik: Adres doğrulama
bolum: Koordinatör olmak
sira: 2
ozet: Koordinatör adresinizin sizin olduğunu .well-known dosyasıyla kanıtlama: adımlar, sunucu örnekleri ve sorun giderme.
---

# Adres doğrulama

Dizinde herkesin yazabildiği bir adres göstermek, başkasının sunucusunu kendinizinki gibi sunmanıza izin verirdi. Bu yüzden adresin gerçekten sizin kontrolünüzde olduğunu kanıtlarsınız: portalın verdiği değeri adresinizde yayınlarsınız, portal de gidip okur.

Doğrulanmış adreslerde herkese açık sayfada ve API'de `adres_dogrulandi: true` görünür. Adresi değiştirirseniz doğrulama kendiliğinden **sıfırlanır**.

## Adımlar

**1. Doğrulamayı başlatın.** Kayıtlı bir `https://` adresiniz olmalı.

```bash
curl -s -X POST https://modelen.tr/api/v1/koordinator/adres-dogrula \
  -H "Authorization: Bearer $MODELEN_API_ANAHTARI"
```

```json
{
  "adres": "https://koordinator.ornek.org",
  "dosya": "https://koordinator.ornek.org/.well-known/modelen-dogrulama.txt",
  "icerik": "modelen-dogrulama-AbC123..."
}
```

**2. Dosyayı yayınlayın.** `dosya` adresinde, gövdesi tam olarak `icerik` değeri olan bir metin dosyası sunun (başındaki/sonundaki boşluk ve satır sonu önemsizdir).

Caddy ile:

```text
koordinator.ornek.org {
    handle /.well-known/modelen-dogrulama.txt {
        respond "modelen-dogrulama-AbC123..." 200
    }
    reverse_proxy 127.0.0.1:8750
}
```

nginx ile:

```text
location = /.well-known/modelen-dogrulama.txt {
    default_type text/plain;
    return 200 "modelen-dogrulama-AbC123...";
}
```

**3. Kontrol ettirin.**

```bash
curl -s -X POST https://modelen.tr/api/v1/koordinator/adres-dogrula/kontrol \
  -H "Authorization: Bearer $MODELEN_API_ANAHTARI"
# {"adres_dogrulandi":true}
```

Doğrulama sonrası dosyayı kaldırabilirsiniz; ama adresi değiştirirseniz yeniden doğrulamanız gerekir.

## Portal adresinizi nasıl okur?

Portal sunucusu adresinize istek atar. Bunun kötüye kullanılamaması için sıkı kurallar vardır:

- Yalnızca **https**; geçerli (alan adına uygun) bir **TLS sertifikası** gerekir.
- Yalnızca **443** ve **8443** portları.
- Adres bir **alan adı** olmalı (IP adresi olamaz) ve **genel internete** çözülmeli. Özel/yerel ağ adresleri (`10.x`, `192.168.x`, `127.x`, `169.254.x` vb.) ve yerel adreslere de çözülen alan adları reddedilir.
- **Yönlendirme (redirect) izlenmez**; yanıt doğrudan `200` olmalı.
- En çok **1 KB** okunur, 6 sn zaman aşımı.

## Sorun giderme

| `kod` | Anlamı | Ne yapmalı |
|---|---|---|
| `baslatilmadi` | Önce doğrulamayı başlatmadınız | Adım 1'i çağırın |
| `adres_yok` | Kayıtlı https adresiniz yok | `PATCH /koordinator` ile `adres` ekleyin |
| `okunamadi` | Dosya okunamadı (404, sertifika hatası, zaman aşımı, özel IP...) | Mesajı okuyun; dosyanın `curl -i` ile https üzerinden doğrudan 200 döndüğünü doğrulayın |
| `icerik_uyusmuyor` | Dosya bulundu ama içerik farklı | Değeri birebir kopyalayın; yeni başlattıysanız eski değeri değil güncelini kullanın |
| `hiz_siniri` | 10 dakikada 10 kontrolden fazla | Biraz bekleyin |

:::ipucu
Kendi kendinize denemek için: `curl -sS -i https://adresiniz/.well-known/modelen-dogrulama.txt` komutu `HTTP/… 200` ve beklenen metni göstermelidir. Sertifika hatası veriyorsa portal da okuyamaz.
:::
