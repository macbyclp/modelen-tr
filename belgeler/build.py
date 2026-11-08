"""Modelen dokümantasyon sitesini (docs.modelen.tr) üretir: python belgeler/build.py  -> belgeler/cikti/

İçerik: belgeler/icerik/<dil>/*.md (ön bilgi: baslik, bolum, sira, ozet). Dil klasörleri: tr (kök), en (/en/).
API başvuru sayfası, portal/api_sema.py'deki OpenAPI şemasından üretilir; openapi.json da çıktıya kopyalanır.
Bağımlılık yok (yalnızca standart kütüphane)."""
import html
import json
import os
import re
import shutil
import sys

KOK = os.path.dirname(os.path.abspath(__file__))
DEPO = os.path.dirname(KOK)
sys.path.insert(0, KOK)
sys.path.insert(0, os.path.join(DEPO, "portal"))
import api_sema  # noqa: E402
import md  # noqa: E402

CIKTI = os.path.join(KOK, "cikti")
BASE = "https://docs.modelen.tr"
SITE = "https://modelen.tr"
GITHUB = "https://github.com/macbyclp/modelen-tr"
LOGO = open(os.path.join(DEPO, "site", "assets", "logo-isaret.svg"), encoding="utf-8").read().strip().replace('width="128" height="128"', 'aria-hidden="true" width="26" height="26"')
BOLUM_SIRASI = {"tr": ["Başlarken", "Koordinatör olmak", "Kendi sistemini bağlamak", "Portal API", "Güvenlik", "Kaynaklar"],
                "en": ["Getting started", "Becoming a coordinator", "Connecting your system", "Portal API", "Security", "Resources"]}
UI = {
    "tr": dict(lang="tr", ad="Dokümantasyon", ara="Ara…", ara_etiket="Dokümantasyonda ara", on="Önceki", son="Sonraki", bu_sayfada="Bu sayfada", site="modelen.tr", portal="Portal",
               anasayfa="Dokümantasyon", gecis="English", gecis_yol="/en/", menu="Menü", yok="Aradığınız sayfa bulunamadı.", sayfa_yok="Sonuç yok.",
               alt="Modelen Alternatif Eğitim Topluluğu · Apache-2.0 · Sorunlar ve katkı için GitHub'a bakın.", kopyala="Kopyala", kopyalandi="Kopyalandı",
               en_not="", sonraki_surum="API v1 · Protokol v1"),
    "en": dict(lang="en", ad="Documentation", ara="Search…", ara_etiket="Search the documentation", on="Previous", son="Next", bu_sayfa="On this page", bu_sayfada="On this page",
               site="modelen.tr", portal="Portal", anasayfa="Documentation", gecis="Türkçe", gecis_yol="/", menu="Menu", yok="The page you are looking for was not found.", sayfa_yok="No results.",
               alt="Modelen Alternatif Eğitim Topluluğu · Apache-2.0 · See GitHub for issues and contributions.", kopyala="Copy", kopyalandi="Copied",
               en_not="Some pages are available in Turkish only for now.", sonraki_surum="API v1 · Protocol v1"),
}


def on_bilgi(metin):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", metin.replace("\r\n", "\n"), re.S)
    if not m:
        return {}, metin
    d = {}
    for s in m.group(1).split("\n"):
        k, _, v = s.partition(":")
        if v:
            d[k.strip()] = v.strip()
    return d, m.group(2)


def sayfalari_oku(dil):
    klasor = os.path.join(KOK, "icerik", dil)
    sayfalar = []
    for ad in sorted(os.listdir(klasor)) if os.path.isdir(klasor) else []:
        if not ad.endswith(".md"):
            continue
        b, govde = on_bilgi(open(os.path.join(klasor, ad), encoding="utf-8").read())
        slug = ad[:-3]
        sayfalar.append(dict(slug=slug, baslik=b.get("baslik", slug), bolum=b.get("bolum", ""), sira=int(b.get("sira", "99")), ozet=b.get("ozet", ""), govde=govde, dil=dil))
    return sayfalar


# ------------------------------------------------------------------ API başvuru sayfası (şemadan)
def alan_tablosu(sema, bilesenler, ust=""):
    if "$ref" in sema:
        sema = bilesenler[sema["$ref"].split("/")[-1]]
    ozel = sema.get("properties", {})
    if not ozel:
        return ""
    gerekli = set(sema.get("required", []))
    satirlar = []
    for ad, a in ozel.items():
        tur = a.get("type", "nesne") if "$ref" not in a else a["$ref"].split("/")[-1]
        if a.get("enum"):
            tur += " (" + " \\| ".join(a["enum"]) + ")"
        kisit = []
        for k, e in (("minLength", "en az {} karakter"), ("maxLength", "en çok {} karakter"), ("minimum", "en az {}")):
            if k in a:
                kisit.append(e.format(a[k]))
        satirlar.append(f"| `{ad}` | {tur} | {'evet' if ad in gerekli else ''} | {a.get('description', '')} {', '.join(kisit)} |")
    return "| Alan | Tür | Zorunlu | Açıklama |\n|---|---|---|---|\n" + "\n".join(satirlar) + "\n"


def api_referans_md(dil):
    s = api_sema.sema(SITE)
    bil = s["components"]["schemas"]
    tr = dil == "tr"
    cikti = []
    cikti.append(("Tüm uç noktalar" if tr else "All endpoints") + f": `{s['servers'][0]['url']}`. " + ("Anahtarlı uç noktalar `Authorization: Bearer mdl_...` ister; \"Herkese açık\" olanlar anahtarsız çağrılır ve CORS'a açıktır." if tr else
                                                                                                          "Key-protected endpoints need `Authorization: Bearer mdl_...`; \"Public\" ones need no key and allow CORS.") + "\n")
    etiket = {"Genel": "Genel" if tr else "General", "Herkese açık": "Herkese açık" if tr else "Public", "Hesap": "Hesap" if tr else "Account", "Koordinatör": "Koordinatör" if tr else "Coordinator"}
    for yol, op in s["paths"].items():
        for yontem, d in op.items():
            baslik = d["summary"] if tr else d.get("x-en", d["summary"])
            gerek = "anahtar gerekli" if d.get("security") else "anahtarsız"
            if not tr:
                gerek = "key required" if d.get("security") else "no key"
            cikti.append(f"## {yontem.upper()} `{yol}`\n")
            cikti.append(f"**{baslik}** · {etiket.get(d['tags'][0], d['tags'][0])} · {gerek}\n")
            if d.get("description") and tr:
                cikti.append(d["description"] + "\n")
            for prm in d.get("parameters", []):
                cikti.append(("Yol parametresi" if tr else "Path parameter") + f": `{prm['name']}`\n")
            if "requestBody" in d:
                cikti.append(("**İstek gövdesi** (JSON):" if tr else "**Request body** (JSON):") + "\n")
                cikti.append(alan_tablosu(d["requestBody"]["content"]["application/json"]["schema"], bil))
            cikti.append(("**Yanıtlar:**" if tr else "**Responses:**") + "\n")
            cikti.append("| HTTP | " + ("Anlamı" if tr else "Meaning") + " |\n|---|---|\n" + "\n".join(f"| {k} | {v['description']} |" for k, v in d["responses"].items()) + "\n")
            for k, v in d["responses"].items():
                if k.startswith("2") and "content" in v:
                    sch = v["content"]["application/json"]["schema"]
                    t = alan_tablosu(sch, bil)
                    if t:
                        cikti.append((f"**{k} yanıt alanları:**" if tr else f"**{k} response fields:**") + "\n")
                        cikti.append(t)
                    break
    cikti.append("## " + ("Hata biçimi" if tr else "Error format") + "\n")
    cikti.append(("Tüm hatalar şu biçimdedir; `kod` makine okunur, `hata` insan okunurdur:" if tr else "All errors have this shape; `kod` is machine-readable, `hata` human-readable:") + "\n")
    cikti.append('```json\n{"hata": "Geçerli bir API anahtarı gerekli (Authorization: Bearer mdl_...).", "kod": "yetkisiz"}\n```\n')
    return "\n".join(cikti)


# ------------------------------------------------------------------ şablon
def ADRES(on, slug):
    return (on + "/") if slug in ("giris", "index") else f"{on}/{slug}/"


def nav_html(dil, sayfalar, aktif):
    ui = UI[dil]
    on = "" if dil == "tr" else "/en"
    gruplar = {}
    for s in sayfalar:
        gruplar.setdefault(s["bolum"], []).append(s)
    parcalar = []
    for bolum in BOLUM_SIRASI[dil] + [b for b in gruplar if b not in BOLUM_SIRASI[dil]]:
        if bolum not in gruplar:
            continue
        li = "".join(f'<li><a href="{(on + "/") if s["slug"] in ("giris", "index") else on + "/" + s["slug"] + "/"}"{" aria-current=\"page\"" if s["slug"] == aktif else ""}>{html.escape(s["baslik"])}</a></li>' for s in sorted(gruplar[bolum], key=lambda x: x["sira"]))
        parcalar.append(f"<h4>{html.escape(bolum)}</h4><ul>{li}</ul>")
    return "".join(parcalar)


def sayfa_html(dil, sayfalar, s, govde_html, basliklar):
    ui = UI[dil]
    on = "" if dil == "tr" else "/en"
    diger = "en" if dil == "tr" else "tr"
    slug = s["slug"]
    yol = f"{on}/{slug}/" if slug != "giris" and slug != "index" else (f"{on}/" if on else "/")
    ana = slug in ("giris", "index")
    canonical = BASE + (yol if not ana else (on + "/" if on else "/"))
    ayni = [x for x in sayfalar if x["slug"] == slug]
    diger_yol = None
    toc = "".join(f'<li class="sev{sev}"><a href="#{hid}">{html.escape(t)}</a></li>' for sev, hid, t in basliklar if sev in (2, 3))
    toc_html = f'<aside class="toc" aria-label="{ui["bu_sayfada"]}"><h4>{ui["bu_sayfada"]}</h4><ul>{toc}</ul></aside>' if toc else ""
    sirali = sorted(sayfalar, key=lambda x: (BOLUM_SIRASI[dil].index(x["bolum"]) if x["bolum"] in BOLUM_SIRASI[dil] else 99, x["sira"]))
    idx = next((i for i, x in enumerate(sirali) if x["slug"] == slug), 0)
    gez = ""
    if idx > 0:
        p = sirali[idx - 1]
        gez += f'<a class="onceki" href="{ADRES(on, p["slug"])}"><small>{ui["on"]}</small>{html.escape(p["baslik"])}</a>'
    if idx < len(sirali) - 1:
        n = sirali[idx + 1]
        gez += f'<a class="sonraki" href="{ADRES(on, n["slug"])}"><small>{ui["son"]}</small>{html.escape(n["baslik"])}</a>'
    gecis = ADRES("/en" if dil == "tr" else "", slug)
    gecis_var = os.path.exists(os.path.join(KOK, "icerik", diger, slug + ".md")) or slug == "api-referans"
    gecis_href = gecis if gecis_var else ui["gecis_yol"]
    not_en = f'<p class="kutu-en">{ui["en_not"]}</p>' if ui["en_not"] and ana else ""
    return f"""<!doctype html>
<html lang="{ui['lang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(s['baslik'])} · Modelen {ui['ad']}</title>
<meta name="description" content="{html.escape(s['ozet'] or s['baslik'], quote=True)}">
<link rel="canonical" href="{canonical}">
<meta name="theme-color" content="#101013"><meta name="color-scheme" content="dark">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/assets/belgeler.css">
</head>
<body data-dil="{dil}" data-kopyala="{ui['kopyala']}" data-kopyalandi="{ui['kopyalandi']}" data-yok="{ui['sayfa_yok']}">
<a class="atla" href="#icerik">{'İçeriğe geç' if dil == 'tr' else 'Skip to content'}</a>
<header class="ust"><div class="ust-ic">
<div class="marka"><a class="marka-site" href="{SITE}{'/en/' if dil == 'en' else '/'}" aria-label="modelen.tr">{LOGO}<span>modelen</span></a><a class="marka-docs" href="{on or '/'}"><em>{ui['ad']}</em></a></div>
<div class="arama"><input id="ara" type="search" placeholder="{ui['ara']}" aria-label="{ui['ara_etiket']}" autocomplete="off"><div id="sonuc" class="sonuc" hidden></div></div>
<nav class="ust-link"><a href="{SITE}/giris">{ui['portal']}</a><a href="{GITHUB}" rel="noopener">GitHub</a><a class="dil" href="{gecis_href}" hreflang="{diger}" lang="{diger}">{ui['gecis']}</a></nav>
</div></header>
<div class="duzen">
<nav class="yan" aria-label="{ui['ad']}"><details class="yan-menu" open><summary>{ui['menu']}</summary>{nav_html(dil, sayfalar, slug)}</details></nav>
<main id="icerik" class="icerik"><article>
{not_en}{govde_html}
</article>
<div class="gez">{gez}</div></main>
{toc_html}
</div>
<footer class="alt"><p>{ui['alt']}</p><p class="surum">{ui['sonraki_surum']}</p></footer>
<script src="/assets/belgeler.js" defer></script>
</body>
</html>
"""


def olustur():
    if os.path.exists(CIKTI):
        shutil.rmtree(CIKTI)
    os.makedirs(os.path.join(CIKTI, "assets"))
    for d in ("belgeler.css", "belgeler.js"):
        shutil.copy(os.path.join(KOK, "assets", d), os.path.join(CIKTI, "assets", d))
    shutil.copy(os.path.join(DEPO, "site", "assets", "favicon.svg"), os.path.join(CIKTI, "assets", "favicon.svg"))
    with open(os.path.join(CIKTI, "openapi.json"), "w", encoding="utf-8") as f:
        json.dump(api_sema.sema(SITE), f, ensure_ascii=False, indent=2)
    url_listesi, arama = [], {}
    for dil in ("tr", "en"):
        sayfalar = sayfalari_oku(dil)
        sayfalar.append(dict(slug="api-referans", baslik="API başvurusu" if dil == "tr" else "API reference", bolum="Portal API" if dil == "tr" else "Portal API", sira=90,
                             ozet="Portal API v1 uç noktaları, alanlar ve yanıtlar." if dil == "tr" else "Portal API v1 endpoints, fields and responses.", govde=api_referans_md(dil), dil=dil))
        on = "" if dil == "tr" else "en"
        arama[dil] = []
        for s in sayfalar:
            h, basliklar = md.cevir(s["govde"])
            if not any(sev == 1 for sev, _, _ in basliklar):
                h = f'<h1>{html.escape(s["baslik"])}</h1>\n' + h
            slug = s["slug"]
            hedef = os.path.join(CIKTI, on, "" if slug in ("giris", "index") else slug)
            os.makedirs(hedef, exist_ok=True)
            with open(os.path.join(hedef, "index.html"), "w", encoding="utf-8", newline="\n") as f:
                f.write(sayfa_html(dil, sayfalar, s, h, basliklar))
            yol = ("/" + on + "/" if on else "/") + ("" if slug in ("giris", "index") else slug + "/")
            url_listesi.append(BASE + yol)
            duz = re.sub(r"<[^>]+>", " ", h)
            arama[dil].append({"b": s["baslik"], "u": yol, "bolum": s["bolum"], "t": html.unescape(re.sub(r"\s+", " ", duz))[:1800]})
    for dil, liste in arama.items():
        with open(os.path.join(CIKTI, "assets", f"arama-{dil}.json"), "w", encoding="utf-8") as f:
            json.dump(liste, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(CIKTI, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(f"  <url><loc>{u}</loc></url>\n" for u in url_listesi) + "</urlset>\n")
    with open(os.path.join(CIKTI, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
    yok = {"baslik": "404", "ozet": "", "slug": "404", "bolum": "", "sira": 0}
    with open(os.path.join(CIKTI, "404.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(sayfa_html("tr", sayfalari_oku("tr"), yok, f'<h1>404</h1><p>{UI["tr"]["yok"]}</p><p><a href="/">{UI["tr"]["anasayfa"]}</a></p>', []).replace('<link rel="canonical" href="https://docs.modelen.tr/404/">', '<meta name="robots" content="noindex">'))
    print(f"{len(url_listesi)} sayfa üretildi -> {CIKTI}")


if __name__ == "__main__":
    olustur()
