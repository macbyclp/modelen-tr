# Uyarlama yolu: açık bir tabanı Türkçeye uyarlama

Karar (kullanıcı beyanı, 2026-11-06): ilk model sıfırdan değil, açık bir taban modelin Türkçe uyarlaması olacak.

## Neden bu yol

- 1B'yi sıfırdan eğitmek tek 8 GB GPU'da aylar sürer ve sığmaz. Uyarlama LoRA/QLoRA ile 8 GB'a sığar (1–3B için kaba tahmin 4–6 GB, kaynaklar ikincil; kendimiz ölçeceğiz).
- Türkçe talimat ince ayarı kalabalık (bkz. README). Türkçe dil edinimini (sürekli ön eğitim) görev hizalamasından ayırmak, MODA çalışmasının önerdiği çerçeve ([SIGTURK 2026](https://aclanthology.org/2026.sigturk-1.17.pdf)).

## Taban model adayları

| Aday | Boyut | Lisans | Not |
|---|---|---|---|
| **Qwen/Qwen3-0.6B-Base** | 596M, BF16 ≈ 1,2 GB | Apache-2.0 (model kartından doğrulandı) | Hızlı döngü için ilk seçim |
| Qwen/Qwen3-1.7B-Base | ~1,7B, ≈ 3,4 GB (tahmin) | Apache-2.0 (model kartından doğrulandı) | Asıl "~1B" hedefine en yakın |
| Gemma 3 1B | ~1B | Google Gemma koşulları, Apache değil | Lisans şartları ayrıca okunmalı |
| SmolLM3-3B, MiniCPM5-2B | 2–3B | Apache-2.0 olduğu söyleniyor, doğrulanmadı | 8 GB için sıkı; sonraya |

Öneri: 0.6B ile boru hattını kur, sonra 1.7B'ye geç.

## Yöntem

1. **Taban ölçümü:** uyarlamadan önce Türkçe perplexity (Vikipedi ayrılmış parçası) ve TurkishMMLU / TR-MMLU gibi kıyas testleriyle tabanı ölç. Kıyas yoksa "iyileşti" demek mümkün değil.
2. **Tokenizer:** önce tabanın Türkçedeki kelime başına token sayısını ölç. Kelime dağarcığını genişletmek riskli ve ek eğitim ister; ölçüm kötü çıkmadıkça genişletme.
3. **Sürekli ön eğitim (LoRA/QLoRA):** Türkçe Vikipedi (elimizde) ile başla, sonra FineWeb2 `tur_Latn` alt kümesi. Unutmayı sınırlamak için karışıma İngilizce / çok dilli tekrar verisi ekle; "Hamza" çalışması Türkçe sürekli ön eğitimde özgün dildeki doğruluğun düştüğünü (yıkıcı unutma) bildiriyor.
4. **Değerlendirme:** aynı testlerle öncesi/sonrası, ayrıca İngilizce bir test ile unutma kontrolü.
5. **Görev hizalaması** ayrı, sonraki adım.

## Gönüllü ağıyla bağlantı (hipotez, kanıtlanmadı)

LoRA adaptörleri tabanın küçük bir bölümü kadar parametre içerir. Bu iki şeyi birden hafifletebilir: gönüllü GPU'nun VRAM gereksinimi (taban dondurulmuş, yalnızca adaptör eğitilir) ve DiLoCo senkronizasyonunda taşınan veri miktarı. Sonraki simülasyon: DiLoCo'yu yalnızca adaptör parametreleri üzerinde çalıştırmak.

Risk: DiLoCo ile ön eğitilmiş ağırlıkların sonradan standart DDP eğitimle uyumsuz kalabileceğini bildiren bir çalışma var ([arXiv 2511.13761](https://arxiv.org/abs/2511.13761)); adaptör ölçeğinde geçerli olup olmadığı bilinmiyor.

## İlk sonuç: 20 dakikalık LoRA koşusu (2026-11-06)

Kurulum: Qwen3-0.6B-Base (bf16), LoRA r=16 (tüm doğrusal katmanlar), dizi 512, etkin yığın 16 dizi, lr 2e-4 (kosinüs), gradyan kontrol noktalama, 215 adım ≈ 1,76M token, RTX 4060 Laptop 8 GB. Veri: Türkçe Vikipedi'nin ilk 30 MB'ı (`corpus-wiki-tr-30mb.txt`). Değerlendirme: ikinci parquet dosyasının son satır grubu (eğitimle örtüşmez), 200 bin token. Betikler `lora_cpt.py`, `olc_taban.py`.

| | Taban | LoRA sonrası |
|---|---|---|
| Token başına kayıp (nat) | 2,7228 | 2,6045 |
| Perplexity | 15,22 | 13,52 |
| Bayt başına bit | 1,2969 | 1,2406 (−%4,3) |
| Kelime başına token | 2,780 | 2,780 (tokenizer değişmedi) |

Eğitim kaybı (ilk 10 / son 10 adım ortalaması): 2,645 → 2,458. Tepe eğitim VRAM'i 5,23 GB (8 GB'a sığıyor, ~2,8 GB pay var). Hız ≈ 5,6 sn/adım. Adaptör dosyası 40,4 MB.

**Okuma:** uyarlama yolu bu donanımda çalışıyor ve kısa bir koşu bile Vikipedi benzeri Türkçe metinde ölçülebilir iyileşme veriyor. Sınırlar: tek koşu, tek tohum; değerlendirme metni eğitimle aynı alandan (Vikipedi), yani genel Türkçe başarısını göstermez; İngilizce unutma ölçülmedi; kıyas testleri (TurkishMMLU vb.) henüz yok. "Türkçe model iyileşti" demek için bunlar gerekir.

**Tokenizer notu:** 2,78 token/kelime Türkçe için yüksek (tokenizer Türkçeyi parçalıyor). Bu hem eğitim hem çıkarım maliyetini artırır; kelime dağarcığı genişletmenin değeri ayrıca ölçülmeli.

**Adaptör boyutu notu:** 40 MB'lık adaptör, DiLoCo senkronizasyonunda tüm modeli (1,2 GB) taşımaktan ~30 kat küçük. Hipotez (adaptör-DiLoCo) için umut verici, henüz denenmedi.

## Unutma ve kıyas testi (2026-11-06)

Veri: WikiText-2 raw test (İngilizce, CC BY-SA 3.0, 735 KB) ve TurkishMMLU (AYueksel/TurkishMMLU, 900 test sorusu, 9 konu × 100, 1,3 MB; lisansı doğrulanmadı, README'de bulunamadı). Betikler `olc_ing.py`, `olc_mmlu.py`; ham çıktı `olcum-sonuc.txt`. TurkishMMLU 5-shot, harf olasılığıyla; şans düzeyi %20.

| | Taban | LoRA (20 dk) |
|---|---|---|
| Türkçe bayt başına bit (Vikipedi, ayrılmış) | 1,297 | 1,241 |
| İngilizce bayt başına bit (WikiText-2) | 0,9468 | 0,9597 (+%1,4, ppl 16,68 → 17,33) |
| TurkishMMLU 5-shot doğruluk | %35,6 (320/900) | %34,7 (312/900) |

**Okuma:**
- Türkçe dil modelleme iyileşti (−%4,3), ama kıyas testinde iyileşme yok: fark 8 soru, 900 soruluk testin standart hatası (~1,6 puan) içinde, yani gürültü. Konu bazında da tek yönlü bir örüntü yok.
- İngilizcede hafif unutma var (+%1,4 bayt başına bit). Küçük ama tek koşu ve yalnızca Türkçe veriyle eğitim için beklenen yönde.
- Anlamı: 1,76M token ve Vikipedi ile dil modelleme kaybı düşüyor, ama bilgi/akıl yürütme kıyası kıpırdamıyor. TurkishMMLU bilgi ve muhakeme ölçer; bunu oynatmak için çok daha fazla ve çeşitli veri (milyarlarca token), İngilizce tekrar karışımı ve muhtemelen daha büyük taban gerekir.
- Dolayısıyla "Türkçe model iyileşti" iddiası bu aşamada **yapılamaz**; yapılabilecek olan, "yöntem çalışıyor ve bellek/hız bütçesi ölçüldü" demek.

## Adaptör-DiLoCo simülasyonu (2026-11-06)

Betik `adaptor_diloco.py`, ham veri `adaptor-diloco-h25.json` / `.log`. Qwen3-0.6B-Base dondurulmuş ve 4 sanal işçi arasında paylaşılıyor; yalnızca LoRA (r=16, 10,1M parametre, 40,4 MB fp32) işçiye özgü ve senkronizasyonda taşınıyor. 8 tur × 25 yerel adım (işçi başına 4 dizi × 512 token/adım), dış lr 1,0 / mom 0,5 (önceki oyuncak denemeden alındı, bu model için ayarlanmadı). Baseline: aynı toplam işlem, her adımda senkron (4×4 dizi). Değerlendirme: ayrılmış Türkçe Vikipedi parçasında 60 bin token, bayt başına bit.

| Tur | Baseline | Adaptör-DiLoCo |
|---|---|---|
| 0 | 1,2714 | 1,2714 |
| 2 | 1,2390 | 1,2395 |
| 4 | 1,2238 | 1,2275 |
| 6 | 1,2184 | 1,2201 |
| 8 (son) | **1,2155** | **1,2166** |

Fark 0,0011 bit/bayt (−%0,09); baseline'ın toplam kazancının (0,0559) yaklaşık %98'i DiLoCo ile elde edildi (0,0548). Tepe VRAM 5,64 GB.

**İletişim (hesap):** baseline her adımda adaptör boyutunda veri değişir: 200 adım × 4 işçi × 40,4 MB ≈ 32 GB. DiLoCo 8 turda 8 × 4 × 40,4 MB ≈ 1,3 GB: yaklaşık 25 kat az.

**Okuma:** adaptör ölçeğinde seyrek senkronizasyonun bedeli bu kurulumda ihmal edilebilir. Oyuncak modelde görülen ~0,11 nat fark burada görünmüyor; olası nedenler: dondurulmuş güçlü taban, küçük ve düşük gürültülü LoRA güncellemeleri, kısa eğitim.

**Sınırlar (önemli):** tek tohum; yalnızca 200 adım; 60 bin tokenlik ölçüm (küçük farklar gürültü olabilir); veri dilimleri aynı Vikipedi akışından geldiği için işçiler yaklaşık aynı dağılımı görüyor (gerçek gönüllülerde veri farklı olur); ağ gecikmesi, işçi kaybı ve kötü niyetli katkı simüle edilmedi; kıyas testi ve İngilizce unutma ölçülmedi; DiLoCo sonrası standart eğitimle uyumsuzluk riski (arXiv 2511.13761) sınanmadı.

## Sıradaki somut adımlar

1. Python ortamına `transformers`, `peft`, `accelerate`, `bitsandbytes` kurulumu (küçük paketler).
2. `Qwen/Qwen3-0.6B-Base` indirmesi (~1,2 GB, kullanıcı onayı gerekir).
3. Taban ölçümü: Türkçe perplexity ve kelime başına token.
4. 8 GB'da bellek ölçümüyle ilk LoRA sürekli ön eğitim koşusu (küçük ölçek).

## Kaynaklar / uyarılar

Aramalar tek turdu; model lisansları yalnızca Qwen3 için model kartı API'sinden doğrulandı. 2026 tarihli bazı makale bağlantıları (ufakzeka-1 vb.) doğrulanmadı.
