#!/usr/bin/env bash
# Yerel SFT denemesi: koordinatör (--mod sft) + 2 işçi + değerlendirme. Kullanım: bash istemci/sft_dene.sh [tur] [adim]
set -euo pipefail
cd "$(dirname "$0")/.."
TUR="${1:-4}"; ADIM="${2:-25}"; PORT=8765
PY=.venv/Scripts/python.exe; [ -f "$PY" ] || PY=.venv/bin/python
C="$(mktemp -d)"; echo "çalışma klasörü: $C"
$PY istemci/baslat.py --cikti "$C/tur-0.safetensors" >/dev/null 2>&1
$PY istemci/koordinator.py --baslangic "$C/tur-0.safetensors" --tur "$TUR" --en-az 2 --ic-adim "$ADIM" --port $PORT --calisma "$C" --mod sft >"$C/koordinator.log" 2>&1 &
KP=$!
trap 'kill $KP 2>/dev/null || true' EXIT
for i in $(seq 1 60); do curl -s "http://127.0.0.1:$PORT/durum" >/dev/null 2>&1 && break; sleep 1; done
$PY istemci/isci.py --koordinator "http://127.0.0.1:$PORT" --isci sft-a >"$C/a.log" 2>&1 &
$PY istemci/isci.py --koordinator "http://127.0.0.1:$PORT" --isci sft-b >"$C/b.log" 2>&1 &
wait %2 %3
echo "--- işçi günlüğü"; grep -a "işçi" "$C/a.log" | tr -d '\r' | tail -6
$PY istemci/degerlendir_sft.py "$C/tur-0.safetensors" "$C/tur-$TUR.safetensors" 2>&1 | tr '\r' '\n' | grep -aE "yanıt kaybı|S:|C:"
echo "klasör: $C"
