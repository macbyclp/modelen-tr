# modelen: çalışma notları

> Bu dosya projenin ilk README'sidir ve gün gün tutulan çalışma notları olarak saklanır. Güncel tanıtım için kök dizindeki README.md'ye bakın. Notlardaki "kullanıcı beyanı" ifadeleri, kararların proje sahibinden geldiğini belirtir.

Türkçe odaklı, küçük dil modellerini **gönüllü GPU'larla dağıtık olarak eğitme** projesi.

> Durum: fikir aşaması. Başlangıç tarihi: 2026-11-05.

## Hedef

Türk topluluğunun GPU'larını birleştirip ortak, açık bir Türkçe model eğitmek. Kâr değil, ortak sahiplik ve şeffaflık ön planda.

## Başlangıç kararları (kullanıcı beyanı, 2026-11-05)

- Amaç: modelleri **eğitirken** gönüllü GPU'lar kullanmak (çıkarım ağı ya da ses üretimi değil).
- Referans: [farm-vakit.hakancelik.dev](https://farm-vakit.hakancelik.dev/#katil) tarzı gönüllü katılım; ama bu proje seslendirme değil eğitim yapacak.

## Netleşen kararlar (kullanıcı beyanı, 2026-11-05)

- **Hedef model boyutu:** ~1B parametre (ilk gerçek hedef).
- **Donanım:** yalnızca tek GPU, RTX 4060 Laptop, 8 GB VRAM.
- **İlk somut adım:** küçük DiLoCo deneyi, `diloco_sim.py`.

**Önemli sınır (benim değerlendirmem):** 8 GB VRAM'e 1B modeli tam eğitmek sığmaz (ağırlık + Adam durumu tek başına bunu aşar). Bu yüzden simülasyon ~3M–100M parametreli küçük bir modelle yapılır; amaç modelin kalitesi değil, **seyrek senkronizasyonun kayıp eğrisini bozup bozmadığını** ölçmek. 1B hedefi, gerçek gönüllü ağı veya kiralık GPU ile sonraki aşama.

## Ürün ve organizasyon kararları (kullanıcı onayı "önerilerin kabul", 2026-11-07)

1. **Kitle:** önce Türkçe kullanan geliştiriciler ve kurumlar; ürün biçimi API ve yerel çalışan model.
2. **Farklılaştırıcı:** topluluk sahipliği ve şeffaf katkı kaydı.
3. **Teşvik:** başlangıçta kripto/para yok; katkı kaydı ve model üzerinde söz hakkı.
4. **Hukuki yapı:** önce yalnızca açık kaynak proje; tüzel kişilik gerekirse sonra (dernek/vakıf vb.). Veri toplama (KVKK) ve lisans buna göre ele alınır.
5. **Gönüllü güveni:** açık kaynak istemci, imzalı güncelleme, GPU'ya yalnızca eğitim işi, kullanıcı verisine erişim yok.
6. **Zaman ve ortaklar:** CEVAPLANMADI. Haftada kaç saat ve ortak olup olmayacağı belirsiz; plan buna göre küçülür.

## Dosyalar

- `diloco_sim.py`: tek GPU'da K sanal işçiyle DiLoCo simülasyonu + tek işçili referans.
- `.venv/`: yerel Python ortamı (PyTorch CUDA).
- `ADAPTASYON.md`: uyarlama yolu planı ve ölçümler (LoRA, unutma, TurkishMMLU, adaptör-DiLoCo).
- `LICENSE`, `NOTICE`: Apache-2.0 metni ve bildirim.
- `site/`: modelen.tr statik web sitesi (TR + EN, 30 sayfa, yeni Ölçümler sayfası dahil; `python site/build.py` ile derlenir; çerezsiz, üçüncü taraf kaynaksız). Yer tutucular `site/build.py` içinde.
- `logo/`: `fener/kucuk/` (küçük boyut: kucuk-ikon.svg, kucuk-isaret.svg, tek renk ve beyaz, png/ 16-512), `fener/f03-vektor.svg` (seçilen logo: Halay Halkası, vektör; tek renk ve beyaz sürümleri yanında), `f03-onizleme.html`, `fener-varyantlari.html` (#049 için 8 "ele ele" kompozisyonu), `finalistler.html` (kullanıcının 13 finalisti, görüşlerle) ve 100 adaylı logo seçim tabloları: `secim-tablosu-gorsel.html` (gpt-image-2 görselleri, `img/` içinde tam boyutlu PNG, ~116 MB) ve `secim-tablosu.html` (SVG vektör taslakları), tekil SVG'ler (`svg/`), kavramlar (`konseptler.py`), Codex fleet betikleri (`run_fleet.sh`, `make_briefs.py`, `collect.py`, `build_sheet.py`).
- `kurumsal/`: `KURUMSAL.md` (kimlik, yayın öncesi kontrol), `AVUKAT-ONAY-LISTESI.md` (avukata sorular, yayın kapısı).
- `istemci/`: gönüllü GPU istemcisi prototipi (koordinatör, işçi, adaptör-DiLoCo; `ISTEMCI.md`). Kimlik, zehirleme önlemi, TLS ve arayüz eksik.
- `uygulama/`: **Modelen masaüstü uygulaması (Rust, egui)**: gönüllü GPU katkısı, yerel model, Türkçe kod yardımcısı (Modelen + OpenAI uyumlu + Anthropic + Ollama), tek exe (~10 MB). Ayrıntı ve dürüst eksikler: `uygulama/UYGULAMA.md` (eğitim hâlâ Python alt süreci; arayüz elle tıklanarak denenmedi).
- `sunucu/`: Modelen modelini OpenAI uyumlu uçta sunan yerel sunucu. `ide/`: eski VS Code eklentisi prototipi, **artık kullanılmıyor** (kullanıcı VS Code istemiyor).

## Kurumsal kararlar (kullanıcı, 2026-11-07)

- Ad: **Modelen Alternatif Eğitim Topluluğu**, alan adı **modelen.tr**.
- Lisans: kod Apache-2.0, model Apache-2.0.
- Site: Türkçe + İngilizce, çok sayfalı. Kimlik: yalnızca e-posta (`iletisim@modelen.tr` varsayımı), kişi adı yok.
- Yasal metinler taslaktır; avukat onayı olmadan yayınlanmamalı (bkz. `kurumsal/AVUKAT-ONAY-LISTESI.md`).

## İlk sonuçlar (2026-11-05)

Ortam: RTX 4060 Laptop, 3,31M parametreli bayt düzeyi GPT, 4 sanal işçi, 20 tur × 25 yerel adım (senkronizasyon 25 kat seyrek), eşit token. Veri: `corpus-yerel.txt` (~256 KB, vault notları; **kişisel, paylaşma/yayınlama**). Ayrıntılar `sonuc-h25.json` ve `sweep-*.json`.

| Yöntem | Son val_loss |
|---|---|
| Tek işçi, her adımda senkron (referans) | 1,520 |
| DiLoCo, dış lr 0,7 / momentum 0,9 | 1,800 |
| DiLoCo, dış lr 1,0 / momentum 0,0 | 1,904 |
| DiLoCo, dış lr 0,7 / momentum 0,5 | 1,778 |
| DiLoCo, dış lr 0,5 / momentum 0,9 | 1,867 |
| **DiLoCo, dış lr 1,0 / momentum 0,5** | **1,630** |

**Okuma:** dış optimizer ayarı sonucu çok değiştiriyor; en iyi ayarla seyrek senkronizasyon referanstan ~0,11 nat geride, iletişim ise 25 kat az. Bu umut verici ama **kanıt değil**: tek tohum, çok küçük model, çok küçük ve tekrarlı veri, eğri henüz yakınsamadı, ayar ızgarası dar. Sonraki adım: gerçek Türkçe veri, birden çok tohum, H değerlerini (25/100/500) tarama.

### Tohum × senkronizasyon aralığı taraması (2026-11-06)

3 tohum, her işçi toplam 500 yerel adım, dış lr 1,0 / momentum 0,5 (sabit; yalnızca H=25 ve tohum 0'da ayarlandı). Referans (3 tohum ortalaması): **1,532**. Ham veri `sweep/`.

| H (iki senkron arası adım) | Senkron sayısı | Ort. val_loss | Referanstan fark |
|---|---|---|---|
| 10 | 50 | 1,599 | +0,067 |
| 25 | 20 | 1,639 | +0,107 |
| 50 | 10 | 1,694 | +0,161 |
| 100 | 5 | 1,758 | +0,226 |

**Okuma:** H büyüdükçe fark düzenli artıyor, tohumlar arası dağılım küçük (≤0,01), yani sonuç gürültü değil. Bu küçük modelde seyrek senkronizasyonun bedeli net: 10 kat daha az iletişim için ~0,16 nat. Sınırlar: dış ayar büyük H için yeniden ayarlanmadı (onları haksız yere kötü gösteriyor olabilir), model 3,3M, veri 256 KB. Gönüllü ağı için asıl soru bu bedelin 1B ölçeğinde ve gerçek veride nasıl değiştiği.

### Gerçek Türkçe veriyle tekrar (2026-11-06)

Veri: Türkçe Vikipedi (`wikimedia/wikipedia`, 20231101.tr, iki parquet, 553 MB, `data/wiki-tr/`, CC BY-SA/GFDL), ilk 3280 makale = 30 MB metin (`corpus-wiki-tr-30mb.txt`, `wiki_to_txt.py` ile). Sıralamanın rastgele olmadığı varsayılmalı. Aynı kurulum: 3,3M model, 4 işçi, 500 adım, 3 tohum, dış lr 1,0 / mom 0,5. Ham veri `sweep-wiki/`.

| H | Ort. val_loss | Referanstan fark | Tohum sapması |
|---|---|---|---|
| referans | 1,919 | — | — |
| 10 | 2,045 | +0,126 | 0,024 |
| 25 | 2,031 | +0,112 | 0,013 |
| 50 | 2,086 | +0,168 | 0,006 |
| 100 | 2,075 | +0,156 | 0,010 |

**Okuma:** gerçek veride fark yine ~0,11–0,17 nat, yani önceki bulgu (seyrek senkronizasyonun makul bir bedeli var) korunuyor. Ama önceki "H büyüdükçe düzenli kötüleşir" deseni burada net değil: H=10 ile 25, 50 ile 100 arasındaki farklar tohum sapmasıyla aynı büyüklükte. Dış ayar bu veri için ayarlanmadı; küçük model ve kısa eğitim (500 adım) sonucu sınırlıyor. Bu yüzden H'nin etkisi hakkında kesin bir şey söylemiyorum.

### Dış optimizer ızgarası, Vikipedi verisi (2026-11-06)

H=25, tohum 0, 12 ayar (dış lr 0,7/1,0/1,5 × momentum 0/0,3/0,5/0,8), referans 1,915. Ham veri `grid-wiki/`.

En iyi: **lr 1,0 / mom 0,5 → 2,032** (zaten kullandığımız ayar). Sonra lr 1,0 / mom 0,3 → 2,050; lr 1,5 / mom 0 → 2,056; lr 0,7 / mom 0,5 → 2,059. En kötü: lr 1,5 / mom 0,8 → 2,491 (dış adım çok büyük, kararsız).

**Okuma:** Ayar yeniden ayarlanınca daha iyi bir nokta çıkmadı; ~0,11 nat fark bu ızgarada dış optimizerdan kaynaklanmıyor. Izgara kaba (12 nokta, tek tohum, tek H); iç lr, iç adım ve işçi sayısı hâlâ sabit. Sonuç: tablodaki fark gerçek bir bedel gibi duruyor, ayar hatası gibi değil.

## Pazar ve literatür taraması (2026-11-06; tek arama turu, eksik olabilir)

**Mevcut Türkçe açık modeller** (yeni değiliz, farklılaşma gerek):
- [Turkish-LLM ailesi (ogulcanaydogan)](https://github.com/ogulcanaydogan/Turkish-LLM): 1,5B–32B, SFT+DPO, 144 bin Türkçe talimat çifti, GGUF sürümleri. Çıkış tarihi doğrulanmadı.
- [Turkce-LLM (matrixportalx)](https://featherless.ai/models/matrixportalx/Turkce-LLM): 8B, LoRA ile ince ayar, Apache-2.0, Nisan 2025.
- Eski/küçük: BERTurk, gpt2-small-turkish. 2026 tarihli yeni küçük model bulunamadı, ama arama dar.
- Çıkarım: Türkçe talimat ince ayarı zaten kalabalık. **Sıfırdan/sürekli ön eğitim ve gönüllü ağ sahipliği** daha az dolu alan.

**Türkçe ön eğitim verisi** (tam bağlantılar aramadan, doğrulanmadı):
- FineWeb2 `tur_Latn`: ODC-By 1.0, ~42 milyar kelime, ~125 GB disk.
- TurMix: ~168 milyar token, lisans doğrulanmadı ([arXiv 2512.18834](https://arxiv.org/abs/2512.18834)).
- `musabc/nanogpt-tr-v5-data`: CC-BY-4.0, 10–100 milyar token aralığı.
- Türkçe Vikipedi (`wikimedia/wikipedia`, 20231101.tr): 2 parquet dosyası, toplam ~553 MB (340 + 213 MB); lisans CC BY-SA/GFDL (doğrulanmalı). Küçük, temiz ilk veri adayı.

**Dağıtık eğitim kanıtı:**
- [OpenDiLoCo](https://arxiv.org/abs/2407.07852): iki kıtada üç ülke, ~%90–95 hesaplama kullanımı.
- INTELLECT-1: ~%96 hesaplama verimliliği (iş ortağı blogu); merkezî modellerin gerisinde kaldığı kabul ediliyor.
- Psyche (Nous): üçüncü taraf özetlerinde merkezî eğitimi geçtiği yazıyor; birincil kaynakla doğrulanmadı.
- **Dikkat:** [nanochat + DiLoCo çalışması](https://arxiv.org/abs/2511.13761) DiLoCo ile ön eğitilmiş ağırlıkların, sonrasında standart DDP ile orta/son eğitimde performansı geri kazanamadığını bildiriyor (temsil kayması). Gönüllü ağ planına doğrudan etki eder.

## Açık sorular

- Veri: hangi Türkçe veri seti, lisansı ne? (simülasyon `--data` ile verilen metin dosyasını kullanır; yoksa sentetik duman testi)
- Güven: gönüllü katkılarını nasıl doğrularız?
- Teşvik: katılımcılar neden GPU versin? (kripto yok, öneri)

## Teknik yol haritası (taslak)

1. **Prototip:** 3–5 GPU, DiLoCo benzeri seyrek senkronizasyon, tek makineyle kayıp eğrisi karşılaştırması.
2. **Güven katmanı:** katkı doğrulama (referans hesap, gradyan normu kontrolü, çift hesaplama).
3. **Türkçe veri hattı:** temizleme, tokenizer, lisans kaydı.
4. **Gönüllü istemcisi:** açık kaynak, imzalı, tek komutla kurulum; kod ve güncelleme akışı şeffaf.
5. **Topluluk açılışı:** küçük bir pilotla başla.

## Referanslar

- DiLoCo (Google DeepMind, 2023): seyrek senkronizasyonla dağıtık eğitim
- Hivemind / Learning@home: gönüllü dağıtık eğitim kütüphanesi
- Prime Intellect (INTELLECT-1) ve Nous Research (DisTrO / Psyche): dağıtık eğitim denemeleri (güncel durumu doğrula)
- BOINC / Folding@home: gönüllü hesaplama modeli
