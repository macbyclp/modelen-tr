"""Modelen koordinatör protokolü v1 uyum testi (yalnızca standart kütüphane).

Bir koordinatör adresinin protokole uyup uymadığını denetler: /bilgi, /durum, /gorev, /agirlik, /sonuc ve hata davranışları.
Gönüllü uygulamanın sizinle çalışabilmesi için tüm "FAIL" maddeleri geçmelidir; "WARN" maddeleri öneridir.

  python istemci/uyum_testi.py --url https://koordinator.ornek.org
  python istemci/uyum_testi.py --url http://127.0.0.1:8750 --anahtar GIZLI --json

Not: /gorev denemesi koordinatörünüzde "uyum-testi" adlı bir işçi kaydı oluşturur; /sonuc'a geçersiz veri gönderir (reddedilmesi beklenir).
Çıkış kodu: tüm zorunlu maddeler geçtiyse 0, aksi hâlde 1.
"""
import argparse
import hashlib
import http.client
import json
import re
import ssl
import struct
import sys
import time
from urllib.parse import urlparse

PROTOKOL = "1"
YEREL = ("127.0.0.1", "localhost", "::1")


class Sonuc:
    def __init__(self):
        self.satirlar = []

    def ekle(self, durum, ad, ayrinti=""):
        self.satirlar.append({"durum": durum, "madde": ad, "ayrinti": ayrinti})

    @property
    def basarili(self):
        return not any(s["durum"] == "FAIL" for s in self.satirlar)


class Istemci:
    def __init__(self, url, anahtar="", zaman=15):
        u = urlparse(url)
        if u.scheme not in ("http", "https") or not u.hostname:
            raise ValueError("--url http:// ya da https:// ile başlamalı")
        self.u, self.anahtar, self.zaman = u, anahtar, zaman
        self.yol_on = u.path.rstrip("/")

    def istek(self, yontem, yol, govde=None, ek=None):
        port = self.u.port or (443 if self.u.scheme == "https" else 80)
        c = (http.client.HTTPSConnection(self.u.hostname, port, timeout=self.zaman, context=ssl.create_default_context())
             if self.u.scheme == "https" else http.client.HTTPConnection(self.u.hostname, port, timeout=self.zaman))
        basliklar = dict(ek or {})
        if self.anahtar:
            basliklar["X-Anahtar"] = self.anahtar
        t0 = time.time()
        c.request(yontem, self.yol_on + yol, govde, basliklar)
        r = c.getresponse()
        veri = r.read(400_000_000)
        return r.status, {k.lower(): v for k, v in r.getheaders()}, veri, time.time() - t0


def json_mu(veri):
    try:
        d = json.loads(veri.decode("utf-8"))
        return d if isinstance(d, dict) else None
    except (ValueError, UnicodeDecodeError):
        return None


def safetensors_dogrula(veri):
    """Pickle olmayan, tutarlı bir safetensors dosyası mı? (torch gerekmez). (hata, bilgi) döndürür."""
    if len(veri) < 16:
        return "dosya çok kısa", None
    n = struct.unpack("<Q", veri[:8])[0]
    if n <= 0 or n > len(veri) - 8 or n > 100_000_000:
        return "başlık uzunluğu geçersiz", None
    try:
        baslik = json.loads(veri[8:8 + n].decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return "başlık JSON değil (pickle olabilir)", None
    govde_boyu = len(veri) - 8 - n
    adlar = [k for k in baslik if k != "__metadata__"]
    if not adlar:
        return "hiç tensör yok", None
    for k in adlar:
        t = baslik[k]
        bas, son = t["data_offsets"]
        if not (0 <= bas <= son <= govde_boyu):
            return f"{k}: veri aralığı dosya dışına taşıyor", None
    dtype = {baslik[k]["dtype"] for k in adlar}
    lora = sum(1 for k in adlar if "lora_A" in k or "lora_B" in k)
    return None, {"tensor": len(adlar), "dtype": sorted(dtype), "lora": lora}


def calistir(url, anahtar="", isci="uyum-testi"):
    s = Sonuc()
    ist = Istemci(url, anahtar)
    # ---- TLS
    if ist.u.scheme == "http" and ist.u.hostname not in YEREL:
        s.ekle("WARN", "TLS", "Adres http:// ile başlıyor; genel ağda https önerilir (adaptörler ve görevler şifresiz akar).")
    else:
        s.ekle("PASS", "TLS", "https" if ist.u.scheme == "https" else "yerel adres (http kabul)")
    # ---- /bilgi (isteğe bağlı)
    try:
        d, b, v, _ = ist.istek("GET", "/bilgi")
        j = json_mu(v) if d == 200 else None
        if j and str(j.get("protokol")) == PROTOKOL:
            s.ekle("PASS", "/bilgi", f"protokol {j['protokol']}, taban_model={j.get('taban_model')}")
        elif d == 404:
            s.ekle("WARN", "/bilgi", "Yok. Önerilir: protokol sürümünü ve taban modeli duyurun (GET /bilgi).")
        else:
            s.ekle("WARN", "/bilgi", f"Beklenen biçimde değil (HTTP {d}); `protokol` alanı \"{PROTOKOL}\" olmalı.")
    except Exception as ex:
        s.ekle("FAIL", "bağlantı", f"{type(ex).__name__}: {ex}")
        return s
    # ---- /durum
    d, b, v, sure = ist.istek("GET", "/durum")
    j = json_mu(v)
    if d == 200 and j and isinstance(j.get("tur"), int) and isinstance(j.get("toplam_tur"), int) and isinstance(j.get("bekleyen_sonuc"), list) \
            and isinstance(j.get("isciler"), dict) and isinstance(j.get("trafik"), dict):
        s.ekle("PASS", "/durum", f"tur {j['tur']}/{j['toplam_tur']} ({sure * 1000:.0f} ms)")
    else:
        s.ekle("FAIL", "/durum", f"HTTP {d}; tur, toplam_tur (int), bekleyen_sonuc (list), isciler (nesne), trafik (nesne) alanları gerekli.")
    if d == 401:
        s.ekle("FAIL", "kimlik", "401 döndü; koordinatör anahtar istiyor: --anahtar verin.")
        return s
    # ---- /gorev
    d, b, v, _ = ist.istek("GET", "/gorev")
    s.ekle("PASS" if d == 400 else "WARN", "/gorev (işçi adı yok)", f"HTTP {d}" + ("" if d == 400 else "; işçi adı yoksa 400 beklenir"))
    d, b, v, _ = ist.istek("GET", f"/gorev?isci={isci}")
    g = json_mu(v)
    gorev = None
    if d == 200 and g is not None and ("bekle" in g or "bitti" in g):
        s.ekle("PASS", "/gorev", "bekle/bitti yanıtı")
    elif d == 200 and g is not None:
        tipler = {"tur": int, "toplam_tur": int, "parca": int, "n_parca": int, "ic_adim": int, "bs": int, "seq": int, "lr": (int, float), "tohum": int, "agirlik_sha256": str}
        eksik = [k for k, t in tipler.items() if not isinstance(g.get(k), t) or isinstance(g.get(k), bool)]
        if eksik:
            s.ekle("FAIL", "/gorev", f"alanlar eksik/yanlış tür: {', '.join(eksik)}")
        elif not re.fullmatch(r"[0-9a-f]{64}", g["agirlik_sha256"]):
            s.ekle("FAIL", "/gorev", "agirlik_sha256 64 karakterlik küçük harfli onaltılı özet olmalı")
        else:
            gorev = g
            s.ekle("PASS", "/gorev", f"tur {g['tur']}, parça {g['parca']}/{g['n_parca']}, {g['ic_adim']} adım")
    else:
        s.ekle("FAIL", "/gorev", f"HTTP {d}; JSON görev, {{\"bekle\":true}} ya da {{\"bitti\":true}} bekleniyor")
    # ---- /veri (isteğe bağlı: görevde veri_sha256 varsa koordinatör veri dilimini kendisi sunar)
    if gorev and "veri_sha256" in gorev:
        if not re.fullmatch(r"[0-9a-f]{64}", str(gorev["veri_sha256"])):
            s.ekle("FAIL", "/veri", "veri_sha256 64 karakterlik küçük harfli onaltılı özet olmalı")
        else:
            d, b, v, sure = ist.istek("GET", f"/veri?parca={gorev['parca']}")
            if d != 200:
                s.ekle("FAIL", "/veri", f"HTTP {d}; görevde veri_sha256 var ama /veri?parca={gorev['parca']} sunulmuyor")
            elif hashlib.sha256(v).hexdigest() != gorev["veri_sha256"]:
                s.ekle("FAIL", "/veri sha256", "indirilen veri diliminin özeti görevdeki veri_sha256 ile uyuşmuyor")
            else:
                hata, bilgi = safetensors_dogrula(v)
                s.ekle("FAIL" if hata else "PASS", "/veri", hata or f"{bilgi['tensor']} tensör, {len(v) / 1e6:.1f} MB, özet doğru")
    # ---- /agirlik
    d, b, v, sure = ist.istek("GET", "/agirlik")
    if d != 200:
        s.ekle("FAIL", "/agirlik", f"HTTP {d}")
    else:
        sha = hashlib.sha256(v).hexdigest()
        if b.get("x-sha256") != sha:
            s.ekle("FAIL", "/agirlik sha256", f"X-Sha256 başlığı ({b.get('x-sha256')}) gövdenin özetiyle ({sha[:16]}…) uyuşmuyor")
        else:
            s.ekle("PASS", "/agirlik sha256", "başlık gövdeyle eşleşiyor")
        s.ekle("PASS" if re.fullmatch(r"\d+", b.get("x-tur", "")) else "FAIL", "/agirlik X-Tur", b.get("x-tur", "yok"))
        if gorev and gorev["agirlik_sha256"] != sha and int(b.get("x-tur", -1)) == gorev["tur"]:
            s.ekle("FAIL", "görev-ağırlık", "gorev.agirlik_sha256 ile indirilen ağırlığın özeti aynı turda uyuşmuyor")
        hata, bilgi = safetensors_dogrula(v)
        if hata:
            s.ekle("FAIL", "/agirlik safetensors", hata)
        else:
            s.ekle("PASS", "/agirlik safetensors", f"{bilgi['tensor']} tensör, dtype {bilgi['dtype']}, LoRA: {bilgi['lora']} ({len(v) / 1e6:.1f} MB, {sure:.1f} sn)")
            if bilgi["dtype"] != ["F32"]:
                s.ekle("WARN", "/agirlik dtype", "referans uygulama float32 kullanır; farklı tür gönüllü istemciyle uyumsuz olabilir")
    # ---- /sonuc
    tur = gorev["tur"] if gorev else 0
    d, b, v, _ = ist.istek("POST", f"/sonuc?isci={isci}&tur={tur}", b"bu bir safetensors dosyasi degil" * 4, {"Content-Type": "application/octet-stream"})
    s.ekle("PASS" if d in (400, 422) else "FAIL", "/sonuc (bozuk veri)", f"HTTP {d}" + ("" if d in (400, 422) else "; 400 ya da 422 beklenir (200/500 olmamalı)"))
    d, b, v, _ = ist.istek("POST", f"/sonuc?isci={isci}&tur=987654", b"x" * 64, {"Content-Type": "application/octet-stream"})
    s.ekle("PASS" if d in (400, 409, 422) else "FAIL", "/sonuc (eski/yanlış tur)", f"HTTP {d}" + ("" if d in (400, 409, 422) else "; 409 ya da reddedilmeli"))
    d, b, v, _ = ist.istek("POST", f"/sonuc?isci={isci}&tur={tur}", b"", {"Content-Length": "0"})
    s.ekle("PASS" if d in (400, 413, 422) else "FAIL", "/sonuc (boş gövde)", f"HTTP {d}" + ("" if d in (400, 413, 422) else "; reddedilmeli"))
    # ---- bilinmeyen yol
    d, b, v, _ = ist.istek("GET", "/yok-boyle-bir-yol")
    s.ekle("PASS" if d == 404 else "WARN", "bilinmeyen yol", f"HTTP {d}" + ("" if d == 404 else "; 404 beklenir"))
    return s


def yazdir(s, json_cikti):
    if json_cikti:
        print(json.dumps({"basarili": s.basarili, "sonuclar": s.satirlar}, ensure_ascii=False, indent=2))
        return
    simge = {"PASS": "  tamam ", "WARN": "  uyarı ", "FAIL": "  HATA  "}
    for x in s.satirlar:
        print(f"{simge[x['durum']]} {x['madde']:<26} {x['ayrinti']}")
    n = {k: sum(1 for x in s.satirlar if x["durum"] == k) for k in ("PASS", "WARN", "FAIL")}
    print(f"\n{n['PASS']} geçti, {n['WARN']} uyarı, {n['FAIL']} hata -> " + ("UYUMLU" if s.basarili else "UYUMLU DEĞİL"))


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows konsolunda (cp1254) çökmesin
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", required=True, help="koordinatör adresi (ör. https://koordinator.ornek.org)")
    ap.add_argument("--anahtar", default="", help="koordinatör X-Anahtar istiyorsa")
    ap.add_argument("--isci", default="uyum-testi", help="deneme işçi adı")
    ap.add_argument("--json", action="store_true", help="makine okunur çıktı")
    a = ap.parse_args(argv)
    try:
        s = calistir(a.url, a.anahtar, a.isci)
    except ValueError as ex:
        sys.exit(str(ex))
    yazdir(s, a.json)
    return 0 if s.basarili else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
