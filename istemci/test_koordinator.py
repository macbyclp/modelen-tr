"""Referans koordinatörün sertleştirme testleri (gerçek süreç, küçük sentetik adaptör; GPU/model gerekmez).

  .venv/Scripts/python.exe -m unittest istemci/test_koordinator.py      (torch + safetensors gerekir)
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request

import torch
from safetensors.torch import save as st_save

KOK = os.path.dirname(os.path.abspath(__file__))
KOORD = os.path.join(KOK, "koordinator.py")


def bos_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def adaptor(deger=0.0):
    t = {"a.lora_A.weight": torch.full((4, 8), float(deger)), "a.lora_B.weight": torch.full((8, 4), float(deger))}
    return st_save(t)


class Koordinator:
    def __init__(self, test, *ek, tur=3):
        self.dizin = tempfile.mkdtemp(prefix="modelen-kt-")
        test.addCleanup(shutil.rmtree, self.dizin, ignore_errors=True)
        self.baslangic = os.path.join(self.dizin, "tur-0.safetensors")
        open(self.baslangic, "wb").write(adaptor(0.0))
        self.calisma = os.path.join(self.dizin, "calisma")
        self.port = bos_port()
        self.tur, self.ek, self.p = tur, list(ek), None
        self.baslat()
        test.addCleanup(self.durdur)

    def baslat(self, *ek):
        self.p = subprocess.Popen([sys.executable, KOORD, "--baslangic", self.baslangic, "--port", str(self.port), "--tur", str(self.tur), "--en-az", "1",
                                   "--calisma", self.calisma, *self.ek, *ek], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                self.al("/bilgi")
                return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError("koordinatör açılmadı")

    def durdur(self):
        if self.p and self.p.poll() is None:
            self.p.terminate()
            self.p.wait(10)

    def istek(self, yol, veri=None, baslik=None):
        r = urllib.request.Request(f"http://127.0.0.1:{self.port}{yol}", data=veri, method="POST" if veri is not None else "GET", headers=baslik or {})
        try:
            with urllib.request.urlopen(r, timeout=20) as y:
                return y.status, y.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def al(self, yol, baslik=None):
        d, b = self.istek(yol, None, baslik)
        return json.loads(b) if b[:1] in (b"{", b"[") else b

    def durum(self):
        return self.al("/durum")

    def gonder(self, isci, tur, veri=None):
        return self.istek(f"/sonuc?isci={urllib.parse.quote(isci)}&tur={tur}", veri if veri is not None else adaptor(1.0))


class Testler(unittest.TestCase):
    def test_durum_kaydedilir_ve_devam_edilir(self):
        k = Koordinator(self)
        self.assertEqual(k.al("/gorev?isci=ali")["tur"], 0)
        self.assertEqual(k.gonder("ali", 0)[0], 200)
        self.assertEqual(k.durum()["tur"], 1)
        self.assertTrue(os.path.exists(os.path.join(k.calisma, "durum.json")))
        self.assertTrue(os.path.exists(os.path.join(k.calisma, "momentum.safetensors")))
        ozet = k.durum()["ozet"]
        k.durdur()
        k.baslat()  # aynı çalışma klasörü: kaldığı yerden devam
        self.assertEqual(k.durum()["tur"], 1)
        self.assertEqual(k.durum()["ozet"], ozet)
        k.durdur()
        k.baslat("--sifirdan")
        self.assertEqual(k.durum()["tur"], 0)

    def test_bozuk_durum_dosyasi_sifirdan_baslatir(self):
        k = Koordinator(self)
        k.gonder("ali", 0)
        k.durdur()
        open(os.path.join(k.calisma, "durum.json"), "w").write("{bozuk")
        k.baslat()
        self.assertEqual(k.durum()["tur"], 0)

    def test_isci_adi_dogrulanir(self):
        k = Koordinator(self)
        for kotu in ("", "a b", "a/b", "x" * 61, "<script>"):
            d, _ = k.istek("/gorev?isci=" + urllib.parse.quote(kotu))
            self.assertEqual(d, 400, repr(kotu))
        for iyi in ("ali-laptop", "gönüllü_1", "a.b-c", "x" * 60):
            d, _ = k.istek("/gorev?isci=" + urllib.parse.quote(iyi))
            self.assertEqual(d, 200, repr(iyi))
        self.assertEqual(k.gonder("a b", 0)[0], 400)

    def test_isci_siniri(self):
        k = Koordinator(self, "--en-cok-isci", "2")
        self.assertEqual(k.istek("/gorev?isci=a")[0], 200)
        self.assertEqual(k.istek("/gorev?isci=b")[0], 200)
        self.assertEqual(k.istek("/gorev?isci=c")[0], 503)
        self.assertEqual(k.istek("/gorev?isci=a")[0], 200)  # bilinen işçi etkilenmez

    def test_hiz_siniri(self):
        k = Koordinator(self, "--istek-siniri", "6")
        kodlar = [k.istek("/durum")[0] for _ in range(9)]  # açılış denetimi de 1 istek harcadı
        ilk = kodlar.index(429)
        self.assertTrue(4 <= ilk <= 6, kodlar)
        self.assertTrue(all(c == 429 for c in kodlar[ilk:]), kodlar)

    def test_vekil_ip_ayri_sayilir(self):
        k = Koordinator(self, "--istek-siniri", "3", "--vekil")
        for _ in range(3):
            self.assertEqual(k.istek("/durum", None, {"X-Forwarded-For": "10.0.0.1"})[0], 200)
        self.assertEqual(k.istek("/durum", None, {"X-Forwarded-For": "10.0.0.1"})[0], 429)
        self.assertEqual(k.istek("/durum", None, {"X-Forwarded-For": "10.0.0.2"})[0], 200)

    def test_birden_cok_anahtar(self):
        k = Koordinator(self, "--anahtar", "anahtar-bir,anahtar-iki")
        self.assertEqual(k.istek("/durum")[0], 401)
        self.assertEqual(k.istek("/durum", None, {"X-Anahtar": "anahtar-bir"})[0], 200)
        self.assertEqual(k.istek("/durum", None, {"X-Anahtar": "anahtar-iki"})[0], 200)
        self.assertEqual(k.istek("/durum", None, {"X-Anahtar": "yanlis"})[0], 401)
        self.assertEqual(k.istek("/bilgi")[0], 200)  # keşif anahtarsız

    def test_anahtar_basina_isci(self):
        k = Koordinator(self, "--anahtar", "k1,k2", "--anahtar-basina-isci", "1")
        h1, h2 = {"X-Anahtar": "k1"}, {"X-Anahtar": "k2"}
        self.assertEqual(k.istek("/gorev?isci=ali", None, h1)[0], 200)
        self.assertEqual(k.istek("/gorev?isci=ali", None, h1)[0], 200)      # aynı ad, aynı anahtar: serbest
        self.assertEqual(k.istek("/gorev?isci=ali2", None, h1)[0], 403)     # anahtar başına tek ad
        self.assertEqual(k.istek("/gorev?isci=ali", None, h2)[0], 403)      # ad başka anahtara geçemez
        self.assertEqual(k.istek("/gorev?isci=veli", None, h2)[0], 200)     # ikinci anahtarın kendi adı
        self.assertEqual(k.istek("/durum", None, h1)[0], 200)               # işçi adı gerektirmeyen yol etkilenmez

    def test_anahtar_basina_isci_kapali_varsayilan(self):
        k = Koordinator(self, "--anahtar", "k1,k2")
        for ad in ("a", "b", "c"):
            self.assertEqual(k.istek(f"/gorev?isci={ad}", None, {"X-Anahtar": "k1"})[0], 200)

    def veri_dosyasi(self, k, n=2400, etiketli=False):
        from safetensors.torch import save_file
        t = {"ids": torch.arange(n, dtype=torch.int32) % 1000}
        if etiketli:
            t["etiket"] = torch.where(torch.arange(n) % 2 == 0, t["ids"], torch.full((n,), -100, dtype=torch.int32))
        yol = os.path.join(k.dizin, "veri.safetensors")
        save_file(t, yol)
        return yol

    def test_veri_dagitimi(self):
        import hashlib
        k = Koordinator(self, "--parca", "2", "--seq", "16")
        k.durdur()
        k.ek += ["--veri", self.veri_dosyasi(k, etiketli=True)]
        k.baslat()
        a, b = k.al("/gorev?isci=a"), k.al("/gorev?isci=b")
        self.assertNotEqual(a["parca"], b["parca"])
        self.assertEqual(a["veri_belirtec"], 1200)
        for g in (a, b):
            d, govde = k.istek(f"/veri?parca={g['parca']}")
            self.assertEqual(d, 200)
            self.assertEqual(hashlib.sha256(govde).hexdigest(), g["veri_sha256"])
        from safetensors.torch import load
        t = load(k.istek(f"/veri?parca={a['parca']}")[1])
        self.assertEqual(set(t), {"ids", "etiket"})
        self.assertEqual(len(t["ids"]), 1200)
        self.assertEqual(k.istek("/veri?parca=9")[0], 400)
        self.assertEqual(k.istek("/veri?parca=x")[0], 400)
        self.assertIn("veri", k.al("/bilgi"))

    def test_veri_yoksa_alan_yok(self):
        k = Koordinator(self)
        self.assertNotIn("veri_sha256", k.al("/gorev?isci=a"))
        self.assertEqual(k.istek("/veri?parca=0")[0], 404)
        self.assertNotIn("veri", k.al("/bilgi"))

    def test_veri_anahtar_ister(self):
        k = Koordinator(self, "--anahtar", "gizli", "--parca", "2", "--seq", "16")
        k.durdur()
        k.ek += ["--veri", self.veri_dosyasi(k)]
        k.baslat()
        self.assertEqual(k.istek("/veri?parca=0")[0], 401)
        self.assertEqual(k.istek("/veri?parca=0", None, {"X-Anahtar": "gizli"})[0], 200)

    def test_anahtar_ortam_degiskeninden(self):
        os.environ["MODELEN_ANAHTAR"] = "ortam-bir,ortam-iki"
        try:
            k = Koordinator(self)  # alt süreç ortamı devralır; --anahtar verilmedi
        finally:
            os.environ.pop("MODELEN_ANAHTAR", None)
        self.assertEqual(k.istek("/durum")[0], 401)
        self.assertEqual(k.istek("/durum", None, {"X-Anahtar": "ortam-bir"})[0], 200)
        self.assertEqual(k.istek("/durum", None, {"X-Anahtar": "ortam-iki"})[0], 200)
        self.assertTrue(k.al("/bilgi")["anahtar_gerekli"])

    def test_bilgi_surum(self):
        k = Koordinator(self)
        b = k.al("/bilgi")
        self.assertEqual(b["protokol"], "1")
        self.assertEqual(b["surum"], "0.5.0")


if __name__ == "__main__":
    unittest.main()
