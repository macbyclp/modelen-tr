# -*- coding: utf-8 -*-
"""Statik siteyi üretir: python build.py  (site/ klasöründe çalıştırılır, ağ ve GPU gerekmez).

Yer tutucuları aşağıdaki PLACEHOLDERS sözlüğünden doldurur. Topluluk bilgileri netleşince yalnızca
burayı güncelleyip yeniden derleyin. DRAFT = False yapınca yasal sayfalardaki
"taslak" uyarısı kalkar (avukat incelemesinden sonra).
"""
import html
import os
import re

import content_en
import content_tr
import home

import pages

content_tr.PAGES["index"] = home.TR
content_en.PAGES["index"] = home.EN
content_tr.PAGES.update(pages.TR)
content_en.PAGES.update(pages.EN)
content_en.FILES["olcumler"] = "measurements"
content_tr.NAV.insert(2, ("olcumler", "Ölçümler"))
content_en.NAV.insert(2, ("olcumler", "Measurements"))

DRAFT = True
BASE = "https://modelen.tr"
TARIH_TR = "7 Kasım 2026"
TARIH_EN = "7 November 2026"
PLACEHOLDERS = {
    "EPOSTA": "iletisim@modelen.tr",
    "UNVAN": "Modelen Alternatif Eğitim Topluluğu",
    "BARINDIRMA": "[BARINDIRMA SAĞLAYICISI — seçilince eklenecek]",
    "MAHKEME": "[YETKİLİ MAHKEME VE İCRA DAİRELERİ — merkez adresine göre]",
}

def _logo():
    """Halay Halkası işareti: assets/logo-isaret.svg dosyası satır içi gömülür (tek kaynak)."""
    yol = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo-isaret.svg")
    s = open(yol, encoding="utf-8").read().strip()
    return s.replace('width="128" height="128"', 'aria-hidden="true" focusable="false"')


LOGO = _logo()
CTA = {"tr": ("Gönüllü ol", "katil.html"), "en": ("Volunteer", "join.html")}
CONTACT = {"tr": "İletişim", "en": "Contact"}
# Giriş/kayıt bağlantıları (portal gerektirir). Giriş yapmış kullanıcıya portal bu bloğu Panel/Çıkış ile değiştirir.
AUTH = {"tr": ("Giriş yap", "Kayıt ol"), "en": ("Sign in", "Register")}


def auth_blok(lang, sinif):
    g, k = AUTH[lang]
    return (f'<!--AUTH--><span class="auth {sinif}"><a href="/giris">{g}</a><a href="/kayit">{k}</a></span><!--/AUTH-->')
MENU = {"tr": "Menü", "en": "Menu"}
ESC_JS = ("<script>document.addEventListener('keydown',function(e){if(e.key==='Escape'){var d=document."
          "querySelector('details.menu');if(d&&d.open){d.open=false;d.querySelector('summary').focus();}}});"
          "document.addEventListener('click',function(e){var d=document.querySelector('details.menu');"
          "if(d&&d.open&&e.target.closest&&e.target.closest('.sheet a')){d.open=false;}});</script>")
FOOT_COLS = {
    "tr": [("Katıl", ["katil", "koordinatorler", "akis", "koordinator-ol", "topluluk-kurallari", "gonullu-sartlari", "katki-sartlari"]),
           ("Öğren", ["nasil-calisir", "olcumler", "yol-haritasi", "sss", "lisans"]),
           ("Modelen", ["hakkinda", "iletisim", "gizlilik", "kvkk", "kullanim-sartlari", "cerez"])],
    "en": [("Join", ["katil", "koordinatorler", "akis", "koordinator-ol", "topluluk-kurallari", "gonullu-sartlari", "katki-sartlari"]),
           ("Learn", ["nasil-calisir", "olcumler", "yol-haritasi", "sss", "lisans"]),
           ("Modelen", ["hakkinda", "iletisim", "gizlilik", "kvkk", "kullanim-sartlari", "cerez"])],
}


def grid_html(cols=28, rows=7):
    """Gönüllü ağını temsil eden süs ızgarası (illüstrasyon; gerçek veri değil)."""
    s, hucre = 20261107, []
    for _ in range(cols * rows):
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        if (s >> 8) % 100 < 24:
            hucre.append(f'<i class="on d{1 + (s >> 4) % 4}"></i>')
        else:
            hucre.append("<i></i>")
    return '<div class="net" aria-hidden="true">' + "".join(hucre) + "</div>"


LEGAL_KEYS = {"gizlilik", "kvkk", "kullanim-sartlari", "cerez", "gonullu-sartlari", "katki-sartlari", "lisans"}


def legalize(body, key, lang):
    """Yasal sayfaların eski düz başlığını iç sayfalardaki başlık bloğuna (etiket + başlık + tarih) çevirir."""
    if key not in LEGAL_KEYS:
        return body, False
    m = re.match(r'\s*<div class="prose">\s*<h1>(.*?)</h1>(?:\s*<p><small>(.*?)</small></p>)?', body, re.S)
    if not m:
        return body, False
    if key == "lisans":
        etiket = "Lisans" if lang == "tr" else "Licence"
    else:
        etiket = "Yasal" if lang == "tr" else "Legal"
    meta = f'<p class="meta">{m.group(2)}</p>' if m.group(2) else ""
    bas = f'<div class="phead legal"><p class="label">{etiket}</p><h1>{m.group(1)}</h1>{meta}</div><div class="prose">'
    return bas + body[m.end():], True


def fill(text, lang):
    t = text.replace("%%GRID%%", grid_html())
    for k, v in PLACEHOLDERS.items():
        t = t.replace(f"%%{k}%%", v)
    return t.replace("%%TARIH%%", TARIH_TR).replace("%%TARIH_EN%%", TARIH_EN)


def fname(key, lang):
    return (content_tr_name(key) if lang == "tr" else content_en.FILES[key]) + ".html"


def content_tr_name(key):
    return key


def render(key, lang):
    c = content_tr if lang == "tr" else content_en
    ui = c.UI
    page = c.PAGES[key]
    other = content_en if lang == "tr" else content_tr
    path_here = ("" if lang == "tr" else "en/") + fname(key, lang)
    path_other = ("en/" if lang == "tr" else "") + fname(key, "en" if lang == "tr" else "tr")
    prefix = "" if lang == "tr" else "../"
    assets = f"{prefix}assets/"
    sw_href = ("en/" + fname(key, "en")) if lang == "tr" else ("../" + fname(key, "tr"))
    nav = "".join(
        f'<a href="{fname(k, lang)}"' + (' aria-current="page"' if k == key else "") + f">{html.escape(label)}</a>"
        for k, label in c.NAV)
    legal = "".join(f'<a href="{fname(k, lang)}">{html.escape(label)}</a>' for k, label in c.FOOT)
    etiket = dict(c.NAV + c.FOOT)
    fcols ="".join(
        f"<div><h3>{html.escape(baslik)}</h3><ul>" + "".join(
            f'<li><a href="{fname(k, lang)}">{html.escape(etiket[k])}</a></li>' for k in keys) + "</ul></div>"
        for baslik, keys in FOOT_COLS[lang])
    banner = f'<div class="draft" role="note">{ui["draft"]}</div>' if (DRAFT and page.get("legal")) else ""
    govde0, donustu = legalize(page["body"], key, lang)
    if donustu and banner:
        govde = govde0.replace('</div><div class="prose">', "</div>" + banner + '<div class="prose">', 1)
    else:
        govde = banner + govde0
    if not page.get("wide"):
        govde = f'<div class="frame"><div class="page">{govde}</div></div>'
    body = fill(govde, lang)
    cta_label, cta_href = CTA[lang]
    title = html.escape(fill(page["title"], lang))
    desc = html.escape(fill(page["desc"], lang), quote=True)
    alt_tr = f"{BASE}/{fname(key, 'tr')}"
    alt_en = f"{BASE}/en/{fname(key, 'en')}"
    canonical = alt_tr if lang == "tr" else alt_en
    home = "index.html"
    return f"""<!doctype html>
<html lang="{ui['lang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="tr" href="{alt_tr}">
<link rel="alternate" hreflang="en" href="{alt_en}">
<link rel="icon" href="{assets}favicon.svg" type="image/svg+xml">
<link rel="icon" href="{assets}icon-32.png" type="image/png" sizes="32x32">
<link rel="apple-touch-icon" href="{assets}apple-touch-icon.png">
<link rel="manifest" href="{prefix}manifest.webmanifest">
<meta name="theme-color" content="#101013"><meta name="color-scheme" content="dark">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{BASE}/assets/og.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{BASE}/assets/og.png">
<link rel="stylesheet" href="{assets}style.css">
</head>
<body>
<a class="skip" href="#icerik">{html.escape(ui['skip'])}</a>
<header class="site"><div class="bar">
<a class="brand" href="{home}">{LOGO}<span>{ui['sitename']}</span></a>
<div class="right">{auth_blok(lang, 'auth-top')}<a class="lang" href="{sw_href}" hreflang="{'en' if lang == 'tr' else 'tr'}" lang="{'en' if lang == 'tr' else 'tr'}">{ui['switch']}</a><a class="btn accent sm" href="{cta_href}">{cta_label}</a>
<details class="menu"><summary aria-label="{MENU[lang]}"><span class="burger" aria-hidden="true"><i></i><i></i><i></i></span></summary>
<div class="sheet">{auth_blok(lang, 'auth-sheet')}<nav aria-label="{ui['nav_label']}">{nav}</nav>
<div class="small">{legal}<a href="{sw_href}" hreflang="{'en' if lang == 'tr' else 'tr'}" lang="{'en' if lang == 'tr' else 'tr'}">{ui['switch']}</a><a href="mailto:{PLACEHOLDERS['EPOSTA']}">{PLACEHOLDERS['EPOSTA']}</a></div></div></details></div>
</div></header>
<main id="icerik">
{body}
</main>
<footer class="site"><div class="frame">
<div class="fcols">{fcols}</div>
<div class="fbase"><span>{ui['copyright']}</span><span><a href="mailto:{PLACEHOLDERS['EPOSTA']}">{PLACEHOLDERS['EPOSTA']}</a> · {ui['footer_tag']}</span></div>
</div></footer>
{ESC_JS}
</body>
</html>
"""


def main():
    kok = os.path.dirname(os.path.abspath(__file__))
    sayfalar = []
    for lang in ("tr", "en"):
        c = content_tr if lang == "tr" else content_en
        for key in c.PAGES:
            yol = os.path.join(kok, "" if lang == "tr" else "en", fname(key, lang))
            os.makedirs(os.path.dirname(yol), exist_ok=True)
            with open(yol, "w", encoding="utf-8", newline="\n") as f:
                f.write(render(key, lang))
            sayfalar.append(("" if lang == "tr" else "en/") + fname(key, lang))
    # 404
    # 404: sitenin kabuğunu (üst çubuk, menü, alt bilgi) kullanır; hangi yolda sunulursa sunulsun
    # çalışsın diye tüm iç bağlantılar köke göre (/...) yazılır.
    content_tr.PAGES["404"] = dict(
        title="Sayfa bulunamadı · Modelen", desc="Aradığınız sayfa bulunamadı.",
        body=pages.phead("404", "Sayfa bulunamadı.", "Aradığınız sayfa taşınmış ya da hiç var olmamış olabilir. "
                         "Page not found.")
        + '<div class="actions" style="justify-content:flex-start"><a class="btn accent" href="index.html">Ana sayfa</a>'
          '<a class="btn ghost" href="en/index.html">Home (English)</a></div>')
    content_en.FILES["404"] = "404"
    k404 = render("404", "tr")
    del content_tr.PAGES["404"], content_en.FILES["404"]
    k404 = re.sub(r'(href|src)="(?!https?:|mailto:|/|#)([^"]*)"', r'\1="/\2"', k404)
    k404 = k404.replace('<meta name="viewport"', '<meta name="robots" content="noindex"><meta name="viewport"', 1)
    with open(os.path.join(kok, "404.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(k404)
    with open(os.path.join(kok, "manifest.webmanifest"), "w", encoding="utf-8", newline="\n") as f:
        f.write('{"name":"Modelen","short_name":"Modelen","description":"Açık, topluluk sahipli yapay zekâ.",'
                '"start_url":"/","display":"standalone","background_color":"#101013","theme_color":"#101013","lang":"tr",'
                '"icons":[{"src":"assets/icon-192.png","sizes":"192x192","type":"image/png"},'
                '{"src":"assets/icon-512.png","sizes":"512x512","type":"image/png"}]}\n')
    # sitemap, robots, security.txt
    urls = "".join(f"  <url><loc>{BASE}/{s}</loc></url>\n" for s in sayfalar)
    with open(os.path.join(kok, "sitemap.xml"), "w", encoding="utf-8", newline="\n") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                + urls + "</urlset>\n")
    with open(os.path.join(kok, "robots.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
    os.makedirs(os.path.join(kok, ".well-known"), exist_ok=True)
    with open(os.path.join(kok, ".well-known", "security.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(f"Contact: mailto:{PLACEHOLDERS['EPOSTA']}\nExpires: 2027-11-07T00:00:00.000Z\n"
                f"Preferred-Languages: tr, en\nCanonical: {BASE}/.well-known/security.txt\n")
    print(f"{len(sayfalar)} sayfa üretildi")


if __name__ == "__main__":
    main()
