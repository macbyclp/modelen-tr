# -*- coding: utf-8 -*-
"""Her logo kavramı için ayrı bir gpt-image-2 istemi üretir (briefs-img/NNN.txt)."""
import os

from konseptler import KONSEPT

KOK = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(KOK, "briefs-img"), exist_ok=True)

SABLON = """$imagegen
TOOL DIRECTIVE: You MUST use the built-in image generation tool (image_gen / gpt-image-2). DO NOT write Python. DO NOT use PIL/Pillow/canvas/sharp/any drawing library. DO NOT generate procedurally with code. If the image generation tool is unavailable, refuse and say so explicitly. Generate exactly ONE image. After generating, reply with only the word DONE.

Size: 1024x1024.

Use case: logo mark concept for "Modelen", an open-source Turkish AI startup that trains language models together with volunteers' graphics cards (open, transparent, community-owned, Turkish-first).
Subject: a single logo MARK (symbol only) for the concept "{ad}". Meaning: {anlam} Construction idea: {ipucu}
Composition: one centered mark with generous empty padding on all sides, strong simple silhouette, readable at very small size.
Style: modern minimal flat vector logo design, bold geometric shapes and thick lines, crisp clean edges, no gradients, no shadows, no 3D, no texture. Distinctive and memorable, designer-quality, like a professional brand identity presentation mark.
Palette: brand red #ff4640 and deep red #e30a17 as the main colors, with small optional off-white #fafaf4 accents. At most three colors.
Background: flat solid near-black #101013, nothing else on the canvas.
Constraints: NO text, NO letters (unless the concept itself is a letter shape), NO words, NO watermark, NO frame or border, NO mockup, NO multiple variants or grids; exactly one mark. Do not imitate any existing company logo. No national flags, crescent-and-star, coats of arms or religious symbols.
"""

for i, (kat, ad, anlam, ipucu) in enumerate(KONSEPT, start=1):
    with open(os.path.join(KOK, "briefs-img", f"{i:03d}.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(SABLON.format(ad=ad, anlam=anlam, ipucu=ipucu))
print("briefs-img:", len(KONSEPT))
