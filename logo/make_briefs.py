# -*- coding: utf-8 -*-
"""10 hat için brief dosyaları üretir (hat k, kavram numarası (id-1) % 10 == k-1 olanları alır)."""
import os
from konseptler import KONSEPT

KOK = os.path.dirname(os.path.abspath(__file__))
LANES = 10

SPEC = """You are a senior logo designer drawing SVG marks for "Modelen", an open-source Turkish AI startup (community-trained language models on volunteers' graphics cards; open, transparent, Turkish-first). You will draw {n} DIFFERENT logo marks, one per concept listed at the end. Output SVG only.

HARD RULES for every SVG
- Standalone, well-formed XML starting exactly with: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128">
- Symbol only. NO <text>. No <style>, <script>, <image>, <use>, <filter>, <mask>, <clipPath>, gradients, opacity tricks, blur or external references. Letters may only appear as drawn shapes (paths/polygons), and only if the concept is a letter.
- Allowed elements: svg, g, path, circle, ellipse, rect, polygon, polyline, line. Use explicit fill/stroke attributes (no CSS classes).
- Palette ONLY: #ff4640 (bright red), #e30a17 (deep red), #fafaf4 (off-white), #8a8a96 (gray), #101013 (near-black). At most 3 colors per mark. Transparent background: do NOT draw a background rectangle. The mark is shown on dark AND light backgrounds, so the essential silhouette must be red (#ff4640 or #e30a17); use off-white or gray only for secondary details.
- Bold, geometric, flat. It must stay recognisable at 24x24 px: minimum stroke width 6 units on the 128 grid, minimum gap 4 units, no hairlines, no tiny details. Keep an 8-unit margin and center the mark. Strong, simple silhouette.
- One clear idea per mark. Make the {n} marks visibly different in construction (mix filled shapes, thick-stroke line art, negative space, pixel/grid constructions, symmetric and asymmetric ones).
- Originality: do not imitate any existing company logo (no Mistral, OpenAI, Anthropic, Hugging Face, Google, Meta, etc.). No national flags, crescent-and-star, coats of arms, religious symbols, or real people.
- Each SVG under 1800 bytes.

Work method: for each concept, decide the construction on the 128x128 grid (coordinates), check balance and legibility at small size, then write the final SVG. Do not write any files and do not run commands; just answer.

OUTPUT FORMAT (your final message must contain ONLY these blocks, no prose, no markdown fences, one block per concept, using the given id, in the given order):
<<<LOGO 007>>>
<svg ...>...</svg>
<<<END>>>

CONCEPTS (id | name | meaning | construction hint)
"""

for k in range(1, LANES + 1):
    satirlar = []
    for i, (kat, ad, anlam, ipucu) in enumerate(KONSEPT, start=1):
        if (i - 1) % LANES == k - 1:
            satirlar.append(f"{i:03d} | {ad} | {anlam} | {ipucu}")
    metin = SPEC.format(n=len(satirlar)) + "\n".join(satirlar) + "\n"
    with open(os.path.join(KOK, "briefs", f"lane-{k:02d}.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(metin)
    print(f"lane-{k:02d}: {len(satirlar)} kavram, {len(metin.encode('utf-8'))} bayt")
