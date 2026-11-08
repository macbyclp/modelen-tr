"""Hesap e-postası akışları: e-posta doğrulama, şifre sıfırlama, başvuru durumu bildirimleri.

portal.py tarafından `baglan(modul)` ile bağlanır. Belirteçler veritabanında yalnızca SHA-256 özeti olarak durur, tek kullanımlıktır
ve süreleri sınırlıdır (doğrulama 24 saat, şifre sıfırlama 1 saat). Şifre sıfırlama istekleri hesabın var olup olmadığını sızdırmaz.
"""
import hashlib
import secrets
import time

import eposta

P = None
SURE_DOGRULAMA = 24 * 3600
SURE_SIFRE = 3600
MESAJLAR = {"dogrulama-gonderildi": "Doğrulama e-postası gönderildi; gelen kutunuzu (ve spam klasörünü) kontrol edin.",
            "dogrulandi": "E-posta adresiniz doğrulandı.", "sifre": "Parolanız değiştirildi. Yeni parolayla giriş yapabilirsiniz."}


def baglan(modul):
    global P
    P = modul
    P.MESAJLAR.update(MESAJLAR)
    P.db_hazirla_ek.append(semayi_kur)


def semayi_kur(c):
    c.executescript("""
    CREATE TABLE IF NOT EXISTS tokenlar(
      ozet TEXT PRIMARY KEY, kullanici_id INTEGER NOT NULL REFERENCES kullanicilar(id) ON DELETE CASCADE,
      amac TEXT NOT NULL, bitis INTEGER NOT NULL, kullanildi INTEGER NOT NULL DEFAULT 0, olusturma INTEGER NOT NULL);
    """)
    kol = [r["name"] for r in c.execute("PRAGMA table_info(kullanicilar)")]
    if "eposta_dogrulandi" not in kol:
        c.execute("ALTER TABLE kullanicilar ADD COLUMN eposta_dogrulandi INTEGER NOT NULL DEFAULT 0")
        c.execute("UPDATE kullanicilar SET eposta_dogrulandi=1 WHERE rol='yonetici'")  # yöneticiler komut satırından açılır


def ozet(t):
    return hashlib.sha256(t.encode()).hexdigest()


def yeni_token(kid, amac, sure):
    t = secrets.token_urlsafe(32)
    P.yurut("DELETE FROM tokenlar WHERE kullanici_id=? AND amac=? AND kullanildi=0", kid, amac)  # tek etkin belirteç
    P.yurut("INSERT INTO tokenlar(ozet,kullanici_id,amac,bitis,olusturma) VALUES(?,?,?,?,?)", ozet(t), kid, amac, int(time.time()) + sure, int(time.time()))
    return t


def token_bul(t, amac):
    if not t or len(t) > 100:
        return None
    r = P.tek("SELECT * FROM tokenlar WHERE ozet=? AND amac=?", ozet(t), amac)
    return r if r and r["kullanildi"] == 0 and r["bitis"] >= time.time() else None


def dogrulanmis(k):
    """E-posta yapılandırılmamışsa doğrulama şartı aranmaz (yerel/dev kurulum)."""
    return (not eposta.hazir()) or k["eposta_dogrulandi"] == 1


def dogrulama_gonder(k):
    t = yeni_token(k["id"], "dogrulama", SURE_DOGRULAMA)
    return eposta.gonder(k["eposta"], *eposta.dogrulama(k["ad"], f"{eposta.site()}/eposta-dogrula?t={t}"))


def dogrulama_notu(h):
    """Panelde doğrulanmamış hesap için uyarı + yeniden gönder düğmesi."""
    k = h.kullanici
    if dogrulanmis(k):
        return ""
    return ('<p class="note"><b>E-posta adresiniz doğrulanmadı.</b> Koordinatör başvurusu ve topluluk gönderileri için doğrulama gerekir. '
            f'Doğrulama e-postası <b>{P.e(k["eposta"])}</b> adresine gönderildi.</p>'
            '<form method="post" action="/eposta-dogrula-gonder">' + P.csrf_alani(h.csrf) +
            '<button class="btn" type="submit">Doğrulama e-postasını yeniden gönder</button></form>')


# ------------------------------------------------------------------ yönlendirme
def get(h, yol, q):
    if yol == "/eposta-dogrula":
        dogrula(h, (q.get("t") or [""])[0])
    elif yol == "/sifre-sifirla":
        sifirla_formu(h)
    elif yol == "/sifre-yenile":
        yenile_formu(h, (q.get("t") or [""])[0])
    else:
        return False
    return True


def post(h, yol, f):
    if yol == "/sifre-sifirla":
        sifirla(h, f)
    elif yol == "/sifre-yenile":
        yenile(h, f)
    elif yol == "/eposta-dogrula-gonder":
        if not h.kullanici:
            return h._yonlendir("/giris") or True
        yeniden_gonder(h)
    else:
        return False
    return True


def sayfa(h, kod, baslik, ust, icerik="", aciklama=""):
    h._html(kod, baslik, P.pages.phead("Hesap", ust, aciklama) + icerik)


def dogrula(h, t):
    r = token_bul(t, "dogrulama")
    if not r:
        giris = '<p><a class="btn" href="/panel">Panele git</a></p>' if h.kullanici else '<p><a class="btn" href="/giris">Giriş yap</a></p>'
        return sayfa(h, 400, "Bağlantı geçersiz", "Doğrulama bağlantısı geçersiz.", giris + "<p>Bağlantı kullanılmış ya da süresi dolmuş olabilir. Panelinizden yenisini isteyebilirsiniz.</p>")
    P.yurut("UPDATE kullanicilar SET eposta_dogrulandi=1 WHERE id=?", r["kullanici_id"])
    P.yurut("UPDATE tokenlar SET kullanildi=1 WHERE ozet=?", r["ozet"])
    sayfa(h, 200, "Doğrulandı", "E-posta adresiniz doğrulandı.", '<p><a class="btn accent" href="/panel">Panele git</a></p>')


def yeniden_gonder(h):
    k = h.kullanici
    if k["eposta_dogrulandi"] == 1 or not eposta.hazir():
        return h._yonlendir("/panel")
    if P.hiz_asildi(("dogrulama", k["id"]), 3, 3600):
        return h._panel({}, "Çok sık istek; bir saat içinde en çok 3 doğrulama e-postası gönderilebilir.")
    dogrulama_gonder(k)
    h._yonlendir("/panel?m=dogrulama-gonderildi")


def sifirla_formu(h, mesaj=""):
    sayfa(h, 200, "Şifremi unuttum", "Şifremi unuttum", (f'<p class="note">{P.e(mesaj)}</p>' if mesaj else "")
          + '<form class="kform" method="post" action="/sifre-sifirla">' + P.csrf_alani(h.csrf)
          + P.alan("eposta", "Hesabın e-posta adresi", "", "email", 'maxlength="120" required autocomplete="email"')
          + '<button class="btn accent" type="submit">Sıfırlama bağlantısı gönder</button></form><p><a href="/giris">Girişe dön</a></p>',
          "E-posta adresinize tek kullanımlık bir bağlantı göndeririz.")


def sifirla(h, f):
    ep = f.get("eposta", "").strip().lower()
    genel = "Bu e-posta adresi kayıtlıysa, şifre sıfırlama bağlantısı gönderildi. Gelen kutunuzu (ve spam klasörünü) kontrol edin."
    if not eposta.hazir():
        return sifirla_formu(h, "Bu sunucuda e-posta gönderimi şu an kapalı. Şifre sıfırlama için info@modelen.tr adresine yazın.")
    if P.hiz_asildi(("sifre-ip", h._ip()), 10, 3600) or P.hiz_asildi(("sifre-ep", ep), 3, 3600):
        return sifirla_formu(h, "Çok sık istek. Bir süre sonra tekrar deneyin.")
    k = P.tek("SELECT * FROM kullanicilar WHERE eposta=?", ep) if P.EPOSTA.match(ep) else None
    if k:
        t = yeni_token(k["id"], "sifre", SURE_SIFRE)
        eposta.gonder(k["eposta"], *eposta.sifirlama(k["ad"], f"{eposta.site()}/sifre-yenile?t={t}"))
    sayfa(h, 200, "Gönderildi", "Bağlantı gönderildi", f"<p>{P.e(genel)}</p><p><a href=\"/giris\">Girişe dön</a></p>")


def yenile_formu(h, t, hata=""):
    if not token_bul(t, "sifre"):
        return sayfa(h, 400, "Bağlantı geçersiz", "Sıfırlama bağlantısı geçersiz.",
                     '<p>Bağlantı kullanılmış ya da süresi dolmuş olabilir.</p><p><a class="btn" href="/sifre-sifirla">Yeni bağlantı iste</a></p>')
    sayfa(h, 200, "Yeni parola", "Yeni parola belirleyin", (f'<p class="note">{P.e(hata)}</p>' if hata else "")
          + '<form class="kform" method="post" action="/sifre-yenile">' + P.csrf_alani(h.csrf)
          + f'<input type="hidden" name="t" value="{P.e(t)}">'
          + P.alan("parola", "Yeni parola (en az 10 karakter)", "", "password", 'minlength="10" maxlength="200" required autocomplete="new-password"')
          + P.alan("parola2", "Yeni parola (tekrar)", "", "password", 'minlength="10" maxlength="200" required autocomplete="new-password"')
          + '<button class="btn accent" type="submit">Parolayı değiştir</button></form>')


def yenile(h, f):
    t = f.get("t", "")
    r = token_bul(t, "sifre")
    if not r:
        return yenile_formu(h, t)
    p1, p2 = f.get("parola", ""), f.get("parola2", "")
    hata = "Parola en az 10 karakter olmalı." if len(p1) < 10 or len(p1) > 200 else "Parolalar aynı değil." if p1 != p2 else ""
    if hata:
        return yenile_formu(h, t, hata)
    k = P.tek("SELECT * FROM kullanicilar WHERE id=?", r["kullanici_id"])
    P.yurut("UPDATE kullanicilar SET parola=?, eposta_dogrulandi=1 WHERE id=?", P.parola_ozet(p1), k["id"])  # e-postaya erişim kanıtlandı
    P.yurut("UPDATE tokenlar SET kullanildi=1 WHERE kullanici_id=? AND amac='sifre'", k["id"])
    P.yurut("DELETE FROM oturumlar WHERE kullanici_id=?", k["id"])  # eski oturumlar kapanır
    eposta.gonder(k["eposta"], *eposta.sifre_degisti(k["ad"]))
    h._yonlendir("/giris?m=sifre", [h._cerez("ms", "", 0)])


# ------------------------------------------------------------------ başvuru bildirimleri
def basvuru_yoneticiye(b, hesap_ad):
    for a in P.sorgu("SELECT eposta FROM kullanicilar WHERE rol='yonetici'"):
        eposta.gonder(a["eposta"], *eposta.yeni_basvuru_yoneticiye(b["ad"], hesap_ad, f"{eposta.site()}/yonetim/basvuru/{b['id']}"))


def basvuru_karar_bildir(b, durum, nota):
    k = P.tek("SELECT eposta, ad FROM kullanicilar WHERE id=?", b["kullanici_id"])
    if k and durum in ("onaylandi", "reddedildi", "askida", "duzenleme-onayla", "duzenleme-reddet"):
        eposta.gonder(k["eposta"], *eposta.basvuru_karar(k["ad"], b["ad"], durum, nota, f"{eposta.site()}/koordinator/{b['slug']}"))
