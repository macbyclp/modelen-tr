# Modelen Kod (IDE, ilk sürüm)

Karar (kullanıcı, 2026-11-07): istemciden sonra Cursor / Claude Code tarzı bir IDE; hem kendi modellerimiz hem dış API'ler. Sıfırdan editör yazmak yerine **VS Code eklentisi** yaptım (bu, "VS Code çatalı"na giden en ucuz ilk adım; aynı çekirdek sonra çatala taşınabilir).

## Parçalar

| Yol | Görev |
|---|---|
| `ide/modelen-kod/src/saglayici.js` | Sağlayıcı katmanı: `openai` (Modelen sunucusu, Ollama, llama.cpp, OpenRouter, OpenAI…) ve `anthropic`. SSE akışı, iptal, hata. Bağımlılık yok |
| `ide/modelen-kod/src/baglam.js` | Mesaj kurma (seçim/dosya bağlamı, kırpma), cevaptan ilk kod bloğunu çıkarma |
| `ide/modelen-kod/src/extension.js` | VS Code komutları, sohbet paneli, anahtar kasası (SecretStorage) |
| `ide/modelen-kod/src/arayuz.js` | Sohbet paneli HTML'i (CSP + nonce; model çıktısı yalnızca `textContent`) |
| `ide/modelen-kod/test/test.js` | 9 test (sahte OpenAI/Anthropic sunucularıyla) |
| `sunucu/modelen_sunucu.py` | Qwen3-0.6B-Base + Modelen adaptörünü OpenAI uyumlu uçta sunar (`127.0.0.1:8760`) |

## Özellikler

- Sağlayıcı seçici (ayar: `modelen.saglayicilar`); yerel Modelen ve Ollama anahtarsız, bulut sağlayıcılar anahtarlı.
- **API anahtarı ayarlara yazılmaz**; `Modelen: API anahtarı ayarla` komutuyla işletim sistemi anahtar kasasına gider, panele/webview'a hiç geçmez, günlüğe yazılmaz.
- Akışlı cevap, **Dur** düğmesi, yeni sohbet, açık dosya/seçim bağlamı (12 000 karakterde kırpılır).
- **Seçimi değiştir**: cevaptaki ilk kod bloğunu yalnızca kullanıcı düğmeye basınca ve yalnızca seçili alana yazar. Otomatik dosya düzenleme yok.
- Kısayol: `Ctrl+Alt+M` (seçimi sor).

## Doğrulananlar

- 9/9 birim testi (`node --test test/`): iki sağlayıcının akış ayrıştırması (satır ortasından bölünmüş parçalar dahil), başlıklar, hata, iptal, bağlam kurma, eklentinin `vscode` taklidiyle etkinleşmesi, anahtar yokken hata, paneldeki betiğin sözdizimi.
- **Gerçek uçtan uca**: JS sağlayıcı katmanı → `modelen_sunucu.py` (Qwen3-0.6B-Base + tur-3 adaptörü) akışla 8 parça aldı (~3 sn).

## Dürüst notlar / eksikler

- **Eklenti gerçek VS Code içinde çalıştırılmadı** (bu makinede VS Code kurulu değil). Yalnızca taklit `vscode` modülüyle ve birim testleriyle denendi; paneli gözle görmedim. İlk iş: VS Code'da F5 ile "Extension Development Host" açıp denemek.
- Gerçek Anthropic/OpenAI uçlarına çağrı yapılmadı (anahtar yok); yalnızca sahte sunucularla ve belgelenmiş biçimle denendi.
- **Modelin kalitesi sohbet asistanı değil**: 0.6B taban model talimat ayarlı değil; örnek istekte soruyu neredeyse aynen tekrarladı. Hat çalışıyor, yararlı cevap için talimat ayarlı (SFT) bir Türkçe model ya da daha büyük taban gerekir.
- Henüz yok: dosya düzenleme/araç çağırma (ajan), çok dosyalı bağlam, satır içi tamamlama, Türkçe kod verisiyle eğitim. Cursor/Claude Code düzeyi ajan özellikleri ayrı ve büyük iş.
- Paketleme (`vsce`) ve Marketplace yayını yapılmadı; kimlik/yayıncı adı gerektirir.

## Çalıştırma

```bash
# Modelen modelini sun (ayrı terminal; modelen/ klasöründen)
.venv/Scripts/python.exe sunucu/modelen_sunucu.py --adaptor istemci/calisma/tur-3.safetensors
# Testler
cd ide/modelen-kod && node --test test/
# VS Code'da: klasörü aç -> F5 -> komut paleti "Modelen: Sohbeti aç"
```
