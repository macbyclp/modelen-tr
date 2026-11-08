#!/usr/bin/env bash
# Modelen gönüllü kurulumu (Linux / Ubuntu): eğitim ortamı + taban model + "modelen-isci" komutu.
#
#   bash kur.sh                 # kur (varsayılan: ~/.local/share/modelen)
#   bash kur.sh --dene          # hiçbir şey kurmadan ön koşulları denetle, planı yaz
#   bash kur.sh --cuda cu121    # PyTorch CUDA sürümü: cu124 (varsayılan), cu121, cu126, cpu (yalnızca deneme)
#
# Yönetici (sudo) yetkisi gerekmez. Sistem Python'una dokunmaz; her şey tek klasördedir, silerek kaldırılır.
# Gereksinim: x86_64 Linux, NVIDIA GPU (en az 6 GB) + güncel NVIDIA sürücüsü, ~8 GB boş disk, internet, curl.
# Not: grafik arayüz (modelen.exe) yalnızca Windows içindir; Linux'ta işçi komut satırından çalışır.
set -euo pipefail

DEPO="macbyclp/modelen-tr"
MODEL="Qwen/Qwen3-0.6B-Base"
PAKETLER=(transformers peft safetensors huggingface_hub)
HEDEF="${XDG_DATA_HOME:-$HOME/.local/share}/modelen"
BIN="$HOME/.local/bin"
SURUM="latest"
KAYNAK=""
CUDA="cu124"
MODEL_ATLA=0
DENE=0

kullanim() { sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }
adim() { printf '\n==> %s\n' "$*"; }
tamam() { printf '    %s\n' "$*"; }
hata() { printf '\nHATA: %s\n' "$*" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --hedef) HEDEF="$2"; shift 2 ;;
    --surum) SURUM="$2"; shift 2 ;;
    --kaynak) KAYNAK="$2"; shift 2 ;;
    --cuda) CUDA="$2"; shift 2 ;;
    --model-atla) MODEL_ATLA=1; shift ;;
    --dene) DENE=1; shift ;;
    -h|--help) kullanim 0 ;;
    *) printf 'Bilinmeyen seçenek: %s\n' "$1" >&2; kullanim 1 ;;
  esac
done
case "$CUDA" in cu124|cu121|cu126|cpu) ;; *) hata "--cuda cu124, cu121, cu126 ya da cpu olmalı" ;; esac

# ---------------------------------------------------------------- ön koşullar
adim "Ön koşullar"
[ "$(uname -s)" = "Linux" ] || hata "Bu betik yalnızca Linux içindir (macOS desteklenmiyor: NVIDIA/CUDA yok)."
ARCH="$(uname -m)"
case "$ARCH" in
  x86_64) UV_ARCH="x86_64-unknown-linux-gnu" ;;
  aarch64) UV_ARCH="aarch64-unknown-linux-gnu"; [ "$CUDA" = "cpu" ] || hata "aarch64'te yalnızca --cuda cpu denenebilir (CUDA tekerleri x86_64 içindir)." ;;
  *) hata "Desteklenmeyen mimari: $ARCH" ;;
esac
command -v curl >/dev/null 2>&1 || hata "curl gerekli (Ubuntu: sudo apt install curl)."
mkdir -p "$HEDEF" 2>/dev/null || hata "$HEDEF oluşturulamadı."
BOS_KB="$(df -Pk "$HEDEF" | awk 'NR==2{print $4}')"
BOS_GB=$((BOS_KB / 1024 / 1024))
[ "$BOS_GB" -ge 8 ] || hata "Hedefte en az 8 GB boş yer gerekli (şu an ~${BOS_GB} GB)."
tamam "Boş disk: ~${BOS_GB} GB"
tamam "Hedef: $HEDEF"

if [ "$CUDA" != "cpu" ]; then
  command -v nvidia-smi >/dev/null 2>&1 || hata "nvidia-smi bulunamadı: NVIDIA sürücüsü yok. Ubuntu: 'sudo ubuntu-drivers install' ile kurup yeniden başlatın. Yalnızca denemek için --cuda cpu kullanın."
  GPU="$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | head -n1 || true)"
  [ -n "$GPU" ] || hata "nvidia-smi bir GPU göstermedi (sürücü yüklü ama çalışmıyor olabilir)."
  tamam "GPU: $GPU"
  # PyTorch CUDA tekerleri asgari sürücü ister (Linux): cu124 >= 550, cu126 >= 560, cu121 >= 525
  case "$CUDA" in cu124) ASGARI=550 ;; cu126) ASGARI=560 ;; cu121) ASGARI=525 ;; esac
  SUR="$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -n1 | cut -d. -f1 || true)"
  if [ -n "$SUR" ] && [ "$SUR" -lt "$ASGARI" ] 2>/dev/null; then
    hata "NVIDIA sürücünüz ($SUR) PyTorch $CUDA için çok eski (en az $ASGARI gerekir). Güncelleyin ya da --cuda cu121 deneyin."
  fi
fi

if [ "$DENE" -eq 1 ]; then
  adim "Plan (--dene: hiçbir şey kurulmadı)"
  tamam "1. uv indirilir (astral-sh/uv, $UV_ARCH)"
  tamam "2. Python 3.12 sanal ortamı: $HEDEF/.venv"
  tamam "3. PyTorch ($CUDA) + ${PAKETLER[*]}"
  tamam "4. İstemci betikleri: $([ -n "$KAYNAK" ] && echo "yerel: $KAYNAK" || echo "GitHub $DEPO ($SURUM)")"
  tamam "5. Taban model: $MODEL -> $HEDEF/models/qwen3-0.6b-base"
  tamam "6. Komut: $BIN/modelen-isci"
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
if [ ! -x "$VENV/bin/python" ]; then
  "$UV" venv "$VENV" --python 3.12 --seed 2>&1 | sed 's/^/    /' || hata "sanal ortam oluşturulamadı."
fi
PY="$VENV/bin/python"

# ---------------------------------------------------------------- betikler
adim "Eğitim betikleri"
if [ -n "$KAYNAK" ]; then
  [ -f "$KAYNAK/istemci/isci.py" ] || hata "$KAYNAK içinde istemci/isci.py yok."
  for d in istemci sunucu; do
    [ -d "$KAYNAK/$d" ] && { rm -rf "${HEDEF:?}/$d"; cp -r "$KAYNAK/$d" "$HEDEF/$d"; }
  done
  find "$HEDEF" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
  rm -rf "$HEDEF/istemci/calisma"
  tamam "yerel kaynaktan kopyalandı"
else
  if [ "$SURUM" = "latest" ]; then BASE="https://github.com/$DEPO/releases/latest/download"; else BASE="https://github.com/$DEPO/releases/download/$SURUM"; fi
  curl -fsSL "$BASE/modelen-istemci.zip" -o "$GECICI/modelen-istemci.zip" || hata "modelen-istemci.zip indirilemedi ($BASE)."
  if curl -fsSL "$BASE/SHA256SUMS" -o "$GECICI/SHA256SUMS" 2>/dev/null; then
    BEKLENEN="$(grep ' modelen-istemci.zip$' "$GECICI/SHA256SUMS" | awk '{print $1}')"
    GERCEK="$(sha256sum "$GECICI/modelen-istemci.zip" | awk '{print $1}')"
    [ -z "$BEKLENEN" ] || [ "$BEKLENEN" = "$GERCEK" ] || hata "modelen-istemci.zip özeti SHA256SUMS ile uyuşmuyor; indirme bozuk ya da değiştirilmiş."
    tamam "SHA-256 özeti doğrulandı"
  else
    tamam "UYARI: SHA256SUMS yok; özet doğrulanamadı."
  fi
  "$PY" -m zipfile -e "$GECICI/modelen-istemci.zip" "$HEDEF" || hata "zip açılamadı."
fi
[ -f "$HEDEF/istemci/isci.py" ] || hata "kurulum sonrası istemci/isci.py bulunamadı."

# ---------------------------------------------------------------- PyTorch + paketler
adim "PyTorch ($CUDA) ve gerekli paketler (birkaç GB; sabırlı olun)"
"$UV" pip install --python "$PY" torch --index-url "https://download.pytorch.org/whl/$CUDA" 2>&1 | sed 's/^/    /' || hata "PyTorch kurulamadı."
"$UV" pip install --python "$PY" "${PAKETLER[@]}" 2>&1 | sed 's/^/    /' || hata "paketler kurulamadı."

# ---------------------------------------------------------------- taban model
MODEL_KLASORU="$HEDEF/models/qwen3-0.6b-base"
if [ "$MODEL_ATLA" -eq 1 ]; then
  adim "Taban model atlandı (--model-atla)"
elif [ -f "$MODEL_KLASORU/config.json" ]; then
  adim "Taban model zaten var"; tamam "$MODEL_KLASORU"
else
  adim "Taban model indiriliyor ($MODEL, Apache-2.0, ~1.2 GB)"
  mkdir -p "$MODEL_KLASORU"
  "$PY" -c "from huggingface_hub import snapshot_download; snapshot_download('$MODEL', local_dir='$MODEL_KLASORU', allow_patterns=['*.json','*.safetensors','*.txt'])" 2>&1 | sed 's/^/    /' || hata "model indirilemedi."
fi

# ---------------------------------------------------------------- komut
adim "Komut"
mkdir -p "$BIN"
cat > "$BIN/modelen-isci" <<KOMUT
#!/usr/bin/env bash
# Modelen gönüllü işçisi. Örnek: modelen-isci --koordinator https://koordinator.ornek.org --isci takma-adiniz
cd "$HEDEF" && exec "$PY" istemci/isci.py "\$@"
KOMUT
chmod +x "$BIN/modelen-isci"
tamam "$BIN/modelen-isci"
case ":$PATH:" in *":$BIN:"*) ;; *) tamam "UYARI: $BIN PATH'inizde değil; ekleyin: export PATH=\"$BIN:\$PATH\"" ;; esac

# ---------------------------------------------------------------- doğrulama
adim "Doğrulama"
"$PY" -c "import torch; print('torch', torch.__version__, '| CUDA available:', torch.cuda.is_available()); import transformers, peft, safetensors; print('packages ok')" 2>&1 | sed 's/^/    /' || hata "Python ortamı doğrulanamadı."
"$PY" "$HEDEF/istemci/isci.py" --help >/dev/null 2>&1 || hata "isci.py çalıştırılamadı."

printf '\nKurulum tamam: %s\n' "$HEDEF"
printf "Başlatmak için: modelen-isci --koordinator <koordinatör adresi> --isci <takma adınız>\n"
printf "Kaldırmak için: rm -rf %s %s/modelen-isci\n" "$HEDEF" "$BIN"
