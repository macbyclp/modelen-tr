"""Uçtan uca deneme (yerel, yalıtılmış): portal + API + koordinatör + 2 gerçek işçi + uyum testi + nabız.

  py -3 istemci/uctan_uca.py [--tur 2] [--adim 5]

Geçici klasörde çalışır; canlı siteye/veritabanına dokunmaz. Eğitim için .venv gerekir (PyTorch).
Portal yalnızca https adresi kabul eder; yerel koordinatör adressiz başvurur. Adres doğrulama birim testlerinde sınanır.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "portal"))
sys.path.insert(0, os.path.join(KOK, "istemci", "ornekler"))
VENV = os.path.join(KOK, ".venv", "Scripts", "python.exe")
if not os.path.exists(VENV):
    VENV = os.path.join(KOK, ".venv", "bin", "python")

sonuclar = []


def kontrol(ad, tamam, ayrinti=""):
    sonuclar.append((ad, tamam))
    print(f"  {'tamam' if tamam else 'HATA ':5}  {ad}  {ayrinti}", flush=True)
    return tamam


def getir(url, zaman=20):
    with urllib.request.urlopen(url, timeout=zaman) as y:
        return json.loads(y.read().decode("utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tur", type=int, default=2)
    ap.add_argument("--adim", type=int, default=5)
    ap.add_argument("--port", type=int, default=8761)
    a = ap.parse_args()

    import portal
    import api
    from modelen_api import ModelenApi
    from test_portal import Oturum

    gecici = tempfile.mkdtemp(prefix="modelen-uu-")
    calisma = os.path.join(gecici, "calisma")
    os.makedirs(calisma)
    print(f"geçici klasör: {gecici}")

    # --- 1. portal + hesap + onaylı koordinatör
    print("[1] portal ve API")
    sunucu = portal.sunucu_kur(os.path.join(gecici, "portal.db"), "127.0.0.1", 0)
    pport = sunucu.server_address[1]
    threading.Thread(target=sunucu.serve_forever, daemon=True).start()
    taban = f"http://127.0.0.1:{pport}/api/v1"
    o = Oturum(pport)
    o.get("/kayit")
    o.post("/kayit", ad="Deneme Koordinatör", eposta="uu@ornek.org", parola="uzun-parola-123", parola2="uzun-parola-123", kabul="1")
    kid = portal.tek("SELECT id FROM kullanicilar WHERE eposta=?", "uu@ornek.org")["id"]
    _, anahtar = api.anahtar_olustur(kid, "uctan-uca")
    cli = ModelenApi(anahtar, taban)
    kontrol("API sağlık", cli.saglik().get("durum") == "tamam")
    kontrol("API anahtarıyla hesap", cli.ben().get("eposta") == "uu@ornek.org")
    k = cli.basvur(ad="Uçtan Uca Lab", kisa="Uçtan uca deneme koordinatörü (yerel)")
    kontrol("başvuru oluşturuldu (beklemede)", k.get("durum") == "beklemede", k.get("slug", ""))
    portal.yurut("UPDATE basvurular SET durum='onaylandi', karar_tarihi=? WHERE kullanici_id=?", int(time.time()), kid)
    kontrol("yönetici onayı sonrası dizinde", any(x["slug"] == k["slug"] for x in cli.koordinatorler()))

    # --- 2. başlangıç adaptörü + koordinatör
    print("[2] koordinatör")
    tur0 = os.path.join(calisma, "tur-0.safetensors")
    r = subprocess.run([VENV, os.path.join(KOK, "istemci", "baslat.py"), "--cikti", tur0], cwd=KOK, capture_output=True, text=True, encoding="utf-8", errors="replace")
    kontrol("başlangıç adaptörü üretildi", os.path.exists(tur0) and r.returncode == 0, f"{os.path.getsize(tur0) / 1e6:.1f} MB" if os.path.exists(tur0) else r.stderr[-200:])
    url = f"http://127.0.0.1:{a.port}"
    koord = subprocess.Popen([VENV, os.path.join(KOK, "istemci", "koordinator.py"), "--baslangic", tur0, "--tur", str(a.tur), "--en-az", "2",
                              "--ic-adim", str(a.adim), "--port", str(a.port), "--calisma", calisma], cwd=KOK,
                             stdout=open(os.path.join(gecici, "koordinator.log"), "w"), stderr=subprocess.STDOUT)
    islemler = [koord]
    try:
        for _ in range(60):
            try:
                getir(url + "/durum", 2)
                break
            except OSError:
                time.sleep(1)
        bilgi = getir(url + "/bilgi")
        kontrol("/bilgi protokol 1", bilgi.get("protokol") == "1")

        # --- 3. uyum testi
        print("[3] uyum testi")
        u = subprocess.run([sys.executable, os.path.join(KOK, "istemci", "uyum_testi.py"), "--url", url, "--json"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        kontrol("uyum testi geçti", u.returncode == 0, "")

        # --- 4. nabız (koordinatörün gerçek /durum'una göre)
        print("[4] nabız")
        from modelen_api import nabiz_dongusu
        nabiz_dongusu(cli, url, once=True)
        o4 = next((x for x in cli.koordinatorler() if x["slug"] == k["slug"]), {})
        kontrol("dizinde çevrimiçi", (o4.get("nabiz") or {}).get("durum") == "cevrimici", str(o4.get("nabiz")))

        # --- 5. iki gerçek işçi, tüm turlar
        print(f"[5] iki işçi, {a.tur} tur, tur başına {a.adim} adım (GPU'da birkaç dakika sürebilir)")
        for ad in ("gonullu-a", "gonullu-b"):
            islemler.append(subprocess.Popen([VENV, os.path.join(KOK, "istemci", "isci.py"), "--koordinator", url, "--isci", ad], cwd=KOK,
                                             stdout=open(os.path.join(gecici, f"{ad}.log"), "w"), stderr=subprocess.STDOUT))
        bitis = time.time() + 40 * 60
        son = -1
        while time.time() < bitis:
            d = getir(url + "/durum")
            if d["tur"] != son:
                son = d["tur"]
                print(f"    tur {d['tur']}/{d['toplam_tur']}  bekleyen {d['bekleyen_sonuc']}", flush=True)
            if d["tur"] >= d["toplam_tur"]:
                break
            if all(p.poll() is not None for p in islemler[1:]):
                break
            time.sleep(5)
        d = getir(url + "/durum")
        kontrol(f"{a.tur} tur tamamlandı", d["tur"] >= a.tur, f"tur {d['tur']}")
        son_dosya = os.path.join(calisma, f"tur-{a.tur}.safetensors")
        kontrol("son tur adaptörü diske yazıldı", os.path.exists(son_dosya))
        gunluk = os.path.join(calisma, "gunluk.json")
        if os.path.exists(gunluk):
            g = json.load(open(gunluk, encoding="utf-8"))
            turlar = g.get("gunluk", []) if isinstance(g, dict) else g
            kullanilan = [len(t.get("kullanilan", [])) for t in turlar] if isinstance(turlar, list) else []
            kontrol("her turda 2 işçi sonucu kullanıldı", bool(kullanilan) and all(n == 2 for n in kullanilan), str(kullanilan))

        # --- 6. bitiş sonrası nabız
        nabiz_dongusu(cli, url, once=True)
        cli.nabiz("bakimda", protokol="1", mesaj="deneme bitti")
        o6 = next((x for x in cli.koordinatorler() if x["slug"] == k["slug"]), {})
        kontrol("nabız 'bakımda' görünüyor", (o6.get("nabiz") or {}).get("durum") == "bakimda")

        # --- 7. değerlendirme
        if os.path.exists(son_dosya):
            print("[6] değerlendirme (bit/bayt, düşük iyidir)")
            dg = subprocess.run([VENV, os.path.join(KOK, "istemci", "degerlendir.py"), tur0, son_dosya], cwd=KOK, capture_output=True, text=True, encoding="utf-8", errors="replace")
            print("   ", (dg.stdout or dg.stderr).strip().replace("\n", "\n    ")[-600:])
    finally:
        for p in islemler:
            if p.poll() is None:
                p.terminate()
        sunucu.shutdown()

    gecen = sum(1 for _, t in sonuclar if t)
    print(f"\n{gecen}/{len(sonuclar)} madde geçti -> {'BAŞARILI' if gecen == len(sonuclar) else 'BAŞARISIZ'}")
    print(f"günlükler: {gecici}")
    return 0 if gecen == len(sonuclar) else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
