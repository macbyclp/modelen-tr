"""SFT adaptörlerini değerlendirir: (1) ayrık doğrulama konuşmalarında yanıt-belirteci kaybı, (2) sabit sorularla örnek üretim.

  python istemci/degerlendir_sft.py tur-0.safetensors tur-3.safetensors [--veri data/sft-oasst2.pt] [--pencere 80]

Kayıp yalnızca asistan yanıtı belirteçlerinde hesaplanır (düşük iyidir). Üretim açgözlü (greedy), kısa; nitel bir işarettir, ölçüt değildir.
"""
import argparse
import math
import os
import sys

import torch
from transformers import AutoTokenizer

sys.path.insert(0, os.path.dirname(__file__))
import ortak  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("adaptorler", nargs="+")
ap.add_argument("--model", default="models/qwen3-0.6b-base")
ap.add_argument("--veri", default="data/sft-oasst2.pt")
ap.add_argument("--seq", type=int, default=512)
ap.add_argument("--pencere", type=int, default=80)
ap.add_argument("--uretim", type=int, default=1, help="1 = örnek üretimleri de yazdır")
A = ap.parse_args()

SORULAR = [
    "What is the capital of France? Answer in one sentence.",
    "Write a short Python function that returns the n-th Fibonacci number.",
    "Türkiye'nin başkenti neresidir? Tek cümleyle cevap ver.",
    "Bir takımın dört oyuncusu var, her biri iki gol attı. Toplam kaç gol atıldı? Kısaca açıkla.",
]

tok = AutoTokenizer.from_pretrained(A.model)
d = torch.load(A.veri)
ids, et = d["dogrulama_ids"], d["dogrulama_etiket"]
m = ortak.yeni_model(A.model, 0, "cuda")
m.eval()
adim = max(1, (len(ids) - A.seq - 1) // A.pencere)
pencereler = [i for i in range(0, len(ids) - A.seq - 1, adim) if (et[i:i + A.seq] != -100).any()][: A.pencere]

for yol in A.adaptorler:
    ortak.adaptor_yaz(m, ortak.bayttan(open(yol, "rb").read()))
    top, say = 0.0, 0
    with torch.no_grad():
        for i in pencereler:
            x = ids[i:i + A.seq].unsqueeze(0).cuda()
            y = et[i:i + A.seq].unsqueeze(0).cuda()
            lg = m(input_ids=x).logits[0, :-1].float()
            hedef = y[0, 1:]
            gecerli = hedef != -100
            top += torch.nn.functional.cross_entropy(lg[gecerli], hedef[gecerli], reduction="sum").item()
            say += int(gecerli.sum())
    print(f"{os.path.basename(os.path.dirname(yol))}/{os.path.basename(yol)}: yanıt kaybı {top / say:.4f}  (ppl {math.exp(top / say):.2f}, {say} belirteç, {len(pencereler)} pencere)", flush=True)
    if A.uretim:
        for q in SORULAR:
            istem = f"<|im_start|>user\n{q}<|im_end|>\n<|im_start|>assistant\n"
            x = tok(istem, return_tensors="pt", add_special_tokens=False)["input_ids"].cuda()
            with torch.no_grad():
                o = m.generate(input_ids=x, max_new_tokens=70, do_sample=False, repetition_penalty=1.1, pad_token_id=tok.eos_token_id)
            yanit = tok.decode(o[0, x.shape[1]:], skip_special_tokens=False).split("<|im_end|>")[0].strip().replace("\n", " ")
            print(f"    S: {q}\n    C: {yanit[:260]}", flush=True)
