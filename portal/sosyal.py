"""Portalın sosyal katmanı: kullanıcı profilleri, sosyal bağlantılar, takip, kısa gönderi akışı, şikayet ve moderasyon.

portal.py tarafından `baglan(portal_modulu)` ile bağlanır; veritabanı ve yardımcıları oradan kullanır.

Gizlilik: profil varsayılan olarak GİZLİDİR. Kullanıcı "herkese açık" yapmadıkça adı, fotoğrafı, bağlantıları ve gönderileri
başkalarına görünmez. E-posta hiçbir sayfada gösterilmez (yalnızca yönetici panelinde).
"""
import re
import time

P = None  # portal modülü

AGLAR = {
    "x": ("X (Twitter)", r"^https://(www\.)?(x|twitter)\.com/[A-Za-z0-9_]{1,15}/?$"),
    "github": ("GitHub", r"^https://github\.com/[A-Za-z0-9\-_.]+(/[A-Za-z0-9\-_.]+)?/?$"),
    "huggingface": ("Hugging Face", r"^https://(huggingface\.co|hf\.co)/[A-Za-z0-9_.\-/]+$"),
    "linkedin": ("LinkedIn", r"^https://([a-z]{2,3}\.)?linkedin\.com/(in|company)/[A-Za-z0-9\-_%]+/?$"),
    "youtube": ("YouTube", r"^https://(www\.)?youtube\.com/(@[A-Za-z0-9_.\-]+|channel/[A-Za-z0-9_\-]+|c/[A-Za-z0-9_.\-]+)/?$"),
    "instagram": ("Instagram", r"^https://(www\.)?instagram\.com/[A-Za-z0-9_.]+/?$"),
    "discord": ("Discord", r"^https://(discord\.gg|discord\.com/invite)/[A-Za-z0-9\-]+$"),
    "web": ("Web sitesi", r"^https://[^\s/]+\.[^\s/]+(/\S*)?$"),
}
MAKS_BAGLANTI = 8
MAKS_AVATAR = 1_000_000
MAKS_BIYO = 280
MAKS_GONDERI = 500
ADI_KURAL = re.compile(r"^[a-z0-9_]{3,20}$")
REZERVE = {"admin", "yonetim", "yonetici", "panel", "akis", "profil", "u", "giris", "kayit", "cikis", "koordinator", "koordinatorler", "modelen",
           "destek", "api", "www", "root", "sistem", "moderator", "avatar", "gorsel", "yardim", "iletisim"}
NEDENLER = {"spam": "Spam / reklam", "taciz": "Taciz ya da nefret", "uygunsuz": "Uygunsuz içerik", "yaniltici": "Yanıltıcı bilgi",
            "kisisel": "Kişisel veri ifşası", "diger": "Diğer"}
MESAJLAR = {"profil": "Profiliniz kaydedildi.", "baglanti": "Bağlantı güncellendi.", "gonderi": "Gönderiniz yayınlandı.",
            "sikayet": "Bildiriminiz alındı; yöneticiler inceleyecek.", "gonderi-silindi": "Gönderi silindi.", "takip": "Güncellendi.",
            "engel": "Engel durumu güncellendi.", "avatar": "Profil fotoğrafı güncellendi."}


def baglan(modul):
    global P
    P = modul
    P.MESAJLAR.update(MESAJLAR)
    P.db_hazirla_ek.append(semayi_kur)


def semayi_kur(c):
    """Sosyal tablolar ve kullanicilar sütunları (idempotent)."""
    c.executescript("""
    CREATE TABLE IF NOT EXISTS avatarlar(
      kullanici_id INTEGER PRIMARY KEY REFERENCES kullanicilar(id) ON DELETE CASCADE,
      tur TEXT NOT NULL, veri BLOB NOT NULL, olusturma INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS baglantilar(
      id INTEGER PRIMARY KEY, kullanici_id INTEGER NOT NULL REFERENCES kullanicilar(id) ON DELETE CASCADE,
      ag TEXT NOT NULL, url TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS takip(
      takip_eden INTEGER NOT NULL REFERENCES kullanicilar(id) ON DELETE CASCADE,
      takip_edilen INTEGER NOT NULL REFERENCES kullanicilar(id) ON DELETE CASCADE,
      zaman INTEGER NOT NULL, PRIMARY KEY(takip_eden, takip_edilen));
    CREATE TABLE IF NOT EXISTS engeller(
      engelleyen INTEGER NOT NULL REFERENCES kullanicilar(id) ON DELETE CASCADE,
      engellenen INTEGER NOT NULL REFERENCES kullanicilar(id) ON DELETE CASCADE,
      zaman INTEGER NOT NULL, PRIMARY KEY(engelleyen, engellenen));
    CREATE TABLE IF NOT EXISTS gonderiler(
      id INTEGER PRIMARY KEY, kullanici_id INTEGER NOT NULL REFERENCES kullanicilar(id) ON DELETE CASCADE,
      metin TEXT NOT NULL, zaman INTEGER NOT NULL, durum TEXT NOT NULL DEFAULT 'yayinda');
    CREATE TABLE IF NOT EXISTS sikayetler(
      id INTEGER PRIMARY KEY, hedef_tur TEXT NOT NULL, hedef_id INTEGER NOT NULL,
      sikayetci_id INTEGER NOT NULL REFERENCES kullanicilar(id) ON DELETE CASCADE,
      neden TEXT NOT NULL, aciklama TEXT NOT NULL DEFAULT '', zaman INTEGER NOT NULL, durum TEXT NOT NULL DEFAULT 'acik',
      UNIQUE(hedef_tur, hedef_id, sikayetci_id));
    """)
    kol = [r["name"] for r in c.execute("PRAGMA table_info(kullanicilar)")]
    for ad, tanim in (("kullanici_adi", "TEXT"), ("biyografi", "TEXT NOT NULL DEFAULT ''"), ("herkese_acik", "INTEGER NOT NULL DEFAULT 0"),
                      ("susturuldu", "INTEGER NOT NULL DEFAULT 0"), ("zorla_gizli", "INTEGER NOT NULL DEFAULT 0")):
        if ad not in kol:
            c.execute(f"ALTER TABLE kullanicilar ADD COLUMN {ad} {tanim}")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_kullanici_adi ON kullanicilar(kullanici_adi) WHERE kullanici_adi IS NOT NULL")
    c.execute("CREATE INDEX IF NOT EXISTS ix_gonderi_zaman ON gonderiler(id DESC)")


# ------------------------------------------------------------------ yardımcılar
def zaman(ts):
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))


def acik_mi(k):
    return bool(k) and k["herkese_acik"] == 1 and k["zorla_gizli"] == 0


def yonetici_mi(h):
    return bool(h.kullanici) and h.kullanici["rol"] == "yonetici"


def engelli_mi(a, b):
    """a ile b arasında herhangi bir yönde engel var mı?"""
    return bool(a and b and P.tek("SELECT 1 FROM engeller WHERE (engelleyen=? AND engellenen=?) OR (engelleyen=? AND engellenen=?)", a, b, b, a))


def gorebilir(h, k):
    if not k:
        return False
    if h.kullanici and (h.kullanici["id"] == k["id"] or yonetici_mi(h)):
        return True
    if not acik_mi(k):
        return False
    return not (h.kullanici and engelli_mi(h.kullanici["id"], k["id"]))


def avatar_html(k, sinif="avatar"):
    if P.tek("SELECT 1 FROM avatarlar WHERE kullanici_id=?", k["id"]):
        return f'<img class="{sinif}" src="/avatar/{k["id"]}" alt="" loading="lazy">'
    bas = (k["ad"] or "?").strip()[:1].upper() or "?"
    return f'<span class="{sinif} bos" aria-hidden="true">{P.e(bas)}</span>'


def ad_baglantisi(k):
    if k["kullanici_adi"]:
        return f'<a href="/u/{P.e(k["kullanici_adi"])}">{P.e(k["ad"])}</a> <small>@{P.e(k["kullanici_adi"])}</small>'
    return P.e(k["ad"])


def baglanti_rozetleri(kid):
    satirlar = P.sorgu("SELECT ag, url FROM baglantilar WHERE kullanici_id=? ORDER BY id", kid)
    if not satirlar:
        return ""
    return '<p class="rozetler">' + "".join(
        f'<a class="rozet" href="{P.e(r["url"])}" rel="noopener nofollow noreferrer ugc" target="_blank">{P.e(AGLAR[r["ag"]][0])}</a>' for r in satirlar if r["ag"] in AGLAR) + "</p>"


def baglanti_dogrula(ag, url):
    url = url.strip()
    if ag not in AGLAR:
        return "Geçersiz ağ."
    if len(url) > 200 or not re.match(AGLAR[ag][1], url):
        return f"{AGLAR[ag][0]} için geçerli bir https bağlantısı girin."
    return ""


def metin_html(m):
    return P.e(m).replace("\n", "<br>")


def gonderi_html(h, g, mod=False):
    """Tek gönderi kartı. g: gönderi + yazar sütunları."""
    k = {"id": g["kid"], "ad": g["ad"], "kullanici_adi": g["kullanici_adi"]}
    eylem = ""
    if h.kullanici:
        if h.kullanici["id"] == g["kid"]:
            eylem = ('<form method="post" action="/gonderi-sil" class="satir">' + P.csrf_alani(h.csrf) +
                     f'<input type="hidden" name="id" value="{g["id"]}"><button class="btn ghost sm" type="submit">Sil</button></form>')
        else:
            sec = "".join(f'<option value="{a}">{P.e(b)}</option>' for a, b in NEDENLER.items())
            eylem = ('<details class="sikayet"><summary>Bildir</summary><form method="post" action="/sikayet" class="kform">' + P.csrf_alani(h.csrf) +
                     f'<input type="hidden" name="tur" value="gonderi"><input type="hidden" name="id" value="{g["id"]}">'
                     f'<label>Neden<select name="neden">{sec}</select></label>'
                     '<label>Açıklama (isteğe bağlı)<input name="aciklama" maxlength="300"></label>'
                     '<button class="btn sm" type="submit">Bildir</button></form></details>')
        if yonetici_mi(h):
            eylem += ('<form method="post" action="/yonetim/gonderi-gizle" class="satir">' + P.csrf_alani(h.csrf) +
                      f'<input type="hidden" name="id" value="{g["id"]}"><button class="btn ghost sm" type="submit">Yönetici: gizle</button></form>')
    return (f'<article class="gonderi"><div class="gonderi-ust">{avatar_html(k, "avatar kucuk")}<div><b>{ad_baglantisi(k)}</b>'
            f'<br><small>{zaman(g["zaman"])}</small></div></div><p>{metin_html(g["metin"])}</p>{eylem}</article>')


# ------------------------------------------------------------------ GET
def get(h, yol, q):
    """True: işlendi."""
    if yol.startswith("/u/"):
        profil_sayfasi(h, yol[3:], q)
    elif yol.startswith("/avatar/"):
        avatar_ver(h, yol[8:])
    elif yol in ("/akis", "/akis.html", "/en/akis.html"):
        akis(h, q)
    elif yol == "/profil":
        if h._gerekli():
            profil_duzenle(h, q)
    elif yol == "/yonetim/moderasyon":
        if h._gerekli(True):
            moderasyon(h, q)
    else:
        return False
    return True


def avatar_ver(h, kimlik):
    k = P.tek("SELECT * FROM kullanicilar WHERE id=?", kimlik) if kimlik.isdigit() else None
    a = P.tek("SELECT tur, veri FROM avatarlar WHERE kullanici_id=?", kimlik) if k else None
    if not a or not gorebilir(h, k):
        return h._statik("/__yok__.html")
    acik = acik_mi(k)
    h._gonder(200, bytes(a["veri"]), P.gorsel.TURLER[a["tur"]],
              ek={"Cache-Control": "public, max-age=600" if acik else "private, no-store", "Content-Disposition": "inline"})


def profil_sayfasi(h, adi, q):
    k = P.tek("SELECT * FROM kullanicilar WHERE kullanici_adi=?", adi.lower()) if ADI_KURAL.match(adi.lower()) else None
    if not gorebilir(h, k):
        return h._statik("/__yok__.html")
    ben = h.kullanici
    sahibi = bool(ben) and ben["id"] == k["id"]
    n_gonderi = P.tek("SELECT COUNT(*) n FROM gonderiler WHERE kullanici_id=? AND durum='yayinda'", k["id"])["n"]
    n_takipci = P.tek("SELECT COUNT(*) n FROM takip WHERE takip_edilen=?", k["id"])["n"]
    n_takip = P.tek("SELECT COUNT(*) n FROM takip WHERE takip_eden=?", k["id"])["n"]
    uyari = ""
    if not acik_mi(k):
        uyari = ('<p class="note">Bu profil <b>gizli</b>; yalnızca siz ve yöneticiler görebilir. Herkese açmak için <a href="/profil">profil ayarlarına</a> gidin.</p>'
                 if sahibi else '<p class="note">Bu profil gizli (yönetici görünümü).</p>')
    eylemler = ""
    if ben and not sahibi:
        takipte = bool(P.tek("SELECT 1 FROM takip WHERE takip_eden=? AND takip_edilen=?", ben["id"], k["id"]))
        eylemler = ('<div class="satir"><form method="post" action="/takip">' + P.csrf_alani(h.csrf) +
                    f'<input type="hidden" name="hedef" value="{k["id"]}"><input type="hidden" name="islem" value="{"birak" if takipte else "ekle"}">'
                    f'<button class="btn{" ghost" if takipte else " accent"}" type="submit">{"Takibi bırak" if takipte else "Takip et"}</button></form>'
                    '<form method="post" action="/engel">' + P.csrf_alani(h.csrf) +
                    f'<input type="hidden" name="hedef" value="{k["id"]}"><input type="hidden" name="islem" value="ekle">'
                    '<button class="btn ghost sm" type="submit">Engelle</button></form>'
                    '<details class="sikayet"><summary>Profili bildir</summary><form method="post" action="/sikayet" class="kform">' + P.csrf_alani(h.csrf) +
                    f'<input type="hidden" name="tur" value="profil"><input type="hidden" name="id" value="{k["id"]}">'
                    '<label>Neden<select name="neden">' + "".join(f'<option value="{a}">{P.e(b)}</option>' for a, b in NEDENLER.items()) + '</select></label>'
                    '<label>Açıklama (isteğe bağlı)<input name="aciklama" maxlength="300"></label><button class="btn sm" type="submit">Bildir</button></form></details></div>')
    elif sahibi:
        eylemler = '<p><a class="btn" href="/profil">Profili düzenle</a></p>'
    gonderiler = P.sorgu("SELECT g.id, g.metin, g.zaman, k.id AS kid, k.ad, k.kullanici_adi FROM gonderiler g JOIN kullanicilar k ON k.id=g.kullanici_id "
                         "WHERE g.kullanici_id=? AND g.durum='yayinda' ORDER BY g.id DESC LIMIT 30", k["id"])
    akis_html = "".join(gonderi_html(h, g) for g in gonderiler) or "<p>Henüz gönderi yok.</p>"
    kunye = f'<p>{P.e(k["biyografi"])}</p>' if k["biyografi"] else ""
    ust = (f'<div class="profil">{avatar_html(k, "avatar buyuk")}<div><h1>{P.e(k["ad"])}</h1><p class="ad">@{P.e(k["kullanici_adi"] or "")}</p></div></div>')
    sayilar = f'<p class="sayilar"><b>{n_gonderi}</b> gönderi · <b>{n_takipci}</b> takipçi · <b>{n_takip}</b> takip</p>'
    basvuru = P.tek("SELECT slug, ad FROM basvurular WHERE kullanici_id=? AND durum='onaylandi'", k["id"])
    kord = f'<p>Koordinatör: <a href="/koordinator/{P.e(basvuru["slug"])}">{P.e(basvuru["ad"])}</a></p>' if basvuru and acik_mi(k) else ""
    h._html(200, k["ad"], '<div class="phead"><p class="label">Profil</p></div>' + P._mesaj_html(h, q) + uyari + ust + kunye + baglanti_rozetleri(k["id"]) + kord + sayilar + eylemler
            + "<h2>Gönderiler</h2>" + akis_html, f"{k['ad']} (@{k['kullanici_adi']}) · Modelen topluluğu")


def akis(h, q):
    ben = h.kullanici
    takipte = (q.get("takip") or [""])[0] == "1" and bool(ben)
    once = (q.get("once") or [""])[0]
    kosul, arg = ["g.durum='yayinda'", "k.herkese_acik=1", "k.zorla_gizli=0"], []
    if ben:
        kosul += ["k.id NOT IN (SELECT engellenen FROM engeller WHERE engelleyen=?)", "k.id NOT IN (SELECT engelleyen FROM engeller WHERE engellenen=?)"]
        arg += [ben["id"], ben["id"]]
    if takipte:
        kosul.append("k.id IN (SELECT takip_edilen FROM takip WHERE takip_eden=?)")
        arg.append(ben["id"])
    if once.isdigit():
        kosul.append("g.id < ?")
        arg.append(int(once))
    satirlar = P.sorgu("SELECT g.id, g.metin, g.zaman, k.id AS kid, k.ad, k.kullanici_adi FROM gonderiler g JOIN kullanicilar k ON k.id=g.kullanici_id "
                       "WHERE " + " AND ".join(kosul) + " ORDER BY g.id DESC LIMIT 31", *arg)
    daha = len(satirlar) > 30
    satirlar = satirlar[:30]
    yaz = ""
    if ben:
        if ben["susturuldu"]:
            yaz = '<p class="note">Gönderi paylaşımınız yöneticiler tarafından kısıtlandı.</p>'
        elif acik_mi(ben):
            yaz = ('<form class="kform" method="post" action="/gonderi">' + P.csrf_alani(h.csrf) +
                   f'<label>Topluluğa bir şey yazın ({MAKS_GONDERI} karakter; düz metin)<textarea name="metin" maxlength="{MAKS_GONDERI}" rows="3" required></textarea></label>'
                   '<p class="note">Paylaşmadan önce <a href="/topluluk-kurallari.html">topluluk kurallarını</a> okuyun. Gönderiniz herkese açık profilinizde ve akışta görünür.</p>'
                   '<button class="btn accent" type="submit">Paylaş</button></form>')
        else:
            yaz = '<p class="note">Gönderi paylaşmak için profilinizi herkese açık yapın: <a href="/profil">profil ayarları</a>.</p>'
    sekme = ('<p><a class="btn' + ("" if not takipte else " ghost") + '" href="/akis">Herkes</a> ' +
             (('<a class="btn' + (" ghost" if not takipte else "") + '" href="/akis?takip=1">Takip ettiklerim</a>') if ben else '<a class="btn ghost" href="/giris">Takip için giriş yapın</a>') + "</p>")
    liste = "".join(gonderi_html(h, g) for g in satirlar) or ('<p class="note">Henüz gönderi yok.</p>' if not takipte else
                                                              '<p class="note">Takip ettiklerinizden gönderi yok. Önce birkaç kişiyi takip edin.</p>')
    sonraki = (f'<p><a class="btn ghost" href="/akis?{"takip=1&" if takipte else ""}once={satirlar[-1]["id"]}">Daha eski gönderiler</a></p>' if daha else "")
    h._html(200, "Akış", P.pages.phead("Topluluk", "Akış", "Modelen topluluğunun kısa güncellemeleri. Yalnızca profilini herkese açan üyelerin gönderileri görünür.")
            + P._mesaj_html(h, q) + sekme + yaz + '<div class="akis">' + liste + "</div>" + sonraki, "Modelen topluluk akışı")


def profil_duzenle(h, q, hata="", form=None):
    k = h.kullanici
    f = form or dict(k)
    baglantilar = P.sorgu("SELECT * FROM baglantilar WHERE kullanici_id=? ORDER BY id", k["id"])
    var_ag = {b["ag"] for b in baglantilar}
    ag_sec = "".join(f'<option value="{a}">{P.e(b[0])}</option>' for a, b in AGLAR.items() if a not in var_ag or a == "web")
    avatar = (f'<div class="satir">{avatar_html(k, "avatar buyuk")}<form method="post" action="/avatar-sil">' + P.csrf_alani(h.csrf) +
              '<button class="btn ghost sm" type="submit">Fotoğrafı kaldır</button></form></div>') if P.tek("SELECT 1 FROM avatarlar WHERE kullanici_id=?", k["id"]) else ""
    liste = "".join(f'<li>{P.e(AGLAR[b["ag"]][0])}: {P.e(b["url"])} <form method="post" action="/baglanti-sil" class="satir">{P.csrf_alani(h.csrf)}'
                    f'<input type="hidden" name="id" value="{b["id"]}"><button class="btn ghost sm" type="submit">Sil</button></form></li>' for b in baglantilar if b["ag"] in AGLAR)
    govde = (P.pages.phead("Profil", "Profilini düzenle", "Profilin varsayılan olarak gizlidir; \"herkese açık\" yapana kadar kimse göremez.") + P._mesaj_html(h, q)
             + (f'<p class="note">{P.e(hata)}</p>' if hata else "") + avatar
             + '<form class="kform" method="post" action="/profil" enctype="multipart/form-data">' + P.csrf_alani(h.csrf)
             + P.alan("ad", "Görünen ad (gerçek adınız olmak zorunda değil)", f.get("ad", ""), ek='maxlength="60" required')
             + P.alan("kullanici_adi", "Kullanıcı adı (3-20 karakter: küçük harf, rakam, alt çizgi)", f.get("kullanici_adi") or "", ek='maxlength="20" pattern="[a-z0-9_]{3,20}"')
             + f'<label>Hakkında (en çok {MAKS_BIYO} karakter)<textarea name="biyografi" maxlength="{MAKS_BIYO}" rows="3">{P.e(f.get("biyografi") or "")}</textarea></label>'
             + f'<label>Profil fotoğrafı (PNG/JPEG/WebP, en çok 1 MB; konum bilgisi silinir)<input name="avatar" type="file" accept="image/png,image/jpeg,image/webp"></label>'
             + f'<label class="chk"><input type="checkbox" name="herkese_acik" value="1" {"checked" if f.get("herkese_acik") else ""}> <span>Profilimi <b>herkese açık</b> yap: adım, kullanıcı adım, fotoğrafım, hakkımda yazım, bağlantılarım ve gönderilerim herkes tarafından görülebilir. E-posta adresim hiçbir zaman gösterilmez.</span></label>'
             + '<button class="btn accent" type="submit">Kaydet</button></form>'
             + (f'<p><a href="/u/{P.e(k["kullanici_adi"])}">Profilime bak</a></p>' if k["kullanici_adi"] else "")
             + "<h2>Sosyal bağlantılar</h2>" + (f"<ul>{liste}</ul>" if liste else "<p>Henüz bağlantı eklemediniz.</p>")
             + (f'<form class="kform" method="post" action="/baglanti-ekle">{P.csrf_alani(h.csrf)}<label>Ağ<select name="ag">{ag_sec}</select></label>'
                '<label>Bağlantı (https://…)<input name="url" type="url" maxlength="200" required placeholder="https://"></label>'
                '<button class="btn" type="submit">Ekle</button></form>' if len(baglantilar) < MAKS_BAGLANTI else "")
             + "<h2>Engellediklerim</h2>" + engelliler_html(h)
             + '<p><a class="btn ghost" href="/panel">Panele dön</a></p>')
    h._html(200, "Profil", govde)


def engelliler_html(h):
    satirlar = P.sorgu("SELECT k.id, k.ad, k.kullanici_adi FROM engeller e JOIN kullanicilar k ON k.id=e.engellenen WHERE e.engelleyen=?", h.kullanici["id"])
    if not satirlar:
        return "<p>Kimseyi engellemediniz.</p>"
    return "<ul>" + "".join(f'<li>{P.e(r["ad"])} <form method="post" action="/engel" class="satir">{P.csrf_alani(h.csrf)}<input type="hidden" name="hedef" value="{r["id"]}">'
                            f'<input type="hidden" name="islem" value="kaldir"><button class="btn ghost sm" type="submit">Engeli kaldır</button></form></li>' for r in satirlar) + "</ul>"


# ------------------------------------------------------------------ POST
def post(h, yol, f):
    """True: işlendi (giriş yapmış kullanıcı için)."""
    if yol == "/profil":
        profil_kaydet(h, f)
    elif yol == "/avatar-sil":
        P.yurut("DELETE FROM avatarlar WHERE kullanici_id=?", h.kullanici["id"])
        h._yonlendir("/profil?m=avatar")
    elif yol == "/baglanti-ekle":
        baglanti_ekle(h, f)
    elif yol == "/baglanti-sil":
        if f.get("id", "").isdigit():
            P.yurut("DELETE FROM baglantilar WHERE id=? AND kullanici_id=?", int(f["id"]), h.kullanici["id"])
        h._yonlendir("/profil?m=baglanti")
    elif yol == "/gonderi":
        gonderi_ekle(h, f)
    elif yol == "/gonderi-sil":
        if f.get("id", "").isdigit():
            P.yurut("DELETE FROM gonderiler WHERE id=? AND kullanici_id=?", int(f["id"]), h.kullanici["id"])
        h._yonlendir("/akis?m=gonderi-silindi")
    elif yol == "/takip":
        takip(h, f)
    elif yol == "/engel":
        engel(h, f)
    elif yol == "/sikayet":
        sikayet(h, f)
    elif yol == "/yonetim/gonderi-gizle":
        if not yonetici_mi(h):
            return h._gerekli(True) or True
        if f.get("id", "").isdigit():
            P.yurut("UPDATE gonderiler SET durum='gizli' WHERE id=?", int(f["id"]))
        h._yonlendir("/akis?m=gonderi-silindi")
    elif yol == "/yonetim/moderasyon-karar":
        if not yonetici_mi(h):
            return h._gerekli(True) or True
        mod_karar(h, f)
    elif yol == "/yonetim/kullanici-kisit":
        if not yonetici_mi(h):
            return h._gerekli(True) or True
        kullanici_kisit(h, f)
    else:
        return False
    return True


def profil_kaydet(h, f):
    k = h.kullanici
    ad, adi = f.get("ad", "").strip(), f.get("kullanici_adi", "").strip().lower()
    biyo = f.get("biyografi", "").strip().replace("\r\n", "\n")
    acik = 1 if f.get("herkese_acik") == "1" else 0
    form = dict(f, herkese_acik=acik)
    hata = ("Görünen ad 2-60 karakter olmalı." if not 2 <= len(ad) <= 60 else
            f"Hakkında en çok {MAKS_BIYO} karakter olabilir." if len(biyo) > MAKS_BIYO else
            "Kullanıcı adı 3-20 karakter olmalı: küçük harf, rakam, alt çizgi." if adi and not ADI_KURAL.match(adi) else
            "Bu kullanıcı adı ayrılmış." if adi in REZERVE else
            "Herkese açık profil için kullanıcı adı gerekli." if acik and not adi else "")
    if not hata and adi:
        baska = P.tek("SELECT id FROM kullanicilar WHERE kullanici_adi=? AND id<>?", adi, k["id"])
        hata = "Bu kullanıcı adı alınmış." if baska else ""
    if not hata and acik and k["zorla_gizli"]:
        hata = "Profiliniz yöneticiler tarafından gizlendi; herkese açılamaz."
    yeni_avatar = None
    if not hata:
        dosyalar = [v for a, v in h.dosyalar if a == "avatar"]
        if dosyalar:
            if len(dosyalar[0]) > MAKS_AVATAR:
                hata = "Profil fotoğrafı 1 MB'tan büyük."
            else:
                try:
                    yeni_avatar = P.gorsel.temizle(dosyalar[0])
                except P.gorsel.GorselHatasi as ex:
                    hata = f"Profil fotoğrafı: {ex}"
    if hata:
        return profil_duzenle(h, {}, hata, form)
    P.yurut("UPDATE kullanicilar SET ad=?, kullanici_adi=?, biyografi=?, herkese_acik=? WHERE id=?", ad, adi or None, biyo, acik, k["id"])
    if yeni_avatar:
        tur, temiz, _, _ = yeni_avatar
        P.yurut("INSERT INTO avatarlar(kullanici_id,tur,veri,olusturma) VALUES(?,?,?,?) ON CONFLICT(kullanici_id) DO UPDATE SET tur=excluded.tur, veri=excluded.veri, olusturma=excluded.olusturma",
                k["id"], tur, temiz, int(time.time()))
    h._yonlendir("/profil?m=profil")


def baglanti_ekle(h, f):
    k, ag, url = h.kullanici, f.get("ag", ""), f.get("url", "").strip()
    hata = baglanti_dogrula(ag, url)
    mevcut = P.sorgu("SELECT ag FROM baglantilar WHERE kullanici_id=?", k["id"])
    if not hata and len(mevcut) >= MAKS_BAGLANTI:
        hata = f"En çok {MAKS_BAGLANTI} bağlantı eklenebilir."
    if not hata and ag != "web" and any(m["ag"] == ag for m in mevcut):
        hata = f"{AGLAR[ag][0]} için zaten bir bağlantınız var; önce onu silin."
    if not hata and ag == "web" and sum(1 for m in mevcut if m["ag"] == "web") >= 2:
        hata = "En çok 2 web sitesi eklenebilir."
    if hata:
        return profil_duzenle(h, {}, hata)
    P.yurut("INSERT INTO baglantilar(kullanici_id,ag,url) VALUES(?,?,?)", k["id"], ag, url)
    h._yonlendir("/profil?m=baglanti")


def gonderi_ekle(h, f):
    k = h.kullanici
    metin = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", f.get("metin", "")).replace("\r\n", "\n").strip()
    metin = re.sub(r"\n{3,}", "\n\n", metin)
    hata = ("Profiliniz gizli; önce herkese açın." if not acik_mi(k) else
            "Gönderi paylaşımınız kısıtlandı." if k["susturuldu"] else
            "Gönderi boş olamaz." if not metin else
            f"Gönderi en çok {MAKS_GONDERI} karakter olabilir." if len(metin) > MAKS_GONDERI else "")
    if not hata and (P.hiz_asildi(("gonderi", k["id"]), 10, 3600) or P.hiz_asildi(("gonderi-gun", k["id"]), 40, 86400)):
        hata = "Çok sık paylaşım yapıyorsunuz; biraz bekleyin."
    if not hata:
        son = P.tek("SELECT metin FROM gonderiler WHERE kullanici_id=? ORDER BY id DESC LIMIT 1", k["id"])
        if son and son["metin"] == metin:
            hata = "Aynı gönderiyi tekrar paylaşamazsınız."
    if hata:
        return h._html(400, "Gönderi", P.pages.phead("Gönderi", "Paylaşılamadı.", hata) + '<p><a class="btn" href="/akis">Akışa dön</a></p>')
    P.yurut("INSERT INTO gonderiler(kullanici_id,metin,zaman) VALUES(?,?,?)", k["id"], metin, int(time.time()))
    h._yonlendir("/akis?m=gonderi")


def hedef_kullanici(h, f):
    if not f.get("hedef", "").isdigit():
        return None
    k = P.tek("SELECT * FROM kullanicilar WHERE id=?", int(f["hedef"]))
    return k if k and k["id"] != h.kullanici["id"] else None


def takip(h, f):
    hedef, ben = hedef_kullanici(h, f), h.kullanici["id"]
    if not hedef:
        return h._yonlendir("/akis")
    if f.get("islem") == "ekle":
        if acik_mi(hedef) and not engelli_mi(ben, hedef["id"]) and not P.hiz_asildi(("takip", ben), 60, 3600):
            P.yurut("INSERT OR IGNORE INTO takip(takip_eden,takip_edilen,zaman) VALUES(?,?,?)", ben, hedef["id"], int(time.time()))
    else:
        P.yurut("DELETE FROM takip WHERE takip_eden=? AND takip_edilen=?", ben, hedef["id"])
    h._yonlendir(f"/u/{hedef['kullanici_adi']}?m=takip" if hedef["kullanici_adi"] else "/akis")


def engel(h, f):
    hedef, ben = hedef_kullanici(h, f), h.kullanici["id"]
    if not hedef:
        return h._yonlendir("/profil")
    if f.get("islem") == "ekle":
        P.yurut("INSERT OR IGNORE INTO engeller(engelleyen,engellenen,zaman) VALUES(?,?,?)", ben, hedef["id"], int(time.time()))
        P.yurut("DELETE FROM takip WHERE (takip_eden=? AND takip_edilen=?) OR (takip_eden=? AND takip_edilen=?)", ben, hedef["id"], hedef["id"], ben)
        return h._yonlendir("/akis?m=engel")
    P.yurut("DELETE FROM engeller WHERE engelleyen=? AND engellenen=?", ben, hedef["id"])
    h._yonlendir("/profil?m=engel")


def sikayet(h, f):
    tur, kimlik, neden = f.get("tur", ""), f.get("id", ""), f.get("neden", "")
    if tur not in ("gonderi", "profil") or not kimlik.isdigit() or neden not in NEDENLER or P.hiz_asildi(("sikayet", h.kullanici["id"]), 10, 3600):
        return h._html(400, "Bildirim", P.pages.phead("Bildirim", "Gönderilemedi.", "Geçersiz istek ya da çok sık bildirim."))
    kid = int(kimlik)
    sahip = (P.tek("SELECT kullanici_id AS s FROM gonderiler WHERE id=?", kid) if tur == "gonderi" else P.tek("SELECT id AS s FROM kullanicilar WHERE id=?", kid))
    if not sahip or sahip["s"] == h.kullanici["id"]:
        return h._yonlendir("/akis")
    P.yurut("INSERT OR IGNORE INTO sikayetler(hedef_tur,hedef_id,sikayetci_id,neden,aciklama,zaman) VALUES(?,?,?,?,?,?)",
            tur, kid, h.kullanici["id"], neden, f.get("aciklama", "").strip()[:300], int(time.time()))
    h._yonlendir("/akis?m=sikayet")


# ------------------------------------------------------------------ moderasyon
def moderasyon(h, q):
    acik = P.sorgu("SELECT * FROM sikayetler WHERE durum='acik' ORDER BY id")
    kartlar = ""
    for s in acik:
        if s["hedef_tur"] == "gonderi":
            g = P.tek("SELECT g.id, g.metin, g.durum, k.id AS kid, k.ad, k.kullanici_adi, k.eposta FROM gonderiler g JOIN kullanicilar k ON k.id=g.kullanici_id WHERE g.id=?", s["hedef_id"])
            if not g:
                P.yurut("UPDATE sikayetler SET durum='islendi' WHERE id=?", s["id"])
                continue
            ic = f'<p><b>Gönderi</b> ({P.e(g["durum"])}) — {P.e(g["ad"])} @{P.e(g["kullanici_adi"] or "-")} · {P.e(g["eposta"])}</p><blockquote>{metin_html(g["metin"])}</blockquote>'
        else:
            g = P.tek("SELECT id AS kid, ad, kullanici_adi, eposta, biyografi FROM kullanicilar WHERE id=?", s["hedef_id"])
            if not g:
                P.yurut("UPDATE sikayetler SET durum='islendi' WHERE id=?", s["id"])
                continue
            ic = f'<p><b>Profil</b> — {P.e(g["ad"])} @{P.e(g["kullanici_adi"] or "-")} · {P.e(g["eposta"])}</p><blockquote>{metin_html(g["biyografi"] or "—")}</blockquote>'
        butonlar = "".join(f'<button class="btn{"" if k_ == "gizle" else " ghost"} sm" name="karar" value="{k_}" type="submit">{P.e(a)}</button> '
                           for k_, a in ([("gizle", "Gönderiyi gizle"), ("sustur", "Gizle + yazarı sustur")] if s["hedef_tur"] == "gonderi" else [("profil-gizle", "Profili gizle")])
                           + [("reddet", "Bildirimi reddet")])
        kartlar += (f'<div class="kart">{ic}<p><small>Neden: {P.e(NEDENLER.get(s["neden"], s["neden"]))}'
                    f'{" · " + P.e(s["aciklama"]) if s["aciklama"] else ""} · {zaman(s["zaman"])}</small></p>'
                    f'<form method="post" action="/yonetim/moderasyon-karar">{P.csrf_alani(h.csrf)}<input type="hidden" name="id" value="{s["id"]}">{butonlar}</form></div>')
    kisitli = P.sorgu("SELECT id, ad, kullanici_adi, eposta, susturuldu, zorla_gizli FROM kullanicilar WHERE susturuldu=1 OR zorla_gizli=1")
    kis = "".join(f'<li>{P.e(r["ad"])} @{P.e(r["kullanici_adi"] or "-")} · {P.e(r["eposta"])} — {"susturuldu " if r["susturuldu"] else ""}{"profil gizli" if r["zorla_gizli"] else ""} '
                  f'<form method="post" action="/yonetim/kullanici-kisit" class="satir">{P.csrf_alani(h.csrf)}<input type="hidden" name="id" value="{r["id"]}">'
                  '<button class="btn ghost sm" type="submit">Kısıtlamaları kaldır</button></form></li>' for r in kisitli)
    h._html(200, "Moderasyon", P.pages.phead("Moderasyon", "Açık bildirimler", f"{len(acik)} açık bildirim") + P._mesaj_html(h, q)
            + (kartlar or '<p class="note">Açık bildirim yok.</p>') + "<h2>Kısıtlı kullanıcılar</h2>" + (f"<ul>{kis}</ul>" if kis else "<p>Yok.</p>")
            + '<p><a class="btn ghost" href="/yonetim">Başvurulara dön</a></p>')


def mod_karar(h, f):
    kimlik, karar = f.get("id", ""), f.get("karar", "")
    s = P.tek("SELECT * FROM sikayetler WHERE id=?", int(kimlik)) if kimlik.isdigit() else None
    if not s or karar not in ("gizle", "sustur", "profil-gizle", "reddet"):
        return h._yonlendir("/yonetim/moderasyon")
    if karar == "reddet":
        P.yurut("UPDATE sikayetler SET durum='reddedildi' WHERE id=?", s["id"])
    elif s["hedef_tur"] == "gonderi":
        g = P.tek("SELECT kullanici_id FROM gonderiler WHERE id=?", s["hedef_id"])
        P.yurut("UPDATE gonderiler SET durum='gizli' WHERE id=?", s["hedef_id"])
        if karar == "sustur" and g:
            P.yurut("UPDATE kullanicilar SET susturuldu=1 WHERE id=?", g["kullanici_id"])
        P.yurut("UPDATE sikayetler SET durum='islendi' WHERE hedef_tur='gonderi' AND hedef_id=?", s["hedef_id"])
    else:
        P.yurut("UPDATE kullanicilar SET zorla_gizli=1 WHERE id=?", s["hedef_id"])
        P.yurut("UPDATE sikayetler SET durum='islendi' WHERE hedef_tur='profil' AND hedef_id=?", s["hedef_id"])
    h._yonlendir("/yonetim/moderasyon?m=karar")


def kullanici_kisit(h, f):
    if f.get("id", "").isdigit():
        P.yurut("UPDATE kullanicilar SET susturuldu=0, zorla_gizli=0 WHERE id=?", int(f["id"]))
    h._yonlendir("/yonetim/moderasyon?m=karar")
