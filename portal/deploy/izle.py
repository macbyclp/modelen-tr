#!/usr/bin/env python3
"""VDS izleme (systemd zamanlayıcısı ile 5 dakikada bir). Standart kütüphane.

Denetler: portal sağlığı (yerel + Caddy üzerinden HTTPS), docs sitesi, TLS sertifika süresi, disk, bellek, son yedek yaşı.
Portal yanıt vermiyorsa en çok 10 dakikada bir yeniden başlatır. Sorunlar journal'a yazılır (`journalctl -t modelen-izle`).
Uyarı e-postası YALNIZCA /etc/modelen/portal.env içinde MODELEN_UYARI_EPOSTA tanımlıysa gönderilir (aynı sorun için 6 saatte bir).

  python3 izle.py            # denetle, gerekirse eylem yap
  python3 izle.py --dene     # yalnızca denetle ve sonucu yazdır (eylem yok, e-posta yok)
"""
import glob
import json
import os
import shutil
import ssl
import socket
import subprocess
import sys
import time
import urllib.request

DURUM = "/var/lib/modelen-izle.json"
PORTAL = "http://127.0.0.1:8780/api/v1/saglik"
YEDEK = "/opt/modelen/yedek"
ALAN_ADLARI = ["modelen.tr", "docs.modelen.tr"]
DENE = "--dene" in sys.argv


def log(m):
    print(m, flush=True)
    if not DENE:
        subprocess.run(["logger", "-t", "modelen-izle", m], check=False)


def http_ok(url, host=None, zaman=8):
    """host verilirse HTTPS isteği yerel Caddy'ye (127.0.0.1:443) o ad için yapılır."""
    try:
        if host:
            ctx = ssl.create_default_context()
            with socket.create_connection(("127.0.0.1", 443), timeout=zaman) as s, ctx.wrap_socket(s, server_hostname=host) as t:
                t.sendall(f"GET {url} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\nUser-Agent: modelen-izle\r\n\r\n".encode())
                ilk = t.recv(64).decode("latin-1")
                return " 200 " in ilk.split("\r\n")[0] or " 301 " in ilk.split("\r\n")[0]
        with urllib.request.urlopen(url, timeout=zaman) as y:
            return y.status == 200
    except Exception:
        return False


def sertifika_gun(host):
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection(("127.0.0.1", 443), timeout=8) as s, ctx.wrap_socket(s, server_hostname=host) as t:
            bitis = ssl.cert_time_to_seconds(t.getpeercert()["notAfter"])
        return int((bitis - time.time()) // 86400)
    except Exception:
        return None


def denetle():
    sorunlar = {}
    if not http_ok(PORTAL):
        sorunlar["portal"] = "portal yerelde yanıt vermiyor"
    if not http_ok("/api/v1/saglik", "modelen.tr"):
        sorunlar["https-modelen"] = "https://modelen.tr/api/v1/saglik yanıt vermiyor (Caddy ya da portal)"
    if not http_ok("/", "docs.modelen.tr"):
        sorunlar["https-docs"] = "https://docs.modelen.tr yanıt vermiyor"
    for ad in ALAN_ADLARI:
        g = sertifika_gun(ad)
        if g is not None and g < 10:
            sorunlar[f"sertifika-{ad}"] = f"{ad} sertifikasının bitmesine {g} gün kaldı"
    kul = shutil.disk_usage("/")
    if kul.used / kul.total > 0.85:
        sorunlar["disk"] = f"disk %{kul.used * 100 // kul.total} dolu"
    try:
        mem = {l.split(":")[0]: int(l.split()[1]) for l in open("/proc/meminfo")}
        if mem["MemAvailable"] < 300 * 1024:
            sorunlar["bellek"] = f"kullanılabilir bellek {mem['MemAvailable'] // 1024} MB"
    except OSError:
        pass
    yedekler = glob.glob(os.path.join(YEDEK, "portal-*.db"))
    if yedekler and time.time() - max(os.path.getmtime(f) for f in yedekler) > 36 * 3600:
        sorunlar["yedek"] = "son veritabanı yedeği 36 saatten eski"
    elif not yedekler:
        sorunlar["yedek"] = "hiç veritabanı yedeği yok"
    return sorunlar


def eposta_gonder(konu, metin):
    hedef = ""
    try:
        for satir in open("/etc/modelen/portal.env"):
            if satir.startswith("MODELEN_UYARI_EPOSTA="):
                hedef = satir.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        return
    if not hedef:
        return
    sys.path.insert(0, "/opt/modelen/portal")
    try:
        for satir in open("/etc/modelen/portal.env"):  # SMTP ayarları eposta modülü için ortamdan okunur
            if "=" in satir and not satir.startswith("#"):
                k, v = satir.strip().split("=", 1)
                os.environ.setdefault(k, v.strip('"').strip("'"))
        import eposta
        eposta.ayar_yukle()
        if eposta.hazir():
            eposta.gonder(hedef, konu, metin)
    except Exception as e:  # uyarı göndermek asla izleyiciyi düşürmesin
        log(f"uyarı e-postası gönderilemedi: {type(e).__name__}")


def main():
    sorunlar = denetle()
    if DENE:
        print(json.dumps(sorunlar, ensure_ascii=False, indent=2) if sorunlar else "tüm denetimler geçti")
        return 0 if not sorunlar else 1
    try:
        d = json.load(open(DURUM))
    except (OSError, ValueError):
        d = {}
    simdi = time.time()
    # portal yanıt vermiyorsa: en çok 10 dakikada bir yeniden başlat
    if "portal" in sorunlar and simdi - d.get("son_yeniden_baslatma", 0) > 600:
        log("portal yanıt vermiyor, yeniden başlatılıyor")
        subprocess.run(["systemctl", "restart", "modelen-portal"], check=False)
        d["son_yeniden_baslatma"] = simdi
        time.sleep(4)
        if http_ok(PORTAL):
            sorunlar.pop("portal", None)
            sorunlar.pop("https-modelen", None)
            log("portal yeniden başlatıldıktan sonra sağlıklı")
            eposta_gonder("Modelen portalı yeniden başlatıldı", "Portal yanıt vermediği için otomatik yeniden başlatıldı ve şimdi sağlıklı.")
    bildirilen = d.setdefault("bildirilen", {})
    yeni = []
    for k, m in sorunlar.items():
        log(f"SORUN {k}: {m}")
        if simdi - bildirilen.get(k, 0) > 6 * 3600:
            bildirilen[k] = simdi
            yeni.append(m)
    for k in [k for k in bildirilen if k not in sorunlar]:
        log(f"düzeldi: {k}")
        bildirilen.pop(k)
    if yeni:
        eposta_gonder("Modelen uyarısı", "Sunucu izleyicisi sorun buldu:\n\n- " + "\n- ".join(yeni))
    json.dump(d, open(DURUM, "w"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
