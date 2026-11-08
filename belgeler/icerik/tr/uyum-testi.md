---
baslik: Uyum testi
bolum: Kendi sistemini bağlamak
sira: 6
ozet: Koordinatörünüzün protokol v1'e uyup uymadığını denetleyen araç: kullanım, maddeler, çıktı ve CI örneği.
---

# Uyum testi

`istemci/uyum_testi.py`, koordinatörünüzün [protokol v1](/protokol/)'e uyup uymadığını denetler. Yalnızca Python standart kütüphanesine dayanır (PyTorch gerekmez); herhangi bir dilde yazılmış koordinatörü uzaktan test eder.

```bash
python istemci/uyum_testi.py --url https://koordinator.ornek.org
python istemci/uyum_testi.py --url http://127.0.0.1:8750 --anahtar GIZLI --json
```

| Bayrak | Anlamı |
|---|---|
| `--url` | Koordinatör adresi (zorunlu) |
| `--anahtar` | Koordinatör `X-Anahtar` istiyorsa |
| `--isci` | Deneme işçi adı (varsayılan `uyum-testi`) |
| `--json` | Makine okunur çıktı |

**Çıkış kodu:** tüm zorunlu maddeler geçerse `0`, bir `FAIL` varsa `1`.

:::uyari
Test, koordinatörünüzde `uyum-testi` adlı bir işçi kaydı oluşturur (`/gorev` çağrısı) ve `/sonuc`'a **bilerek geçersiz** veri gönderir (reddedilmesi beklenir). Canlı bir eğitimin ortasında çalıştırırsanız deneme işçisi veri dilimi atamasını etkileyebilir; ayrı bir deneme örneğinde çalıştırmanız önerilir.
:::

## Örnek çıktı

```text
  tamam  TLS                        https
  tamam  /bilgi                     protokol 1, taban_model=Qwen/Qwen3-0.6B-Base
  tamam  /durum                     tur 0/6 (4 ms)
  tamam  /gorev (işçi adı yok)      HTTP 400
  tamam  /gorev                     tur 0, parça 0/4, 20 adım
  tamam  /agirlik sha256            başlık gövdeyle eşleşiyor
  tamam  /agirlik X-Tur             0
  tamam  /agirlik safetensors       392 tensör, dtype ['F32'], LoRA: 392 (40.4 MB, 0.3 sn)
  tamam  /sonuc (bozuk veri)        HTTP 400
  tamam  /sonuc (eski/yanlış tur)   HTTP 409
  tamam  /sonuc (boş gövde)         HTTP 413
  tamam  bilinmeyen yol             HTTP 404

12 geçti, 0 uyarı, 0 hata -> UYUMLU
```

## Maddeler

| Madde | Durum | Ne denetlenir |
|---|---|---|
| **TLS** | uyarı | Yerel olmayan `http://` adresi uyarı verir |
| **/bilgi** | uyarı | `protokol: "1"` içeren JSON; yoksa uyarı |
| **/durum** | zorunlu | `tur`, `toplam_tur` (tamsayı), `bekleyen_sonuc` (liste), `isciler` (nesne), `trafik` (nesne) |
| **/gorev (işçi adı yok)** | uyarı | `isci` yoksa `400` |
| **/gorev** | zorunlu | `bekle`/`bitti` ya da tüm görev alanları (tipleriyle) + 64 haneli `agirlik_sha256` |
| **/agirlik sha256** | zorunlu | `X-Sha256` başlığı gövdenin gerçek özetiyle aynı |
| **/agirlik X-Tur** | zorunlu | Tamsayı |
| **görev-ağırlık** | zorunlu | Aynı turda `gorev.agirlik_sha256` indirilen ağırlığın özetiyle aynı |
| **/agirlik safetensors** | zorunlu | Geçerli safetensors: başlık JSON, aralıklar dosya içinde, pickle değil |
| **/agirlik dtype** | uyarı | `F32` dışı tür uyarı verir |
| **/sonuc (bozuk veri)** | zorunlu | `400` ya da `422` (asla `200`/`500`) |
| **/sonuc (eski/yanlış tur)** | zorunlu | `400`, `409` ya da `422` |
| **/sonuc (boş gövde)** | zorunlu | `400`, `413` ya da `422` |
| **bilinmeyen yol** | uyarı | `404` |
| **kimlik** | zorunlu | `401` dönerse `--anahtar` gerekir |
| **bağlantı** | zorunlu | Adrese bağlanılabilmeli (sertifika dahil) |

## CI'da kullanmak

GitHub Actions ile her değişiklikte denetleyin:

```yaml
name: Modelen uyum
on: [push]
jobs:
  uyum:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4          # Modelen deposundan uyum_testi.py'yi alın
        with: { repository: macbyclp/modelen-tr }
      - name: Koordinatörünüzü başlatın
        run: ./sizin-kodunuz --port 8750 &
      - name: Uyum testi
        run: python istemci/uyum_testi.py --url http://127.0.0.1:8750 --json
```

## Araç kendisi nasıl test edilir?

`istemci/test_uyum.py`, uyumlu ve bilerek bozulmuş sahte koordinatörlerle aracı sınar (yanlış `X-Sha256`, `500` dönen `/sonuc`, geçersizi `200` ile kabul eden `/sonuc`, eksik `/durum` alanı, pickle benzeri ağırlık…) ve mevcutsa gerçek referans koordinatörün geçtiğini doğrular.
