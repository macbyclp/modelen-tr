"""Modelen portalı: kayıt / giriş, koordinatör başvurusu, herkese açık koordinatör sayfaları ve yönetici paneli.

Tek dosya, yalnızca standart kütüphane (SQLite + http.server). Sitenin statik sayfalarını da sunar, böylece
tek süreç tüm siteyi çalıştırır:

  py -3 portal/portal.py admin-olustur --eposta admin@ornek.org      # yönetici hesabı (parola sorulur)
  py -3 portal/portal.py calistir --port 8780                        # siteyi + portalı çalıştır
  py -3 portal/portal.py liste                                       # başvuruları terminalde göster

Güvenlik özeti: parolalar scrypt ile saklanır; oturum belirteci veritabanında yalnızca özet olarak durur;
çerezler HttpOnly + SameSite=Lax; formlarda CSRF belirteci; giriş/kayıt hız sınırı; tüm kullanıcı metni
kaçışlanır; SQL parametrelidir; iletişim e-postası yalnızca yöneticiye görünür. Eksikler: e-posta doğrulaması
ve parola sıfırlama yok (e-posta sunucusu yok), TLS bu sürecin dışında (ters vekil / barındırıcı) kurulmalı.
"""
import argparse
import hashlib
import hmac
import html
import json
import os
import re
import secrets
import sqlite3
import sys
import threading
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, unquote, urlparse

KOK = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(os.path.dirname(KOK), "site")
sys.path.insert(0, SITE)
import gorsel  # noqa: E402  (görsel doğrulama/temizleme)
import api  # noqa: E402  (koordinatör API'si)
import eposta  # noqa: E402  (SMTP gönderimi)
import hesap  # noqa: E402  (e-posta doğrulama, şifre sıfırlama, bildirimler)
import sosyal  # noqa: E402  (profil, takip, akış, moderasyon)
import build  # noqa: E402  (sitenin kabuğu: üst çubuk, menü, alt bilgi)
import content_en  # noqa: E402
import content_tr  # noqa: E402
import pages  # noqa: E402

SURE_OTURUM = 14 * 24 * 3600
MAKS_GORSEL = 2_000_000  # görsel başına bayt
MAKS_GORSEL_SAYISI = 4  # başvuru başına
MAKS_GOVDE = MAKS_GORSEL * MAKS_GORSEL_SAYISI + 200_000
DURUMLAR = {"beklemede": "İncelemede", "onaylandi": "Onaylandı", "reddedildi": "Reddedildi", "askida": "Askıda"}
STATIK_UZANTI = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8",
                 ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon", ".webp": "image/webp",
                 ".webmanifest": "application/manifest+json", ".txt": "text/plain; charset=utf-8", ".xml": "application/xml",
                 ".jpg": "image/jpeg", ".woff2": "font/woff2"}
MESAJLAR = {
    "kayit": "Hesabınız oluşturuldu.", "giris": "Giriş yaptınız.", "cikis": "Çıkış yaptınız.",
    "basvuru": "Başvurunuz kaydedildi ve incelemeye alındı.", "duzenleme": "Düzenlemeniz incelemeye alındı. Onaylanana kadar yayındaki sayfa değişmez.", "karar": "Karar kaydedildi.", "silindi": "Hesabınız ve verileriniz silindi.",
}

BAGLAM = {"db": None, "kil": threading.Lock(), "guvenli": False, "vekil": False}
db_hazirla_ek = []  # sosyal.py gibi eklentilerin şema kurucuları
HIZ = {}  # (anahtar) -> [zaman damgaları]


# ---------------------------------------------------------------- veritabanı
def db_ac(yol):
    os.makedirs(os.path.dirname(yol) or ".", exist_ok=True)
    c = sqlite3.connect(yol, check_same_thread=False, isolation_level=None)
    c.row_factory = sqlite3.Row
    c.executescript("""
    PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;
    CREATE TABLE IF NOT EXISTS kullanicilar(
      id INTEGER PRIMARY KEY, eposta TEXT UNIQUE NOT NULL, ad TEXT NOT NULL, parola TEXT NOT NULL,
      rol TEXT NOT NULL DEFAULT 'kullanici', olusturma INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS oturumlar(
      ozet TEXT PRIMARY KEY, kullanici_id INTEGER NOT NULL REFERENCES kullanicilar(id) ON DELETE CASCADE, bitis INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS basvurular(
      id INTEGER PRIMARY KEY, kullanici_id INTEGER UNIQUE NOT NULL REFERENCES kullanicilar(id) ON DELETE CASCADE,
      slug TEXT UNIQUE NOT NULL, ad TEXT NOT NULL, kisa TEXT NOT NULL, ayrinti TEXT NOT NULL DEFAULT '',
      baglanti TEXT NOT NULL DEFAULT '', adres TEXT NOT NULL DEFAULT '', iletisim TEXT NOT NULL,
      durum TEXT NOT NULL DEFAULT 'beklemede', yonetici_notu TEXT NOT NULL DEFAULT '',
      olusturma INTEGER NOT NULL, guncelleme INTEGER NOT NULL, karar_tarihi INTEGER);
    CREATE TABLE IF NOT EXISTS gorseller(
      id INTEGER PRIMARY KEY, basvuru_id INTEGER NOT NULL REFERENCES basvurular(id) ON DELETE CASCADE,
      tur TEXT NOT NULL, veri BLOB NOT NULL, genislik INTEGER NOT NULL, yukseklik INTEGER NOT NULL, olusturma INTEGER NOT NULL);
    """)
    kolonlar = [r["name"] for r in c.execute("PRAGMA table_info(basvurular)")]
    if "hf" not in kolonlar:  # eski veritabanı geçişleri
        c.execute("ALTER TABLE basvurular ADD COLUMN hf TEXT NOT NULL DEFAULT ''")
    if "taslak" not in kolonlar:  # onaylı profilde bekleyen düzenleme (JSON); yayındaki alanlar onaya kadar değişmez
        c.execute("ALTER TABLE basvurular ADD COLUMN taslak TEXT NOT NULL DEFAULT ''")
    if "onayli" not in [r["name"] for r in c.execute("PRAGMA table_info(gorseller)")]:
        c.execute("ALTER TABLE gorseller ADD COLUMN onayli INTEGER NOT NULL DEFAULT 1")
    for kur in db_hazirla_ek:
        kur(c)
    return c


def sorgu(sql, *p):
    with BAGLAM["kil"]:
        return BAGLAM["db"].execute(sql, p).fetchall()


def tek(sql, *p):
    r = sorgu(sql, *p)
    return r[0] if r else None


def yurut(sql, *p):
    with BAGLAM["kil"]:
        return BAGLAM["db"].execute(sql, p)


# ---------------------------------------------------------------- parola / oturum
def parola_ozet(parola, tuz=None):
    tuz = tuz or secrets.token_bytes(16)
    h = hashlib.scrypt(parola.encode("utf-8"), salt=tuz, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt$16384$8$1${tuz.hex()}${h.hex()}"


def parola_dogru(parola, kayit):
    try:
        _, n, r, p, tuz, h = kayit.split("$")
        yeni = hashlib.scrypt(parola.encode("utf-8"), salt=bytes.fromhex(tuz), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(yeni.hex(), h)
    except Exception:
        return False


def ozet(belirtec):
    return hashlib.sha256(belirtec.encode()).hexdigest()


def oturum_ac(kullanici_id):
    belirtec = secrets.token_urlsafe(32)
    yurut("INSERT INTO oturumlar(ozet,kullanici_id,bitis) VALUES(?,?,?)", ozet(belirtec), kullanici_id, int(time.time()) + SURE_OTURUM)
    return belirtec


def oturumdan_kullanici(belirtec):
    if not belirtec:
        return None
    yurut("DELETE FROM oturumlar WHERE bitis < ?", int(time.time()))
    return tek("SELECT k.* FROM oturumlar o JOIN kullanicilar k ON k.id=o.kullanici_id WHERE o.ozet=?", ozet(belirtec))


def hiz_asildi(anahtar, sinir, pencere):
    simdi = time.time()
    l = [t for t in HIZ.get(anahtar, []) if simdi - t < pencere]
    asildi = len(l) >= sinir
    if not asildi:
        l.append(simdi)
    HIZ[anahtar] = l
    return asildi


# ---------------------------------------------------------------- doğrulama
EPOSTA = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,120}\.[^@\s]{2,30}$")
TR_HARF = str.maketrans("çğıöşüÇĞİÖŞÜâîû", "cgiosuCGIOSUaiu")


def slug_uret(ad):
    s = re.sub(r"[^a-z0-9]+", "-", ad.translate(TR_HARF).lower()).strip("-")[:40] or "koordinator"
    taban, n = s, 2
    while tek("SELECT 1 FROM basvurular WHERE slug=?", s):
        s, n = f"{taban}-{n}", n + 1
    return s


def https_mi(a):
    return a.startswith("https://") and len(a) > 10 and len(a) <= 200 and not re.search(r"\s", a)


def http_mi(a):
    return (a.startswith("https://") or a.startswith("http://")) and len(a) > 8 and len(a) <= 200 and not re.search(r"\s", a)


def basvuru_dogrula(f, varsayilan_eposta):
    ad, kisa = f.get("ad", "").strip(), f.get("kisa", "").strip()
    ayrinti, baglanti = f.get("ayrinti", "").strip(), f.get("baglanti", "").strip()
    adres, iletisim = f.get("adres", "").strip().rstrip("/"), f.get("iletisim", "").strip() or varsayilan_eposta
    hf = f.get("hf", "").strip().rstrip("/")
    if not 2 <= len(ad) <= 60:
        return None, "Proje adı 2-60 karakter olmalı."
    if not 10 <= len(kisa) <= 200:
        return None, "Kısa açıklama 10-200 karakter olmalı."
    if len(ayrinti) > 5000:
        return None, "Ayrıntılı açıklama en çok 5000 karakter olabilir."
    if baglanti and not http_mi(baglanti):
        return None, "Web/depo bağlantısı http:// ya da https:// ile başlamalı."
    if adres and not https_mi(adres):
        return None, "Koordinatör adresi (boş bırakılabilir) https:// ile başlamalı."
    if hf and not (re.match(r"^https://(huggingface\.co|hf\.co)/[A-Za-z0-9_.\-/]+$", hf) and len(hf) <= 200):
        return None, "Hugging Face bağlantısı https://huggingface.co/... biçiminde olmalı."
    if not EPOSTA.match(iletisim) or len(iletisim) > 120:
        return None, "Geçerli bir iletişim e-postası yazın."
    return dict(ad=ad, kisa=kisa, ayrinti=ayrinti, baglanti=baglanti, adres=adres, iletisim=iletisim, hf=hf), None


# ---------------------------------------------------------------- multipart
def coz_multipart(govde, icerik_turu):
    """multipart/form-data gövdesini (alanlar, dosyalar) olarak ayrıştırır. Dosyalar: [(alan_adı, bayt)]."""
    m = re.search(r'boundary="?([^";]+)"?', icerik_turu)
    if not m:
        raise ValueError("sınır yok")
    sinir = b"--" + m.group(1).encode()
    alanlar, dosyalar = {}, []
    parcalar = govde.split(sinir)
    if len(parcalar) > 30:
        raise ValueError("çok parça")
    for parca in parcalar[1:]:
        if parca[:2] == b"--":
            break
        parca = parca[2:] if parca[:2] == b"\r\n" else parca
        bas, ayrac, icerik = parca.partition(b"\r\n\r\n")
        if not ayrac:
            continue
        if icerik.endswith(b"\r\n"):
            icerik = icerik[:-2]
        ad = re.search(rb'name="([^"]*)"', bas, re.I)
        if not ad:
            continue
        ad = ad.group(1).decode("utf-8", errors="replace")
        if re.search(rb'filename="', bas, re.I):
            if icerik:  # boş dosya alanı (seçilmedi) yok sayılır
                dosyalar.append((ad, icerik))
        else:
            alanlar[ad] = icerik.decode("utf-8", errors="replace")
    return alanlar, dosyalar


# ---------------------------------------------------------------- HTML
def e(x):
    """Kullanıcı metnini kaçışla; %% belirteçlerini (site şablon yer tutucuları) etkisizleştir."""
    return html.escape(str(x), quote=True).replace("%%", "&#37;&#37;")


def sayfa_html(baslik, govde, aciklama="Modelen koordinatör portalı"):
    """Site kabuğuna (menü, alt bilgi) sarılmış tam sayfa; bağlantılar köke göre yazılır."""
    anahtar = "_portal"
    content_tr.PAGES[anahtar] = dict(title=f"{baslik} · Modelen", desc=aciklama, body=govde)
    content_en.FILES[anahtar] = anahtar
    try:
        h = build.render(anahtar, "tr")
    finally:
        content_tr.PAGES.pop(anahtar, None)
        content_en.FILES.pop(anahtar, None)
    h = re.sub(r'(href|src)="(?!https?:|mailto:|/|#)([^"]*)"', r'\1="/\2"', h)
    h = re.sub(r'<link rel="(canonical|alternate)"[^>]*>\n?', "", h)
    h = re.sub(r'<meta property="og:url"[^>]*>\n?', "", h)
    h = re.sub(r'<a class="lang"[^>]*>.*?</a>', "", h, flags=re.S)
    h = re.sub(r'<a href="/en/_portal\.html"[^>]*>.*?</a>', "", h, flags=re.S)
    return h.replace('<meta name="viewport"', '<meta name="robots" content="noindex"><meta name="viewport"', 1)


def alan(ad, etiket, deger="", tur="text", ek=""):
    return f'<label>{etiket}<input name="{ad}" type="{tur}" value="{e(deger)}" {ek}></label>'


def csrf_alani(csrf):
    return f'<input type="hidden" name="csrf" value="{e(csrf)}">'


def paragraflar(metin):
    return "".join(f"<p>{e(p).replace(chr(10), '<br>')}</p>" for p in re.split(r"\n\s*\n", metin.strip()) if p.strip())


def durum_rozeti(d):
    return f'<span class="status">{e(DURUMLAR.get(d, d))}</span>'


AUTH_KALIP = re.compile(r'<!--AUTH--><span class="auth ([a-z\-]+)">.*?</span><!--/AUTH-->', re.S)


def auth_degistir(h, kullanici, csrf):
    """Giriş yapmış kullanıcıya üst çubukta Panel/Yönetim ve Çıkış göster (statik sayfalar dahil)."""
    if not kullanici:
        return h
    yonetici = kullanici["rol"] == "yonetici"
    yer, ad = ("/yonetim", "Yönetim") if yonetici else ("/panel", "Panel")
    en = '<html lang="en"' in h
    if en:
        ad = "Admin" if yonetici else "Panel"
    cikis = "Sign out" if en else "Çıkış"
    return AUTH_KALIP.sub(lambda m: (f'<span class="auth {m.group(1)}"><a href="{yer}">{ad}</a>'
                                     f'<form method="post" action="/cikis"><input type="hidden" name="csrf" value="{e(csrf)}">'
                                     f'<button type="submit">{cikis}</button></form></span>'), h)


def _mesaj_html(h, q):
    return h._mesaj(q)


# ---------------------------------------------------------------- işleyici
class H(BaseHTTPRequestHandler):
    server_version = "ModelenPortal"

    def log_message(self, *a):
        pass

    # ---- yardımcılar
    def _gonder(self, kod, govde, tip="text/html; charset=utf-8", ek=None, cerezler=None):
        if isinstance(govde, str):
            govde = govde.encode("utf-8")
        self.send_response(kod)
        self.send_header("Content-Type", tip)
        self.send_header("Content-Length", str(len(govde)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
                         "img-src 'self' data:; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
        if kod == 200 and tip.startswith("text/html") and (self.kullanici or self.yeni_cerezler):
            self.send_header("Cache-Control", "no-store")
        for k, v in (ek or {}).items():
            self.send_header(k, v)
        for c in (cerezler or []) + self.yeni_cerezler:
            self.send_header("Set-Cookie", c)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(govde)

    def _cerez(self, ad, deger, sure=None):
        c = f"{ad}={deger}; Path=/; HttpOnly; SameSite=Lax"
        if sure is not None:
            c += f"; Max-Age={sure}"
        if BAGLAM["guvenli"]:
            c += "; Secure"
        return c

    def _html(self, kod, baslik, govde, aciklama="Modelen koordinatör portalı"):
        self._gonder(kod, auth_degistir(sayfa_html(baslik, govde, aciklama), self.kullanici, self.csrf))

    def _yonlendir(self, yer, cerezler=None):
        self._gonder(303, b"", ek={"Location": yer}, cerezler=cerezler)

    def _mesaj(self, q):
        m = MESAJLAR.get((q.get("m") or [""])[0])
        return f'<p class="note">{e(m)}</p>' if m else ""

    def _form(self, maks=80_000):
        n = int(self.headers.get("Content-Length", "0") or 0)
        self.dosyalar = []
        if n < 0 or n > maks:
            return None
        veri = self.rfile.read(n)
        tur = self.headers.get("Content-Type", "")
        if tur.startswith("multipart/form-data"):
            try:
                alanlar, self.dosyalar = coz_multipart(veri, tur)
            except ValueError:
                return None
            return alanlar
        return {k: v[0] for k, v in parse_qs(veri.decode("utf-8", errors="replace"), keep_blank_values=True).items()}

    def _csrf_ok(self, f):
        return bool(self.csrf) and hmac.compare_digest(self.csrf, f.get("csrf", ""))

    def _ip(self):
        """İstemci IP'si. Ters vekil (Caddy/nginx) arkasında `--vekil` ile, yerel vekilin eklediği X-Forwarded-For kullanılır."""
        ip = self.client_address[0]
        if BAGLAM["vekil"] and ip in ("127.0.0.1", "::1"):
            xff = self.headers.get("X-Forwarded-For", "").split(",")[-1].strip()
            if xff:
                return xff[:45]
        return ip

    # ---- yönlendirme
    def _isle(self, yontem):
        u = urlparse(self.path)
        yol, q = unquote(u.path), parse_qs(u.query)
        if yol.startswith("/api/"):  # API: Bearer anahtarı, çerez ve CSRF yok
            self.yeni_cerezler, self.kullanici, self.csrf = [], None, ""
            try:
                return api.isle(self, yontem, yol, q)
            except Exception as ex:
                print("API HATA", yol, repr(ex), file=sys.stderr)
                return api.hata(self, 500, "sunucu", "Beklenmeyen bir hata oluştu.")
        ck = SimpleCookie(self.headers.get("Cookie", ""))
        self.yeni_cerezler = []
        self.csrf = ck["mc"].value if "mc" in ck and re.fullmatch(r"[A-Za-z0-9_\-]{20,80}", ck["mc"].value) else ""
        if not self.csrf:
            self.csrf = secrets.token_urlsafe(24)
            self.yeni_cerezler.append(self._cerez("mc", self.csrf))
        self.kullanici = oturumdan_kullanici(ck["ms"].value if "ms" in ck else "")
        try:
            if yontem not in ("GET", "POST"):
                return self._gonder(405, "Yöntem desteklenmiyor", "text/plain; charset=utf-8", ek={"Allow": "GET, POST"})
            if yontem == "POST":
                return self._post(yol)
            return self._get(yol, q)
        except Exception as ex:  # hata ayrıntısı kullanıcıya gösterilmez
            print("HATA", yol, repr(ex), file=sys.stderr)
            return self._html(500, "Hata", pages.phead("Hata", "Bir şeyler ters gitti."))

    def do_GET(self):
        self._isle("GET")

    do_HEAD = do_GET

    def do_PATCH(self):
        self._isle("PATCH")

    def do_OPTIONS(self):
        self._isle("OPTIONS")

    def do_DELETE(self):
        self._isle("DELETE")

    def do_POST(self):
        self._isle("POST")

    def _gerekli(self, yonetici=False):
        if not self.kullanici:
            self._yonlendir("/giris")
            return False
        if yonetici and self.kullanici["rol"] != "yonetici":
            self._html(403, "Yetkisiz", self._cerceve(pages.phead("Yetkisiz", "Bu sayfa yalnızca yöneticiler içindir.")))
            return False
        return True

    @staticmethod
    def _cerceve(icerik):
        return icerik  # site kabuğu içeriği zaten çerçeveliyor

    def _gerekli_degil_yonetici(self):
        self._html(403, "Yetkisiz", pages.phead("Yetkisiz", "Yönetici hesabı başvuru yapmaz.", "Başvuruları yalnızca görüntüler ve onaylarsınız."))

    # ---- GET
    def _get(self, yol, q):
        if hesap.get(self, yol, q) or api.web_get(self, yol, q) or sosyal.get(self, yol, q):
            return
        if yol == "/koordinatorler.json":
            return self._json_dizin()
        if yol in ("/koordinatorler", "/koordinatorler.html", "/en/koordinatorler.html"):
            return self._koordinatorler()
        if yol.startswith("/koordinator/"):
            return self._koordinator(yol[len("/koordinator/"):])
        if yol.startswith("/gorsel/"):
            return self._gorsel(yol[len("/gorsel/"):])
        if yol == "/kayit":
            return self._kayit_formu()
        if yol == "/giris":
            return self._giris_formu(q)
        if yol == "/panel":
            if not self._gerekli():
                return None
            if self.kullanici["rol"] == "yonetici":  # yönetici hesabı başvuru yapmaz; yalnızca görüntüler ve onaylar
                return self._yonlendir("/yonetim" + ("?m=" + q["m"][0] if q.get("m") else ""))
            return self._panel(q)
        if yol == "/yonetim":
            return self._yonetim(q) if self._gerekli(True) else None
        if yol.startswith("/yonetim/basvuru/"):
            return self._yonetim_basvuru(yol[len("/yonetim/basvuru/"):]) if self._gerekli(True) else None
        return self._statik(yol)

    def _statik(self, yol):
        if yol in ("", "/"):
            yol = "/index.html"
        goreli = os.path.normpath(yol.lstrip("/")).replace("\\", "/")
        tam = os.path.realpath(os.path.join(SITE, goreli))
        uz = os.path.splitext(tam)[1].lower()
        if (not tam.startswith(os.path.realpath(SITE) + os.sep) or uz not in STATIK_UZANTI or any(p.startswith(".") and p != ".well-known" for p in goreli.split("/"))
                or not os.path.isfile(tam)):
            k404 = os.path.join(SITE, "404.html")
            icerik = b"404"
            if os.path.exists(k404):
                with open(k404, "rb") as f:
                    icerik = f.read()
            return self._gonder(404, icerik)
        with open(tam, "rb") as f:
            veri = f.read()
        if uz == ".html":
            veri = auth_degistir(veri.decode("utf-8"), self.kullanici, self.csrf).encode("utf-8")
            return self._gonder(200, veri, STATIK_UZANTI[uz], ek={"Cache-Control": "private, no-cache"})
        self._gonder(200, veri, STATIK_UZANTI[uz], ek={"Cache-Control": "public, max-age=300"})

    def _gorsel(self, kimlik):
        r = tek("SELECT g.tur, g.veri, g.onayli, b.durum, b.kullanici_id FROM gorseller g JOIN basvurular b ON b.id=g.basvuru_id WHERE g.id=?", kimlik) if kimlik.isdigit() else None
        herkese_acik = bool(r) and r["durum"] == "onaylandi" and r["onayli"] == 1
        sahip_ya_da_yonetici = bool(r) and self.kullanici and (self.kullanici["rol"] == "yonetici" or self.kullanici["id"] == r["kullanici_id"])
        if not r or not (herkese_acik or sahip_ya_da_yonetici):
            return self._statik("/__yok__.html")
        self._gonder(200, bytes(r["veri"]), gorsel.TURLER[r["tur"]],
                     ek={"Cache-Control": "public, max-age=3600" if herkese_acik else "private, no-store", "Content-Disposition": "inline"})

    def _gorseller_html(self, basvuru_id, ad, hepsi=False):
        """Galeri. hepsi=False: herkese açık görünüm (yalnızca onaylı görseller); hepsi=True: sahibi/yönetici (onay bekleyenler rozetli)."""
        satirlar = sorgu("SELECT id, onayli FROM gorseller WHERE basvuru_id=?" + ("" if hepsi else " AND onayli=1") + " ORDER BY id", basvuru_id)
        if not satirlar:
            return ""
        return '<div class="galeri">' + "".join(
            f'<div><a href="/gorsel/{g["id"]}" target="_blank" rel="noopener"><img src="/gorsel/{g["id"]}" alt="{e(ad)} görseli {n}" loading="lazy"></a>'
            + ('' if g["onayli"] else '<p><span class="status">Onay bekliyor</span></p>') + "</div>" for n, g in enumerate(satirlar, 1)) + "</div>"

    def _json_dizin(self):
        satirlar = sorgu("SELECT ad,adres,kisa FROM basvurular WHERE durum='onaylandi' AND adres<>'' ORDER BY ad COLLATE NOCASE")
        d = {"surum": 1, "guncelleme": time.strftime("%Y-%m-%d"),
             "koordinatorler": [{"ad": r["ad"], "adres": r["adres"], "aciklama": r["kisa"], "onayli": True} for r in satirlar]}
        self._gonder(200, json.dumps(d, ensure_ascii=False), "application/json; charset=utf-8", ek={"Cache-Control": "public, max-age=120"})

    def _kapak(self, r):
        g = tek("SELECT id FROM gorseller WHERE basvuru_id=? AND onayli=1 ORDER BY id LIMIT 1", r["id"])
        return f'<a href="/koordinator/{e(r["slug"])}"><img class="kapak" src="/gorsel/{g["id"]}" alt="{e(r["ad"])}" loading="lazy"></a>' if g else ""

    def _koordinatorler(self):
        satirlar = sorgu("SELECT * FROM basvurular WHERE durum='onaylandi' ORDER BY ad COLLATE NOCASE")
        if satirlar:
            kartlar = "".join(
                f'<div>{self._kapak(r)}<h3><a href="/koordinator/{e(r["slug"])}">{e(r["ad"])}</a></h3><p>{e(r["kisa"])}</p>'
                f'<p class="note">{"GPU adanabilir (uygulamada listelenir)" if r["adres"] else "Koordinatör adresi henüz yok"}</p>'
                f'<a class="btn" href="/koordinator/{e(r["slug"])}">Ayrıntılar</a></div>' for r in satirlar)
            liste = f'<div class="cards2">{kartlar}</div>'
        else:
            liste = '<p class="note">Henüz onaylanmış koordinatör yok. İlk koordinatör siz olabilirsiniz.</p>'
        govde = self._cerceve(pages.phead("Koordinatörler", "Gönüllü GPU'larla çalışan projeler.",
                                          "Yöneticilerin onayladığı koordinatörler. Birine tıklayarak ne yaptığını görebilirsiniz.")
                              + liste + '<p><a class="btn accent" href="/kayit">Koordinatör olmak istiyorum</a></p>')
        self._html(200, "Koordinatörler", govde, "Modelen'de onaylanmış koordinatörler ve çalıştıkları projeler.")

    def _koordinator(self, slug):
        r = tek("SELECT * FROM basvurular WHERE slug=? AND durum='onaylandi'", slug)
        if not r:
            return self._statik("/__yok__.html")
        ayrinti = paragraflar(r["ayrinti"]) if r["ayrinti"].strip() else f"<p>{e(r['kisa'])}</p>"
        bilgi = [("Proje", e(r["ad"])), ("Özet", e(r["kisa"]))]
        if r["baglanti"]:
            bilgi.append(("Web / depo", f'<a href="{e(r["baglanti"])}" rel="noopener nofollow noreferrer">{e(r["baglanti"])}</a>'))
        if r["hf"]:
            bilgi.append(("Hugging Face", f'<a href="{e(r["hf"])}" rel="noopener nofollow noreferrer">{e(r["hf"])}</a>'))
        bilgi.append(("Koordinatör adresi", f"<code>{e(r['adres'])}</code> (uygulamada seçilebilir)" if r["adres"] else "Henüz yok; uygulamada listelenmez"))
        sahip = tek("SELECT * FROM kullanicilar WHERE id=?", r["kullanici_id"])
        if sahip and sosyal.acik_mi(sahip) and sahip["kullanici_adi"]:
            bilgi.append(("Koordinatör profili", f'<a href="/u/{e(sahip["kullanici_adi"])}">@{e(sahip["kullanici_adi"])}</a>'))
        bilgi.append(("Onay tarihi", time.strftime("%Y-%m-%d", time.localtime(r["karar_tarihi"] or r["guncelleme"]))))
        govde = self._cerceve(pages.phead("Koordinatör", e(r["ad"]), e(r["kisa"])) + pages.kv(bilgi) + "<h2>Neler yapıyor?</h2>" + ayrinti + self._gorseller_html(r["id"], r["ad"])
                              + '<p class="note">Bu bilgileri koordinatörün kendisi yazdı; Modelen yöneticileri başvuruyu onayladı. '
                                'GPU adamadan önce açıklamayı okuyun.</p><p><a class="btn ghost" href="/koordinatorler">Tüm koordinatörler</a></p>')
        self._html(200, r["ad"], govde, r["kisa"])

    def _kayit_formu(self, hata="", f=None):
        f = f or {}
        govde = self._cerceve(
            pages.phead("Kayıt ol", "Hesap oluştur.", "Koordinatör başvurusu için bir hesap gerekir. Gönüllü olmak için hesap gerekmez.")
            + (f'<p class="note">{e(hata)}</p>' if hata else "")
            + '<form class="kform" method="post" action="/kayit">' + csrf_alani(self.csrf)
            + alan("ad", "Adınız (ya da takma adınız)", f.get("ad", ""), ek='maxlength="60" required')
            + alan("eposta", "E-posta", f.get("eposta", ""), "email", 'maxlength="120" required autocomplete="email"')
            + alan("parola", "Parola (en az 10 karakter)", "", "password", 'minlength="10" maxlength="200" required autocomplete="new-password"')
            + alan("parola2", "Parola (tekrar)", "", "password", 'minlength="10" maxlength="200" required autocomplete="new-password"')
            + '<label class="chk"><input type="checkbox" name="kabul" value="1" required> <span><a href="/kvkk.html">Aydınlatma Metni</a>\'ni okudum; '
              'e-postamın ve girdiğim bilgilerin başvurum için işlenmesini kabul ediyorum.</span></label>'
            + '<button class="btn accent" type="submit">Kayıt ol</button></form>'
            + '<p>Hesabınız var mı? <a href="/giris">Giriş yapın</a>.</p>')
        self._html(200, "Kayıt ol", govde)

    def _giris_formu(self, q, hata="", eposta=""):
        govde = self._cerceve(
            pages.phead("Giriş yap", "Hesabınıza girin.") + self._mesaj(q) + (f'<p class="note">{e(hata)}</p>' if hata else "")
            + '<form class="kform" method="post" action="/giris">' + csrf_alani(self.csrf)
            + alan("eposta", "E-posta", eposta, "email", 'maxlength="120" required autocomplete="email"')
            + alan("parola", "Parola", "", "password", 'maxlength="200" required autocomplete="current-password"')
            + '<button class="btn accent" type="submit">Giriş yap</button></form><p><a href="/sifre-sifirla">Şifremi unuttum</a></p><p>Hesabınız yok mu? <a href="/kayit">Kayıt olun</a>.</p>')
        self._html(200, "Giriş yap", govde)

    # ---- kullanıcı paneli
    def _basvuru_formu(self, b=None, hata="", duzenleme=False):
        b = b or {}
        return ((f'<p class="note">{e(hata)}</p>' if hata else "")
                + '<form class="kform" method="post" action="/basvuru" enctype="multipart/form-data">' + csrf_alani(self.csrf)
                + alan("ad", "Proje / koordinatör adı", b.get("ad", ""), ek='maxlength="60" required')
                + f'<label>Kısa açıklama (10-200 karakter; listelerde görünür)<textarea name="kisa" maxlength="200" rows="3" required>{e(b.get("kisa", ""))}</textarea></label>'
                + f'<label>Ayrıntılı açıklama: ne yapıyorsunuz, hangi veri ve lisansla, GPU\'ları nasıl kullanacaksınız? (en çok 5000 karakter, herkese açık sayfada görünür)<textarea name="ayrinti" maxlength="5000" rows="10">{e(b.get("ayrinti", ""))}</textarea></label>'
                + alan("baglanti", "Web sitesi ya da depo bağlantısı (isteğe bağlı)", b.get("baglanti", ""), "url", 'maxlength="200" placeholder="https://"')
                + alan("hf", "Hugging Face bağlantısı: profil, organizasyon, model ya da veri kümesi (isteğe bağlı)", b.get("hf", ""), "url", 'maxlength="200" placeholder="https://huggingface.co/..."')
                + alan("adres", "Koordinatör adresi (isteğe bağlı; https://… ile başlamalı)", b.get("adres", ""), "url", 'maxlength="200" placeholder="https://"')
                + '<p class="note">Adres yoksa sorun değil: projeniz sitede görünür. Gönüllüler GPU\'larını yalnızca adresi olan koordinatörlere adayabilir.</p>'
                + alan("iletisim", "İletişim e-postası (yalnızca yöneticiler görür)", b.get("iletisim", self.kullanici["eposta"] if self.kullanici else ""), "email", 'maxlength="120"')
                + f'<label>Görseller (isteğe bağlı; PNG, JPEG ya da WebP; her biri en çok 2 MB, toplam en çok {MAKS_GORSEL_SAYISI})<input name="gorsel" type="file" accept="image/png,image/jpeg,image/webp" multiple></label>'
                + '<p class="note">Yüklediğiniz görseller onaylanınca herkese açık sayfanızda görünür. Fotoğraflardaki konum ve cihaz bilgileri (EXIF) otomatik silinir.</p>'
                + f'<button class="btn accent" type="submit">{"Düzenlemeyi incelemeye gönder" if duzenleme else "Başvuruyu kaydet"}</button></form>'
                + self._yuklu_gorseller(b))

    def _yuklu_gorseller(self, b):
        """Mevcut görseller ve silme düğmeleri (ayrı formlar: iç içe form olmaz)."""
        if not b or not b.get("id"):
            return ""
        satirlar = sorgu("SELECT id, onayli FROM gorseller WHERE basvuru_id=? ORDER BY id", b["id"])
        if not satirlar:
            return ""
        return ("<h3>Yüklü görseller</h3><div class=\"galeri\">" + "".join(
            f'<div><img src="/gorsel/{g["id"]}" alt="Yüklü görsel" loading="lazy">' + ("" if g["onayli"] else '<p><span class="status">Onay bekliyor</span></p>')
            + '<form method="post" action="/gorsel-sil">'
            + csrf_alani(self.csrf) + f'<input type="hidden" name="id" value="{g["id"]}"><button class="btn ghost sm" type="submit">Sil</button></form></div>'
            for g in satirlar) + "</div>")

    PANEL_SEKMELER = [("genel", "Genel bakış"), ("basvuru", "Başvuru"), ("profil", "Profil ve topluluk"), ("gelistirici", "Geliştiriciler"), ("hesap", "Hesap")]

    def _panel_genel(self, b, k):
        def kart(baslik, deger, alt=""):
            return f'<div class="pk"><span class="pk-b">{e(baslik)}</span><strong>{deger}</strong>' + (f'<span class="pk-a">{alt}</span>' if alt else "") + "</div>"
        n_anahtar = tek("SELECT COUNT(*) n FROM api_anahtarlari WHERE kullanici_id=? AND iptal=0", k["id"])["n"]
        if b is None:
            kartlar = kart("Başvuru", "Yok", '<a href="/panel?s=basvuru">Başvuru yap</a>')
        else:
            nabiz = api.nabiz_durumu(b)["durum"] if b["durum"] == "onaylandi" else None
            nabiz_ad = {"cevrimici": "Çevrimiçi", "gecikmeli": "Gecikmeli", "bakimda": "Bakımda", "durdu": "Durdu", "bilinmiyor": "Bilinmiyor"}
            kartlar = (kart("Başvuru", durum_rozeti(b["durum"]), '<a href="/panel?s=basvuru">Ayrıntı</a>')
                       + kart("Koordinatör adresi", "Doğrulandı" if b["adres_dogrulandi"] else ("Doğrulanmadı" if b["adres"] else "Yok"),
                              '<a href="https://docs.modelen.tr/adres-dogrulama/" rel="noopener">Nasıl doğrulanır?</a>' if b["adres"] and not b["adres_dogrulandi"] else "")
                       + (kart("Nabız", nabiz_ad.get(nabiz, "—"), '<a href="https://docs.modelen.tr/nabiz/" rel="noopener">Nabız nedir?</a>') if nabiz else ""))
        kartlar += kart("API anahtarı", str(n_anahtar), '<a href="/panel/api">Yönet</a>')
        icerik = f'<div class="pkartlar">{kartlar}</div>'
        if b is not None:
            if b["yonetici_notu"]:
                icerik += f'<p class="note"><b>Yönetici notu:</b> {e(b["yonetici_notu"])}</p>'
            if b["durum"] == "onaylandi":
                icerik += f'<p>Sayfanız yayında: <a href="/koordinator/{e(b["slug"])}">/koordinator/{e(b["slug"])}</a></p>'
                if b["taslak"]:
                    icerik += '<p class="note"><b>Düzenlemeniz incelemede.</b> Yönetici onaylayana kadar yayındaki sayfa değişmez.</p>'
        icerik += ('<h2>Hızlı işlemler</h2><p><a class="btn" href="/panel?s=basvuru">Başvuruyu düzenle</a> <a class="btn ghost" href="/profil">Profilim</a> '
                   '<a class="btn ghost" href="/akis">Topluluk akışı</a> <a class="btn ghost" href="https://docs.modelen.tr" rel="noopener">Dokümantasyon</a></p>')
        return icerik

    def _panel(self, q, hata="", form=None):
        k = self.kullanici
        b = tek("SELECT * FROM basvurular WHERE kullanici_id=?", k["id"])
        sekme = (q.get("s") or ["genel"])[0]
        if hata and sekme == "genel":
            sekme = "basvuru"  # başvuru formu hataları formun olduğu sekmede gösterilir
        if sekme not in dict(self.PANEL_SEKMELER):
            sekme = "genel"
        ust = self._mesaj(q) + hesap.dogrulama_notu(self)
        yan = ('<aside class="panel-yan"><div class="panel-kisi"><span class="avatar bos" aria-hidden="true">' + e((k["ad"] or "?")[:1].upper()) + '</span>'
               f'<div><b>{e(k["ad"])}</b><span>{e(k["eposta"])}</span></div></div><nav aria-label="Panel bölümleri">'
               + "".join(f'<a href="/panel?s={ad}"' + (' aria-current="page" class="aktif"' if ad == sekme else "") + f">{e(et)}</a>" for ad, et in self.PANEL_SEKMELER)
               + '</nav></aside>')
        if sekme == "genel":
            baslik, icerik = f"Merhaba, {k['ad']}.", self._panel_genel(b, k)
        elif sekme == "basvuru":
            baslik = "Başvuru"
            if b is None:
                icerik = "<p>Başvurunuz yönetici tarafından incelenir; sonuç bu sayfada görünür.</p>" + self._basvuru_formu(form, hata)
            else:
                icerik = f'<p>Durum: {durum_rozeti(b["durum"])}</p>'
                if b["yonetici_notu"]:
                    icerik += f'<p class="note"><b>Yönetici notu:</b> {e(b["yonetici_notu"])}</p>'
                if b["durum"] == "onaylandi":
                    icerik += (f'<p>Sayfanız yayında: <a href="/koordinator/{e(b["slug"])}">/koordinator/{e(b["slug"])}</a></p>'
                               + pages.kv([("Proje", e(b["ad"])), ("Özet", e(b["kisa"])), ("Hugging Face", e(b["hf"]) or "yok"), ("Adres", e(b["adres"]) or "yok")])
                               + self._gorseller_html(b["id"], b["ad"]))
                    taslak = json.loads(b["taslak"]) if b["taslak"] else None
                    acik = " open" if (hata or form or taslak) else ""
                    icerik += (f'<details class="duzenle"{acik}><summary><b>Bilgilerinizi düzenleyin</b></summary>'
                               + ('<p class="note"><b>Düzenlemeniz incelemede.</b> Yönetici onaylayana kadar yayındaki sayfa değişmez; yeniden gönderirseniz önceki düzenlemenin yerine geçer.</p>' if taslak else
                                  '<p class="note">Değişiklikleriniz yönetici onayından sonra yayına girer; o zamana kadar yayındaki sayfa değişmez.</p>')
                               + self._basvuru_formu(form or {**dict(b), **(taslak or {})}, hata, duzenleme=True) + '</details>')
                else:
                    icerik += self._basvuru_formu(form or dict(b), hata)
        elif sekme == "profil":
            baslik = "Profil ve topluluk"
            icerik = ('<p>Profiliniz varsayılan olarak özeldir; paylaşmayı siz seçersiniz.</p>'
                      '<p><a class="btn" href="/profil">Profilimi düzenle</a> <a class="btn ghost" href="/akis">Topluluk akışı</a></p>')
        elif sekme == "gelistirici":
            baslik = "Geliştiriciler"
            icerik = ('<p>Koordinatörünüzü portala programla bağlayın: API anahtarları, nabız ve adres doğrulama.</p>'
                      '<p><a class="btn" href="/panel/api">API anahtarları</a> <a class="btn ghost" href="https://docs.modelen.tr" rel="noopener">Dokümantasyon</a></p>')
        else:
            baslik = "Hesap"
            icerik = ((f'<p class="note">{e(hata)}</p>' if hata else "")
                      + '<form method="post" action="/cikis">' + csrf_alani(self.csrf) + '<button class="btn ghost" type="submit">Çıkış yap</button></form>'
                      '<details><summary>Hesabımı ve verilerimi sil</summary><form class="kform" method="post" action="/hesap-sil">'
                      + csrf_alani(self.csrf) + alan("parola", "Parolanız (onay)", "", "password", 'maxlength="200" required')
                      + '<p class="note">Hesabınız, başvurunuz ve sayfanız kalıcı olarak silinir.</p><button class="btn" type="submit">Hesabı sil</button></form></details>')
        if k["rol"] == "yonetici":
            icerik += '<p><a class="btn accent" href="/yonetim">Yönetici paneli</a></p>'
        ana = f'<section class="panel-ic"><h1 class="panel-b">{e(baslik)}</h1>{ust}{icerik}</section>'
        self._html(200, "Panel", self._cerceve(f'<div class="panel-duzen">{yan}{ana}</div>'))

    # ---- yönetici paneli
    def _yonetim(self, q):
        durum = (q.get("durum") or ["hepsi"])[0]
        sayilar = {r["durum"]: r["n"] for r in sorgu("SELECT durum, COUNT(*) n FROM basvurular GROUP BY durum")}
        n_duzenleme = tek("SELECT COUNT(*) n FROM basvurular WHERE taslak<>''")["n"]
        sayilar["duzenleme"] = n_duzenleme
        sekme = "".join(f'<a class="btn{"" if d == durum else " ghost"}" href="/yonetim?durum={d}">{e(ad)} ({sayilar.get(d, 0) if d != "hepsi" else sum(v for k, v in sayilar.items() if k != "duzenleme")})</a> '
                        for d, ad in [("hepsi", "Hepsi"), ("beklemede", "İncelemede"), ("duzenleme", "Düzenleme bekleyen"), ("onaylandi", "Onaylı"), ("reddedildi", "Reddedilen"), ("askida", "Askıda")])
        sql = "SELECT b.*, k.eposta AS hesap, k.ad AS hesap_ad FROM basvurular b JOIN kullanicilar k ON k.id=b.kullanici_id"
        kosul, arg = (" WHERE b.durum=?", [durum]) if durum in DURUMLAR else ((" WHERE b.taslak<>''", []) if durum == "duzenleme" else ("", []))
        satirlar = sorgu(sql + kosul + " ORDER BY b.guncelleme DESC", *arg)
        tablo = pages.table(["#", "Proje", "Durum", "Başvuran (hesap)", "İletişim e-postası", "Adres", "Güncelleme"],
                            [[r["id"], f'<a href="/yonetim/basvuru/{r["id"]}">{e(r["ad"])}</a>', e(DURUMLAR[r["durum"]]) + (" · düzenleme bekliyor" if r["taslak"] else ""), e(f'{r["hesap_ad"]} · {r["hesap"]}'),
                             e(r["iletisim"]), e(r["adres"]) or "—", time.strftime("%Y-%m-%d %H:%M", time.localtime(r["guncelleme"]))] for r in satirlar],
                            num_from=99) if satirlar else '<p class="note">Bu durumda başvuru yok.</p>'
        n_kullanici = tek("SELECT COUNT(*) n FROM kullanicilar")["n"]
        n_sikayet = tek("SELECT COUNT(*) n FROM sikayetler WHERE durum='acik'")["n"]
        sekme += f'<a class="btn accent" href="/yonetim/moderasyon">Moderasyon ({n_sikayet})</a>'
        self._html(200, "Yönetim", pages.phead("Yönetim", "Koordinatör başvuruları", f"{n_kullanici} kayıtlı hesap")
                   + self._mesaj(q) + f"<p>{sekme}</p>" + tablo
                   + f'<p>{e(self.kullanici["eposta"])} (yönetici) · <form method="post" action="/cikis" style="display:inline">'
                     + csrf_alani(self.csrf) + '<button class="btn ghost sm" type="submit">Çıkış yap</button></form></p>')

    def _yonetim_basvuru(self, kimlik):
        r = tek("SELECT b.*, k.eposta AS hesap, k.ad AS hesap_ad FROM basvurular b JOIN kullanicilar k ON k.id=b.kullanici_id WHERE b.id=?", kimlik) if kimlik.isdigit() else None
        if not r:
            return self._html(404, "Bulunamadı", self._cerceve(pages.phead("Bulunamadı", "Böyle bir başvuru yok.")))
        etiketler = [("onaylandi", "Onayla"), ("reddedildi", "Reddet"), ("askida", "Askıya al"), ("beklemede", "İncelemeye al")]
        taslak = json.loads(r["taslak"]) if r["taslak"] else None
        if taslak:  # bekleyen düzenleme: önce onay/ret; genel durum düğmeleri geri planda
            etiketler = [("duzenleme-onayla", "Düzenlemeyi onayla"), ("duzenleme-reddet", "Düzenlemeyi reddet")] + [x for x in etiketler if x[0] in ("askida",)]
        butonlar = "".join(f'<button class="btn{"" if k in ("onaylandi", "duzenleme-onayla") else " ghost"}" name="karar" value="{k}" type="submit">{e(ad)}</button> '
                           for k, ad in etiketler)
        alan_adlari = {"ad": "Proje adı", "kisa": "Kısa açıklama", "ayrinti": "Ayrıntılı açıklama", "baglanti": "Web / depo", "adres": "Koordinatör adresi", "iletisim": "İletişim e-postası", "hf": "Hugging Face"}
        fark = ""
        if taslak:
            satirlar_f = [(alan_adlari[a], e(r[a]) or "—", e(v) or "—") for a, v in taslak.items() if a in alan_adlari and v != r[a]]
            fark = ("<h2>Bekleyen düzenleme</h2>" + (pages.table(["Alan", "Yayındaki", "Önerilen"], satirlar_f, num_from=99) if satirlar_f else "<p>Yalnızca görsel değişikliği var.</p>")
                    + "<p>Yeni görseller (rozetli) onaylanırsa yayına girer:</p>" + self._gorseller_html(r["id"], r["ad"], hepsi=True))
        govde = (pages.phead("Başvuru", e(r["ad"]), "") + f'<p>Durum: {durum_rozeti(r["durum"])}</p>'
                 + pages.kv([("Hesap", e(f'{r["hesap_ad"]} · {r["hesap"]}')), ("İletişim e-postası", f'<a href="mailto:{e(r["iletisim"])}">{e(r["iletisim"])}</a>'),
                             ("Kısa açıklama", e(r["kisa"])), ("Web / depo", e(r["baglanti"]) or "—"), ("Hugging Face", e(r["hf"]) or "—"), ("Koordinatör adresi", e(r["adres"]) or "yok"),
                             ("Sayfa", f'/koordinator/{e(r["slug"])}'),
                             ("Başvuru", time.strftime("%Y-%m-%d %H:%M", time.localtime(r["olusturma"])))])
                 + "<h2>Ayrıntılı açıklama</h2>" + (paragraflar(r["ayrinti"]) or "<p>—</p>") + (fark or self._gorseller_html(r["id"], r["ad"], hepsi=True))
                 + '<h2>Karar</h2><form class="kform" method="post" action="/yonetim/karar">' + csrf_alani(self.csrf)
                 + f'<input type="hidden" name="id" value="{r["id"]}">'
                 + f'<label>Başvurana görünecek not (isteğe bağlı)<textarea name="not" maxlength="500" rows="3">{e(r["yonetici_notu"])}</textarea></label>'
                 + f"<p>{butonlar}</p></form>" + '<p><a class="btn ghost" href="/yonetim">Listeye dön</a></p>')
        self._html(200, "Başvuru", self._cerceve(govde))

    # ---- POST
    def _post(self, yol):
        if yol in ("/basvuru", "/profil") and not self.kullanici:  # büyük gövdeyi girişsiz okuma
            return self._yonlendir("/giris")
        f = self._form(MAKS_GOVDE if yol == "/basvuru" else (1_300_000 if yol == "/profil" else 80_000))
        if f is None:
            return self._html(413, "Çok büyük", self._cerceve(pages.phead("Hata", "İstek çok büyük.")))
        if not self._csrf_ok(f):
            return self._html(400, "Geçersiz istek", self._cerceve(pages.phead("Hata", "Geçersiz istek.", "Sayfayı yenileyip tekrar deneyin.")))
        if hesap.post(self, yol, f):
            return
        if yol == "/kayit":
            return self._kayit(f)
        if yol == "/giris":
            return self._giris(f)
        if yol == "/cikis":
            ck = SimpleCookie(self.headers.get("Cookie", ""))
            if "ms" in ck:
                yurut("DELETE FROM oturumlar WHERE ozet=?", ozet(ck["ms"].value))
            return self._yonlendir("/giris?m=cikis", [self._cerez("ms", "", 0)])
        if not self.kullanici:
            return self._yonlendir("/giris")
        if api.web_post(self, yol, f) or sosyal.post(self, yol, f):
            return
        if yol == "/basvuru":
            if self.kullanici["rol"] == "yonetici":
                return self._gerekli_degil_yonetici()
            return self._basvuru(f)
        if yol == "/hesap-sil":
            return self._hesap_sil(f)
        if yol == "/gorsel-sil":
            return self._gorsel_sil(f)
        if yol == "/yonetim/karar":
            return self._karar(f) if self.kullanici["rol"] == "yonetici" else self._gerekli(True)
        self._statik("/__yok__.html")

    def _kayit(self, f):
        if hiz_asildi(("kayit", self._ip()), 5, 3600):
            return self._kayit_formu("Çok fazla deneme. Daha sonra tekrar deneyin.", f)
        ad, eposta_adresi, p1, p2 = f.get("ad", "").strip(), f.get("eposta", "").strip().lower(), f.get("parola", ""), f.get("parola2", "")
        hata = ("Adınız 2-60 karakter olmalı." if not 2 <= len(ad) <= 60 else
                "Geçerli bir e-posta yazın." if not EPOSTA.match(eposta_adresi) or len(eposta_adresi) > 120 else
                "Parola en az 10 karakter olmalı." if len(p1) < 10 or len(p1) > 200 else
                "Parolalar aynı değil." if p1 != p2 else
                "Aydınlatma metnini kabul etmelisiniz." if f.get("kabul") != "1" else "")
        if not hata and tek("SELECT 1 FROM kullanicilar WHERE eposta=?", eposta_adresi):
            hata = "Bu e-posta ile zaten bir hesap var. Giriş yapmayı deneyin."
        if hata:
            return self._kayit_formu(hata, f)
        kid = yurut("INSERT INTO kullanicilar(eposta,ad,parola,olusturma) VALUES(?,?,?,?)", eposta_adresi, ad, parola_ozet(p1), int(time.time())).lastrowid
        if eposta.hazir():
            hesap.dogrulama_gonder(tek("SELECT * FROM kullanicilar WHERE id=?", kid))
        self._yonlendir("/panel?m=kayit", [self._cerez("ms", oturum_ac(kid), SURE_OTURUM)])

    def _giris(self, f):
        eposta = f.get("eposta", "").strip().lower()
        if hiz_asildi(("giris-ip", self._ip()), 15, 600) or hiz_asildi(("giris-ep", eposta), 6, 600):
            return self._giris_formu({}, "Çok fazla deneme. On dakika sonra tekrar deneyin.", eposta)
        k = tek("SELECT * FROM kullanicilar WHERE eposta=?", eposta)
        # kullanıcı yoksa da aynı maliyetli hesaplama yapılır (zamanlama farkı sızdırmasın)
        dogru = parola_dogru(f.get("parola", ""), k["parola"] if k else parola_ozet("yok", b"0" * 16))
        if not k or not dogru:
            return self._giris_formu({}, "E-posta ya da parola hatalı.", eposta)
        self._yonlendir("/yonetim?m=giris" if k["rol"] == "yonetici" else "/panel?m=giris", [self._cerez("ms", oturum_ac(k["id"]), SURE_OTURUM)])

    def _basvuru(self, f):
        k = self.kullanici
        mevcut = tek("SELECT * FROM basvurular WHERE kullanici_id=?", k["id"])
        if not hesap.dogrulanmis(k):
            return self._panel({}, "Önce e-posta adresinizi doğrulayın (yukarıdaki bağlantıyı kullanın).", f)
        if mevcut and mevcut["durum"] == "askida":
            return self._panel({}, "Başvurunuz askıda; değişiklik yapılamaz.", None)
        duzenleme = bool(mevcut and mevcut["durum"] == "onaylandi")  # yayındaki profil: değişiklik onaya düşer, sayfa onaya kadar değişmez
        d, hata = basvuru_dogrula(f, k["eposta"])
        form = dict(f, id=mevcut["id"]) if mevcut else f
        if hata:
            return self._panel({}, hata, form)
        # görselleri kaydetmeden önce hepsini doğrula (yarım kayıt olmasın)
        yeni = []
        var = tek("SELECT COUNT(*) n FROM gorseller WHERE basvuru_id=?", mevcut["id"])["n"] if mevcut else 0
        dosyalar = [veri for ad, veri in self.dosyalar if ad == "gorsel"]
        if var + len(dosyalar) > MAKS_GORSEL_SAYISI:
            return self._panel({}, f"En çok {MAKS_GORSEL_SAYISI} görsel yüklenebilir (şu an {var} var).", form)
        for n, veri in enumerate(dosyalar, 1):
            if len(veri) > MAKS_GORSEL:
                return self._panel({}, f"{n}. görsel 2 MB'tan büyük.", form)
            try:
                yeni.append(gorsel.temizle(veri))
            except gorsel.GorselHatasi as ex:
                return self._panel({}, f"{n}. görsel: {ex}", form)
        simdi = int(time.time())
        if duzenleme:
            yurut("UPDATE basvurular SET taslak=?, guncelleme=? WHERE id=?", json.dumps(d, ensure_ascii=False), simdi, mevcut["id"])
            for tur, temiz, w, h in yeni:
                yurut("INSERT INTO gorseller(basvuru_id,tur,veri,genislik,yukseklik,olusturma,onayli) VALUES(?,?,?,?,?,?,0)", mevcut["id"], tur, temiz, w, h, simdi)
            return self._yonlendir("/panel?m=duzenleme")
        if mevcut:
            yurut("UPDATE basvurular SET ad=?,kisa=?,ayrinti=?,baglanti=?,adres=?,iletisim=?,hf=?,durum='beklemede',guncelleme=? WHERE id=?",
                  d["ad"], d["kisa"], d["ayrinti"], d["baglanti"], d["adres"], d["iletisim"], d["hf"], simdi, mevcut["id"])
            bid = mevcut["id"]
        else:
            bid = yurut("INSERT INTO basvurular(kullanici_id,slug,ad,kisa,ayrinti,baglanti,adres,iletisim,hf,olusturma,guncelleme) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                        k["id"], slug_uret(d["ad"]), d["ad"], d["kisa"], d["ayrinti"], d["baglanti"], d["adres"], d["iletisim"], d["hf"], simdi, simdi).lastrowid
        for tur, temiz, w, h in yeni:
            yurut("INSERT INTO gorseller(basvuru_id,tur,veri,genislik,yukseklik,olusturma) VALUES(?,?,?,?,?,?)", bid, tur, temiz, w, h, simdi)
        yeni_b = tek("SELECT * FROM basvurular WHERE id=?", bid)
        eposta.gonder(k["eposta"], *eposta.basvuru_alindi(k["ad"], yeni_b["ad"]))
        hesap.basvuru_yoneticiye(yeni_b, k["ad"])
        self._yonlendir("/panel?m=basvuru")

    def _gorsel_sil(self, f):
        k = self.kullanici
        r = tek("SELECT g.id, b.durum FROM gorseller g JOIN basvurular b ON b.id=g.basvuru_id WHERE g.id=? AND b.kullanici_id=?", f.get("id", ""), k["id"]) if f.get("id", "").isdigit() else None
        if r:
            yurut("DELETE FROM gorseller WHERE id=?", r["id"])
        self._yonlendir("/panel")

    def _hesap_sil(self, f):
        k = self.kullanici
        if hiz_asildi(("sil", k["id"]), 5, 600) or not parola_dogru(f.get("parola", ""), k["parola"]):
            return self._panel({"s": ["hesap"]}, "Parola hatalı; hesap silinmedi.")
        if k["rol"] == "yonetici" and tek("SELECT COUNT(*) n FROM kullanicilar WHERE rol='yonetici'")["n"] <= 1:
            return self._panel({"s": ["hesap"]}, "Son yönetici hesabı silinemez.")
        yurut("DELETE FROM kullanicilar WHERE id=?", k["id"])
        self._yonlendir("/giris?m=silindi", [self._cerez("ms", "", 0)])

    def _karar(self, f):
        karar = f.get("karar", "")
        if karar not in list(DURUMLAR) + ["duzenleme-onayla", "duzenleme-reddet"] or not f.get("id", "").isdigit():
            return self._html(400, "Geçersiz", self._cerceve(pages.phead("Hata", "Geçersiz karar.")))
        kimlik, simdi, nota = int(f["id"]), int(time.time()), f.get("not", "").strip()[:500]
        r = tek("SELECT * FROM basvurular WHERE id=?", kimlik)
        if not r:
            return self._html(404, "Bulunamadı", self._cerceve(pages.phead("Bulunamadı", "Böyle bir başvuru yok.")))
        if karar == "duzenleme-onayla":
            if r["taslak"]:
                t = json.loads(r["taslak"])
                yurut("UPDATE basvurular SET ad=?,kisa=?,ayrinti=?,baglanti=?,adres=?,iletisim=?,hf=?,taslak='',yonetici_notu=?,karar_tarihi=?,guncelleme=? WHERE id=?",
                      t["ad"], t["kisa"], t["ayrinti"], t["baglanti"], t["adres"], t["iletisim"], t["hf"], nota, simdi, simdi, kimlik)
            yurut("UPDATE gorseller SET onayli=1 WHERE basvuru_id=?", kimlik)
        elif karar == "duzenleme-reddet":
            yurut("UPDATE basvurular SET taslak='', yonetici_notu=?, guncelleme=? WHERE id=?", nota, simdi, kimlik)
            yurut("DELETE FROM gorseller WHERE basvuru_id=? AND onayli=0", kimlik)
        else:
            yurut("UPDATE basvurular SET durum=?, yonetici_notu=?, karar_tarihi=?, guncelleme=? WHERE id=?", karar, nota, simdi, simdi, kimlik)
            if karar == "onaylandi":  # ilk onay: başvuruyla gelen tüm görseller yayına girer; varsa bekleyen düzenleme de uygulanır
                if r["taslak"]:
                    t = json.loads(r["taslak"])
                    yurut("UPDATE basvurular SET ad=?,kisa=?,ayrinti=?,baglanti=?,adres=?,iletisim=?,hf=?,taslak='' WHERE id=?",
                          t["ad"], t["kisa"], t["ayrinti"], t["baglanti"], t["adres"], t["iletisim"], t["hf"], kimlik)
                yurut("UPDATE gorseller SET onayli=1 WHERE basvuru_id=?", kimlik)
        if karar != "beklemede":
            hesap.basvuru_karar_bildir(tek("SELECT * FROM basvurular WHERE id=?", kimlik), karar, nota)
        self._yonlendir("/yonetim?m=karar")


# ---------------------------------------------------------------- çalıştırma
def sunucu_kur(db_yolu, adres="127.0.0.1", port=8780, guvenli=False, vekil=False):
    BAGLAM["db"] = db_ac(db_yolu)
    BAGLAM["guvenli"] = guvenli
    BAGLAM["vekil"] = vekil
    return ThreadingHTTPServer((adres, port), H)


def yonetici_olustur(eposta, ad, parola):
    eposta = eposta.strip().lower()
    if not EPOSTA.match(eposta) or len(parola) < 10:
        raise ValueError("geçerli e-posta ve en az 10 karakterli parola gerekli")
    if tek("SELECT 1 FROM kullanicilar WHERE eposta=?", eposta):
        yurut("UPDATE kullanicilar SET rol='yonetici', parola=?, eposta_dogrulandi=1 WHERE eposta=?", parola_ozet(parola), eposta)
    else:
        yurut("INSERT INTO kullanicilar(eposta,ad,parola,rol,olusturma,eposta_dogrulandi) VALUES(?,?,?,?,?,1)", eposta, ad, parola_ozet(parola), "yonetici", int(time.time()))


hesap.baglan(sys.modules[__name__])
api.baglan(sys.modules[__name__])
sosyal.baglan(sys.modules[__name__])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("komut", choices=["calistir", "admin-olustur", "liste", "eposta-test"])
    ap.add_argument("--db", default=os.path.join(KOK, "veri", "portal.db"))
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8780)
    ap.add_argument("--guvenli", action="store_true", help="çerezlere Secure ekle (TLS arkasında çalışırken)")
    ap.add_argument("--vekil", action="store_true", help="yerel ters vekil arkasında: X-Forwarded-For'u istemci IP'si say")
    ap.add_argument("--eposta")
    ap.add_argument("--to", help="eposta-test: deneme iletisinin gideceği adres")
    ap.add_argument("--ad", default="Yönetici")
    a = ap.parse_args()
    if a.komut != "eposta-test":  # SMTP denemesi veritabanına dokunmaz
        BAGLAM["db"] = db_ac(a.db)
    if a.komut == "admin-olustur":
        import getpass
        if not a.eposta:
            sys.exit("--eposta gerekli")
        p1 = getpass.getpass("Parola (en az 10 karakter): ")
        if p1 != getpass.getpass("Parola (tekrar): "):
            sys.exit("Parolalar aynı değil")
        yonetici_olustur(a.eposta, a.ad, p1)
        print("Yönetici hazır:", a.eposta)
    elif a.komut == "eposta-test":
        if not a.to or not eposta.ADRES.match(a.to):
            sys.exit("--to <geçerli adres> gerekli")
        if not eposta.hazir():
            sys.exit("SMTP yapılandırılmamış: MODELEN_SMTP_HOST / _USER / _PASS (bkz. portal/PORTAL.md)")
        try:
            eposta.simdi_gonder(a.to, "Modelen: SMTP testi", "Bu bir deneme iletisidir. Bunu alıyorsanız Modelen portalının e-posta ayarı çalışıyor.")
        except Exception as ex:
            sys.exit(f"Gönderilemedi: {type(ex).__name__}: {ex}")
        print(f"Gönderildi: {a.to} (gönderen: {eposta.AYAR['gonderen']}, sunucu: {eposta.AYAR['host']}:{eposta.AYAR['port']} {eposta.AYAR['mod']})")
    elif a.komut == "liste":
        for r in sorgu("SELECT b.id,b.ad,b.durum,b.iletisim,b.adres,k.eposta FROM basvurular b JOIN kullanicilar k ON k.id=b.kullanici_id ORDER BY b.id"):
            print(f"#{r['id']} {r['ad']} [{r['durum']}] iletişim={r['iletisim']} hesap={r['eposta']} adres={r['adres'] or '-'}")
    else:
        s = sunucu_kur(a.db, a.host, a.port, a.guvenli, a.vekil)
        print(f"Modelen portalı: http://{a.host}:{a.port}  (db: {a.db})")
        try:
            s.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
