---
baslik: Becoming a coordinator
bolum: Becoming a coordinator
sira: 1
ozet: Steps to get a coordinator listed in the public Modelen directory.
---

# Becoming a coordinator

A coordinator is an HTTPS service that implements [protocol v1](/en/protokol/). Listing it in the public directory lets volunteers find and join it.

## Steps

1. **Run a coordinator** — the [reference one](https://github.com/macbyclp/modelen-tr/blob/main/istemci/koordinator.py), the minimal example, or your own implementation.
2. **Publish it over HTTPS** behind a reverse proxy (Caddy, nginx).
3. **Pass the [conformance test](/en/uyum-testi/).**
4. **Create an account** on [modelen.tr](https://modelen.tr) and verify your e-mail.
5. **Apply** from the panel, or with `POST /api/v1/koordinator` ([API](/en/api/)). An administrator reviews applications manually.
6. **Verify your address**: publish a one-line file at `/.well-known/modelen-dogrulama.txt` on your coordinator's host and ask the portal to check it. This proves you control the address.
7. **Send a [heartbeat](/en/nabiz/)** at least every 15 minutes to appear as online.

## After approval

- Edits to an approved profile are saved as a draft and published after review (the API answers `202`).
- Changing the address resets verification.
- A suspended application cannot be edited until an administrator restores it.
