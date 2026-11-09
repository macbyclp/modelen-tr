"""Modelen Portal API v1 için küçük Python istemcisi (yalnızca standart kütüphane).

  export MODELEN_API_ANAHTARI=mdl_...            # panel > API anahtarları
  python modelen_api.py ben
  python modelen_api.py koordinator
  python modelen_api.py nabiz --durum calisiyor --tur 3 --toplam-tur 10 --aktif-isci 4
  python modelen_api.py nabiz-dongusu --koordinator https://koordinator.ornek.org --aralik 300
  python modelen_api.py adres-dogrula

Kütüphane olarak: `from modelen_api import ModelenApi; ModelenApi("mdl_...").nabiz("calisiyor", tur=3)`
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

TABAN = "https://modelen.tr/api/v1"


class ApiHatasi(Exception):
    def __init__(self, kod_http, kod, mesaj):
        super().__init__(f"{kod_http} {kod}: {mesaj}")
        self.kod_http, self.kod, self.mesaj = kod_http, kod, mesaj


class ModelenApi:
    def __init__(self, anahtar="", taban=TABAN, zaman=20):
        self.anahtar, self.taban, self.zaman = anahtar, taban.rstrip("/"), zaman

    def _istek(self, yontem, yol, govde=None):
        veri = json.dumps(govde).encode() if govde is not None else None
        r = urllib.request.Request(self.taban + yol, data=veri, method=yontem, headers={"Content-Type": "application/json", "User-Agent": "modelen-api-python/1"})
        if self.anahtar:
            r.add_header("Authorization", f"Bearer {self.anahtar}")
        try:
            with urllib.request.urlopen(r, timeout=self.zaman) as y:
                ham = y.read().decode("utf-8")
                return json.loads(ham) if ham else None
        except urllib.error.HTTPError as e:
            try:
                j = json.loads(e.read().decode("utf-8"))
            except ValueError:
                j = {}
            raise ApiHatasi(e.code, j.get("kod", "http"), j.get("hata", e.reason)) from None

    # --- herkese açık
    def saglik(self):
        return self._istek("GET", "/saglik")

    def koordinatorler(self):
        return self._istek("GET", "/koordinatorler")["koordinatorler"]

    # --- anahtarlı
    def ben(self):
        return self._istek("GET", "/ben")

    def koordinator(self):
        return self._istek("GET", "/koordinator")

    def basvur(self, **alanlar):
        return self._istek("POST", "/koordinator", alanlar)

    def guncelle(self, **alanlar):
        return self._istek("PATCH", "/koordinator", alanlar)

    def nabiz(self, durum="calisiyor", **ek):
        return self._istek("POST", "/koordinator/nabiz", {"durum": durum, **ek})

    def adres_dogrulama_baslat(self):
        return self._istek("POST", "/koordinator/adres-dogrula")

    def adres_dogrulama_kontrol(self):
        return self._istek("POST", "/koordinator/adres-dogrula/kontrol")


def koordinator_durumu(url, zaman=10, anahtar=""):
    """Referans koordinatörün /durum çıktısından nabız alanlarını türetir.
    Koordinatör anahtar istiyorsa (X-Anahtar) `anahtar` ya da MODELEN_ANAHTAR ortam değişkeni kullanılır; anahtar yoksa/reddedilirse
    anahtarsız açılan /bilgi'ye (tur, toplam_tur) düşülür; koordinatör ayakta olduğu sürece "durdu" bildirilmez."""
    anahtar = anahtar or os.environ.get("MODELEN_ANAHTAR", "")
    taban = url.rstrip("/")
    try:
        r = urllib.request.Request(taban + "/durum", headers={"X-Anahtar": anahtar} if anahtar else {})
        with urllib.request.urlopen(r, timeout=zaman) as y:
            d = json.loads(y.read().decode("utf-8"))
        return {"tur": d["tur"], "toplam_tur": d["toplam_tur"], "aktif_isci": len(d.get("isciler", {}))}
    except urllib.error.HTTPError as e:
        if e.code not in (401, 403):
            raise
    with urllib.request.urlopen(taban + "/bilgi", timeout=zaman) as y:
        d = json.loads(y.read().decode("utf-8"))
    return {"tur": d["tur"], "toplam_tur": d["toplam_tur"]}


def nabiz_dongusu(api, koordinator_url, aralik=300, once=False):
    """Koordinatörünüzü yoklayıp portala nabız gönderir. Ulaşılamazsa `durdu` bildirir."""
    while True:
        try:
            api.nabiz("calisiyor", protokol="1", **koordinator_durumu(koordinator_url))
            print("nabız gönderildi", flush=True)
        except (urllib.error.URLError, OSError, ValueError):
            try:
                api.nabiz("durdu", protokol="1", mesaj="koordinatöre ulaşılamıyor")
            except ApiHatasi:
                pass
            print("koordinatöre ulaşılamadı", flush=True)
        except ApiHatasi as ex:
            print("API hatası:", ex, file=sys.stderr, flush=True)
        if once:
            return
        time.sleep(aralik)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("komut", choices=["ben", "koordinator", "nabiz", "nabiz-dongusu", "adres-dogrula", "adres-kontrol", "liste"])
    ap.add_argument("--taban", default=os.environ.get("MODELEN_API_TABANI", TABAN))
    ap.add_argument("--durum", default="calisiyor")
    ap.add_argument("--tur", type=int)
    ap.add_argument("--toplam-tur", type=int)
    ap.add_argument("--aktif-isci", type=int)
    ap.add_argument("--koordinator", help="nabiz-dongusu: koordinatör adresi")
    ap.add_argument("--aralik", type=int, default=300)
    a = ap.parse_args(argv)
    api = ModelenApi(os.environ.get("MODELEN_API_ANAHTARI", ""), a.taban)
    try:
        if a.komut == "ben":
            r = api.ben()
        elif a.komut == "koordinator":
            r = api.koordinator()
        elif a.komut == "liste":
            r = api.koordinatorler()
        elif a.komut == "adres-dogrula":
            r = api.adres_dogrulama_baslat()
        elif a.komut == "adres-kontrol":
            r = api.adres_dogrulama_kontrol()
        elif a.komut == "nabiz":
            ek = {k: v for k, v in (("tur", a.tur), ("toplam_tur", a.toplam_tur), ("aktif_isci", a.aktif_isci)) if v is not None}
            r = api.nabiz(a.durum, protokol="1", **ek)
        else:
            if not a.koordinator:
                sys.exit("--koordinator gerekli")
            return nabiz_dongusu(api, a.koordinator, a.aralik) or 0
        print(json.dumps(r, ensure_ascii=False, indent=2))
    except ApiHatasi as ex:
        sys.exit(str(ex))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
