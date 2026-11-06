"""TurkishMMLU (AYueksel/TurkishMMLU) 5-shot ölçümü: harf olasılığına göre doğruluk.

Kullanım: python olc_mmlu.py MODEL_DIZINI [ADAPTOR_DIZINI]
Her konu için dev bölümündeki ilk 5 soru örnek, test bölümündeki tüm sorular ölçülür.
"""
import glob
import json
import os
import sys

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

model_dir = sys.argv[1]
adapter = sys.argv[2] if len(sys.argv) > 2 else None
KOK = "data/olcum/turkishmmlu"
HARF = "ABCDE"

tok = AutoTokenizer.from_pretrained(model_dir)
model = AutoModelForCausalLM.from_pretrained(model_dir, dtype=torch.bfloat16).cuda().eval()
if adapter:
    from peft import PeftModel
    model = PeftModel.from_pretrained(model, adapter).eval()
harf_id = [tok(" " + h, add_special_tokens=False)["input_ids"][-1] for h in HARF]


def blok(s, cevap=None):
    t = f"Soru: {s['question']}\n"
    for h, c in zip(HARF, s["choices"]):
        t += f"{h}) {c}\n"
    t += "Cevap:"
    return t + (f" {cevap}\n\n" if cevap else "")


dogru_t = toplam_t = 0
sonuc = {}
for yol in sorted(glob.glob(f"{KOK}/test/*.json")):
    ad = os.path.basename(yol).replace("TurkishMMLU_", "").replace(".json", "")
    test = json.load(open(yol, encoding="utf-8"))
    dev = json.load(open(f"{KOK}/dev/TurkishMMLU_{ad}.json", encoding="utf-8"))[:5]
    ornek = "".join(blok(s, s["answer"]) for s in dev)
    dogru = 0
    for s in test:
        ids = tok(ornek + blok(s), return_tensors="pt").input_ids.cuda()
        with torch.no_grad():
            lg = model(ids).logits[0, -1]
        tahmin = HARF[int(torch.argmax(lg[harf_id]))]
        dogru += tahmin == s["answer"]
    sonuc[ad] = dogru / len(test)
    dogru_t += dogru
    toplam_t += len(test)
    print(f"  {ad:32s} {dogru}/{len(test)} = {dogru / len(test):.3f}", flush=True)
print(f"TURKISHMMLU 5-shot toplam: {dogru_t}/{toplam_t} = {dogru_t / toplam_t:.4f}")
