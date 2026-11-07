#!/usr/bin/env bash
# Tek logo için gpt-image-2 üretimi (Codex, gpt-6-sol, salt okunur sandbox). Çıktıyı img/NNN.png'ye kopyalar.
cd "$(dirname "$0")" || exit 1
id=$(printf "%03d" "$1")
[ -s "img/$id.png" ] && { echo "var $id"; exit 0; }
sleep $((RANDOM % 6))
for deneme in 1 2; do
  codex exec --skip-git-repo-check --ephemeral -m gpt-6-sol -c model_reasoning_effort=low \
    --sandbox read-only --ignore-rules --color never -o "ham-img/$id.out" - \
    < "briefs-img/$id.txt" > "ham-img/$id.log" 2>&1
  sid=$(grep -m1 "session id:" "ham-img/$id.log" | awk '{print $3}')
  f=$(ls -t ~/.codex/generated_images/"$sid"/*.png 2>/dev/null | head -n 1)
  if [ -n "$sid" ] && [ -n "$f" ]; then cp "$f" "img/$id.png"; echo "ok $id"; exit 0; fi
  echo "tekrar $id (deneme $deneme)"
done
echo "BASARISIZ $id"
