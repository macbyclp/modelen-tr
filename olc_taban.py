"""Taban ölçümü: Türkçe tokenizer verimi ve ayrılmış Vikipedi metninde bayt başına bit.

Kullanım: python olc_taban.py MODEL_DIZINI [ADAPTOR_DIZINI]

Bayt başına bit (bits per byte), farklı tokenizer'lar arasında karşılaştırılabilir
tek ölçüdür. Değerlendirme metni, eğitim için kullanılan ilk dosyadan DEĞİL,
ikinci parquet dosyasının son satır grubundan alınır (eğitimle örtüşmez).
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

pf = pq.ParquetFile("data/wiki-tr/train-00001-of-00002.parquet")
metinler = pf.read_row_group(pf.num_row_groups - 1, columns=["text"]).to_pydict()["text"]
metin = "\n\n".join(metinler)
ids = tok(metin, add_special_tokens=False)["input_ids"][:MAX_TOKEN]
kesik = tok.decode(ids)
n_bayt = len(kesik.encode("utf-8"))
n_kelime = len(kesik.split())
print(f"token={len(ids)} bayt={n_bayt} kelime={n_kelime}")
print(f"kelime başına token = {len(ids) / n_kelime:.3f}   bayt başına token = {len(ids) / n_bayt:.4f}")

toplam_nll, sayi = 0.0, 0
with torch.no_grad():
    for i in range(0, len(ids) - BLOK, BLOK):
        x = torch.tensor([ids[i:i + BLOK]]).cuda()
        logits = model(x).logits[0, :-1].float()
        nll = torch.nn.functional.cross_entropy(logits, x[0, 1:], reduction="sum")
        toplam_nll += nll.item()
        sayi += BLOK - 1
print(f"token başına kayıp = {toplam_nll / sayi:.4f} nat   perplexity = {math.exp(toplam_nll / sayi):.2f}")
# kaba bayt oranı: ölçülen tokenlerin kapsadığı bayt payı
bayt_olcu = n_bayt * sayi / len(ids)
print(f"bayt başına bit = {toplam_nll / math.log(2) / bayt_olcu:.4f}")
if torch.cuda.is_available():
    print(f"tepe VRAM = {torch.cuda.max_memory_allocated() / 1e9:.2f} GB")
