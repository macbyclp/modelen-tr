"""Talimat (SFT) verisi hazırlama: OpenAssistant/oasst2 (Apache-2.0) -> belirteçlenmiş, yanıt-maskeli veri.

  python istemci/sft_veri.py --diller tr,en --cikti data/sft-oasst2.pt

Çıktı (torch.save): {"ids": LongTensor[N], "etiket": LongTensor[N], "dogrulama_ids", "dogrulama_etiket", "bilgi": {...}}
`etiket`, yalnızca asistan yanıtı belirteçlerinde `ids` ile aynıdır; diğer yerlerde -100 (kayıp hesaplanmaz).
Konuşmalar ChatML biçiminde ve EOS ile ayrılarak art arda paketlenir.
"""
import argparse
import gzip
import json
import os
import random
import sys

ap = argparse.ArgumentParser()
ap.add_argument("--diller", default="tr,en")
ap.add_argument("--model", default="models/qwen3-0.6b-base")
ap.add_argument("--cikti", default="data/sft-oasst2.pt")
ap.add_argument("--en-cok-dil-basina", type=int, default=0, help="0 = sınırsız (örn. en ağırlığını azaltmak için)")
ap.add_argument("--dogrulama-orani", type=float, default=0.05)
ap.add_argument("--tohum", type=int, default=0)
A = ap.parse_args()

from huggingface_hub import hf_hub_download  # noqa: E402
import torch  # noqa: E402
from transformers import AutoTokenizer  # noqa: E402

dosya = hf_hub_download("OpenAssistant/oasst2", "2023-11-05_oasst2_ready.trees.jsonl.gz", repo_type="dataset")
diller = set(A.diller.split(","))


def yollar(dugum, onek):
    """Ağaçtaki her kökten yaprağa konuşma yolu; her adımda en iyi sıralı (rank) yanıtı izle."""
    onek = onek + [dugum]
    cocuklar = [c for c in dugum.get("replies", []) if not c.get("deleted") and c.get("review_result", True) and c.get("text")]
    if not cocuklar:
        return [onek]
    cocuklar.sort(key=lambda c: (c.get("rank") if c.get("rank") is not None else 99))
    return yollar(cocuklar[0], onek)


konusmalar = []
sayac = {}
with gzip.open(dosya, "rt", encoding="utf-8") as f:
    for satir in f:
        agac = json.loads(satir)
        kok = agac["prompt"]
        if kok.get("lang") not in diller or kok.get("deleted") or not kok.get("review_result", True):
            continue
        for yol in yollar(kok, []):
            # prompter, assistant, prompter, assistant ... biçiminde, asistanla biten yol
            if len(yol) < 2 or yol[0].get("role") != "prompter":
                continue
            if yol[-1].get("role") != "assistant":
                yol = yol[:-1]
            if len(yol) < 2:
                continue
            konusmalar.append((kok["lang"], [(d["role"], d["text"]) for d in yol]))
            sayac[kok["lang"]] = sayac.get(kok["lang"], 0) + 1

rng = random.Random(A.tohum)
rng.shuffle(konusmalar)
if A.en_cok_dil_basina:
    tut, kalan = [], {}
    for dil, k in konusmalar:
        if kalan.get(dil, 0) < A.en_cok_dil_basina:
            tut.append((dil, k))
            kalan[dil] = kalan.get(dil, 0) + 1
    konusmalar = tut
print("konuşma sayıları:", {d: sum(1 for x, _ in konusmalar if x == d) for d in diller}, flush=True)

tok = AutoTokenizer.from_pretrained(A.model)
EOS = tok.eos_token_id if tok.eos_token_id is not None else tok.convert_tokens_to_ids("<|endoftext|>")
ROL = {"prompter": "user", "assistant": "assistant"}


def kodla(konusma):
    ids, et = [], []
    for rol, metin in konusma:
        r = ROL[rol]
        bas = tok(f"<|im_start|>{r}\n", add_special_tokens=False)["input_ids"]
        govde = tok(metin.strip() + "<|im_end|>\n", add_special_tokens=False)["input_ids"]
        ids += bas + govde
        et += [-100] * len(bas) + (govde if r == "assistant" else [-100] * len(govde))
    ids.append(EOS)
    et.append(-100)
    return ids, et


n_dog = max(1, int(len(konusmalar) * A.dogrulama_orani))
parcalar = {"egitim": [], "dogrulama": []}
for i, (_, k) in enumerate(konusmalar):
    parcalar["dogrulama" if i < n_dog else "egitim"].append(kodla(k))


def birlestir(liste):
    ids = [t for i, _ in liste for t in i]
    et = [t for _, e in liste for t in e]
    return torch.tensor(ids, dtype=torch.long), torch.tensor(et, dtype=torch.long)


ids, et = birlestir(parcalar["egitim"])
dids, det = birlestir(parcalar["dogrulama"])
bilgi = {"kaynak": "OpenAssistant/oasst2 (Apache-2.0)", "diller": sorted(diller), "konusma": len(konusmalar), "egitim_belirtec": len(ids),
         "yanit_belirteci": int((et != -100).sum()), "dogrulama_belirtec": len(dids), "sablon": "ChatML", "tohum": A.tohum}
os.makedirs(os.path.dirname(A.cikti) or ".", exist_ok=True)
torch.save({"ids": ids, "etiket": et, "dogrulama_ids": dids, "dogrulama_etiket": det, "bilgi": bilgi}, A.cikti)
print(json.dumps(bilgi, ensure_ascii=False, indent=2))
