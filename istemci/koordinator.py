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
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import torch

for _akis in (sys.stdout, sys.stderr):  # İngilizce Windows'ta konsol cp1252'dir; Türkçe karakterler UnicodeEncodeError verirdi
    try:
        _akis.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

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
ap.add_argument("--anahtar", default="", help="boş değilse istekler X-Anahtar başlığı taşımalı; virgülle ayırarak birden çok anahtar verilebilir (işçi başına bir anahtar, tek tek iptal için)")
ap.add_argument("--sifirdan", action="store_true", help="calisma klasöründeki kayıtlı durumu yok say ve tur 0'dan başla (varsayılan: kayıtlıysa kaldığı yerden devam et)")
ap.add_argument("--anahtar-basina-isci", type=int, default=0, help="çoklu anahtarla: bir anahtarın kullanabileceği en çok farklı işçi adı; bir ad ilk kullanan anahtara bağlanır (0 = sınırsız). 1 verirseniz bir anahtar = bir oy (kayıt yeniden başlatmada sıfırlanır)")
ap.add_argument("--en-cok-isci", type=int, default=1000, help="takip edilen en çok farklı işçi adı (bellek sınırı)")
ap.add_argument("--istek-siniri", type=int, default=240, help="IP başına dakikada en çok istek (0 = sınırsız; ters vekil arkasında X-Forwarded-For kullanılır)")
ap.add_argument("--vekil", action="store_true", help="güvenilir bir ters vekil (Caddy/nginx) arkasındayım: istemci IP'sini X-Forwarded-For'dan al")
ap.add_argument("--calisma", default="istemci/calisma")
ap.add_argument("--tohum", type=int, default=0)
ap.add_argument("--veri", default="", help="belirteçlenmiş eğitim verisi (safetensors: ids [+ etiket]); verilirse dilimlenip /veri?parca=i ile işçilere sunulur (istemci/veri_donustur.py ile üretilir)")
ap.add_argument("--mod", choices=["cpt", "sft"], default="cpt", help="işçilere bildirilen eğitim modu: cpt = ham metinde devam eden ön eğitim, sft = talimat (yanıt-maskeli) ince ayar")
A = ap.parse_args()

KIL = threading.Lock()
ANAHTAR_ISCI = {}  # anahtar -> {işçi adları}; ad -> anahtar ILK_ANAHTAR
ILK_ANAHTAR = {}
ANAHTAR_KIL = threading.Lock()
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
SURUM = "0.5.0"
DURUM_DOSYASI = os.path.join(A.calisma, "durum.json")
MOMENTUM_DOSYASI = os.path.join(A.calisma, "momentum.safetensors")
ANAHTARLAR = {k.strip() for k in (A.anahtar or os.environ.get("MODELEN_ANAHTAR", "")).split(",") if k.strip()}  # ortam değişkeni: anahtar süreç listesinde (ps) görünmesin
VERI_DILIMLERI = {}  # parca -> (bayt, sha256, belirteç sayısı)


def veri_hazirla():
    """--veri verilmişse ids (ve varsa etiket) parça sayısına bölünür; her dilim ayrı safetensors olarak önceden serileştirilir (int32)."""
    from safetensors.torch import load_file
    d = load_file(A.veri)
    if "ids" not in d:
        sys.exit("--veri dosyasında 'ids' tensörü yok")
    ids = d["ids"].to(torch.int32)
    et = d["etiket"].to(torch.int32) if "etiket" in d else None
    if et is not None and et.shape != ids.shape:
        sys.exit("--veri: etiket ve ids aynı uzunlukta olmalı")
    n = len(ids) // A.parca
    if n < A.seq + 2:
        sys.exit(f"--veri çok kısa: parça başına {n} belirteç, en az {A.seq + 2} gerekir")
    for p in range(A.parca):
        t = {"ids": ids[p * n:(p + 1) * n].contiguous()}
        if et is not None:
            t["etiket"] = et[p * n:(p + 1) * n].contiguous()
        b = ortak.bayta(t)
        VERI_DILIMLERI[p] = (b, ortak.ozet(b), n)
    print(f"[koordinatör] veri: {len(ids)} belirteç, {A.parca} dilim x {n}, dilim başına ~{len(VERI_DILIMLERI[0][0]) / 1e6:.1f} MB", flush=True)


ISCI_AD = re.compile(r"^[\w.\-]{1,60}$")


def durum_kaydet():
    """Her tur sonunda: momentum tamponu + sayaçlar. Yeniden başlatınca kaldığı yerden devam edilir. Yazım atomik (geçici dosya + yeniden adlandırma)."""
    gecici = MOMENTUM_DOSYASI + ".yeni"
    open(gecici, "wb").write(ortak.bayta({n: t.contiguous() for n, t in buf.items()}))
    os.replace(gecici, MOMENTUM_DOSYASI)
    gecici = DURUM_DOSYASI + ".yeni"
    json.dump({"tur": tur, "isci_parca": isci_parca, "gunluk": gunluk[-200:], "trafik": trafik, "mod": A.mod, "tohum": A.tohum}, open(gecici, "w"))
    os.replace(gecici, DURUM_DOSYASI)


def durum_yukle():
    """calisma klasöründe kayıt varsa glob/buf/tur'u geri yükle. Tutarsızsa (eksik dosya) None döner ve sıfırdan başlanır."""
    global glob, buf, glob_bytes, glob_ozet, tur, isci_parca, gunluk, trafik
    if A.sifirdan or not os.path.exists(DURUM_DOSYASI):
        return False
    try:
        d = json.load(open(DURUM_DOSYASI))
        son = os.path.join(A.calisma, f"tur-{d['tur']}.safetensors")
        g = ortak.bayttan(open(son, "rb").read())
        b = ortak.bayttan(open(MOMENTUM_DOSYASI, "rb").read()) if os.path.exists(MOMENTUM_DOSYASI) else {n: torch.zeros_like(t) for n, t in g.items()}
        if set(g) != set(glob) or any(g[n].shape != glob[n].shape for n in g):
            print("[koordinatör] kayıtlı durum başlangıç adaptörüyle uyuşmuyor; sıfırdan başlanıyor", flush=True)
            return False
    except (OSError, ValueError, KeyError) as e:
        print(f"[koordinatör] kayıtlı durum okunamadı ({type(e).__name__}); sıfırdan başlanıyor", flush=True)
        return False
    glob, buf, tur = g, b, int(d["tur"])
    glob_bytes = ortak.bayta(glob)
    glob_ozet = ortak.ozet(glob_bytes)
    isci_parca, gunluk, trafik = d.get("isci_parca", {}), d.get("gunluk", []), d.get("trafik", trafik)
    print(f"[koordinatör] kayıtlı durumdan devam: tur {tur}/{A.tur}", flush=True)
    return True


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
    durum_kaydet()


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


ip_istekleri = {}


class H(BaseHTTPRequestHandler):
    timeout = 120  # yavaş/asılı bağlantılar (slowloris) iş parçacığını sonsuza dek tutamaz

    def log_message(self, *a):
        pass

    def _ip(self):
        if A.vekil:
            xff = self.headers.get("X-Forwarded-For", "")
            if xff:
                return xff.split(",")[0].strip()[:64]
        return self.client_address[0]

    def _hiz_siniri(self):
        if not A.istek_siniri:
            return True
        ip, simdi = self._ip(), time.time()
        with KIL:
            son = [t for t in ip_istekleri.get(ip, []) if simdi - t < 60]
            if len(son) >= A.istek_siniri:
                ip_istekleri[ip] = son
                self._yaz(429, {"hata": "çok fazla istek"}, ek={"Retry-After": "30"})
                return False
            ip_istekleri[ip] = son + [simdi]
            if len(ip_istekleri) > 20000:  # bellek sınırı: eski kayıtları at
                for k in [k for k, v in ip_istekleri.items() if not v or simdi - v[-1] > 60]:
                    ip_istekleri.pop(k, None)
        return True

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
        if ANAHTARLAR and self.headers.get("X-Anahtar") not in ANAHTARLAR:
            self._yaz(401, {"hata": "yetkisiz"})
            return False
        return True

    def _isci_adi(self, q):
        """Geçerli işçi adı ya da None (yanıt zaten yazıldı). Yeni adlar `en-cok-isci` sınırına tabidir."""
        isci = (q.get("isci") or [""])[0]
        if not isci:
            self._yaz(400, {"hata": "isci gerekli"})
            return None
        if not ISCI_AD.match(isci):
            self._yaz(400, {"hata": "isci adı 1-60 karakter; harf, rakam, _ . - kullanın"})
            return None
        if A.anahtar_basina_isci > 0 and ANAHTARLAR:  # bir anahtar = en çok N işçi adı; ad başka anahtara geçemez
            k = self.headers.get("X-Anahtar", "")
            with ANAHTAR_KIL:
                sahip = ILK_ANAHTAR.get(isci)
                if sahip is None:
                    if len(ANAHTAR_ISCI.get(k, ())) >= A.anahtar_basina_isci:
                        sahip = ""
                    else:
                        ILK_ANAHTAR[isci] = sahip = k
                        ANAHTAR_ISCI.setdefault(k, set()).add(isci)
                if sahip != k:
                    self._yaz(403, {"hata": "bu işçi adı bu anahtara ait değil ya da anahtarın işçi sınırı doldu"})
                    return None
        return isci

    def do_GET(self):
        if not self._hiz_siniri():
            return
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/":
            return self._yaz(200, "<meta charset=utf-8><title>Modelen koordinatör</title><pre id=d>yükleniyor</pre>"
                             "<script>async function t(){d.textContent=JSON.stringify(await (await fetch('/durum')).json(),null,2)}"
                             "t();setInterval(t,3000)</script>", "text/html; charset=utf-8")
        if u.path == "/bilgi":  # kimlik gerektirmez: keşif ve uyum denetimi için
            with KIL:
                return self._yaz(200, {"protokol": "1", "uygulama": "modelen-koordinator", "surum": SURUM, "tur": tur, "toplam_tur": A.tur,
                                       "taban_model": "Qwen/Qwen3-0.6B-Base",
                                       "adaptor": {"yontem": "lora", "r": ortak.LORA_R, "alfa": ortak.LORA_ALPHA, "hedef_moduller": ortak.HEDEF,
                                                   "dtype": "float32", "tensor_sayisi": len(glob)},
                                       "mod": A.mod, **({"veri": {"bicim": "safetensors-ids-v1", "parca": A.parca}} if VERI_DILIMLERI else {}), "agirlik_boyutu": len(glob_bytes), "agirlik_sha256": glob_ozet, "anahtar_gerekli": bool(ANAHTARLAR)})
        if not self._yetki():
            return
        if u.path == "/durum":
            with KIL:
                return self._yaz(200, {"tur": tur, "toplam_tur": A.tur, "bekleyen_sonuc": list(sonuclar), "ozet": glob_ozet[:16],
                                       "isciler": {i: round(time.time() - t, 1) for i, t in son_gorulme.items()},
                                       "trafik": trafik, "gunluk": gunluk[-5:]})
        if u.path == "/gorev":
            isci = self._isci_adi(q)
            if isci is None:
                return
            with KIL:
                if isci not in son_gorulme and len(son_gorulme) >= A.en_cok_isci:
                    return self._yaz(503, {"hata": "koordinatör dolu (işçi sınırı)"}, ek={"Retry-After": "300"})
                son_gorulme[isci] = time.time()
                if tur >= A.tur:
                    return self._yaz(200, {"bitti": True})
                if isci in sonuclar:
                    return self._yaz(200, {"bekle": True, "tur": tur})
                if isci not in isci_parca:
                    isci_parca[isci] = len(isci_parca) % A.parca
                return self._yaz(200, {"tur": tur, "toplam_tur": A.tur, "parca": isci_parca[isci], "n_parca": A.parca,
                                       "ic_adim": A.ic_adim, "bs": A.bs, "seq": A.seq, "lr": A.lr, "tohum": A.tohum, "mod": A.mod,
                                       **({"veri_sha256": VERI_DILIMLERI[isci_parca[isci]][1], "veri_belirtec": VERI_DILIMLERI[isci_parca[isci]][2]} if VERI_DILIMLERI else {}),
                                       "agirlik_sha256": glob_ozet})
        if u.path == "/veri":
            if not VERI_DILIMLERI:
                return self._yaz(404, {"hata": "bu koordinatör veri sunmuyor"})
            try:
                p = int((q.get("parca") or ["-1"])[0])
            except ValueError:
                p = -1
            if p not in VERI_DILIMLERI:
                return self._yaz(400, {"hata": f"parca 0-{A.parca - 1} olmalı"})
            b, oz, _ = VERI_DILIMLERI[p]
            with KIL:
                trafik["indirilen_bayt"] += len(b)
            return self._yaz(200, b, "application/octet-stream", {"X-Sha256": oz})
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
        ip, simdi = self._ip(), time.time()
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
        if not self._hiz_siniri():
            return
        u = urlparse(self.path)
        if u.path == "/soru":
            return self._soru()
        if u.path != "/sonuc" or not self._yetki():
            return self._yaz(404, {"hata": "yok"})
        q = parse_qs(u.query)
        isci = self._isci_adi(q)
        if isci is None:
            return
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
    if A.veri:
        veri_hazirla()
    durum_yukle()
    threading.Thread(target=zaman_asimi_dongusu, daemon=True).start()
    ThreadingHTTPServer.daemon_threads = True
    srv = ThreadingHTTPServer((A.host, A.port), H)
    print(f"[koordinatör] http://{A.host}:{A.port}  tur=0/{A.tur}  en-az={A.en_az}  sha256={glob_ozet[:16]}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
