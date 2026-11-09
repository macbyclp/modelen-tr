# modelen: working notes

[Türkçe](CALISMA-NOTLARI.md) · **English**

> **Note (2026-11-09):** `site/`, `belgeler/`, `portal/`, `kurumsal/` and `logo/` have been split out of this repository; the web side lives in the private `macbyclp/modelen-web` repository. Lines below that refer to these folders are a historical record.


> This file is the project's first README and is kept as day-by-day working notes. For the current introduction see README.md in the root directory. The phrase "user statement" in the notes indicates that decisions came from the project owner.

A project to train small, Turkish-focused language models **in a distributed way on volunteer GPUs**.

> Status: idea stage. Start date: 2026-11-05.

## Goal

To pool the Turkish community's GPUs and train a shared, open Turkish model. Common ownership and transparency come first, not profit.

## Initial decisions (user statement, 2026-11-05)

- Purpose: to use volunteer GPUs while **training** models (not an inference network or audio generation).
- Reference: volunteer participation in the style of [farm-vakit.hakancelik.dev](https://farm-vakit.hakancelik.dev/#katil); but this project will do training, not voice-over.

## Decisions clarified (user statement, 2026-11-05)

- **Target model size:** ~1B parameters (the first real target).
- **Hardware:** a single GPU only, RTX 4060 Laptop, 8 GB VRAM.
- **First concrete step:** a small DiLoCo experiment, `diloco_sim.py`.

**Important limit (my assessment):** fully training a 1B model does not fit in 8 GB VRAM (weights + Adam state alone exceed it). So the simulation is done with a small model of ~3M–100M parameters; the aim is not model quality but to measure **whether sparse synchronisation distorts the loss curve**. The 1B target is a later stage, with a real volunteer network or rented GPUs.

## Product and organisation decisions (user approval "accept the recommendations", 2026-11-07)

1. **Audience:** first Turkish-speaking developers and institutions; the product form is an API and a locally running model.
2. **Differentiator:** community ownership and a transparent contribution record.
3. **Incentive:** no crypto/money at the start; a contribution record and a voice over the model.
4. **Legal structure:** first only an open-source project; a legal entity later if needed (association/foundation etc.). Data collection (KVKK) and licensing are handled accordingly.
5. **Volunteer trust:** open-source client, signed updates, only the training job on the GPU, no access to user data.
6. **Time and partners:** NOT ANSWERED. How many hours a week and whether there will be partners is unclear; the plan shrinks accordingly.

## Files

- `diloco_sim.py`: DiLoCo simulation with K virtual workers on a single GPU + a single-worker reference.
- `.venv/`: local Python environment (PyTorch CUDA).
- `ADAPTASYON.md`: adaptation path plan and measurements (LoRA, forgetting, TurkishMMLU, adapter-DiLoCo).
- `LICENSE`, `NOTICE`: Apache-2.0 text and notice.
- `site/`: the modelen.tr static website (TR + EN, 30 pages, including the new Measurements page; built with `python site/build.py`; cookie-free, no third-party resources). Placeholders are in `site/build.py`.
- `logo/`: `fener/kucuk/` (small sizes: kucuk-ikon.svg, kucuk-isaret.svg, monochrome and white, png/ 16-512), `fener/f03-vektor.svg` (the chosen logo: Halay Ring, vector; monochrome and white versions beside it), `f03-onizleme.html`, `fener-varyantlari.html` (8 "hand in hand" compositions for #049), `finalistler.html` (the user's 13 finalists, with comments) and 100-candidate logo selection tables: `secim-tablosu-gorsel.html` (gpt-image-2 images, full-size PNGs in `img/`, ~116 MB) and `secim-tablosu.html` (SVG vector drafts), individual SVGs (`svg/`), concepts (`konseptler.py`), Codex fleet scripts (`run_fleet.sh`, `make_briefs.py`, `collect.py`, `build_sheet.py`).
- `kurumsal/`: `KURUMSAL.md` (identity, pre-release checklist), `AVUKAT-ONAY-LISTESI.md` (questions for the lawyer, release gate).
- `istemci/`: volunteer GPU client prototype (coordinator, worker, adapter-DiLoCo; `ISTEMCI.md`). Identity, anti-poisoning, TLS and a UI are missing.
- `uygulama/`: **the Modelen desktop app (Rust, egui)**: volunteer GPU contribution, local model, a Turkish code assistant (Modelen + OpenAI-compatible + Anthropic + Ollama), a single exe (~10 MB). Details and honest gaps: `uygulama/UYGULAMA.md` (training is still a Python subprocess; the UI was not tried by clicking).
- `sunucu/`: a local server that serves the Modelen model on an OpenAI-compatible endpoint. `ide/`: the old VS Code extension prototype, **no longer used** (the user does not want VS Code).

## Corporate decisions (user, 2026-11-07)

- Name: **Modelen Alternative Training Community** (Modelen Alternatif Eğitim Topluluğu), domain **modelen.tr**.
- License: code Apache-2.0, model Apache-2.0.
- Site: Turkish + English, multi-page. Identity: e-mail only (`iletisim@modelen.tr` assumed), no personal names.
- The legal texts are drafts; they must not be published without lawyer approval (see `kurumsal/AVUKAT-ONAY-LISTESI.md`).

## First results (2026-11-05)

Setup: RTX 4060 Laptop, a 3.31M-parameter byte-level GPT, 4 virtual workers, 20 rounds × 25 local steps (synchronisation 25× sparser), equal tokens. Data: `corpus-yerel.txt` (~256 KB, vault notes; **personal, do not share/publish**). Details in `sonuc-h25.json` and `sweep-*.json`.

| Method | Final val_loss |
|---|---|
| Single worker, synchronised every step (reference) | 1.520 |
| DiLoCo, outer lr 0.7 / momentum 0.9 | 1.800 |
| DiLoCo, outer lr 1.0 / momentum 0.0 | 1.904 |
| DiLoCo, outer lr 0.7 / momentum 0.5 | 1.778 |
| DiLoCo, outer lr 0.5 / momentum 0.9 | 1.867 |
| **DiLoCo, outer lr 1.0 / momentum 0.5** | **1.630** |

**Reading:** the outer-optimizer setting changes the result a lot; with the best setting, sparse synchronisation is ~0.11 nat behind the reference, while communication is 25× less. This is promising but **not proof**: a single seed, a very small model, very small and repetitive data, the curve has not converged yet, the tuning grid is narrow. Next step: real Turkish data, multiple seeds, sweeping H values (25/100/500).

### Seed × synchronisation interval sweep (2026-11-06)

3 seeds, each worker 500 local steps in total, outer lr 1.0 / momentum 0.5 (fixed; tuned only at H=25 and seed 0). Reference (mean of 3 seeds): **1.532**. Raw data in `sweep/`.

| H (steps between two syncs) | Number of syncs | Mean val_loss | Gap to reference |
|---|---|---|---|
| 10 | 50 | 1.599 | +0.067 |
| 25 | 20 | 1.639 | +0.107 |
| 50 | 10 | 1.694 | +0.161 |
| 100 | 5 | 1.758 | +0.226 |

**Reading:** as H grows the gap increases steadily, and the spread between seeds is small (≤0.01), so the result is not noise. In this small model the cost of sparse synchronisation is clear: ~0.16 nat for 10× less communication. Limits: the outer setting was not retuned for large H (it may be unfairly making them look bad), the model is 3.3M, the data 256 KB. For a volunteer network the real question is how this cost changes at 1B scale and on real data.

### Repeat with real Turkish data (2026-11-06)

Data: Turkish Wikipedia (`wikimedia/wikipedia`, 20231101.tr, two parquet files, 553 MB, `data/wiki-tr/`, CC BY-SA/GFDL), the first 3280 articles = 30 MB of text (`corpus-wiki-tr-30mb.txt`, via `wiki_to_txt.py`). The ordering should be assumed non-random. Same setup: 3.3M model, 4 workers, 500 steps, 3 seeds, outer lr 1.0 / mom 0.5. Raw data in `sweep-wiki/`.

| H | Mean val_loss | Gap to reference | Seed deviation |
|---|---|---|---|
| reference | 1.919 | — | — |
| 10 | 2.045 | +0.126 | 0.024 |
| 25 | 2.031 | +0.112 | 0.013 |
| 50 | 2.086 | +0.168 | 0.006 |
| 100 | 2.075 | +0.156 | 0.010 |

**Reading:** on real data the gap is again ~0.11–0.17 nat, so the earlier finding (sparse synchronisation has a reasonable cost) holds. But the earlier "gets steadily worse as H grows" pattern is not clear here: the differences between H=10 and 25, and between 50 and 100, are the same size as the seed deviation. The outer setting was not tuned for this data; the small model and short training (500 steps) limit the result. So I am not saying anything definite about the effect of H.

### Outer-optimizer grid, Wikipedia data (2026-11-06)

H=25, seed 0, 12 settings (outer lr 0.7/1.0/1.5 × momentum 0/0.3/0.5/0.8), reference 1.915. Raw data in `grid-wiki/`.

Best: **lr 1.0 / mom 0.5 → 2.032** (the setting we already use). Then lr 1.0 / mom 0.3 → 2.050; lr 1.5 / mom 0 → 2.056; lr 0.7 / mom 0.5 → 2.059. Worst: lr 1.5 / mom 0.8 → 2.491 (outer step too large, unstable).

**Reading:** retuning the setting did not turn up a better point; the ~0.11 nat gap does not come from the outer optimizer in this grid. The grid is coarse (12 points, a single seed, a single H); inner lr, inner steps and worker count are still fixed. Conclusion: the gap in the table looks like a real cost, not a tuning error.

## Market and literature survey (2026-11-06; a single search round, may be incomplete)

**Existing open Turkish models** (we are not new, differentiation is needed):
- [Turkish-LLM family (ogulcanaydogan)](https://github.com/ogulcanaydogan/Turkish-LLM): 1.5B–32B, SFT+DPO, 144k Turkish instruction pairs, GGUF versions. Release date not verified.
- [Turkce-LLM (matrixportalx)](https://featherless.ai/models/matrixportalx/Turkce-LLM): 8B, fine-tuned with LoRA, Apache-2.0, April 2025.
- Old/small: BERTurk, gpt2-small-turkish. No new small model dated 2026 was found, but the search was narrow.
- Inference: Turkish instruction tuning is already crowded. **From-scratch/continued pre-training and volunteer-network ownership** is a less filled space.

**Turkish pre-training data** (full links from search, not verified):
- FineWeb2 `tur_Latn`: ODC-By 1.0, ~42 billion words, ~125 GB disk.
- TurMix: ~168 billion tokens, license not verified ([arXiv 2512.18834](https://arxiv.org/abs/2512.18834)).
- `musabc/nanogpt-tr-v5-data`: CC-BY-4.0, in the 10–100 billion token range.
- Turkish Wikipedia (`wikimedia/wikipedia`, 20231101.tr): 2 parquet files, ~553 MB in total (340 + 213 MB); license CC BY-SA/GFDL (to be verified). A small, clean first data candidate.

**Evidence for distributed training:**
- [OpenDiLoCo](https://arxiv.org/abs/2407.07852): three countries on two continents, ~90–95% compute utilisation.
- INTELLECT-1: ~96% compute efficiency (partner blog); acknowledged to lag behind centralised models.
- Psyche (Nous): third-party summaries say it surpassed centralised training; not verified with a primary source.
- **Caution:** the [nanochat + DiLoCo study](https://arxiv.org/abs/2511.13761) reports that weights pre-trained with DiLoCo could not regain performance in subsequent mid/late training with standard DDP (representation drift). This directly affects the volunteer network plan.

## Open questions

- Data: which Turkish dataset, and what is its license? (the simulation uses the text file given with `--data`; otherwise a synthetic smoke test)
- Trust: how do we verify volunteer contributions?
- Incentive: why would participants give GPU time? (no crypto; recommendation)

## Technical roadmap (draft)

1. **Prototype:** 3–5 GPUs, DiLoCo-like sparse synchronisation, a loss-curve comparison on a single machine.
2. **Trust layer:** contribution verification (reference computation, gradient norm check, double computation).
3. **Turkish data pipeline:** cleaning, tokenizer, license record.
4. **Volunteer client:** open source, signed, single-command install; transparent code and update flow.
5. **Community launch:** start with a small pilot.

## References

- DiLoCo (Google DeepMind, 2023): distributed training with sparse synchronisation
- Hivemind / Learning@home: a volunteer distributed-training library
- Prime Intellect (INTELLECT-1) and Nous Research (DisTrO / Psyche): distributed training attempts (verify the current status)
- BOINC / Folding@home: the volunteer computing model
