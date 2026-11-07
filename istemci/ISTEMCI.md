# Modelen gönüllü istemcisi (prototip)

Gönüllünün GPU'sunda adaptör-DiLoCo turu çalıştıran en küçük çalışan sistem. Amaç: "Katıl" sayfasının arkasında gerçek bir şey olması ve protokolün uçtan uca denenmesi. **Üretim istemcisi değildir.**

## Parçalar

| Dosya | Görev |
|---|---|
| `baslat.py` | Tohumdan başlangıç LoRA adaptörünü üretir (`calisma/tur-0.safetensors`, 40,4 MB) |
| `koordinator.py` | Tur yönetimi: görev dağıtır, sonuçları doğrular, ortalar, Nesterov dış adımı uygular, her tur için adaptörü kaydeder |
| `isci.py` | Gönüllü tarafı: GPU'yu algılar, adaptörü indirir, H yerel adım eğitir, adaptörü geri yollar |
| `degerlendir.py` | Bir adaptörün Türkçe bit/bayt değerini ölçer |
| `ortak.py` | Ortak model kurulumu, safetensors (de)serileştirme, öğrenme oranı |

## Protokol (HTTP, JSON + safetensors)

```
işçi → GET  /gorev?isci=<takma-ad>   ← {tur, parca, ic_adim, bs, seq, lr, tohum, agirlik_sha256} | {bekle} | {bitti}
işçi → GET  /agirlik                 ← küresel adaptör (safetensors), sha256 görevdekiyle eşleşmeli
işçi → POST /sonuc?isci=..&tur=..    → yeni adaptör (safetensors)       ← {tamam} | 409 eski tur | 422 geçersiz
```

Koordinatör, `--en-az` sonuç gelince (ya da `--zaman-asimi` dolunca eldeki sonuçlarla) turu kapatır:
`delta = küresel − ortalama(işçi sonuçları)`, `tampon = m·tampon + delta`, `küresel −= lr_dış · (delta + m·tampon)` (m=0,5, lr_dış=1,0; simülasyondaki en iyi ayar).

## Güvenlik özellikleri (var olanlar)

- Ağdan gelen ağırlıklar **yalnızca safetensors** ile okunur; pickle yok, kod çalıştırılamaz.
- Gelen sonuçta anahtar kümesi, şekil ve tür kontrolü; NaN/Inf reddedilir.
- Delta normu medyanın 5 katını aşan sonuç elenir (≥3 sonuçta). Bu **basit** bir zehirleme önlemidir; kararlı bir saldırgana karşı yetmez.
- Bir işçi bir turda bir sonuç gönderebilir; eski tur sonucu reddedilir.
- Her tur adaptörünün sha256 özeti görevde duyurulur (indirme bozulmasını yakalar).
- İsteğe bağlı paylaşılan anahtar (`--anahtar`); varsayılan olarak yalnızca `127.0.0.1` dinler.
- Gönüllü takma ad kullanır; kişisel veri toplanmaz.

## Bilinen eksikler (dürüst liste)

- **Kimlik doğrulama / hesap yok**: tek paylaşılan anahtar. Sybil saldırısına açık.
- **Zehirleme önlemi zayıf**: gerçek çözüm tekrarlı doğrulama (aynı görevi 2 işçiye ver, karşılaştır) ve gözden saklı bir doğrulama kümesinde kayıp kontrolü. Yapılmadı.
- **TLS yok**: genel ağda ters vekil (Caddy/nginx) arkasında HTTPS şart.
- **Veri**: işçi yerel `data/tok-wiki30.pt` dosyasını okur. Gerçekte imzalı veri parçası manifesti ve parça indirme gerekir (lisans: CC BY-SA veri → avukat sorusu).
- **Arayüz yok**: komut satırı. Hedef: Tauri (Rust + web arayüzü) kabuğu; eğitim işçisini alt süreç olarak çalıştırır, GPU/VRAM, ilerleme ve duraklat/durdur gösterir.
- **Dayanıklılık**: koordinatör durumu bellekte (turlar diske yazılır ama momentum tamponu yazılmaz → yeniden başlatmada sıfırlanır).
- **Dengesiz donanım**: tüm işçiler aynı adım sayısını yapar; yavaş GPU turu geciktirir (zaman aşımı eldekilerle kapatır).
- **İmza**: sürümler imzalanmıyor; "imzalı açık kaynak istemci" kararı için sürüm hattı gerekli.
- Test yalnızca tek makinede, iki işçi aynı GPU'da.

## Çalıştırma

```bash
# modelen/ klasöründen
.venv/Scripts/python.exe istemci/baslat.py
.venv/Scripts/python.exe istemci/koordinator.py --baslangic istemci/calisma/tur-0.safetensors --tur 3 --en-az 2 --ic-adim 10
.venv/Scripts/python.exe istemci/isci.py --isci gonullu-a      # ayrı terminal
.venv/Scripts/python.exe istemci/isci.py --isci gonullu-b      # ayrı terminal
.venv/Scripts/python.exe istemci/degerlendir.py istemci/calisma/tur-0.safetensors istemci/calisma/tur-3.safetensors
```

Durum paneli: `http://127.0.0.1:8750/` (JSON: `/durum`).

## Sonraki adım: IDE

Kullanıcı kararı (2026-11-07): istemciden sonra Cursor / Claude Code tarzı bir IDE; kendi modellerimizi ve dış API'leri bağlayabilsin. Öneri: sıfırdan editör yazmak yerine açık kaynak bir VS Code çatalı ya da eklenti; sağlayıcı katmanı (OpenAI uyumlu uç, Anthropic, yerel Ollama/llama.cpp ve Modelen) ortak arayüzün arkasında. API anahtarları kullanıcıda kalır, işletim sistemi anahtar zincirinde saklanır.

## İlk uçtan uca deneme (2026-11-07)

2 işçi (aynı RTX 4060, ayrı süreç), 3 tur, tur başına 10 yerel adım, tek tohum, 60 sn'lik ayrık Vikipedi parçasında:

| adaptör | bit/bayt |
|---|---|
| tur 0 (başlangıç) | 1,2714 |
| tur 3 | 1,2613 |

Protokol uçtan uca çalıştı (görev → indirme → eğitim → yükleme → ortalama → yeni tur, hiçbir sonuç reddedilmedi). Düşüş küçük, tek tohum ve toplam 30 adımlık eğitim; "model iyileşti" kanıtı değil, yalnızca hattın doğru yönde çalıştığının işareti. Tur başına işçi yükü 40,4 MB.
