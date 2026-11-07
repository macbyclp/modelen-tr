# -*- coding: utf-8 -*-
"""Hat çıktılarından SVG'leri ayıklar, doğrular, svg/NNN-slug.svg olarak yazar, rapor.json üretir."""
import glob
import json
import os
import re
import xml.etree.ElementTree as ET

from konseptler import KONSEPT

KOK = os.path.dirname(os.path.abspath(__file__))
IZINLI = {"svg", "g", "path", "circle", "ellipse", "rect", "polygon", "polyline", "line"}
PALET = {"#ff4640", "#e30a17", "#fafaf4", "#8a8a96", "#101013", "none"}
KIRMIZI = {"#ff4640", "#e30a17"}
YASAK_ATTR = {"style", "class", "href", "onload", "onclick", "filter", "mask", "clip-path"}
TR = str.maketrans("çğıöşüÇĞİÖŞÜâîû", "cgiosuCGIOSUaiu")
BLOK = re.compile(r"<<<LOGO\s+(\d{1,3})>>>\s*(<svg\b.*?</svg>)\s*<<<END>>>", re.S)


def slug(ad):
    s = ad.translate(TR).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def ns(tag):
    return tag.split("}")[-1]


def dogrula(svg):
    sorunlar = []
    if len(svg.encode("utf-8")) > 2400:
        sorunlar.append("çok büyük")
    try:
        kok = ET.fromstring(svg)
    except ET.ParseError as e:
        return None, [f"XML hatası: {e}"]
    if ns(kok.tag) != "svg":
        sorunlar.append("kök svg değil")
    if kok.attrib.get("viewBox", "").split() != ["0", "0", "128", "128"]:
        sorunlar.append("viewBox 0 0 128 128 değil")
    renkler = set()
    for el in kok.iter():
        if ns(el.tag) not in IZINLI:
            sorunlar.append(f"yasak etiket <{ns(el.tag)}>")
        for a, v in el.attrib.items():
            if a.split("}")[-1] in YASAK_ATTR:
                sorunlar.append(f"yasak öznitelik {a}")
            if a in ("fill", "stroke"):
                v = v.strip().lower()
                if v not in PALET:
                    sorunlar.append(f"paletdışı renk {v}")
                else:
                    renkler.add(v)
    renkler.discard("none")
    if len(renkler) > 3:
        sorunlar.append(f"{len(renkler)} renk")
    if not (renkler & KIRMIZI):
        sorunlar.append("kırmızı yok")
    return kok, sorunlar


def main():
    ham = {}
    for yol in sorted(glob.glob(os.path.join(KOK, "ham", "lane-*.out"))):
        t = open(yol, encoding="utf-8", errors="replace").read()
        if "<<<LOGO" not in t:  # son mesaj boşsa günlükten dene
            log = yol[:-4] + ".log"
            if os.path.exists(log):
                t = open(log, encoding="utf-8", errors="replace").read()
        bloklar = [(int(m.group(1)), m.group(2).strip()) for m in BLOK.finditer(t)]
        k = int(re.search(r"lane-(\d+)", os.path.basename(yol)).group(1))
        beklenen = [i for i in range(1, len(KONSEPT) + 1) if (i - 1) % 10 == k - 1]
        if len(bloklar) == len(beklenen):
            # Sıraya güven: hat kavramları verilen sırayla çizer; modeller bazen örnek numarayı (007) kopyalar.
            for (etiket, svg), gercek in zip(bloklar, beklenen):
                if etiket != gercek:
                    print(f"  not: hat {k:02d} etiket #{etiket:03d} -> konuma göre #{gercek:03d}")
                ham[gercek] = svg
        else:
            print(f"  uyarı: hat {k:02d} {len(bloklar)} blok verdi, {len(beklenen)} bekleniyordu; etikete göre alındı")
            for etiket, svg in bloklar:
                ham[etiket] = svg
    os.makedirs(os.path.join(KOK, "svg"), exist_ok=True)
    for eski in glob.glob(os.path.join(KOK, "svg", "*.svg")):
        os.remove(eski)
    rapor = {"gecerli": [], "sorunlu": {}, "eksik": []}
    for i, (kat, ad, anlam, ipucu) in enumerate(KONSEPT, start=1):
        svg = ham.get(i)
        if not svg:
            rapor["eksik"].append(i)
            continue
        _, sorunlar = dogrula(svg)
        if sorunlar:
            rapor["sorunlu"][i] = sorunlar
            continue
        with open(os.path.join(KOK, "svg", f"{i:03d}-{slug(ad)}.svg"), "w", encoding="utf-8", newline="\n") as f:
            f.write(svg + "\n")
        rapor["gecerli"].append(i)
    with open(os.path.join(KOK, "rapor.json"), "w", encoding="utf-8") as f:
        json.dump(rapor, f, ensure_ascii=False, indent=1)
    print(f"geçerli {len(rapor['gecerli'])} | sorunlu {len(rapor['sorunlu'])} | eksik {len(rapor['eksik'])}")
    for k, v in rapor["sorunlu"].items():
        print(f"  #{k:03d}:", "; ".join(sorted(set(v)))[:140])
    if rapor["eksik"]:
        print("  eksik:", rapor["eksik"])


if __name__ == "__main__":
    main()
