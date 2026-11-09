"""Örnek koordinatör testleri (API istemcisinin portal ile uçtan uca testi web deposundadır) (dokümantasyondaki kodun çalıştığını kanıtlar).
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

import minimal_koordinator as mk  # noqa: E402
import modelen_api  # noqa: E402
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

class NabizAnahtari(unittest.TestCase):
    """Nabız betiği anahtar isteyen (kapalı) koordinatörde de çalışmalı; anahtar yoksa /bilgi'ye düşmeli."""

    @classmethod
    def setUpClass(cls):
        import http.server

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                if self.path == "/durum":
                    if self.headers.get("X-Anahtar") != "gizli":
                        self.send_response(401)
                        self.end_headers()
                        return
                    govde = json.dumps({"tur": 3, "toplam_tur": 9, "isciler": {"a": 1, "b": 2}}).encode()
                elif self.path == "/bilgi":
                    govde = json.dumps({"tur": 3, "toplam_tur": 9}).encode()
                else:
                    self.send_response(404)
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Length", str(len(govde)))
                self.end_headers()
                self.wfile.write(govde)

        cls.sunucu = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        cls.url = f"http://127.0.0.1:{cls.sunucu.server_address[1]}"
        threading.Thread(target=cls.sunucu.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.sunucu.shutdown()

    def test_dogru_anahtarla_isci_sayisi_gelir(self):
        self.assertEqual(modelen_api.koordinator_durumu(self.url, anahtar="gizli"), {"tur": 3, "toplam_tur": 9, "aktif_isci": 2})

    def test_ortam_degiskeninden_anahtar(self):
        os.environ["MODELEN_ANAHTAR"] = "gizli"
        try:
            self.assertEqual(modelen_api.koordinator_durumu(self.url)["aktif_isci"], 2)
        finally:
            os.environ.pop("MODELEN_ANAHTAR", None)

    def test_anahtar_yoksa_ya_da_yanlissa_bilgiye_duser(self):
        self.assertEqual(modelen_api.koordinator_durumu(self.url), {"tur": 3, "toplam_tur": 9})
        self.assertEqual(modelen_api.koordinator_durumu(self.url, anahtar="yanlis"), {"tur": 3, "toplam_tur": 9})

if __name__ == "__main__":
    unittest.main()
