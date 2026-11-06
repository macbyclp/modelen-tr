"""Türkçe Vikipedi parquet dosyalarından düz metin korpusu üretir.

Kullanım: python wiki_to_txt.py ÇIKTI.txt [HEDEF_MB]
Makaleler başlıkla birlikte, boş satırla ayrılmış yazılır. Veri CC BY-SA 3.0 / GFDL
lisanslı Vikipedi'dendir; dağıtılırsa atıf ve aynı lisans gerekir.
"""
import glob
import sys

import pyarrow.parquet as pq

out = sys.argv[1]
hedef = int(sys.argv[2]) * 1_000_000 if len(sys.argv) > 2 else None
yazilan = makale = 0
with open(out, "w", encoding="utf-8") as f:
    for yol in sorted(glob.glob("data/wiki-tr/*.parquet")):
        pf = pq.ParquetFile(yol)
        for grup in range(pf.num_row_groups):
            tablo = pf.read_row_group(grup, columns=["title", "text"]).to_pydict()
            for baslik, metin in zip(tablo["title"], tablo["text"]):
                blok = f"{baslik}\n{metin}\n\n"
                f.write(blok)
                yazilan += len(blok.encode("utf-8"))
                makale += 1
                if hedef and yazilan >= hedef:
                    print(f"{makale} makale, {yazilan / 1e6:.1f} MB (hedefte durdu)")
                    sys.exit(0)
print(f"{makale} makale, {yazilan / 1e6:.1f} MB")
