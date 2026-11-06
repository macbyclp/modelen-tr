"""LoRA ile Türkçe sürekli ön eğitim (kısa koşu). Bellek ve hız ölçümü yapar.

Kullanım: python lora_cpt.py MODEL_DIZINI KORPUS.txt CIKTI_DIZINI [DAKIKA]
"""
import json
import math
import random
import sys
import time

import torch
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer

model_dir, korpus, cikti = sys.argv[1:4]
dakika = float(sys.argv[4]) if len(sys.argv) > 4 else 15.0
SEQ, BS, ACC, LR, RANK = 512, 4, 4, 2e-4, 16

torch.manual_seed(0)
random.seed(0)
tok = AutoTokenizer.from_pretrained(model_dir)
metin = open(korpus, encoding="utf-8").read()
t0 = time.time()
ids = torch.tensor(tok(metin, add_special_tokens=False)["input_ids"])
print(f"token sayısı={len(ids):,} (tokenleştirme {time.time() - t0:.0f} sn)", flush=True)

model = AutoModelForCausalLM.from_pretrained(model_dir, dtype=torch.bfloat16).cuda()
model.gradient_checkpointing_enable()
model.enable_input_require_grads()
cfg = LoraConfig(r=RANK, lora_alpha=2 * RANK, lora_dropout=0.0, task_type="CAUSAL_LM",
                 target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"])
model = get_peft_model(model, cfg)
model.print_trainable_parameters()
params = [p for p in model.parameters() if p.requires_grad]
opt = torch.optim.AdamW(params, lr=LR, weight_decay=0.0, betas=(0.9, 0.95))
model.train()

log, adim, baslangic = [], 0, time.time()
butce = dakika * 60
while time.time() - baslangic < butce:
    ilerleme = min(1.0, (time.time() - baslangic) / butce)
    lr = LR * min(1.0, (adim + 1) / 10) * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * ilerleme)))
    for g in opt.param_groups:
        g["lr"] = lr
    toplam = 0.0
    for _ in range(ACC):
        ix = [random.randrange(0, len(ids) - SEQ - 1) for _ in range(BS)]
        x = torch.stack([ids[i:i + SEQ] for i in ix]).cuda()
        kayip = model(input_ids=x, labels=x).loss / ACC
        kayip.backward()
        toplam += kayip.item()
    torch.nn.utils.clip_grad_norm_(params, 1.0)
    opt.step()
    opt.zero_grad(set_to_none=True)
    adim += 1
    log.append({"adim": adim, "kayip": toplam, "sn": time.time() - baslangic})
    if adim % 10 == 0 or adim == 1:
        print(f"adım {adim:4d}  kayıp {toplam:.4f}  lr {lr:.2e}  {time.time() - baslangic:.0f} sn  "
              f"tepe VRAM {torch.cuda.max_memory_allocated() / 1e9:.2f} GB", flush=True)

model.save_pretrained(cikti)
json.dump({"log": log, "tepe_vram_gb": torch.cuda.max_memory_allocated() / 1e9,
           "token_adim": SEQ * BS * ACC}, open(f"{cikti}/egitim-log.json", "w"))
print(f"kaydedildi: {cikti}  ({adim} adım, {adim * SEQ * BS * ACC:,} token)")
