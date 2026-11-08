"""Belirteçlenmiş eğitim verisini koordinatörün sunabileceği güvenli biçime (safetensors, int32) dönüştürür.

  python istemci/veri_donustur.py data/tok-wiki30.pt data/wiki30.safetensors          # düz belirteç dizisi (cpt)
  python istemci/veri_donustur.py data/sft-oasst2.pt data/sft-oasst2.safetensors      # sft_veri.py çıktısı (ids + etiket)
  python istemci/koordinator.py --baslangic ... --veri data/wiki30.safetensors

Girdi: torch.load ile açılan (YEREL, güvendiğiniz) bir dosya: 1-B tensör ya da {"ids":..., "etiket":...} sözlüğü.
Çıktı: {"ids": int32[N], "etiket": int32[N] (isteğe bağlı)}. Ağdan yalnızca bu biçim dağıtılır; pickle dağıtılmaz.
"""
import sys

import torch
from safetensors.torch import save_file

if len(sys.argv) != 3:
    sys.exit(__doc__)
girdi, cikti = sys.argv[1], sys.argv[2]
d = torch.load(girdi)
if isinstance(d, torch.Tensor):
    t = {"ids": d.to(torch.int32).contiguous()}
elif isinstance(d, dict) and "ids" in d:
    t = {"ids": d["ids"].to(torch.int32).contiguous()}
    if "etiket" in d:
        t["etiket"] = d["etiket"].to(torch.int32).contiguous()
else:
    sys.exit("girdi 1-B tensör ya da {'ids':..., 'etiket':...} sözlüğü olmalı")
save_file(t, cikti)
print(f"yazıldı: {cikti}  {len(t['ids'])} belirteç" + ("  (+etiket)" if "etiket" in t else ""))
