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

## The pieces

- **Volunteer app** (Rust desktop app): downloads a task, trains locally, uploads the adapter.
- **Coordinator**: any HTTP service that implements [protocol v1](/en/protokol/). A reference implementation and a stdlib-only minimal one are provided.
- **Portal** (modelen.tr): accounts, coordinator applications, the public directory and the [Portal API](/en/api/).

:::not
The Turkish documentation at the site root is the primary version; this English version covers the core pages. Pages not yet translated are linked from the Turkish site.
:::
