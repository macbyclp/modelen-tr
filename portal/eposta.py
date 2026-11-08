"""İşlemsel e-posta gönderimi (SMTP): doğrulama, şifre sıfırlama, başvuru durumu bildirimleri.

Yapılandırma ortam değişkenleriyle (systemd `EnvironmentFile`); parola depoya/koda yazılmaz:

  MODELEN_SMTP_HOST   örn. cpanel1.kayizer.com
  MODELEN_SMTP_PORT   465 (ssl) ya da 587 (starttls); varsayılan 465
  MODELEN_SMTP_MODE   ssl | starttls | none   (varsayılan: 465 -> ssl, 587 -> starttls)
  MODELEN_SMTP_USER   örn. info@modelen.tr
  MODELEN_SMTP_PASS   posta kutusunun parolası
  MODELEN_SMTP_FROM   varsayılan: "Modelen <MODELEN_SMTP_USER>"
  MODELEN_SITE_URL    e-postalardaki bağlantı tabanı, varsayılan https://modelen.tr

Gönderim arka plan iş parçacığında yapılır (web isteği SMTP'yi beklemez), en çok 3 deneme. Günlüğe yalnızca "kime (maskeli) +
konu + sonuç" yazılır; e-posta gövdesi ve bağlantı belirteçleri asla yazılmaz.
Yapılandırma yoksa `hazir()` False döner ve e-posta gerektiren zorunluluklar (doğrulama şartı) devreye girmez.
"""
import email.utils
import os
import queue
import re
import smtplib
import ssl
import sys
import threading
import time
from email.message import EmailMessage

AYAR = {}
YAKALA = None  # testler: callable(kime, konu, metin); verilirse SMTP yerine çağrılır
_KUYRUK = queue.Queue()
_ISCI = {"t": None}
ADRES = re.compile(r"^[^@\s<>\",;]{1,64}@[^@\s<>\",;]{1,120}\.[^@\s<>\",;]{2,30}$")


def ayar_yukle(ortam=None):
    o = os.environ if ortam is None else ortam
    host = o.get("MODELEN_SMTP_HOST", "").strip()
    port = int(o.get("MODELEN_SMTP_PORT", "465") or 465)
    mod = o.get("MODELEN_SMTP_MODE", "").strip().lower() or ("starttls" if port == 587 else "ssl")
    kullanici = o.get("MODELEN_SMTP_USER", "").strip()
    AYAR.clear()
    AYAR.update(host=host, port=port, mod=mod, kullanici=kullanici, parola=o.get("MODELEN_SMTP_PASS", ""),
                gonderen=o.get("MODELEN_SMTP_FROM", "").strip() or (f"Modelen <{kullanici}>" if kullanici else ""),
                site=o.get("MODELEN_SITE_URL", "https://modelen.tr").rstrip("/"))


ayar_yukle()


def hazir():
    if YAKALA is not None:
        return True
    # parola henüz girilmemişse (kimlik doğrulamalı sunucu) e-posta "hazır" sayılmaz: doğrulama şartı kullanıcıları kilitlemesin
    return bool(AYAR.get("host") and AYAR.get("gonderen") and (AYAR.get("mod") == "none" or (AYAR.get("kullanici") and AYAR.get("parola"))))


def site():
    return AYAR.get("site", "https://modelen.tr")


def maske(adres):
    ad, _, alan = adres.partition("@")
    return (ad[:1] + "***@" + alan) if alan else "***"


def _temizle(konu):
    return re.sub(r"[\x00-\x1f\x7f]", " ", konu).strip()[:150]


def gonder(kime, konu, metin):
    """Gönderimi sıraya alır. Geçersiz adres ya da yapılandırma yoksa False."""
    if not isinstance(kime, str) or not ADRES.match(kime) or len(kime) > 200:
        return False
    konu = _temizle(konu)
    if YAKALA is not None:
        YAKALA(kime, konu, metin)
        return True
    if not hazir():
        return False
    _KUYRUK.put((kime, konu, metin))
    if _ISCI["t"] is None or not _ISCI["t"].is_alive():
        _ISCI["t"] = threading.Thread(target=_isci, daemon=True)
        _ISCI["t"].start()
    return True


def _isci():
    while True:
        try:
            kime, konu, metin = _KUYRUK.get(timeout=60)
        except queue.Empty:
            return
        for deneme, bekle in enumerate((0, 3, 12), 1):
            time.sleep(bekle)
            try:
                simdi_gonder(kime, konu, metin)
                print(f"E-POSTA gönderildi: {maske(kime)} · {konu}", file=sys.stderr, flush=True)
                break
            except smtplib.SMTPAuthenticationError:
                print(f"E-POSTA kimlik doğrulama hatası (parola/kullanıcı yanlış): {maske(kime)}", file=sys.stderr, flush=True)
                break  # tekrar denemek anlamsız
            except (smtplib.SMTPException, OSError) as ex:
                print(f"E-POSTA hata (deneme {deneme}): {type(ex).__name__} · {maske(kime)}", file=sys.stderr, flush=True)


def mesaj_kur(kime, konu, metin):
    m = EmailMessage()
    gonderen = AYAR.get("gonderen") or "Modelen <info@modelen.tr>"
    m["From"] = gonderen
    m["To"] = kime
    m["Subject"] = _temizle(konu)
    m["Date"] = email.utils.formatdate(localtime=False)
    m["Message-ID"] = email.utils.make_msgid(domain=email.utils.parseaddr(gonderen)[1].partition("@")[2] or "modelen.tr")
    m["Reply-To"] = email.utils.parseaddr(gonderen)[1]
    m["Auto-Submitted"] = "auto-generated"
    m["X-Auto-Response-Suppress"] = "All"
    m.set_content(metin)
    return m


def simdi_gonder(kime, konu, metin):
    """Eşzamanlı gönderim (hata fırlatır). `eposta-test` komutu ve işçi kullanır."""
    m = mesaj_kur(kime, konu, metin)
    host, port, mod = AYAR["host"], AYAR["port"], AYAR["mod"]
    if mod == "ssl":
        s = smtplib.SMTP_SSL(host, port, timeout=25, context=ssl.create_default_context())
    else:
        s = smtplib.SMTP(host, port, timeout=25)
    try:
        s.ehlo()
        if mod == "starttls":
            s.starttls(context=ssl.create_default_context())
            s.ehlo()
        if AYAR.get("kullanici") and AYAR.get("parola"):
            s.login(AYAR["kullanici"], AYAR["parola"])
        s.send_message(m)
    finally:
        try:
            s.quit()
        except Exception:
            pass


# ------------------------------------------------------------------ şablonlar
ALT = "\n\n--\nModelen Alternatif Eğitim Topluluğu · modelen.tr\nBu iletiyi siz istemediyseniz yok sayabilirsiniz; başka bir işlem gerekmez."


def dogrulama(ad, baglanti):
    return ("Modelen: e-posta adresinizi doğrulayın",
            f"Merhaba {ad},\n\nModelen hesabınızı açtığınız için teşekkürler. E-posta adresinizi doğrulamak için bağlantıya tıklayın (24 saat geçerli):\n\n{baglanti}\n\n"
            "Doğrulama, koordinatör başvurusu ve topluluk gönderileri için gereklidir." + ALT)


def sifirlama(ad, baglanti):
    return ("Modelen: şifre sıfırlama",
            f"Merhaba {ad},\n\nHesabınız için şifre sıfırlama istendi. Yeni bir parola belirlemek için bağlantıya tıklayın (1 saat geçerli, tek kullanımlık):\n\n{baglanti}\n\n"
            "Bu isteği siz yapmadıysanız bu iletiyi yok sayın; parolanız değişmez." + ALT)


def sifre_degisti(ad):
    return ("Modelen: parolanız değiştirildi",
            f"Merhaba {ad},\n\nHesabınızın parolası az önce değiştirildi ve açık tüm oturumlarınız kapatıldı.\n\n"
            "Bunu siz yapmadıysanız hemen info@modelen.tr adresine yazın." + ALT)


def basvuru_alindi(ad, proje):
    return ("Modelen: koordinatör başvurunuz alındı",
            f"Merhaba {ad},\n\n“{proje}” koordinatör başvurunuz alındı. Yöneticiler inceleyecek; sonuç size e-postayla bildirilecek ve panelinizde görünecek." + ALT)


def basvuru_karar(ad, proje, durum, nota, baglanti):
    baslik = {"onaylandi": "koordinatör başvurunuz onaylandı", "reddedildi": "koordinatör başvurunuz sonuçlandı",
              "askida": "koordinatör başvurunuz askıya alındı", "duzenleme-onayla": "düzenlemeniz onaylandı",
              "duzenleme-reddet": "düzenlemeniz onaylanmadı"}[durum]
    govde = {"onaylandi": f"“{proje}” koordinatör başvurunuz onaylandı. Sayfanız yayında:\n\n{baglanti}\n\nAdresiniz varsa gönüllüler GPU'larını size adayabilir.",
             "reddedildi": f"“{proje}” koordinatör başvurunuz bu aşamada onaylanmadı. Bilgilerinizi panelinizden güncelleyip yeniden gönderebilirsiniz:\n\n{site()}/panel",
             "askida": f"“{proje}” koordinatör sayfanız yöneticiler tarafından askıya alındı ve şu an yayında değil.",
             "duzenleme-onayla": f"“{proje}” için gönderdiğiniz düzenleme onaylandı ve yayına girdi:\n\n{baglanti}",
             "duzenleme-reddet": f"“{proje}” için gönderdiğiniz düzenleme onaylanmadı; yayındaki sayfanız değişmedi. Panelinizden yeniden gönderebilirsiniz."}[durum]
    if nota:
        govde += f"\n\nYönetici notu: {nota}"
    return (f"Modelen: {baslik}", f"Merhaba {ad},\n\n{govde}" + ALT)


def yeni_basvuru_yoneticiye(proje, kisi, baglanti):
    return ("Modelen: yeni koordinatör başvurusu",
            f"Yeni bir koordinatör başvurusu geldi.\n\nProje: {proje}\nBaşvuran: {kisi}\n\nİncelemek için:\n{baglanti}" + ALT)
