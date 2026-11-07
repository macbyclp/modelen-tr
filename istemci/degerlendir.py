"""Bir adaptör dosyasının Türkçe Vikipedi ayrık parçasında bayt başına bitini ölçer.

  python istemci/degerlendir.py istemci/calisma/tur-0.safetensors istemci/calisma/tur-3.safetensors
"""
import math
import os
import sys

import pyarrow.parquet as pq
import torch
from transformers import AutoTokenizer

sys.path.insert(0, os.path.dirname(__file__))
import ortak  # noqa: E402

MODEL = "models/qwen3-0.6b-base"
SEQ, TOKEN = 512, 60_000
tok = AutoTokenizer.from_pretrained(MODEL)
pf = pq.ParquetFile("data/wiki-tr/train-00001-of-00002.parquet")
metin = "\n\n".join(pf.read_row_group(pf.num_row_groups - 1, columns=["text"]).to_pydict()["text"])
ev = tok(metin, add_special_tokens=False)["input_ids"][:TOKEN]
bayt = len(tok.decode(ev).encode("utf-8"))
m = ortak.yeni_model(MODEL, 0, "cuda")
m.eval()
for yol in sys.argv[1:]:
    ortak.adaptor_yaz(m, ortak.bayttan(open(yol, "rb").read()))
    top, say = 0.0, 0
    with torch.no_grad():
        for i in range(0, len(ev) - SEQ, SEQ):
            x = torch.tensor([ev[i:i + SEQ]]).cuda()
            lg = m(input_ids=x).logits[0, :-1].float()
            top += torch.nn.functional.cross_entropy(lg, x[0, 1:], reduction="sum").item()
            say += SEQ - 1
    print(f"{yol}: bit/bayt {top / math.log(2) / (bayt * say / len(ev)):.4f}")
