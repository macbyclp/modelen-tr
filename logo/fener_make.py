# -*- coding: utf-8 -*-
"""#049 Fener Zinciri için 8 kompozisyon: eller birbirini tutuyor, her el bir fener taşıyor.
Görsel istemleri (fener/briefs-img/fNN.txt) ve tek SVG hattı brief'i (fener/brief-svg.txt) üretir."""
import os

KOK = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(KOK, "fener")
for alt in ("briefs-img", "img", "svg", "ham"):
    os.makedirs(os.path.join(D, alt), exist_ok=True)

# (ad, kompozisyon)
VARYANT = [
    ("Üç El Zinciri", "Three simplified lanterns in a horizontal row. Each lantern hangs from a chunky hand above it, and the three hands are clearly CLASPED to each other (each hand grips its neighbour's hand), forming one continuous hand-to-hand chain across the top. Each lantern glows with a few short rays."),
    ("Ortada Kenetlenen Eller", "Symmetrical composition: two big chunky hands clasped together in the center (clear interlocked handshake). Each hand also holds a lantern, one hanging on the left and one on the right, mirror image of each other, glowing."),
    ("Halay Halkası", "A circular ring of five chunky hands, each hand gripping the next hand (clearly clasped, like a halay circle). Each hand holds one lantern that hangs outward, like a wreath of lanterns. Bold, centered, radially symmetric."),
    ("Fener Köprüsü", "A row of hands clasped in a continuous arch (like a bridge) with lanterns hanging down from the clasped joints. The clasps between neighbouring hands are clearly visible. Symmetric arch."),
    ("Fenerler Ele Ele", "Three simple lantern characters in a row, WITHOUT faces, each lantern with two stubby arms; neighbouring lanterns hold each other's hands (clasped hands clearly visible between them), so the lanterns themselves are holding hands. Glowing, bold, flat, simple."),
    ("Işığı Devretmek", "Two chunky hands clasped around ONE lantern between them, both hands holding the lantern together (handing the light over). Strong simple symmetrical pictogram with short glow rays."),
    ("Yükselen Zincir", "Three lanterns of increasing size going up diagonally from bottom-left to top-right, each held by a hand, and the hands are clasped to each other along the diagonal chain. Dynamic, progress feeling."),
    ("Rozet", "Circular badge emblem: inside a thick ring, three hands clasped in a triangle formation (each gripping the next), and each hand holds a small lantern pointing outward toward the ring. Centered, symmetrical."),
]

IMG = """$imagegen
TOOL DIRECTIVE: You MUST use the built-in image generation tool (image_gen / gpt-image-2). DO NOT write Python. DO NOT use PIL/Pillow/canvas/sharp/any drawing library. DO NOT generate procedurally with code. If the image generation tool is unavailable, refuse and say so explicitly. Generate exactly ONE image. After generating, reply with only the word DONE.

Size: 1024x1024.

Use case: logo mark for "Modelen", an open-source Turkish AI startup that trains language models together with volunteers (community passing the light hand to hand).
Subject: a single logo MARK (symbol only), concept "Fener Zinciri": lanterns passed along and held hand in hand. The key idea that MUST be clearly readable: hands clasping each other (hand-in-hand), and lanterns being held by those hands. Composition: {kompozisyon}
Rendering of hands and lanterns: very simplified, chunky, geometric pictogram shapes. NO realistic anatomy, NO fingers detail beyond a few thick blocky forms, NO faces. Traditional Turkish street lantern silhouette (a simple lantern with a top cap, a glass body and a base). It must stay readable at 32 pixels: thick shapes, big gaps between parts, minimal detail.
Style: modern minimal flat vector logo design, bold shapes, crisp clean edges, no gradients, no shadows, no 3D, no texture, professional brand identity mark.
Palette: brand red #ff4640 and deep red #e30a17 as the main colors, small off-white #fafaf4 accents for the lantern glass or glow. At most three colors.
Background: flat solid near-black #101013, nothing else on the canvas.
Constraints: NO text, NO letters, NO watermark, NO frame, NO mockup, NO multiple variants or grids; exactly one mark, centered with generous padding. Do not imitate any existing logo.
"""

for i, (ad, komp) in enumerate(VARYANT, start=1):
    with open(os.path.join(D, "briefs-img", f"f{i:02d}.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(IMG.format(kompozisyon=komp))

SVG = """You are a senior logo designer drawing SVG marks for "Modelen", an open-source Turkish AI startup (community-trained models; the community passes the light hand to hand). Draw {n} DIFFERENT logo marks for the concept "Fener Zinciri": lanterns held in hands, and the hands CLASPED to each other (hand-in-hand). The two things that MUST be clearly readable in every mark: (1) hands gripping each other, (2) lanterns held by those hands. One mark per composition below.

HARD RULES for every SVG
- Standalone, well-formed XML starting exactly with: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128">
- Symbol only. NO <text>. No <style>, <script>, <image>, <use>, <filter>, <mask>, <clipPath>, gradients, opacity tricks or external references. Allowed elements: svg, g, path, circle, ellipse, rect, polygon, polyline, line. Explicit fill/stroke attributes (no CSS classes).
- Palette ONLY: #ff4640 (bright red), #e30a17 (deep red), #fafaf4 (off-white), #8a8a96 (gray), #101013 (near-black). At most 3 colors per mark. Transparent background (no background rectangle). The essential silhouette must be red (#ff4640 or #e30a17); off-white only for the lantern glass/glow or small details.
- Bold, geometric, flat pictogram. Hands are chunky simplified shapes (no fingers detail beyond a few thick blocky forms), lanterns are simple traditional street lanterns (cap, glass body, base). Recognisable at 24x24 px: minimum stroke width 6 units on the 128 grid, minimum gap 4 units, no hairlines. 8-unit margin, centered.
- No faces. No flags, crescent-and-star, religious symbols, real people, or copies of existing logos.
- Each SVG under 2200 bytes.

Work method: for each composition decide the construction on the 128x128 grid, check that clasped hands and lanterns are both legible, then write the SVG. Do not write files or run commands; just answer.

OUTPUT FORMAT (final message contains ONLY these blocks, no prose, no markdown fences, one per composition, using the given id, in order):
<<<LOGO f01>>>
<svg ...>...</svg>
<<<END>>>

COMPOSITIONS (id | name | description)
"""
satirlar = "\n".join(f"f{i:02d} | {ad} | {komp}" for i, (ad, komp) in enumerate(VARYANT, start=1))
with open(os.path.join(D, "brief-svg.txt"), "w", encoding="utf-8", newline="\n") as f:
    f.write(SVG.format(n=len(VARYANT)) + satirlar + "\n")
print("hazır:", len(VARYANT), "görsel istemi + 1 SVG brief'i")
