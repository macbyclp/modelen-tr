"""Yüklenen görselleri doğrular ve temizler (yalnızca standart kütüphane).

- Yalnızca PNG, JPEG ve WebP kabul edilir (SVG/HTML/GIF reddedilir: betik/XSS riski).
- Tür, dosya adına ya da istemcinin bildirdiği türe değil, dosyanın ilk baytlarına göre belirlenir.
- Üst veriler silinir: JPEG EXIF/XMP/IPTC/yorum, PNG tEXt/iTXt/zTXt/eXIf/tIME, WebP EXIF/XMP.
  (Telefon fotoğraflarındaki konum bilgisi sızmasın diye.)
- Boyut sınırı: kenar başına en çok 6000 px.

Görüntü yeniden kodlanmaz; yalnızca üst veri parçaları çıkarılır, piksel verisine dokunulmaz.
"""
import struct

MAKS_KENAR = 6000
IZINLI_PNG = {b"IHDR", b"PLTE", b"IDAT", b"IEND", b"tRNS", b"gAMA", b"cHRM", b"sRGB", b"iCCP", b"pHYs", b"sBIT", b"bKGD", b"acTL", b"fcTL", b"fdAT"}
TURLER = {"png": "image/png", "jpeg": "image/jpeg", "webp": "image/webp"}


class GorselHatasi(ValueError):
    pass


def temizle(veri):
    """(tur, temiz_bayt, genislik, yukseklik) döndürür; geçersizse GorselHatasi."""
    if veri[:8] == b"\x89PNG\r\n\x1a\n":
        tur, temiz, w, h = (("png",) + _png(veri))
    elif veri[:3] == b"\xff\xd8\xff":
        tur, temiz, w, h = (("jpeg",) + _jpeg(veri))
    elif veri[:4] == b"RIFF" and veri[8:12] == b"WEBP":
        tur, temiz, w, h = (("webp",) + _webp(veri))
    else:
        raise GorselHatasi("Yalnızca PNG, JPEG ya da WebP yüklenebilir.")
    if not (1 <= w <= MAKS_KENAR and 1 <= h <= MAKS_KENAR):
        raise GorselHatasi(f"Görsel en çok {MAKS_KENAR}x{MAKS_KENAR} piksel olabilir.")
    return tur, temiz, w, h


def _png(v):
    cikti, i, w, h, iend = [v[:8]], 8, 0, 0, False
    while i + 8 <= len(v):
        n, tip = struct.unpack(">I4s", v[i:i + 8])
        son = i + 12 + n
        if n > len(v) or son > len(v):
            raise GorselHatasi("PNG dosyası bozuk.")
        if tip == b"IHDR":
            if n != 13:
                raise GorselHatasi("PNG dosyası bozuk.")
            w, h = struct.unpack(">II", v[i + 8:i + 16])
        if tip in IZINLI_PNG:
            cikti.append(v[i:son])
        i = son
        if tip == b"IEND":
            iend = True
            break
    if not iend or not w:
        raise GorselHatasi("PNG dosyası eksik ya da bozuk.")
    return b"".join(cikti), w, h


def _jpeg(v):
    cikti, i, w, h = [v[:2]], 2, 0, 0
    while i + 4 <= len(v):
        if v[i] != 0xFF:
            raise GorselHatasi("JPEG dosyası bozuk.")
        m = v[i + 1]
        if m == 0xFF:  # dolgu baytı
            i += 1
            continue
        if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
            cikti.append(v[i:i + 2])
            i += 2
            continue
        if m == 0xD9:
            cikti.append(v[i:i + 2])
            break
        n = struct.unpack(">H", v[i + 2:i + 4])[0]
        if n < 2 or i + 2 + n > len(v):
            raise GorselHatasi("JPEG dosyası bozuk.")
        if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF) and n >= 7:
            h, w = struct.unpack(">HH", v[i + 5:i + 9])
        if m == 0xDA:  # taranan veri: dosyanın kalanı olduğu gibi
            cikti.append(v[i:])
            break
        # yorum (FE) ve APP1..APP13 (Exif/XMP/IPTC...) atılır; APP0 (JFIF), APP2 (ICC), APP14 (Adobe) ve diğerleri kalır
        if not (m == 0xFE or 0xE1 <= m <= 0xED and m != 0xE2):
            cikti.append(v[i:i + 2 + n])
        i += 2 + n
    if not w or not h:
        raise GorselHatasi("JPEG boyutu okunamadı.")
    return b"".join(cikti), w, h


def _webp(v):
    toplam = struct.unpack("<I", v[4:8])[0] + 8
    if toplam > len(v) or toplam < 20:
        raise GorselHatasi("WebP dosyası bozuk.")
    govde, i, w, h = [], 12, 0, 0
    while i + 8 <= toplam:
        tip, n = v[i:i + 4], struct.unpack("<I", v[i + 4:i + 8])[0]
        veri = v[i + 8:i + 8 + n]
        if len(veri) < n:
            raise GorselHatasi("WebP dosyası bozuk.")
        tam = v[i:i + 8 + n + (n & 1)]
        if tip == b"VP8X" and n >= 10:
            w, h = (int.from_bytes(veri[4:7], "little") + 1, int.from_bytes(veri[7:10], "little") + 1)
            tam = tam[:8] + bytes([veri[0] & ~0x0C & 0xFF]) + tam[9:]  # EXIF (0x08) ve XMP (0x04) bayraklarını temizle
        elif tip == b"VP8L" and n >= 5 and veri[0] == 0x2F and not w:
            b = int.from_bytes(veri[1:5], "little")
            w, h = (b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1
        elif tip == b"VP8 " and n >= 10 and veri[3:6] == b"\x9d\x01\x2a" and not w:
            w, h = struct.unpack("<HH", veri[6:10])
            w, h = w & 0x3FFF, h & 0x3FFF
        if tip not in (b"EXIF", b"XMP "):
            govde.append(tam)
        i += 8 + n + (n & 1)
    if not w or not h:
        raise GorselHatasi("WebP boyutu okunamadı.")
    icerik = b"WEBP" + b"".join(govde)
    return b"RIFF" + struct.pack("<I", len(icerik)) + icerik, w, h
