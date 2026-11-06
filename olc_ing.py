"""İngilizce unutma ölçümü: WikiText-2 (raw) test bölümünde bayt başına bit.

Kullanım: python olc_ing.py MODEL_DIZINI [ADAPTOR_DIZINI]
"""
import math
import sys

import pyarrow.parquet as pq
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

model_dir = sys.argv[1]
adapter = sys.argv[2] if len(sys.argv) > 2 else None
BLOK, MAX_TOKEN = 512, 200_000

tok = AutoTokenizer.from_pretrained(model_dir)
model = AutoModelForCausalLM.from_pretrained(model_dir, dtype=torch.bfloat16).cuda().eval()
if adapter:
    from peft import PeftModel
    model = PeftModel.from_pretrained(model, adapter).eval()

satirlar = pq.read_table("data/olcum/wikitext/wikitext-2-raw-v1/test-00000-of-00001.parquet").to_pydict()["text"]
metin = "".join(satirlar)
ids = tok(metin, add_special_tokens=False)["input_ids"][:MAX_TOKEN]
kesik = tok.decode(ids)
n_bayt = len(kesik.encode("utf-8"))
toplam, sayi = 0.0, 0
with torch.no_grad():
    for i in range(0, len(ids) - BLOK, BLOK):
        x = torch.tensor([ids[i:i + BLOK]]).cuda()
        logits = model(x).logits[0, :-1].float()
        toplam += torch.nn.functional.cross_entropy(logits, x[0, 1:], reduction="sum").item()
        sayi += BLOK - 1
bayt_olcu = n_bayt * sayi / len(ids)
print(f"INGILIZCE token={len(ids)} kayıp={toplam / sayi:.4f} nat ppl={math.exp(toplam / sayi):.2f} "
      f"bayt başına bit={toplam / math.log(2) / bayt_olcu:.4f}")
