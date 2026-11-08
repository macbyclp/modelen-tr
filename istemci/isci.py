"""Modelen gönüllü işçisi (prototip).

GPU'yu algılar, koordinatörden küresel adaptörü alır, H yerel adım eğitir, güncel adaptörü geri yollar.
Yalnızca LoRA adaptörü (~40 MB) ağa çıkar; taban model ve veri yerelde kalır.

  python istemci/isci.py --koordinator http://127.0.0.1:8750 --isci ali-laptop
"""
import argparse
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request

import torch

sys.path.insert(0, os.path.dirname(__file__))
import ortak  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--koordinator", default="http://127.0.0.1:8750")
ap.add_argument("--isci", default="isci-1", help="gönüllü takma adı (kişisel veri girmeyin)")
ap.add_argument("--model", default="models/qwen3-0.6b-base")
ap.add_argument("--veri", default="data/tok-wiki30.pt", help="belirteçlenmiş eğitim verisi (prototip: yerel dosya)")
ap.add_argument("--sft-veri", default="data/sft-oasst2.pt", help="talimat (SFT) verisi: istemci/sft_veri.py çıktısı; yalnızca görev mod=sft ise kullanılır")
ap.add_argument("--anahtar", default="")
ap.add_argument("--en-cok-tur", type=int, default=0, help="0 = bitene kadar")
ap.add_argument("--bekleme", type=float, default=3.0)
A = ap.parse_args()


def istek(yol, veri=None):
    r = urllib.request.Request(A.koordinator + yol, data=veri, method="POST" if veri is not None else "GET")
    if A.anahtar:
        r.add_header("X-Anahtar", A.anahtar)
    with urllib.request.urlopen(r, timeout=600) as y:
        return y.read(), y.headers


def gorev():
    b, _ = istek(f"/gorev?isci={A.isci}")
    return json.loads(b)


def donanim():
    if not torch.cuda.is_available():
        return {"gpu": None}
    p = torch.cuda.get_device_properties(0)
    return {"gpu": p.name, "vram_gb": round(p.total_memory / 1e9, 1)}


def _yanitli_pencere(etiket, seq, rng, deneme=200):
    for _ in range(deneme):
        i = rng.randrange(0, len(etiket) - seq - 1)
        if (etiket[i:i + seq] != -100).any():
            return i
    raise RuntimeError("yanıt belirteci içeren pencere bulunamadı; SFT verisini kontrol edin")


def main():
    if not torch.cuda.is_available():
        print("CUDA GPU bulunamadı; prototip işçi GPU gerektirir.", file=sys.stderr)
        sys.exit(2)
    print(f"[işçi {A.isci}] donanım: {donanim()}", flush=True)
    g = gorev()
    veri_onbellek = {}

    def veri_al(mod):
        """mod=cpt: düz belirteç dizisi (kayıp her yerde). mod=sft: (ids, etiket) — kayıp yalnızca yanıt belirteçlerinde."""
        if mod not in veri_onbellek:
            if mod == "sft":
                d = torch.load(A.sft_veri)
                veri_onbellek[mod] = (d["ids"], d["etiket"])
            else:
                ids_ = torch.load(A.veri)
                veri_onbellek[mod] = (ids_, ids_)
        return veri_onbellek[mod]
    while g.get("bekle") or not g.get("bitti"):
        if g.get("bekle"):
            time.sleep(A.bekleme)
            g = gorev()
            continue
        break
    if g.get("bitti"):
        print("eğitim zaten bitmiş")
        return
    m = ortak.yeni_model(A.model, g["tohum"], "cuda")
    params = [p for p in m.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=g["lr"], weight_decay=0.0, betas=(0.9, 0.95))
    yapilan = 0
    while True:
        if g.get("bitti"):
            print(f"[işçi {A.isci}] eğitim tamamlandı")
            break
        if g.get("bekle"):
            time.sleep(A.bekleme)
            g = gorev()
            continue
        t0 = time.time()
        veri, _ = istek("/agirlik")
        if ortak.ozet(veri) != g["agirlik_sha256"]:
            g = gorev()  # tur arada ilerledi
            continue
        ortak.adaptor_yaz(m, ortak.bayttan(veri))
        mod = g.get("mod", "cpt")
        ids, etiketler = veri_al(mod)
        n = len(ids) // g["n_parca"]
        dilim = ids[g["parca"] * n:(g["parca"] + 1) * n]
        etiket_dilim = etiketler[g["parca"] * n:(g["parca"] + 1) * n]
        rng = random.Random(f"{A.isci}-{g['tur']}")
        H = g["ic_adim"]
        toplam = g["toplam_tur"] * H
        for s in range(H):
            for gr in opt.param_groups:
                gr["lr"] = ortak.lr_at(g["lr"], g["tur"] * H + s, toplam)
            ix = [rng.randrange(0, len(dilim) - g["seq"] - 1) for _ in range(g["bs"])]
            if mod == "sft":  # yanıt belirteci içermeyen pencereleri atla (kayıp tanımsız olur)
                ix = [i if (etiket_dilim[i:i + g["seq"]] != -100).any() else _yanitli_pencere(etiket_dilim, g["seq"], rng) for i in ix]
            x = torch.stack([dilim[i:i + g["seq"]] for i in ix]).cuda()
            y = torch.stack([etiket_dilim[i:i + g["seq"]] for i in ix]).cuda()
            m(input_ids=x, labels=y).loss.backward()
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step()
            opt.zero_grad(set_to_none=True)
        gonder = ortak.bayta(ortak.adaptor_al(m))
        try:
            b, _ = istek(f"/sonuc?isci={A.isci}&tur={g['tur']}", gonder)
            print(f"[işçi {A.isci}] tur {g['tur']} {H} adım, {time.time() - t0:.0f} sn, yük {len(gonder) / 1e6:.1f} MB -> {b.decode()}", flush=True)
        except urllib.error.HTTPError as e:
            print(f"[işçi {A.isci}] tur {g['tur']} reddedildi: {e.code} {e.read().decode()}", flush=True)
        yapilan += 1
        if A.en_cok_tur and yapilan >= A.en_cok_tur:
            break
        g = gorev()


if __name__ == "__main__":
    main()
