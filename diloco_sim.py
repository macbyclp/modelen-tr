"""modelen: DiLoCo benzeri seyrek senkronizasyonlu dağıtık eğitimin tek-GPU simülasyonu.

Amaç: gönüllü ağını kurmadan önce "seyrek senkronizasyon, tek makineli eğitimle
aynı kayıp eğrisine yaklaşıyor mu?" sorusunu küçük bir modelle ölçmek.

Modlar:
  baseline : tek işçi, her adımda güncelleme (referans).
  diloco   : K sanal işçi, her biri H yerel adım atar; sonra "sözde gradyan"
             (global ağırlık - ortalama yerel ağırlık) Nesterov momentumlu
             dış optimizeyle uygulanır.

Veri: --data ile verilen UTF-8 metin dosyası (bayt düzeyinde tokenleştirme).
Dosya yoksa yalnızca duman testi için sentetik Türkçe cümle üretilir; sentetik
veriyle elde edilen kayıp değerleri bir şey kanıtlamaz.

Her işçi farklı bir veri dilimini görür (gönüllülerin ayrı veri parçaları
işlediği durumu taklit eder).
"""
import argparse
import copy
import json
import math
import random
import time

import torch
import torch.nn as nn
import torch.nn.functional as F


# ---------- veri ----------
def synth_text(n_chars: int, seed: int = 0) -> str:
    rng = random.Random(seed)
    ozne = ["ben", "sen", "o", "biz", "siz", "onlar", "kedi", "çocuk", "öğretmen"]
    nesne = ["kitabı", "elmayı", "arabayı", "evi", "mektubu", "suyu", "yemeği"]
    fiil = ["okudu", "aldı", "gördü", "yedi", "açtı", "buldu", "getirdi"]
    zarf = ["bugün", "dün", "yarın", "sabah", "akşam", "hızlıca", "sessizce"]
    out, size = [], 0
    while size < n_chars:
        s = f"{rng.choice(zarf)} {rng.choice(ozne)} {rng.choice(nesne)} {rng.choice(fiil)}. "
        out.append(s)
        size += len(s)
    return "".join(out)


def load_data(path):
    if path:
        text = open(path, encoding="utf-8", errors="ignore").read()
        src = path
    else:
        text = synth_text(2_000_000)
        src = "SENTETIK (yalnızca duman testi)"
    data = torch.frombuffer(bytearray(text.encode("utf-8")), dtype=torch.uint8).long()
    return data, src


def make_batch(shard, block, bs, gen, device):
    ix = torch.randint(0, len(shard) - block - 1, (bs,), generator=gen)
    x = torch.stack([shard[i:i + block] for i in ix]).to(device)
    y = torch.stack([shard[i + 1:i + block + 1] for i in ix]).to(device)
    return x, y


# ---------- model (küçük GPT) ----------
class Block(nn.Module):
    def __init__(self, d, h):
        super().__init__()
        self.h = h
        self.ln1 = nn.LayerNorm(d)
        self.qkv = nn.Linear(d, 3 * d, bias=False)
        self.proj = nn.Linear(d, d, bias=False)
        self.ln2 = nn.LayerNorm(d)
        self.mlp = nn.Sequential(nn.Linear(d, 4 * d, bias=False), nn.GELU(),
                                 nn.Linear(4 * d, d, bias=False))

    def forward(self, x):
        b, t, d = x.shape
        q, k, v = self.qkv(self.ln1(x)).chunk(3, dim=-1)
        q, k, v = (z.view(b, t, self.h, d // self.h).transpose(1, 2) for z in (q, k, v))
        a = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        x = x + self.proj(a.transpose(1, 2).reshape(b, t, d))
        return x + self.mlp(self.ln2(x))


class GPT(nn.Module):
    def __init__(self, vocab=256, block=128, d=256, layers=4, heads=4):
        super().__init__()
        self.tok = nn.Embedding(vocab, d)
        self.pos = nn.Embedding(block, d)
        self.blocks = nn.ModuleList(Block(d, heads) for _ in range(layers))
        self.ln = nn.LayerNorm(d)
        self.head = nn.Linear(d, vocab, bias=False)

    def forward(self, x, y=None):
        t = x.shape[1]
        h = self.tok(x) + self.pos(torch.arange(t, device=x.device))
        for b in self.blocks:
            h = b(h)
        logits = self.head(self.ln(h))
        loss = F.cross_entropy(logits.view(-1, logits.size(-1)), y.view(-1)) if y is not None else None
        return logits, loss


# ---------- yardımcılar ----------
@torch.no_grad()
def evaluate(model, val, args, device, gen):
    model.eval()
    losses = []
    for _ in range(args.eval_batches):
        x, y = make_batch(val, args.block, args.bs, gen, device)
        losses.append(model(x, y)[1].item())
    model.train()
    return sum(losses) / len(losses)


def lr_at(step, total, base, warmup):
    if step < warmup:
        return base * (step + 1) / warmup
    p = (step - warmup) / max(1, total - warmup)
    return base * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * p)))


def build(args, device):
    return GPT(block=args.block, d=args.dim, layers=args.layers, heads=args.heads).to(device)


# ---------- koşular ----------
def run_baseline(args, shards, val, device):
    torch.manual_seed(args.seed)
    model = build(args, device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01, betas=(0.9, 0.95))
    gen = torch.Generator().manual_seed(args.seed)
    egen = torch.Generator().manual_seed(999)
    curve, total = [], args.rounds * args.inner
    # taban çizgi, DiLoCo ile aynı işlem miktarını görsün: K işçi * toplam adım
    # toplu iş boyutunu K ile çarpmak yerine adım sayısını K ile çarpmak yerine
    # eşit "token" için bs'yi K katına çıkarıyoruz.
    eff_bs = args.bs * args.workers
    full = torch.cat(shards)
    for step in range(total):
        for g in opt.param_groups:
            g["lr"] = lr_at(step, total, args.lr, args.warmup)
        x, y = make_batch(full, args.block, eff_bs, gen, device)
        _, loss = model(x, y)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        if (step + 1) % args.inner == 0:
            v = evaluate(model, val, args, device, egen)
            curve.append({"round": (step + 1) // args.inner, "step": step + 1, "val_loss": v})
            print(f"[baseline] tur {(step + 1) // args.inner:3d}  val_loss {v:.4f}", flush=True)
    return curve


def run_diloco(args, shards, val, device):
    torch.manual_seed(args.seed)
    glob = build(args, device)  # küresel (sunucudaki) ağırlıklar
    outer_buf = [torch.zeros_like(p) for p in glob.parameters()]
    gens = [torch.Generator().manual_seed(args.seed + 1 + k) for k in range(args.workers)]
    egen = torch.Generator().manual_seed(999)
    curve = []
    # her işçinin kendi AdamW durumu var (yerel kalır, paylaşılmaz)
    workers = [build(args, device) for _ in range(args.workers)]
    opts = [torch.optim.AdamW(w.parameters(), lr=args.lr, weight_decay=0.01, betas=(0.9, 0.95))
            for w in workers]
    total = args.rounds * args.inner
    step = 0
    for r in range(args.rounds):
        for w in workers:
            w.load_state_dict(glob.state_dict())
        for k, (w, opt) in enumerate(zip(workers, opts)):
            for s in range(args.inner):
                for g in opt.param_groups:
                    g["lr"] = lr_at(r * args.inner + s, total, args.lr, args.warmup)
                x, y = make_batch(shards[k], args.block, args.bs, gens[k], device)
                _, loss = w(x, y)
                opt.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(w.parameters(), 1.0)
                opt.step()
        # dış adım: sözde gradyan = küresel - ortalama(yerel)
        with torch.no_grad():
            for i, gp in enumerate(glob.parameters()):
                avg = torch.stack([list(w.parameters())[i] for w in workers]).mean(0)
                delta = gp - avg
                outer_buf[i].mul_(args.outer_mom).add_(delta)
                update = delta + args.outer_mom * outer_buf[i]  # Nesterov
                gp.sub_(args.outer_lr * update)
        step += args.inner
        v = evaluate(glob, val, args, device, egen)
        curve.append({"round": r + 1, "step": step, "val_loss": v})
        print(f"[diloco  ] tur {r + 1:3d}  val_loss {v:.4f}", flush=True)
    return curve


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["baseline", "diloco", "both"], default="both")
    ap.add_argument("--data", default=None, help="UTF-8 metin dosyası")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--rounds", type=int, default=20)
    ap.add_argument("--inner", type=int, default=50, help="H: iki senkronizasyon arası yerel adım")
    ap.add_argument("--bs", type=int, default=16)
    ap.add_argument("--block", type=int, default=128)
    ap.add_argument("--dim", type=int, default=256)
    ap.add_argument("--layers", type=int, default=4)
    ap.add_argument("--heads", type=int, default=4)
    ap.add_argument("--lr", type=float, default=3e-3)
    ap.add_argument("--warmup", type=int, default=50)
    ap.add_argument("--outer-lr", type=float, default=0.7)
    ap.add_argument("--outer-mom", type=float, default=0.9)
    ap.add_argument("--eval-batches", type=int, default=20)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="sonuc.json")
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    data, src = load_data(args.data)
    n = len(data)
    val, train = data[: n // 20], data[n // 20:]
    shard_len = len(train) // args.workers
    shards = [train[k * shard_len:(k + 1) * shard_len] for k in range(args.workers)]
    n_params = sum(p.numel() for p in build(args, "cpu").parameters())
    print(f"cihaz={device} veri={src} bayt={n} işçi={args.workers} parametre={n_params / 1e6:.2f}M", flush=True)

    result = {"args": vars(args), "data": src, "params_m": n_params / 1e6}
    t0 = time.time()
    if args.mode in ("baseline", "both"):
        result["baseline"] = run_baseline(args, shards, val, device)
    if args.mode in ("diloco", "both"):
        result["diloco"] = run_diloco(args, shards, val, device)
    result["seconds"] = time.time() - t0
    json.dump(result, open(args.out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"yazıldı: {args.out}  ({result['seconds']:.0f} sn)")


if __name__ == "__main__":
    main()
