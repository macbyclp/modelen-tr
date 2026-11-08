"""README görsellerini üretir: kapak, logo animasyonu, tur GIF'i, deney grafikleri.

Girdiler: docs/assets/ içindeki ekran görüntüleri, uygulama/assets/logo-512.png, adaptor-diloco-h25.json.
Çalıştırma (depo kökünden): py -3 docs/gorsel_uret.py
Grafikler gerçek ölçüm dosyalarından çizilir; sayı uydurulmaz. Logo animasyonu yalnızca süslemedir.
"""
import json
import math
import os

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(KOK, "docs", "assets")
ZEMIN, KIRMIZI, ACIK, GRI, BEYAZ = (16, 16, 19), (227, 10, 23), (255, 120, 112), (150, 150, 160), (249, 249, 251)


def font(boyut, kalin=False):
    for ad in (("segoeuib.ttf" if kalin else "segoeui.ttf"), ("arialbd.ttf" if kalin else "arial.ttf")):
        try:
            return ImageFont.truetype(os.path.join("C:/Windows/Fonts", ad), boyut)
        except OSError:
            continue
    return ImageFont.load_default()


def logo(boyut):
    return Image.open(os.path.join(KOK, "uygulama", "assets", "logo-512.png")).convert("RGBA").resize((boyut, boyut), Image.LANCZOS)


def kapak():
    w, h = 1600, 640
    im = Image.new("RGB", (w, h), ZEMIN)
    # yumuşak kırmızı ışıma
    isik = Image.new("RGB", (w, h), (0, 0, 0))
    d = ImageDraw.Draw(isik)
    d.ellipse((w * 0.05, h * -0.3, w * 0.75, h * 1.2), fill=(90, 8, 14))
    isik = isik.filter(ImageFilter.GaussianBlur(160))
    im = ImageChops.add(im, isik)
    # yıldız tozu
    d = ImageDraw.Draw(im)
    import random
    r = random.Random(7)
    for _ in range(140):
        x, y, p = r.randrange(w), r.randrange(h), r.choice((60, 90, 120))
        d.ellipse((x, y, x + 2, y + 2), fill=(p, p, p + 10))
    lg = logo(430)
    im.paste(lg, (110, (h - 430) // 2), lg)
    d.text((600, 150), "modelen", font=font(150, True), fill=KIRMIZI)
    d.text((606, 330), "Topluluğun birlikte eğittiği açık yapay zekâ.", font=font(40), fill=BEYAZ)
    d.text((606, 392), "Boştaki ekran kartları  ·  LoRA + DiLoCo  ·  Apache-2.0  ·  ilk dil: Türkçe", font=font(30), fill=GRI)
    d.rounded_rectangle((606, 470, 1262, 520), radius=10, outline=(70, 70, 78), width=2)
    d.text((628, 478), "Araştırma aşaması  ·  henüz yayınlanmış model yok", font=font(27), fill=ACIK)
    im.save(os.path.join(A, "kapak.png"), optimize=True)
    # sosyal önizleme (1280x640)
    im.resize((1280, 512), Image.LANCZOS).convert("RGB").save(os.path.join(A, "sosyal-onizleme.png"), optimize=True)


def logo_nabiz():
    """Logonun etrafında yavaş atan kırmızı ışıma (süsleme)."""
    n, boyut = 24, 360
    kareler = []
    lg = logo(250)
    for i in range(n):
        t = i / n
        im = Image.new("RGB", (boyut, boyut), ZEMIN)
        parla = Image.new("L", (boyut, boyut), 0)
        yar = 120 + 26 * math.sin(2 * math.pi * t)
        ImageDraw.Draw(parla).ellipse((boyut / 2 - yar, boyut / 2 - yar, boyut / 2 + yar, boyut / 2 + yar), fill=int(110 + 50 * math.sin(2 * math.pi * t)))
        parla = parla.filter(ImageFilter.GaussianBlur(38))
        im.paste(Image.new("RGB", (boyut, boyut), (150, 12, 22)), (0, 0), parla)
        im.paste(lg, ((boyut - 250) // 2, (boyut - 250) // 2), lg)
        kareler.append(im.convert("P", palette=Image.ADAPTIVE, colors=64))
    kareler[0].save(os.path.join(A, "logo-nabiz.gif"), save_all=True, append_images=kareler[1:], duration=70, loop=0, optimize=True)


def tur_gif():
    """Gerçek ekran görüntülerinden gezinti: site, uygulama, portal."""
    sahneler = [("site-ana", "Site: modelen.tr"), ("uygulama-kolay", "Masaüstü uygulaması: Kolay mod"), ("site-nasil", "Nasıl çalışır?"),
                ("uygulama-gonullu", "Uygulama: koordinatör seçimi"), ("site-olcumler", "Ölçümler: ne ölçtük, ne ölçemedik"),
                ("site-koordinatorler", "Portal: Koordinatörler"), ("site-akis", "Portal: topluluk akışı"), ("uygulama-kod", "Uygulama: topluluğa sor")]
    W, H = 960, 600
    kareler = []
    for ad, baslik in sahneler:
        ss = Image.open(os.path.join(A, ad + ".png")).convert("RGB")
        oran = min((W - 40) / ss.width, (H - 90) / ss.height)
        ss = ss.resize((int(ss.width * oran), int(ss.height * oran)), Image.LANCZOS)
        tuval = Image.new("RGB", (W, H), ZEMIN)
        d = ImageDraw.Draw(tuval)
        d.text((24, 16), "modelen", font=font(26, True), fill=KIRMIZI)
        d.text((150, 21), baslik, font=font(21), fill=BEYAZ)
        tuval.paste(ss, ((W - ss.width) // 2, 70 + (H - 90 - ss.height) // 2))
        d.rounded_rectangle(((W - ss.width) // 2 - 1, 70 + (H - 90 - ss.height) // 2 - 1, (W + ss.width) // 2, 70 + (H - 90 - ss.height) // 2 + ss.height), radius=3, outline=(60, 60, 68))
        kareler.append(tuval.convert("P", palette=Image.ADAPTIVE, colors=128, dither=Image.NONE))
    kareler[0].save(os.path.join(A, "tur.gif"), save_all=True, append_images=kareler[1:], duration=2400, loop=0, optimize=True)


def grafik_curve():
    """Adaptör-DiLoCo ve her adımda senkron referansın bayt-başına-bit eğrisi (adaptor-diloco-h25.json)."""
    d = json.load(open(os.path.join(KOK, "adaptor-diloco-h25.json"), encoding="utf-8"))
    taban = [(x["tur"], x["bpb"]) for x in d["baseline"]]
    dil = [(x["tur"], x["bpb"]) for x in d["diloco"]]
    W, H, sol, alt, ust, sag = 900, 460, 90, 70, 70, 40
    im = Image.new("RGB", (W, H), ZEMIN)
    g = ImageDraw.Draw(im)
    y0, y1 = 1.210, 1.275
    X = lambda t: sol + (W - sol - sag) * t / max(x[0] for x in taban)
    Y = lambda v: H - alt - (H - alt - ust) * (v - y0) / (y1 - y0)
    g.text((sol, 18), "Adaptör-DiLoCo: seyrek senkronizasyonun bedeli", font=font(26, True), fill=BEYAZ)
    g.text((sol, 50), "Qwen3-0.6B-Base + LoRA, 4 sanal işçi, Türkçe Vikipedi (ayrılmış 60 bin token)", font=font(16), fill=GRI)
    for v in (1.22, 1.23, 1.24, 1.25, 1.26, 1.27):
        g.line((sol, Y(v), W - sag, Y(v)), fill=(40, 40, 46))
        g.text((20, Y(v) - 9), f"{v:.2f}", font=font(15), fill=GRI)
    for t, _ in taban:
        g.text((X(t) - 6, H - alt + 8), str(t), font=font(15), fill=GRI)
    g.text((W // 2 - 60, H - 30), "tur (her tur 25 adım)", font=font(15), fill=GRI)
    g.text((10, ust - 28), "bit/bayt", font=font(15), fill=GRI)
    for seri, renk, kal in ((taban, GRI, 3), (dil, KIRMIZI, 4)):
        g.line([(X(t), Y(v)) for t, v in seri], fill=renk, width=kal)
        for t, v in seri:
            g.ellipse((X(t) - 5, Y(v) - 5, X(t) + 5, Y(v) + 5), fill=renk)
    g.text((W - 330, ust + 5), "● her adımda senkron (referans)", font=font(16), fill=GRI)
    g.text((W - 330, ust + 28), "● DiLoCo, 25 adımda bir senkron", font=font(16), fill=ACIK)
    g.text((sol + 20, H - alt - 44), f"8. turda: referans {taban[-1][1]:.4f}  ·  DiLoCo {dil[-1][1]:.4f}  (fark {dil[-1][1] - taban[-1][1]:+.4f} bit/bayt)", font=font(17, True), fill=BEYAZ)
    im.save(os.path.join(A, "grafik-diloco.png"), optimize=True)


def grafik_lora():
    """Taban ve 20 dakikalık LoRA: Türkçe / İngilizce bayt başına bit (ADAPTASYON.md tablosundan)."""
    veri = [("Türkçe (Vikipedi)", 1.2969, 1.2406), ("İngilizce (WikiText-2)", 0.9468, 0.9597)]
    W, H = 900, 430
    im = Image.new("RGB", (W, H), ZEMIN)
    g = ImageDraw.Draw(im)
    g.text((60, 18), "20 dakikalık LoRA: kazanç ve unutma", font=font(26, True), fill=BEYAZ)
    g.text((60, 52), "Bayt başına bit, düşük iyi. Tek koşu, tek tohum.", font=font(16), fill=GRI)
    taban_y, tepe = H - 70, 110
    olcek = (taban_y - tepe) / 1.4
    for i, (ad, a, b) in enumerate(veri):
        x0 = 100 + i * 400
        for j, (deger, renk, etiket) in enumerate(((a, GRI, "taban"), (b, KIRMIZI, "LoRA"))):
            x = x0 + j * 150
            y = taban_y - deger * olcek
            g.rectangle((x, y, x + 110, taban_y), fill=renk)
            g.text((x + 14, y - 28), f"{deger:.4f}", font=font(19, True), fill=BEYAZ)
            g.text((x + 28, taban_y + 8), etiket, font=font(16), fill=GRI)
        degisim = (b - a) / a * 100
        g.text((x0 + 10, taban_y + 34), f"{ad}  ({degisim:+.1f}%)", font=font(18), fill=ACIK if degisim < 0 else (255, 190, 120))
    im.save(os.path.join(A, "grafik-lora.png"), optimize=True)


if __name__ == "__main__":
    for f in (kapak, logo_nabiz, tur_gif, grafik_curve, grafik_lora):
        f()
        print("üretildi:", f.__name__)
