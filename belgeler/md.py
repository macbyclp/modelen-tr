"""Küçük, bağımlılıksız Markdown → HTML çevirici (dokümantasyon sitesi için).

Desteklenen: başlıklar (#..####), paragraf, **kalın**, *italik*, `kod`, [bağlantı](url), kod blokları (```dil), sıralı/sırasız liste
(bir iç seviye), tablo, alıntı (>), yatay çizgi, uyarı kutuları (:::not / :::uyari / :::ipucu ... :::).
Ham HTML geçirilmez: tüm metin kaçışlanır. Başlıklara kendiliğinden `id` verilir.
"""
import html
import re

ANAHTAR = {
    "python": {"kw": r"\b(def|class|import|from|return|if|elif|else|for|while|in|not|and|or|try|except|finally|with|as|None|True|False|raise|lambda|pass|break|continue)\b"},
    "bash": {"kw": r"\b(curl|python|python3|py|sudo|cd|export|echo|ssh|systemctl|chmod|mkdir|cat|grep|pip)\b"},
    "js": {"kw": r"\b(const|let|var|function|return|if|else|for|await|async|new|null|true|false|import|from)\b"},
    "json": {"kw": r"\b(true|false|null)\b"},
}
ESLEME = {"py": "python", "sh": "bash", "shell": "bash", "javascript": "js", "javascript ": "js", "jsonc": "json"}


def kaçış(s):
    return html.escape(s, quote=True)


def vurgula(kod, dil):
    """Çok basit söz dizimi renklendirme: dize, yorum, sayı, anahtar sözcük. Çıktı güvenlidir (önce kaçışlanır)."""
    dil = ESLEME.get(dil, dil)
    if dil not in ANAHTAR:
        return kaçış(kod)
    yorum = {"python": r"#[^\n]*", "bash": r"#[^\n]*", "js": r"//[^\n]*", "json": r"(?!x)x"}[dil]
    desen = re.compile(rf"(?P<c>{yorum})|(?P<s>\"(?:\\.|[^\"\\\n])*\"|'(?:\\.|[^'\\\n])*')|(?P<k>{ANAHTAR[dil]['kw']})|(?P<n>\b\d+(?:\.\d+)?\b)")
    cikti, son = [], 0
    for m in desen.finditer(kod):
        cikti.append(kaçış(kod[son:m.start()]))
        sinif = {"c": "t-c", "s": "t-s", "k": "t-k", "n": "t-n"}[m.lastgroup]
        cikti.append(f'<span class="{sinif}">{kaçış(m.group())}</span>')
        son = m.end()
    cikti.append(kaçış(kod[son:]))
    return "".join(cikti)


def slug(metin):
    t = metin.lower().translate(str.maketrans("çğıöşüâîû", "cgiosuaiu"))
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-") or "bolum"


def satir_ici(m):
    kodlar = []

    def kod_sakla(x):
        kodlar.append(x.group(1))
        return f"\x00{len(kodlar) - 1}\x00"

    m = re.sub(r"`([^`]+)`", kod_sakla, m)
    m = kaçış(m)
    m = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", m)
    m = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", m)

    def baglanti(x):
        url = html.unescape(x.group(2))
        if not re.match(r"^(https?://|/|#|mailto:|[\w\-./]+(#[\w\-]+)?$)", url):
            return x.group(0)
        ek = ' rel="noopener"' if url.startswith("http") else ""
        return f'<a href="{kaçış(url)}"{ek}>{x.group(1)}</a>'

    m = re.sub(r"!\[([^\]]*)\]\((/[^)\s]+)\)", lambda x: f'<img src="{x.group(2)}" alt="{x.group(1)}" loading="lazy">', m)
    m = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", baglanti, m)
    m = re.sub(r"&lt;(https?://[^\s&]+)&gt;", r'<a href="\1" rel="noopener">\1</a>', m)
    return re.sub(r"\x00(\d+)\x00", lambda x: f"<code>{kaçış(kodlar[int(x.group(1))])}</code>", m)


def cevir(metin):
    """(html, başlıklar[(seviye, id, metin)]) döndürür."""
    satirlar = metin.replace("\r\n", "\n").split("\n")
    cikti, basliklar, i = [], [], 0
    kullanilan = {}

    def baslik_id(t):
        s = slug(t)
        kullanilan[s] = kullanilan.get(s, 0) + 1
        return s if kullanilan[s] == 1 else f"{s}-{kullanilan[s]}"

    while i < len(satirlar):
        s = satirlar[i]
        if not s.strip():
            i += 1
            continue
        # kod bloğu
        m = re.match(r"^```(\w*)\s*$", s)
        if m:
            dil, kod = m.group(1).lower(), []
            i += 1
            while i < len(satirlar) and not satirlar[i].startswith("```"):
                kod.append(satirlar[i])
                i += 1
            i += 1
            cikti.append(f'<div class="kod"><pre><code class="dil-{kaçış(dil)}">{vurgula(chr(10).join(kod), dil)}</code></pre></div>')
            continue
        # uyarı kutusu
        m = re.match(r"^:::(not|uyari|ipucu)\s*$", s)
        if m:
            tur, ic = m.group(1), []
            i += 1
            while i < len(satirlar) and satirlar[i].strip() != ":::":
                ic.append(satirlar[i])
                i += 1
            i += 1
            govde, _ = cevir("\n".join(ic))
            etiket = {"not": "Not", "uyari": "Dikkat", "ipucu": "İpucu"}[tur]
            cikti.append(f'<div class="kutu kutu-{tur}"><div class="kutu-b">{etiket}</div>{govde}</div>')
            continue
        # başlık
        m = re.match(r"^(#{1,4})\s+(.+?)\s*#*$", s)
        if m:
            sev, t = len(m.group(1)), m.group(2)
            hid = baslik_id(re.sub(r"[`*]", "", t))
            basliklar.append((sev, hid, re.sub(r"[`*]", "", t)))
            cikti.append(f'<h{sev} id="{hid}">{satir_ici(t)}<a class="cap" href="#{hid}" aria-label="Bu başlığa bağlantı">#</a></h{sev}>')
            i += 1
            continue
        # yatay çizgi
        if re.match(r"^(-{3,}|\*{3,})\s*$", s):
            cikti.append("<hr>")
            i += 1
            continue
        # tablo
        if "|" in s and i + 1 < len(satirlar) and re.match(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$", satirlar[i + 1]):
            bas = [c.strip() for c in s.strip().strip("|").split("|")]
            i += 2
            govde = []
            while i < len(satirlar) and "|" in satirlar[i] and satirlar[i].strip():
                govde.append([c.strip() for c in re.split(r"(?<!\\)\|", satirlar[i].strip().strip("|"))])
                i += 1
            th = "".join(f"<th>{satir_ici(c)}</th>" for c in bas)
            tr = "".join("<tr>" + "".join(f"<td>{satir_ici(c.replace(chr(92) + '|', '|'))}</td>" for c in r) + "</tr>" for r in govde)
            cikti.append(f'<div class="tablo"><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>')
            continue
        # alıntı
        if s.startswith(">"):
            ic = []
            while i < len(satirlar) and satirlar[i].startswith(">"):
                ic.append(satirlar[i][1:].lstrip())
                i += 1
            govde, _ = cevir("\n".join(ic))
            cikti.append(f"<blockquote>{govde}</blockquote>")
            continue
        # liste
        m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", s)
        if m:
            sirali = m.group(2)[0].isdigit()
            ogeler = []  # (derinlik, metin)
            while i < len(satirlar):
                m2 = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", satirlar[i])
                if m2:
                    ogeler.append([len(m2.group(1)) // 2, m2.group(3)])
                    i += 1
                elif satirlar[i].startswith("  ") and satirlar[i].strip() and ogeler:
                    ogeler[-1][1] += " " + satirlar[i].strip()
                    i += 1
                else:
                    break
            etiket = "ol" if sirali else "ul"
            html_, derinlik = [f"<{etiket}>"], 0
            for d, t in ogeler:
                d = min(d, 1)
                if d > derinlik:
                    html_.append("<ul>")
                elif d < derinlik:
                    html_.append("</li></ul></li>")
                elif html_[-1] != f"<{etiket}>":
                    html_.append("</li>")
                derinlik = d
                html_.append(f"<li>{satir_ici(t)}")
            html_.append("</li>" + ("</ul></li>" if derinlik else "") + f"</{etiket}>")
            cikti.append("".join(html_))
            continue
        # paragraf
        par = [satirlar[i].strip()]  # en az bir satır tüket (sonsuz döngü olmasın)
        i += 1
        while i < len(satirlar) and satirlar[i].strip() and not re.match(r"^(#{1,4}\s|```|:::|>|\s*([-*]|\d+\.)\s)", satirlar[i]):
            par.append(satirlar[i].strip())
            i += 1
        cikti.append(f"<p>{satir_ici(' '.join(par))}</p>")
    return "\n".join(cikti), basliklar
