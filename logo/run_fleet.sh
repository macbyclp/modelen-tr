#!/usr/bin/env bash
# Codex fleet: 10 salt-okunur hat (gpt-6-sol), her biri 10 SVG logo çizer. Hatlar 3 sn arayla başlar.
# Kullanım: bash run_fleet.sh [hat numaraları...]   (boşsa 1..10)
cd "$(dirname "$0")" || exit 1
LANES="${@:-1 2 3 4 5 6 7 8 9 10}"
for k in $LANES; do
  n=$(printf "%02d" "$k")
  codex exec --skip-git-repo-check -m gpt-6-sol -c model_reasoning_effort=high \
    --sandbox read-only --color never -o "ham/lane-$n.out" - < "briefs/lane-$n.txt" \
    > "ham/lane-$n.log" 2>&1 &
  sleep 3
done
wait
echo "FLEET_BITTI"
