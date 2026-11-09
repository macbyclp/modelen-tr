# Adaptation path: adapting an open base model to Turkish

[Türkçe](ADAPTASYON.md) · **English**

Decision (user statement, 2026-11-06): the first model will not be trained from scratch; it will be a Turkish adaptation of an open base model.

## Why this path

- Training a 1B model from scratch on a single 8 GB GPU would take months and would not fit. Adaptation with LoRA/QLoRA fits in 8 GB (rough estimate for 1–3B: 4–6 GB; sources are secondary, we will measure ourselves).
- Turkish instruction tuning is crowded (see the README). Separating Turkish language acquisition (continued pre-training) from task alignment is the framework suggested by the MODA work ([SIGTURK 2026](https://aclanthology.org/2026.sigturk-1.17.pdf)).

## Base model candidates

| Candidate | Size | License | Note |
|---|---|---|---|
| **Qwen/Qwen3-0.6B-Base** | 596M, BF16 ≈ 1.2 GB | Apache-2.0 (verified from the model card) | First choice for a fast loop |
| Qwen/Qwen3-1.7B-Base | ~1.7B, ≈ 3.4 GB (estimate) | Apache-2.0 (verified from the model card) | Closest to the real "~1B" target |
| Gemma 3 1B | ~1B | Google Gemma terms, not Apache | License terms must be read separately |
| SmolLM3-3B, MiniCPM5-2B | 2–3B | Said to be Apache-2.0, not verified | Tight for 8 GB; later |

Recommendation: build the pipeline with 0.6B, then move to 1.7B.

## Method

1. **Base measurement:** before adapting, measure the base with Turkish perplexity (a held-out Wikipedia slice) and benchmarks such as TurkishMMLU / TR-MMLU. Without a benchmark we cannot say "it improved".
2. **Tokenizer:** first measure the base's tokens per word in Turkish. Extending the vocabulary is risky and needs extra training; do not extend it unless the measurement is bad.
3. **Continued pre-training (LoRA/QLoRA):** start with Turkish Wikipedia (which we have), then the FineWeb2 `tur_Latn` subset. To limit forgetting, add English / multilingual replay data to the mix; the "Hamza" work reports that accuracy in the original language drops during Turkish continued pre-training (catastrophic forgetting).
4. **Evaluation:** before/after with the same tests, plus an English test to check forgetting.
5. **Task alignment** is a separate, later step.

## Link to the volunteer network (hypothesis, not proven)

LoRA adapters contain only a small fraction of the base model's parameters. This can lighten two things at once: the VRAM requirement of a volunteer GPU (the base is frozen, only the adapter is trained) and the amount of data carried in DiLoCo synchronisation. Next simulation: run DiLoCo on the adapter parameters only.

Risk: one study reports that weights pre-trained with DiLoCo may later be incompatible with standard DDP training ([arXiv 2511.13761](https://arxiv.org/abs/2511.13761)); whether this holds at adapter scale is unknown.

## First result: a 20-minute LoRA run (2026-11-06)

Setup: Qwen3-0.6B-Base (bf16), LoRA r=16 (all linear layers), sequence 512, effective batch 16 sequences, lr 2e-4 (cosine), gradient checkpointing, 215 steps ≈ 1.76M tokens, RTX 4060 Laptop 8 GB. Data: the first 30 MB of Turkish Wikipedia (`corpus-wiki-tr-30mb.txt`). Evaluation: the last row group of the second parquet file (does not overlap with training), 200k tokens. Scripts `lora_cpt.py`, `olc_taban.py`.

| | Base | After LoRA |
|---|---|---|
| Loss per token (nat) | 2.7228 | 2.6045 |
| Perplexity | 15.22 | 13.52 |
| Bits per byte | 1.2969 | 1.2406 (−4.3%) |
| Tokens per word | 2.780 | 2.780 (tokenizer unchanged) |

Training loss (mean of first 10 / last 10 steps): 2.645 → 2.458. Peak training VRAM 5.23 GB (fits in 8 GB, ~2.8 GB headroom). Speed ≈ 5.6 s/step. Adapter file 40.4 MB.

**Reading:** the adaptation path works on this hardware, and even a short run gives a measurable improvement on Wikipedia-like Turkish text. Limits: a single run, a single seed; the evaluation text comes from the same domain as training (Wikipedia), so it does not show general Turkish performance; English forgetting was not measured; benchmarks (TurkishMMLU etc.) are not there yet. These are needed to say "the Turkish model improved".

**Tokenizer note:** 2.78 tokens/word is high for Turkish (the tokenizer fragments Turkish). This raises both training and inference cost; the value of extending the vocabulary must be measured separately.

**Adapter size note:** a 40 MB adapter is ~30× smaller than carrying the whole model (1.2 GB) in DiLoCo synchronisation. Promising for the hypothesis (adapter-DiLoCo), not tried yet.

## Forgetting and benchmark (2026-11-06)

Data: WikiText-2 raw test (English, CC BY-SA 3.0, 735 KB) and TurkishMMLU (AYueksel/TurkishMMLU, 900 test questions, 9 subjects × 100, 1.3 MB; license not verified, not found in the README). Scripts `olc_ing.py`, `olc_mmlu.py`; raw output `olcum-sonuc.txt`. TurkishMMLU 5-shot, by letter probability; chance level 20%.

| | Base | LoRA (20 min) |
|---|---|---|
| Turkish bits per byte (Wikipedia, held out) | 1.297 | 1.241 |
| English bits per byte (WikiText-2) | 0.9468 | 0.9597 (+1.4%, ppl 16.68 → 17.33) |
| TurkishMMLU 5-shot accuracy | 35.6% (320/900) | 34.7% (312/900) |

**Reading:**
- Turkish language modelling improved (−4.3%), but there is no improvement on the benchmark: the difference is 8 questions, within the standard error of a 900-question test (~1.6 points), i.e. noise. There is no one-directional pattern by subject either.
- There is mild forgetting in English (+1.4% bits per byte). Small, but it is a single run and in the expected direction for training on Turkish data only.
- Meaning: with 1.76M tokens and Wikipedia the language-modelling loss goes down, but the knowledge/reasoning benchmark does not move. TurkishMMLU measures knowledge and reasoning; moving it needs far more and more diverse data (billions of tokens), an English replay mix and probably a larger base.
- Therefore the claim "the Turkish model improved" **cannot be made** at this stage; what can be said is "the method works and the memory/speed budget has been measured".

## Adapter-DiLoCo simulation (2026-11-06)

Script `adaptor_diloco.py`, raw data `adaptor-diloco-h25.json` / `.log`. Qwen3-0.6B-Base is frozen and shared among 4 virtual workers; only the LoRA (r=16, 10.1M parameters, 40.4 MB fp32) is worker-specific and carried in synchronisation. 8 rounds × 25 local steps (per worker 4 sequences × 512 tokens/step), outer lr 1.0 / mom 0.5 (taken from the earlier toy experiment, not tuned for this model). Baseline: the same total compute, synchronised every step (4×4 sequences). Evaluation: 60k tokens on the held-out Turkish Wikipedia slice, bits per byte.

| Round | Baseline | Adapter-DiLoCo |
|---|---|---|
| 0 | 1.2714 | 1.2714 |
| 2 | 1.2390 | 1.2395 |
| 4 | 1.2238 | 1.2275 |
| 6 | 1.2184 | 1.2201 |
| 8 (last) | **1.2155** | **1.2166** |

The difference is 0.0011 bits/byte (−0.09%); about 98% of the baseline's total gain (0.0559) was achieved with DiLoCo (0.0548). Peak VRAM 5.64 GB.

**Communication (calculation):** the baseline exchanges adapter-sized data every step: 200 steps × 4 workers × 40.4 MB ≈ 32 GB. DiLoCo in 8 rounds: 8 × 4 × 40.4 MB ≈ 1.3 GB: about 25× less.

**Reading:** at adapter scale, the cost of sparse synchronisation is negligible in this setup. The ~0.11 nat gap seen in the toy model does not appear here; possible reasons: a strong frozen base, small and low-noise LoRA updates, short training.

**Limits (important):** a single seed; only 200 steps; a 60k-token evaluation (small differences may be noise); the data shards come from the same Wikipedia stream, so workers see roughly the same distribution (with real volunteers the data will differ); network latency, worker loss and malicious contributions were not simulated; the benchmark and English forgetting were not measured; the risk of incompatibility with standard training after DiLoCo (arXiv 2511.13761) was not tested.

## Next concrete steps

1. Install `transformers`, `peft`, `accelerate`, `bitsandbytes` into the Python environment (small packages).
2. Download `Qwen/Qwen3-0.6B-Base` (~1.2 GB, needs user approval).
3. Base measurement: Turkish perplexity and tokens per word.
4. The first LoRA continued pre-training run with memory measurement on 8 GB (small scale).

## Sources / caveats

The searches were single-pass; model licenses were verified from the model card API only for Qwen3. Some 2026 paper links (ufakzeka-1 etc.) were not verified.
