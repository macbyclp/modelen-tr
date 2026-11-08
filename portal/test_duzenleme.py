"""Onaylı profil düzenleme (onaya düşer, yayındaki sayfa onaya kadar değişmez). Çalıştırma: portal/ klasöründe py -3 -m unittest test_duzenleme"""
import json
import os
import re
import tempfile
import threading
import unittest

import portal
from test_gorsel import bytes_get, multipart, png
from test_portal import Oturum


class Duzenleme(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sunucu = portal.sunucu_kur(os.path.join(tempfile.mkdtemp(), "d.db"), "127.0.0.1", 0)
        cls.port = cls.sunucu.server_address[1]
        threading.Thread(target=cls.sunucu.serve_forever, daemon=True).start()
        portal.yonetici_olustur("admin@ornek.org", "Yönetici", "yonetici-parola-1")

    @classmethod
    def tearDownClass(cls):
        cls.sunucu.shutdown()

    def setUp(self):
        portal.HIZ.clear()

    def yonetici(self):
        a = Oturum(self.port)
        a.get("/giris")
        a.post("/giris", eposta="admin@ornek.org", parola="yonetici-parola-1")
        return a

    def onayli_kullanici(self, eposta, ad):
        o = Oturum(self.port)
        o.get("/kayit")
        o.post("/kayit", ad="Kişi", eposta=eposta, parola="parola-123456", parola2="parola-123456", kabul="1")
        multipart(o, "/basvuru", self.alanlar(o, ad=ad, kisa="İlk yayın özeti burada yazıyor", ayrinti="ilk ayrıntı"), [("ilk.png", png())])
        adm = self.yonetici()
        kimlik = re.search(rf'/yonetim/basvuru/(\d+)">{re.escape(ad)}', adm.get("/yonetim")[1]).group(1)
        adm.post("/yonetim/karar", id=kimlik, karar="onaylandi")
        return o, adm, kimlik

    def alanlar(self, o, **ek):
        a = dict(ad="X", kisa="Yeterince uzun bir özet yazısı", ayrinti="", baglanti="", adres="", iletisim="", hf="", csrf=o.cerez["mc"])
        a.update(ek)
        return a

    def test_1_duzenleme_onaya_duser_yayin_degismez_onayla(self):
        o, adm, kimlik = self.onayli_kullanici("d1@ornek.org", "Duzen Bir")
        anon = Oturum(self.port)
        ilk_gorsel = portal.tek("SELECT id FROM gorseller ORDER BY id DESC LIMIT 1")["id"]
        self.assertIn("Duzen Bir", anon.get("/koordinatorler")[1])
        # panelde düzenleme formu var
        self.assertIn("Düzenlemeyi incelemeye gönder", o.get("/panel?s=basvuru")[1])
        # düzenleme gönder: yeni ad, yeni özet, HF bağlantısı ve yeni görsel
        d, _, _ = multipart(o, "/basvuru", self.alanlar(o, ad="Duzen Bir Yeni", kisa="Güncellenmiş özet burada yer alıyor", ayrinti="yeni ayrıntı",
                                                          hf="https://huggingface.co/yeni-org"), [("yeni.png", png(2, 2))])
        self.assertEqual(d, 303)
        # yayın DEĞİŞMEDİ; durum hâlâ onaylı; yeni görsel herkese kapalı
        h = anon.get("/koordinator/duzen-bir")[1]
        self.assertIn("Duzen Bir", h)
        self.assertNotIn("Yeni", h)
        self.assertNotIn("yeni-org", h)
        yeni_gorsel = portal.tek("SELECT id FROM gorseller WHERE onayli=0")["id"]
        self.assertEqual(bytes_get(anon, f"/gorsel/{yeni_gorsel}")[0], 404)
        self.assertEqual(bytes_get(o, f"/gorsel/{yeni_gorsel}")[0], 200)   # sahibi görür
        self.assertEqual(bytes_get(adm, f"/gorsel/{yeni_gorsel}")[0], 200)  # yönetici görür
        self.assertEqual(bytes_get(anon, f"/gorsel/{ilk_gorsel}")[0], 200)  # eski onaylı görsel yayında
        self.assertIn("Düzenlemeniz incelemede", o.get("/panel")[1])
        # yönetici: bekleyen düzenleme sekmesi ve fark tablosu
        self.assertIn("Düzenleme bekleyen (1)", adm.get("/yonetim")[1])
        self.assertIn("düzenleme bekliyor", adm.get("/yonetim?durum=duzenleme")[1])
        h = adm.get(f"/yonetim/basvuru/{kimlik}")[1]
        self.assertIn("Bekleyen düzenleme", h)
        self.assertIn("Duzen Bir Yeni", h)
        self.assertIn("Düzenlemeyi onayla", h)
        # onayla → yayına girer
        adm.post("/yonetim/karar", id=kimlik, karar="duzenleme-onayla", **{"not": "Teşekkürler"})
        h = anon.get("/koordinator/duzen-bir")[1]  # slug sabit kalır
        self.assertIn("Duzen Bir Yeni", h)
        self.assertIn("Güncellenmiş özet", h)
        self.assertIn('href="https://huggingface.co/yeni-org"', h)
        self.assertEqual(bytes_get(anon, f"/gorsel/{yeni_gorsel}")[0], 200)
        self.assertEqual(portal.tek("SELECT taslak, durum FROM basvurular WHERE id=?", int(kimlik))["taslak"], "")
        self.assertIn("Teşekkürler", o.get("/panel")[1])

    def test_2_duzenleme_reddi_yayini_ve_eski_gorselleri_korur(self):
        o, adm, kimlik = self.onayli_kullanici("d2@ornek.org", "Duzen Iki")
        multipart(o, "/basvuru", self.alanlar(o, ad="Kötü Ad", kisa="Reddedilecek düzenleme özeti yazısı"), [("kotu.png", png(3, 3))])
        self.assertEqual(portal.tek("SELECT COUNT(*) n FROM gorseller WHERE onayli=0")["n"], 1)
        adm.post("/yonetim/karar", id=kimlik, karar="duzenleme-reddet", **{"not": "Uygun değil"})
        anon = Oturum(self.port)
        h = anon.get("/koordinator/duzen-iki")[1]
        self.assertIn("Duzen Iki", h)
        self.assertNotIn("Kötü Ad", h)
        self.assertEqual(portal.tek("SELECT COUNT(*) n FROM gorseller WHERE onayli=0")["n"], 0)  # bekleyen görsel silindi
        self.assertEqual(portal.tek("SELECT COUNT(*) n FROM gorseller WHERE basvuru_id=?", int(kimlik))["n"], 1)  # eski görsel duruyor
        self.assertEqual(portal.tek("SELECT taslak FROM basvurular WHERE id=?", int(kimlik))["taslak"], "")
        self.assertIn("Uygun değil", o.get("/panel")[1])

    def test_3_yeniden_gonderim_taslagin_yerine_gecer_dogrulama_ve_askida(self):
        o, adm, kimlik = self.onayli_kullanici("d3@ornek.org", "Duzen Uc")
        multipart(o, "/basvuru", self.alanlar(o, ad="Birinci Taslak", kisa="Birinci taslak özet yazısı yazıldı"))
        multipart(o, "/basvuru", self.alanlar(o, ad="Ikinci Taslak", kisa="İkinci taslak özet yazısı yazıldı"))
        t = json.loads(portal.tek("SELECT taslak FROM basvurular WHERE id=?", int(kimlik))["taslak"])
        self.assertEqual(t["ad"], "Ikinci Taslak")
        # geçersiz düzenleme (http adres) taslağı bozmaz
        d, h, _ = multipart(o, "/basvuru", self.alanlar(o, ad="Kötü", adres="http://x.org"))
        self.assertIn("https://", h)
        self.assertEqual(json.loads(portal.tek("SELECT taslak FROM basvurular WHERE id=?", int(kimlik))["taslak"])["ad"], "Ikinci Taslak")
        # yayındaki sayfa hâlâ ilk hâlinde
        self.assertIn("Duzen Uc", Oturum(self.port).get("/koordinator/duzen-uc")[1])
        # askıya alınınca düzenleme yapılamaz
        adm.post("/yonetim/karar", id=kimlik, karar="askida")
        d, h, _ = multipart(o, "/basvuru", self.alanlar(o, ad="Askida Deneme"))
        self.assertIn("askıda", h)
        self.assertEqual(Oturum(self.port).get("/koordinator/duzen-uc")[0], 404)  # askıdaki sayfa yayında değil

    def test_4_eski_veritabani_taslak_ve_onayli_sutunlari(self):
        import sqlite3
        yol = os.path.join(tempfile.mkdtemp(), "eski2.db")
        c = sqlite3.connect(yol)
        c.executescript("CREATE TABLE kullanicilar(id INTEGER PRIMARY KEY, eposta TEXT UNIQUE NOT NULL, ad TEXT NOT NULL, parola TEXT NOT NULL, rol TEXT NOT NULL DEFAULT 'kullanici', olusturma INTEGER NOT NULL);"
                        "CREATE TABLE basvurular(id INTEGER PRIMARY KEY, kullanici_id INTEGER UNIQUE NOT NULL, slug TEXT UNIQUE NOT NULL, ad TEXT NOT NULL, kisa TEXT NOT NULL, ayrinti TEXT NOT NULL DEFAULT '', baglanti TEXT NOT NULL DEFAULT '', adres TEXT NOT NULL DEFAULT '', iletisim TEXT NOT NULL, durum TEXT NOT NULL DEFAULT 'beklemede', yonetici_notu TEXT NOT NULL DEFAULT '', olusturma INTEGER NOT NULL, guncelleme INTEGER NOT NULL, karar_tarihi INTEGER, hf TEXT NOT NULL DEFAULT '');"
                        "CREATE TABLE gorseller(id INTEGER PRIMARY KEY, basvuru_id INTEGER NOT NULL, tur TEXT NOT NULL, veri BLOB NOT NULL, genislik INTEGER NOT NULL, yukseklik INTEGER NOT NULL, olusturma INTEGER NOT NULL);"
                        "INSERT INTO gorseller VALUES(1,1,'png',x'00',1,1,0);")
        c.close()
        yeni = portal.db_ac(yol)
        self.assertIn("taslak", [r["name"] for r in yeni.execute("PRAGMA table_info(basvurular)")])
        self.assertEqual(yeni.execute("SELECT onayli FROM gorseller WHERE id=1").fetchone()["onayli"], 1)  # eski görseller yayında kalır
        yeni.close()


if __name__ == "__main__":
    unittest.main()
