"""Görsel yükleme, Hugging Face alanı ve metin sarma testleri. Çalıştırma: py -3 -m unittest test_gorsel (portal/ klasöründe)."""
import base64
import http.client
import os
import re
import struct
import tempfile
import threading
import unittest
import zlib

import gorsel
import portal
from test_portal import Oturum


def png(w=1, h=1, ekstra=b""):
    def parca(tip, veri):
        return struct.pack(">I", len(veri)) + tip + veri + struct.pack(">I", zlib.crc32(tip + veri) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + parca(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
            + (parca(b"tEXt", b"Comment\x00GPS-SECRET") if ekstra == b"txt" else b"")
            + parca(b"IDAT", zlib.compress(b"\x00\x00")) + parca(b"IEND", b""))


def jpeg():
    def seg(m, veri):
        return bytes([0xFF, m]) + struct.pack(">H", len(veri) + 2) + veri
    return (b"\xff\xd8" + seg(0xE0, b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00") + seg(0xE1, b"Exif\x00\x00GPS-SECRET-41.0N")
            + seg(0xFE, b"gizli yorum") + seg(0xC0, b"\x08\x00\x02\x00\x03\x01\x01\x11\x00") + seg(0xDA, b"\x01\x01\x00\x00\x3f\x00") + b"\x12\x34\xff\xd9")


WEBP_1x1 = base64.b64decode("UklGRhoAAABXRUJQVlA4TA0AAAAvAAAAEAcQERGIiP4HAA==")


def webp_exifli():
    vp8x = b"VP8X" + struct.pack("<I", 10) + bytes([0x08, 0, 0, 0]) + (0).to_bytes(3, "little") + (0).to_bytes(3, "little")
    vp8l = WEBP_1x1[12:]
    exif = b"EXIF" + struct.pack("<I", 12) + b"GPS-SECRET!!"
    icerik = b"WEBP" + vp8x + vp8l + exif
    return b"RIFF" + struct.pack("<I", len(icerik)) + icerik


class GorselBirim(unittest.TestCase):
    def test_png_ust_veri_silinir(self):
        tur, temiz, w, h = gorsel.temizle(png(ekstra=b"txt"))
        self.assertEqual((tur, w, h), ("png", 1, 1))
        self.assertNotIn(b"GPS-SECRET", temiz)
        self.assertIn(b"IDAT", temiz)
        self.assertTrue(temiz.endswith(b"IEND\xaeB`\x82"))

    def test_jpeg_exif_ve_yorum_silinir(self):
        tur, temiz, w, h = gorsel.temizle(jpeg())
        self.assertEqual((tur, w, h), ("jpeg", 3, 2))
        self.assertNotIn(b"GPS-SECRET", temiz)
        self.assertNotIn(b"gizli yorum", temiz)
        self.assertIn(b"JFIF", temiz)  # JFIF kalır
        self.assertTrue(temiz.endswith(b"\xff\xd9"))

    def test_webp_exif_silinir_bayrak_temizlenir(self):
        tur, temiz, w, h = gorsel.temizle(webp_exifli())
        self.assertEqual(tur, "webp")
        self.assertNotIn(b"GPS-SECRET", temiz)
        self.assertEqual(temiz[20], 0x00)  # VP8X bayrak baytı: EXIF biti temiz
        self.assertEqual(struct.unpack("<I", temiz[4:8])[0] + 8, len(temiz))  # RIFF boyutu tutarlı
        self.assertEqual(gorsel.temizle(WEBP_1x1)[0], "webp")

    def test_gecersiz_ve_tehlikeli_dosyalar_reddedilir(self):
        for kotu in (b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>', b"<html><script>1</script></html>", b"GIF89a\x01\x00\x01\x00", b"", b"rastgele metin" * 10,
                     png()[:30], b"\xff\xd8\xff" + b"\x00" * 10):
            with self.assertRaises(gorsel.GorselHatasi):
                gorsel.temizle(kotu)
        with self.assertRaises(gorsel.GorselHatasi):  # dev boyut
            gorsel.temizle(png(w=7000, h=7000))


def multipart(oturum, yol, alanlar, dosyalar=()):
    sinir = "----ModelenTestSiniri7f3a"
    govde = b""
    for k, v in alanlar.items():
        govde += f'--{sinir}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode("utf-8")
    for ad, veri in dosyalar:
        govde += f'--{sinir}\r\nContent-Disposition: form-data; name="gorsel"; filename="{ad}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode() + veri + b"\r\n"
    govde += f"--{sinir}--\r\n".encode()
    c = http.client.HTTPConnection("127.0.0.1", oturum.port, timeout=20)
    c.request("POST", yol, govde, {"Cookie": "; ".join(f"{k}={v}" for k, v in oturum.cerez.items()),
                                   "Content-Type": f"multipart/form-data; boundary={sinir}"})
    r = c.getresponse()
    veri = r.read().decode("utf-8", errors="replace")
    return r.status, veri, dict(r.getheaders())


def bytes_get(oturum, yol):
    c = http.client.HTTPConnection("127.0.0.1", oturum.port, timeout=20)
    c.request("GET", yol, headers={"Cookie": "; ".join(f"{k}={v}" for k, v in oturum.cerez.items())})
    r = c.getresponse()
    return r.status, r.read(), dict(r.getheaders())


class GorselAkis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sunucu = portal.sunucu_kur(os.path.join(tempfile.mkdtemp(), "g.db"), "127.0.0.1", 0)
        cls.port = cls.sunucu.server_address[1]
        threading.Thread(target=cls.sunucu.serve_forever, daemon=True).start()
        portal.yonetici_olustur("admin@ornek.org", "Yönetici", "yonetici-parola-1")

    @classmethod
    def tearDownClass(cls):
        cls.sunucu.shutdown()

    def setUp(self):
        portal.HIZ.clear()

    def kullanici(self, eposta):
        o = Oturum(self.port)
        o.get("/kayit")
        o.post("/kayit", ad="Foto", eposta=eposta, parola="parola-123456", parola2="parola-123456", kabul="1")
        return o

    def alanlar(self, **ek):
        a = dict(ad="Foto Lab", kisa="Fotoğraflı deneme başvurusu yazısı", ayrinti="x", baglanti="", adres="", iletisim="", hf="https://huggingface.co/foto-lab", csrf="")
        a.update(ek)
        return a

    def test_1_yukle_goruntule_onayla_sil(self):
        o = self.kullanici("foto@ornek.org")
        a = self.alanlar(csrf=o.cerez["mc"])
        d, h, _ = multipart(o, "/basvuru", a, [("a.png", png(ekstra=b"txt")), ("b.jpg", jpeg())])
        self.assertEqual(d, 303)
        satirlar = portal.sorgu("SELECT id, tur FROM gorseller ORDER BY id")
        self.assertEqual([r["tur"] for r in satirlar], ["png", "jpeg"])
        gid = satirlar[0]["id"]
        # onaysızken: anonim göremez, sahibi ve yönetici görür; konum bilgisi silinmiş
        anon = Oturum(self.port)
        self.assertEqual(bytes_get(anon, f"/gorsel/{gid}")[0], 404)
        d, veri, bas = bytes_get(o, f"/gorsel/{gid}")
        self.assertEqual((d, bas["Content-Type"]), (200, "image/png"))
        self.assertNotIn(b"GPS-SECRET", veri)
        self.assertEqual(bas["X-Content-Type-Options"], "nosniff")
        adm = Oturum(self.port)
        adm.get("/giris")
        adm.post("/giris", eposta="admin@ornek.org", parola="yonetici-parola-1")
        self.assertEqual(bytes_get(adm, f"/gorsel/{gid}")[0], 200)
        kimlik = re.search(r"/yonetim/basvuru/(\d+)", adm.get("/yonetim")[1]).group(1)
        h = adm.get(f"/yonetim/basvuru/{kimlik}")[1]
        self.assertIn(f"/gorsel/{gid}", h)  # yönetici görselleri ve HF bağlantısını görür
        self.assertIn("https://huggingface.co/foto-lab", h)
        adm.post("/yonetim/karar", id=kimlik, karar="onaylandi")
        # onaylı: herkese açık, ayrıntı sayfasında galeri + HF, listede kapak
        self.assertEqual(bytes_get(anon, f"/gorsel/{gid}")[0], 200)
        h = anon.get("/koordinator/foto-lab")[1]
        self.assertIn(f'src="/gorsel/{gid}"', h)
        self.assertIn('href="https://huggingface.co/foto-lab"', h)
        self.assertIn('class="kapak"', anon.get("/koordinatorler")[1])
        # sahibi kendi görselini onaylıyken de hemen kaldırabilir (kaldırmak güvenlidir)
        o.post("/gorsel-sil", id=str(gid))
        self.assertEqual(bytes_get(anon, f"/gorsel/{gid}")[0], 404)

    def test_2_silme_ve_sinirlar(self):
        o = self.kullanici("sinir@ornek.org")
        a = self.alanlar(ad="Sinir Lab", csrf=o.cerez["mc"])
        self.assertEqual(multipart(o, "/basvuru", a, [("1.png", png())])[0], 303)
        gid = portal.tek("SELECT id FROM gorseller ORDER BY id DESC LIMIT 1")["id"]
        o.post("/gorsel-sil", id=str(gid))  # beklemede: sahibi silebilir
        self.assertIsNone(portal.tek("SELECT 1 FROM gorseller WHERE id=?", gid))
        # 5 görsel: reddedilir, başvuru da kaydedilmez/güncellenmez
        onceki = portal.tek("SELECT COUNT(*) n FROM gorseller")["n"]
        d, h, _ = multipart(o, "/basvuru", self.alanlar(ad="Sinir Lab", csrf=o.cerez["mc"]), [(f"{i}.png", png()) for i in range(5)])
        self.assertIn("En çok 4", h)
        self.assertEqual(portal.tek("SELECT COUNT(*) n FROM gorseller")["n"], onceki)
        # metin dosyası png diye gelirse reddedilir
        d, h, _ = multipart(o, "/basvuru", self.alanlar(ad="Sinir Lab", csrf=o.cerez["mc"]), [("sahte.png", b"bu bir resim degil" * 20)])
        self.assertIn("Yalnızca PNG, JPEG ya da WebP", h)
        # SVG reddedilir
        d, h, _ = multipart(o, "/basvuru", self.alanlar(ad="Sinir Lab", csrf=o.cerez["mc"]), [("x.svg", b'<svg onload="alert(1)"></svg>')])
        self.assertIn("Yalnızca PNG", h)
        # 2 MB üstü
        d, h, _ = multipart(o, "/basvuru", self.alanlar(ad="Sinir Lab", csrf=o.cerez["mc"]), [("dev.png", png() + b"\x00" * 2_100_000)])
        self.assertIn("2 MB", h)
        # geçersiz Hugging Face bağlantısı
        d, h, _ = multipart(o, "/basvuru", self.alanlar(ad="Sinir Lab", hf="https://kotu.example/x", csrf=o.cerez["mc"]))
        self.assertIn("Hugging Face", h)
        # CSRF'siz multipart reddedilir
        d, _, _ = multipart(o, "/basvuru", self.alanlar(ad="Sinir Lab", csrf="yanlis"))
        self.assertEqual(d, 400)
        # girişsiz büyük gövde okunmadan yönlendirilir
        self.assertEqual(multipart(Oturum(self.port), "/basvuru", self.alanlar(), [("1.png", png())])[0], 303)

    def test_3_baskasinin_gorselini_silemez_hesap_silince_gider(self):
        a1, a2 = self.kullanici("bir@ornek.org"), self.kullanici("iki@ornek.org")
        multipart(a1, "/basvuru", self.alanlar(ad="Bir Lab", csrf=a1.cerez["mc"]), [("1.png", png())])
        gid = portal.tek("SELECT g.id FROM gorseller g JOIN basvurular b ON b.id=g.basvuru_id WHERE b.ad='Bir Lab'")["id"]
        a2.post("/gorsel-sil", id=str(gid))
        self.assertIsNotNone(portal.tek("SELECT 1 FROM gorseller WHERE id=?", gid))
        self.assertEqual(bytes_get(a2, f"/gorsel/{gid}")[0], 404)  # başkasının onaysız görseli görünmez
        a1.post("/hesap-sil", parola="parola-123456")
        self.assertIsNone(portal.tek("SELECT 1 FROM gorseller WHERE id=?", gid))  # hesapla birlikte silinir

    def test_4_uzun_metin_sarilir_css_ve_kaçış(self):
        css = open(os.path.join(portal.SITE, "assets", "style.css"), encoding="utf-8").read()
        self.assertIn("overflow-wrap: anywhere", css)
        self.assertIn("white-space: pre-wrap", css)
        o = self.kullanici("uzun@ornek.org")
        uzun = "A" * 3000 + "<script>x</script>"
        multipart(o, "/basvuru", self.alanlar(ad="Uzun Lab", ayrinti=uzun, csrf=o.cerez["mc"]))
        adm = Oturum(self.port)
        adm.get("/giris")
        adm.post("/giris", eposta="admin@ornek.org", parola="yonetici-parola-1")
        kimlik = re.search(r'/yonetim/basvuru/(\d+)">Uzun Lab', adm.get("/yonetim")[1]).group(1)
        adm.post("/yonetim/karar", id=kimlik, karar="onaylandi")
        h = Oturum(self.port).get("/koordinator/uzun-lab")[1]
        self.assertIn("&lt;script&gt;", h)
        self.assertNotIn("<script>x", h)

    def test_5_eski_veritabani_hf_sutunu_gecisi(self):
        import sqlite3
        yol = os.path.join(tempfile.mkdtemp(), "eski.db")
        c = sqlite3.connect(yol)
        c.executescript("CREATE TABLE kullanicilar(id INTEGER PRIMARY KEY, eposta TEXT UNIQUE NOT NULL, ad TEXT NOT NULL, parola TEXT NOT NULL, rol TEXT NOT NULL DEFAULT 'kullanici', olusturma INTEGER NOT NULL);"
                        "CREATE TABLE basvurular(id INTEGER PRIMARY KEY, kullanici_id INTEGER UNIQUE NOT NULL, slug TEXT UNIQUE NOT NULL, ad TEXT NOT NULL, kisa TEXT NOT NULL, ayrinti TEXT NOT NULL DEFAULT '', baglanti TEXT NOT NULL DEFAULT '', adres TEXT NOT NULL DEFAULT '', iletisim TEXT NOT NULL, durum TEXT NOT NULL DEFAULT 'beklemede', yonetici_notu TEXT NOT NULL DEFAULT '', olusturma INTEGER NOT NULL, guncelleme INTEGER NOT NULL, karar_tarihi INTEGER);")
        c.close()
        yeni = portal.db_ac(yol)
        self.assertIn("hf", [r["name"] for r in yeni.execute("PRAGMA table_info(basvurular)")])
        self.assertIn("gorseller", [r["name"] for r in yeni.execute("SELECT name FROM sqlite_master WHERE type='table'")])
        yeni.close()


if __name__ == "__main__":
    unittest.main()
