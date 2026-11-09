# -*- coding: utf-8 -*-
"""Ana sayfa (TR/EN). Düzen Mistral'in sayfa yapısından esinlenmiştir (çerçeveli koyu sayfa,
yapışkan yan menü, "Biz X. Siz Y." satırları, düşen bloklar, dönen kelime); renk, logo, görsel
ve metinler bize aittir. Kanıt olarak müşteri yerine kendi ölçümlerimiz kullanılır."""


def _lcg(seed):
    s = seed
    while True:
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        yield s


def strings(n=16):
    g = _lcg(7117)
    cizgi = []
    for _ in range(n):
        x1 = next(g) % 100
        y1 = next(g) % 100
        dx = 12 + next(g) % 26
        dy = -(4 + next(g) % 12)
        cizgi.append(f'<line x1="{x1}%" y1="{y1}%" x2="{x1 + dx}%" y2="{y1 + dy}%"/>')
    return '<svg class="strings" aria-hidden="true">' + "".join(cizgi) + "</svg>"


def sky(n_kayan=7, n_toz=34):
    """Hero için kayan yıldızlar ve yıldız tozu (yalnızca CSS animasyonu)."""
    g = _lcg(8675309)
    toz = []
    for _ in range(n_toz):
        x, y = next(g) % 100, next(g) % 78
        boy = 1 + next(g) % 3
        sure = 3 + next(g) % 5
        gec = -(next(g) % 80) / 10
        toz.append(f'<i class="tw" style="left:{x}%;top:{y}%;width:{boy}px;height:{boy}px;--t:{sure}s;--d:{gec}s"></i>')
    kayan = []
    for k in range(n_kayan):
        x, y = next(g) % 62, next(g) % 38
        boy = 120 + next(g) % 110
        aci = 22 + next(g) % 16
        sure = 9 + next(g) % 7
        gec = (k * 2.3) % 11
        kayan.append(f'<i class="shoot" style="left:{x}%;top:{y}%;--len:{boy}px;--a:{aci}deg;--dur:{sure}s;--del:{gec:.1f}s"></i>')
    return '<div class="sky" aria-hidden="true">' + "".join(toz) + "".join(kayan) + "</div>"


def blocks(heights=(4, 3, 2, 1, 1), right=False):
    cols = []
    for c, h in enumerate(heights):
        kare = "".join(
            f'<i class="c{min(4, 1 + r)}" style="--d:{350 + c * 150 + r * 190}"></i>' for r in range(h))
        fn = (f'<b class="fn" style="--d:{1500 + c * 330}">{fener_svg()}</b>' if (c < 3 and not right) else "")
        cols.append(f'<div class="col">{kare}{fn}</div>')
    return f'<div class="blocks{" right" if right else ""}" aria-hidden="true">' + "".join(cols) + "</div>"


def mosaic(cols=18, rows=8, seed=424242):
    g = _lcg(seed)
    h = []
    for _ in range(cols * rows):
        if next(g) % 100 < 26:
            h.append(f'<i class="on d{1 + (next(g) % 4)}"></i>')
        else:
            h.append("<i></i>")
    return f'<div class="net" style="--c:{cols}" aria-hidden="true">' + "".join(h) + "</div>"


def cells(lit_all):
    return '<div class="cells" aria-hidden="true">' + "".join(
        '<i class="on"></i>' if (lit_all or i == 24) else "<i></i>" for i in range(25)) + "</div>"


_RENK = {"B": "#e0262d", "D": "#2a2a31", "f": "#ff4640", "O": "#5f0d13", "C": "#ff6a62", "P": "#8a8a96"}


def _sprite(kare):
    """Piksel ekran kartı (24x11), kendi çizimimiz; pervane iki karede dönüyormuş gibi görünür."""
    W, H = 24, 11
    g = [["."] * W for _ in range(H)]
    for x in range(1, 23):
        g[1][x] = g[8][x] = "B"
    for y in range(1, 9):
        g[y][1] = g[y][22] = "B"
    for y in range(2, 8):
        for x in range(2, 22):
            g[y][x] = "D"
        g[y][0] = "P"
    disk = [".fff.", "fffff", "fffff", "fffff", ".fff."]
    artı = {(2, 0), (2, 1), (0, 2), (1, 2), (2, 2), (3, 2), (4, 2), (2, 3), (2, 4)}
    çarpı = {(0, 0), (4, 0), (1, 1), (3, 1), (2, 2), (1, 3), (3, 3), (0, 4), (4, 4)}
    kanat = artı if kare == 1 else çarpı
    for fx in (3, 10):
        for dy, satir in enumerate(disk):
            for dx, ch in enumerate(satir):
                if ch == "f":
                    g[2 + dy][fx + dx] = "O" if (dx, dy) in kanat else "f"
    for y in range(3, 7):
        for x in range(17, 21):
            g[y][x] = "C"
    for x in range(3, 23, 2):
        g[9][x] = "P"
    rects = []
    for y, satir in enumerate(g):
        x = 0
        while x < W:
            ch = satir[x]
            if ch == ".":
                x += 1
                continue
            n = x
            while n < W and satir[n] == ch:
                n += 1
            rects.append(f'<rect x="{x}" y="{y}" width="{n - x}" height="1" fill="{_RENK[ch]}"/>')
            x = n
    return "".join(rects)


_FENER = ["....BBBB....",
          "...B....B...",
          "....CCCC....",
          "...CCCCCC...",
          "..CCCCCCCC..",
          "...BGGGGB...",
          "...BGGGGB...",
          "...BGFFGB...",
          "...BGFFGB...",
          "...BGGGGB...",
          "...BGGGGB...",
          "..BBBBBBBB..",
          "..BBBBBBBB.."]
_FENER2 = list(_FENER)
_FENER2[6] = "...BGFGGB..."
_FENER2[8] = "...BGFFGB..."
_FENER2[9] = "...BGGFGB..."
_FRENK = {"B": "#e30a17", "C": "#ff4640", "G": "#fafaf4", "F": "#ff4640"}


def _fener_sprite(kare):
    """12x13 piksel fener (kulp, kapak, camlı gövde, taban); iki karede alev titrer."""
    g = _FENER if kare == 1 else _FENER2
    rects = []
    for y, satir in enumerate(g):
        x = 0
        while x < len(satir):
            ch = satir[x]
            if ch == ".":
                x += 1
                continue
            n = x
            while n < len(satir) and satir[n] == ch:
                n += 1
            rects.append(f'<rect x="{x}" y="{y}" width="{n - x}" height="1" fill="{_FRENK[ch]}"/>')
            x = n
    return "".join(rects)


def fener_svg():
    """Üst üste iki kare: CSS ile dönüşümlü görünür (alev titremesi)."""
    ic = lambda s: f'<svg viewBox="0 0 12 13" shape-rendering="crispEdges" aria-hidden="true">{_fener_sprite(s)}</svg>'
    return f'<span class="f1">{ic(1)}</span><span class="f2">{ic(2)}</span>'


def sprite_defs():
    return ('<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false">'
            f'<symbol id="gpu1" viewBox="0 0 24 11">{_sprite(1)}</symbol>'
            f'<symbol id="gpu2" viewBox="0 0 24 11">{_sprite(2)}</symbol></svg>')


def gpu_svg(sym, led_delay=0):
    return (f'<svg viewBox="0 0 24 11" shape-rendering="crispEdges"><use href="#{sym}"/>'
            f'<rect class="led" x="20" y="8" width="1" height="1" style="animation-delay:-{led_delay}s"/></svg>')


def gpu_net(cols=4, rows=3):
    g = _lcg(99)
    hucre = []
    for _ in range(cols * rows):
        hucre.append(f'<div class="g">{gpu_svg("gpu1", 0.4 * (next(g) % 12))}</div>')
    return f'<div class="gpunet" style="--c:{cols}" aria-hidden="true">' + "".join(hucre) + "</div>"


def story(L):
    pencere = "".join(
        f'<div class="w w{i + 1}"><h2>{w}</h2><p>{p}</p></div>' for i, (w, p) in enumerate(L["story_w"]))
    return (f'<section class="story" aria-label="{L["story_label"]}"><div class="stage">'
            f'<p class="lead-in">{L["story_lead"]}</p><div class="words">{pencere}</div></div></section>')


MARQ = ["APACHE-2.0", "LORA", "DILOCO", "QWEN3-0.6B-BASE", "TURKISHMMLU", "WIKITEXT-2",
        "TÜRKÇE VİKİPEDİ", "PYTORCH", "PEFT", "8 GB VRAM"]


def marquee(items):
    ic = "".join(f"<span>{x}</span>" for x in items)
    return f'<div class="marq" aria-hidden="true"><div class="track">{ic}{ic}</div></div>'


def build(L):
    hero = f"""
<section class="hero">
  {sky()}
  {strings()}
  {blocks()}
  <div class="diamond" aria-hidden="true"></div><div class="diamond sm" aria-hidden="true"></div>
  <div class="hero-copy">
    <h1><span class="vh">{L['h1_full']}</span><span aria-hidden="true">{L['h1_pre']} <span class="swap"><b>{L['w'][0]}</b><b>{L['w'][1]}</b><b>{L['w'][2]}</b><b>{L['w'][3]}</b></span> {L['h1_post']}</span></h1>
    <p class="sub">{L['sub']}</p>
    <div class="actions"><a class="btn" href="{L['join_href']}">{L['join']}</a><a class="btn ghost" href="{L['how_href']}">{L['how']}</a></div>
  </div>
  <a class="ticker" href="{L['road_href']}"><span class="sq" aria-hidden="true"></span><span class="t">{L['ticker']}</span><span aria-hidden="true">›</span></a>
</section>
{marquee(MARQ)}
{sprite_defs()}
{story(L)}
"""
    viz_bars = f"""<div class="viz bars">
<div class="bar"><span>{L['bar1']}</span><div class="track"><i style="width:35.6%"></i><u style="left:20%"></u></div><b>35,6%</b></div>
<div class="bar"><span>{L['bar2']}</span><div class="track"><i style="width:34.7%"></i><u style="left:20%"></u></div><b>34,7%</b></div>
<p class="vcap">{L['bar_cap']}</p></div>"""
    rows = f"""
<div class="frame showcase">
  <aside class="side" aria-label="{L['side_label']}"><p>{L['side_title']}</p>
    <a href="#acik">{L['s1']}<span aria-hidden="true">›</span></a><a href="#ekran">{L['s2']}<span aria-hidden="true">›</span></a>
    <a href="#seyrek">{L['s3']}<span aria-hidden="true">›</span></a><a href="#sinirlar">{L['s4']}<span aria-hidden="true">›</span></a></aside>
  <div class="rows">
    <section class="row rv" id="acik"><div><h3>{L['r1h']}</h3><p>{L['r1p']}</p><a class="more" href="{L['r1_href']}">{L['r1_link']}</a></div>
      <div class="viz">{gpu_net()}<p class="vcap">{L['r1cap']}</p></div></section>
    <section class="row flip rv" id="ekran"><div><h3>{L['r2h']}</h3><p>{L['r2p']}</p><a class="more" href="{L['how_href']}">{L['how']}</a></div>
      <div class="viz scale"><div class="big"><span>{L['base']}</span></div><div class="small"><span>{L['adapter']}</span></div><p class="vcap">{L['r2cap']}</p></div></section>
    <section class="row rv" id="seyrek"><div><h3>{L['r3h']}</h3><p>{L['r3p']}</p><a class="more" href="{L['meas_href']}">{L['r3_link']}</a></div>
      <div class="viz"><p class="rowlabel">{L['every']}</p>{cells(True)}<p class="rowlabel">{L['sparse']}</p>{cells(False)}<p class="vcap">{L['r3cap']}</p></div></section>
    <section class="row flip rv" id="sinirlar"><div><h3>{L['r4h']}</h3><p>{L['r4p']}</p><a class="more" href="{L['road_href']}">{L['road']}</a></div>
      {viz_bars}</section>
  </div>
</div>
"""
    stats = f"""
<div class="frame">
<section class="sec" aria-labelledby="olcum">
  <h2 class="rv" id="olcum">{L['st_h']}</h2>
  <p class="lead">{L['st_lead']}</p>
  <div class="stats">
    <div><b>~25×</b><em>{L['st1e']}</em><p>{L['st1p']}</p></div>
    <div><b>{L['st2b']}</b><em>{L['st2e']}</em><p>{L['st2p']}</p></div>
    <div><b>{L['st3b']}</b><em>{L['st3e']}</em><p>{L['st3p']}</p></div>
    <div class="neg"><b>0</b><em>{L['st4e']}</em><p>{L['st4p']}</p></div>
  </div>
  <p class="fine">{L['st_fine']}</p>
</section>
<section class="sec" aria-labelledby="neredeyiz">
  <h2 class="rv" id="neredeyiz">{L['where']}</h2>
  <div class="stages">
    <div class="done"><small>{L['g0']}</small><b>{L['g0t']}</b><p>{L['g0p']}</p></div>
    <div class="done"><small>{L['g1']}</small><b>{L['g1t']}</b><p>{L['g1p']}</p></div>
    <div><small>{L['g2']}</small><b>{L['g2t']}</b><p>{L['g2p']}</p></div>
    <div><small>{L['g3']}</small><b>{L['g3t']}</b><p>{L['g3p']}</p></div>
    <div><small>{L['g4']}</small><b>{L['g4t']}</b><p>{L['g4p']}</p></div>
  </div>
  <p class="fine">{L['where_fine']}</p>
</section>
<section class="sec brandsec" aria-labelledby="neden">
  <div class="brandgrid">
    <div class="bt">
      <h2 class="rv" id="neden">{L['brand_h']}</h2>
      <p class="lead">{L['brand_p1']}</p>
      <p>{L['brand_p2']}</p>
      <dl class="kv2">
        <div><dt>{L['bk1']}</dt><dd>{L['bv1']}</dd></div>
        <div><dt>{L['bk2']}</dt><dd>{L['bv2']}</dd></div>
        <div><dt>{L['bk3']}</dt><dd>{L['bv3']}</dd></div>
      </dl>
    </div>
    <div class="bl"><img src="{L['logo_src']}" width="520" height="520" alt="{L['logo_alt']}" loading="lazy"></div>
  </div>
</section>
<section class="sec" aria-labelledby="yardim">
  <h2 class="rv" id="yardim">{L['help_h']}</h2>
  <p class="lead">{L['help_lead']}</p>
  <div class="needs">
    <a href="{L['join_href']}"><small>01</small><b>{L['n1']}</b><span>{L['n1p']}</span></a>
    <a href="{L['join_href']}"><small>02</small><b>{L['n2']}</b><span>{L['n2p']}</span></a>
    <a href="{L['join_href']}"><small>03</small><b>{L['n3']}</b><span>{L['n3p']}</span></a>
    <a href="{L['join_href']}"><small>04</small><b>{L['n4']}</b><span>{L['n4p']}</span></a>
  </div>
</section>
<section class="sec" aria-labelledby="derin">
  <h2 class="rv" id="derin">{L['deeper']}</h2>
  <div class="deeper">
    <a href="{L['how_href']}"><b>{L['d1']}</b><span>{L['d1p']}</span></a>
    <a href="{L['road_href']}"><b>{L['d2']}</b><span>{L['d2p']}</span></a>
    <a href="{L['faq_href']}"><b>{L['d3']}</b><span>{L['d3p']}</span></a>
  </div>
</section>
<section class="sec cta">
  <h2>{L['cta_h']}</h2><p>{L['cta_p']}</p>
  <a class="btn accent" href="{L['join_href']}">{L['join']}</a>
</section>
</div>
"""
    return hero + rows + stats


TR_L = dict(
    logo_src="assets/halay-halkasi.svg", logo_alt="Modelen logosu: birbirinin koluna giren beş el, her biri bir fener taşıyor",
    brand_h="Neden Halay Halkası?",
    brand_p1="Halayda herkes komşusunun koluna girer; çemberin ne başı vardır ne sonu. Ağımız da böyle çalışacak.",
    brand_p2="Her gönüllü bir fener taşır: ekran kartınızın verdiği emek, bir ışık. Işık elden ele geçer, onu hiçbir tek el tutmaz.",
    bk1="Çember", bv1="Lider yok, herkes eşit yerde durur.",
    bk2="Eller", bv2="Katkılar birbirine bağlı ve birbirini doğrular.",
    bk3="Fenerler", bv3="Her gönüllünün ışığı ortak modele akar.",
    help_h="Aradığımız yardım", help_lead="Bu iş tek kişilik değil. Şu an en çok şunlara ihtiyacımız var:",
    n1="Dil kıyas testleri", n1p="Modelin gerçekten iyileştiğini ölçmek için daha çok ve daha iyi test (önce Türkçe).",
    n2="Veri ve lisans", n2p="Açık, temiz, lisansı belli veri kaynaklarını (önce Türkçe) bulmak ve belgelemek.",
    n3="Güvenlik ve doğrulama", n3p="Hatalı ya da kötü niyetli katkıyı yakalayan yöntemler tasarlamak.",
    n4="Gönüllü istemcisi", n4p="Bilgisayarda güvenle çalışan açık kaynak istemci (Windows ve Ubuntu) yayında; imzalı sürüm sırada.",
    h1_full="Yapay zekâ ortak olmalı.", h1_pre="Yapay zekâ", h1_post="olmalı.",
    w=["ortak", "açık", "şeffaf", "bizim"],
    sub="Boştaki ekran kartlarını birleştirip açık dil modellerini birlikte eğitiyoruz. İlk dilimiz Türkçe. Sonuç açık lisansla, herkesin kullanımına.",
    join="Gönüllü ol", join_href="katil.html", how="Nasıl çalışır", how_href="nasil-calisir.html",
    road="Yol haritası", road_href="yol-haritasi.html", faq_href="sss.html",
    ticker="Araştırma aşamasındayız. Yayınlanmış model yok.",
    story_label="İlkelerimiz", story_lead="Yapay zekâda şunu kimse tek başına tutmasın:",
    story_w=[("kodu.", "Eğitim kodunu ve gönüllü istemcisini Apache-2.0 ile açtık."),
             ("ağırlıkları.", "Model ağırlıkları, herkesin indirip kendi makinesinde çalıştırabileceği biçimde yayınlanacak."),
             ("veri listesini.", "Neyle eğittiğimizi ve her kaynağın lisansını açıkça yazacağız."),
             ("kararları.", "Katkılar kayıt altında olacak; yönü birlikte belirleyeceğiz.")],
    side_label="Bölümler", side_title="Modelen", s1="Açık modeller", s2="Ekran kartı", s3="Seyrek eğitim", s4="Sınırlar",
    r1h="Birlikte eğitiriz. Hepimizin olur.",
    r1p="Kodu ve model ağırlıklarını Apache-2.0 ile yayınlayacağız. Eğitim verisinin kaynaklarını ve lisanslarını açıkça listeleyeceğiz.",
    r1_href="lisans.html", r1_link="Lisans", r1cap="Her kare bir gönüllü ekran kartını temsil eden illüstrasyondur. Gerçek ağ henüz yok.",
    r2h="Ekran kartınız yeter. Sunucu salonu gerekmez.",
    r2p="Taban modeli dondurup yalnızca küçük bir LoRA adaptörünü eğitiyoruz. Denememizde tepe bellek 5,2 GB oldu; 8 GB'lık bir dizüstü kartına sığdı.",
    base="taban ≈ 1,2 GB", adapter="adaptör ≈ 40 MB", r2cap="Alanlar gerçek boyut oranında (≈30:1)",
    r3h="Az veri taşırız. Aynı sonucu alırız.",
    r3p="Gönüllüler her adımda değil, 25 adımda bir senkronize olur. Simülasyonumuzda yaklaşık 25 kat az veri taşındı; bayt başına bitte fark %0,09 oldu.",
    r3_link="Ölçümlerimiz", meas_href="olcumler.html", every="Her adımda senkron: 25 senkron", sparse="Seyrek senkron: 1 senkron",
    r3cap="25 adımlık bir pencere (illüstrasyon)",
    r4h="Sınırlarımızı da yazarız.",
    r4p="Türkçe dil modellemesi iyileşti, ama TurkishMMLU'da iyileşme görmedik. Hepsi küçük deney: tek koşu, tek tohum, gerçek ağ yok.",
    bar1="Taban", bar2="LoRA sonrası", bar_cap="TurkishMMLU 5-shot · kesik çizgi: şans %20 · ölçüm gürültüsü ≈ ±1,6 puan",
    st_h="Şimdiye kadar ölçtüklerimiz", st_lead="Müşteri logomuz yok. Elimizde ölçümlerimiz var.",
    st1e="daha az veri taşındı", st1p="Adaptör üzerinde seyrek senkronizasyon, 4 sanal işçi. Simülasyon.",
    st2b="%0,09", st2e="fark", st2p="Seyrek ve her adımda senkron eğitim arasında, bayt başına bit: 1,2166 ve 1,2155.",
    st3b="−%4,3", st3e="Türkçe bayt başına bit", st3p="Qwen3-0.6B'ye 20 dakikalık LoRA ile, 8 GB'lık tüketici ekran kartında.",
    st4e="kıyas iyileşmesi", st4p="TurkishMMLU %35,6 → %34,7, fark gürültü içinde. Henüz “model iyileşti” diyemiyoruz.",
    st_fine="Küçük denemeler: tek koşu, tek tohum, gerçek ağ yok. Tüm tablolar <a href=\"olcumler.html\">Ölçümler</a> sayfasında.",
    where="Neredeyiz",
    g0="00 · YAPILDI", g0t="Araştırma", g0p="Küçük modelde seyrek senkronizasyon simülasyonu.",
    g1="01 · İLK DENEY", g1t="İlk dil: Türkçe", g1p="LoRA ile 8 GB'ta kısa sürekli ön eğitim.",
    g2="02 · SIRADA", g2t="Veri ve ölçüm", g2p="Daha çok Türkçe veri, kıyas testleri.",
    g3="03 · YAYINDA (ALFA)", g3t="Gönüllü istemcisi", g3p="Açık kaynak; Windows ve Ubuntu. İmzalı güncelleme sırada.",
    g4="04", g4t="Pilot ve açık ağ", g4p="Gerçek ağda deneme, sonra ilk yayın.",
    where_fine="Tarih taahhüdü vermiyoruz.",
    deeper="Daha derine", d1="Nasıl çalışır", d1p="Taban, adaptör ve seyrek senkronizasyon.",
    d2="Yol haritası", d2p="Aşamalar ve bilinen riskler.", d3="Sık sorulan sorular", d3p="Gönüllülük, güvenlik, lisans, veri.",
    cta_h="GPU'nuzu adayın ya da koordinatör olun.", cta_p="E-posta adresinizi yalnızca Modelen duyuruları için kullanırız.",
)

EN_L = dict(
    logo_src="../assets/halay-halkasi.svg", logo_alt="Modelen logo: five hands linked arm in arm, each carrying a lantern",
    brand_h="Why the Halay Ring?",
    brand_p1="In a halay everyone links arms with their neighbour; the circle has no beginning and no end. Our network will work the same way.",
    brand_p2="Every volunteer carries a lantern: the effort of your graphics card, a light. The light passes from hand to hand and no single hand holds it.",
    bk1="The circle", bv1="No leader; everyone stands in an equal place.",
    bk2="The hands", bv2="Contributions are linked and verify one another.",
    bk3="The lanterns", bv3="Each volunteer's light flows into the shared model.",
    help_h="Help we are looking for", help_lead="This is not a one-person job. Right now we need most:",
    n1="Language benchmarks", n1p="More and better tests (Turkish first) to measure whether the model really improves.",
    n2="Data and licensing", n2p="Finding and documenting open, clean, clearly licensed data sources (Turkish first).",
    n3="Security and verification", n3p="Designing methods that catch faulty or malicious contributions.",
    n4="Volunteer client", n4p="An open-source client that runs safely on a computer (Windows and Ubuntu) is available; a signed release is next.",
    h1_full="AI should be shared.", h1_pre="AI should be", h1_post=".",
    w=["shared", "open", "ours", "yours"],
    sub="We are pooling idle graphics cards to train open language models together. Turkish comes first. The result goes out under an open licence for everyone to use.",
    join="Volunteer", join_href="join.html", how="How it works", how_href="how-it-works.html",
    road="Roadmap", road_href="roadmap.html", faq_href="faq.html",
    ticker="We are at the research stage. No released model yet.",
    story_label="Our principles", story_lead="In AI, no one should hold this alone:",
    story_w=[("the code.", "We have opened the training code and the volunteer client under Apache-2.0."),
             ("the weights.", "Model weights will be released so anyone can download and run them on their own machine."),
             ("the data list.", "We will state plainly what we train on and the licence of every source."),
             ("the decisions.", "Contributions will be on record; we will set the direction together.")],
    side_label="Sections", side_title="Modelen", s1="Open models", s2="Graphics card", s3="Sparse training", s4="Limits",
    r1h="We train it together. It belongs to everyone.",
    r1p="We will release code and model weights under Apache-2.0. We will list training-data sources and their licences openly.",
    r1_href="license.html", r1_link="Licence", r1cap="Each square illustrates one volunteer graphics card. The real network does not exist yet.",
    r2h="Your graphics card is enough. No server room needed.",
    r2p="We freeze the base model and train only a small LoRA adapter. In our experiment peak memory was 5.2 GB; it fit on an 8 GB laptop card.",
    base="base ≈ 1.2 GB", adapter="adapter ≈ 40 MB", r2cap="Areas are to scale (≈30:1)",
    r3h="We move less data. We get the same result.",
    r3p="Volunteers synchronise once every 25 steps, not every step. In our simulation about 25 times less data moved; the difference was 0.09% in bits per byte.",
    r3_link="Our measurements", meas_href="measurements.html", every="Synchronise every step: 25 syncs", sparse="Sparse sync: 1 sync",
    r3cap="A 25-step window (illustration)",
    r4h="We write down our limits too.",
    r4p="Turkish language modelling improved, but we saw no improvement on TurkishMMLU. All small experiments: single run, single seed, no real network.",
    bar1="Base", bar2="After LoRA", bar_cap="TurkishMMLU 5-shot · dashed line: chance 20% · measurement noise ≈ ±1.6 points",
    st_h="What we have measured so far", st_lead="We have no customer logos. We have measurements.",
    st1e="less data moved", st1p="Sparse synchronisation on an adapter, 4 simulated workers. Simulation.",
    st2b="0.09%", st2e="difference", st2p="Between sparse and every-step synchronised training, in bits per byte: 1.2166 vs 1.2155.",
    st3b="−4.3%", st3e="Turkish bits per byte", st3p="20 minutes of LoRA on Qwen3-0.6B, on an 8 GB consumer graphics card.",
    st4e="benchmark improvement", st4p="TurkishMMLU 35.6% → 34.7%, within noise. We cannot yet say “the model improved”.",
    st_fine="Small experiments: single run, single seed, no real network. All tables on the <a href=\"measurements.html\">Measurements</a> page.",
    where="Where we are",
    g0="00 · DONE", g0t="Research", g0p="Sparse-sync simulation on a small model.",
    g1="01 · FIRST EXPERIMENT", g1t="First language: Turkish", g1p="Short continued pre-training with LoRA on 8 GB.",
    g2="02 · NEXT", g2t="Data and evaluation", g2p="More Turkish data, benchmarks.",
    g3="03 · LIVE (ALPHA)", g3t="Volunteer client", g3p="Open source; Windows and Ubuntu. Signed updates next.",
    g4="04", g4t="Pilot and open network", g4p="Real-network trials, then a first release.",
    where_fine="No date commitments.",
    deeper="Go deeper", d1="How it works", d1p="Base, adapter and sparse synchronisation.",
    d2="Roadmap", d2p="Stages and known risks.", d3="FAQ", d3p="Volunteering, security, licence, data.",
    cta_h="Lend your GPU or become a coordinator.", cta_p="We use your email address only for Modelen announcements.",
)

TR = dict(
    title="Modelen · Yapay zekâ ortak olmalı",
    desc="Modelen, boştaki ekran kartlarını birleştirerek açık yapay zekâ modellerini topluluk olarak eğitmeyi hedefler. İlk dil Türkçe. Araştırma aşamasında.",
    wide=True, body=build(TR_L))
EN = dict(
    title="Modelen · AI should be shared",
    desc="Modelen aims to train open AI models as a community by pooling idle graphics cards. Turkish is the first language. Research stage.",
    wide=True, body=build(EN_L))
