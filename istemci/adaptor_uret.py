"""Başlangıç LoRA adaptörünü MODELSİZ üretir (Qwen3-0.6B-Base biçimi: 392 tensör, ~40,4 MB, float32).

`baslat.py` aynı adaptörü taban modeli yükleyerek üretir; bu betik ise yalnızca belgelenmiş tensör adlarını ve şekillerini kullanır
(bkz. docs.modelen.tr/adaptor-bicimi). Böylece bir koordinatör sunucusunda 1,2 GB'lık modeli indirmeye gerek kalmaz.
Başlatma: PEFT ile aynı (A: Kaiming-düzgün, B: sıfır). Aynı tohum -> aynı adaptör.

  python istemci/adaptor_uret.py --cikti istemci/calisma/tur-0.safetensors [--tohum 0]
"""
import argparse
import math
import os
import sys

import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ortak  # noqa: E402

KATMAN, GIZLI, Q_CIKIS, KV_CIKIS, ARA = 28, 1024, 2048, 1024, 3072
# (blok, modül, giriş, çıkış)
MODULLER = [
    ("self_attn", "q_proj", GIZLI, Q_CIKIS),
    ("self_attn", "k_proj", GIZLI, KV_CIKIS),
    ("self_attn", "v_proj", GIZLI, KV_CIKIS),
    ("self_attn", "o_proj", Q_CIKIS, GIZLI),
    ("mlp", "gate_proj", GIZLI, ARA),
    ("mlp", "up_proj", GIZLI, ARA),
    ("mlp", "down_proj", ARA, GIZLI),
]


def uret(tohum=0):
    g = torch.Generator().manual_seed(tohum)
    r = ortak.LORA_R
    d = {}
    for kat in range(KATMAN):
        for blok, ad, giris, cikis in MODULLER:
            onek = f"base_model.model.model.layers.{kat}.{blok}.{ad}.lora_"
            sinir = 1.0 / math.sqrt(giris)  # kaiming_uniform_(a=sqrt(5)) sınırı: 1/sqrt(fan_in)
            d[onek + "A.default.weight"] = (torch.rand(r, giris, generator=g) * 2 - 1) * sinir
            d[onek + "B.default.weight"] = torch.zeros(cikis, r)
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tohum", type=int, default=0)
    ap.add_argument("--cikti", default="istemci/calisma/tur-0.safetensors")
    a = ap.parse_args()
    veri = ortak.bayta(uret(a.tohum))
    os.makedirs(os.path.dirname(a.cikti) or ".", exist_ok=True)
    with open(a.cikti, "wb") as f:
        f.write(veri)
    print(f"yazıldı {a.cikti}  {len(veri) / 1e6:.1f} MB  sha256={ortak.ozet(veri)[:16]}")


if __name__ == "__main__":
    main()
