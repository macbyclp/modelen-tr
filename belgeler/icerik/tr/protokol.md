---
baslik: Koordinatör protokolü v1
bolum: Kendi sistemini bağlamak
sira: 2
ozet: Gönüllü uygulaması ile koordinatör arasındaki HTTP sözleşmesi: uç noktalar, şemalar, hata kodları, tur yaşam döngüsü ve dış adım.
---

# Koordinatör protokolü v1

Bu sayfa, **gönüllü uygulaması (işçi) ile koordinatör arasındaki** sözleşmedir. Bir koordinatörün gönüllü uygulamasıyla çalışması için gereken her şey burada. Sözleşmeye uyup uymadığınızı [uyum testi](/uyum-testi/) ile denetleyebilirsiniz.

:::not
"**Zorunlu**" = olmazsa gönüllü uygulaması çalışmaz. "**Önerilir**" = çalışır ama uyum testi uyarı verir. "**İsteğe bağlı**" = uzantıdır.
:::

## Genel kurallar

- Aktarım **HTTP/1.1**, yanıtlar **UTF-8 JSON**; ağırlıklar **safetensors** (ikili). **Pickle yok**: ağdan gelen hiçbir veri kod olarak yorumlanmaz.
- Genel ağda **HTTPS zorunludur** (adaptörler ve görevler şifresiz akmamalı). Yalnızca `127.0.0.1` üzerinde `http` kabul edilir.
- İşçi kimliği, gönüllünün seçtiği **takma addır** (`isci`); kişisel veri içermemelidir. En çok 60 karakter öneririz.
- Koordinatör isteğe bağlı olarak **paylaşılan anahtar** isteyebilir: işçi her isteğe `X-Anahtar: <anahtar>` başlığı ekler; yanlışsa `401 {"hata":"yetkisiz"}`. `/bilgi` anahtarsız çağrılabilir.
- Hata gövdeleri `{"hata": "<açıklama>"}` biçimindedir.

## Tur yaşam döngüsü

```text
   işçi                                   koordinatör
    |-- GET /gorev?isci=ali ------------->|  {tur:0, parca:0, ic_adim:20, agirlik_sha256:...}
    |-- GET /agirlik --------------------->|  X-Tur: 0, X-Sha256: ...  (safetensors)
    |   (sha256 doğrula; H adım eğit)     |
    |-- POST /sonuc?isci=ali&tur=0 ------>|  doğrula -> {tamam:true, tur:0}
    |-- GET /gorev?isci=ali ------------->|  {bekle:true, tur:0}   (bu tur için sonucu var)
    |            ...diğer işçiler...      |  --en-az sonuç geldi -> tur kapanır
    |-- GET /gorev?isci=ali ------------->|  {tur:1, ...}          (yeni adaptör)
    |            ...                      |
    |-- GET /gorev?isci=ali ------------->|  {bitti:true}          (toplam_tur doldu)
```

Bir **tur**, koordinatörün yeterli sayıda (`en_az`) işçi sonucu toplayınca ya da zaman aşımı dolunca (en az 1 sonuçla) eldeki sonuçları birleştirip yeni adaptörü yayınlamasıyla biter. Bir işçi bir turda **en çok bir** sonuç gönderebilir.

## `GET /bilgi` — önerilir

Kimlik gerektirmez. Keşif ve uyum denetimi içindir.

```json
{
  "protokol": "1",
  "uygulama": "modelen-koordinator",
  "surum": "0.4.0",
  "tur": 3,
  "toplam_tur": 20,
  "taban_model": "Qwen/Qwen3-0.6B-Base",
  "adaptor": {"yontem": "lora", "r": 16, "alfa": 32, "hedef_moduller": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"], "dtype": "float32", "tensor_sayisi": 392},
  "agirlik_boyutu": 40400000,
  "agirlik_sha256": "9f2c...",
  "anahtar_gerekli": false
}
```

`protokol` alanı `"1"` olmalıdır. Diğer alanlar bilgi amaçlıdır.

## `GET /durum` — zorunlu

Koordinatörün anlık durumu.

```json
{
  "tur": 3,
  "toplam_tur": 20,
  "bekleyen_sonuc": ["ali", "veli"],
  "ozet": "9f2c1a7be0d34c55",
  "isciler": {"ali": 4.2, "veli": 61.0},
  "trafik": {"indirilen_bayt": 80800000, "yuklenen_bayt": 40400000},
  "gunluk": []
}
```

| Alan | Tür | Anlamı |
|---|---|---|
| `tur` | tamsayı | Şu anki tur (0'dan başlar) |
| `toplam_tur` | tamsayı | Planlanan toplam tur |
| `bekleyen_sonuc` | liste | Bu tur sonucunu göndermiş işçiler |
| `isciler` | nesne | İşçi → "son görülmeden bu yana saniye" |
| `trafik` | nesne | `indirilen_bayt`, `yuklenen_bayt` sayaçları |

## `GET /gorev?isci=<takma-ad>` — zorunlu

İşçiye bu turdaki görevi verir. `isci` parametresi yoksa **400** dönmelidir.

**Görev** (yeni sonuç bekleniyor):

```json
{
  "tur": 3, "toplam_tur": 20,
  "parca": 1, "n_parca": 4,
  "ic_adim": 20, "bs": 4, "seq": 512,
  "lr": 0.0002, "tohum": 0,
  "agirlik_sha256": "9f2c1a7be0d34c55e8b6...64 karakter"
}
```

| Alan | Tür | Anlamı |
|---|---|---|
| `tur` | tamsayı | Bu görevin turu; sonucu **aynı `tur` değeriyle** yüklenmelidir |
| `toplam_tur` | tamsayı | Öğrenme oranı çizelgesi için |
| `parca`, `n_parca` | tamsayı | İşçi, verinin `parca`. dilimini (`n_parca` eşit parçadan) kullanır |
| `ic_adim` | tamsayı | H: yerelde atılacak adım |
| `bs`, `seq` | tamsayı | Yığın büyüklüğü ve dizi uzunluğu |
| `lr` | sayı | Tepe öğrenme oranı (kosinüs çizelgesi işçide uygulanır) |
| `tohum` | tamsayı | Başlangıç adaptörünü ve modeli kuran tohum (tüm işçilerde aynı) |
| `mod` | metin | **İsteğe bağlı.** `"cpt"` (varsayılan): ham metinde devam eden ön eğitim, kayıp her belirteçte. `"sft"`: talimat ince ayarı, kayıp yalnızca asistan yanıtı belirteçlerinde (ChatML). Yoksa `cpt` varsayılır. Adaptör biçimi iki modda da aynıdır.
| `agirlik_sha256` | metin | İndirilecek adaptörün 64 karakterlik **küçük harfli onaltılı** SHA-256 özeti |

**Diğer yanıtlar:**

- `{"bekle": true, "tur": 3}` — işçinin bu tur için sonucu zaten var; bekleyip yeniden sorar.
- `{"bitti": true}` — eğitim tamamlandı.

## `GET /agirlik` — zorunlu

Güncel **global adaptörü** safetensors olarak döndürür (`application/octet-stream`).

| Başlık | Zorunlu | Anlamı |
|---|---|---|
| `X-Sha256` | evet | Gövdenin SHA-256 özeti (küçük harfli onaltılı). **Gövdeyle birebir eşleşmeli.** |
| `X-Tur` | evet | Ağırlığın ait olduğu tur (tamsayı) |

İşçi, indirdiği gövdenin özetini görevdeki `agirlik_sha256` ile karşılaştırır; uyuşmazsa (tur arada ilerlemiştir) görevi yeniden ister. Bu yüzden `/gorev` ve `/agirlik` aynı turda tutarlı olmalıdır.

## `POST /sonuc?isci=<ad>&tur=<n>` — zorunlu

İşçi eğittiği adaptörü yükler. Gövde: safetensors (`application/octet-stream`).

| Durum | Gövde | Ne zaman |
|---|---|---|
| **200** | `{"tamam": true, "tur": 3}` | Kabul edildi |
| **400** | `{"hata": "safetensors okunamadı: ..."}` | Gövde geçerli safetensors değil |
| **409** | `{"hata": "eski tur", "tur": 4}` | `tur` parametresi güncel turla uyuşmuyor |
| **409** | `{"hata": "bu tur için sonuç zaten var"}` | Aynı işçi aynı tur için ikinci kez gönderdi |
| **409** | `{"hata": "eğitim bitti"}` | Tüm turlar tamamlandı |
| **413** | `{"hata": "boyut"}` | Gövde boş ya da çok büyük (referans sınır: 300 MB) |
| **422** | `{"hata": "anahtar kümesi uyuşmuyor"}` | Tensör adları global adaptörle aynı değil |
| **422** | `{"hata": "şekil/tür uyuşmuyor: <ad>"}` | Bir tensörün şekli ya da dtype'ı farklı |
| **422** | `{"hata": "sonlu olmayan değer: <ad>"}` | NaN ya da sonsuz değer var |

:::uyari
Geçersiz bir yüklemeyi **asla `200` ile kabul etmeyin** ve hiçbir koşulda `500` dönmeyin: uyum testi bunu denetler. Bozuk girdi daima `4xx` olmalıdır.
:::

## Koordinatörün yapması gerekenler

Protokol, birleştirmenin *nasıl* yapılacağını dayatmaz. Gönüllü uygulamasının beklediği ve referans uygulamanın yaptığı şunlardır:

1. **Doğrula**: gelen adaptör global olanla aynı anahtar kümesine, şekle ve dtype'a sahip olmalı; tüm değerler sonlu olmalı.
2. **Topla**: `en_az` sonuç ya da zaman aşımı (en az 1 sonuç) ile turu kapat.
3. **Birleştir**: işçi sonuçlarını birleştirip yeni global adaptörü üret.
4. **Yayınla**: `tur += 1`, yeni baytların SHA-256'sını hesapla, `/gorev` ve `/agirlik` bunu yansıtsın.

### Referans dış adım

Referans koordinatörde (`istemci/koordinator.py`), `W` global adaptör ve `S_i` işçi sonuçları için:

```text
ortalama = mean(S_i)                     # aykırı delta elemesinden sonra
delta    = W - ortalama
tampon   = m * tampon + delta            # m = 0.5 (--dis-mom)
W        = W - lr_dis * (delta + m * tampon)   # lr_dis = 1.0 (--dis-lr)
```

**Aykırı eleme:** en az 3 sonuç varsa, `W - S_i` farkının normu medyanın `aykiri_kat` (varsayılan 5) katını aşan sonuç elenir. Bu basit bir zehirlenme önlemidir; kararlı bir saldırgana karşı yetmez ([Güvenlik](/guvenlik/)).

Düz ortalama (`W = ortalama`) da protokole uygundur; [örnek koordinatör](/minimal-koordinator/) bunu yapar.

## İşçi ne yapar?

Gönüllü tarafı (`istemci/isci.py`) şu döngüyü izler:

1. `GET /gorev` — `bekle` ise birkaç sn bekleyip yeniden sorar; `bitti` ise çıkar.
2. `GET /agirlik` — SHA-256'yı görevle karşılaştırır; uyuşmazsa 1'e döner.
3. Adaptörü yerel taban modele yükler (modeli `tohum` ile kurar).
4. Verinin `parca`. dilimini (`n = len(veri) // n_parca`) kullanarak `ic_adim` adım eğitir: AdamW (β=0,9/0,95), kosinüs çizelgeli `lr`, gradyan klibi 1,0. Örnekleme tohumu `"{isci}-{tur}"`.
5. `POST /sonuc?isci=…&tur=…` — eğitilen adaptör. `4xx` alırsa sonucu yok sayıp 1'e döner.

## İsteğe bağlı uzantı: `POST /soru`

Gönüllü uygulamasındaki **Topluluğa sor** paneli, sorusunu koordinatörün `/soru` adresine gönderir. Uygulamazsanız panel "iletilemedi" gösterir; çalışmayı etkilemez.

```bash
curl -s -X POST https://koordinator.ornek.org/soru -H "Content-Type: application/json" \
  -d '{"soru": "Ne zaman yeni tur başlar?", "isci": "ali", "surum": "0.1.0", "baglam": ""}'
# {"tamam": true, "no": 7}
```

Referans koordinatör bunu `calisma/sorular.jsonl` dosyasına yazar (IP saklamaz), 1-2000 karakterle sınırlar ve IP başına 10 dakikada 5 soruya izin verir (`429`).
