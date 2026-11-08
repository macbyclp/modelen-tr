"""Portal API v1 testleri. Çalıştırma (portal/ klasöründe): py -3 -W ignore -m unittest test_api"""
import http.client
import json
import os
import re
import socket
import tempfile
import threading
import time
import unittest
from unittest import mock

import api
import eposta
import portal
from test_portal import Oturum


def api_istek(port, yontem, yol, govde=None, anahtar=None, ek=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=15)
    b = {}
    if anahtar:
        b["Authorization"] = f"Bearer {anahtar}"
    b.update(ek or {})
    veri = None
    if govde is not None:
        veri = json.dumps(govde) if not isinstance(govde, (str, bytes)) else govde
        b["Content-Type"] = "application/json"
    c.request(yontem, yol, veri, b)
    r = c.getresponse()
    ham = r.read().decode("utf-8", errors="replace")
    try:
        js = json.loads(ham) if ham else None
    except ValueError:
        js = None
    return r.status, js, dict(r.getheaders()), ham


class ApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sunucu = portal.sunucu_kur(os.path.join(tempfile.mkdtemp(), "a.db"), "127.0.0.1", 0)
        cls.port = cls.sunucu.server_address[1]
        threading.Thread(target=cls.sunucu.serve_forever, daemon=True).start()
        portal.yonetici_olustur("admin@ornek.org", "Yönetici", "yonetici-parola-1")

    @classmethod
    def tearDownClass(cls):
        cls.sunucu.shutdown()

    def setUp(self):
        portal.HIZ.clear()
        eposta.ayar_yukle({})
        eposta.YAKALA = None
        api.GETIR = api.guvenli_getir

    def tearDown(self):
        eposta.YAKALA = None
        api.GETIR = api.guvenli_getir

    def kullanici_anahtar(self, ep, ad="Api Kişi"):
        """Hesap aç, panelden anahtar oluştur; (oturum, anahtar) döndür."""
        o = Oturum(self.port)
        o.get("/kayit")
        o.post("/kayit", ad=ad, eposta=ep, parola="parola-123456", parola2="parola-123456", kabul="1")
        d, h, _ = o.post("/panel/api-anahtar-olustur", ad="deneme anahtarı")
        self.assertEqual(d, 200)
        return o, re.search(r"(mdl_[\w\-]{20,})", h).group(1)

    def yonetici(self):
        a = Oturum(self.port)
        a.get("/giris")
        a.post("/giris", eposta="admin@ornek.org", parola="yonetici-parola-1")
        return a

    # ---- herkese açık
    def test_01_herkese_acik_uclar_ve_cors(self):
        d, js, b, _ = api_istek(self.port, "GET", "/api/v1/saglik")
        self.assertEqual((d, js["durum"]), (200, "tamam"))
        self.assertEqual(b["Access-Control-Allow-Origin"], "*")
        d, js, b, _ = api_istek(self.port, "GET", "/api/v1/openapi.json")
        self.assertEqual(d, 200)
        self.assertEqual(js["openapi"], "3.0.3")
        self.assertIn("/koordinator/nabiz", js["paths"])
        d, js, b, _ = api_istek(self.port, "GET", "/api/v1/koordinatorler")
        self.assertEqual((d, js["koordinatorler"]), (200, []))
        d, _, b, _ = api_istek(self.port, "OPTIONS", "/api/v1/koordinatorler")
        self.assertEqual((d, b["Access-Control-Allow-Origin"]), (204, "*"))
        self.assertEqual(api_istek(self.port, "POST", "/api/v1/koordinatorler", {})[0], 405)
        self.assertEqual(api_istek(self.port, "GET", "/api/v1/koordinatorler/yok-boyle")[0], 404)
        self.assertEqual(api_istek(self.port, "GET", "/api/v1/koordinatorler/../../etc")[0], 404)
        self.assertEqual(api_istek(self.port, "GET", "/api/v1/bilinmeyen")[0], 401)  # anahtarsız: önce kimlik

    # ---- kimlik doğrulama
    def test_02_anahtar_zorunlu_gecersiz_iptal(self):
        for yol in ("/api/v1/ben", "/api/v1/koordinator"):
            d, js, b, _ = api_istek(self.port, "GET", yol)
            self.assertEqual((d, js["kod"], b["WWW-Authenticate"]), (401, "yetkisiz", "Bearer"))
        self.assertEqual(api_istek(self.port, "GET", "/api/v1/ben", anahtar="mdl_uydurma")[0], 401)
        self.assertEqual(api_istek(self.port, "GET", "/api/v1/ben", ek={"Authorization": "Basic abc"})[0], 401)
        o, a = self.kullanici_anahtar("a1@ornek.org")
        d, js, _, _ = api_istek(self.port, "GET", "/api/v1/ben", anahtar=a)
        self.assertEqual((d, js["eposta"], js["koordinator"]), (200, "a1@ornek.org", None))
        # anahtar veritabanında düz metin değil
        self.assertIsNone(portal.tek("SELECT 1 FROM api_anahtarlari WHERE ozet=?", a))
        self.assertEqual(portal.tek("SELECT COUNT(*) n FROM api_anahtarlari WHERE ozet=?", api.anahtar_ozet(a))["n"], 1)
        # iptal
        aid = portal.tek("SELECT id FROM api_anahtarlari WHERE ozet=?", api.anahtar_ozet(a))["id"]
        o.post("/panel/api-anahtar-iptal", id=str(aid))
        self.assertEqual(api_istek(self.port, "GET", "/api/v1/ben", anahtar=a)[0], 401)

    def test_03_anahtar_sayfasi_sinirlar_ve_baskasinin_anahtari(self):
        o, a = self.kullanici_anahtar("a2@ornek.org")
        self.assertIn("mdl_", o.get("/panel/api")[1])
        self.assertNotIn(a, o.get("/panel/api")[1])  # tam anahtar bir daha gösterilmez
        for i in range(api.MAKS_ANAHTAR - 1):
            self.assertEqual(o.post("/panel/api-anahtar-olustur", ad=f"k{i}")[0], 200)
        self.assertIn("En çok 5", o.post("/panel/api-anahtar-olustur", ad="fazla")[1])
        # başkası iptal edemez
        b = Oturum(self.port)
        b.get("/kayit")
        b.post("/kayit", ad="Baska", eposta="a2b@ornek.org", parola="parola-123456", parola2="parola-123456", kabul="1")
        aid = portal.tek("SELECT id FROM api_anahtarlari WHERE ozet=?", api.anahtar_ozet(a))["id"]
        b.post("/panel/api-anahtar-iptal", id=str(aid))
        self.assertEqual(api_istek(self.port, "GET", "/api/v1/ben", anahtar=a)[0], 200)
        # girişsiz sayfa
        self.assertEqual(Oturum(self.port).get("/panel/api")[0], 303)
        # CSRF'siz oluşturma
        self.assertEqual(o.istek("POST", "/panel/api-anahtar-olustur", {"ad": "x", "csrf": "yanlis"}, csrf_al=False)[0], 400)

    # ---- başvuru yaşam döngüsü
    def test_04_basvuru_olustur_guncelle_onay_taslak(self):
        o, a = self.kullanici_anahtar("a3@ornek.org", "Başvurucu")
        d, js, _, _ = api_istek(self.port, "GET", "/api/v1/koordinator", anahtar=a)
        self.assertEqual((d, js["kod"]), (404, "basvuru_yok"))
        self.assertEqual(api_istek(self.port, "PATCH", "/api/v1/koordinator", {"ad": "x"}, anahtar=a)[1]["kod"], "basvuru_yok")
        # doğrulama hataları
        self.assertEqual(api_istek(self.port, "POST", "/api/v1/koordinator", {"ad": "A", "kisa": "kısa"}, anahtar=a)[1]["kod"], "dogrulama")
        self.assertEqual(api_istek(self.port, "POST", "/api/v1/koordinator", {"ad": "Api Lab", "kisa": "Yeterince uzun bir özet yazısı", "bilinmeyen": 1}, anahtar=a)[1]["kod"], "bilinmeyen_alan")
        self.assertEqual(api_istek(self.port, "POST", "/api/v1/koordinator", {"ad": 5, "kisa": "x"}, anahtar=a)[1]["kod"], "gecersiz_tur")
        self.assertEqual(api_istek(self.port, "POST", "/api/v1/koordinator", "{bozuk", anahtar=a)[1]["kod"], "gecersiz_istek")
        self.assertEqual(api_istek(self.port, "POST", "/api/v1/koordinator", {"ad": "Api Lab", "kisa": "Yeterince uzun bir özet yazısı", "adres": "http://x.org"}, anahtar=a)[0], 400)
        # oluştur
        d, js, _, _ = api_istek(self.port, "POST", "/api/v1/koordinator", {"ad": "Api Lab", "kisa": "Yeterince uzun bir özet yazısı", "adres": "https://koord.api-lab.example/", "hf": "https://huggingface.co/api-lab"}, anahtar=a)
        self.assertEqual((d, js["durum"], js["slug"], js["adres"]), (201, "beklemede", "api-lab", "https://koord.api-lab.example"))
        self.assertEqual(api_istek(self.port, "POST", "/api/v1/koordinator", {"ad": "Tekrar", "kisa": "Yeterince uzun bir özet yazısı"}, anahtar=a)[1]["kod"], "basvuru_var")
        # beklemedeyken PATCH doğrudan uygulanır
        d, js, _, _ = api_istek(self.port, "PATCH", "/api/v1/koordinator", {"kisa": "Güncellenmiş daha uzun bir özet yazısı"}, anahtar=a)
        self.assertEqual((d, js["kisa"], js["taslak_var"]), (200, "Güncellenmiş daha uzun bir özet yazısı", False))
        self.assertEqual(js["adres"], "https://koord.api-lab.example")  # gönderilmeyen alan korunur
        # yönetici onaylar → herkese açık dizin
        adm = self.yonetici()
        kimlik = re.search(r"/yonetim/basvuru/(\d+)", adm.get("/yonetim")[1]).group(1)
        adm.post("/yonetim/karar", id=kimlik, karar="onaylandi")
        d, js, b, _ = api_istek(self.port, "GET", "/api/v1/koordinatorler")
        self.assertEqual([x["slug"] for x in js["koordinatorler"]], ["api-lab"])
        self.assertEqual(js["koordinatorler"][0]["nabiz"]["durum"], "bilinmiyor")
        d, js, _, _ = api_istek(self.port, "GET", "/api/v1/koordinatorler/api-lab")
        self.assertEqual((d, js["ad"], js["gorseller"]), (200, "Api Lab", []))
        self.assertNotIn("iletisim", js)  # iletişim e-postası herkese açık değil
        # onaylıyken PATCH taslak olur (202), yayın değişmez
        d, js, _, _ = api_istek(self.port, "PATCH", "/api/v1/koordinator", {"ad": "Api Lab Yeni"}, anahtar=a)
        self.assertEqual((d, js["taslak_var"], js["ad"]), (202, True, "Api Lab"))
        self.assertEqual(api_istek(self.port, "GET", "/api/v1/koordinatorler/api-lab")[1]["ad"], "Api Lab")
        adm.post("/yonetim/karar", id=kimlik, karar="duzenleme-onayla")
        self.assertEqual(api_istek(self.port, "GET", "/api/v1/koordinatorler/api-lab")[1]["ad"], "Api Lab Yeni")
        # askıya alınınca güncellenemez, dizinden çıkar
        adm.post("/yonetim/karar", id=kimlik, karar="askida")
        self.assertEqual(api_istek(self.port, "PATCH", "/api/v1/koordinator", {"ad": "Olmaz"}, anahtar=a)[1]["kod"], "askida")
        self.assertEqual(api_istek(self.port, "GET", "/api/v1/koordinatorler")[1]["koordinatorler"], [])
        self.assertEqual(api_istek(self.port, "GET", "/api/v1/koordinatorler/api-lab")[0], 404)

    def test_05_dogrulanmamis_eposta_basvuramaz(self):
        o, a = self.kullanici_anahtar("a4@ornek.org")
        eposta.YAKALA = lambda k, s, m: None  # e-posta "yapılandırılmış": doğrulama şartı devrede
        d, js, _, _ = api_istek(self.port, "POST", "/api/v1/koordinator", {"ad": "Doğrulanmamış", "kisa": "Yeterince uzun bir özet yazısı"}, anahtar=a)
        self.assertEqual((d, js["kod"]), (403, "eposta_dogrulanmadi"))
        self.assertIn("doğrulayın", o.post("/panel/api-anahtar-olustur", ad="yeni")[1])

    # ---- nabız
    def onayli_koordinator(self, ep, ad):
        o, a = self.kullanici_anahtar(ep, ad)
        api_istek(self.port, "POST", "/api/v1/koordinator", {"ad": ad + " Lab", "kisa": "Nabız ve adres denemeleri için koordinatör", "adres": f"https://koord.{ad.lower()}.example"}, anahtar=a)
        adm = self.yonetici()
        kimlik = re.search(rf"/yonetim/basvuru/(\d+)\">{ad} Lab", adm.get("/yonetim")[1]).group(1)
        adm.post("/yonetim/karar", id=kimlik, karar="onaylandi")
        return a, ad.lower() + "-lab"

    def test_06_nabiz(self):
        a, slug = self.onayli_koordinator("n1@ornek.org", "Nabiz")
        d, js, _, _ = api_istek(self.port, "POST", "/api/v1/koordinator/nabiz", {"durum": "calisiyor", "tur": 3, "toplam_tur": 10, "aktif_isci": 4, "protokol": "1", "surum": "0.4"}, anahtar=a)
        self.assertEqual((d, js["tamam"]), (200, True))
        n = api_istek(self.port, "GET", f"/api/v1/koordinatorler/{slug}")[1]["nabiz"]
        self.assertEqual((n["durum"], n["tur"], n["toplam_tur"], n["aktif_isci"]), ("cevrimici", 3, 10, 4))
        # eski nabız: gecikmeli → bilinmiyor
        portal.yurut("UPDATE basvurular SET nabiz_zaman=? WHERE slug=?", int(time.time()) - 3600, slug)
        self.assertEqual(api_istek(self.port, "GET", f"/api/v1/koordinatorler/{slug}")[1]["nabiz"]["durum"], "gecikmeli")
        portal.yurut("UPDATE basvurular SET nabiz_zaman=? WHERE slug=?", int(time.time()) - 90000, slug)
        self.assertEqual(api_istek(self.port, "GET", f"/api/v1/koordinatorler/{slug}")[1]["nabiz"]["durum"], "bilinmiyor")
        # bakımda
        api_istek(self.port, "POST", "/api/v1/koordinator/nabiz", {"durum": "bakimda", "mesaj": "kısa bakım"}, anahtar=a)
        self.assertEqual(api_istek(self.port, "GET", f"/api/v1/koordinatorler/{slug}")[1]["nabiz"]["durum"], "bakimda")
        # doğrulamalar
        for kotu, kod in (({"durum": "uyuyor"}, "gecersiz_durum"), ({}, "gecersiz_durum"), ({"durum": "calisiyor", "tur": -1}, "gecersiz_sayi"), ({"durum": "calisiyor", "tur": "3"}, "gecersiz_sayi"),
                          ({"durum": "calisiyor", "tur": True}, "gecersiz_sayi"), ({"durum": "calisiyor", "mesaj": "x" * 200}, "gecersiz_metin"), ({"durum": "calisiyor", "baska": 1}, "bilinmeyen_alan")):
            portal.HIZ.clear()
            self.assertEqual(api_istek(self.port, "POST", "/api/v1/koordinator/nabiz", kotu, anahtar=a)[1]["kod"], kod, kotu)
        # hız sınırı: dakikada 6
        portal.HIZ.clear()
        kodlar = [api_istek(self.port, "POST", "/api/v1/koordinator/nabiz", {"durum": "calisiyor"}, anahtar=a)[0] for _ in range(8)]
        self.assertEqual(kodlar[:6], [200] * 6)
        self.assertEqual(kodlar[6], 429)
        # onaysız koordinatör nabız gönderemez
        o, b = self.kullanici_anahtar("n2@ornek.org")
        api_istek(self.port, "POST", "/api/v1/koordinator", {"ad": "Onaysiz Lab", "kisa": "Henüz onaylanmamış koordinatör"}, anahtar=b)
        self.assertEqual(api_istek(self.port, "POST", "/api/v1/koordinator/nabiz", {"durum": "calisiyor"}, anahtar=b)[1]["kod"], "onayli_degil")

    # ---- adres doğrulama
    def test_07_adres_dogrulama_akisi(self):
        a, slug = self.onayli_koordinator("d1@ornek.org", "Dogrula")
        d, js, _, _ = api_istek(self.port, "POST", "/api/v1/koordinator/adres-dogrula/kontrol", anahtar=a)
        self.assertEqual(js["kod"], "baslatilmadi")
        d, js, _, _ = api_istek(self.port, "POST", "/api/v1/koordinator/adres-dogrula", anahtar=a)
        self.assertEqual(d, 200)
        self.assertEqual(js["dosya"], "https://koord.dogrula.example/.well-known/modelen-dogrulama.txt")
        t = js["icerik"]
        self.assertTrue(t.startswith("modelen-dogrulama-"))
        self.assertEqual(api_istek(self.port, "POST", "/api/v1/koordinator/adres-dogrula", anahtar=a)[1]["icerik"], t)  # aynı değer (tekrarlanabilir)
        istenen = []
        api.GETIR = lambda url: (istenen.append(url), "yanlis-icerik")[1]
        self.assertEqual(api_istek(self.port, "POST", "/api/v1/koordinator/adres-dogrula/kontrol", anahtar=a)[1]["kod"], "icerik_uyusmuyor")
        self.assertEqual(istenen, ["https://koord.dogrula.example/.well-known/modelen-dogrulama.txt"])
        def okunamadi(url):
            raise api.AdresHatasi("Dosya okunamadı (HTTP 404).")
        api.GETIR = okunamadi
        self.assertEqual(api_istek(self.port, "POST", "/api/v1/koordinator/adres-dogrula/kontrol", anahtar=a)[1]["kod"], "okunamadi")
        api.GETIR = lambda url: t + "\n"
        d, js, _, _ = api_istek(self.port, "POST", "/api/v1/koordinator/adres-dogrula/kontrol", anahtar=a)
        self.assertEqual((d, js["adres_dogrulandi"]), (200, True))
        self.assertTrue(api_istek(self.port, "GET", f"/api/v1/koordinatorler/{slug}")[1]["adres_dogrulandi"])
        # adres değişince doğrulama kendiliğinden sıfırlanır (tetikleyici)
        api_istek(self.port, "PATCH", "/api/v1/koordinator", {"adres": "https://baska.dogrula.example"}, anahtar=a)
        adm = self.yonetici()
        kimlik = re.search(r"/yonetim/basvuru/(\d+)\">Dogrula Lab", adm.get("/yonetim")[1]).group(1)
        adm.post("/yonetim/karar", id=kimlik, karar="duzenleme-onayla")
        self.assertFalse(api_istek(self.port, "GET", f"/api/v1/koordinatorler/{slug}")[1]["adres_dogrulandi"])
        # kontrol hız sınırı
        portal.HIZ.clear()
        api_istek(self.port, "POST", "/api/v1/koordinator/adres-dogrula", anahtar=a)
        kodlar = [api_istek(self.port, "POST", "/api/v1/koordinator/adres-dogrula/kontrol", anahtar=a)[0] for _ in range(12)]
        self.assertIn(429, kodlar)

    def test_08_guvenli_getir_ssrf_korumasi(self):
        def cozucu(ip):
            return lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443))]
        kotu = ["http://ornek.org/x", "https://127.0.0.1/x", "https://[::1]/x", "https://10.0.0.5/x", "ftp://ornek.org/x", "https://u:p@ornek.org/x", "https://ornek.org:22/x", "https://ornek.org:8080/x"]
        for url in kotu:
            with self.assertRaises(api.AdresHatasi, msg=url):
                api.guvenli_getir(url)
        for ip in ("127.0.0.1", "10.1.2.3", "192.168.1.9", "169.254.169.254", "172.16.0.4", "100.64.0.1", "0.0.0.0", "::1", "fe80::1", "224.0.0.1"):
            with mock.patch("socket.getaddrinfo", cozucu(ip)):
                with self.assertRaises(api.AdresHatasi, msg=ip):
                    api.guvenli_getir("https://dis.ornek.org/.well-known/modelen-dogrulama.txt")
        # bir alan adı hem genel hem özel IP'ye çözülüyorsa (DNS yeniden bağlama) reddedilir
        karisik = lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)), (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 443))]
        with mock.patch("socket.getaddrinfo", karisik):
            with self.assertRaises(api.AdresHatasi):
                api.guvenli_getir("https://karisik.ornek.org/x")
        self.assertTrue(api.adres_global_mi("93.184.216.34"))
        self.assertFalse(api.adres_global_mi("kötü"))

    # ---- genel
    def test_09_hiz_siniri_ve_yontemler(self):
        for _ in range(250):
            d = api_istek(self.port, "GET", "/api/v1/saglik")[0]
            if d == 429:
                break
        self.assertEqual(d, 429)
        portal.HIZ.clear()
        o, a = self.kullanici_anahtar("h1@ornek.org")
        self.assertEqual(api_istek(self.port, "DELETE", "/api/v1/ben", anahtar=a)[0], 405)
        self.assertEqual(api_istek(self.port, "POST", "/api/v1/ben", {}, anahtar=a)[0], 405)
        # 64 KB üstü gövde
        d, js, _, _ = api_istek(self.port, "POST", "/api/v1/koordinator", "x" * 70000, anahtar=a)
        self.assertEqual((d, js["kod"]), (400, "gecersiz_istek"))
        # API çağrıları çerez/CSRF gerektirmez ve çerez yerleştirmez
        d, js, b, _ = api_istek(self.port, "GET", "/api/v1/ben", anahtar=a)
        self.assertNotIn("Set-Cookie", b)
        self.assertEqual(b["X-Content-Type-Options"], "nosniff")
        # yanlış anahtarlarla toplu deneme hız sınırlanır
        portal.HIZ.clear()
        kodlar = [api_istek(self.port, "GET", "/api/v1/ben", anahtar=f"mdl_yanlis{i}")[0] for i in range(35)]
        self.assertIn(429, kodlar)

    def test_10_eski_veritabani_gecisi(self):
        import sqlite3
        yol = os.path.join(tempfile.mkdtemp(), "eski5.db")
        c = sqlite3.connect(yol)
        c.executescript("CREATE TABLE kullanicilar(id INTEGER PRIMARY KEY, eposta TEXT UNIQUE NOT NULL, ad TEXT NOT NULL, parola TEXT NOT NULL, rol TEXT NOT NULL DEFAULT 'kullanici', olusturma INTEGER NOT NULL);"
                        "CREATE TABLE basvurular(id INTEGER PRIMARY KEY, kullanici_id INTEGER UNIQUE NOT NULL, slug TEXT UNIQUE NOT NULL, ad TEXT NOT NULL, kisa TEXT NOT NULL, ayrinti TEXT NOT NULL DEFAULT '', baglanti TEXT NOT NULL DEFAULT '', adres TEXT NOT NULL DEFAULT '', iletisim TEXT NOT NULL, durum TEXT NOT NULL DEFAULT 'beklemede', yonetici_notu TEXT NOT NULL DEFAULT '', olusturma INTEGER NOT NULL, guncelleme INTEGER NOT NULL, karar_tarihi INTEGER);")
        c.close()
        yeni = portal.db_ac(yol)
        kol = [r["name"] for r in yeni.execute("PRAGMA table_info(basvurular)")]
        for k in ("adres_dogrulandi", "dogrulama_token", "nabiz_zaman", "nabiz_json"):
            self.assertIn(k, kol)
        self.assertTrue(yeni.execute("SELECT 1 FROM sqlite_master WHERE name='api_anahtarlari'").fetchone())
        self.assertTrue(yeni.execute("SELECT 1 FROM sqlite_master WHERE type='trigger' AND name='tr_adres_degisti'").fetchone())
        yeni.close()


if __name__ == "__main__":
    unittest.main()
