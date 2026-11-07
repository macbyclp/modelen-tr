# -*- coding: utf-8 -*-
"""Fener Zinciri varyantlarını toplar, SVG'leri doğrular ve fener-varyantlari.html üretir."""
import base64
import glob
import html
import io
import os
import re

from PIL import Image

from collect import dogrula

KOK = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(KOK, "fener")
BLOK = re.compile(r"<<<LOGO\s+(f\d+)>>>\s*(<svg\b.*?</svg>)\s*<<<END>>>", re.S)

TR = {
    "f01": ("Üç El Zinciri", "Üç fener, üstte birbirini kavrayan üç el: kesintisiz bir el zinciri."),
    "f02": ("Ortada Kenetlenen Eller", "Ortada kenetlenmiş iki el, iki yanda birer fener; ayna simetrisi."),
    "f03": ("Halay Halkası", "Beş el birbirini tutarak halka kurar, her biri dışa doğru bir fener taşır."),
    "f04": ("Fener Köprüsü", "Birbirini tutan ellerin kemeri bir köprü gibi; tutuşma yerlerinden fenerler sarkar."),
    "f05": ("Fenerler Ele Ele", "Yüzsüz üç fener, kısa kollarıyla birbirinin elini tutuyor."),
    "f06": ("Işığı Devretmek", "İki el tek bir feneri birlikte tutuyor: ışığın devri."),
    "f07": ("Yükselen Zincir", "Köşegende büyüyen üç fener, birbirini tutan eller: ilerleme."),
    "f08": ("Rozet", "Halka içinde üçgen düzende birbirini tutan üç el, her biri küçük bir fener taşıyor."),
}


def kucuk(yol):
    im = Image.open(yol).convert("RGB").resize((360, 360), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, "JPEG", quality=84, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode("ascii")


def ic(s):
    return re.sub(r"^<svg[^>]*>|</svg>\s*$", "", s.strip(), flags=re.S)


def use(k, n):
    return f'<svg width="{n}" height="{n}" viewBox="0 0 128 128" aria-hidden="true"><use href="#S{k}"/></svg>'


def main():
    # SVG'leri ayıkla
    svg_ham = os.path.join(D, "ham", "svg.out")
    metin = open(svg_ham, encoding="utf-8", errors="replace").read() if os.path.exists(svg_ham) else ""
    svgler, notlar = {}, []
    for k, s in BLOK.findall(metin):
        _, sorun = dogrula(s)
        if sorun:
            notlar.append((k, sorun))
        else:
            svgler[k] = s.strip()
            with open(os.path.join(D, "svg", f"{k}.svg"), "w", encoding="utf-8", newline="\n") as f:
                f.write(s.strip() + "\n")
    # mevcut #049 (referans)
    ref = {}
    r_svg = glob.glob(os.path.join(KOK, "svg", "049-*.svg"))
    if r_svg:
        ref["svg"] = open(r_svg[0], encoding="utf-8").read().strip()
    ref["img"] = os.path.join(KOK, "img", "049.png")
    kartlar, semboller = "", ""
    anahtarlar = ["r049"] + [f"f{i:02d}" for i in range(1, 9)]
    for k in anahtarlar:
        if k == "r049":
            ad, an = "Mevcut #049", "Seçtiğiniz ilk çizim: eller fener tutuyor ama birbirini tutmuyor (karşılaştırma için)."
            imgyol, svg = ref["img"], ref.get("svg")
        else:
            ad, an = TR[k]
            imgyol, svg = os.path.join(D, "img", f"{k}.png"), svgler.get(k)
        if svg:
            semboller += f'<symbol id="S{k}" viewBox="0 0 128 128">{ic(svg)}</symbol>'
        src = kucuk(imgyol) if os.path.exists(imgyol) else None
        gorsel = (f'<div class="pic"><img src="{src}" alt="{html.escape(ad)}"></div><div class="sm"><img src="{src}" width="64" height="64" alt=""><img src="{src}" width="32" height="32" alt=""><img src="{src}" width="20" height="20" alt=""></div>'
                  if src else '<div class="pic none">görsel yok</div>')
        if svg:
            vek = (f'<div class="two"><div class="v dk">{use(k, 140)}</div><div class="v lt">{use(k, 140)}</div></div>'
                   f'<div class="sm"><span class="dk">{use(k, 48)}</span><span class="dk">{use(k, 24)}</span><span class="dk">{use(k, 16)}</span><span class="lt">{use(k, 48)}</span><span class="lt">{use(k, 24)}</span></div>'
                   f'<div class="mock dk"><span class="lg">{use(k, 22)}<b>modelen</b></span><span class="lk">Nasıl çalışır</span><span class="bt">Gönüllü ol</span></div>')
        else:
            vek = '<div class="pic none">SVG yok</div>'
        kartlar += f"""<article class="fc" id="{k}"><header><h2><span class="no">{k.upper()}</span> {html.escape(ad)}</h2><button class="star" aria-pressed="false" data-k="{k}" data-ad="{html.escape(ad)}" aria-label="{html.escape(ad)} seç"><span aria-hidden="true">☆</span></button></header>
<p class="an">{html.escape(an)}</p><div class="row"><div class="blk"><div class="cap">gpt-image</div>{gorsel}</div><div class="blk"><div class="cap">SVG (vektör)</div>{vek}</div></div></article>"""
    sayfa = f"""<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Modelen · Fener Zinciri varyantları</title>
<style>
:root{{--bg:#101013;--bg2:#1a1a1e;--line:#27272b;--text:#fafaf4;--muted:#9a9aa6;--red:#ff4640;--mono:ui-monospace,"SF Mono",Consolas,monospace}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}}
main{{max-width:1300px;margin:0 auto;padding:26px 16px 110px}}h1{{font-size:1.6rem;margin:0 0 6px;font-weight:600;letter-spacing:-.02em}}.lead{{color:var(--muted);max-width:90ch;margin:0 0 22px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(520px,1fr));gap:16px}}
.fc{{background:var(--bg2);border:1px solid var(--line);padding:14px;position:relative}}.fc.on{{border-color:var(--red);box-shadow:0 0 0 1px var(--red) inset}}
.fc header{{display:flex;justify-content:space-between;align-items:center}}.fc h2{{margin:0;font-size:1.1rem;font-weight:600}}.no{{font:12px var(--mono);color:var(--red);margin-right:6px}}.an{{color:var(--muted);margin:2px 0 10px;font-size:14px}}
.row{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}.cap{{font:11px var(--mono);color:var(--muted);letter-spacing:.06em;margin-bottom:6px;text-transform:uppercase}}
.pic{{background:#101013;aspect-ratio:1;max-width:290px}}.pic img{{width:100%;height:100%;display:block}}.pic.none{{display:flex;align-items:center;justify-content:center;color:var(--muted);font:12px var(--mono);border:1px dashed var(--line)}}
.sm{{display:flex;gap:8px;align-items:center;margin-top:8px}}.sm img{{display:block;background:#101013}}.sm span{{display:flex;padding:5px}}
.dk{{background:#0b0b0d}}.lt{{background:#fafaf4}}.two{{display:flex;gap:6px}}.v{{display:flex;align-items:center;justify-content:center;width:140px;height:140px}}
.mock{{display:flex;align-items:center;gap:12px;padding:9px 10px;margin-top:8px;font-size:13px}}.mock .lg{{display:flex;align-items:center;gap:6px;font-weight:600}}.mock .lk{{opacity:.75}}.mock .bt{{margin-left:auto;background:#e30a17;color:#fff;padding:4px 9px;border-radius:5px;font-weight:600}}
.star{{width:34px;height:34px;border-radius:6px;border:1px solid var(--line);background:rgba(16,16,19,.85);color:var(--muted);font-size:18px;cursor:pointer}}.star[aria-pressed=true]{{background:#e30a17;border-color:#e30a17;color:#fff}}
footer{{position:fixed;left:0;right:0;bottom:0;background:#000;border-top:1px solid var(--line)}}.sel{{max-width:1300px;margin:0 auto;padding:10px 16px;display:flex;gap:12px;align-items:center;font-size:14px}}#liste{{font:13px var(--mono);color:var(--muted);flex:1}}
button.b{{background:#f1f1f3;color:#1a1a1e;border:0;border-radius:6px;padding:8px 14px;font:600 14px inherit;cursor:pointer}}
@media(max-width:700px){{.grid{{grid-template-columns:1fr}}.row{{grid-template-columns:1fr}}}}
</style></head><body><svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false">{semboller}</svg>
<main><h1>Fener Zinciri varyantları</h1><p class="lead">#049 Fener Zinciri için sekiz yeni kompozisyon: fenerleri tutan eller birbirini de tutuyor. Her biri hem gpt-image görseli hem SVG olarak çizildi; küçük boyutta (64/32/20 piksel) ve sitenin üst çubuğunda denendi. İlk kart sizin seçtiğiniz mevcut çizim (karşılaştırma için). Beğendiğinizi yıldızlayın.</p>
<div class="grid">{kartlar}</div></main>
<footer><div class="sel"><span>Seçilen: <b id="say" style="color:#ff4640">0</b></span><span id="liste">henüz seçim yok</span><button class="b" id="kopya">Kopyala</button></div></footer>
<script>(function(){{var sel={{}},K='modelen-fener-secim';try{{sel=JSON.parse(localStorage.getItem(K)||'{{}}')}}catch(e){{}}
var bt=[].slice.call(document.querySelectorAll('.star'));
function ciz(){{var ks=Object.keys(sel);bt.forEach(function(b){{var on=!!sel[b.dataset.k];b.setAttribute('aria-pressed',on);b.querySelector('span').textContent=on?'★':'☆';b.closest('.fc').classList.toggle('on',on)}});
document.getElementById('say').textContent=ks.length;document.getElementById('liste').textContent=ks.length?ks.map(function(k){{return k.toUpperCase()+' '+sel[k]}}).join(' · '):'henüz seçim yok'}}
bt.forEach(function(b){{b.addEventListener('click',function(){{var k=b.dataset.k;if(sel[k])delete sel[k];else sel[k]=b.dataset.ad;try{{localStorage.setItem(K,JSON.stringify(sel))}}catch(e){{}}ciz()}})}});
document.getElementById('kopya').addEventListener('click',function(){{var t='Seçtiğim fener varyantları: '+document.getElementById('liste').textContent;if(navigator.clipboard&&navigator.clipboard.writeText){{navigator.clipboard.writeText(t).catch(function(){{window.prompt('Kopyalayın:',t)}})}}else{{window.prompt('Kopyalayın:',t)}}}});ciz()}})();</script></body></html>"""
    with open(os.path.join(KOK, "fener-varyantlari.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(sayfa)
    print(f"fener-varyantlari.html: svg geçerli {len(svgler)}/8, sorunlu {notlar}, görsel {sum(os.path.exists(os.path.join(D,'img',f'f{i:02d}.png')) for i in range(1,9))}/8")


if __name__ == "__main__":
    main()
