# -*- coding: utf-8 -*-
"""F03 (Halay Halkası) gpt-image görselini temiz bir SVG'ye izler.
1) Görseli 4 renkli palete oturtur (koyu zemin, derin kırmızı, parlak kırmızı, kırık beyaz).
2) vtracer ile 'cutout' modunda izler (koyu ayırıcılar gerçek boşluk olur).
3) Zemin/koyu yolları siler (şeffaf), renkleri paletle sabitler, viewBox'ı düzenler."""
import os
import re
import sys

import numpy as np
import vtracer
from PIL import Image, ImageFilter

KOK = os.path.dirname(os.path.abspath(__file__))
KAYNAK = sys.argv[1] if len(sys.argv) > 1 else os.path.join(KOK, "fener", "img", "f03.png")
AD = sys.argv[2] if len(sys.argv) > 2 else "f03"
CIKTI = os.path.join(KOK, "fener")
PAL = {"D": (13, 13, 17), "R2": (227, 10, 23), "R1": (255, 70, 64), "W": (250, 250, 244)}
HEX = {"R2": "#e30a17", "R1": "#ff4640", "W": "#fafaf4"}
anahtarlar = list(PAL)
renkler = np.array([PAL[k] for k in anahtarlar], dtype=np.int32)

im = Image.open(KAYNAK).convert("RGB")
a = np.asarray(im, dtype=np.int32)
d = ((a[:, :, None, :] - renkler[None, None, :, :]) ** 2).sum(-1)
idx = d.argmin(-1)
düz = renkler[idx].astype(np.uint8)
dz = Image.fromarray(düz, "RGB")
# 1 pikselik kenar kırıntılarını gider: 5x5 mod süzgeci
p = Image.fromarray(idx.astype(np.uint8), "L").filter(ImageFilter.ModeFilter(5))
idx2 = np.asarray(p, dtype=np.int32)
dz = Image.fromarray(renkler[idx2].astype(np.uint8), "RGB")
duz_yol = os.path.join(CIKTI, f"{AD}-duz.png")
dz.save(duz_yol)
ham = os.path.join(CIKTI, f"{AD}-ham.svg")
vtracer.convert_image_to_svg_py(
    duz_yol, ham, colormode="color", hierarchical="cutout", mode="spline",
    filter_speckle=10, color_precision=8, layer_difference=8, corner_threshold=55,
    length_threshold=5.0, max_iterations=12, splice_threshold=40, path_precision=1)
svg = open(ham, encoding="utf-8").read()
w, h = im.size
yollar = re.findall(r"<path\b[^>]*?/>", svg, flags=re.S)
cikan, sayac = [], {"D": 0, "R2": 0, "R1": 0, "W": 0}
for y in yollar:
    m = re.search(r'fill="(#[0-9a-fA-F]{6})"', y)
    if not m:
        continue
    r, g, b = (int(m.group(1)[i:i + 2], 16) for i in (1, 3, 5))
    en_yakin = min(anahtarlar, key=lambda k: (PAL[k][0] - r) ** 2 + (PAL[k][1] - g) ** 2 + (PAL[k][2] - b) ** 2)
    sayac[en_yakin] += 1
    if en_yakin == "D":
        continue  # zemin ve koyu ayırıcılar: şeffaf boşluk
    y = re.sub(r'fill="#[0-9a-fA-F]{6}"', f'fill="{HEX[en_yakin]}"', y)
    cikan.append(y)
govde = "\n".join(cikan)
svg_son = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="512" height="512">\n{govde}\n</svg>\n')
cikti_yol = os.path.join(CIKTI, f"{AD}-vektor.svg")
open(cikti_yol, "w", encoding="utf-8", newline="\n").write(svg_son)
print(f"yol sayıları (palete göre): {sayac}; yazılan yol: {len(cikan)}; SVG {len(svg_son) // 1024} KB -> {cikti_yol}")
