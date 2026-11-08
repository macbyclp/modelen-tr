---
baslik: Roadmap
bolum: Resources
sira: 3
ozet: Planned work for protocol v2. Nothing here is implemented yet.
---

# Roadmap

:::uyari
Everything on this page is **planned, not implemented**. No dates are promised.
:::

## Protocol v2 candidates

- **Rich `/bilgi`**: full manifest of the base model and adapter configuration; support for other models and LoRA settings.
- **Signed data manifest**: machine-readable statement of the data shards and licences a coordinator uses, with signatures. (Plain shard distribution already exists; see [`/veri`](/en/protokol/#get-veri-parca-i-optional).)
- **Per-volunteer keys**: a worker identity instead of one shared key; a first step towards Sybil resistance.
- **Double computation**: giving the same task to two workers and comparing results (poisoning resistance).
- **Asynchronous / slow-worker tolerance**: variable step counts for GPUs of different speeds.
- **Smaller transfers**: the adapter download dominated a real-network test (~1 MB/s link, 40 MB took ~38 s); compression, lower precision or delta transfer would help.

## Portal API

- Webhooks for notifications (application status).
- Read-only statistics endpoints for coordinators.

For suggestions, open an issue on [GitHub](https://github.com/macbyclp/modelen-tr/issues).
