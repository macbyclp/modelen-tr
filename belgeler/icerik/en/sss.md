---
baslik: FAQ
bolum: Resources
sira: 1
ozet: Short answers about coordinating, the protocol, the API and the conformance test.
---

# FAQ

## What do I need to become a coordinator?
An HTTPS address, a service implementing protocol v1 ([reference](/en/referans-koordinator/) or [your own](/en/minimal-koordinator/)) and a portal account. No GPU needed; the GPUs are with the workers.

## Can I connect my own training system (not PyTorch, another language)?
Yes. A coordinator speaks only HTTP + safetensors. As long as you follow the [adapter format](/en/adaptor-bicimi/) (392 tensors, F32) and pass the [conformance test](/en/uyum-testi/), your internals are up to you.

## Is Modelen fine-tuning or training from scratch?
Fine-tuning: the base model stays frozen and only a LoRA adapter is trained. See the [introduction](/en/#what-kind-of-training-does-modelen-do).

## Can I use a different base model?
Protocol v1 supports only `Qwen/Qwen3-0.6B-Base` with the stated LoRA settings. Another model needs a manifest, which is planned ([roadmap](/en/yol-haritasi/)).

## Which data does training use?
The coordinator's. Modelen neither provides nor selects data. The coordinator can serve its own data shards to workers (`--veri`); its source and licence are the coordinator's responsibility.

## When is my application approved?
Applications are reviewed by an administrator by hand. You see the status in the panel or with `GET /api/v1/koordinator`; the result is also sent by e-mail.

## I edited my approved profile but the change is not visible.
Changes to an approved profile are saved as a draft (the API returns `202`) and go live after administrator approval.

## Why is the "online" badge missing?
You must be approved and send a [heartbeat](/en/nabiz/) at least every 15 minutes.

## Why does address verification fail?
Most common causes: the file is not at `https://address/.well-known/modelen-dogrulama.txt`, the content is not exactly the expected single line, the address redirects (redirects are not followed) or uses a port other than 443/8443. Details: [Address verification](/en/adres-dogrulama/).

## I lost my API key.
It cannot be recovered. Revoke it in the panel and create a new one.

## I get `429`.
You hit the [rate limits](/en/api/#rate-limits). Wait for `Retry-After`; do not send heartbeats more than 6 times a minute.

## What does the conformance test not catch?
It does not check merge correctness, performance or security (poisoning resistance); it only checks contract conformance.

## Is the code open? What licence?
Yes; repository: [github.com/macbyclp/modelen-tr](https://github.com/macbyclp/modelen-tr).
