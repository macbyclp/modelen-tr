"""Örnek koordinatör ve Python API istemcisi testleri (dokümantasyondaki kodun çalıştığını kanıtlar).
Çalıştırma (istemci/ornekler/ klasöründe): py -3 -W ignore -m unittest test_ornekler"""
import array
import hashlib
import json
import os
import struct
import sys
import tempfile
import threading
import time
import unittest
import urllib.request

AD = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AD)
sys.path.insert(0, os.path.dirname(AD))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(AD)), "portal"))

import api  # noqa: E402
import minimal_koordinator as mk  # noqa: E402
import modelen_api  # noqa: E402
import portal  # noqa: E402
import uyum_testi  # noqa: E402


def adaptor(deger=0.0, adlar=("a.lora_A.default.weight", "a.lora_B.default.weight"), sekil=(2, 3)):
    t = {a: array.array("f", [deger + i * 0.5 for i in range(sekil[0] * sekil[1])]) for a in adlar}
    return mk.st_yaz({a: list(sekil) for a in adlar}, t), t


def post(url, yol, veri):
    r = urllib.request.Request(url + yol, data=veri, method="POST", headers={"Content-Type": "application/octet-stream"})
    try:
        with urllib.request.urlopen(r, timeout=10) as y:
            return y.status, json.loads(y.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def get(url, yol):
    with urllib.request.urlopen(url + yol, timeout=10) as y:
        return y.status, dict(y.getheaders()), y.read()


class MinimalKoordinator(unittest.TestCase):
    def setUp(self):
        self.bayt, _ = adaptor(1.0)
        self.srv, self.d = mk.sunucu_olustur(self.bayt, "127.0.0.1", 0, tur=2, en_az=2)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"

    def tearDown(self):
        self.srv.shutdown()

    def test_uyum_testinden_gecer(self):
        r = uyum_testi.calistir(self.url)
        self.assertTrue(r.basarili, r.satirlar)
        d = {x["madde"]: x["durum"] for x in r.satirlar}
        self.assertEqual((d["/bilgi"], d["/durum"], d["/gorev"], d["/agirlik sha256"], d["/agirlik safetensors"]), ("PASS",) * 5)

    def test_tam_tur_dongusu_ve_dogrulamalar(self):
        # iki işçi görev alır
        _, _, g1 = get(self.url, "/gorev?isci=a")
        _, _, g2 = get(self.url, "/gorev?isci=b")
        g1, g2 = json.loads(g1), json.loads(g2)
        self.assertEqual((g1["tur"], g1["parca"], g2["parca"], g1["agirlik_sha256"]), (0, 0, 1, self.d.sha))
        # ağırlık indirilir, sha doğrulanır
        _, b, veri = get(self.url, "/agirlik")
        self.assertEqual((b["X-Tur"], b["X-Sha256"], hashlib.sha256(veri).hexdigest()), ("0", self.d.sha, self.d.sha))
        # geçersiz yüklemeler
        self.assertEqual(post(self.url, "/sonuc?isci=a&tur=0", b"bozuk")[0], 400)
        yanlis_ad, _ = adaptor(0, adlar=("baska.lora_A.default.weight", "baska.lora_B.default.weight"))
        self.assertEqual(post(self.url, "/sonuc?isci=a&tur=0", yanlis_ad)[0], 422)  # anahtar kümesi
        self.assertEqual(post(self.url, "/sonuc?isci=a&tur=0", adaptor(0, sekil=(3, 3))[0])[0], 422)  # şekil
        nan, _ = adaptor(float("nan"))
        self.assertEqual(post(self.url, "/sonuc?isci=a&tur=0", nan)[0], 422)  # NaN
        self.assertEqual(post(self.url, "/sonuc?isci=a&tur=5", adaptor(0)[0])[0], 409)  # eski/yanlış tur
        # geçerli iki sonuç → ortalama alınır, tur 1 olur
        self.assertEqual(post(self.url, "/sonuc?isci=a&tur=0", adaptor(2.0)[0])[0], 200)
        self.assertEqual(post(self.url, "/sonuc?isci=a&tur=0", adaptor(2.0)[0])[0], 409)  # aynı işçi aynı turda bir kez
        self.assertEqual(json.loads(get(self.url, "/gorev?isci=a")[2]), {"bekle": True, "tur": 0})
        self.assertEqual(post(self.url, "/sonuc?isci=b&tur=0", adaptor(4.0)[0])[0], 200)
        _, b, veri = get(self.url, "/agirlik")
        self.assertEqual(b["X-Tur"], "1")
        _, t = mk.st_oku(veri)
        self.assertEqual(list(t["a.lora_A.default.weight"])[:3], [3.0, 3.5, 4.0])  # (2+4)/2 + i*0.5
        self.assertEqual(hashlib.sha256(veri).hexdigest(), b["X-Sha256"])
        # ikinci tur ve bitiş
        post(self.url, "/sonuc?isci=a&tur=1", adaptor(1.0)[0])
        post(self.url, "/sonuc?isci=b&tur=1", adaptor(1.0)[0])
        self.assertEqual(json.loads(get(self.url, "/gorev?isci=a")[2]), {"bitti": True})
        self.assertEqual(post(self.url, "/sonuc?isci=a&tur=2", adaptor(1.0)[0])[0], 409)
        self.assertEqual(json.loads(get(self.url, "/durum")[2])["tur"], 2)


class ApiIstemcisi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sunucu = portal.sunucu_kur(os.path.join(tempfile.mkdtemp(), "o.db"), "127.0.0.1", 0)
        cls.port = cls.sunucu.server_address[1]
        threading.Thread(target=cls.sunucu.serve_forever, daemon=True).start()
        kid = portal.yurut("INSERT INTO kullanicilar(eposta,ad,parola,olusturma,eposta_dogrulandi) VALUES(?,?,?,?,1)", "ornek@ornek.org", "Örnek", portal.parola_ozet("parola-123456"), int(time.time())).lastrowid
        cls.anahtar = api.anahtar_olustur(kid, "test")[1]
        cls.api = modelen_api.ModelenApi(cls.anahtar, f"http://127.0.0.1:{cls.port}/api/v1")

    @classmethod
    def tearDownClass(cls):
        cls.sunucu.shutdown()

    def test_istemci_akisi(self):
        a = self.api
        self.assertEqual(a.saglik()["durum"], "tamam")
        self.assertEqual(modelen_api.ModelenApi("", a.taban).koordinatorler(), [])
        self.assertEqual(a.ben()["eposta"], "ornek@ornek.org")
        with self.assertRaises(modelen_api.ApiHatasi) as h:
            a.koordinator()
        self.assertEqual(h.exception.kod, "basvuru_yok")
        k = a.basvur(ad="Örnek Lab", kisa="Python istemcisiyle oluşturulan başvuru", adres="https://koord.ornek.example")
        self.assertEqual((k["slug"], k["durum"]), ("ornek-lab", "beklemede"))
        self.assertEqual(a.guncelle(hf="https://huggingface.co/ornek")["hf"], "https://huggingface.co/ornek")
        with self.assertRaises(modelen_api.ApiHatasi) as h:
            a.nabiz("calisiyor")
        self.assertEqual(h.exception.kod, "onayli_degil")
        portal.yurut("UPDATE basvurular SET durum='onaylandi' WHERE slug='ornek-lab'")  # yönetici onayı
        # nabız döngüsü: sahte koordinatörü yoklar
        srv, d = mk.sunucu_olustur(adaptor(1.0)[0], "127.0.0.1", 0, tur=4, en_az=2)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            get(f"http://127.0.0.1:{srv.server_address[1]}", "/gorev?isci=x")
            modelen_api.nabiz_dongusu(a, f"http://127.0.0.1:{srv.server_address[1]}", once=True)
        finally:
            srv.shutdown()
        n = modelen_api.ModelenApi("", a.taban)._istek("GET", "/koordinatorler/ornek-lab")["nabiz"]
        self.assertEqual((n["durum"], n["tur"], n["toplam_tur"], n["aktif_isci"]), ("cevrimici", 0, 4, 1))
        # koordinatöre ulaşılamazsa "durdu"
        portal.HIZ.clear()
        modelen_api.nabiz_dongusu(a, "http://127.0.0.1:1", once=True)
        self.assertEqual(modelen_api.ModelenApi("", a.taban)._istek("GET", "/koordinatorler/ornek-lab")["nabiz"]["durum"], "durdu")
        # adres doğrulama
        t = a.adres_dogrulama_baslat()
        self.assertEqual(t["dosya"], "https://koord.ornek.example/.well-known/modelen-dogrulama.txt")
        api.GETIR = lambda url: t["icerik"]
        try:
            self.assertTrue(a.adres_dogrulama_kontrol()["adres_dogrulandi"])
        finally:
            api.GETIR = api.guvenli_getir
        # CLI
        self.assertEqual(modelen_api.main(["liste", "--taban", a.taban]), 0)
        with self.assertRaises(SystemExit):
            modelen_api.main(["ben", "--taban", a.taban])  # anahtar yok (ortam değişkeni boş): 401


if __name__ == "__main__":
    unittest.main()
