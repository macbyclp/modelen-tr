"""Koordinatör ve işçinin ortak parçaları: model kurulumu, adaptör (de)serileştirme, öğrenme oranı.

Güvenlik: ağdan gelen ağırlıklar yalnızca safetensors ile okunur (pickle yok, kod çalıştırmaz).
"""
import hashlib
import math

import torch
from safetensors.torch import load as st_load
from safetensors.torch import save as st_save

LORA_R = 16
LORA_ALPHA = 32
HEDEF = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]


def yeni_model(model_yolu, tohum, cihaz="cuda"):
    """Taban model (dondurulmuş) + tohumdan belirlenen LoRA. Aynı tohum -> aynı başlangıç adaptörü."""
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM

    torch.manual_seed(tohum)
    dtype = torch.bfloat16 if cihaz == "cuda" else torch.float32
    m = AutoModelForCausalLM.from_pretrained(model_yolu, dtype=dtype).to(cihaz)
    if cihaz == "cuda":
        m.gradient_checkpointing_enable()
        m.enable_input_require_grads()
    cfg = LoraConfig(r=LORA_R, lora_alpha=LORA_ALPHA, lora_dropout=0.0, task_type="CAUSAL_LM", target_modules=HEDEF)
    m = get_peft_model(m, cfg)
    m.train()
    return m


def adaptor_al(m):
    return {n: p.detach().to("cpu", torch.float32).contiguous() for n, p in m.named_parameters() if p.requires_grad}


@torch.no_grad()
def adaptor_yaz(m, durum):
    for n, p in m.named_parameters():
        if p.requires_grad:
            p.copy_(durum[n].to(p.device, p.dtype))


def bayta(durum):
    return st_save(durum)


def bayttan(veri):
    return st_load(veri)


def ozet(veri):
    return hashlib.sha256(veri).hexdigest()


def lr_at(taban_lr, adim, toplam):
    return taban_lr * min(1.0, (adim + 1) / 10) * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * adim / max(1, toplam))))
