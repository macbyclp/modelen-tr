---
baslik: Integration options
bolum: Connecting your system
sira: 1
ozet: Today's ways to connect your own training system to Modelen, what you can customise and the limits.
---

# Integration options

The honest answer to "how do I connect my own training system to Modelen?": you can write the **coordinator side** any way you like, but the **training script and model on the volunteer's machine are Modelen's fixed definition**. The reason is security: a volunteer does not run your code.

## Three paths

### A. Use the reference coordinator (recommended start)

`istemci/koordinator.py` works out of the box: hands out tasks, validates results, drops outliers, applies the Nesterov outer step, writes every round to disk and resumes after a restart. You only choose its settings (rounds, H, learning rates…). See [Reference coordinator](/en/referans-koordinator/).

### B. Write your own coordinator

Any HTTP service implementing protocol v1 can be a coordinator: another language, another merge method, your own database, auth and observability. The volunteer app only knows the protocol. See [Protocol v1](/en/protokol/), [Write your own coordinator](/en/minimal-koordinator/) and the [Conformance test](/en/uyum-testi/).

### C. Your own model / training script (planned, not available)

For a different base model or adapter format you would need: a model **manifest**, signed data/model distribution and worker-side sandboxing. These are *planned* items on the [roadmap](/en/yol-haritasi/), not implemented today. (Distributing **your own data** with the same model and format *is* possible today; see the table below.)

## What can you change today?

| Topic | Free? | Note |
|---|---|---|
| Coordinator software / language / infrastructure | Yes | As long as it follows protocol v1 |
| Rounds, H (`ic_adim`), `bs`, `seq`, `lr`, `tohum` | Yes | Sent to the worker in the task |
| Merge method (average, momentum, weighted, filtering…) | Yes | Entirely on your side |
| Outlier / poisoning defence | Yes | Your responsibility ([Security](/en/guvenlik/)) |
| Which worker gets which data shard | Yes | Via `parca` / `n_parca` |
| Base model | **No** | Qwen3-0.6B-Base |
| Adapter format | **No** | LoRA r=16, 7 target modules, float32, 392 tensors ([details](/en/adaptor-bicimi/)) |
| Training script (loss, optimiser, data loading) | **No** | `istemci/isci.py`; AdamW, cosine schedule, clip 1.0 |
| Training data | **Yes** | You serve tokenised data (safetensors) with `--veri`; the coordinator shards it and serves it at [`/veri`](/en/protokol/#get-veri-parca-i-optional). Tokenise with the **base model's** tokenizer. Source and licence of the data are your responsibility |
| Training type (`mod`) | **Yes** | `cpt` (continued pretraining on raw text) or `sft` (instruction fine-tuning) |

:::uyari
Because of these limits you cannot connect a different model to Modelen today. But you can run **your own coordinator with your own volunteer community** using the same model and format; if you do not want to be listed in the portal, you can simply give volunteers your address (the app accepts custom addresses).
:::

## Decision guide

- *"I just want to try it and open it to volunteers"* → **A**.
- *"I must fit my own infrastructure / monitoring / identity system"* → **B**.
- *"I want to train a different model"* → no **C** yet; see the [roadmap](/en/yol-haritasi/) and describe your need on [GitHub](https://github.com/macbyclp/modelen-tr/issues).
