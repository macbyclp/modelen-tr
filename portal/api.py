"""Modelen Portal API v1: koordinatörler için programatik erişim.

portal.py tarafından `baglan(modul)` ile bağlanır. Kimlik doğrulama `Authorization: Bearer mdl_...` anahtarıdır (çerez ve CSRF yok).
Anahtarlar veritabanında yalnızca SHA-256 özeti olarak durur, oluşturulurken bir kez gösterilir, iptal edilebilir.
Herkese açık uç noktalar (dizin, sağlık, OpenAPI) CORS'a açıktır; anahtarlı uç noktalar değildir.

Adres doğrulama: koordinatör, adresinde `/.well-known/modelen-dogrulama.txt` dosyasında portalın verdiği değeri yayınlar; portal bunu
okur. Okuma SSRF'e karşı korunur: yalnızca https, yalnızca genel (global) IP'ler, 443/8443 portları, yönlendirme yok, 1 KB sınır.
"""
import hashlib
import http.client
import ipaddress
import json
import re
import secrets
import socket
import ssl
import time
from urllib.parse import urlparse

import api_sema
import eposta

P = None
ANAHTAR_ON = "mdl_"
MAKS_ANAHTAR = 5
NABIZ_DURUMLAR = ("calisiyor", "bekliyor", "bakimda", "durdu")
ALANLAR = ("ad", "kisa", "ayrinti", "baglanti", "adres", "hf", "iletisim")
DOGRULAMA_YOLU = "/.well-known/modelen-dogrulama.txt"
MESAJLAR = {"api-iptal": "Anahtar iptal edildi."}


class AdresHatasi(Exception):
    pass


def baglan(modul):
    global P
    P = modul
    P.MESAJLAR.update(MESAJLAR)
    P.db_hazirla_ek.append(semayi_kur)


def semayi_kur(c):
    c.executescript("""
    CREATE TABLE IF NOT EXISTS api_anahtarlari(
      id INTEGER PRIMARY KEY, kullanici_id INTEGER NOT NULL REFERENCES kullanicilar(id) ON DELETE CASCADE,
      ad TEXT NOT NULL, onek TEXT NOT NULL, ozet TEXT UNIQUE NOT NULL, olusturma INTEGER NOT NULL,
      son_kullanim INTEGER, iptal INTEGER NOT NULL DEFAULT 0);
    """)
    kol = [r["name"] for r in c.execute("PRAGMA table_info(basvurular)")]
    for ad, tanim in (("adres_dogrulandi", "INTEGER NOT NULL DEFAULT 0"), ("dogrulama_token", "TEXT NOT NULL DEFAULT ''"),
                      ("nabiz_zaman", "INTEGER"), ("nabiz_json", "TEXT NOT NULL DEFAULT ''")):
        if ad not in kol:
            c.execute(f"ALTER TABLE basvurular ADD COLUMN {ad} {tanim}")
    # adres değişince doğrulama kendiliğinden sıfırlanır (panel, API ve yönetici onayı dahil her yol)
    c.execute("""CREATE TRIGGER IF NOT EXISTS tr_adres_degisti AFTER UPDATE OF adres ON basvurular
                 WHEN old.adres <> new.adres
                 BEGIN UPDATE basvurular SET adres_dogrulandi=0, dogrulama_token='' WHERE id=new.id; END;""")


# ------------------------------------------------------------------ anahtarlar
def anahtar_ozet(a):
    return hashlib.sha256(a.encode()).hexdigest()


def anahtar_olustur(kid, ad):
    anahtar = ANAHTAR_ON + secrets.token_urlsafe(30)
    aid = P.yurut("INSERT INTO api_anahtarlari(kullanici_id,ad,onek,ozet,olusturma) VALUES(?,?,?,?,?)",
                  kid, ad, anahtar[:10], anahtar_ozet(anahtar), int(time.time())).lastrowid
    return aid, anahtar


def anahtardan_kullanici(h):
    """Bearer anahtarından kullanıcı satırı; yoksa None. Son kullanım zamanını (dakikada bir) günceller."""
    b = h.headers.get("Authorization", "")
    if not b.startswith("Bearer "):
        return None
    a = b[7:].strip()
    if not a.startswith(ANAHTAR_ON) or len(a) > 100:
        return None
    r = P.tek("SELECT a.id AS aid, a.son_kullanim, k.* FROM api_anahtarlari a JOIN kullanicilar k ON k.id=a.kullanici_id WHERE a.ozet=? AND a.iptal=0", anahtar_ozet(a))
    if r and (r["son_kullanim"] or 0) < time.time() - 60:
        P.yurut("UPDATE api_anahtarlari SET son_kullanim=? WHERE id=?", int(time.time()), r["aid"])
    return r


# ------------------------------------------------------------------ yanıt yardımcıları
def yanit(h, kod, nesne, cors=False, ek=None):
    e = {"Cache-Control": "no-store"}
    if cors:
        e = {"Access-Control-Allow-Origin": "*", "Cache-Control": "public, max-age=60"}
    e.update(ek or {})
    h._gonder(kod, json.dumps(nesne, ensure_ascii=False, separators=(",", ":")), "application/json; charset=utf-8", ek=e)


def hata(h, kod, kodu, mesaj, cors=False, ek=None):
    e = {"Cache-Control": "no-store"}
    if cors:
        e["Access-Control-Allow-Origin"] = "*"
    e.update(ek or {})
    h._gonder(kod, json.dumps({"hata": mesaj, "kod": kodu}, ensure_ascii=False, separators=(",", ":")), "application/json; charset=utf-8", ek=e)


def govde(h):
    n = int(h.headers.get("Content-Length", "0") or 0)
    if n <= 0:
        return {}
    if n > 65536:
        raise ValueError("gövde 64 KB'tan büyük")
    try:
        d = json.loads(h.rfile.read(n).decode("utf-8"))
    except Exception:
        raise ValueError("geçerli bir JSON gövdesi gerekli")
    if not isinstance(d, dict):
        raise ValueError("JSON gövdesi bir nesne olmalı")
    return d


# ------------------------------------------------------------------ kayıt gösterimi
def nabiz_durumu(b):
    """Son nabıza göre herkese açık durum."""
    if not b["nabiz_zaman"]:
        return {"durum": "bilinmiyor", "son_gorulme": None, "tur": None, "toplam_tur": None, "aktif_isci": None}
    try:
        n = json.loads(b["nabiz_json"] or "{}")
    except ValueError:
        n = {}
    yas = time.time() - b["nabiz_zaman"]
    if yas > 24 * 3600:
        durum = "bilinmiyor"
    elif n.get("durum") in ("bakimda", "durdu"):
        durum = n["durum"]
    else:
        durum = "cevrimici" if yas <= 15 * 60 else "gecikmeli"
    return {"durum": durum, "son_gorulme": b["nabiz_zaman"], "tur": n.get("tur"), "toplam_tur": n.get("toplam_tur"), "aktif_isci": n.get("aktif_isci")}


def sayfa_url(b):
    return f"{eposta.site()}/koordinator/{b['slug']}" if b["durum"] == "onaylandi" else None


def kayit_json(b):
    taslak = json.loads(b["taslak"]) if b["taslak"] else None
    gorsel = P.tek("SELECT COUNT(*) n FROM gorseller WHERE basvuru_id=?", b["id"])["n"]
    return {"slug": b["slug"], "ad": b["ad"], "kisa": b["kisa"], "ayrinti": b["ayrinti"], "baglanti": b["baglanti"], "adres": b["adres"], "hf": b["hf"],
            "iletisim": b["iletisim"], "durum": b["durum"], "yonetici_notu": b["yonetici_notu"], "taslak_var": bool(taslak),
            "adres_dogrulandi": bool(b["adres_dogrulandi"]), "gorsel_sayisi": gorsel, "sayfa": sayfa_url(b), "nabiz": nabiz_durumu(b)}


def ozet_json(b, tam=False):
    d = {"slug": b["slug"], "ad": b["ad"], "aciklama": b["kisa"], "adres": b["adres"] or None, "adres_dogrulandi": bool(b["adres_dogrulandi"]),
         "hf": b["hf"] or None, "baglanti": b["baglanti"] or None, "nabiz": nabiz_durumu(b), "sayfa": sayfa_url(b)}
    if tam:
        d["ayrinti"] = b["ayrinti"]
        d["gorseller"] = [f"{eposta.site()}/gorsel/{g['id']}" for g in P.sorgu("SELECT id FROM gorseller WHERE basvuru_id=? AND onayli=1 ORDER BY id", b["id"])]
    return d


# ------------------------------------------------------------------ yönlendirme
HERKESE_ACIK = ("/api/v1/saglik", "/api/v1/openapi.json", "/api/v1/koordinatorler")


def isle(h, yontem, yol, q):
    """portal._isle tarafından /api/ ile başlayan her istek için çağrılır."""
    ip = h._ip()
    acik = yol in HERKESE_ACIK or yol.startswith("/api/v1/koordinatorler/")
    if yontem == "OPTIONS":
        return h._gonder(204, b"", "text/plain", ek={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, OPTIONS",
                                                       "Access-Control-Allow-Headers": "Content-Type", "Access-Control-Max-Age": "600"})
    if P.hiz_asildi(("api-ip", ip), 240, 60):
        return hata(h, 429, "hiz_siniri", "Çok fazla istek; bir dakika sonra tekrar deneyin.", ek={"Retry-After": "60"})
    if acik:
        if yontem != "GET":
            return hata(h, 405, "yontem", "Bu uç nokta yalnızca GET kabul eder.", cors=True, ek={"Allow": "GET, OPTIONS"})
        return genel(h, yol, q)
    # ---- anahtarlı uç noktalar
    kullanici = anahtardan_kullanici(h)
    if not kullanici:
        if P.hiz_asildi(("api-yetkisiz", ip), 30, 600):
            return hata(h, 429, "hiz_siniri", "Çok fazla geçersiz anahtar denemesi.", ek={"Retry-After": "600"})
        return hata(h, 401, "yetkisiz", "Geçerli bir API anahtarı gerekli (Authorization: Bearer mdl_...).", ek={"WWW-Authenticate": "Bearer"})
    if P.hiz_asildi(("api-anahtar", kullanici["aid"]), 120, 60):
        return hata(h, 429, "hiz_siniri", "Anahtar başına dakikada en çok 120 istek.", ek={"Retry-After": "60"})
    try:
        yonlendir(h, yontem, yol, kullanici)
    except ValueError as ex:
        hata(h, 400, "gecersiz_istek", str(ex))


def genel(h, yol, q):
    if yol == "/api/v1/saglik":
        return yanit(h, 200, {"durum": "tamam", "zaman": int(time.time())}, cors=True, ek={"Cache-Control": "no-store"})
    if yol == "/api/v1/openapi.json":
        return yanit(h, 200, api_sema.sema(eposta.site()), cors=True, ek={"Cache-Control": "public, max-age=300"})
    if yol == "/api/v1/koordinatorler":
        satirlar = P.sorgu("SELECT * FROM basvurular WHERE durum='onaylandi' ORDER BY ad COLLATE NOCASE")
        return yanit(h, 200, {"surum": 1, "guncelleme": time.strftime("%Y-%m-%d"), "koordinatorler": [ozet_json(b) for b in satirlar]}, cors=True)
    slug = yol[len("/api/v1/koordinatorler/"):]
    b = P.tek("SELECT * FROM basvurular WHERE slug=? AND durum='onaylandi'", slug) if re.fullmatch(r"[a-z0-9\-]{1,60}", slug) else None
    if not b:
        return hata(h, 404, "yok", "Koordinatör bulunamadı.", cors=True)
    yanit(h, 200, ozet_json(b, tam=True), cors=True)


def yonlendir(h, yontem, yol, k):
    yollar = {"/api/v1/ben": ("GET",), "/api/v1/koordinator": ("GET", "POST", "PATCH"), "/api/v1/koordinator/nabiz": ("POST",),
              "/api/v1/koordinator/adres-dogrula": ("POST",), "/api/v1/koordinator/adres-dogrula/kontrol": ("POST",)}
    if yol not in yollar:
        return hata(h, 404, "yok", "Böyle bir uç nokta yok.")
    if yontem not in yollar[yol]:
        return hata(h, 405, "yontem", f"İzin verilen yöntemler: {', '.join(yollar[yol])}.", ek={"Allow": ", ".join(yollar[yol])})
    b = P.tek("SELECT * FROM basvurular WHERE kullanici_id=?", k["id"])
    if yol == "/api/v1/ben":
        return yanit(h, 200, {"id": k["id"], "ad": k["ad"], "eposta": k["eposta"], "eposta_dogrulandi": bool(k["eposta_dogrulandi"]), "rol": k["rol"],
                              "koordinator": {"slug": b["slug"], "ad": b["ad"], "durum": b["durum"]} if b else None})
    if yol == "/api/v1/koordinator":
        if yontem == "GET":
            return yanit(h, 200, kayit_json(b)) if b else hata(h, 404, "basvuru_yok", "Henüz koordinatör başvurunuz yok.")
        return kaydet(h, k, b, govde(h), olustur=(yontem == "POST"))
    if not b:
        return hata(h, 404, "basvuru_yok", "Henüz koordinatör başvurunuz yok.")
    if yol == "/api/v1/koordinator/nabiz":
        return nabiz(h, b, govde(h))
    if yol == "/api/v1/koordinator/adres-dogrula":
        return adres_baslat(h, b)
    adres_kontrol(h, k, b)


# ------------------------------------------------------------------ başvuru oluşturma / güncelleme
def kaydet(h, k, mevcut, d, olustur):
    bilinmeyen = [a for a in d if a not in ALANLAR]
    if bilinmeyen:
        return hata(h, 400, "bilinmeyen_alan", f"Bilinmeyen alan: {', '.join(sorted(bilinmeyen))}. İzin verilenler: {', '.join(ALANLAR)}.")
    if any(not isinstance(v, str) for v in d.values()):
        return hata(h, 400, "gecersiz_tur", "Tüm alanlar metin (string) olmalı.")
    if not P.hesap.dogrulanmis(k):
        return hata(h, 403, "eposta_dogrulanmadi", "Önce e-posta adresinizi doğrulayın.")
    if olustur and mevcut:
        return hata(h, 409, "basvuru_var", "Zaten bir koordinatör başvurunuz var; güncellemek için PATCH kullanın.")
    if not olustur and not mevcut:
        return hata(h, 404, "basvuru_yok", "Henüz koordinatör başvurunuz yok; önce POST ile oluşturun.")
    if mevcut and mevcut["durum"] == "askida":
        return hata(h, 409, "askida", "Başvurunuz askıda; değişiklik yapılamaz.")
    temel = {a: (mevcut[a] if mevcut else "") for a in ALANLAR}
    if mevcut and mevcut["taslak"]:
        temel.update(json.loads(mevcut["taslak"]))
    temel.update(d)
    dogru, sorun = P.basvuru_dogrula(temel, k["eposta"])
    if sorun:
        return hata(h, 400, "dogrulama", sorun)
    simdi = int(time.time())
    if not mevcut:
        bid = P.yurut("INSERT INTO basvurular(kullanici_id,slug,ad,kisa,ayrinti,baglanti,adres,iletisim,hf,olusturma,guncelleme) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                      k["id"], P.slug_uret(dogru["ad"]), dogru["ad"], dogru["kisa"], dogru["ayrinti"], dogru["baglanti"], dogru["adres"], dogru["iletisim"], dogru["hf"], simdi, simdi).lastrowid
        yeni = P.tek("SELECT * FROM basvurular WHERE id=?", bid)
        eposta.gonder(k["eposta"], *eposta.basvuru_alindi(k["ad"], yeni["ad"]))
        P.hesap.basvuru_yoneticiye(yeni, k["ad"])
        return yanit(h, 201, kayit_json(yeni))
    if mevcut["durum"] == "onaylandi":
        P.yurut("UPDATE basvurular SET taslak=?, guncelleme=? WHERE id=?", json.dumps(dogru, ensure_ascii=False), simdi, mevcut["id"])
        return yanit(h, 202, kayit_json(P.tek("SELECT * FROM basvurular WHERE id=?", mevcut["id"])))
    P.yurut("UPDATE basvurular SET ad=?,kisa=?,ayrinti=?,baglanti=?,adres=?,iletisim=?,hf=?,durum='beklemede',guncelleme=? WHERE id=?",
            dogru["ad"], dogru["kisa"], dogru["ayrinti"], dogru["baglanti"], dogru["adres"], dogru["iletisim"], dogru["hf"], simdi, mevcut["id"])
    yeni = P.tek("SELECT * FROM basvurular WHERE id=?", mevcut["id"])
    eposta.gonder(k["eposta"], *eposta.basvuru_alindi(k["ad"], yeni["ad"]))
    P.hesap.basvuru_yoneticiye(yeni, k["ad"])
    yanit(h, 200, kayit_json(yeni))


# ------------------------------------------------------------------ nabız
def nabiz(h, b, d):
    if b["durum"] != "onaylandi":
        return hata(h, 403, "onayli_degil", "Nabız yalnızca onaylı koordinatörler için kabul edilir.")
    if P.hiz_asildi(("nabiz", b["id"]), 6, 60):
        return hata(h, 429, "hiz_siniri", "Nabız dakikada en çok 6 kez gönderilebilir.", ek={"Retry-After": "30"})
    izinli = {"durum", "tur", "toplam_tur", "aktif_isci", "protokol", "surum", "mesaj"}
    if set(d) - izinli:
        return hata(h, 400, "bilinmeyen_alan", f"Bilinmeyen alan: {', '.join(sorted(set(d) - izinli))}.")
    if d.get("durum") not in NABIZ_DURUMLAR:
        return hata(h, 400, "gecersiz_durum", f"durum şunlardan biri olmalı: {', '.join(NABIZ_DURUMLAR)}.")
    for a in ("tur", "toplam_tur", "aktif_isci"):
        if a in d and (not isinstance(d[a], int) or isinstance(d[a], bool) or not 0 <= d[a] <= 10_000_000):
            return hata(h, 400, "gecersiz_sayi", f"{a} 0 ile 10.000.000 arasında tamsayı olmalı.")
    for a, m in (("protokol", 10), ("surum", 30), ("mesaj", 120)):
        if a in d and (not isinstance(d[a], str) or len(d[a]) > m):
            return hata(h, 400, "gecersiz_metin", f"{a} en çok {m} karakterlik metin olmalı.")
    simdi = int(time.time())
    P.yurut("UPDATE basvurular SET nabiz_zaman=?, nabiz_json=? WHERE id=?", simdi, json.dumps(d, ensure_ascii=False, separators=(",", ":")), b["id"])
    yanit(h, 200, {"tamam": True, "kaydedildi": simdi})


# ------------------------------------------------------------------ adres doğrulama
def adres_global_mi(ip):
    try:
        return ipaddress.ip_address(ip).is_global
    except ValueError:
        return False


def guvenli_getir(url, azami=1024, zaman=6):
    """Adres doğrulama dosyasını okur. SSRF'e karşı: yalnızca https, yalnızca genel IP'ler, 443/8443, yönlendirme yok, boyut sınırı."""
    u = urlparse(url)
    if u.scheme != "https" or not u.hostname or u.username or u.password:
        raise AdresHatasi("Yalnızca https adresleri okunur.")
    port = u.port or 443
    if port not in (443, 8443):
        raise AdresHatasi("Yalnızca 443 ve 8443 portları desteklenir.")
    host = u.hostname
    try:
        ipaddress.ip_address(host)
        raise AdresHatasi("Adres bir alan adı olmalı (IP adresi olamaz).")
    except ValueError:
        pass
    try:
        bilgi = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError:
        raise AdresHatasi("Alan adı çözümlenemedi.")
    ipler = [b[4][0] for b in bilgi]
    if not ipler or not all(adres_global_mi(i) for i in ipler):
        raise AdresHatasi("Adres genel internette değil (özel/yerel ağ adresleri okunmaz).")
    try:
        sock = socket.create_connection((ipler[0], port), timeout=zaman)
        ctx = ssl.create_default_context()
        c = http.client.HTTPSConnection(host, port, timeout=zaman, context=ctx)
        c.sock = ctx.wrap_socket(sock, server_hostname=host)
        c.request("GET", u.path or "/", headers={"User-Agent": "ModelenPortal/1 (adres-dogrulama)", "Accept": "text/plain"})
        r = c.getresponse()
        if r.status != 200:
            raise AdresHatasi(f"Dosya okunamadı (HTTP {r.status}).")
        veri = r.read(azami + 1)
    except AdresHatasi:
        raise
    except (OSError, ssl.SSLError, http.client.HTTPException) as ex:
        raise AdresHatasi(f"Bağlanılamadı ya da sertifika geçersiz ({type(ex).__name__}).")
    if len(veri) > azami:
        raise AdresHatasi("Dosya çok büyük.")
    return veri.decode("utf-8", errors="replace")


GETIR = guvenli_getir  # testler sahte okuyucu verebilir


def adres_baslat(h, b):
    if not b["adres"] or not b["adres"].startswith("https://"):
        return hata(h, 400, "adres_yok", "Önce https:// ile başlayan bir koordinatör adresi kaydedin.")
    t = b["dogrulama_token"] or ("modelen-dogrulama-" + secrets.token_urlsafe(18))
    P.yurut("UPDATE basvurular SET dogrulama_token=? WHERE id=?", t, b["id"])
    yanit(h, 200, {"adres": b["adres"], "dosya": b["adres"].rstrip("/") + DOGRULAMA_YOLU, "icerik": t})


def adres_kontrol(h, k, b):
    if not b["dogrulama_token"] or not b["adres"]:
        return hata(h, 400, "baslatilmadi", "Önce /koordinator/adres-dogrula ile doğrulamayı başlatın.")
    if P.hiz_asildi(("adres-kontrol", k["id"]), 10, 600):
        return hata(h, 429, "hiz_siniri", "10 dakikada en çok 10 kontrol.", ek={"Retry-After": "300"})
    try:
        metin = GETIR(b["adres"].rstrip("/") + DOGRULAMA_YOLU)
    except AdresHatasi as ex:
        return hata(h, 422, "okunamadi", str(ex))
    if metin.strip() != b["dogrulama_token"]:
        return hata(h, 422, "icerik_uyusmuyor", "Dosya bulundu ama içeriği beklenen değerle aynı değil.")
    P.yurut("UPDATE basvurular SET adres_dogrulandi=1, dogrulama_token='' WHERE id=?", b["id"])
    yanit(h, 200, {"adres_dogrulandi": True})


# ------------------------------------------------------------------ panel: API anahtarları sayfası
def web_get(h, yol, q):
    if yol != "/panel/api":
        return False
    if h._gerekli():
        sayfa(h, q)
    return True


def web_post(h, yol, f):
    if yol == "/panel/api-anahtar-olustur":
        olustur(h, f)
    elif yol == "/panel/api-anahtar-iptal":
        if f.get("id", "").isdigit():
            P.yurut("UPDATE api_anahtarlari SET iptal=1 WHERE id=? AND kullanici_id=?", int(f["id"]), h.kullanici["id"])
        h._yonlendir("/panel/api?m=api-iptal")
    else:
        return False
    return True


def sayfa(h, q, yeni_anahtar="", hata_metni=""):
    k = h.kullanici
    liste = P.sorgu("SELECT * FROM api_anahtarlari WHERE kullanici_id=? AND iptal=0 ORDER BY id", k["id"])
    satirlar = "".join(
        f'<tr><td>{P.e(a["ad"])}</td><td><code>{P.e(a["onek"])}…</code></td><td>{time.strftime("%Y-%m-%d", time.localtime(a["olusturma"]))}</td>'
        f'<td>{time.strftime("%Y-%m-%d %H:%M", time.localtime(a["son_kullanim"])) if a["son_kullanim"] else "—"}</td>'
        f'<td><form method="post" action="/panel/api-anahtar-iptal" class="satir">{P.csrf_alani(h.csrf)}<input type="hidden" name="id" value="{a["id"]}">'
        '<button class="btn ghost sm" type="submit">İptal et</button></form></td></tr>' for a in liste)
    tablo = (f'<div class="tscroll"><table class="xt"><thead><tr><th>Ad</th><th>Anahtar</th><th>Oluşturma</th><th>Son kullanım</th><th></th></tr></thead><tbody>{satirlar}</tbody></table></div>'
             if liste else "<p>Henüz API anahtarınız yok.</p>")
    yeni = (f'<p class="note"><b>Anahtarınız (bir daha gösterilmez, güvenli bir yere kaydedin):</b></p><p><code style="word-break:break-all">{P.e(yeni_anahtar)}</code></p>' if yeni_anahtar else "")
    form = ('<form class="kform" method="post" action="/panel/api-anahtar-olustur">' + P.csrf_alani(h.csrf)
            + P.alan("ad", "Anahtarın adı (ör. koordinatör sunucum)", "", ek='maxlength="40" required')
            + '<button class="btn accent" type="submit">Yeni anahtar oluştur</button></form>' if len(liste) < MAKS_ANAHTAR else f'<p class="note">En çok {MAKS_ANAHTAR} etkin anahtar. Yeni oluşturmak için birini iptal edin.</p>')
    h._html(200, "API anahtarları", P.pages.phead("Panel", "API anahtarları", "Koordinatör sunucunuzdan portala bağlanmak için. Anahtar parola gibidir; kimseyle paylaşmayın.")
            + P._mesaj_html(h, q) + (f'<p class="note">{P.e(hata_metni)}</p>' if hata_metni else "") + yeni + tablo + "<h2>Yeni anahtar</h2>" + form
            + '<p>Nasıl kullanılır: <a href="https://docs.modelen.tr/api/">API dokümantasyonu</a> · <a href="/panel">Panele dön</a></p>')


def olustur(h, f):
    k = h.kullanici
    ad = f.get("ad", "").strip()
    sorun = ("Anahtar adı 1-40 karakter olmalı." if not 1 <= len(ad) <= 40 else
             "Önce e-posta adresinizi doğrulayın." if not P.hesap.dogrulanmis(k) else
             f"En çok {MAKS_ANAHTAR} etkin anahtar olabilir." if P.tek("SELECT COUNT(*) n FROM api_anahtarlari WHERE kullanici_id=? AND iptal=0", k["id"])["n"] >= MAKS_ANAHTAR else
             "Çok sık anahtar oluşturuyorsunuz." if P.hiz_asildi(("api-olustur", k["id"]), 10, 3600) else "")
    if sorun:
        return sayfa(h, {}, hata_metni=sorun)
    _, anahtar = anahtar_olustur(k["id"], ad)
    sayfa(h, {}, yeni_anahtar=anahtar)
