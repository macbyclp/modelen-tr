# -*- coding: utf-8 -*-
"""Tek dosyalık logo seçim tablosunu (secim-tablosu.html) üretir."""
import glob
import html
import os
import re

from collect import slug
from konseptler import A, B, C, D, E, KONSEPT

KOK = os.path.dirname(os.path.abspath(__file__))
KATEGORILER = [A, B, C, D, E]
KAT_ID = {A: "kultur", B: "dil", C: "topluluk", D: "yz", E: "doga"}


def ic(svg):
    return re.sub(r"^<svg[^>]*>|</svg>\s*$", "", svg.strip(), flags=re.S)


def yukle():
    d = {}
    for yol in glob.glob(os.path.join(KOK, "svg", "*.svg")):
        i = int(os.path.basename(yol)[:3])
        d[i] = open(yol, encoding="utf-8").read()
    return d


def u(i, boy, ek=""):
    return f'<svg class="m {ek}" width="{boy}" height="{boy}" viewBox="0 0 128 128" aria-hidden="true"><use href="#L{i:03d}"/></svg>'


def kart(i, kat, ad, anlam, var):
    no = f"{i:03d}"
    if not var:
        govde = '<div class="tile big none">çizim yok</div>'
    else:
        govde = f"""<div class="tile big dark">{u(i, 112)}</div>
<div class="sizes">
<div class="t dark">{u(i, 48)}</div><div class="t dark">{u(i, 24)}</div><div class="t dark">{u(i, 16)}</div>
<div class="t light">{u(i, 48)}</div><div class="t light">{u(i, 24)}</div>
<div class="lock dark">{u(i, 26)}<span>modelen</span></div>
<div class="lock light">{u(i, 26)}<span>modelen</span></div>
</div>"""
    return f"""<article class="card" id="l{no}" data-id="{i}" data-ad="{html.escape(ad)}" data-q="{html.escape((ad + ' ' + anlam + ' ' + kat).lower())}">
<button class="star" aria-pressed="false" title="Seç / bırak" aria-label="{no} {html.escape(ad)} seç"><span aria-hidden="true">☆</span></button>
{govde}
<h3><span class="no">{no}</span> {html.escape(ad)}</h3>
<p>{html.escape(anlam)}</p>
</article>"""


def main():
    svgler = yukle()
    semboller = "".join(
        f'<symbol id="L{i:03d}" viewBox="0 0 128 128">{ic(s)}</symbol>' for i, s in sorted(svgler.items()))
    bolumler = ""
    nav = ""
    for kat in KATEGORILER:
        kartlar = "".join(
            kart(i, k, ad, an, i in svgler) for i, (k, ad, an, ip) in enumerate(KONSEPT, start=1) if k == kat)
        n = sum(1 for k, *_ in KONSEPT if k == kat)
        bolumler += f'<section class="grp" id="{KAT_ID[kat]}"><h2>{html.escape(kat)} <small>{n}</small></h2><div class="grid">{kartlar}</div></section>'
        nav += f'<a href="#{KAT_ID[kat]}">{html.escape(kat)}</a>'
    sayfa = f"""<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Modelen · Logo seçim tablosu</title><meta name="color-scheme" content="dark light">
<style>
:root{{--bg:#101013;--bg2:#1a1a1e;--line:#27272b;--text:#fafaf4;--muted:#9a9aa6;--red:#ff4640;--red2:#e30a17;--mono:ui-monospace,"SF Mono","Cascadia Mono",Consolas,monospace}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}}
header{{position:sticky;top:0;z-index:5;background:#000;border-bottom:1px solid var(--line)}}
.bar{{max-width:1500px;margin:0 auto;padding:10px 16px;display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center}}
h1{{font-size:1.05rem;margin:0;font-weight:600;letter-spacing:-.01em}}h1 small{{color:var(--muted);font-weight:400}}
nav{{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:13px}}nav a{{color:var(--muted);text-decoration:none}}nav a:hover{{color:var(--text)}}
input[type=search]{{margin-left:auto;background:var(--bg2);border:1px solid var(--line);color:var(--text);padding:7px 10px;border-radius:6px;min-width:200px;font:inherit}}
main{{max-width:1500px;margin:0 auto;padding:18px 16px 120px}}
.intro{{color:var(--muted);max-width:90ch;margin:6px 0 22px}}
.grp h2{{font-size:1.25rem;font-weight:500;margin:34px 0 14px;letter-spacing:-.01em}}.grp h2 small{{color:var(--muted);font:12px var(--mono);margin-left:8px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:14px}}
.card{{position:relative;background:var(--bg2);border:1px solid var(--line);padding:12px;display:flex;flex-direction:column;gap:8px}}
.card.on{{border-color:var(--red);box-shadow:0 0 0 1px var(--red) inset}}.card.hide{{display:none}}
.star{{position:absolute;top:8px;right:8px;z-index:2;width:34px;height:34px;border-radius:6px;border:1px solid var(--line);background:rgba(16,16,19,.85);color:var(--muted);font-size:18px;cursor:pointer}}
.star[aria-pressed=true]{{background:var(--red2);border-color:var(--red2);color:#fff}}.star:hover{{border-color:var(--muted)}}
.tile{{display:flex;align-items:center;justify-content:center}}.tile.big{{height:150px}}.tile.none{{color:var(--muted);font:12px var(--mono);border:1px dashed var(--line)}}
.dark{{background:#0b0b0d}}.light{{background:#fafaf4;color:#101013}}
.sizes{{display:flex;flex-wrap:wrap;gap:6px;align-items:center}}.t{{display:flex;align-items:center;justify-content:center;padding:6px;min-width:34px}}
.lock{{display:flex;align-items:center;gap:6px;padding:6px 10px;font-weight:600;letter-spacing:-.02em;font-size:15px}}
.m{{display:block}}h3{{margin:2px 0 0;font-size:15px;font-weight:600;padding-right:36px}}.no{{font:12px var(--mono);color:var(--red);margin-right:6px}}
.card p{{margin:0;color:var(--muted);font-size:13px}}
footer{{position:fixed;left:0;right:0;bottom:0;background:#000;border-top:1px solid var(--line);z-index:6}}
.sel{{max-width:1500px;margin:0 auto;padding:10px 16px;display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;font-size:14px}}
.sel b{{color:var(--red)}}#liste{{font:13px var(--mono);color:var(--muted);flex:1;min-width:200px;overflow-wrap:anywhere}}
button.b{{background:#f1f1f3;color:#1a1a1e;border:0;border-radius:6px;padding:8px 14px;font:600 14px inherit;cursor:pointer}}button.b.g{{background:rgba(249,249,251,.08);color:var(--text)}}
:focus-visible{{outline:2px solid var(--red);outline-offset:2px}}
@media (prefers-color-scheme:light){{:root{{--bg:#f6f3ea;--bg2:#fff;--line:#dcd7c9;--text:#151512;--muted:#5f5b50}}header,footer{{background:#fff}}.star{{background:rgba(255,255,255,.9)}}}}
</style></head><body>
<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false">{semboller}</svg>
<header><div class="bar"><h1>Modelen · Logo seçim tablosu <small>{len(svgler)} / 100 çizim</small></h1><nav>{nav}</nav>
<input type="search" id="q" placeholder="Ara: ad ya da anlam" aria-label="Ara"></div></header>
<main><p class="intro">Her kart bir kavramı çizer: sol üstte numara ve ad, altında ne anlattığı. Üç koyu ve iki açık küçük kutu, 16 ile 48 piksel arasında okunurluğu gösterir; en alttaki sıra "modelen" yazısıyla yan yana durur. Beğendiklerinizi yıldızlayın; alttaki çubuk seçimi numaralarıyla listeler ve kopyalar. Seçim bu tarayıcıda saklanır. Çizimler yapay zekâyla üretilmiş taslaklardır; nihai logo için bir tasarımcıyla inceleme ve marka araştırması gerekir.</p>
{bolumler}</main>
<footer><div class="sel"><span>Seçilen: <b id="say">0</b></span><span id="liste">henüz seçim yok</span>
<button class="b" id="kopya">Kopyala</button><button class="b g" id="temiz">Temizle</button></div></footer>
<script>
(function(){{
var KEY='modelen-logo-secim',sel={{}};
try{{sel=JSON.parse(localStorage.getItem(KEY)||'{{}}')}}catch(e){{sel={{}}}}
var cards=[].slice.call(document.querySelectorAll('.card'));
function kaydet(){{try{{localStorage.setItem(KEY,JSON.stringify(sel))}}catch(e){{}}}}
function ciz(){{
  var ids=Object.keys(sel).map(Number).sort(function(a,b){{return a-b}});
  cards.forEach(function(c){{var on=!!sel[c.dataset.id];c.classList.toggle('on',on);c.querySelector('.star').setAttribute('aria-pressed',on);c.querySelector('.star span').textContent=on?'★':'☆'}});
  document.getElementById('say').textContent=ids.length;
  document.getElementById('liste').textContent=ids.length?ids.map(function(i){{return '#'+('00'+i).slice(-3)+' '+sel[i]}}).join(' · '):'henüz seçim yok';
}}
cards.forEach(function(c){{c.querySelector('.star').addEventListener('click',function(){{var i=c.dataset.id;if(sel[i])delete sel[i];else sel[i]=c.dataset.ad;kaydet();ciz()}})}});
document.getElementById('temiz').addEventListener('click',function(){{sel={{}};kaydet();ciz()}});
document.getElementById('kopya').addEventListener('click',function(){{
  var m=document.getElementById('liste').textContent,t='Seçtiğim logolar: '+m;
  if(navigator.clipboard&&navigator.clipboard.writeText){{navigator.clipboard.writeText(t).catch(function(){{window.prompt('Kopyalayın:',t)}})}}else{{window.prompt('Kopyalayın:',t)}}
}});
document.getElementById('q').addEventListener('input',function(e){{var q=e.target.value.trim().toLowerCase();cards.forEach(function(c){{c.classList.toggle('hide',q&&c.dataset.q.indexOf(q)<0)}})}});
ciz();
}})();
</script></body></html>
"""
    with open(os.path.join(KOK, "secim-tablosu.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(sayfa)
    print(f"secim-tablosu.html yazıldı: {len(svgler)} çizim, {len(sayfa) // 1024} KB")


if __name__ == "__main__":
    main()
