# -*- coding: utf-8 -*-
"""Finalist karşılaştırma sayfası (finalistler.html): gpt-image görseli + SVG sürümü, açık/koyu zemin, küçük boyut,
site üst çubuğunda hâli ve kısa değerlendirme. Tek dosya (küçük resimler ve semboller gömülü)."""
import base64
import glob
import html
import io
import os
import re

from PIL import Image

from konseptler import KONSEPT

KOK = os.path.dirname(os.path.abspath(__file__))

# (id, etiket, görüş). Etiket: one / olur / ele. Görüşler benim değerlendirmemdir, hukuki görüş değildir.
FINAL = [
    (17, "one", "Ayırt edici ve anlamlı: taneler gönüllüler, tek kabuk ortak model. Küçük boyutta taneler kayboluyor; sadeleştirilmiş (az taneli) sürüm gerekir."),
    (5, "one", "Küçük boyutta en sağlam adaylardan; Anadolu geometrisi. Sekiz köşe sekiz düğüm gibi de okunur. Biraz genel; ayırt edici kılmak için düğüm/nokta eklenebilir."),
    (25, "one", "En güçlü hikâye: turnalar V düzeninde liderliği paylaşır, tıpkı dağıtık eğitim gibi. İnce kanatlar 32 pikselin altında okunmuyor; daha kalın ve az kuşlu bir sürüm gerekir."),
    (57, "olur", "Küçük boyutta çok net. Ama iç içe üç halka çok yaygın bir 'birlik/bağlantı' kalıbı; ayırt edicilik düşük."),
    (82, "olur", "Küçük boyutta çok sağlam ve 'her tur bir halka' anlamı güzel. Ancak kırmızı hedef tahtası gibi görünüyor; bilinen markalara benzeyebilir, benzerlik araştırması şart."),
    (45, "olur", "Sade ve soyut. 'İleri/gönder' oku ya da yükleniyor göstergesi gibi de okunabilir; anlam bağı zayıf."),
    (49, "ele", "Çok güzel bir illüstrasyon ama logo işareti için fazla ayrıntılı; küçük boyutta çöküyor. Kampanya görseli olarak saklanabilir."),
    (59, "ele", "Çatı = birlikte kurulan yuva, ama emlak/ev simgesi gibi okunuyor; yapay zekâyla bağı zayıf."),
    (61, "ele", "Yapay zekâ için çok yaygın bir görsel; ayrıntılı, küçük boyutta kayboluyor."),
    (62, "ele", "Düğüm ağı aşırı yaygın (blok zincir, kimya, ağ simgeleri); ayırt edici değil."),
    (77, "ele", "Soyut ve sade ama silueti belirsiz; tanınırlığı düşük."),
    (83, "ele", "Wi-Fi/sinyal simgesine benziyor."),
    (98, "ele", "Prizma ve ışık huzmesi bir ünlü albüm kapağını çağrıştırıyor; anlamla bağı da zayıf."),
]
ETIKET = {"one": ("Öne çıkan", "#ff4640"), "olur": ("Olabilir", "#e8b84a"), "ele": ("Eleyin", "#8a8a96")}


def kucuk(i):
    im = Image.open(os.path.join(KOK, "img", f"{i:03d}.png")).convert("RGB").resize((360, 360), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, "JPEG", quality=84, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode("ascii")


def svg_ic(i):
    yol = glob.glob(os.path.join(KOK, "svg", f"{i:03d}-*.svg"))[0]
    s = open(yol, encoding="utf-8").read().strip()
    return re.sub(r"^<svg[^>]*>|</svg>\s*$", "", s, flags=re.S)


def use(i, n):
    return f'<svg width="{n}" height="{n}" viewBox="0 0 128 128" aria-hidden="true"><use href="#L{i:03d}"/></svg>'


def main():
    semboller = "".join(f'<symbol id="L{i:03d}" viewBox="0 0 128 128">{svg_ic(i)}</symbol>' for i, _, _ in FINAL)
    ozet, kartlar = "", ""
    for i, et, gorus in FINAL:
        ad = KONSEPT[i - 1][1]
        anlam = KONSEPT[i - 1][2]
        e_ad, e_renk = ETIKET[et]
        src = kucuk(i)
        ozet += (f'<tr><td class="no">#{i:03d}</td><td><a href="#f{i:03d}">{html.escape(ad)}</a></td>'
                 f'<td><span class="tag" style="--c:{e_renk}">{e_ad}</span></td><td class="g">{html.escape(gorus)}</td></tr>')
        kartlar += f"""<article class="fc" id="f{i:03d}">
<header><h2><span class="no">#{i:03d}</span> {html.escape(ad)}</h2><span class="tag" style="--c:{e_renk}">{e_ad}</span></header>
<p class="an">{html.escape(anlam)}</p>
<div class="row">
 <div class="blk"><div class="cap">gpt-image sürümü</div><div class="pic"><img src="{src}" alt="{html.escape(ad)}"></div>
  <div class="sm"><img src="{src}" width="64" height="64" alt=""><img src="{src}" width="32" height="32" alt=""><img src="{src}" width="20" height="20" alt=""></div></div>
 <div class="blk"><div class="cap">SVG sürümü (vektör)</div>
  <div class="two"><div class="v dk">{use(i, 150)}</div><div class="v lt">{use(i, 150)}</div></div>
  <div class="sm"><span class="dk">{use(i, 48)}</span><span class="dk">{use(i, 24)}</span><span class="dk">{use(i, 16)}</span><span class="lt">{use(i, 48)}</span><span class="lt">{use(i, 24)}</span><span class="lt">{use(i, 16)}</span></div></div>
 <div class="blk"><div class="cap">Üst çubukta (SVG)</div>
  <div class="mock dk"><span class="lg">{use(i, 22)}<b>modelen</b></span><span class="lk">Nasıl çalışır</span><span class="lk">Yol haritası</span><span class="bt">Gönüllü ol</span></div>
  <div class="mock lt"><span class="lg">{use(i, 22)}<b>modelen</b></span><span class="lk">Nasıl çalışır</span><span class="lk">Yol haritası</span><span class="bt">Gönüllü ol</span></div></div>
</div>
<p class="gr"><b>Görüşüm:</b> {html.escape(gorus)}</p></article>"""
    sayfa = f"""<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Modelen · Logo finalistleri</title>
<style>
:root{{--bg:#101013;--bg2:#1a1a1e;--line:#27272b;--text:#fafaf4;--muted:#9a9aa6;--red:#ff4640;--mono:ui-monospace,"SF Mono","Cascadia Mono",Consolas,monospace}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}}
main{{max-width:1300px;margin:0 auto;padding:26px 16px 80px}}h1{{font-size:1.7rem;margin:0 0 6px;font-weight:600;letter-spacing:-.02em}}
.lead{{color:var(--muted);max-width:90ch;margin:0 0 20px}}
table{{border-collapse:collapse;width:100%;margin:0 0 30px;font-size:14px}}td{{border-top:1px solid var(--line);padding:10px 8px;vertical-align:top}}td.no{{font:13px var(--mono);color:var(--red);white-space:nowrap}}td.g{{color:var(--muted)}}td a{{color:var(--text)}}
.tag{{display:inline-block;font:11px var(--mono);letter-spacing:.06em;padding:2px 8px;border:1px solid var(--c);color:var(--c);white-space:nowrap}}
.fc{{background:var(--bg2);border:1px solid var(--line);padding:16px;margin:0 0 18px}}.fc header{{display:flex;justify-content:space-between;align-items:center;gap:10px}}
.fc h2{{margin:0;font-size:1.2rem;font-weight:600}}.no{{font:13px var(--mono);color:var(--red);margin-right:6px}}.an{{color:var(--muted);margin:4px 0 12px}}
.row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}}.cap{{font:11px var(--mono);color:var(--muted);letter-spacing:.06em;margin-bottom:6px;text-transform:uppercase}}
.pic{{background:#101013;aspect-ratio:1;max-width:300px}}.pic img{{width:100%;height:100%;display:block}}
.sm{{display:flex;gap:8px;align-items:center;margin-top:8px}}.sm img{{display:block;background:#101013}}.sm span{{display:flex;padding:5px}}
.dk{{background:#0b0b0d}}.lt{{background:#fafaf4}}.two{{display:flex;gap:8px}}.v{{display:flex;align-items:center;justify-content:center;width:150px;height:150px}}
.mock{{display:flex;align-items:center;gap:14px;padding:10px 12px;margin-bottom:8px;font-size:13px}}.mock.lt{{color:#101013}}.mock .lg{{display:flex;align-items:center;gap:6px;font-weight:600}}
.mock .lk{{opacity:.75}}.mock .bt{{margin-left:auto;background:#e30a17;color:#fff;padding:5px 10px;border-radius:5px;font-weight:600}}
.gr{{margin:12px 0 0;color:var(--muted);max-width:100ch}}.gr b{{color:var(--text)}}
</style></head><body>
<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false">{semboller}</svg>
<main><h1>Logo finalistleri <small style="color:var(--muted);font-weight:400">· 13 aday</small></h1>
<p class="lead">Seçtiğiniz 13 kavramı karşılaştırıyoruz. Her kartta gpt-image görseli ve SVG (vektör) çizimi var; SVG koyu ve açık zeminde, küçük boyutta ve sitenin üst çubuğunda denendi. Etiketler ve görüşler benim değerlendirmemdir: <b>Öne çıkan</b> = ayırt edicilik, anlam ve küçük boyut dengesi iyi; <b>Olabilir</b> = güçlü bir yanı var ama çekince taşıyor; <b>Eleyin</b> = logo işareti olarak zayıf (illüstrasyon olarak değerli olabilir). Bu bir marka ya da hukuk görüşü değildir: seçilen logo için benzerlik araştırması şarttır.</p>
<table><tbody>{ozet}</tbody></table>
{kartlar}</main></body></html>"""
    with open(os.path.join(KOK, "finalistler.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(sayfa)
    print(f"finalistler.html: {len(FINAL)} aday, {len(sayfa) // 1024} KB")


if __name__ == "__main__":
    main()
