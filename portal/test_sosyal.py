"""Profil, sosyal bağlantılar, takip, akış, engel, şikayet ve moderasyon testleri.
Çalıştırma (portal/ klasöründe): py -3 -W ignore -m unittest test_sosyal"""
import http.client
import os
import re
import sqlite3
import tempfile
import threading
import unittest

import portal
from test_gorsel import bytes_get, png
from test_portal import Oturum


def mp_avatar(o, yol, alanlar, dosya=None):
    sinir = "----SosyalTest9c1"
    govde = b""
    for k, v in alanlar.items():
        govde += f'--{sinir}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode("utf-8")
    if dosya is not None:
        govde += f'--{sinir}\r\nContent-Disposition: form-data; name="avatar"; filename="a.png"\r\nContent-Type: image/png\r\n\r\n'.encode() + dosya + b"\r\n"
    govde += f"--{sinir}--\r\n".encode()
    c = http.client.HTTPConnection("127.0.0.1", o.port, timeout=20)
    c.request("POST", yol, govde, {"Cookie": "; ".join(f"{k}={v}" for k, v in o.cerez.items()), "Content-Type": f"multipart/form-data; boundary={sinir}"})
    r = c.getresponse()
    return r.status, r.read().decode("utf-8", errors="replace"), dict(r.getheaders())


class Sosyal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sunucu = portal.sunucu_kur(os.path.join(tempfile.mkdtemp(), "s.db"), "127.0.0.1", 0)
        cls.port = cls.sunucu.server_address[1]
        threading.Thread(target=cls.sunucu.serve_forever, daemon=True).start()
        portal.yonetici_olustur("admin@ornek.org", "Yönetici", "yonetici-parola-1")

    @classmethod
    def tearDownClass(cls):
        cls.sunucu.shutdown()

    def setUp(self):
        portal.HIZ.clear()

    # ---- yardımcılar
    def kullanici(self, eposta, adi=None, acik=True, ad="Kişi"):
        o = Oturum(self.port)
        o.get("/kayit")
        o.post("/kayit", ad=ad, eposta=eposta, parola="parola-123456", parola2="parola-123456", kabul="1")
        if adi:
            alan = dict(ad=ad, kullanici_adi=adi, biyografi=f"{adi} hakkında", csrf=o.cerez["mc"])
            if acik:
                alan["herkese_acik"] = "1"
            self.assertEqual(mp_avatar(o, "/profil", alan)[0], 303)
        return o

    def yonetici(self):
        a = Oturum(self.port)
        a.get("/giris")
        a.post("/giris", eposta="admin@ornek.org", parola="yonetici-parola-1")
        return a

    def uid(self, eposta):
        return portal.tek("SELECT id FROM kullanicilar WHERE eposta=?", eposta)["id"]

    # ---- testler
    def test_01_profil_varsayilan_gizli_acinca_gorunur_eposta_sizmaz(self):
        o = self.kullanici("p1@ornek.org", "profil_bir", acik=False, ad="Profil Bir")
        anon = Oturum(self.port)
        self.assertEqual(anon.get("/u/profil_bir")[0], 404)  # gizli
        d, h, _ = o.get("/u/profil_bir")
        self.assertEqual(d, 200)
        self.assertIn("gizli", h)
        self.assertEqual(self.yonetici().get("/u/profil_bir")[0], 200)
        self.assertEqual(anon.get("/u/yok_boyle_biri")[0], 404)
        # herkese aç + fotoğraf
        mp_avatar(o, "/profil", dict(ad="Profil Bir", kullanici_adi="profil_bir", biyografi="Merhaba <b>dünya</b>", herkese_acik="1", csrf=o.cerez["mc"]), png(2, 2, b"txt"))
        d, h, _ = anon.get("/u/profil_bir")
        self.assertEqual(d, 200)
        self.assertIn("Profil Bir", h)
        self.assertIn("Merhaba &lt;b&gt;dünya&lt;/b&gt;", h)  # bio kaçışlı
        self.assertNotIn("p1@ornek.org", h)  # e-posta sızmaz
        uid = self.uid("p1@ornek.org")
        d, veri, bas = bytes_get(anon, f"/avatar/{uid}")
        self.assertEqual((d, bas["Content-Type"]), (200, "image/png"))
        self.assertNotIn(b"GPS-SECRET", veri)
        # tekrar gizle → fotoğraf da kapanır
        mp_avatar(o, "/profil", dict(ad="Profil Bir", kullanici_adi="profil_bir", biyografi="x", csrf=o.cerez["mc"]))
        self.assertEqual(anon.get("/u/profil_bir")[0], 404)
        self.assertEqual(bytes_get(anon, f"/avatar/{uid}")[0], 404)
        self.assertEqual(bytes_get(o, f"/avatar/{uid}")[0], 200)

    def test_02_profil_dogrulamalari(self):
        o = self.kullanici("p2@ornek.org")
        def dene(**ek):
            a = dict(ad="Kişi", kullanici_adi="", biyografi="", csrf=o.cerez["mc"])
            a.update(ek)
            return mp_avatar(o, "/profil", a, ek.pop("_dosya", None))
        self.assertIn("3-20", dene(kullanici_adi="ab")[1])
        self.assertIn("3-20", dene(kullanici_adi="BÜYÜK harf")[1])
        self.assertIn("ayrılmış", dene(kullanici_adi="admin")[1])
        self.assertIn("kullanıcı adı gerekli", dene(herkese_acik="1")[1])
        self.assertIn("280", dene(biyografi="x" * 281)[1])
        self.assertIn("2-60", dene(ad="K")[1])
        self.kullanici("p2b@ornek.org", "alinmis_ad")
        self.assertIn("alınmış", dene(kullanici_adi="alinmis_ad")[1])
        self.assertIn("Yalnızca PNG", mp_avatar(o, "/profil", dict(ad="Kişi", csrf=o.cerez["mc"]), b'<svg onload="x"/>')[1])
        self.assertIn("1 MB", mp_avatar(o, "/profil", dict(ad="Kişi", csrf=o.cerez["mc"]), png() + b"\0" * 1_100_000)[1])
        self.assertEqual(dene(kullanici_adi="gecerli_ad_2")[0], 303)

    def test_03_sosyal_baglantilar(self):
        o = self.kullanici("p3@ornek.org", "baglanti3")
        ekle = lambda ag, url: o.post("/baglanti-ekle", ag=ag, url=url)
        self.assertEqual(ekle("x", "https://x.com/modelen_tr")[0], 303)
        self.assertEqual(ekle("github", "https://github.com/macbyclp/modelen")[0], 303)
        self.assertIn("geçerli", ekle("x", "https://kotu.example/modelen")[1])           # yanlış alan adı
        self.assertIn("geçerli", ekle("github", "http://github.com/x")[1])               # http değil
        self.assertIn("geçerli", ekle("linkedin", "https://linkedin.com/in/x\" onclick=\"y")[1])  # enjeksiyon
        self.assertIn("zaten", ekle("x", "https://x.com/baska")[1])                      # ağ başına bir
        self.assertEqual(ekle("web", "https://ornek.org/ben")[0], 303)
        self.assertEqual(ekle("web", "https://ornek.com")[0], 303)
        self.assertIn("En çok 2", ekle("web", "https://ucuncu.org")[1])
        self.assertEqual(ekle("huggingface", "https://huggingface.co/modelen")[0], 303)
        h = Oturum(self.port).get("/u/baglanti3")[1]
        self.assertIn('href="https://x.com/modelen_tr"', h)
        self.assertIn('rel="noopener nofollow noreferrer ugc"', h)
        self.assertIn("Hugging Face", h)
        bid = portal.tek("SELECT id FROM baglantilar WHERE ag='github'")["id"]
        o.post("/baglanti-sil", id=str(bid))
        self.assertNotIn("github.com", Oturum(self.port).get("/u/baglanti3")[1])
        # başkası silemez
        b = self.kullanici("p3b@ornek.org", "baglanti3b")
        xid = portal.tek("SELECT id FROM baglantilar WHERE ag='x'")["id"]
        b.post("/baglanti-sil", id=str(xid))
        self.assertIsNotNone(portal.tek("SELECT 1 FROM baglantilar WHERE id=?", xid))

    def test_04_gonderi_akis_ve_sinirlar(self):
        gizli = self.kullanici("g0@ornek.org", "gizli_yazar", acik=False)
        self.assertIn("herkese açın", gizli.post("/gonderi", metin="olmaz")[1])
        o = self.kullanici("g1@ornek.org", "yazar_bir", ad="Yazar Bir")
        self.assertEqual(o.post("/gonderi", metin="İlk gönderi <script>alert(1)</script>\nikinci satır")[0], 303)
        anon = Oturum(self.port)
        h = anon.get("/akis")[1]
        self.assertIn("İlk gönderi &lt;script&gt;alert(1)&lt;/script&gt;<br>ikinci satır", h)
        self.assertNotIn("<script>alert", h)
        self.assertIn("Yazar Bir", anon.get("/u/yazar_bir")[1])
        self.assertIn("Aynı gönderiyi", o.post("/gonderi", metin="İlk gönderi <script>alert(1)</script>\nikinci satır")[1])
        self.assertIn("boş olamaz", o.post("/gonderi", metin="   \n ")[1])
        self.assertIn("500", o.post("/gonderi", metin="x" * 501)[1])
        for i in range(9):
            o.post("/gonderi", metin=f"gönderi {i}")
        self.assertIn("Çok sık", o.post("/gonderi", metin="fazla")[1])   # saatte 10
        # gizli profil gönderisi akışta yok; girişsiz POST yönlendirilir
        self.assertNotIn("olmaz", h)
        anon2 = Oturum(self.port)
        anon2.get("/giris")
        self.assertEqual(anon2.post("/gonderi", metin="x")[0], 303)  # girişsiz: giriş sayfasına yönlenir
        # kendi gönderisini siler, başkası silemez
        gid = portal.tek("SELECT id FROM gonderiler WHERE metin='gönderi 0'")["id"]
        baska = self.kullanici("g2@ornek.org", "yazar_iki")
        baska.post("/gonderi-sil", id=str(gid))
        self.assertIsNotNone(portal.tek("SELECT 1 FROM gonderiler WHERE id=?", gid))
        o.post("/gonderi-sil", id=str(gid))
        self.assertIsNone(portal.tek("SELECT 1 FROM gonderiler WHERE id=?", gid))

    def test_05_takip_ve_takip_akisi(self):
        a = self.kullanici("t1@ornek.org", "takipci_a")
        b = self.kullanici("t2@ornek.org", "takip_edilen_b")
        c = self.kullanici("t3@ornek.org", "yabanci_c")
        gizli = self.kullanici("t4@ornek.org", "gizli_d", acik=False)
        b.post("/gonderi", metin="Yazi B")
        c.post("/gonderi", metin="Yazi C")
        bid, did = self.uid("t2@ornek.org"), self.uid("t4@ornek.org")
        a.post("/takip", hedef=str(bid), islem="ekle")
        a.post("/takip", hedef=str(did), islem="ekle")  # gizli profil takip edilemez
        self.assertEqual(portal.tek("SELECT COUNT(*) n FROM takip WHERE takip_eden=?", self.uid("t1@ornek.org"))["n"], 1)
        h = a.get("/akis?takip=1")[1]
        self.assertIn("Yazi B", h)
        self.assertNotIn("Yazi C", h)
        self.assertIn("1</b> takipçi", Oturum(self.port).get("/u/takip_edilen_b")[1])
        self.assertIn("Takibi bırak", a.get("/u/takip_edilen_b")[1])
        a.post("/takip", hedef=str(bid), islem="birak")
        self.assertNotIn("Yazi B", a.get("/akis?takip=1")[1])
        # kendini takip edemez
        a.post("/takip", hedef=str(self.uid("t1@ornek.org")), islem="ekle")
        self.assertEqual(portal.tek("SELECT COUNT(*) n FROM takip WHERE takip_edilen=?", self.uid("t1@ornek.org"))["n"], 0)

    def test_06_engel(self):
        a = self.kullanici("e1@ornek.org", "engelleyen_a")
        b = self.kullanici("e2@ornek.org", "engellenen_b")
        a.post("/gonderi", metin="A yazdı")
        b.post("/gonderi", metin="B yazdı")
        aid, bid = self.uid("e1@ornek.org"), self.uid("e2@ornek.org")
        b.post("/takip", hedef=str(aid), islem="ekle")
        a.post("/engel", hedef=str(bid), islem="ekle")
        self.assertEqual(portal.tek("SELECT COUNT(*) n FROM takip WHERE takip_eden=?", bid)["n"], 0)  # takip koptu
        self.assertEqual(b.get("/u/engelleyen_a")[0], 404)                    # B artık A'yı göremez
        self.assertNotIn("A yazdı", b.get("/akis")[1])
        self.assertNotIn("B yazdı", a.get("/akis")[1])                       # A da Yazi Bni görmez
        b.post("/takip", hedef=str(aid), islem="ekle")
        self.assertEqual(portal.tek("SELECT COUNT(*) n FROM takip WHERE takip_edilen=?", aid)["n"], 0)
        self.assertIn("Engeli kaldır", a.get("/profil")[1])  # engellenenler listesinde
        a.post("/engel", hedef=str(bid), islem="kaldir")
        self.assertEqual(b.get("/u/engelleyen_a")[0], 200)
        self.assertIn("A yazdı", b.get("/akis")[1])

    def test_07_sikayet_ve_moderasyon(self):
        yazar = self.kullanici("m1@ornek.org", "kotu_yazar")
        izleyen = self.kullanici("m2@ornek.org", "izleyen_m")
        yazar.post("/gonderi", metin="Kurallara aykırı gönderi")
        gid = portal.tek("SELECT id FROM gonderiler WHERE metin='Kurallara aykırı gönderi'")["id"]
        izleyen.post("/sikayet", tur="gonderi", id=str(gid), neden="spam", aciklama="reklam")
        izleyen.post("/sikayet", tur="gonderi", id=str(gid), neden="taciz")           # aynı kişi ikinci kez: yok sayılır
        yazar.post("/sikayet", tur="gonderi", id=str(gid), neden="spam")              # kendi gönderisi: yok sayılır
        self.assertEqual(portal.tek("SELECT COUNT(*) n FROM sikayetler WHERE hedef_id=?", gid)["n"], 1)
        self.assertEqual(Oturum(self.port).istek("GET", "/yonetim/moderasyon")[0], 303)
        self.assertEqual(izleyen.get("/yonetim/moderasyon")[0], 403)                   # yönetici değil
        adm = self.yonetici()
        h = adm.get("/yonetim/moderasyon")[1]
        self.assertIn("Kurallara aykırı gönderi", h)
        self.assertIn("m1@ornek.org", h)                                              # yönetici e-postayı görür
        sid = re.search(r'name="id" value="(\d+)"', h).group(1)
        adm.post("/yonetim/moderasyon-karar", id=sid, karar="sustur")
        self.assertNotIn("Kurallara aykırı gönderi", Oturum(self.port).get("/akis")[1])   # gizlendi
        self.assertIn("kısıtlandı", yazar.post("/gonderi", metin="yeni")[1])              # susturuldu
        self.assertIn("kotu_yazar", adm.get("/yonetim/moderasyon")[1])                    # kısıtlı listesinde
        adm.post("/yonetim/kullanici-kisit", id=str(self.uid("m1@ornek.org")))
        self.assertEqual(yazar.post("/gonderi", metin="özür dilerim")[0], 303)
        # profil bildirimi → profil gizle
        izleyen.post("/sikayet", tur="profil", id=str(self.uid("m1@ornek.org")), neden="uygunsuz")
        sid = re.search(r'name="id" value="(\d+)"', adm.get("/yonetim/moderasyon")[1]).group(1)
        adm.post("/yonetim/moderasyon-karar", id=sid, karar="profil-gizle")
        self.assertEqual(Oturum(self.port).get("/u/kotu_yazar")[0], 404)
        d, h, _ = mp_avatar(yazar, "/profil", dict(ad="Kişi", kullanici_adi="kotu_yazar", herkese_acik="1", csrf=yazar.cerez["mc"]))
        self.assertIn("gizlendi", h)                                                  # kendi açamaz
        adm.post("/yonetim/kullanici-kisit", id=str(self.uid("m1@ornek.org")))
        self.assertEqual(mp_avatar(yazar, "/profil", dict(ad="Kişi", kullanici_adi="kotu_yazar", herkese_acik="1", csrf=yazar.cerez["mc"]))[0], 303)
        self.assertEqual(Oturum(self.port).get("/u/kotu_yazar")[0], 200)
        # yönetici akıştan doğrudan gizleyebilir; reddetme
        yazar.post("/gonderi", metin="ikinci gönderi")
        g2 = portal.tek("SELECT id FROM gonderiler WHERE metin='ikinci gönderi'")["id"]
        adm.post("/yonetim/gonderi-gizle", id=str(g2))
        self.assertNotIn("ikinci gönderi", Oturum(self.port).get("/akis")[1])
        self.assertEqual(izleyen.post("/yonetim/gonderi-gizle", id=str(g2))[0], 403)

    def test_08_hesap_silinince_sosyal_veri_gider(self):
        a = self.kullanici("s1@ornek.org", "silinecek_a")
        b = self.kullanici("s2@ornek.org", "izleyen_b")
        mp_avatar(a, "/profil", dict(ad="Kişi", kullanici_adi="silinecek_a", herkese_acik="1", csrf=a.cerez["mc"]), png())
        a.post("/baglanti-ekle", ag="x", url="https://x.com/silinecek")
        a.post("/gonderi", metin="silinecek gönderi")
        b.post("/takip", hedef=str(self.uid("s1@ornek.org")), islem="ekle")
        uid = self.uid("s1@ornek.org")
        a.post("/hesap-sil", parola="parola-123456")
        for tablo, kolon in (("avatarlar", "kullanici_id"), ("baglantilar", "kullanici_id"), ("gonderiler", "kullanici_id"), ("takip", "takip_edilen")):
            self.assertEqual(portal.tek(f"SELECT COUNT(*) n FROM {tablo} WHERE {kolon}=?", uid)["n"], 0, tablo)
        self.assertEqual(Oturum(self.port).get("/u/silinecek_a")[0], 404)

    def test_09_koordinator_sayfasinda_profil_baglantisi_ve_site_gezinmesi(self):
        o = self.kullanici("k1@ornek.org", "koord_profil")
        sinir = "----k"
        o.post("/basvuru", ad="Profil Lab", kisa="Profil bağlantısı gösteren koordinatör", ayrinti="", baglanti="", adres="", iletisim="", hf="")
        adm = self.yonetici()
        kimlik = re.search(r'/yonetim/basvuru/(\d+)">Profil Lab', adm.get("/yonetim")[1]).group(1)
        adm.post("/yonetim/karar", id=kimlik, karar="onaylandi")
        h = Oturum(self.port).get("/koordinator/profil-lab")[1]
        self.assertIn('href="/u/koord_profil"', h)
        anon = Oturum(self.port)
        self.assertIn('href="akis.html"', anon.get("/index.html")[1])             # menüde Akış
        d, h, _ = anon.get("/topluluk-kurallari.html")
        self.assertEqual(d, 200)
        self.assertIn("Topluluk kuralları", h)
        self.assertEqual(anon.get("/en/community-rules.html")[0], 200)
        self.assertEqual(anon.get("/akis.html")[0], 200)

    def test_10_csrf_ve_giris_gerekli(self):
        o = self.kullanici("c1@ornek.org", "csrf_kisi")
        for yol in ("/gonderi", "/takip", "/engel", "/sikayet", "/baglanti-ekle", "/avatar-sil", "/gonderi-sil", "/baglanti-sil"):
            self.assertEqual(o.istek("POST", yol, {"x": "1", "csrf": "yanlis"}, csrf_al=False)[0], 400, yol)
            self.assertEqual(Oturum(self.port).istek("POST", yol, {"x": "1", "csrf": "yanlis"}, csrf_al=False)[0], 400, yol)  # önce CSRF
        self.assertEqual(Oturum(self.port).get("/profil")[0], 303)

    def test_11_eski_veritabani_sosyal_gecisi(self):
        yol = os.path.join(tempfile.mkdtemp(), "eski3.db")
        c = sqlite3.connect(yol)
        c.executescript("CREATE TABLE kullanicilar(id INTEGER PRIMARY KEY, eposta TEXT UNIQUE NOT NULL, ad TEXT NOT NULL, parola TEXT NOT NULL, rol TEXT NOT NULL DEFAULT 'kullanici', olusturma INTEGER NOT NULL);"
                        "INSERT INTO kullanicilar(eposta,ad,parola,olusturma) VALUES('a@b.co','Eski','x',0);")
        c.close()
        yeni = portal.db_ac(yol)
        kol = [r["name"] for r in yeni.execute("PRAGMA table_info(kullanicilar)")]
        for k in ("kullanici_adi", "biyografi", "herkese_acik", "susturuldu", "zorla_gizli"):
            self.assertIn(k, kol)
        self.assertEqual(yeni.execute("SELECT herkese_acik FROM kullanicilar").fetchone()["herkese_acik"], 0)  # mevcut kullanıcılar gizli kalır
        tablolar = {r["name"] for r in yeni.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"avatarlar", "baglantilar", "takip", "engeller", "gonderiler", "sikayetler"} <= tablolar)
        yeni.close()


if __name__ == "__main__":
    unittest.main()
