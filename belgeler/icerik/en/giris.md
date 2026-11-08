---
baslik: Modelen documentation
bolum: Getting started
sira: 1
ozet: A guide to becoming a Modelen coordinator, connecting your own training system and using the Portal API.
---

# Modelen documentation

Modelen trains open language models with **volunteer GPUs**. The current method is *adapter-DiLoCo*: each volunteer trains a small LoRA adapter (r=16, ~10M parameters, ~40 MB) on top of Qwen3-0.6B-Base for a few steps; a **coordinator** merges the results and publishes the next round. Only the small adapter crosses the network.

This site is for people who want to **run a coordinator** or **plug their own training system into Modelen**.

## Where to start

| I want to… | Read |
|---|---|
| Try everything locally in 10 minutes | [Quick start](/en/hizli-baslangic/) |
| Join the public directory as a coordinator | [Becoming a coordinator](/en/koordinator-olmak/) |
| Know the exact wire contract | [Protocol v1](/en/protokol/) and [adapter format](/en/adaptor-bicimi/) |
| Check my own implementation | [Conformance test](/en/uyum-testi/) |
| Automate the portal (profile, heartbeat) | [API introduction](/en/api/) and [API reference](/en/api-referans/) |
| Keep a coordinator healthy and safe | [Heartbeat](/en/nabiz/), [Security](/en/guvenlik/) |

## What kind of training does Modelen do?

Modelen is a **fine-tuning** system. We do not train a base model from scratch; we train a small **LoRA** adapter on top of an open model (currently Qwen3-0.6B-Base). LoRA is the *parameter-efficient* (PEFT) way of fine-tuning: the base weights stay frozen and only an adapter of roughly 10 million parameters is learned. Only that ~40 MB crosses the network and an 8 GB volunteer GPU is enough. That is why LoRA appears so often in these docs: "fine-tuning" in Modelen means training a LoRA adapter in a distributed way.

| Question | Answer |
|---|---|
| Fine-tuning with LoRA | **Yes.** The fixed format of protocol v1 |
| Full-weight fine-tuning (all parameters) | No (not supported in v1) |
| Training a model from scratch | No |
| Which data? | **The coordinator's choice.** Modelen neither provides nor selects data |
| Training type | Optional `mod` field in the task: `cpt` (continued pretraining on raw text, the default) or `sft` (instruction fine-tuning). Both use the same adapter format; see the [protocol](/en/protokol/) |

:::not
Which data and which mode you train with is your decision as a coordinator, and so is the licence and provenance of that data.
:::

## The pieces

- **Volunteer app** (Rust desktop app): downloads a task, trains locally, uploads the adapter.
- **Coordinator**: any HTTP service that implements [protocol v1](/en/protokol/). A reference implementation and a stdlib-only minimal one are provided.
- **Portal** (modelen.tr): accounts, coordinator applications, the public directory and the [Portal API](/en/api/).

:::not
The Turkish documentation at the site root is the primary version; this English version covers the core pages. Pages not yet translated are linked from the Turkish site.
:::
