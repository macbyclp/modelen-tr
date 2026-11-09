"""Metin dosyalarından koordinatörün sunacağı belirteçlenmiş eğitim verisini (safetensors, int32) üretir.

  python istemci/veri_hazirla.py --girdi metinler/ --cikti veri.safetensors
  python istemci/veri_hazirla.py --girdi a.txt --girdi b.jsonl --cikti veri.safetensors --en-cok-belirtec 20000000

Girdi: .txt, .md (her dosya bir belge) ya da .jsonl (her satırda {"text": "..."}); klasör verilirse içindekiler taranır.
Belirteçleme TABAN MODELİN belirteçleyicisiyle yapılır (varsayılan Qwen/Qwen3-0.6B-Base; yalnızca belirteçleyici dosyaları indirilir, ~10 MB).
Belgeler arasına bitiş belirteci (EOS) konur. Çıktı doğrudan `koordinator.py --veri` ile sunulur.

SORUMLULUK: Verinin kaynağı, lisansı ve içeriği koordinatörün sorumluluğundadır; Modelen veri sağlamaz ve seçmez.
"""
import argparse
import json
import os
import sys

TURLER = (".txt", ".md", ".jsonl")


def dosyalar(girdiler):
    for g in girdiler:
        if os.path.isdir(g):
            for kok, _, fs in os.walk(g):
                for f in sorted(fs):
                    if f.lower().endswith(TURLER):
                        yield os.path.join(kok, f)
        elif os.path.isfile(g):
            yield g
        else:
            sys.exit(f"girdi bulunamadı: {g}")


def belgeler(yol):
    """Dosyadan belge metinlerini üretir (büyük dosyalar satır grupları halinde)."""
    if yol.lower().endswith(".jsonl"):
        with open(yol, encoding="utf-8", errors="replace") as f:
            for n, satir in enumerate(f, 1):
                satir = satir.strip()
                if not satir:
                    continue
                try:
                    t = json.loads(satir).get("text", "")
                except (ValueError, AttributeError):
                    sys.exit(f"{yol}:{n} geçerli JSON değil")
                if t:
                    yield t
        return
    with open(yol, encoding="utf-8", errors="replace") as f:
        blok, boyut = [], 0
        for satir in f:
            blok.append(satir)
            boyut += len(satir)
            if boyut > 2_000_000:  # ~2 MB'lık parçalar; parça sınırında belge bölünmüş sayılmaz (EOS yalnızca dosya sonunda)
                yield "".join(blok)
                blok, boyut = [], 0
        if blok:
            yield "".join(blok)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--girdi", action="append", required=True, help="dosya ya da klasör; birden çok kez verilebilir")
    ap.add_argument("--cikti", required=True)
    ap.add_argument("--belirtecleyici", default="Qwen/Qwen3-0.6B-Base", help="taban modelin belirteçleyicisi (HF adı ya da yerel klasör)")
    ap.add_argument("--en-cok-belirtec", type=int, default=0, help="0 = sınırsız")
    ap.add_argument("--en-az-belirtec", type=int, default=4 * 514, help="parca(4) x (seq 512 + 2) altındaysa uyarır")
    a = ap.parse_args()

    import torch
    from safetensors.torch import save_file
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(a.belirtecleyici)
    eos = tok.eos_token_id if tok.eos_token_id is not None else tok.convert_tokens_to_ids("<|endoftext|>")
    ids, n_belge, toplam = [], 0, 0
    liste = list(dosyalar(a.girdi))
    if not liste:
        sys.exit("girdide .txt, .md ya da .jsonl dosyası yok")
    for yol in liste:
        sayac = 0
        for metin in belgeler(yol):
            ids.extend(tok(metin, add_special_tokens=False)["input_ids"])
            sayac += 1
            n_belge += 1
            if a.en_cok_belirtec and len(ids) >= a.en_cok_belirtec:
                break
        ids.append(eos)  # dosya/belge sonu
        toplam = len(ids)
        print(f"  {yol}: {sayac} parça, toplam {toplam} belirteç", flush=True)
        if a.en_cok_belirtec and toplam >= a.en_cok_belirtec:
            ids = ids[: a.en_cok_belirtec]
            print(f"  belirteç sınırına ulaşıldı ({a.en_cok_belirtec})", flush=True)
            break
    if len(ids) < a.en_az_belirtec:
        print(f"UYARI: yalnızca {len(ids)} belirteç var; koordinatör için en az ~{a.en_az_belirtec} gerekir (parca sayısı x (seq+2)). Daha çok metin ekleyin.", file=sys.stderr)
    t = torch.tensor(ids, dtype=torch.int32)
    os.makedirs(os.path.dirname(a.cikti) or ".", exist_ok=True)
    save_file({"ids": t}, a.cikti)
    print(f"yazıldı {a.cikti}: {len(ids)} belirteç ({len(ids) * 4 / 1e6:.1f} MB), {len(liste)} dosya")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
