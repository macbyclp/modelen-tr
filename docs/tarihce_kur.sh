#!/usr/bin/env bash
# Depo tarihçesini dosya zaman damgalarından yeniden kurar (bkz. README "Sürümler ve tarihçe").
# Yalnızca ilk kurulumda bir kez çalıştırıldı; kaydı şeffaflık için saklanır.
set -euo pipefail
cd "$(dirname "$0")/.."
AD="macbyclp"
EP="309920717+macbyclp@users.noreply.github.com"
TRAILER="Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"

# kaydet "<tarih>" "<başlık>" "<gövde>" yol...
kaydet() {
  local tarih="$1" baslik="$2" govde="$3"; shift 3
  git add -- "$@"
  GIT_AUTHOR_NAME="$AD" GIT_AUTHOR_EMAIL="$EP" GIT_COMMITTER_NAME="$AD" GIT_COMMITTER_EMAIL="$EP" \
  GIT_AUTHOR_DATE="$tarih" GIT_COMMITTER_DATE="$tarih" \
    git commit -q -m "$baslik" -m "$govde" -m "$TRAILER"
  echo "commit: $tarih  $baslik"
}

kaydet "2026-11-06T13:09:00+03:00" "Deney: DiLoCo benzetimi ve senkronizasyon taramaları" \
"Tek GPU'da K sanal işçiyle DiLoCo benzetimi (3,3M parametreli bayt düzeyi GPT), referans eğitim, dış optimizer ayarları ve tohum x senkron aralığı taraması. Çalışma notları docs/CALISMA-NOTLARI.md içinde. Bu commit ve sonrakilerin tarihleri dosya zaman damgalarından yeniden kurulmuştur." \
  diloco_sim.py sweep sweep-0.5-0.9.json sweep-0.7-0.5.json sweep-1.0-0.0.json sweep-1.0-0.5.json duman.json duman-adaptor.json docs/CALISMA-NOTLARI.md .gitignore

kaydet "2026-11-06T21:00:00+03:00" "Gerçek Türkçe veri: Vikipedi ile tekrar ve dış optimizer ızgarası" \
"Türkçe Vikipedi'den 30 MB metin üreten betik (veri depoda yok, CC BY-SA), aynı taramaların gerçek veriyle tekrarı ve 12 noktalı dış optimizer ızgarası." \
  wiki_to_txt.py sweep-wiki grid-wiki

kaydet "2026-11-06T21:37:00+03:00" "Uyarlama yolu: Qwen3-0.6B LoRA (20 dk) ve ölçüm betikleri" \
"Qwen3-0.6B-Base üstünde LoRA sürekli ön eğitim, Türkçe bit/bayt ölçümü, İngilizce unutma (WikiText-2) ve TurkishMMLU 5-shot kıyası. Sonuç: Türkçe bit/bayt 1,297 -> 1,241; TurkishMMLU değişmedi (gürültü içinde)." \
  lora_cpt.py olc_taban.py olc_ing.py olc_mmlu.py olcum-sonuc.txt

kaydet "2026-11-06T22:52:00+03:00" "Adaptör-DiLoCo benzetimi ve uyarlama planı (ADAPTASYON.md)" \
"Dondurulmuş taban + 4 sanal işçi, yalnızca LoRA adaptörü senkronize edilir. 8 turda fark 0,0011 bit/bayt, iletişim ~25 kat az. Yöntem, sınırlar ve literatür taraması ADAPTASYON.md içinde. Tek tohum; kanıt değil, umut verici sinyal." \
  adaptor_diloco.py adaptor-diloco-h25.json adaptor-diloco-h25.log sonuc-h25.json ADAPTASYON.md
git tag -a v0.1.0 -m "v0.1.0: Araştırma (DiLoCo benzetimi, LoRA uyarlaması, adaptör-DiLoCo)"

kaydet "2026-11-07T13:43:00+03:00" "Logo: Halay Halkası (kavram çalışmaları ve seçilen vektör sürümleri)" \
"100 SVG kavram, aday elemesi ve seçilen Halay Halkası (beş kol, beş fener): vektör, tek renk, beyaz ve küçük boyut sürümleri. Ham görsel çıktılar depoda yok." \
  logo

kaydet "2026-11-07T14:37:00+03:00" "Site: modelen.tr (TR + EN, çerezsiz)" \
"Statik site üreticisi (build.py), Türkçe ve İngilizce içerik, ölçümler sayfası, yasal metin taslakları (avukat onayı gerekir)." \
  site

kaydet "2026-11-07T17:23:00+03:00" "Gönüllü istemci prototipi: koordinatör, işçi, değerlendirme" \
"Adaptör-DiLoCo protokolü (HTTP + safetensors): /gorev, /agirlik, /sonuc. Doğrulama, aykırı delta elemesi, tur kaydı. 2 işçi x 3 tur uçtan uca çalıştı (1,2714 -> 1,2613 bit/bayt, tek tohum). Kimlik, zehirlenme koruması ve TLS eksik (ISTEMCI.md)." \
  istemci

kaydet "2026-11-07T17:44:00+03:00" "Yerel model sunucusu ve VS Code eklentisi prototipi" \
"OpenAI uyumlu yerel sunucu. VS Code eklentisi prototipi artık kullanılmıyor; yerine Rust uygulaması geldi." \
  sunucu ide

kaydet "2026-11-07T18:53:00+03:00" "Rust masaüstü uygulaması (egui)" \
"Gönüllü GPU katkısı, Kolay mod (büyük AÇIK/KAPALI), koordinatör seçici, Topluluğa sor, sistem tepsisi, kimlik kasası. 15 birim testi." \
  uygulama

kaydet "2026-11-07T22:39:00+03:00" "Lisans: Apache-2.0 ve bildirimler" "Kod ve model Apache-2.0; üçüncü taraf bildirimleri NOTICE içinde." \
  LICENSE NOTICE

kaydet "2026-11-07T23:07:00+03:00" "Kurumsal belgeler: kimlik notları ve avukat onay listesi" \
"Topluluk kimliği ve yayın öncesi kontrol listesi. Yasal metinler taslak; yayın kapısı avukat onayıdır." \
  kurumsal
git tag -a v0.2.0 -m "v0.2.0: Kimlik ve istemci (logo, site, gönüllü istemci, Rust uygulaması, lisans)"

kaydet "2026-11-08T16:46:00+03:00" "Portal: kayıt/giriş, koordinatör başvurusu, profil ve akış, yönetici paneli" \
"Tek dosya Python portalı (SQLite): koordinatör başvurusu ve onayı, herkese açık koordinatör sayfaları, Hugging Face bağlantısı, görseller (EXIF silinir), onaylı profil düzenleme, profiller (varsayılan gizli), sosyal bağlantılar, takip, akış, engel, bildirim ve moderasyon. 34 test. systemd + Caddy dağıtım örnekleri." \
  portal
git tag -a v0.3.0 -m "v0.3.0: Portal ve topluluk (modelen.tr canlıda)"
echo "tarihçe kuruldu"
