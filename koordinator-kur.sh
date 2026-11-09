#!/usr/bin/env bash
# Modelen koordinatör kurulumu (Linux sunucu: Ubuntu, Debian, Arch ve diğer glibc tabanlı dağıtımlar). GPU GEREKMEZ.
#
#   sudo bash koordinator-kur.sh --alan-adi koordinator.ornek.org --veri metinler/
#   bash koordinator-kur.sh --sistemsiz --veri ornek.txt        # servis/HTTPS kurmadan, yalnızca çalıştır (deneme)
#   bash koordinator-kur.sh --dene                              # hiçbir şey kurmadan planı yaz
#
# Ne kurar: Python + PyTorch (CPU) [uv ile, sistem Python'una dokunmaz], koordinatör betikleri, başlangıç adaptörü (modelsiz),
# isteğe bağlı eğitim verisi (belirteçlenir ve işçilere sunulur), systemd servisi, HTTPS (Caddy, --alan-adi verilirse),
# paylaşılan anahtar ve `modelen-koordinator` yönetim komutu.
#
# Seçenekler:
#   --hedef DIR         kurulum klasörü (root: /opt/modelen-koordinator; değilse ~/modelen-koordinator)
#   --alan-adi AD       HTTPS için alan adı (Caddy kurulur; AD'nin A kaydı bu sunucuyu göstermeli, 80/443 açık olmalı)
#   --veri YOL          eğitim verisi: .txt/.md/.jsonl dosyası ya da klasörü (belirteçlenir) veya hazır .safetensors
#   --tur N             toplam tur (20)            --en-az N      turu kapatmak için gereken sonuç (2)
#   --ic-adim N         işçinin yerel adımı (20)   --parca N      veri dilimi sayısı (4)
#   --port N            koordinatör portu (8750)   --zaman-asimi S tur zaman aşımı sn (900)
#   --acik              anahtarsız: herkes katılabilir. Varsayılan: rastgele paylaşılan anahtar (kapalı grup)
#   --surum ETIKET      GitHub sürüm etiketi (varsayılan: en son)      --kaynak DIR  yerel depo (çevrimdışı/deneme)
#   --sistemsiz         systemd ve Caddy kurma; koordinatörü arka planda çalıştır (deneme/CI)
#   --dene              yalnızca ön koşulları denetle ve planı yaz
set -euo pipefail

DEPO="macbyclp/modelen-tr"
PAKETLER=(safetensors transformers huggingface_hub)
HIZMET_KULLANICI="modelen-koordinator"
ROOT=0; [ "$(id -u)" -eq 0 ] && ROOT=1
if [ "$ROOT" -eq 1 ]; then HEDEF="/opt/modelen-koordinator"; BIN="/usr/local/bin"; else HEDEF="$HOME/modelen-koordinator"; BIN="$HOME/.local/bin"; fi
ALAN=""; VERI=""; TUR=20; EN_AZ=2; IC_ADIM=20; PARCA=4; PORT=8750; ZAMAN_ASIMI=900; ACIK=0
SURUM="latest"; KAYNAK=""; SISTEMSIZ=0; DENE=0

kullanim() { sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }
adim() { printf '\n==> %s\n' "$*"; }
tamam() { printf '    %s\n' "$*"; }
hata() { printf '\nHATA: %s\n' "$*" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --hedef) HEDEF="$2"; shift 2 ;;
    --alan-adi) ALAN="$2"; shift 2 ;;
    --veri) VERI="$2"; shift 2 ;;
    --tur) TUR="$2"; shift 2 ;;
    --en-az) EN_AZ="$2"; shift 2 ;;
    --ic-adim) IC_ADIM="$2"; shift 2 ;;
    --parca) PARCA="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --zaman-asimi) ZAMAN_ASIMI="$2"; shift 2 ;;
    --acik) ACIK=1; shift ;;
    --surum) SURUM="$2"; shift 2 ;;
    --kaynak) KAYNAK="$2"; shift 2 ;;
    --sistemsiz) SISTEMSIZ=1; shift ;;
    --dene) DENE=1; shift ;;
    -h|--help) kullanim 0 ;;
    *) printf 'Bilinmeyen seçenek: %s\n' "$1" >&2; kullanim 1 ;;
  esac
done
for s in "$TUR" "$EN_AZ" "$IC_ADIM" "$PARCA" "$PORT" "$ZAMAN_ASIMI"; do case "$s" in ''|*[!0-9]*) hata "sayısal seçeneklere yalnızca rakam verin (gelen: '$s')" ;; esac; done
if [ -n "$ALAN" ]; then case "$ALAN" in *[!A-Za-z0-9.-]*|.*|*.) hata "geçersiz alan adı: $ALAN" ;; *.*) ;; *) hata "alan adı bir nokta içermeli: $ALAN" ;; esac; fi

# ---------------------------------------------------------------- ön koşullar
adim "Ön koşullar"
[ "$(uname -s)" = "Linux" ] || hata "Bu betik yalnızca Linux sunucular içindir."
case "$(uname -m)" in x86_64) UV_ARCH="x86_64-unknown-linux-gnu"; CADDY_ARCH="amd64" ;; aarch64) UV_ARCH="aarch64-unknown-linux-gnu"; CADDY_ARCH="arm64" ;; *) hata "Desteklenmeyen mimari: $(uname -m)" ;; esac
if ldd --version 2>&1 | grep -qi musl; then hata "musl tabanlı dağıtım (Alpine vb.) desteklenmiyor: PyTorch tekerleri glibc ister."; fi
command -v curl >/dev/null 2>&1 || hata "curl gerekli (Ubuntu/Debian: apt install curl, Arch: pacman -S curl)."
if [ "$SISTEMSIZ" -eq 0 ]; then
  command -v systemctl >/dev/null 2>&1 || hata "systemd bulunamadı. Servis olmadan denemek için --sistemsiz kullanın."
  [ "$ROOT" -eq 1 ] || hata "systemd servisi ve HTTPS için root gerekir: 'sudo bash koordinator-kur.sh ...'. Yalnızca denemek için --sistemsiz kullanın (root gerekmez)."
fi
mkdir -p "$HEDEF" 2>/dev/null || hata "$HEDEF oluşturulamadı."
BOS_GB=$(( $(df -Pk "$HEDEF" | awk 'NR==2{print $4}') / 1024 / 1024 ))
[ "$BOS_GB" -ge 3 ] || hata "Hedefte en az 3 GB boş yer gerekli (şu an ~${BOS_GB} GB)."
tamam "Boş disk: ~${BOS_GB} GB · hedef: $HEDEF · bellek: $(awk '/MemTotal/{printf "%.1f GB", $2/1024/1024}' /proc/meminfo)"
port_kullanimda() { { ss -ltn 2>/dev/null || netstat -ltn 2>/dev/null; } | awk '{print $4}' | grep -qE "[:.]$1$"; }
if port_kullanimda "$PORT" && [ ! -f "$HEDEF/koordinator.conf" ]; then hata "$PORT portu kullanımda. --port ile başka bir port seçin."; fi  # mevcut kurulum güncelleniyorsa port zaten bizim servisindir
CADDY_KUR=0
if [ -n "$ALAN" ] && [ "$SISTEMSIZ" -eq 0 ]; then
  if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet modelen-caddy 2>/dev/null; then
    CADDY_KUR=1  # kendi Caddy'miz zaten çalışıyor: yapılandırma güncellenip yeniden başlatılır
  elif port_kullanimda 80 || port_kullanimda 443; then
    tamam "UYARI: 80/443 portları kullanımda (başka bir web sunucusu var). Caddy KURULMAYACAK; kurulum sonunda mevcut vekiliniz için hazır yapılandırma parçası yazdırılır."
  else
    CADDY_KUR=1
  fi
fi

if [ "$DENE" -eq 1 ]; then
  adim "Plan (--dene: hiçbir şey kurulmadı)"
  tamam "1. uv indirilir; Python 3.12 ortamı: $HEDEF/.venv (PyTorch CPU + ${PAKETLER[*]})"
  tamam "2. Koordinatör betikleri: $([ -n "$KAYNAK" ] && echo "yerel: $KAYNAK" || echo "GitHub $DEPO ($SURUM)")"
  tamam "3. Başlangıç adaptörü (modelsiz): $HEDEF/calisma/tur-0.safetensors"
  tamam "4. Eğitim verisi: ${VERI:-(verilmedi: işçiler yerel veri ister)}"
  tamam "5. Yapılandırma: tur=$TUR en-az=$EN_AZ ic-adim=$IC_ADIM parca=$PARCA port=$PORT; $([ "$ACIK" -eq 1 ] && echo 'anahtarsız (açık)' || echo 'rastgele paylaşılan anahtar (kapalı grup)')"
  if [ "$SISTEMSIZ" -eq 1 ]; then tamam "6. Servis YOK: arka planda başlatılır ($BIN/modelen-koordinator durdur ile kapatılır)"
  else tamam "6. systemd servisi: modelen-koordinator.service (kullanıcı: $HIZMET_KULLANICI)"; [ "$CADDY_KUR" -eq 1 ] && tamam "7. HTTPS: Caddy, https://$ALAN -> 127.0.0.1:$PORT"; fi
  exit 0
fi

GECICI="$(mktemp -d)"
trap 'rm -rf "$GECICI"' EXIT

# ---------------------------------------------------------------- uv + Python ortamı
adim "Python ortamı (uv ile; sistem Python'una dokunulmaz)"
UV="$HEDEF/arac/uv"
if [ ! -x "$UV" ]; then
  mkdir -p "$HEDEF/arac"
  curl -fsSL "https://github.com/astral-sh/uv/releases/latest/download/uv-${UV_ARCH}.tar.gz" -o "$GECICI/uv.tar.gz" || hata "uv indirilemedi."
  tar -xzf "$GECICI/uv.tar.gz" -C "$GECICI"
  UVBUL="$(find "$GECICI" -type f -name uv | head -n1)"
  [ -n "$UVBUL" ] || hata "uv arşivinde uv bulunamadı."
  install -m 0755 "$UVBUL" "$UV"
fi
VENV="$HEDEF/.venv"
[ -x "$VENV/bin/python" ] || "$UV" venv "$VENV" --python 3.12 --seed 2>&1 | sed 's/^/    /'
PY="$VENV/bin/python"
tamam "PyTorch (CPU) ve paketler kuruluyor (~500 MB; birkaç dakika sürebilir)"
"$UV" pip install --python "$PY" torch --index-url "https://download.pytorch.org/whl/cpu" 2>&1 | sed 's/^/    /' || hata "PyTorch kurulamadı."
"$UV" pip install --python "$PY" "${PAKETLER[@]}" 2>&1 | sed 's/^/    /' || hata "paketler kurulamadı."

# ---------------------------------------------------------------- betikler
adim "Koordinatör betikleri"
if [ -n "$KAYNAK" ]; then
  [ -f "$KAYNAK/istemci/koordinator.py" ] || hata "$KAYNAK içinde istemci/koordinator.py yok."
  rm -rf "$HEDEF/istemci"; cp -r "$KAYNAK/istemci" "$HEDEF/istemci"
  find "$HEDEF/istemci" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
  rm -rf "$HEDEF/istemci/calisma"
  tamam "yerel kaynaktan kopyalandı"
else
  if [ "$SURUM" = "latest" ]; then BASE="https://github.com/$DEPO/releases/latest/download"; else BASE="https://github.com/$DEPO/releases/download/$SURUM"; fi
  curl -fsSL "$BASE/modelen-istemci.zip" -o "$GECICI/istemci.zip" || hata "modelen-istemci.zip indirilemedi ($BASE)."
  if curl -fsSL "$BASE/SHA256SUMS" -o "$GECICI/SHA256SUMS" 2>/dev/null; then
    BEKLENEN="$(grep ' modelen-istemci.zip$' "$GECICI/SHA256SUMS" | awk '{print $1}')"
    GERCEK="$(sha256sum "$GECICI/istemci.zip" | awk '{print $1}')"
    [ -z "$BEKLENEN" ] || [ "$BEKLENEN" = "$GERCEK" ] || hata "modelen-istemci.zip özeti SHA256SUMS ile uyuşmuyor; indirme bozuk ya da değiştirilmiş."
    tamam "SHA-256 özeti doğrulandı"
  fi
  rm -rf "$HEDEF/istemci"
  "$PY" -m zipfile -e "$GECICI/istemci.zip" "$HEDEF" || hata "zip açılamadı."
fi
[ -f "$HEDEF/istemci/koordinator.py" ] || hata "kurulum sonrası istemci/koordinator.py bulunamadı."
mkdir -p "$HEDEF/calisma" "$HEDEF/veri" "$HEDEF/dogrulama"

# ---------------------------------------------------------------- başlangıç adaptörü ve veri
adim "Başlangıç adaptörü (modelsiz) ve eğitim verisi"
if [ ! -f "$HEDEF/calisma/tur-0.safetensors" ]; then
  (cd "$HEDEF" && "$PY" istemci/adaptor_uret.py --cikti calisma/tur-0.safetensors 2>&1 | sed 's/^/    /') || hata "başlangıç adaptörü üretilemedi."
else
  tamam "mevcut çalışma klasörü korunuyor (tur-0 ve kayıtlı durum)"
fi
if [ -n "$VERI" ]; then
  [ -e "$VERI" ] || hata "--veri yolu yok: $VERI"
  case "$VERI" in
    *.safetensors) cp "$VERI" "$HEDEF/veri/veri.safetensors"; tamam "hazır veri kopyalandı" ;;
    *) (cd "$HEDEF" && "$PY" istemci/veri_hazirla.py --girdi "$(cd "$(dirname "$VERI")" && pwd)/$(basename "$VERI")" --cikti veri/veri.safetensors 2>&1 | sed 's/^/    /') || hata "veri hazırlanamadı." ;;
  esac
else
  tamam "UYARI: --veri verilmedi. Gönüllüler eğitim verisini koordinatörden alamaz; eski yerel-veri yolu kalır. Gerçek bir topluluk için --veri verin."
fi

# ---------------------------------------------------------------- yapılandırma, anahtar, çalıştırıcı
adim "Yapılandırma"
umask 027
ANAHTAR=""
SINIR=""
if [ -f "$HEDEF/koordinator.env" ]; then
  ANAHTAR="$(sed -n 's/^MODELEN_ANAHTAR=//p' "$HEDEF/koordinator.env" | head -n1)"
  SINIR="$(sed -n 's/^MODELEN_ANAHTAR_BASINA_ISCI=//p' "$HEDEF/koordinator.env" | head -n1)"
fi
if [ "$ACIK" -eq 0 ] && [ -z "$ANAHTAR" ]; then ANAHTAR="$(head -c 24 /dev/urandom | base64 | tr -d '=+/\n' | cut -c1-32)"; fi
if [ "$ACIK" -eq 1 ]; then ANAHTAR=""; fi
VEKIL=0; [ -n "$ALAN" ] && [ "$SISTEMSIZ" -eq 0 ] && VEKIL=1
printf 'MODELEN_ANAHTAR=%s\n' "$ANAHTAR" > "$HEDEF/koordinator.env"
if [ -n "$ANAHTAR" ] && [ -n "$SINIR" ]; then printf 'MODELEN_ANAHTAR_BASINA_ISCI=%s\n' "$SINIR" >> "$HEDEF/koordinator.env"; fi
cat > "$HEDEF/koordinator.conf" <<KONF
PORT=$PORT
TUR=$TUR
EN_AZ=$EN_AZ
IC_ADIM=$IC_ADIM
PARCA=$PARCA
ZAMAN_ASIMI=$ZAMAN_ASIMI
VEKIL=$VEKIL
ALAN=$ALAN
KONF
cat > "$HEDEF/calistir.sh" <<'CALISTIR'
#!/usr/bin/env bash
# systemd (ya da --sistemsiz) bu betiği çalıştırır; ayarlar koordinator.conf ve koordinator.env dosyalarındadır.
set -euo pipefail
cd "$(dirname "$0")"
. ./koordinator.conf
if [ -f ./koordinator.env ]; then set -a; . ./koordinator.env; set +a; fi
ARGS=(--baslangic calisma/tur-0.safetensors --calisma calisma --host 127.0.0.1 --port "$PORT" --tur "$TUR" --en-az "$EN_AZ" --ic-adim "$IC_ADIM" --parca "$PARCA" --zaman-asimi "$ZAMAN_ASIMI")
[ "${VEKIL:-0}" = "1" ] && ARGS+=(--vekil)
[ -f veri/veri.safetensors ] && ARGS+=(--veri veri/veri.safetensors)
exec ./.venv/bin/python istemci/koordinator.py "${ARGS[@]}"
CALISTIR
chmod 0755 "$HEDEF/calistir.sh"
chmod 0644 "$HEDEF/koordinator.conf"   # sır içermez; servis kullanıcısı okuyabilmeli
chmod 0600 "$HEDEF/koordinator.env"

# ---------------------------------------------------------------- yönetim komutu
mkdir -p "$BIN"
cat > "$BIN/modelen-koordinator" <<YONET
#!/usr/bin/env bash
# Modelen koordinatör yönetimi. Kullanım: modelen-koordinator <komut>
HEDEF="$HEDEF"
SISTEMSIZ=$SISTEMSIZ
BIN="$BIN"
YONET
cat >> "$BIN/modelen-koordinator" <<'YONET'
cd "$HEDEF" || exit 1
. ./koordinator.conf
anahtar_liste() { sed -n 's/^MODELEN_ANAHTAR=//p' ./koordinator.env | head -n1; }
anahtar_oku() { anahtar_liste | cut -d, -f1; }   # ilk anahtar = yönetici/izleme anahtarı (uyum testi, nabız, durum)
yeni_anahtar() { head -c 24 /dev/urandom | base64 | tr -d '=+/\n' | cut -c1-32; }
env_yaz() {  # $1 = virgüllü anahtar listesi, $2 = anahtar başına işçi sınırı (boş = yok)
  printf 'MODELEN_ANAHTAR=%s\n' "$1" > koordinator.env
  [ -n "${2:-}" ] && printf 'MODELEN_ANAHTAR_BASINA_ISCI=%s\n' "$2" >> koordinator.env
  env_izin
}
curl_k() { local a; a="$(anahtar_oku)"; if [ -n "$a" ]; then curl -s -H "X-Anahtar: $a" "$@"; else curl -s "$@"; fi; }
env_izin() {  # servis kullanıcısı (systemd) anahtar dosyasını okuyabilmeli, başkaları okuyamamalı; root yeniden yazınca izinler sıfırlanır
  if [ "$SISTEMSIZ" = "1" ]; then chmod 600 koordinator.env; else chgrp modelen-koordinator koordinator.env 2>/dev/null; chmod 640 koordinator.env; fi
}
yeniden() {
  if [ "$SISTEMSIZ" = "1" ]; then "$0" durdur >/dev/null 2>&1 || true; "$0" baslat
  else systemctl restart modelen-koordinator; systemctl try-restart modelen-nabiz 2>/dev/null || true; fi   # nabız servisi de yeni anahtarı alsın
}
case "${1:-}" in
  durum)
    if [ "$SISTEMSIZ" = "1" ]; then [ -f koordinator.pid ] && kill -0 "$(cat koordinator.pid)" 2>/dev/null && echo "çalışıyor (pid $(cat koordinator.pid))" || echo "çalışmıyor"
    else systemctl --no-pager --lines=0 status modelen-koordinator | sed -n '1,4p'; fi
    echo "--- /durum"; curl_k "http://127.0.0.1:$PORT/durum" | head -c 600; echo ;;
  anahtar) a="$(anahtar_oku)"; [ -n "$a" ] && echo "$a" || echo "(anahtar yok: koordinatör AÇIK; herkes katılabilir)" ;;
  anahtar-ekle)
    ad="${2:-}"; [ -n "$ad" ] || { echo "Kullanım: modelen-koordinator anahtar-ekle <gönüllü-adı>"; exit 1; }
    case "$ad" in *[!A-Za-z0-9._-]*) echo "Ad yalnızca harf, rakam, . _ - içerebilir"; exit 1 ;; esac
    [ -n "$(anahtar_oku)" ] || { echo "Koordinatör AÇIK; önce: modelen-koordinator kapat"; exit 1; }
    [ -f anahtarlar.txt ] && grep -q "^$ad " anahtarlar.txt && { echo "Bu ad zaten var: $ad"; exit 1; }
    n="$(yeni_anahtar)"; umask 077; printf '%s %s\n' "$ad" "$n" >> anahtarlar.txt; chmod 600 anahtarlar.txt
    env_yaz "$(anahtar_liste),$n" 1; yeniden
    echo "Gönüllü '$ad' için anahtar: $n"
    echo "(Bir anahtar yalnızca bir işçi adı kullanabilir; iptal: modelen-koordinator anahtar-sil $ad)" ;;
  anahtar-sil)
    ad="${2:-}"; [ -n "$ad" ] || { echo "Kullanım: modelen-koordinator anahtar-sil <gönüllü-adı>"; exit 1; }
    n="$(grep "^$ad " anahtarlar.txt 2>/dev/null | head -n1 | cut -d' ' -f2)"; [ -n "$n" ] || { echo "Böyle bir gönüllü anahtarı yok: $ad"; exit 1; }
    kalan="$(anahtar_liste | tr ',' '\n' | grep -vxF "$n" | paste -sd, -)"
    grep -v "^$ad " anahtarlar.txt > anahtarlar.yeni; mv anahtarlar.yeni anahtarlar.txt; chmod 600 anahtarlar.txt
    env_yaz "$kalan" "$(sed -n 's/^MODELEN_ANAHTAR_BASINA_ISCI=//p' koordinator.env | head -n1)"; yeniden
    echo "'$ad' anahtarı iptal edildi." ;;
  anahtarlar) [ -s anahtarlar.txt ] && cat anahtarlar.txt || echo "(gönüllü başına anahtar yok; tek paylaşılan anahtar: modelen-koordinator anahtar)" ;;
  acik)  env_yaz ""; : > anahtarlar.txt; yeniden; echo "Koordinatör artık AÇIK: anahtar istemez, herkes katılabilir." ;;
  kapat) a="$(yeni_anahtar)"; env_yaz "$a"; : > anahtarlar.txt; yeniden; echo "Koordinatör artık KAPALI. Yeni anahtar: $a" ;;
  dogrulama)
    [ -n "${2:-}" ] || { echo "Kullanım: modelen-koordinator dogrulama <portalın verdiği içerik>"; exit 1; }
    case "$2" in *[!A-Za-z0-9._-]*) echo "Geçersiz içerik (yalnızca harf, rakam, . _ - olmalı)"; exit 1 ;; esac
    printf '%s\n' "$2" > dogrulama/dogrulama.txt; chmod 644 dogrulama/dogrulama.txt
    echo "Yazıldı. https://${ALAN:-<alan-adınız>}/.well-known/modelen-dogrulama.txt adresi artık bu içeriği sunmalı." ;;
  uyum) ./.venv/bin/python istemci/uyum_testi.py --url "http://127.0.0.1:$PORT" --anahtar "$(anahtar_oku)" ;;
  nabiz)
    [ -n "${2:-}" ] || { echo "Kullanım: modelen-koordinator nabiz <mdl_... API anahtarı>  (modelen.tr > Panel > API anahtarları)"; exit 1; }
    [ "$SISTEMSIZ" = "1" ] && { echo "Nabız servisi systemd gerektirir (--sistemsiz kurulumda yok)."; exit 1; }
    printf 'MODELEN_API_ANAHTARI=%s\n' "$2" > nabiz.env; chmod 600 nabiz.env
    cat > /etc/systemd/system/modelen-nabiz.service <<UNIT
[Unit]
Description=Modelen nabiz (portala 'calisiyorum' bildirimi)
After=modelen-koordinator.service
[Service]
User=modelen-koordinator
EnvironmentFile=$HEDEF/nabiz.env
EnvironmentFile=$HEDEF/koordinator.env
ExecStart=$HEDEF/.venv/bin/python $HEDEF/istemci/ornekler/modelen_api.py nabiz-dongusu --koordinator http://127.0.0.1:$PORT --aralik 300
Restart=always
RestartSec=30
NoNewPrivileges=true
[Install]
WantedBy=multi-user.target
UNIT
    chown modelen-koordinator "$HEDEF/nabiz.env" 2>/dev/null || true
    systemctl daemon-reload && systemctl enable modelen-nabiz >/dev/null 2>&1 && systemctl restart modelen-nabiz && echo "Nabız servisi başladı (5 dakikada bir). Koordinatörünüz onaylıysa modelen.tr dizininde 'çevrimiçi' görünür." ;;
  gunluk) if [ "$SISTEMSIZ" = "1" ]; then tail -n 60 koordinator.log; else journalctl -u modelen-koordinator -n 60 --no-pager; fi ;;
  baslat)
    if [ "$SISTEMSIZ" = "1" ]; then nohup ./calistir.sh > koordinator.log 2>&1 & echo $! > koordinator.pid; echo "başlatıldı (pid $(cat koordinator.pid))"
    else systemctl start modelen-koordinator; fi ;;
  durdur)
    if [ "$SISTEMSIZ" = "1" ]; then [ -f koordinator.pid ] && kill "$(cat koordinator.pid)" 2>/dev/null; rm -f koordinator.pid; echo "durduruldu"
    else systemctl stop modelen-koordinator; fi ;;
  yeniden-baslat) yeniden ;;
  kaldir)
    echo "Servisler durdurulup kaldırılıyor (veri klasörü $HEDEF silinmez)."
    if [ "$SISTEMSIZ" = "1" ]; then "$0" durdur
    else for s in modelen-nabiz modelen-caddy modelen-koordinator; do systemctl disable --now "$s" >/dev/null 2>&1; rm -f "/etc/systemd/system/$s.service"; done; systemctl daemon-reload; fi
    rm -f "$BIN/modelen-koordinator"; echo "Tamam. Tamamen silmek için: rm -rf $HEDEF" ;;
  *) cat <<AYD
modelen-koordinator <komut>
  durum            servis durumu ve /durum özeti
  anahtar          paylaşılan anahtarı göster (gönüllülere ver)
  acik | kapat     anahtarsız (herkese açık) / anahtarlı (kapalı grup) mod
  dogrulama <içerik>  portalın adres doğrulaması için dosyayı yaz
  uyum             protokol uyum testini çalıştır
  nabiz <API_ANAHTARI>  portala nabız göndermeyi başlat (systemd servisi)
  gunluk           son günlükler
  baslat | durdur | yeniden-baslat
  kaldir           servisleri kaldır
AYD
    ;;
esac
YONET
chmod 0755 "$BIN/modelen-koordinator"
tamam "$BIN/modelen-koordinator"

# ---------------------------------------------------------------- Caddy yapılandırması
CADDYFILE=""
if [ -n "$ALAN" ]; then
  CADDYFILE="$HEDEF/Caddyfile"
  cat > "$CADDYFILE" <<CADDY
$ALAN {
    encode zstd gzip
    handle /.well-known/modelen-dogrulama.txt {
        root * $HEDEF/dogrulama
        rewrite * /dogrulama.txt
        file_server
    }
    reverse_proxy 127.0.0.1:$PORT
}
CADDY
fi

# ---------------------------------------------------------------- servisler
if [ "$SISTEMSIZ" -eq 1 ]; then
  adim "Koordinatör arka planda başlatılıyor (--sistemsiz)"
  "$BIN/modelen-koordinator" durdur >/dev/null 2>&1 || true   # güncelleme: eski süreç varsa önce kapat
  "$BIN/modelen-koordinator" baslat | sed 's/^/    /'
else
  adim "systemd servisi"
  if ! id "$HIZMET_KULLANICI" >/dev/null 2>&1; then
    useradd --system --home-dir "$HEDEF" --shell /usr/sbin/nologin "$HIZMET_KULLANICI" 2>/dev/null || useradd --system --home-dir "$HEDEF" --shell /bin/false "$HIZMET_KULLANICI" || hata "$HIZMET_KULLANICI kullanıcısı oluşturulamadı."
  fi
  chown -R "$HIZMET_KULLANICI" "$HEDEF/calisma" "$HEDEF/dogrulama"
  chgrp "$HIZMET_KULLANICI" "$HEDEF/koordinator.env" && chmod 0640 "$HEDEF/koordinator.env"
  chmod -R a+rX "$HEDEF/.venv" "$HEDEF/istemci" "$HEDEF/veri" "$HEDEF/arac" 2>/dev/null || true
  MEM_MB=$(( $(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo) / 2 )); [ "$MEM_MB" -lt 700 ] && MEM_MB=700
  cat > /etc/systemd/system/modelen-koordinator.service <<UNIT
[Unit]
Description=Modelen koordinatoru
After=network-online.target
Wants=network-online.target

[Service]
User=$HIZMET_KULLANICI
WorkingDirectory=$HEDEF
ExecStart=$HEDEF/calistir.sh
Restart=always
RestartSec=5
MemoryMax=${MEM_MB}M
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=$HEDEF/calisma
PrivateTmp=true
ProtectHome=true

[Install]
WantedBy=multi-user.target
UNIT
  systemctl daemon-reload
  systemctl enable modelen-koordinator >/dev/null 2>&1
  systemctl restart modelen-koordinator || hata "servis başlatılamadı: journalctl -u modelen-koordinator"
  tamam "modelen-koordinator.service başlatıldı"
  if [ "$CADDY_KUR" -eq 1 ]; then
    adim "HTTPS (Caddy)"
    if [ ! -x /usr/local/bin/modelen-caddy ]; then
      curl -fsSL "https://caddyserver.com/api/download?os=linux&arch=$CADDY_ARCH" -o "$GECICI/caddy" || hata "Caddy indirilemedi."
      install -m 0755 "$GECICI/caddy" /usr/local/bin/modelen-caddy
    fi
    mkdir -p "$HEDEF/caddy"; chown -R "$HIZMET_KULLANICI" "$HEDEF/caddy"
    /usr/local/bin/modelen-caddy validate --config "$CADDYFILE" --adapter caddyfile >/dev/null 2>&1 || hata "Caddy yapılandırması geçersiz: $CADDYFILE"
    cat > /etc/systemd/system/modelen-caddy.service <<UNIT
[Unit]
Description=Modelen koordinator HTTPS (Caddy)
After=network-online.target modelen-koordinator.service
Wants=network-online.target

[Service]
User=$HIZMET_KULLANICI
Environment=XDG_DATA_HOME=$HEDEF/caddy XDG_CONFIG_HOME=$HEDEF/caddy
ExecStart=/usr/local/bin/modelen-caddy run --config $CADDYFILE --adapter caddyfile
Restart=always
AmbientCapabilities=CAP_NET_BIND_SERVICE
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
UNIT
    systemctl daemon-reload
    systemctl enable modelen-caddy >/dev/null 2>&1
    systemctl restart modelen-caddy || hata "Caddy başlatılamadı: journalctl -u modelen-caddy"
    tamam "modelen-caddy.service başlatıldı (sertifika, alan adı bu sunucuyu gösterince otomatik alınır)"
  fi
fi

# ---------------------------------------------------------------- doğrulama
adim "Doğrulama"
for i in $(seq 1 90); do curl -s "http://127.0.0.1:$PORT/bilgi" >/dev/null 2>&1 && break; sleep 1; done
curl -s "http://127.0.0.1:$PORT/bilgi" >/dev/null 2>&1 || hata "koordinatör yanıt vermiyor ($( [ "$SISTEMSIZ" -eq 1 ] && echo "$HEDEF/koordinator.log" || echo "journalctl -u modelen-koordinator" ) dosyasına bakın)."
tamam "/bilgi yanıt veriyor"
if "$BIN/modelen-koordinator" uyum > "$GECICI/uyum.txt" 2>&1; then
  tamam "protokol uyum testi: $(tail -n1 "$GECICI/uyum.txt")"
else
  cat "$GECICI/uyum.txt" | sed 's/^/    /'; hata "protokol uyum testi başarısız."
fi

# ---------------------------------------------------------------- sonraki adımlar
KOMUT="modelen-koordinator"
printf '\n════════════════════════════════════════════════════════════\n'
printf 'Koordinatör kuruldu ve çalışıyor.\n'
printf '  Klasör:   %s\n  Port:     127.0.0.1:%s\n' "$HEDEF" "$PORT"
if [ -n "$ANAHTAR" ]; then printf '  Anahtar:  %s   (KAPALI grup: gönüllülere bunu verin; sonra: %s anahtar)\n' "$ANAHTAR" "$KOMUT"; else printf '  Anahtar:  yok (AÇIK: herkes katılabilir)\n'; fi
printf '\nSıradaki adımlar:\n'
if [ -n "$ALAN" ]; then
  printf '  1. DNS: %s için A kaydı bu sunucunun IP adresini göstersin; 80 ve 443 portları açık olsun.\n' "$ALAN"
  if [ "$CADDY_KUR" -eq 0 ] && [ "$SISTEMSIZ" -eq 0 ]; then
    printf '     Mevcut web sunucunuz için (Caddy: aşağıdakini ekleyin; nginx: proxy_pass http://127.0.0.1:%s ve /.well-known/modelen-dogrulama.txt için %s/dogrulama/dogrulama.txt):\n' "$PORT" "$HEDEF"
    sed 's/^/       /' "$CADDYFILE"
  fi
  [ "$SISTEMSIZ" -eq 1 ] && printf '     (--sistemsiz: HTTPS kurulmadı; Caddy yapılandırma örneği: %s)\n' "$CADDYFILE"
else
  printf '  1. HTTPS: koordinatörünüz yalnızca 127.0.0.1:%s dinliyor. Genel ağa açmak için bir ters vekil (Caddy/nginx) ve alan adı gerekir; yeniden çalıştırın: --alan-adi koordinator.ornek.org\n' "$PORT"
fi
printf '  2. https://modelen.tr üzerinde hesap açın, e-postanızı doğrulayın ve Panel > Başvuru ile koordinatör başvurusu yapın (adres: https://%s).\n' "${ALAN:-<alan-adınız>}"
printf '  3. Portalın verdiği adres doğrulama içeriğini yazın:  %s dogrulama <içerik>\n' "$KOMUT"
printf '  4. Panel > API anahtarları ile anahtar üretip nabız gönderin:  %s nabiz mdl_...\n' "$KOMUT"
printf '  5. Durum ve günlük:  %s durum  |  %s gunluk\n' "$KOMUT" "$KOMUT"
printf 'Ayrıntı: https://docs.modelen.tr/koordinator-kurulum/\n'
printf '════════════════════════════════════════════════════════════\n'
