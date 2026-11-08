"""Uyum testi aracının testleri: sahte koordinatörlerle geçer/kalır senaryoları + (varsa) gerçek referans koordinatör.
Çalıştırma (istemci/ klasöründe): py -3 -W ignore -m unittest test_uyum"""
import hashlib
import json
import os
import socket
import struct
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import uyum_testi

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def st_bayt(adlar=("a.lora_A.default.weight", "a.lora_B.default.weight"), dtype="F32", kotu_aralik=False):
    baslik, ofs = {}, 0
    for ad in adlar:
        boy = 4 * 4
        baslik[ad] = {"dtype": dtype, "shape": [2, 2], "data_offsets": [ofs, ofs + boy + (10_000 if kotu_aralik else 0)]}
        ofs += boy
    h = json.dumps(baslik).encode()
    return struct.pack("<Q", len(h)) + h + b"\x00" * ofs


def sahte_koordinator(**bozuk):
    """Protokol v1'e uyan (ya da `bozuk` ile bilerek bozulan) küçük koordinatör."""
    agirlik = bozuk.get("agirlik", st_bayt())
    sha = hashlib.sha256(agirlik).hexdigest()

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def yaz(self, kod, govde, tip="application/json", ek=None):
            if not isinstance(govde, bytes):
                govde = json.dumps(govde).encode()
            self.send_response(kod)
            self.send_header("Content-Type", tip)
            self.send_header("Content-Length", str(len(govde)))
            for k, v in (ek or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(govde)

        def do_GET(self):
            yol = self.path.split("?")[0]
            if bozuk.get("anahtar") and yol != "/bilgi" and self.headers.get("X-Anahtar") != bozuk["anahtar"]:
                return self.yaz(401, {"hata": "yetkisiz"})
            if yol == "/bilgi" and not bozuk.get("bilgi_yok"):
                return self.yaz(200, {"protokol": "1", "taban_model": "x"})
            if yol == "/durum":
                if bozuk.get("durum_eksik"):
                    return self.yaz(200, {"tur": 0})
                return self.yaz(200, {"tur": 0, "toplam_tur": 3, "bekleyen_sonuc": [], "isciler": {}, "trafik": {"indirilen_bayt": 0, "yuklenen_bayt": 0}})
            if yol == "/gorev":
                if "isci=" not in self.path or self.path.endswith("isci="):
                    return self.yaz(400, {"hata": "isci gerekli"})
                return self.yaz(200, {"tur": 0, "toplam_tur": 3, "parca": 0, "n_parca": 4, "ic_adim": 10, "bs": 4, "seq": 512, "lr": 2e-4, "tohum": 0, "agirlik_sha256": sha})
            if yol == "/agirlik":
                return self.yaz(200, agirlik, "application/octet-stream", {"X-Tur": "0", "X-Sha256": bozuk.get("sha_basligi", sha)})
            self.yaz(404, {"hata": "yok"})

        def do_POST(self):
            n = int(self.headers.get("Content-Length", "0"))
            self.rfile.read(n)
            if bozuk.get("sonuc_500"):
                return self.yaz(500, {"hata": "patladi"})
            if bozuk.get("sonuc_200"):
                return self.yaz(200, {"tamam": True})
            if n == 0:
                return self.yaz(413, {"hata": "boyut"})
            if "tur=987654" in self.path:
                return self.yaz(409, {"hata": "eski tur"})
            self.yaz(400, {"hata": "safetensors okunamadi"})

    s = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, f"http://127.0.0.1:{s.server_address[1]}"


def durumlar(sonuc):
    return {x["madde"]: x["durum"] for x in sonuc.satirlar}


class SafetensorsBirim(unittest.TestCase):
    def test_gecerli_ve_gecersiz(self):
        hata, bilgi = uyum_testi.safetensors_dogrula(st_bayt())
        self.assertIsNone(hata)
        self.assertEqual((bilgi["tensor"], bilgi["dtype"], bilgi["lora"]), (2, ["F32"], 2))
        for kotu, parca in ((b"", "kısa"), (b"\x80\x04\x95" + b"x" * 40, "başlık"), (st_bayt(kotu_aralik=True), "aralığı"), (struct.pack("<Q", 2) + b"{}" + b"\0" * 8, "tensör yok")):
            hata, _ = uyum_testi.safetensors_dogrula(kotu)
            self.assertIn(parca, hata or "")


class UyumSahte(unittest.TestCase):
    def test_uyumlu_koordinator_gecer(self):
        s, url = sahte_koordinator()
        try:
            r = uyum_testi.calistir(url)
            self.assertTrue(r.basarili, r.satirlar)
            d = durumlar(r)
            self.assertEqual((d["/durum"], d["/gorev"], d["/agirlik sha256"], d["/agirlik safetensors"], d["/sonuc (bozuk veri)"],
                              d["/sonuc (eski/yanlış tur)"], d["/sonuc (boş gövde)"], d["bilinmeyen yol"]), ("PASS",) * 8)
            self.assertEqual(uyum_testi.main(["--url", url, "--json"]), 0)
        finally:
            s.shutdown()

    def test_bozuk_koordinatorler_kalir(self):
        senaryolar = [
            ({"sha_basligi": "0" * 64}, "/agirlik sha256"),
            ({"sonuc_500": True}, "/sonuc (bozuk veri)"),
            ({"sonuc_200": True}, "/sonuc (bozuk veri)"),  # geçersiz veriyi kabul etmek
            ({"durum_eksik": True}, "/durum"),
            ({"agirlik": b"\x80\x04\x95pickle-gibi" + b"\0" * 40}, "/agirlik safetensors"),
            ({"agirlik": st_bayt(kotu_aralik=True)}, "/agirlik safetensors"),
        ]
        for bozuk, madde in senaryolar:
            s, url = sahte_koordinator(**bozuk)
            try:
                r = uyum_testi.calistir(url)
                self.assertFalse(r.basarili, bozuk)
                self.assertEqual(durumlar(r)[madde], "FAIL", (bozuk, r.satirlar))
                self.assertEqual(uyum_testi.main(["--url", url]), 1)
            finally:
                s.shutdown()

    def test_bilgi_yoksa_uyari_anahtar_ve_baglanti(self):
        s, url = sahte_koordinator(bilgi_yok=True)
        try:
            r = uyum_testi.calistir(url)
            self.assertTrue(r.basarili)
            self.assertEqual(durumlar(r)["/bilgi"], "WARN")
        finally:
            s.shutdown()
        s, url = sahte_koordinator(anahtar="gizli")
        try:
            self.assertEqual(durumlar(uyum_testi.calistir(url))["kimlik"], "FAIL")  # anahtarsız 401
            self.assertTrue(uyum_testi.calistir(url, anahtar="gizli").basarili)
        finally:
            s.shutdown()
        r = uyum_testi.calistir("http://127.0.0.1:1")  # kimse dinlemiyor
        self.assertEqual(durumlar(r)["bağlantı"], "FAIL")
        with self.assertRaises(ValueError):
            uyum_testi.Istemci("ftp://x")


@unittest.skipUnless(os.path.exists(os.path.join(KOK, ".venv", "Scripts", "python.exe")) and os.path.exists(os.path.join(KOK, "istemci", "calisma", "tur-0.safetensors")),
                     "gerçek referans koordinatör için .venv ve istemci/calisma/tur-0.safetensors gerekli")
class UyumGercekReferans(unittest.TestCase):
    def test_referans_koordinator_uyumlu(self):
        sk = socket.socket()
        sk.bind(("127.0.0.1", 0))
        p = sk.getsockname()[1]
        sk.close()
        calisma = tempfile.mkdtemp()
        proc = subprocess.Popen([os.path.join(KOK, ".venv", "Scripts", "python.exe"), os.path.join(KOK, "istemci", "koordinator.py"), "--baslangic",
                                 os.path.join(KOK, "istemci", "calisma", "tur-0.safetensors"), "--port", str(p), "--en-az", "1", "--calisma", calisma],
                                cwd=KOK, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            url = f"http://127.0.0.1:{p}"
            for _ in range(120):
                try:
                    urllib.request.urlopen(url + "/durum", timeout=2).read()
                    break
                except Exception:
                    time.sleep(0.5)
            r = uyum_testi.calistir(url)
            self.assertTrue(r.basarili, r.satirlar)
            d = durumlar(r)
            self.assertEqual(d["/bilgi"], "PASS")
            self.assertEqual(d["/agirlik safetensors"], "PASS")
            bilgi = json.loads(urllib.request.urlopen(url + "/bilgi", timeout=5).read())
            self.assertEqual((bilgi["protokol"], bilgi["adaptor"]["r"], bilgi["adaptor"]["tensor_sayisi"]), ("1", 16, 392))
        finally:
            proc.terminate()
            proc.wait(timeout=15)


if __name__ == "__main__":
    unittest.main()
