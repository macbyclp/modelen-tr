"""English versions of the README images (cover, tour GIF, charts).

Run from the repo root: py -3 docs/gorsel_uret_en.py
Reuses the helpers of gorsel_uret.py. Charts are drawn from the real measurement files; no number is made up.
English site screenshots (docs/assets/en-site-*.png) were captured from https://modelen.tr/en/.
The desktop app and the portal have Turkish-only interfaces, so their screenshots stay Turkish (captioned as such).
"""
import json
import os
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from gorsel_uret import A, ACIK, BEYAZ, GRI, KIRMIZI, KOK, ZEMIN, font, logo


def cover():
    w, h = 1600, 640
    im = Image.new("RGB", (w, h), ZEMIN)
    isik = Image.new("RGB", (w, h), (0, 0, 0))
    ImageDraw.Draw(isik).ellipse((w * 0.05, h * -0.3, w * 0.75, h * 1.2), fill=(90, 8, 14))
    im = ImageChops.add(im, isik.filter(ImageFilter.GaussianBlur(160)))
    d = ImageDraw.Draw(im)
    r = random.Random(7)
    for _ in range(140):
        x, y, p = r.randrange(w), r.randrange(h), r.choice((60, 90, 120))
        d.ellipse((x, y, x + 2, y + 2), fill=(p, p, p + 10))
    lg = logo(430)
    im.paste(lg, (110, (h - 430) // 2), lg)
    d.text((600, 150), "modelen", font=font(150, True), fill=KIRMIZI)
    d.text((606, 330), "Open AI, trained together by the community.", font=font(40), fill=BEYAZ)
    d.text((606, 392), "Idle GPUs  ·  LoRA + DiLoCo  ·  Apache-2.0  ·  first language: Turkish", font=font(30), fill=GRI)
    d.rounded_rectangle((606, 470, 1262, 520), radius=10, outline=(70, 70, 78), width=2)
    d.text((628, 478), "Research stage  ·  no released model yet", font=font(27), fill=ACIK)
    im.save(os.path.join(A, "kapak-en.png"), optimize=True)
    im.resize((1280, 512), Image.LANCZOS).convert("RGB").save(os.path.join(A, "sosyal-onizleme-en.png"), optimize=True)


def tour():
    scenes = [("en-site-ana", "Website: modelen.tr"), ("uygulama-kolay", "Desktop app: Easy mode (Turkish UI)"),
              ("en-site-nasil", "How it works"), ("uygulama-gonullu", "App: coordinator picker (Turkish UI)"),
              ("en-site-olcumler", "Measurements: what we measured, what we could not"),
              ("site-koordinatorler", "Portal: Coordinators (Turkish UI)"), ("site-akis", "Portal: community feed (Turkish UI)"),
              ("uygulama-kod", "App: Ask the community (Turkish UI)")]
    W, H = 960, 600
    frames = []
    for ad, baslik in scenes:
        ss = Image.open(os.path.join(A, ad + ".png")).convert("RGB")
        oran = min((W - 40) / ss.width, (H - 90) / ss.height)
        ss = ss.resize((int(ss.width * oran), int(ss.height * oran)), Image.LANCZOS)
        tuval = Image.new("RGB", (W, H), ZEMIN)
        d = ImageDraw.Draw(tuval)
        d.text((24, 16), "modelen", font=font(26, True), fill=KIRMIZI)
        d.text((150, 21), baslik, font=font(21), fill=BEYAZ)
        x0, y0 = (W - ss.width) // 2, 70 + (H - 90 - ss.height) // 2
        tuval.paste(ss, (x0, y0))
        d.rounded_rectangle((x0 - 1, y0 - 1, x0 + ss.width, y0 + ss.height), radius=3, outline=(60, 60, 68))
        frames.append(tuval.convert("P", palette=Image.ADAPTIVE, colors=128, dither=Image.NONE))
    frames[0].save(os.path.join(A, "tur-en.gif"), save_all=True, append_images=frames[1:], duration=2400, loop=0, optimize=True)


def chart_diloco():
    d = json.load(open(os.path.join(KOK, "adaptor-diloco-h25.json"), encoding="utf-8"))
    base = [(x["tur"], x["bpb"]) for x in d["baseline"]]
    dil = [(x["tur"], x["bpb"]) for x in d["diloco"]]
    W, H, sol, alt, ust, sag = 900, 460, 90, 70, 70, 40
    im = Image.new("RGB", (W, H), ZEMIN)
    g = ImageDraw.Draw(im)
    y0, y1 = 1.210, 1.275
    X = lambda t: sol + (W - sol - sag) * t / max(x[0] for x in base)
    Y = lambda v: H - alt - (H - alt - ust) * (v - y0) / (y1 - y0)
    g.text((sol, 18), "Adapter-DiLoCo: the cost of sparse synchronisation", font=font(26, True), fill=BEYAZ)
    g.text((sol, 50), "Qwen3-0.6B-Base + LoRA, 4 virtual workers, Turkish Wikipedia (held-out 60k tokens)", font=font(16), fill=GRI)
    for v in (1.22, 1.23, 1.24, 1.25, 1.26, 1.27):
        g.line((sol, Y(v), W - sag, Y(v)), fill=(40, 40, 46))
        g.text((20, Y(v) - 9), f"{v:.2f}", font=font(15), fill=GRI)
    for t, _ in base:
        g.text((X(t) - 6, H - alt + 8), str(t), font=font(15), fill=GRI)
    g.text((W // 2 - 80, H - 30), "round (25 steps per round)", font=font(15), fill=GRI)
    g.text((10, ust - 28), "bits/byte", font=font(15), fill=GRI)
    for seri, renk, kal in ((base, GRI, 3), (dil, KIRMIZI, 4)):
        g.line([(X(t), Y(v)) for t, v in seri], fill=renk, width=kal)
        for t, v in seri:
            g.ellipse((X(t) - 5, Y(v) - 5, X(t) + 5, Y(v) + 5), fill=renk)
    g.text((W - 360, ust + 5), "● synchronised every step (reference)", font=font(16), fill=GRI)
    g.text((W - 360, ust + 28), "● DiLoCo, sync every 25 steps", font=font(16), fill=ACIK)
    g.text((sol + 20, H - alt - 44), f"Round 8: reference {base[-1][1]:.4f}  ·  DiLoCo {dil[-1][1]:.4f}  (gap {dil[-1][1] - base[-1][1]:+.4f} bits/byte)", font=font(17, True), fill=BEYAZ)
    im.save(os.path.join(A, "grafik-diloco-en.png"), optimize=True)


def chart_lora():
    veri = [("Turkish (Wikipedia)", 1.2969, 1.2406), ("English (WikiText-2)", 0.9468, 0.9597)]
    W, H = 900, 430
    im = Image.new("RGB", (W, H), ZEMIN)
    g = ImageDraw.Draw(im)
    g.text((60, 18), "20-minute LoRA: gain and forgetting", font=font(26, True), fill=BEYAZ)
    g.text((60, 52), "Bits per byte, lower is better. Single run, single seed.", font=font(16), fill=GRI)
    taban_y, tepe = H - 70, 110
    olcek = (taban_y - tepe) / 1.4
    for i, (ad, a, b) in enumerate(veri):
        x0 = 100 + i * 400
        for j, (deger, renk, etiket) in enumerate(((a, GRI, "base"), (b, KIRMIZI, "LoRA"))):
            x = x0 + j * 150
            y = taban_y - deger * olcek
            g.rectangle((x, y, x + 110, taban_y), fill=renk)
            g.text((x + 14, y - 28), f"{deger:.4f}", font=font(19, True), fill=BEYAZ)
            g.text((x + 28, taban_y + 8), etiket, font=font(16), fill=GRI)
        degisim = (b - a) / a * 100
        g.text((x0 + 10, taban_y + 34), f"{ad}  ({degisim:+.1f}%)", font=font(18), fill=ACIK if degisim < 0 else (255, 190, 120))
    im.save(os.path.join(A, "grafik-lora-en.png"), optimize=True)


if __name__ == "__main__":
    for f in (cover, tour, chart_diloco, chart_lora):
        f()
        print("generated:", f.__name__)
