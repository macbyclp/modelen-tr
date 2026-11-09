#!/usr/bin/env bash
# koordinator-kur.sh için uçtan uca test (--sistemsiz, CPU): CI'da temiz Ubuntu ve Arch makinelerinde koşar.
# Kullanım (depo kökünden): bash tools/koordinator_kurulum_testi.sh [hedef-klasör]
set -euo pipefail
cd "$(dirname "$0")/.."
H="${1:-${RUNNER_TEMP:-/tmp}/koord-test}"
PORT=8761
rm -rf "$H"
BIN_DIR="${HOME}/.local/bin"; [ "$(id -u)" -eq 0 ] && BIN_DIR="/usr/local/bin"
KOMUT="$BIN_DIR/modelen-koordinator"
ok() { printf 'tamam  %s\n' "$*"; }
fail() { printf 'HATA   %s\n' "$*" >&2; exit 1; }

# --- örnek eğitim metni (yaklaşık 20 bin sözcük)
python3 - <<'PY' > "$H.metin.txt" 2>/dev/null || { for i in $(seq 1 4000); do echo "Modelen açık dil modellerini gönüllü ekran kartlarıyla birlikte eğitir. Satır $i."; done > "$H.metin.txt"; }
print(("Modelen açık dil modellerini gönüllü ekran kartlarıyla birlikte eğitir. " * 40 + "\n") * 100)
PY
[ -s "$H.metin.txt" ] || for i in $(seq 1 4000); do echo "Modelen açık dil modellerini gönüllü ekran kartlarıyla birlikte eğitir. Satır $i."; done > "$H.metin.txt"

# --- 1. --dene hiçbir şey kurmaz
bash koordinator-kur.sh --dene --hedef "$H" --sistemsiz --alan-adi koordinator.ornek.org >/dev/null
[ ! -e "$H/.venv" ] || fail "--dene bir şey kurdu"
ok "--dene plan yazdı, hiçbir şey kurmadı"

# --- 2. geçersiz girdiler reddedilir
if bash koordinator-kur.sh --dene --alan-adi "kotu alan;rm" >/dev/null 2>&1; then fail "geçersiz alan adı kabul edildi"; fi
if bash koordinator-kur.sh --dene --port abc >/dev/null 2>&1; then fail "sayısal olmayan port kabul edildi"; fi
ok "geçersiz alan adı / port reddedildi"

# --- 3. kurulum (yerel kaynak, veri hazırla, Caddyfile yaz, arka planda başlat)
bash koordinator-kur.sh --kaynak . --sistemsiz --hedef "$H" --veri "$H.metin.txt" --alan-adi test.ornek.org --port $PORT --tur 3 --en-az 2
[ -x "$KOMUT" ] || fail "yönetim komutu oluşmadı: $KOMUT"
ok "kurulum bitti (içindeki protokol uyum testi dahil)"

# --- 4. koordinatör gerçekten sunuyor mu?
ANAHTAR="$("$KOMUT" anahtar)"
[ ${#ANAHTAR} -ge 24 ] || fail "anahtar üretilmedi: '$ANAHTAR'"
[ "$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/durum")" = "401" ] || fail "anahtarsız /durum 401 vermedi"
BILGI="$(curl -s "http://127.0.0.1:$PORT/bilgi")"
echo "$BILGI" | grep -q '"veri"' || fail "/bilgi veri dilimlerini duyurmuyor: $BILGI"
echo "$BILGI" | grep -q '"anahtar_gerekli": true' || fail "/bilgi anahtar_gerekli=true demiyor"
G="$(curl -s -H "X-Anahtar: $ANAHTAR" "http://127.0.0.1:$PORT/gorev?isci=test-isci")"
echo "$G" | grep -q 'veri_sha256' || fail "görevde veri_sha256 yok: $G"
SHA="$(echo "$G" | sed 's/.*"veri_sha256": "\([0-9a-f]*\)".*/\1/')"
PARCA="$(echo "$G" | sed 's/.*"parca": \([0-9]*\).*/\1/')"
curl -s -H "X-Anahtar: $ANAHTAR" "http://127.0.0.1:$PORT/veri?parca=$PARCA" -o "$H.dilim"
[ "$(sha256sum "$H.dilim" | cut -d' ' -f1)" = "$SHA" ] || fail "indirilen veri dilimi özeti görevdekiyle uyuşmuyor"
ok "anahtar korumalı, veri dilimi sunuluyor ve özeti doğru"

# --- 5. anahtar süreç listesinde görünmemeli
if ps -eo args | grep -F "koordinator.py" | grep -qF "$ANAHTAR"; then fail "anahtar süreç argümanlarında görünüyor"; fi
ok "anahtar süreç listesinde yok"

# --- 6. açık/kapalı mod değişimi
"$KOMUT" acik >/dev/null; for i in $(seq 1 60); do curl -s "http://127.0.0.1:$PORT/bilgi" >/dev/null && break; sleep 1; done
[ "$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/durum")" = "200" ] || fail "acik modda anahtarsız /durum 200 vermedi"
"$KOMUT" kapat >/dev/null; for i in $(seq 1 60); do curl -s "http://127.0.0.1:$PORT/bilgi" >/dev/null && break; sleep 1; done
[ "$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/durum")" = "401" ] || fail "kapat sonrası anahtarsız /durum 401 vermedi"
ok "acik/kapat modları çalışıyor"

# --- 6b. gönüllü başına anahtar: bir anahtar = bir işçi adı, iptal edilebilir
HAZIR() { for i in $(seq 1 60); do curl -s "http://127.0.0.1:$PORT/bilgi" >/dev/null && break; sleep 1; done; }
ADMIN="$("$KOMUT" anahtar)"
V="$("$KOMUT" anahtar-ekle ali | sed -n 's/^Gönüllü .* için anahtar: //p')"
[ ${#V} -ge 24 ] || fail "gönüllü anahtarı üretilmedi: '$V'"
HAZIR
GK() { curl -s -o /dev/null -w '%{http_code}' -H "X-Anahtar: $1" "http://127.0.0.1:$PORT/gorev?isci=$2"; }
[ "$(GK "$V" ali)" = "200" ] || fail "gönüllü anahtarı kendi işçi adıyla 200 vermedi"
[ "$(GK "$V" baska)" = "403" ] || fail "gönüllü anahtarı ikinci işçi adını kabul etti"
[ "$(GK "$ADMIN" ali)" = "403" ] || fail "başka anahtar bağlı işçi adını aldı"
[ "$(GK "$ADMIN" yonetici-deneme)" = "200" ] || fail "yönetici anahtarı çalışmadı"
"$KOMUT" anahtarlar | grep -q '^ali ' || fail "anahtarlar listesi ali'yi göstermiyor"
"$KOMUT" anahtar-sil ali >/dev/null; HAZIR
[ "$(GK "$V" ali)" = "401" ] || fail "iptal edilen gönüllü anahtarı hâlâ geçerli"
[ "$("$KOMUT" anahtar)" = "$ADMIN" ] || fail "yönetici anahtarı değişti"
ok "gönüllü başına anahtar: ekle, sınır, iptal çalışıyor"

# --- 7. adres doğrulama dosyası ve Caddyfile
"$KOMUT" dogrulama "modelen-dogrulama-AbC123" >/dev/null
[ "$(cat "$H/dogrulama/dogrulama.txt")" = "modelen-dogrulama-AbC123" ] || fail "doğrulama dosyası yazılmadı"
if "$KOMUT" dogrulama 'kotu;icerik' >/dev/null 2>&1; then fail "geçersiz doğrulama içeriği kabul edildi"; fi
grep -q "reverse_proxy 127.0.0.1:$PORT" "$H/Caddyfile" || fail "Caddyfile reverse_proxy içermiyor"
grep -q "test.ornek.org {" "$H/Caddyfile" || fail "Caddyfile alan adını içermiyor"
ok "doğrulama dosyası ve Caddyfile doğru"

# --- 8. Caddyfile'ı gerçek Caddy ile doğrula (ağ varsa)
if curl -fsSL "https://caddyserver.com/api/download?os=linux&arch=amd64" -o "$H.caddy" 2>/dev/null; then
  chmod +x "$H.caddy"
  "$H.caddy" validate --config "$H/Caddyfile" --adapter caddyfile >/dev/null 2>&1 || fail "Caddy Caddyfile'ı geçersiz saydı"
  ok "Caddyfile gerçek Caddy ile doğrulandı"
else
  echo "atlandı: Caddy indirilemedi (ağ)"
fi

# --- 9. yeniden çalıştırma (güncelleme) mevcut anahtarı ve çalışma klasörünü korur
bash koordinator-kur.sh --kaynak . --sistemsiz --hedef "$H" --veri "$H.metin.txt" --port $PORT --tur 3 --en-az 2 >/dev/null
[ "$("$KOMUT" anahtar)" = "$(sed -n 's/^MODELEN_ANAHTAR=//p' "$H/koordinator.env")" ] || fail "yeniden kurulumda anahtar bozuldu"
ok "yeniden çalıştırma güvenli (anahtar korundu)"

"$KOMUT" durdur >/dev/null
echo "TÜM KONTROLLER GEÇTİ"
