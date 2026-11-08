"""Modelen koordinatör protokolü v1'e uyan EN KÜÇÜK koordinatör (yalnızca standart kütüphane, ~150 satır).

Eğitim amaçlıdır: protokolü açıkça gösterir. Referans koordinatörden (istemci/koordinator.py) farkları:
- Dış adım yok: sonuçların düz ortalaması alınır (momentumlu Nesterov adımı, aykırı delta elemesi ve tur günlüğü yok).
- Safetensors okuma/yazma saf Python'dur (yavaş; 10 milyon parametrede tur kapatma birkaç saniye sürer) ve yalnızca float32 destekler.
- Durum bellekte tutulur; yeniden başlatınca sıfırlanır.
Bu dosya `uyum_testi.py` ile denetlenir (bkz. test_uyum.py) ve gönüllü uygulamanın beklediği tüm uç noktaları sağlar.

  python istemci/ornekler/minimal_koordinator.py --baslangic tur-0.safetensors --tur 5 --en-az 2 --port 8750
"""
import argparse
import array
import hashlib
import json
import math
import struct
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


def st_oku(veri):
    """safetensors baytlarını (başlık, {ad: array('f')}) olarak okur. Yalnızca F32; pickle yok."""
    n = struct.unpack("<Q", veri[:8])[0]
    baslik = json.loads(veri[8:8 + n].decode("utf-8"))
    govde = memoryview(veri)[8 + n:]
    tensorler = {}
    for ad, t in baslik.items():
        if ad == "__metadata__":
            continue
        if t["dtype"] != "F32":
            raise ValueError(f"yalnızca F32 desteklenir: {ad}")
        bas, son = t["data_offsets"]
        a = array.array("f")
        a.frombytes(govde[bas:son].tobytes())
        tensorler[ad] = a
    return baslik, tensorler


def st_yaz(sekiller, tensorler):
    baslik, ofs, parcalar = {}, 0, []
    for ad in sorted(tensorler):
        b = tensorler[ad].tobytes()
        baslik[ad] = {"dtype": "F32", "shape": sekiller[ad], "data_offsets": [ofs, ofs + len(b)]}
        ofs += len(b)
        parcalar.append(b)
    h = json.dumps(baslik, separators=(",", ":")).encode()
    h += b" " * (-len(h) % 8)
    return struct.pack("<Q", len(h)) + h + b"".join(parcalar)


class Durum:
    def __init__(self, baslangic, toplam_tur, en_az, ic_adim, parca):
        self.kil = threading.Lock()
        self.baslik, self.glob = st_oku(baslangic)
        self.sekiller = {a: t["shape"] for a, t in self.baslik.items() if a != "__metadata__"}
        self.toplam_tur, self.en_az, self.ic_adim, self.n_parca = toplam_tur, en_az, ic_adim, parca
        self.tur, self.sonuclar, self.isciler, self.parca_of = 0, {}, {}, {}
        self.trafik = {"indirilen_bayt": 0, "yuklenen_bayt": 0}
        self._baytla()

    def _baytla(self):
        self.bayt = st_yaz(self.sekiller, self.glob)
        self.sha = hashlib.sha256(self.bayt).hexdigest()

    def dogrula(self, tensorler):
        if set(tensorler) != set(self.glob):
            return "anahtar kümesi uyuşmuyor"
        for ad, t in tensorler.items():
            if len(t) != len(self.glob[ad]):
                return f"şekil uyuşmuyor: {ad}"
            if not math.isfinite(sum(t)):
                return f"sonlu olmayan değer: {ad}"
        return None

    def tur_kapat(self):
        for ad in self.glob:
            n = len(self.sonuclar)
            ort = array.array("f", (sum(v) / n for v in zip(*(s[ad] for s in self.sonuclar.values()))))
            self.glob[ad] = ort
        self.sonuclar = {}
        self.tur += 1
        self._baytla()


def isleyici(d):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def yaz(self, kod, govde, tip="application/json", ek=None):
            if not isinstance(govde, bytes):
                govde = json.dumps(govde, ensure_ascii=False).encode()
            self.send_response(kod)
            self.send_header("Content-Type", tip)
            self.send_header("Content-Length", str(len(govde)))
            for k, v in (ek or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(govde)

        def do_GET(self):
            u = urlparse(self.path)
            q = parse_qs(u.query)
            with d.kil:
                if u.path == "/bilgi":
                    return self.yaz(200, {"protokol": "1", "uygulama": "minimal-koordinator", "tur": d.tur, "toplam_tur": d.toplam_tur,
                                          "agirlik_sha256": d.sha, "agirlik_boyutu": len(d.bayt)})
                if u.path == "/durum":
                    return self.yaz(200, {"tur": d.tur, "toplam_tur": d.toplam_tur, "bekleyen_sonuc": list(d.sonuclar), "ozet": d.sha[:16],
                                          "isciler": {i: 0 for i in d.isciler}, "trafik": d.trafik, "gunluk": []})
                if u.path == "/gorev":
                    isci = (q.get("isci") or [""])[0]
                    if not isci:
                        return self.yaz(400, {"hata": "isci gerekli"})
                    d.isciler[isci] = True
                    if d.tur >= d.toplam_tur:
                        return self.yaz(200, {"bitti": True})
                    if isci in d.sonuclar:
                        return self.yaz(200, {"bekle": True, "tur": d.tur})
                    d.parca_of.setdefault(isci, len(d.parca_of) % d.n_parca)
                    return self.yaz(200, {"tur": d.tur, "toplam_tur": d.toplam_tur, "parca": d.parca_of[isci], "n_parca": d.n_parca, "ic_adim": d.ic_adim,
                                          "bs": 4, "seq": 512, "lr": 2e-4, "tohum": 0, "agirlik_sha256": d.sha})
                if u.path == "/agirlik":
                    d.trafik["indirilen_bayt"] += len(d.bayt)
                    return self.yaz(200, d.bayt, "application/octet-stream", {"X-Tur": str(d.tur), "X-Sha256": d.sha})
            self.yaz(404, {"hata": "yok"})

        def do_POST(self):
            u = urlparse(self.path)
            q = parse_qs(u.query)
            n = int(self.headers.get("Content-Length", "0") or 0)
            if u.path != "/sonuc":
                self.rfile.read(n)
                return self.yaz(404, {"hata": "yok"})
            if n <= 0 or n > 300_000_000:
                return self.yaz(413, {"hata": "boyut"})
            veri = self.rfile.read(n)
            isci = (q.get("isci") or [""])[0]
            try:
                t_ist = int((q.get("tur") or ["-1"])[0])
            except ValueError:
                t_ist = -1
            try:
                _, tensorler = st_oku(veri)
            except Exception as ex:
                return self.yaz(400, {"hata": f"safetensors okunamadı: {type(ex).__name__}"})
            with d.kil:
                if d.tur >= d.toplam_tur:
                    return self.yaz(409, {"hata": "eğitim bitti"})
                if t_ist != d.tur:
                    return self.yaz(409, {"hata": "eski tur", "tur": d.tur})
                if isci in d.sonuclar:
                    return self.yaz(409, {"hata": "bu tur için sonuç zaten var"})
                hata = d.dogrula(tensorler)
                if hata:
                    return self.yaz(422, {"hata": hata})
                d.sonuclar[isci] = tensorler
                d.trafik["yuklenen_bayt"] += len(veri)
                if len(d.sonuclar) >= d.en_az:
                    d.tur_kapat()
                self.yaz(200, {"tamam": True, "tur": t_ist})

    return H


def sunucu_olustur(baslangic, host="127.0.0.1", port=8750, tur=5, en_az=2, ic_adim=20, parca=4):
    d = Durum(baslangic, tur, en_az, ic_adim, parca)
    return ThreadingHTTPServer((host, port), isleyici(d)), d


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--baslangic", required=True, help="başlangıç adaptörü (safetensors, float32)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8750)
    ap.add_argument("--tur", type=int, default=5, help="toplam tur")
    ap.add_argument("--en-az", type=int, default=2, help="turu kapatmak için gereken sonuç sayısı")
    ap.add_argument("--ic-adim", type=int, default=20, help="işçinin yerel adım sayısı (H)")
    ap.add_argument("--parca", type=int, default=4, help="veri dilimi sayısı")
    a = ap.parse_args()
    srv, durum = sunucu_olustur(open(a.baslangic, "rb").read(), a.host, a.port, a.tur, a.en_az, a.ic_adim, a.parca)
    print(f"[minimal-koordinatör] http://{a.host}:{a.port} tur=0/{a.tur} en-az={a.en_az} sha256={durum.sha[:16]}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
