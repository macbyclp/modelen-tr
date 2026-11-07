# -*- coding: utf-8 -*-
"""F03 Halay Halkası'nın küçük boyut sürümü: 5 kollu halka + 5 fener. Geometri tek kaynaktan hem SVG hem PNG üretir.
Çıktılar: logo/fener/kucuk/ (kucuk-ikon.svg, kucuk-isaret.svg, kucuk-tek-renk.svg, kucuk-beyaz.svg, png/)"""
import math
import os

from PIL import Image, ImageDraw

KOK = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(KOK, "fener", "kucuk")
os.makedirs(os.path.join(OUT, "png"), exist_ok=True)

R1, R2, W, BG = "#ff4640", "#e30a17", "#fafaf4", "#101013"
CX, CY = 64.0, 69.0
R_ORTA, GENIS, BOSLUK = 22.0, 11.0, 7.0
R_FENER = 42.0
EKLEM = [-90 + 72 * k for k in range(5)]


def pol(r, a, c=None):
    cx, cy = c or (CX, CY)
    t = math.radians(a)
    return cx + r * math.cos(t), cy + r * math.sin(t)


def sektor(a0, a1, r0, r1, c=None, n=24):
    d1 = [pol(r1, a0 + (a1 - a0) * i / n, c) for i in range(n + 1)]
    d0 = [pol(r0, a1 - (a1 - a0) * i / n, c) for i in range(n + 1)]
    return d1 + d0


def sektor_yol(a0, a1, r0, r1, c=None):
    x0, y0 = pol(r1, a0, c); x1, y1 = pol(r1, a1, c); x2, y2 = pol(r0, a1, c); x3, y3 = pol(r0, a0, c)
    buyuk = 1 if (a1 - a0) % 360 > 180 else 0
    return (f"M{x0:.2f} {y0:.2f}A{r1} {r1} 0 {buyuk} 1 {x1:.2f} {y1:.2f}"
            f"L{x2:.2f} {y2:.2f}A{r0} {r0} 0 {buyuk} 0 {x3:.2f} {y3:.2f}Z")


def fener(fx, fy, renk_cerceve, cam, mono):
    """Kulplu, kapaklı, camlı, tabanlı sokak feneri (merkez fx,fy)."""
    l = []
    l.append(("sektor", (180, 360, 2.4, 5.0, (fx, fy - 11.5)), renk_cerceve))                 # kulp
    l.append(("poly", [(fx - 3, fy - 11), (fx + 3, fy - 11), (fx + 9, fy - 6), (fx - 9, fy - 6)], renk_cerceve))  # kapak
    if mono:
        for dx in (-6.8, 4.2):                                                                 # cam yerine iki çubuk
            l.append(("poly", [(fx + dx, fy - 6), (fx + dx + 2.6, fy - 6), (fx + dx + 3.4, fy + 6), (fx + dx + 0.8, fy + 6)], renk_cerceve))
    else:
        l.append(("poly", [(fx - 6.5, fy - 6), (fx + 6.5, fy - 6), (fx + 8, fy + 6), (fx - 8, fy + 6)], cam))  # cam
        l.append(("rect", (fx - 1, fy - 6, 2, 12), renk_cerceve))                              # orta çıta
    l.append(("rect", (fx - 9.5, fy + 6, 19, 3.5), renk_cerceve))                              # taban
    return l


def sekiller(mono=None, kontur=BG):
    """[(tür, veri, renk)]. mono verilirse tüm dolgular o renk (camlar boşluk, kollar boşluklu halka);
    aksi hâlde renkli: kollar birbirini 'yumruk' ile kavrar, yumruklar kontur renginde ince halka ile ayrılır."""
    liste = []
    r_in, r_out = R_ORTA - GENIS / 2, R_ORTA + GENIS / 2
    if mono:
        for k in range(5):
            a0, a1 = EKLEM[k] + BOSLUK / 2, EKLEM[k] + 72 - BOSLUK / 2
            liste.append(("sektor", (a0, a1, r_in, r_out), mono))
    else:
        for k in range(5):  # kollar eklem merkezlerinde tam birleşir
            liste.append(("sektor", (EKLEM[k], EKLEM[k] + 72, r_in, r_out), R1 if k % 2 == 0 else R2))
    for k, a in enumerate(EKLEM):
        ex, ey = pol(R_ORTA, a)
        fx, fy = pol(R_FENER, a)
        if not mono:
            onceki = R2 if (k - 1) % 2 == 0 else R1     # eklemde biten kolun rengi (k-1. kol)
            onceki = R1 if (k - 1) % 2 == 0 else R2
            liste.append(("disk", (ex, ey, 8.4 + 2.0), kontur))   # kontur halkası
            liste.append(("disk", (ex, ey, 8.4), onceki))         # yumruk (önceki kolun ucu)
        x0, y0 = pol(R_ORTA + 6.5, a); x1, y1 = pol(R_FENER - 8, a)
        liste.append(("sap", (x0, y0, x1, y1, 5.5), mono or R2))
        liste += fener(fx, fy, mono or R2, W, bool(mono))
    return liste


def svg_icerik(liste, kaydir=(0, 0), olcek=1.0):
    g = []
    for tur, v, renk in liste:
        if tur == "sektor":
            g.append(f'<path d="{sektor_yol(*v)}" fill="{renk}"/>')
        elif tur == "disk":
            g.append(f'<circle cx="{v[0]:.2f}" cy="{v[1]:.2f}" r="{v[2]}" fill="{renk}"/>')
        elif tur == "sap":
            x0, y0, x1, y1, w = v
            g.append(f'<line x1="{x0:.2f}" y1="{y0:.2f}" x2="{x1:.2f}" y2="{y1:.2f}" stroke="{renk}" stroke-width="{w}" stroke-linecap="butt"/>')
        elif tur == "poly":
            g.append('<polygon points="' + " ".join(f"{x:.2f},{y:.2f}" for x, y in v) + f'" fill="{renk}"/>')
        elif tur == "rect":
            x, y, w, h = v
            g.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w}" height="{h}" fill="{renk}"/>')
    govde = "".join(g)
    if olcek != 1.0 or kaydir != (0, 0):
        govde = f'<g transform="translate({kaydir[0]:.2f} {kaydir[1]:.2f}) scale({olcek})">{govde}</g>'
    return govde


def yaz_svg(ad, icerik, arka=None):
    bg = f'<rect width="128" height="128" rx="28" fill="{BG}"/>' if arka else ""
    s = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128">{bg}{icerik}</svg>\n'
    with open(os.path.join(OUT, ad), "w", encoding="utf-8", newline="\n") as f:
        f.write(s)


def png(liste, boyut, arka=True, olcek=1.0):
    S = 8
    N = 128 * S
    im = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if arka:
        d.rounded_rectangle((0, 0, N - 1, N - 1), radius=28 * S, fill=BG)

    def T(p):
        x, y = p
        return ((64 + (x - 64) * olcek) * S, (64 + (y - 64) * olcek) * S)

    for tur, v, renk in liste:
        if tur == "sektor":
            d.polygon([T(p) for p in sektor(*v)], fill=renk)
        elif tur == "disk":
            x, y, r = v
            (x0, y0), (x1, y1) = T((x - r, y - r)), T((x + r, y + r))
            d.ellipse((x0, y0, x1, y1), fill=renk)
        elif tur == "sap":
            x0, y0, x1, y1, w = v
            dx, dy = x1 - x0, y1 - y0
            L = math.hypot(dx, dy); nx, ny = -dy / L * w / 2, dx / L * w / 2
            d.polygon([T((x0 + nx, y0 + ny)), T((x1 + nx, y1 + ny)), T((x1 - nx, y1 - ny)), T((x0 - nx, y0 - ny))], fill=renk)
        elif tur == "poly":
            d.polygon([T(p) for p in v], fill=renk)
        elif tur == "rect":
            x, y, w, h = v
            d.polygon([T((x, y)), T((x + w, y)), T((x + w, y + h)), T((x, y + h))], fill=renk)
    return im.resize((boyut, boyut), Image.LANCZOS)


def main():
    renkli = sekiller()
    yaz_svg("kucuk-isaret.svg", svg_icerik(renkli))
    yaz_svg("kucuk-ikon.svg", svg_icerik(renkli, kaydir=(6.4, 6.4), olcek=0.9), arka=True)
    yaz_svg("kucuk-tek-renk.svg", svg_icerik(sekiller(mono=R2)))
    yaz_svg("kucuk-beyaz.svg", svg_icerik(sekiller(mono=W)))
    for b in (16, 32, 48, 64, 180, 192, 512):
        png(renkli, b, arka=True, olcek=0.9).save(os.path.join(OUT, "png", f"ikon-{b}.png"))
    png(renkli, 512, arka=False).save(os.path.join(OUT, "png", "isaret-512.png"))
    # kontrol montajı: aynı ikon 16/32/48/64 px, en yakın komşu ile 6 kat büyütülmüş + gerçek boyut
    montaj = Image.new("RGB", (900, 330), (40, 40, 44))
    x = 10
    for b in (16, 32, 48, 64):
        ic = png(renkli, b, arka=True, olcek=0.9).convert("RGB")
        montaj.paste(ic, (x, 10))
        montaj.paste(ic.resize((b * 4, b * 4), Image.NEAREST), (x, 80))
        x += b * 4 + 20
    montaj.save(os.path.join(KOK, "ham-img", "kucuk-montaj.png"))
    print("yazıldı:", sorted(os.listdir(OUT)))


if __name__ == "__main__":
    main()
