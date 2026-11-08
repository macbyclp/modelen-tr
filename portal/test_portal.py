"""Portal testleri: gerçek HTTP sunucusu + geçici veritabanı. Çalıştırma: py -3 -m unittest portal/test_portal.py"""
import http.client
import json
import os
import re
import tempfile
import threading
import unittest
from urllib.parse import urlencode

import portal


class Oturum:
    """Çerez tutan küçük istemci."""

    def __init__(self, port):
        self.port, self.cerez = port, {}

    def istek(self, yontem, yol, form=None, csrf_al=True):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        basliklar = {"Cookie": "; ".join(f"{k}={v}" for k, v in self.cerez.items())}
        govde = None
        if form is not None:
            form = dict(form)
            if csrf_al and "csrf" not in form:
                form["csrf"] = self.cerez.get("mc", "")
            govde = urlencode(form)
            basliklar["Content-Type"] = "application/x-www-form-urlencoded"
        c.request(yontem, yol, govde, basliklar)
        r = c.getresponse()
        veri = r.read().decode("utf-8", errors="replace")
        for k, v in r.getheaders():
            if k.lower() == "set-cookie":
                ad, _, deger = v.split(";")[0].partition("=")
                if "Max-Age=0" in v:
                    self.cerez.pop(ad, None)
                else:
                    self.cerez[ad] = deger
        return r.status, veri, dict(r.getheaders())

    def get(self, yol):
        return self.istek("GET", yol)

    def post(self, yol, **form):
        return self.istek("POST", yol, form)


class PortalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dizin = tempfile.mkdtemp()
        cls.sunucu = portal.sunucu_kur(os.path.join(cls.dizin, "t.db"), "127.0.0.1", 0)
        cls.port = cls.sunucu.server_address[1]
        threading.Thread(target=cls.sunucu.serve_forever, daemon=True).start()
        portal.yonetici_olustur("admin@ornek.org", "Yönetici", "yonetici-parola-1")

    @classmethod
    def tearDownClass(cls):
        cls.sunucu.shutdown()

    def setUp(self):
        portal.HIZ.clear()

    def giris(self, eposta, parola):
        o = Oturum(self.port)
        o.get("/giris")
        d, _, _ = o.post("/giris", eposta=eposta, parola=parola)
        return o, d

    def kayit(self, eposta, ad="Deneme"):
        o = Oturum(self.port)
        o.get("/kayit")
        d, _, _ = o.post("/kayit", ad=ad, eposta=eposta, parola="parola-123456", parola2="parola-123456", kabul="1")
        return o, d

    def test_1_akis_kayit_basvuru_onay_liste(self):
        ali, d = self.kayit("ali@ornek.org", "Ali")
        self.assertEqual(d, 303)
        d, h, _ = ali.get("/panel")
        self.assertEqual(d, 200)
        self.assertIn("Merhaba, Ali", h)
        # başvuru (adres boş: zorunlu değil)
        d, _, _ = ali.post("/basvuru", ad="Ali Lab", kisa="Türkçe LoRA ile kod modeli denemeleri",
                           ayrinti="Birinci paragraf.\n\nİkinci <b>paragraf</b>.", baglanti="https://ornek.org/ali",
                           adres="", iletisim="iletisim@ali.org")
        self.assertEqual(d, 303)
        anon = Oturum(self.port)
        self.assertNotIn("Ali Lab", anon.get("/koordinatorler")[1])
        self.assertEqual(anon.get("/koordinator/ali-lab")[0], 404)
        adm, d = self.giris("admin@ornek.org", "yonetici-parola-1")
        self.assertEqual(d, 303)
        d, h, _ = adm.get("/yonetim")
        self.assertIn("Ali Lab", h)
        self.assertIn("iletisim@ali.org", h)
        self.assertEqual(ali.get("/yonetim")[0], 403)
        kimlik = re.search(r"/yonetim/basvuru/(\d+)", h).group(1)
        d, h, _ = adm.get(f"/yonetim/basvuru/{kimlik}")
        self.assertIn("mailto:iletisim@ali.org", h)
        d, _, _ = adm.post("/yonetim/karar", id=kimlik, karar="onaylandi", **{"not": "Hoş geldiniz"})
        self.assertEqual(d, 303)
        d, h, _ = anon.get("/koordinatorler")
        self.assertIn("Ali Lab", h)
        self.assertIn("Koordinatör adresi henüz yok", h)
        d, h, _ = anon.get("/koordinator/ali-lab")
        self.assertEqual(d, 200)
        self.assertIn("&lt;b&gt;paragraf&lt;/b&gt;", h)
        self.assertNotIn("<b>paragraf</b>", h)
        self.assertNotIn("iletisim@ali.org", h)  # iletişim e-postası herkese açık değil
        self.assertEqual(json.loads(anon.get("/koordinatorler.json")[1])["koordinatorler"], [])  # adres yok
        self.assertIn("Hoş geldiniz", ali.get("/panel")[1])

    def test_2_adresli_koordinator_json_dizinine_girer(self):
        o, _ = self.kayit("veli@ornek.org", "Veli")
        o.post("/basvuru", ad="Veli GPU", kisa="Türkçe Vikipedi uyarlaması", ayrinti="", baglanti="",
               adres="https://koord.veli.example/", iletisim="")
        adm, _ = self.giris("admin@ornek.org", "yonetici-parola-1")
        kimlik = re.search(r'/yonetim/basvuru/(\d+)">Veli GPU', adm.get("/yonetim")[1]).group(1)
        adm.post("/yonetim/karar", id=kimlik, karar="onaylandi")
        d, h, _ = Oturum(self.port).get("/koordinatorler.json")
        self.assertEqual(json.loads(h)["koordinatorler"],
                         [{"ad": "Veli GPU", "adres": "https://koord.veli.example", "aciklama": "Türkçe Vikipedi uyarlaması", "onayli": True}])
        adm.post("/yonetim/karar", id=kimlik, karar="askida")
        self.assertEqual(json.loads(Oturum(self.port).get("/koordinatorler.json")[1])["koordinatorler"], [])

    def test_3_dogrulama_ve_guvenlik(self):
        o, _ = self.kayit("zeynep@ornek.org", "Zeynep")
        d, h, _ = o.post("/basvuru", ad="Z", kisa="kısa", ayrinti="", baglanti="", adres="", iletisim="")
        self.assertIn("2-60", h)
        d, h, _ = o.post("/basvuru", ad="Zeynep Lab", kisa="Yeterince uzun bir açıklama yazıldı", ayrinti="",
                         baglanti="", adres="http://x.org", iletisim="")
        self.assertIn("https://", h)
        d, _, _ = o.istek("POST", "/basvuru", {"ad": "x"}, csrf_al=False)  # CSRF yok
        self.assertEqual(d, 400)
        d, _, _ = o.istek("POST", "/basvuru", {"ad": "x", "csrf": "yanlis"}, csrf_al=False)
        self.assertEqual(d, 400)
        anon = Oturum(self.port)
        self.assertEqual(anon.get("/panel")[0], 303)
        self.assertEqual(anon.get("/yonetim")[0], 303)
        _, _, b = anon.get("/koordinatorler")
        self.assertIn("default-src 'self'", b["Content-Security-Policy"])
        c = http.client.HTTPConnection("127.0.0.1", self.port)
        c.request("GET", "/giris")
        sc = [v for k, v in c.getresponse().getheaders() if k.lower() == "set-cookie"][0]
        self.assertIn("HttpOnly", sc)
        self.assertIn("SameSite=Lax", sc)
        r = portal.tek("SELECT parola FROM kullanicilar WHERE eposta='zeynep@ornek.org'")
        self.assertTrue(r["parola"].startswith("scrypt$"))
        self.assertNotIn("parola-123456", r["parola"])
        for yol in ("/../portal/portal.py", "/build.py", "/%2e%2e/portal/veri/portal.db", "/pages.py"):
            self.assertEqual(anon.get(yol)[0], 404, yol)
        self.assertEqual(anon.get("/index.html")[0], 200)

    def test_4_giris_hatasi_hiz_siniri_ve_cikis(self):
        o, d = self.giris("yok@ornek.org", "yanlis-parola")
        self.assertEqual(d, 200)
        for _ in range(8):
            o.post("/giris", eposta="yok2@ornek.org", parola="x")
        self.assertIn("Çok fazla deneme", o.post("/giris", eposta="yok2@ornek.org", parola="x")[1])
        ali, _ = self.giris("ali@ornek.org", "parola-123456")
        self.assertEqual(ali.get("/panel")[0], 200)
        ali.post("/cikis")
        self.assertEqual(ali.get("/panel")[0], 303)

    def test_5_hesap_silme(self):
        o, _ = self.kayit("sil@ornek.org", "Sil")
        o.post("/basvuru", ad="Silinecek Lab", kisa="Silinecek bir başvuru örneği", ayrinti="", baglanti="", adres="", iletisim="")
        d, h, _ = o.post("/hesap-sil", parola="yanlis")
        self.assertIn("hatalı", h)
        d, _, _ = o.post("/hesap-sil", parola="parola-123456")
        self.assertEqual(d, 303)
        self.assertIsNone(portal.tek("SELECT 1 FROM kullanicilar WHERE eposta='sil@ornek.org'"))
        self.assertIsNone(portal.tek("SELECT 1 FROM basvurular WHERE ad='Silinecek Lab'"))
        self.assertEqual(o.get("/panel")[0], 303)

    def test_6_kayit_dogrulamalari(self):
        o = Oturum(self.port)
        o.get("/kayit")
        _, h, _ = o.post("/kayit", ad="A", eposta="a@b.co", parola="parola-123456", parola2="parola-123456", kabul="1")
        self.assertIn("2-60", h)
        _, h, _ = o.post("/kayit", ad="Ayşe", eposta="gecersiz", parola="parola-123456", parola2="parola-123456", kabul="1")
        self.assertIn("e-posta", h)
        _, h, _ = o.post("/kayit", ad="Ayşe", eposta="ayse@ornek.org", parola="kisa", parola2="kisa", kabul="1")
        self.assertIn("10 karakter", h)
        _, h, _ = o.post("/kayit", ad="Ayşe", eposta="ayse@ornek.org", parola="parola-123456", parola2="parola-123456")
        self.assertIn("kabul", h)
        _, h, _ = o.post("/kayit", ad="Ali", eposta="ali@ornek.org", parola="parola-123456", parola2="parola-123456", kabul="1")
        self.assertIn("zaten", h)

    def test_7_vekil_arkasinda_ip_ayrimi(self):
        portal.BAGLAM["vekil"] = True
        try:
            def dene(ip, eposta):
                c = http.client.HTTPConnection("127.0.0.1", self.port)
                o = Oturum(self.port)
                o.get("/giris")
                govde = urlencode({"eposta": eposta, "parola": "x", "csrf": o.cerez["mc"]})
                c.request("POST", "/giris", govde, {"Cookie": f"mc={o.cerez['mc']}", "X-Forwarded-For": ip,
                                                    "Content-Type": "application/x-www-form-urlencoded"})
                return c.getresponse().read().decode("utf-8", errors="replace")
            for i in range(16):
                dene("203.0.113.5", f"a{i}@ornek.org")
            self.assertIn("Çok fazla deneme", dene("203.0.113.5", "z@ornek.org"))  # aynı IP sınırlandı
            self.assertNotIn("Çok fazla deneme", dene("203.0.113.9", "y@ornek.org"))  # başka IP etkilenmedi
        finally:
            portal.BAGLAM["vekil"] = False

    def test_8_yonetici_basvuru_yapmaz_yalniz_gorur_ve_onaylar(self):
        adm, d = self.giris("admin@ornek.org", "yonetici-parola-1")
        self.assertEqual(adm.istek("GET", "/panel")[2]["Location"], "/yonetim")  # panel yerine yönetim
        self.assertEqual(adm.post("/basvuru", ad="Yönetici Lab", kisa="Yönetici başvuru yapmamalı", ayrinti="", baglanti="", adres="", iletisim="")[0], 403)
        self.assertIsNone(portal.tek("SELECT 1 FROM basvurular WHERE ad='Yönetici Lab'"))
        _, h, _ = adm.get("/yonetim")
        self.assertNotIn("/basvuru", h.replace("/yonetim/basvuru", ""))  # başvuru formu yok
        self.assertIn("Çıkış yap", h)

    def test_9_yonetici_girisi_yonetime_gider(self):
        o = Oturum(self.port)
        o.get("/giris")
        _, _, b = o.istek("POST", "/giris", {"eposta": "admin@ornek.org", "parola": "yonetici-parola-1"})
        self.assertTrue(b["Location"].startswith("/yonetim"))

    def test_10_ust_cubukta_giris_kayit_menusu(self):
        anon = Oturum(self.port)
        for yol in ("/index.html", "/koordinatorler", "/en/index.html"):
            h = anon.get(yol)[1]
            self.assertIn('href="/giris"', h, yol)
            self.assertIn('href="/kayit"', h, yol)
        ali, _ = self.kayit("menu@ornek.org", "Menü")
        h = ali.get("/index.html")[1]  # statik sayfa, giriş yapmış kullanıcı
        self.assertIn('<a href="/panel">Panel</a>', h)
        self.assertIn("Çıkış", h)
        self.assertNotIn('<a href="/giris">Giriş yap</a>', h)
        self.assertIn('<a href="/panel">Panel</a>', ali.get("/koordinatorler")[1])
        adm, _ = self.giris("admin@ornek.org", "yonetici-parola-1")
        self.assertIn('<a href="/yonetim">Yönetim</a>', adm.get("/index.html")[1])
        self.assertIn("Sign out", ali.get("/en/index.html")[1])


if __name__ == "__main__":
    unittest.main()
