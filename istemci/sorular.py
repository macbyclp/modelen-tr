"""Topluluktan gelen soruları listeler (koordinatörün yazdığı calisma/sorular.jsonl).

  python istemci/sorular.py [--calisma istemci/calisma]
"""
import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ap = argparse.ArgumentParser()
ap.add_argument("--calisma", default="istemci/calisma")
a = ap.parse_args()
yol = os.path.join(a.calisma, "sorular.jsonl")
if not os.path.exists(yol):
    print("Henüz soru yok.")
    raise SystemExit
for satir in open(yol, encoding="utf-8"):
    d = json.loads(satir)
    print(f"#{d['no']}  {d['zaman']}  ({d.get('isci') or 'adsız'}, v{d.get('surum', '?')})")
    print("  " + d["soru"].replace("\n", "\n  "))
    if d.get("baglam"):
        print(f"  [+ bağlam: {len(d['baglam'])} karakter]")
    print()
