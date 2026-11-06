"""Adaptör-DiLoCo: gerçek bir LLM'in (Qwen3-0.6B-Base) LoRA parametreleri üzerinde,
tek GPU'da K sanal gönüllü işçiyle seyrek senkronizasyonlu eğitim simülasyonu.

Taban model dondurulmuş ve işçiler arasında paylaşılır; yalnızca LoRA parametreleri
(~10M, 40 MB fp32) işçiye özgüdür ve senkronizasyonda taşınır.

Modlar:
  baseline : tek optimizer, her adımda K * BS dizilik toplu iş (her adımda senkron).
  diloco   : K işçi, her biri H yerel adım (BS dizi/adım, ayrı Adam durumu, ayrı veri dilimi);
             tur sonunda sözde gradyan (küresel - ortalama) Nesterov momentumlu dış adımla uygulanır.

Aynı işlem miktarı: baseline toplam R*H adım * (K*BS) dizi = diloco K*R*H adım * BS dizi.
Her turdan sonra ayrılmış Türkçe Vikipedi parçasında bayt başına bit ölçülür.
"""
import argparse
import json
import math
import os
import random
import time

import pyarrow.parquet as pq
import torch
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer

ap = argparse.ArgumentParser()
ap.add_argument("--model", default="models/qwen3-0.6b-base")
ap.add_argument("--corpus", default="corpus-wiki-tr-30mb.txt")
ap.add_argument("--mode", choices=["baseline", "diloco", "both"], default="both")
ap.add_argument("--workers", type=int, default=4)
ap.add_argument("--rounds", type=int, default=6)
ap.add_argument("--inner", type=int, default=20)
ap.add_argument("--bs", type=int, default=4)
ap.add_argument("--seq", type=int, default=512)
ap.add_argument("--lr", type=float, default=2e-4)
ap.add_argument("--outer-lr", type=float, default=1.0)
ap.add_argument("--outer-mom", type=float, default=0.5)
ap.add_argument("--eval-tokens", type=int, default=60_000)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--out", default="adaptor-diloco.json")
args = ap.parse_args()

tok = AutoTokenizer.from_pretrained(args.model)

# ---- veri (belirteçler önbelleğe alınır) ----
onbellek = "data/tok-wiki30.pt"
if os.path.exists(onbellek):
    ids = torch.load(onbellek)
else:
    ids = torch.tensor(tok(open(args.corpus, encoding="utf-8").read(), add_special_tokens=False)["input_ids"])
    torch.save(ids, onbellek)
pf = pq.ParquetFile("data/wiki-tr/train-00001-of-00002.parquet")
ev_metin = "\n\n".join(pf.read_row_group(pf.num_row_groups - 1, columns=["text"]).to_pydict()["text"])
ev_ids = tok(ev_metin, add_special_tokens=False)["input_ids"][: args.eval_tokens]
ev_bayt = len(tok.decode(ev_ids).encode("utf-8"))
K = args.workers
dilim = len(ids) // K
shards = [ids[k * dilim:(k + 1) * dilim] for k in range(K)]
print(f"eğitim tokeni={len(ids):,}  değerlendirme tokeni={len(ev_ids):,}", flush=True)


def batch(kaynak, bs, rng):
    ix = [rng.randrange(0, len(kaynak) - args.seq - 1) for _ in range(bs)]
    return torch.stack([kaynak[i:i + args.seq] for i in ix]).cuda()


def yeni_model():
    torch.manual_seed(args.seed)
    m = AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.bfloat16).cuda()
    m.gradient_checkpointing_enable()
    m.enable_input_require_grads()
    cfg = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.0, task_type="CAUSAL_LM",
                     target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"])
    m = get_peft_model(m, cfg)
    m.train()
    return m, [p for p in m.parameters() if p.requires_grad]


@torch.no_grad()
def degerlendir(m):
    m.eval()
    toplam, sayi = 0.0, 0
    for i in range(0, len(ev_ids) - args.seq, args.seq):
        x = torch.tensor([ev_ids[i:i + args.seq]]).cuda()
        lg = m(input_ids=x).logits[0, :-1].float()
        toplam += torch.nn.functional.cross_entropy(lg, x[0, 1:], reduction="sum").item()
        sayi += args.seq - 1
    m.train()
    return toplam / math.log(2) / (ev_bayt * sayi / len(ev_ids))


def lr_at(adim, toplam):
    return args.lr * min(1.0, (adim + 1) / 10) * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * adim / max(1, toplam))))


def adim_at(m, params, opt, kaynak, rng, lr, bs, acc=1):
    for g in opt.param_groups:
        g["lr"] = lr
    for _ in range(acc):
        x = batch(kaynak, bs, rng)
        (m(input_ids=x, labels=x).loss / acc).backward()
    torch.nn.utils.clip_grad_norm_(params, 1.0)
    opt.step()
    opt.zero_grad(set_to_none=True)


sonuc = {"args": vars(args)}
R, H = args.rounds, args.inner
toplam_adim = R * H
n_param = None

if args.mode in ("baseline", "both"):
    m, params = yeni_model()
    n_param = sum(p.numel() for p in params)
    opt = torch.optim.AdamW(params, lr=args.lr, weight_decay=0.0, betas=(0.9, 0.95))
    rng = random.Random(args.seed)
    egri, t0 = [], time.time()
    egri.append({"tur": 0, "bpb": degerlendir(m)})
    print(f"[baseline] tur 0  bit/bayt {egri[-1]['bpb']:.4f}", flush=True)
    for r in range(R):
        for s in range(H):
            adim_at(m, params, opt, ids, rng, lr_at(r * H + s, toplam_adim), args.bs, acc=K)
        egri.append({"tur": r + 1, "bpb": degerlendir(m), "sn": time.time() - t0})
        print(f"[baseline] tur {r + 1}  bit/bayt {egri[-1]['bpb']:.4f}  {time.time() - t0:.0f} sn", flush=True)
    sonuc["baseline"] = egri
    del m, params, opt
    torch.cuda.empty_cache()

if args.mode in ("diloco", "both"):
    m, params = yeni_model()
    n_param = sum(p.numel() for p in params)
    glob = [p.detach().clone() for p in params]
    buf = [torch.zeros_like(p) for p in params]
    opts = [torch.optim.AdamW(params, lr=args.lr, weight_decay=0.0, betas=(0.9, 0.95)) for _ in range(K)]
    rngs = [random.Random(args.seed + 1 + k) for k in range(K)]
    egri, t0 = [], time.time()
    egri.append({"tur": 0, "bpb": degerlendir(m)})
    print(f"[diloco  ] tur 0  bit/bayt {egri[-1]['bpb']:.4f}", flush=True)
    for r in range(R):
        yerel = []
        for k in range(K):
            with torch.no_grad():
                for p, g in zip(params, glob):
                    p.copy_(g)
            for s in range(H):
                adim_at(m, params, opts[k], shards[k], rngs[k], lr_at(r * H + s, toplam_adim), args.bs)
            yerel.append([p.detach().clone() for p in params])
        with torch.no_grad():
            for i, g in enumerate(glob):
                ort = torch.stack([y[i] for y in yerel]).mean(0)
                delta = g - ort
                buf[i].mul_(args.outer_mom).add_(delta)
                g.sub_(args.outer_lr * (delta + args.outer_mom * buf[i]))
            for p, g in zip(params, glob):
                p.copy_(g)
        del yerel
        egri.append({"tur": r + 1, "bpb": degerlendir(m), "sn": time.time() - t0})
        print(f"[diloco  ] tur {r + 1}  bit/bayt {egri[-1]['bpb']:.4f}  {time.time() - t0:.0f} sn", flush=True)
    sonuc["diloco"] = egri

sonuc["lora_parametre"] = n_param
sonuc["adaptor_mb_fp32"] = n_param * 4 / 1e6
sonuc["tepe_vram_gb"] = torch.cuda.max_memory_allocated() / 1e9
json.dump(sonuc, open(args.out, "w", encoding="utf-8"), indent=2)
print(f"yazıldı {args.out}; adaptör={sonuc['adaptor_mb_fp32']:.1f} MB; tepe VRAM {sonuc['tepe_vram_gb']:.2f} GB")
