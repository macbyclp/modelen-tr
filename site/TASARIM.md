# Site tasarım notları

## Geçmiş
- 2026-11-07, 1. sürüm: kullanıcı "çok yapay zekâ gibi" dedi (soyut sıfat kartları, kimliksiz görünüm).
- 2. sürüm: Mistral, Codex, Prime Intellect incelendi; koyu/mint kimlik, ölçüm odaklı kanıt.
- 3. sürüm (güncel): kullanıcı "Mistral'e benzet: CSS, layout, animasyon" dedi. mistral.ai ana sayfası canlı incelendi (hesaplanmış stiller, `@keyframes` adları, bölüm yapısı, ekran görüntüleri). Claude in Chrome bağlı değildi; uygulamanın yerleşik tarayıcısı kullanıldı.

## 9. tur: kayan yıldızlar, daha fazla kırmızı, iki yeni bölüm (2026-11-07, kullanıcı isteği)
- **Kayan yıldızlar ve yıldız tozu (hero):** 7 kayan yıldız (beyaz baş, kırmızı kuyruk, farklı açı/süre/gecikme) + 34 titreyen toz noktası, yalnızca CSS (`.sky`, `home.py` içinde `sky()` ile deterministik üretilir). `prefers-reduced-motion` altında kayan yıldızlar görünmez, toz noktaları sabit kalır.
- **Kırmızı vurgu (CSS):** üst çubuk altında kırmızı gradyan çizgi; hero'da sağ üst ve taban kırmızı parıltı; ilke bölümü ve çağrı bandı arkasında kırmızı ışık; bölüm başlıklarının ve iç sayfa başlık bloklarının üstünde kısa kırmızı çubuk; ölçüm hücreleri, evre ızgarası, kartlar ve satırlarda kırmızı hover/üst çizgi; şeritte her üçüncü öğe kırmızı; alt bilgide kırmızı çizgi ve ışık; seçili metin ve kaydırma çubuğu kırmızı.
- **Yeni ana sayfa bölümleri (TR+EN):** (1) "Neden Halay Halkası?": halay ve fener anlatımı + büyük, ayrıntılı vektör logo (`assets/halay-halkasi.svg`, izleme çıktısı, 34 KB, yavaş süzülür); (2) "Aradığımız yardım": dört ihtiyaç (Türkçe kıyas testleri, veri ve lisans, güvenlik ve doğrulama, gönüllü istemcisi), hepsi Katıl sayfasına bağlı.
- **Doğrulama:** 31 sayfa × 375 ve 1440 px taşma ve tek `h1` denetimi temiz; kayan yıldızlar animasyonu çalışıyor (7/7 `running`), bir kare uçuşun ortasında dondurularak gözle görüldü (normal akışta bir an yakalanamadı); yeni bölümler masaüstü ve mobilde görüldü. `prefers-reduced-motion` davranışı tarayıcıda denenmedi.
- **Not:** Hero artık daha kalabalık; çok hareket hoşa gitmezse yıldız sayısı `sky()` parametrelerinden azaltılabilir.

## 8. tur: hero maskotu fener oldu (2026-11-07, kullanıcı onayı "Evet, yap")
- Hero'daki piksel ekran kartı maskotu kaldırıldı. Yerine basamakların ilk üç sütununun tepesine **üç piksel fener** kondu (12x13 piksel sprite: kulp, kapak, camlı gövde, taban; `home.py` içinde `_fener_sprite`, kodla üretilir). Alev iki karede titrer (CSS `steps`), fenerler bloklardan sonra sırayla düşer ve kırmızı bir parıltı taşır. `prefers-reduced-motion` altında hareket kapanır.
- Doğrulama: masaüstünde üç fenerin konumu ve animasyonların bittiği, taşma olmadığı ölçüldü; masaüstü ve mobil ekranda gözle görüldü. Mobilde fenerler durum şeridinin hemen üstünde ve küçük; kabul edilebilir ama masaüstündeki kadar belirgin değil.
- Ana sayfadaki "gönüllü ağı" illüstrasyonu (4x3 piksel ekran kartı) bilerek korundu: gönüllülerin ekran kartlarını anlatıyor.

## 7. tur: gerçek logo uygulandı (2026-11-07, kullanıcı onayı "Evet, siteye uygula")
- **Logo:** Halay Halkası küçük boyut sürümü (5 kollu halka, her eklemde kavrayan yumruk, 5 fener). Kaynak geometri `logo/make_kucuk.py`; site için `site/assets/logo-isaret.svg` (kontur #000 = üst çubuk zemini) üretildi ve `build.py` içinde satır içi gömülüyor (tek kaynak). Üst çubukta 32 px (eski 3x3 nokta ağı kalktı).
- **Favicon ve simgeler:** `assets/favicon.svg` (kendi zeminli simge), `icon-32.png`, `apple-touch-icon.png` (180), `icon-192.png`, `icon-512.png`; `manifest.webmanifest` (ad, renkler, simgeler, `display: standalone`).
- **Paylaşım görseli:** `assets/og.png` (1200x630: işaret, "modelen", Türkçe slogan, modelen.tr); `og:image` ve `twitter:card` etiketleri her sayfada. Yazı Segoe UI ile basıldı; markaya özel yazı tipi seçilince yenilenmeli.
- **Doğrulama:** 31 sayfa derlendi, kırık bağlantı ve yer tutucu yok, manifest geçerli JSON; masaüstü ve mobil (EN ana sayfa) üst çubukta logo görüldü; 170 px büyütmede ve 32/24/16 px'te okunurluk görüldü. Gerçek bir tarayıcı sekmesinde favicon'un nasıl göründüğüne ve sosyal ağlarda paylaşım kartına bakılmadı.
- **Not:** Hero'daki piksel ekran kartı maskotu ve düşen bloklar eski kimlikten kaldı; yeni logoyla (fener ve halka) görsel dili farklı. Gerekirse sadeleştirilir ya da fener temalı yapılır.

## Gözle kontrol, ikinci tur (2026-11-07)
- Gözle bakılanlar (dar/mobil genişlikte pencere): SSS, İletişim, KVKK, 404, Lisans, İngilizce Roadmap, Join, Measurements, About; önceki turdan Katıl, Yol haritası, Nasıl çalışır, Ölçümler, Hakkında. Bakılmayanlar (aynı şablonlar): Gizlilik, Çerez, Gönüllü şartları, Katkı şartları, Kullanım şartları, İngilizce FAQ/Contact/How it works/yasal sayfalar. Masaüstü genişliğinde yalnızca ana sayfa ve birkaç iç sayfa gözle görüldü.
- **Bulunan ve düzeltilen hata:** 404 sayfası eski, stilsiz kabukla duruyordu (üst çubuk/alt bilgi yok). Artık sitenin kabuğuyla üretiliyor (`build.py`), iç bağlantılar köke göre (`/…`) yazılı (her yolda çalışsın diye), `noindex`, sitemap'te yok.
- **Tutarlılık (çözüldü, kullanıcı isteği "Evet, geçir"):** Lisans ve altı yasal sayfa (TR+EN, 14 sayfa) artık iç sayfalarla aynı başlık bloğunu kullanıyor: etiket (Yasal/Lisans), başlık, tarih satırı, ardından sarı taslak uyarısı. Dönüşüm `build.py` içinde `legalize()` ile otomatik; metin dosyaları değişmedi. Doğrulama: 14 sayfa × 375/1440 px (tek `h1`, tek başlık bloğu, taşma yok); KVKK TR, Lisans TR ve Terms EN gözle görüldü (KVKK ilk bakışta tarayıcı önbelleğinden eski halini gösterdi, önbellek kırılınca yeni hal doğrulandı).

## Kalan sayfaların kontrolü (2026-11-07)
- **Otomatik (31 HTML sayfa × 375 ve 1440 px, yerel sunucuda gerçek tarayıcıda):** yatay taşma yok, her sayfada tek `h1`, sızan yer tutucu/`undefined`/`%%` yok, yinelenen `id` yok, bozuk iç bağlantı yok.
- **Gözle:** Katıl, Yol haritası, Nasıl çalışır, Ölçümler (masaüstü), Ölçümler (mobil), Hakkında (üst kısım). Tarayıcı penceresi arada başka pencerenin arkasında kaldığı için ekran görüntüleri zaman aşımına uğradı; SSS, İletişim, yasal sayfalar, 404 ve İngilizce sayfalar gözle bakılmadı, yalnızca otomatik denetim yapıldı.
- Düzeltme: soluk yazı rengi (`--dim`) küçük yazıda AA kontrastı vermiyordu (≈3,6:1); `#6d6d78` → `#8a8a96` (≈5,6:1, `#1a1a1e` üstünde ≈4,9:1).

## 6. tur: iç sayfalar + Ölçümler (2026-11-07, "siteyi geliştirelim")
- İç sayfalar (Nasıl çalışır, Yol haritası, SSS, Katıl, Hakkında, İletişim) ana sayfanın diliyle yeniden yazıldı (`pages.py`): başlık bloğu (etiket + büyük başlık + kısa giriş), akış kutuları, numaralı adımlar, evre ızgarası, sözlük satırları, risk listesi, büyük e-posta bağlantısı. Metinler kısaltıldı.
- **Yeni sayfa: Ölçümler** (`olcumler.html` / `measurements.html`, menüde ve alt bilgide): üç deneyin tüm tabloları (seyrek senkronizasyon, Türkçe uyarlama, adaptör-DiLoCo) ve her birinin sınırı; sayılar `ADAPTASYON.md`, `README.md` ve ham `.json` çıktılarından alındı. Kişisel not korpusu "küçük yerel Türkçe metin" olarak anıldı. Betikler/ham çıktılar "depo yayınlanınca paylaşılacak" diye belirtildi.
- Ana sayfadaki "Ölçümlerimiz" ve kanıt notu artık Ölçümler sayfasına gidiyor.
- Tablolar mobilde yatay kaydırılabilir kapta (`.tscroll`); sayfa yatay taşmıyor (375 px'te doğrulandı).
- Doğrulama: yerel sunucuda masaüstünde Nasıl çalışır ve Ölçümler, mobilde Ölçümler görüldü; Katıl, Hakkında, SSS, Yol haritası, İletişim ve İngilizce sayfalar ekranda gözle kontrol edilmedi (yalnızca yapı ve bağlantı denetimi).

## 5. tur: kırmızı ana renk + hamburger/ortalanmış menü (2026-11-07, kullanıcı isteği)
- Ana renk mint yerine **kırmızı**: `--accent #ff4640` (metin/vurgu), `--a2 #e0262d`, `--a3 #a3141c`, `--a4 #5f0d13` (bloklar, sprite), ana düğme `#e30a17` üstünde beyaz metin. Logo, favicon, piksel ekran kartı paleti ve parıltılar kırmızıya çevrildi.
- Üst çubuk: logo solda; sağda dil bağlantısı, kırmızı "Gönüllü ol" düğmesi ve **hamburger**. Hamburger, tam ekran **ortalanmış menü** açar (büyük ortalı bağlantılar, aktif sayfa kırmızı, altta yasal bağlantılar, dil ve e-posta). Düğme X'e dönüşür. `<details>` ile çalışır; Escape ile kapanma ve bağlantıya tıklayınca kapanma için küçük, kendi yazdığımız satır içi betik var (üçüncü taraf betik yok). Menü açıkken arka sayfa kaymaz (`body:has(details.menu[open])`).
- Not: "center menu" yorumu benim: ortalanmış tam ekran menü. İstenen buysa tamam; yalnızca ortalanmış logolu çubuk kastedildiyse değiştirilir.
- Doğrulama: yerel sunucuda masaüstü ve mobilde menü açılıp görüldü; kırmızı palet ana sayfada görüldü. Ekran görüntüleri bir adım gecikmeli geldi, bu yüzden bazı kareleri ikinci kez almak gerekti.

## 4. tur: "daha da yaklaştır" (2026-11-07)
- **Kaydırmayla ilerleyen ilke bölümü** (`.story`): Mistral'in "iplerin kimde olduğu" bölümünün yöntemi. Yapışkan sahne + CSS scroll-driven animasyon (`view-timeline`, `animation-timeline`); cümle sabit, kelime/açıklama kaydırdıkça değişir. Kendi cümlemiz: "Türkçenin yapay zekâsında şunu kimse tek başına tutmasın: kodu / ağırlıkları / veri listesini / kararları". Desteklemeyen tarayıcıda ve `prefers-reduced-motion`'da dört madde alt alta statik görünür.
- **Piksel maskot**: kendi çizdiğimiz piksel ekran kartı (24×11, `home.py` içinde kodla üretilir), hero'daki basamakların üstüne düşer, pervaneleri iki karede döner, LED'i yanıp söner. İlk satırda aynı sprite'tan 4×3'lük "gönüllü ağı" (illüstrasyon etiketli).
- Görsel kutularda hafif renkli parıltı (radial gradyan), satır başına farklı tonda.
- Doğrulama: yerel sunucuda masaüstü (1440) ve mobil (375); konsol hatası yok; kaydırmalı bölümün dört evresinden biri ("ağırlıkları.") ekranda doğrulandı, diğer üçü ve ters yönde kaydırma tek tek izlenmedi.

## Mistral'den alınan yöntemler (kod, logo, maskot, renk kopyalanmadı)
| Gözlem | Bizde |
|---|---|
| Çok koyu, hafif soğuk zemin (#101013), yüzey #1a1a1e, çizgi #27272b, sıcak beyaz metin | Aynı tür nötr koyu değerler; vurgu rengi bizim mint (#7cf5c8), onların turuncu-sarı gradyanı yok |
| Başlıklar orta kalınlıkta (500), sıkı harf aralığı | Aynı (`font-weight:500`, `letter-spacing:-0.015em`); yazı tipi sistem yazı tipi (üçüncü taraf yok) |
| Keskin köşeli, 1px çizgilerle çerçeveli sayfa; ince üst çubuk, logo hücresi | `.frame` dikey çizgiler, `header.site` 52px, logo hücresi |
| Hero'da düşen bloklar, ince çapraz "ip" çizgileri, süzülen elmas | `.blocks` (düşen basamaklı mint blokları), `.strings` SVG çizgiler, `.diamond` |
| Hero'da dönen kelime ("...to your [Process knowledge / IP / ...]") | `.swap` ile CSS-only dönen kelime (ortak / açık / şeffaf / bizim) |
| Hero altında tıklanabilir duyuru satırı | `.ticker` (durum + yol haritası bağlantısı) |
| Müşteri logo şeridi | Kendi yığınımızın akan şeridi (Apache-2.0, LoRA, DiLoCo, Qwen3, TurkishMMLU ...) |
| Sol yapışkan sekme menüsü + "Biz X. Siz Y." satırları, sağda büyük görsel | `.showcase`: yapışkan yan menü, dört satır (Birlikte eğitiriz / Ekran kartınız yeter / Az veri taşırız / Sınırlarımızı da yazarız), alternatif görseller |
| Alt bilgi: sütun başlıkları soluk gri | `.fcols` (Katıl / Öğren / Modelen) |
| `pop-in`, `fade-in`, `fall`, `float` animasyonları | `pop`, `fall`, `float`, `swap`, `marq`, `nabiz` + kaydırmayla beliren `.rv` (CSS scroll-driven, destek yoksa görünür) |

## Görsellerin dürüstlüğü
Satır görselleri uydurma değil, ölçülen şeylerin çizimi: taban/adaptör alanları gerçek ≈30:1 oranında; 25'lik hücre dizisi H=25 penceresi; çubuklar TurkishMMLU %35,6 / %34,7 ve ≈±1,6 gürültü; mozaik "illüstrasyon" etiketli.

## Bilerek yapılmayanlar
Sahte müşteri logosu/yorum, canlı gönüllü sayısı, Mistral'in piksel maskotu/logosu/turuncu gradyanı, onların metinleri.

## Doğrulama (2026-11-07)
Yerel sunucu üzerinden yerleşik tarayıcıda masaüstü (1440) ve mobil (375) genişlikte bakıldı; konsol hatası yok. Düzeltilen sorunlar: dönen kelime boşluğu (kısa kelimeler), `flip` satırlarında görsel sütunu dar kalması, küçük blok etiketinin kesilmesi. Gerçek cihazlarda, Safari/Firefox'ta ve farklı genişliklerde denenmedi.

## Açık
- Logo/marka rengi için tasarımcı; mint geçici.
- İç sayfaların metni sadeleştirilmedi (yalnızca stil yeni).
- Yalnızca koyu tema (açık tema yok).
- `.claude/launch.json` içine `modelen-site` önizleme girdisi eklendi (port 5180).
