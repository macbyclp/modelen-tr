"""Sürüm varlıklarını üretir: dist/modelen-istemci.zip (+ dist/SHA256SUMS). kur.ps1 bu zip'i indirip açar.

  python tools/paketle.py [--exe uygulama/target/release/modelen.exe]

Zip içeriği (açılınca kurulum klasörüne): istemci/*.py, sunucu/*.py. Testler, çalışma klasörleri ve önbellekler dahil edilmez.
--exe verilirse modelen.exe de dist/ altına kopyalanır ve özet dosyasına eklenir.
"""
import argparse
import hashlib
import os
import shutil
import zipfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAHIL = ["istemci", "sunucu"]
ATLA_AD = ("test_", "__pycache__", "calisma")


def dosyalar():
    for d in DAHIL:
        for kok, altlar, fs in os.walk(os.path.join(KOK, d)):
            altlar[:] = [a for a in altlar if a not in ATLA_AD and not a.startswith(".")]
            for f in fs:
                if f.endswith((".py", ".md")) and not f.startswith(ATLA_AD):
                    yield os.path.join(kok, f)


def sha(yol):
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for blok in iter(lambda: f.read(1 << 20), b""):
            h.update(blok)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", default="")
    ap.add_argument("--kurulum", default="", help="Modelen-Kurulum.exe olarak dist/ altına kopyalanacak kurulum programı")
    ap.add_argument("--cikti", default=os.path.join(KOK, "dist"))
    a = ap.parse_args()
    os.makedirs(a.cikti, exist_ok=True)
    zip_yolu = os.path.join(a.cikti, "modelen-istemci.zip")
    with zipfile.ZipFile(zip_yolu, "w", zipfile.ZIP_DEFLATED) as z:
        n = 0
        for yol in sorted(dosyalar()):
            z.write(yol, os.path.relpath(yol, KOK).replace(os.sep, "/"))
            n += 1
    varliklar = [zip_yolu]
    if a.exe:
        hedef = os.path.join(a.cikti, "modelen.exe")
        shutil.copyfile(a.exe, hedef)
        varliklar.append(hedef)
    if a.kurulum:
        hedef = os.path.join(a.cikti, "Modelen-Kurulum.exe")
        shutil.copyfile(a.kurulum, hedef)
        varliklar.append(hedef)
    for betik in ("kur.sh", "koordinator-kur.sh"):  # Linux kurulum betikleri: indirilebilir sürüm varlıkları (LF satır sonlu kalmalı)
        kaynak = os.path.join(KOK, betik)
        if os.path.exists(kaynak):
            hedef = os.path.join(a.cikti, betik)
            veri = open(kaynak, "rb").read().replace(bytes([13, 10]), bytes([10]))
            open(hedef, "wb").write(veri)
            varliklar.append(hedef)
    with open(os.path.join(a.cikti, "SHA256SUMS"), "w", encoding="utf-8", newline="\n") as f:
        for v in varliklar:
            f.write(f"{sha(v)}  {os.path.basename(v)}\n")
    print(f"{n} dosya -> {zip_yolu}")
    print(open(os.path.join(a.cikti, "SHA256SUMS"), encoding="utf-8").read().strip())


if __name__ == "__main__":
    main()
