---
baslik: Release notes
bolum: Resources
sira: 2
ozet: Protocol and Portal API versions; backward-compatibility principles.
---

# Release notes

Full history: [GitHub releases](https://github.com/macbyclp/modelen-tr/releases).

## Unreleased (after v0.5.0)

- **Data distribution:** the coordinator can serve tokenised training data shards (`--veri`, `GET /veri`); workers verify the SHA-256 and cache them. No local data file is needed any more. Optional protocol fields `veri_sha256` / `veri_belirtec`.
- **Training mode:** optional task field `mod` (`cpt` / `sft`).
- **Reference coordinator hardening:** state and outer-step momentum persisted every round and restored on restart; worker-name validation (`400`); per-IP rate limit (`429`); worker-count limit (`503`); connection timeout; several comma-separated keys; `--vekil` for proxies. Coordinator version `0.5.0`.
- **Worker:** URL-encodes the worker name.
- **Volunteer install script** `kur.ps1` and a signed release pipeline (CI + attestation), **both not yet tested end to end**.
- **Server monitoring** (portal, docs, certificate, disk, memory, backup age) with automatic portal restart.
- **docs:** fine-tuning section, SVG overview diagram, volunteer-setup page, more English pages.

## v0.5.0

docs.modelen.tr, Portal API v1, `GET /bilgi`, conformance test, example coordinator and API client.

## v0.4.0

End-to-end reference coordinator and volunteer app round; community questions (`/soru`).

## Backward-compatibility principle

- **Protocol v1**: existing endpoints and fields do not change. New optional fields may be added; clients must ignore fields they do not know.
- **Portal API v1**: the same principle. Breaking changes arrive under `/api/v2`.
