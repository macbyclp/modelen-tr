"""E-posta: SMTP gönderimi, doğrulama, şifre sıfırlama, başvuru bildirimleri.
Çalıştırma (portal/ klasöründe): py -3 -W ignore -m unittest test_eposta"""
import email
import os
import re
import socket
import sqlite3
import tempfile
import threading
import time
import unittest

import eposta
import portal
from test_gorsel import png
from test_portal import Oturum
from test_sosyal import mp_avatar


class SahteSMTP:
    """Gerçek smtplib yolunu denemek için küçük SMTP sunucusu (kimlik doğrulamasız, TLS'siz)."""

    def __init__(self):
        self.mesajlar = []
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(5)
        self.port = self.sock.getsockname()[1]
        threading.Thread(target=self._dinle, daemon=True).start()

    def _dinle(self):
        while True:
            try:
                c, _ = self.sock.accept()
            except OSError:
                return
            threading.Thread(target=self._oturum, args=(c,), daemon=True).start()

    def _oturum(self, c):
        f = c.makefile("rwb")
        yaz = lambda s: (f.write(s.encode() + b"\r\n"), f.flush())
        yaz("220 sahte ESMTP")
        veri_modu, tampon, zarf = False, [], {}
        while True:
            satir = f.readline()
            if not satir:
                return
            if veri_modu:
                if satir == b".\r\n":
                    self.mesajlar.append((zarf.get("from"), zarf.get("to"), b"".join(tampon)))
                    veri_modu, tampon = False, []
                    yaz("250 tamam")
                else:
                    tampon.append(satir[1:] if satir.startswith(b"..") else satir)
                continue
            k = satir.decode(errors="replace").strip()
            u = k.upper()
            if u.startswith("EHLO") or u.startswith("HELO"):
                yaz("250 sahte")
            elif u.startswith("MAIL FROM"):
                zarf["from"] = k[10:].strip("<> ")
                yaz("250 ok")
            elif u.startswith("RCPT TO"):
                zarf["to"] = k[8:].strip("<> ")
                yaz("250 ok")
            elif u == "DATA":
                veri_modu = True
                yaz("354 devam")
            elif u == "QUIT":
                yaz("221 gule gule")
                c.close()
                return
            else:
                yaz("250 ok")

    def kapat(self):
        self.sock.close()


class EpostaBirim(unittest.TestCase):
    def tearDown(self):
        eposta.YAKALA = None
        eposta.ayar_yukle({})

    def test_ayar_yukleme(self):
        eposta.ayar_yukle({"MODELEN_SMTP_HOST": "m.ornek.org", "MODELEN_SMTP_PORT": "587", "MODELEN_SMTP_USER": "info@ornek.org", "MODELEN_SMTP_PASS": "x"})
        self.assertEqual((eposta.AYAR["mod"], eposta.AYAR["gonderen"], eposta.AYAR["site"]), ("starttls", "Modelen <info@ornek.org>", "https://modelen.tr"))
        self.assertTrue(eposta.hazir())
        eposta.ayar_yukle({"MODELEN_SMTP_HOST": "m.ornek.org", "MODELEN_SMTP_USER": "info@ornek.org", "MODELEN_SITE_URL": "https://ornek.org/"})
        self.assertEqual((eposta.AYAR["mod"], eposta.AYAR["port"], eposta.AYAR["site"]), ("ssl", 465, "https://ornek.org"))
        eposta.ayar_yukle({"MODELEN_SMTP_HOST": "m.ornek.org", "MODELEN_SMTP_USER": "info@ornek.org"})  # parola yok -> hazır değil
        self.assertFalse(eposta.hazir())
        eposta.ayar_yukle({})
        self.assertFalse(eposta.hazir())
        self.assertFalse(eposta.gonder("a@b.co", "k", "m"))  # yapılandırma yok

    def test_gercek_smtp_yolu_ve_baslik_guvenligi(self):
        s = SahteSMTP()
        try:
            eposta.ayar_yukle({"MODELEN_SMTP_HOST": "127.0.0.1", "MODELEN_SMTP_PORT": str(s.port), "MODELEN_SMTP_MODE": "none", "MODELEN_SMTP_FROM": "Modelen <info@modelen.tr>"})
            konu, metin = eposta.dogrulama("Ayşe", "https://modelen.tr/eposta-dogrula?t=abc")
            eposta.simdi_gonder("ayse@ornek.org", konu, metin)
            self.assertEqual(len(s.mesajlar), 1)
            zarf_g, zarf_a, ham = s.mesajlar[0]
            m = email.message_from_bytes(ham, policy=email.policy.default)
            self.assertEqual((zarf_g, zarf_a), ("info@modelen.tr", "ayse@ornek.org"))
            self.assertEqual(m["From"], "Modelen <info@modelen.tr>")
            self.assertEqual(m["To"], "ayse@ornek.org")
            self.assertEqual(m["Subject"], "Modelen: e-posta adresinizi doğrulayın")
            self.assertEqual(m["Auto-Submitted"], "auto-generated")
            self.assertEqual(m["Reply-To"], "info@modelen.tr")
            self.assertIn("https://modelen.tr/eposta-dogrula?t=abc", m.get_content())
            self.assertIn("Merhaba Ayşe", m.get_content())  # Türkçe karakterler bozulmadan
            # kuyruk yolu (arka plan işçisi)
            self.assertTrue(eposta.gonder("veli@ornek.org", "Konu\r\nBcc: kotu@ornek.org", "gövde"))
            for _ in range(60):
                if len(s.mesajlar) >= 2:
                    break
                time.sleep(0.1)
            self.assertEqual(len(s.mesajlar), 2)
            m2 = email.message_from_bytes(s.mesajlar[1][2], policy=email.policy.default)
            self.assertIsNone(m2["Bcc"])  # konu satırı enjeksiyonu yok
            self.assertEqual(s.mesajlar[1][1], "veli@ornek.org")
            # geçersiz / enjeksiyonlu adresler reddedilir
            for kotu in ("a@b.co\r\nBcc: x@y.zz", "a b@c.de", "<x@y.zz>", "yok", "", None, "a@b.co,c@d.ef"):
                self.assertFalse(eposta.gonder(kotu, "k", "m"), repr(kotu))
        finally:
            s.kapat()


class Akislar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sunucu = portal.sunucu_kur(os.path.join(tempfile.mkdtemp(), "e.db"), "127.0.0.1", 0)
        cls.port = cls.sunucu.server_address[1]
        threading.Thread(target=cls.sunucu.serve_forever, daemon=True).start()
        portal.yonetici_olustur("admin@ornek.org", "Yönetici", "yonetici-parola-1")

    @classmethod
    def tearDownClass(cls):
        cls.sunucu.shutdown()

    def setUp(self):
        portal.HIZ.clear()
        self.posta = []
        eposta.ayar_yukle({})
        eposta.YAKALA = lambda k, s, m: self.posta.append((k, s, m))

    def tearDown(self):
        eposta.YAKALA = None

    def yeni(self, ep, ad="Kişi"):
        o = Oturum(self.port)
        o.get("/kayit")
        o.post("/kayit", ad=ad, eposta=ep, parola="parola-123456", parola2="parola-123456", kabul="1")
        return o

    def son(self, kime, konu_parcasi=""):
        for k, s, m in reversed(self.posta):
            if k == kime and konu_parcasi in s:
                return s, m
        return None

    def token(self, kime, yol):
        s, m = self.son(kime)
        return re.search(rf"{yol}\?t=([\w\-]+)", m).group(1)

    def yonetici(self):
        a = Oturum(self.port)
        a.get("/giris")
        a.post("/giris", eposta="admin@ornek.org", parola="yonetici-parola-1")
        return a

    # ---- doğrulama
    def test_01_dogrulama_epostasi_ve_baglanti(self):
        o = self.yeni("d1@ornek.org", "Doğrulanacak")
        s, m = self.son("d1@ornek.org", "doğrulayın")
        self.assertIn("Doğrulanacak", m)
        t = self.token("d1@ornek.org", "eposta-dogrula")
        # belirteç düz metin olarak veritabanında yok (yalnızca özet)
        self.assertEqual(portal.tek("SELECT COUNT(*) n FROM tokenlar WHERE ozet=?", t)["n"], 0)
        self.assertIn("doğrulanmadı", o.get("/panel")[1])
        d, h, _ = Oturum(self.port).get(f"/eposta-dogrula?t={t}")  # oturumsuz da çalışır (e-postadaki bağlantı)
        self.assertEqual(d, 200)
        self.assertIn("doğrulandı", h)
        self.assertNotIn("doğrulanmadı", o.get("/panel")[1])
        d, h, _ = Oturum(self.port).get(f"/eposta-dogrula?t={t}")  # tek kullanımlık
        self.assertEqual(d, 400)
        self.assertEqual(Oturum(self.port).get("/eposta-dogrula?t=uydurma")[0], 400)
        self.assertEqual(Oturum(self.port).get("/eposta-dogrula")[0], 400)

    def test_02_sure_dolumu_ve_yeniden_gonderme_siniri(self):
        o = self.yeni("d2@ornek.org")
        t = self.token("d2@ornek.org", "eposta-dogrula")
        portal.yurut("UPDATE tokenlar SET bitis=? WHERE ozet=?", int(time.time()) - 5, __import__("hesap").ozet(t))
        self.assertEqual(Oturum(self.port).get(f"/eposta-dogrula?t={t}")[0], 400)  # süresi dolmuş
        for _ in range(3):
            o.post("/eposta-dogrula-gonder")
        self.assertEqual(sum(1 for k, s, m in self.posta if k == "d2@ornek.org" and "doğrulayın" in s), 1 + 3)
        d, h, _ = o.post("/eposta-dogrula-gonder")
        self.assertIn("en çok 3", h)  # saatte 3
        # yeniden gönderme eski belirteci geçersiz kılar
        self.assertEqual(portal.tek("SELECT COUNT(*) n FROM tokenlar WHERE kullanici_id=(SELECT id FROM kullanicilar WHERE eposta='d2@ornek.org') AND kullanildi=0")["n"], 1)

    def test_03_dogrulanmamis_hesap_basvuru_ve_gonderi_yapamaz(self):
        o = self.yeni("d3@ornek.org", "Kısıtlı")
        alan = dict(ad="Kısıtlı Lab", kisa="Doğrulanmadan başvuru denemesi yazısı", ayrinti="", baglanti="", adres="", iletisim="", hf="")
        self.assertIn("doğrulayın", o.post("/basvuru", **alan)[1])
        self.assertIsNone(portal.tek("SELECT 1 FROM basvurular WHERE ad='Kısıtlı Lab'"))
        mp_avatar(o, "/profil", dict(ad="Kısıtlı", kullanici_adi="kisitli_d3", herkese_acik="1", csrf=o.cerez["mc"]))
        self.assertIn("doğrulayın", o.post("/gonderi", metin="deneme")[1])
        # doğrula → serbest
        Oturum(self.port).get(f"/eposta-dogrula?t={self.token('d3@ornek.org', 'eposta-dogrula')}")
        self.assertEqual(o.post("/basvuru", **alan)[0], 303)
        self.assertEqual(o.post("/gonderi", metin="artık yazabilirim")[0], 303)

    def test_04_sifre_sifirlama_tam_akis(self):
        o = self.yeni("s1@ornek.org", "Şifreli")
        yeni_oturum = Oturum(self.port)
        yeni_oturum.get("/giris")
        yeni_oturum.post("/giris", eposta="s1@ornek.org", parola="parola-123456")
        self.assertEqual(yeni_oturum.get("/panel")[0], 200)
        self.posta.clear()
        anon = Oturum(self.port)
        anon.get("/sifre-sifirla")
        # kayıtsız adres: aynı yanıt, e-posta gitmez
        d, h_yok, _ = anon.post("/sifre-sifirla", eposta="yok@ornek.org")
        self.assertEqual(d, 200)
        self.assertEqual(self.posta, [])
        d, h_var, _ = anon.post("/sifre-sifirla", eposta="s1@ornek.org")
        self.assertEqual(d, 200)
        govde = lambda h: re.search(r"Bu e-posta adresi kayıtlıysa[^<]*", h).group(0)
        self.assertEqual(govde(h_yok), govde(h_var))  # hesap varlığı sızmaz
        t = self.token("s1@ornek.org", "sifre-yenile")
        # GET belirteci tüketmez
        self.assertIn("Yeni parola", anon.get(f"/sifre-yenile?t={t}")[1])
        self.assertIn("Yeni parola", anon.get(f"/sifre-yenile?t={t}")[1])
        # zayıf / uyuşmayan parola reddedilir, belirteç hâlâ geçerli
        self.assertIn("10 karakter", anon.post("/sifre-yenile", t=t, parola="kisa", parola2="kisa")[1])
        self.assertIn("aynı değil", anon.post("/sifre-yenile", t=t, parola="yeni-parola-9876", parola2="baska-parola-9876")[1])
        d, _, b = anon.istek("POST", "/sifre-yenile", {"t": t, "parola": "yeni-parola-9876", "parola2": "yeni-parola-9876", "csrf": anon.cerez["mc"]})
        self.assertEqual((d, b["Location"]), (303, "/giris?m=sifre"))
        # eski parola çalışmaz, yeni çalışır; eski oturum kapanmış
        self.assertIn("hatalı", self.giris_dene("s1@ornek.org", "parola-123456"))
        self.assertEqual(yeni_oturum.get("/panel")[0], 303)
        self.assertEqual(self.giris_dene("s1@ornek.org", "yeni-parola-9876"), "ok")
        # bilgilendirme e-postası + belirteç tek kullanımlık
        self.assertIsNotNone(self.son("s1@ornek.org", "parolanız değiştirildi"))
        self.assertEqual(anon.get(f"/sifre-yenile?t={t}")[0], 400)
        self.assertEqual(anon.post("/sifre-yenile", t=t, parola="uc-uncu-parola-1", parola2="uc-uncu-parola-1")[0], 400)
        # sıfırlama e-postaya erişimi kanıtladığı için hesap doğrulanmış sayılır
        self.assertEqual(portal.tek("SELECT eposta_dogrulandi n FROM kullanicilar WHERE eposta='s1@ornek.org'")["n"], 1)

    def giris_dene(self, ep, parola):
        o = Oturum(self.port)
        o.get("/giris")
        d, h, _ = o.post("/giris", eposta=ep, parola=parola)
        return "ok" if d == 303 else h

    def test_05_sifirlama_siniri_yeni_istek_eskisini_gecersiz_kilar(self):
        self.yeni("s2@ornek.org")
        anon = Oturum(self.port)
        anon.get("/sifre-sifirla")
        anon.post("/sifre-sifirla", eposta="s2@ornek.org")
        t1 = self.token("s2@ornek.org", "sifre-yenile")
        anon.post("/sifre-sifirla", eposta="s2@ornek.org")
        t2 = self.token("s2@ornek.org", "sifre-yenile")
        self.assertNotEqual(t1, t2)
        self.assertEqual(anon.get(f"/sifre-yenile?t={t1}")[0], 400)  # eskisi geçersiz
        self.assertEqual(anon.get(f"/sifre-yenile?t={t2}")[0], 200)
        anon.post("/sifre-sifirla", eposta="s2@ornek.org")
        self.assertIn("Çok sık", anon.post("/sifre-sifirla", eposta="s2@ornek.org")[1])  # aynı adres saatte 3
        # süresi dolmuş belirteç
        portal.yurut("UPDATE tokenlar SET bitis=? WHERE kullanici_id=(SELECT id FROM kullanicilar WHERE eposta='s2@ornek.org') AND amac='sifre'", int(time.time()) - 1)
        self.assertEqual(anon.get(f"/sifre-yenile?t={self.token('s2@ornek.org', 'sifre-yenile')}")[0], 400)

    def test_06_basvuru_bildirimleri(self):
        o = self.yeni("b1@ornek.org", "Başvuran")
        Oturum(self.port).get(f"/eposta-dogrula?t={self.token('b1@ornek.org', 'eposta-dogrula')}")
        self.posta.clear()
        o.post("/basvuru", ad="Bildirim Lab", kisa="Bildirim akışını deneyen koordinatör", ayrinti="", baglanti="", adres="", iletisim="", hf="")
        self.assertIsNotNone(self.son("b1@ornek.org", "başvurunuz alındı"))
        s, m = self.son("admin@ornek.org", "yeni koordinatör başvurusu")
        self.assertIn("Bildirim Lab", m)
        kimlik = re.search(r"/yonetim/basvuru/(\d+)", m).group(1)
        adm = self.yonetici()
        adm.post("/yonetim/karar", id=kimlik, karar="onaylandi", **{"not": "Hoş geldiniz"})
        s, m = self.son("b1@ornek.org", "onaylandı")
        self.assertIn("/koordinator/bildirim-lab", m)
        self.assertIn("Hoş geldiniz", m)
        # düzenleme akışı e-postaları
        self.posta.clear()
        o.post("/basvuru", ad="Bildirim Lab Yeni", kisa="Güncellenmiş bildirim özeti yazısı", ayrinti="", baglanti="", adres="", iletisim="", hf="")
        self.assertIsNone(self.son("admin@ornek.org", "yeni koordinatör başvurusu"))  # düzenleme için "yeni başvuru" gitmez
        adm.post("/yonetim/karar", id=kimlik, karar="duzenleme-onayla")
        self.assertIsNotNone(self.son("b1@ornek.org", "düzenlemeniz onaylandı"))
        o.post("/basvuru", ad="Bildirim Lab Üç", kisa="Üçüncü sürüm özet yazısı burada", ayrinti="", baglanti="", adres="", iletisim="", hf="")
        adm.post("/yonetim/karar", id=kimlik, karar="duzenleme-reddet", **{"not": "Uygun değil"})
        s, m = self.son("b1@ornek.org", "düzenlemeniz onaylanmadı")
        self.assertIn("Uygun değil", m)
        # askı ve red
        self.posta.clear()
        adm.post("/yonetim/karar", id=kimlik, karar="askida")
        self.assertIsNotNone(self.son("b1@ornek.org", "askıya alındı"))
        self.posta.clear()
        adm.post("/yonetim/karar", id=kimlik, karar="beklemede")  # beklemeye alma e-posta göndermez
        self.assertEqual(self.posta, [])
        adm.post("/yonetim/karar", id=kimlik, karar="reddedildi", **{"not": "Eksik bilgi"})
        s, m = self.son("b1@ornek.org", "sonuçlandı")
        self.assertIn("Eksik bilgi", m)

    def test_07_yapilandirma_yoksa_ozellikler_zarifce_kapali(self):
        eposta.YAKALA = None  # SMTP yok
        self.assertFalse(eposta.hazir())
        o = self.yeni("y1@ornek.org", "Yapılandırmasız")
        self.assertEqual(o.get("/panel")[0], 200)  # kayıt çalışır
        self.assertNotIn("doğrulanmadı", o.get("/panel")[1])  # doğrulama şartı aranmaz
        alan = dict(ad="Mailsiz Lab", kisa="E-posta yokken de başvuru yapılabilir", ayrinti="", baglanti="", adres="", iletisim="", hf="")
        self.assertEqual(o.post("/basvuru", **alan)[0], 303)
        anon = Oturum(self.port)
        anon.get("/sifre-sifirla")
        self.assertIn("kapalı", anon.post("/sifre-sifirla", eposta="y1@ornek.org")[1])

    def test_08_yoneticiler_dogrulanmis_acilir_ve_eski_veritabani_gecisi(self):
        self.assertEqual(portal.tek("SELECT eposta_dogrulandi n FROM kullanicilar WHERE eposta='admin@ornek.org'")["n"], 1)
        yol = os.path.join(tempfile.mkdtemp(), "eski4.db")
        c = sqlite3.connect(yol)
        c.executescript("CREATE TABLE kullanicilar(id INTEGER PRIMARY KEY, eposta TEXT UNIQUE NOT NULL, ad TEXT NOT NULL, parola TEXT NOT NULL, rol TEXT NOT NULL DEFAULT 'kullanici', olusturma INTEGER NOT NULL);"
                        "INSERT INTO kullanicilar(eposta,ad,parola,rol,olusturma) VALUES('y@b.co','Yön','x','yonetici',0),('k@b.co','Kul','x','kullanici',0);")
        c.close()
        yeni = portal.db_ac(yol)
        d = {r["eposta"]: r["eposta_dogrulandi"] for r in yeni.execute("SELECT eposta, eposta_dogrulandi FROM kullanicilar")}
        self.assertEqual(d, {"y@b.co": 1, "k@b.co": 0})
        self.assertTrue(yeni.execute("SELECT 1 FROM sqlite_master WHERE name='tokenlar'").fetchone())
        yeni.close()

    def test_09_giris_sayfasinda_sifremi_unuttum(self):
        self.assertIn('href="/sifre-sifirla"', Oturum(self.port).get("/giris")[1])


if __name__ == "__main__":
    unittest.main()
