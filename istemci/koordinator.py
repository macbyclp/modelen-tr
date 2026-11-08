"""Modelen koordinatörü (prototip): adaptör-DiLoCo turlarını yönetir.

Gönüllü işçiler küresel LoRA adaptörünü (~40 MB) indirir, H yerel adım eğitir ve yeni ağırlığı geri yollar.
Koordinatör gelen sonuçları doğrular, ortalamasını alır ve Nesterov momentumlu dış adımı uygular.

Yalnızca standart kütüphane + torch/safetensors. Ağırlıklar safetensors ile okunur (kod çalıştırmaz).

  python istemci/koordinator.py --baslangic istemci/calisma/tur-0.safetensors --tur 6 --en-az 2
"""
import argparse
import json
import math
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import torch

sys.path.insert(0, os.path.dirname(__file__))
import ortak  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--baslangic", required=True, help="baslat.py çıktısı (tur 0 adaptörü)")
ap.add_argument("--port", type=int, default=8750)
ap.add_argument("--host", default="127.0.0.1")
ap.add_argument("--tur", type=int, default=6, help="toplam tur sayısı")
ap.add_argument("--en-az", type=int, default=2, help="turu kapatmak için gereken en az işçi sonucu")
ap.add_argument("--zaman-asimi", type=float, default=900, help="sn; süre dolunca eldeki sonuçlarla (>=1) turu kapat")
ap.add_argument("--parca", type=int, default=4, help="veri dilimi sayısı (işçiler dönüşümlü atanır)")
ap.add_argument("--ic-adim", type=int, default=20)
ap.add_argument("--bs", type=int, default=4)
ap.add_argument("--seq", type=int, default=512)
ap.add_argument("--lr", type=float, default=2e-4)
ap.add_argument("--dis-lr", type=float, default=1.0)
ap.add_argument("--dis-mom", type=float, default=0.5)
ap.add_argument("--aykiri-kat", type=float, default=5.0, help="delta normu medyanın bu katını aşan sonuç elenir (>=3 sonuçta)")
ap.add_argument("--anahtar", default="", help="boş değilse istekler X-Anahtar başlığı taşımalı")
ap.add_argument("--calisma", default="istemci/calisma")
ap.add_argument("--tohum", type=int, default=0)
ap.add_argument("--mod", choices=["cpt", "sft"], default="cpt", help="işçilere bildirilen eğitim modu: cpt = ham metinde devam eden ön eğitim, sft = talimat (yanıt-maskeli) ince ayar")
A = ap.parse_args()

KIL = threading.Lock()
glob = ortak.bayttan(open(A.baslangic, "rb").read())
buf = {n: torch.zeros_like(t) for n, t in glob.items()}
glob_bytes = ortak.bayta(glob)
glob_ozet = ortak.ozet(glob_bytes)
tur = 0
sonuclar = {}  # isci -> durum
tur_basi = time.time()
isci_parca = {}
son_gorulme = {}
gunluk = []
trafik = {"indirilen_bayt": 0, "yuklenen_bayt": 0}
os.makedirs(A.calisma, exist_ok=True)


def tur_kapat(neden):
    """KIL altında çağrılır. Eldeki sonuçlarla dış adımı uygular."""
    global glob, glob_bytes, glob_ozet, tur, sonuclar, tur_basi
    adaylar = list(sonuclar.items())
    deltalar = []
    for isci, st in adaylar:
        d = {n: glob[n] - st[n] for n in glob}
        nrm = math.sqrt(sum(float((x.double() ** 2).sum()) for x in d.values()))
        deltalar.append((isci, st, nrm))
    elenen = []
    if len(deltalar) >= 3:
        med = sorted(n for _, _, n in deltalar)[len(deltalar) // 2]
        kalan = []
        for isci, st, nrm in deltalar:
            if med > 0 and nrm > A.aykiri_kat * med:
                elenen.append(isci)
            else:
                kalan.append((isci, st, nrm))
        deltalar = kalan
    if deltalar:
        with torch.no_grad():
            for n in glob:
                ort = torch.stack([st[n] for _, st, _ in deltalar]).mean(0)
                delta = glob[n] - ort
                buf[n].mul_(A.dis_mom).add_(delta)
                glob[n] = glob[n] - A.dis_lr * (delta + A.dis_mom * buf[n])
    glob_bytes = ortak.bayta(glob)
    glob_ozet = ortak.ozet(glob_bytes)
    tur += 1
    open(os.path.join(A.calisma, f"tur-{tur}.safetensors"), "wb").write(glob_bytes)
    kayit = {"tur": tur, "neden": neden, "kullanilan": [i for i, _, _ in deltalar], "elenen": elenen,
             "delta_norm": {i: round(n, 4) for i, _, n in deltalar}, "sn": round(time.time() - tur_basi, 1)}
    gunluk.append(kayit)
    print(f"[koordinatör] tur {tur}/{A.tur} kapandı ({neden}) kullanılan={kayit['kullanilan']} elenen={elenen}", flush=True)
    json.dump({"gunluk": gunluk, "trafik": trafik}, open(os.path.join(A.calisma, "gunluk.json"), "w"), indent=2)
    sonuclar = {}
    tur_basi = time.time()


def zaman_asimi_dongusu():
    while True:
        time.sleep(2)
        with KIL:
            if tur < A.tur and sonuclar and time.time() - tur_basi > A.zaman_asimi:
                tur_kapat("zaman-aşımı")


def dogrula(st):
    if set(st) != set(glob):
        return "anahtar kümesi uyuşmuyor"
    for n, t in st.items():
        if t.shape != glob[n].shape or t.dtype != glob[n].dtype:
            return f"şekil/tür uyuşmuyor: {n}"
        if not torch.isfinite(t).all():
            return f"sonlu olmayan değer: {n}"
    return None


soru_zamanlari = {}
SORU_DOSYASI = os.path.join(A.calisma, "sorular.jsonl")


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _yaz(self, kod, govde, tip="application/json", ek=None):
        if isinstance(govde, (dict, list)):
            govde = json.dumps(govde, ensure_ascii=False).encode()
        elif isinstance(govde, str):
            govde = govde.encode()
        self.send_response(kod)
        self.send_header("Content-Type", tip)
        self.send_header("Content-Length", str(len(govde)))
        for k, v in (ek or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(govde)

    def _yetki(self):
        if A.anahtar and self.headers.get("X-Anahtar") != A.anahtar:
            self._yaz(401, {"hata": "yetkisiz"})
            return False
        return True

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/":
            return self._yaz(200, "<meta charset=utf-8><title>Modelen koordinatör</title><pre id=d>yükleniyor</pre>"
                             "<script>async function t(){d.textContent=JSON.stringify(await (await fetch('/durum')).json(),null,2)}"
                             "t();setInterval(t,3000)</script>", "text/html; charset=utf-8")
        if u.path == "/bilgi":  # kimlik gerektirmez: keşif ve uyum denetimi için
            with KIL:
                return self._yaz(200, {"protokol": "1", "uygulama": "modelen-koordinator", "surum": "0.4.0", "tur": tur, "toplam_tur": A.tur,
                                       "taban_model": "Qwen/Qwen3-0.6B-Base",
                                       "adaptor": {"yontem": "lora", "r": ortak.LORA_R, "alfa": ortak.LORA_ALPHA, "hedef_moduller": ortak.HEDEF,
                                                   "dtype": "float32", "tensor_sayisi": len(glob)},
                                       "mod": A.mod, "agirlik_boyutu": len(glob_bytes), "agirlik_sha256": glob_ozet, "anahtar_gerekli": bool(A.anahtar)})
        if not self._yetki():
            return
        if u.path == "/durum":
            with KIL:
                return self._yaz(200, {"tur": tur, "toplam_tur": A.tur, "bekleyen_sonuc": list(sonuclar), "ozet": glob_ozet[:16],
                                       "isciler": {i: round(time.time() - t, 1) for i, t in son_gorulme.items()},
                                       "trafik": trafik, "gunluk": gunluk[-5:]})
        if u.path == "/gorev":
            isci = (q.get("isci") or [""])[0]
            if not isci:
                return self._yaz(400, {"hata": "isci gerekli"})
            with KIL:
                son_gorulme[isci] = time.time()
                if tur >= A.tur:
                    return self._yaz(200, {"bitti": True})
                if isci in sonuclar:
                    return self._yaz(200, {"bekle": True, "tur": tur})
                if isci not in isci_parca:
                    isci_parca[isci] = len(isci_parca) % A.parca
                return self._yaz(200, {"tur": tur, "toplam_tur": A.tur, "parca": isci_parca[isci], "n_parca": A.parca,
                                       "ic_adim": A.ic_adim, "bs": A.bs, "seq": A.seq, "lr": A.lr, "tohum": A.tohum, "mod": A.mod,
                                       "agirlik_sha256": glob_ozet})
        if u.path == "/agirlik":
            with KIL:
                veri, oz, t = glob_bytes, glob_ozet, tur
                trafik["indirilen_bayt"] += len(veri)
            return self._yaz(200, veri, "application/octet-stream", {"X-Tur": str(t), "X-Sha256": oz})
        self._yaz(404, {"hata": "yok"})

    def _soru(self):
        """Topluluk sorusu: istemciden gelen soruyu calisma/sorular.jsonl dosyasına ekler (IP saklanmaz)."""
        n = int(self.headers.get("Content-Length", "0"))
        if n <= 0 or n > 20_000:
            return self._yaz(413, {"hata": "boyut"})
        try:
            d = json.loads(self.rfile.read(n).decode("utf-8", errors="replace"))
            soru = str(d.get("soru", "")).strip()
        except Exception:
            return self._yaz(400, {"hata": "geçersiz istek"})
        if not soru or len(soru) > 2000:
            return self._yaz(400, {"hata": "soru 1-2000 karakter olmalı"})
        ip, simdi = self.client_address[0], time.time()
        with KIL:
            son = [t for t in soru_zamanlari.get(ip, []) if simdi - t < 600]
            if len(son) >= 5:
                soru_zamanlari[ip] = son
                return self._yaz(429, {"hata": "çok sık soru"})
            soru_zamanlari[ip] = son + [simdi]
            no = sum(1 for _ in open(SORU_DOSYASI, encoding="utf-8")) + 1 if os.path.exists(SORU_DOSYASI) else 1
            kayit = {"no": no, "zaman": time.strftime("%Y-%m-%d %H:%M:%S"), "isci": str(d.get("isci", ""))[:60],
                     "surum": str(d.get("surum", ""))[:20], "soru": soru, "baglam": str(d.get("baglam", ""))[:6000]}
            with open(SORU_DOSYASI, "a", encoding="utf-8") as f:
                f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
        self._yaz(200, {"tamam": True, "no": no})

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/soru":
            return self._soru()
        if u.path != "/sonuc" or not self._yetki():
            return self._yaz(404, {"hata": "yok"})
        q = parse_qs(u.query)
        isci = (q.get("isci") or [""])[0]
        try:
            t_ist = int((q.get("tur") or ["-1"])[0])
        except ValueError:
            t_ist = -1
        n = int(self.headers.get("Content-Length", "0"))
        if n <= 0 or n > 300_000_000:
            return self._yaz(413, {"hata": "boyut"})
        veri = self.rfile.read(n)
        try:
            st = ortak.bayttan(veri)
        except Exception as e:  # bozuk dosya
            return self._yaz(400, {"hata": f"safetensors okunamadı: {type(e).__name__}"})
        with KIL:
            if tur >= A.tur:
                return self._yaz(409, {"hata": "eğitim bitti"})
            if t_ist != tur:
                return self._yaz(409, {"hata": "eski tur", "tur": tur})
            if isci in sonuclar:
                return self._yaz(409, {"hata": "bu tur için sonuç zaten var"})
            hata = dogrula(st)
            if hata:
                return self._yaz(422, {"hata": hata})
            sonuclar[isci] = st
            trafik["yuklenen_bayt"] += len(veri)
            print(f"[koordinatör] tur {tur}: {isci} sonucu alındı ({len(sonuclar)}/{A.en_az})", flush=True)
            if len(sonuclar) >= A.en_az:
                tur_kapat("yeterli-sonuç")
            self._yaz(200, {"tamam": True, "tur": tur})


if __name__ == "__main__":
    threading.Thread(target=zaman_asimi_dongusu, daemon=True).start()
    srv = ThreadingHTTPServer((A.host, A.port), H)
    print(f"[koordinatör] http://{A.host}:{A.port}  tur=0/{A.tur}  en-az={A.en_az}  sha256={glob_ozet[:16]}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
