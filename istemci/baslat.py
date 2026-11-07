"""Başlangıç adaptörünü üretir (tohumdan, CPU'da): koordinatör bununla açılır.

  python istemci/baslat.py --model models/qwen3-0.6b-base --tohum 0 --cikti istemci/calisma/tur-0.safetensors
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import ortak  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--model", default="models/qwen3-0.6b-base")
ap.add_argument("--tohum", type=int, default=0)
ap.add_argument("--cikti", default="istemci/calisma/tur-0.safetensors")
a = ap.parse_args()

m = ortak.yeni_model(a.model, a.tohum, cihaz="cpu")
veri = ortak.bayta(ortak.adaptor_al(m))
os.makedirs(os.path.dirname(a.cikti) or ".", exist_ok=True)
open(a.cikti, "wb").write(veri)
print(f"yazıldı {a.cikti}  {len(veri) / 1e6:.1f} MB  sha256={ortak.ozet(veri)[:16]}")
