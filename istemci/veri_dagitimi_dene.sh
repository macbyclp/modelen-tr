#!/usr/bin/env bash
# Uçtan uca: koordinatör veri dilimlerini kendisi sunar; işçilerde yerel veri dosyası YOK (boş önbellek klasörü, olmayan --veri yolu).
# Kullanım: bash istemci/veri_dagitimi_dene.sh [tur] [adim]
set -euo pipefail
cd "$(dirname "$0")/.."
TUR="${1:-2}"; ADIM="${2:-5}"; PORT=8766
PY=.venv/Scripts/python.exe; [ -f "$PY" ] || PY=.venv/bin/python
C="$(mktemp -d)"; echo "çalışma klasörü: $C"
[ -f data/wiki30.safetensors ] || $PY istemci/veri_donustur.py data/tok-wiki30.pt data/wiki30.safetensors
$PY istemci/baslat.py --cikti "$C/tur-0.safetensors" >/dev/null 2>&1
$PY istemci/koordinator.py --baslangic "$C/tur-0.safetensors" --veri data/wiki30.safetensors --tur "$TUR" --en-az 2 --ic-adim "$ADIM" --port $PORT --calisma "$C/k" >"$C/koordinator.log" 2>&1 &
KP=$!
trap 'kill $KP 2>/dev/null || true' EXIT
for i in $(seq 1 90); do curl -s "http://127.0.0.1:$PORT/durum" >/dev/null 2>&1 && break; sleep 1; done
for ad in a b; do
  MODELEN_VERI_KLASORU="$C/onbellek-$ad" $PY istemci/isci.py --koordinator "http://127.0.0.1:$PORT" --isci "gonullu-$ad" --veri "$C/YOK.pt" >"$C/$ad.log" 2>&1 &
done
wait %2 %3
echo "--- işçi günlüğü"; grep -a "işçi" "$C/a.log" | tr -d '\r' | tail -5
echo "--- önbellek"; ls -la "$C"/onbellek-*/ | grep safetensors
grep -a "veri:" "$C/koordinator.log" | head -2
echo "--- değerlendirme (bit/bayt)"; $PY istemci/degerlendir.py "$C/tur-0.safetensors" "$C/k/tur-$TUR.safetensors" 2>&1 | tr '\r' '\n' | grep -a "bit/bayt"
echo "klasör: $C"
