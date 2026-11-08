# Modelen portalı

Sitenin dinamik kısmı: kayıt/giriş, koordinatör başvurusu, herkese açık koordinatör sayfaları ve yönetici paneli. Tek dosya (`portal.py`), yalnızca Python standart kütüphanesi (SQLite + http.server). Statik siteyi de sunar; tek süreç tüm siteyi çalıştırır.

## Çalıştırma

```
py -3 portal/portal.py admin-olustur --eposta admin@ornek.org   # yönetici hesabı (parola sorulur)
py -3 portal/portal.py calistir --port 8780                     # TLS arkasındaysa --guvenli ekle
py -3 portal/portal.py liste                                    # başvuruları terminalde listele
py -3 -m unittest portal/test_portal.py                         # portal testleri
# tüm testler (portal/ klasöründen): py -3 -W ignore -m unittest test_portal test_gorsel test_duzenleme test_sosyal   # 34 test
```

Veritabanı: `portal/veri/portal.db` (e-posta ve parola özeti içerir; yedek ve erişim politikası size ait).

## Sayfalar

| Yol | Kim | Ne |
|---|---|---|
| `/kayit`, `/giris` | herkes | hesap aç, giriş yap |
| `/panel` | giriş yapmış | başvuru formu, durum, yönetici notu, hesabı sil, çıkış |
| `/koordinatorler`, `/koordinator/<slug>` | herkes | onaylı koordinatörler ve ayrıntı sayfaları |
| `/koordinatorler.json` | uygulama | yalnızca onaylı **ve adresi olan** koordinatörler |
| `/yonetim`, `/yonetim/basvuru/<id>` | yönetici | başvurular, iletişim e-postaları, onayla / reddet / askıya al / not |

Başvuruya isteğe bağlı **Hugging Face bağlantısı** (huggingface.co / hf.co) ve en çok 4 **görsel** (PNG/JPEG/WebP, her biri ≤ 2 MB, kenar ≤ 6000 px) eklenebilir. Görseller `gorsel.py` ile doğrulanır (tür dosya baytlarından belirlenir; SVG/GIF/HTML reddedilir) ve EXIF/konum, XMP, yorum gibi üst veriler silinir; piksel verisi yeniden kodlanmaz. Görseller veritabanında saklanır, onaylanınca herkese açık olur; onaysızken yalnızca sahibi ve yönetici görür.

**Onaylı profil düzenleme:** onaylı koordinatör bilgilerini panelden düzenleyebilir; değişiklik *taslak* olarak onaya düşer ve yönetici onaylayana kadar yayındaki sayfa değişmez (yeni görseller de gizli kalır). Yönetici "Düzenleme bekleyen" sekmesinde yayındaki/önerilen farkı görür, "Düzenlemeyi onayla" ya da "reddet" der (reddedilirse bekleyen görseller silinir). Sahibi kendi görselini her zaman hemen silebilir. Slug (adres) değişmez.

Koordinatör adresi **zorunlu değildir**: adresi olmayan onaylı proje sitede görünür, uygulamadaki listede görünmez.

## Profil ve topluluk (sosyal katman, `sosyal.py`)

Profil varsayılan **gizlidir**; kullanıcı "herkese açık" yapana kadar adı, fotoğrafı, bağlantıları ve gönderileri kimseye görünmez (sahibi ve yönetici hariç). E-posta hiçbir sayfada gösterilmez.

| Yol | Ne |
|---|---|
| `/profil` | profil ayarları: görünen ad, kullanıcı adı, hakkında (≤280), fotoğraf (≤1 MB, EXIF silinir), herkese açık anahtarı, sosyal bağlantılar (X, GitHub, Hugging Face, LinkedIn, YouTube, Instagram, Discord, web; ağ başına alan adı doğrulaması, en çok 8), engellenenler |
| `/u/<kullanici_adi>` | herkese açık profil: fotoğraf, hakkında, rozetli bağlantılar, sayılar, gönderiler; takip/engelle/bildir |
| `/akis`, `?takip=1` | herkese açık kısa gönderi akışı (düz metin ≤500, saatte 10 / günde 40), takip edilenler sekmesi, sayfalama |
| `/yonetim/moderasyon` | açık bildirimler (gönderi/profil): gizle, gizle+sustur, profili gizle, reddet; kısıtlı kullanıcılar ve kaldırma |

Engel iki yönlüdür (taraflar birbirini göremez/takip edemez). Bildirim: kendi içeriğine ve tekrar bildirime izin yok, saatte 10. Yönetici akıştan doğrudan gönderi gizleyebilir. Gönderiler düz metindir (otomatik bağlantı yok), HTML kaçışlıdır. `topluluk-kurallari.html` (TR/EN, taslak) ve KVKK/gizlilik metinleri güncellendi.

Yok: gönderiye görsel/yorum/beğeni, bildirimler, doğrudan mesaj, profil arama, bildirim e-postaları.

## Güvenlik (ve eksikler)

Var: scrypt parola özeti; oturum belirteci veritabanında yalnızca SHA-256 özeti; HttpOnly + SameSite=Lax çerez; CSRF belirteci; giriş ve kayıt hız sınırı; tüm kullanıcı metni HTML kaçışlı; parametreli SQL; CSP ve güvenlik başlıkları; statik sunumda yol gezintisi ve kaynak dosya engeli; iletişim e-postası yalnızca yöneticide.

Yok: e-posta doğrulaması ve parola sıfırlama (e-posta sunucusu yok), iki adımlı doğrulama, yönetici işlem günlüğü, İngilizce arayüz (portal şimdilik Türkçe), TLS (ters vekil ya da barındırıcıda kurulmalı), süreçler arası paylaşılan hız sınırı.

## Yayına alırken

Site statik barındırmayla (yalnızca dosya yükleyerek) çalışmaz: menüdeki Koordinatörler, Kayıt ve Giriş bağlantıları portal sürecini gerektirir. `modelen.tr` için bir sunucu, TLS ve bu sürecin çalıştırılması gerekir. Hukuk metinleri (çerez, gizlilik, KVKK) hesap sistemine göre güncellendi ama hâlâ avukat onayı bekleyen taslaktır.

## Sunucuya kurulum (örnek: systemd + Caddy)

`portal/deploy/` altında genel örnek dosyalar var: `modelen-portal.service` (ayrı sistem kullanıcısı, bellek/CPU sınırı, salt-okunur dosya sistemi), `Caddyfile.ornek` (TLS + ters vekil; `www` → ana alan adı yönlendirmesi), `yedekle.sh` + `modelen-yedek.*` (günlük sqlite yedeği, 14 gün). Portal `127.0.0.1` üstünde dinler; dışarıya yalnızca ters vekil açılır. TLS arkasında `--guvenli --vekil` ile çalıştırın.

- Güncelleme: `bash portal/yayinla.sh <ssh-takma-adı>` (siteyi derler, sunucuya yükler, hizmeti yeniden başlatır; veritabanına dokunmaz).
- İlk yönetici hesabı, parolayı siz sunucuda yazarak: `runuser -u modelen -- python3 /opt/modelen/portal/portal.py admin-olustur --eposta <e-posta> --db /opt/modelen/veri/portal.db`
