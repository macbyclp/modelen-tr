#!/usr/bin/env bash
# Fener varyantı için tek görsel üretimi (gpt-image-2, Codex gpt-6-sol, salt okunur). Kullanım: bash fener_one.sh 3
cd "$(dirname "$0")/fener" || exit 1
id=$(printf "f%02d" "$1")
[ -s "img/$id.png" ] && { echo "var $id"; exit 0; }
sleep $((RANDOM % 5))
for deneme in 1 2; do
  codex exec --skip-git-repo-check --ephemeral -m gpt-6-sol -c model_reasoning_effort=low \
    --sandbox read-only --ignore-rules --color never -o "ham/$id.out" - \
    < "briefs-img/$id.txt" > "ham/$id.log" 2>&1
  sid=$(grep -m1 "session id:" "ham/$id.log" | awk '{print $3}')
  f=$(ls -t ~/.codex/generated_images/"$sid"/*.png 2>/dev/null | head -n 1)
  if [ -n "$sid" ] && [ -n "$f" ]; then cp "$f" "img/$id.png"; echo "ok $id"; exit 0; fi
  echo "tekrar $id"
done
echo "BASARISIZ $id"
