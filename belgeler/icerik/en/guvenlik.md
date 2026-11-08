---
baslik: Security
bolum: Security
sira: 1
ozet: Running a coordinator safely: HTTPS, keys, no pickle, poisoning limits and responsible disclosure.
---

# Security

## Network and data

- **HTTPS is mandatory** on public networks; put the coordinator behind a TLS reverse proxy.
- **No pickle.** Accept only [safetensors](/en/adaptor-bicimi/); never `torch.load` data from the network.
- **Bound request bodies** (reference limit 300 MB) and check `Content-Length` before reading.
- **Don't collect personal data.** Worker ids are pseudonyms; don't log IPs, or keep them short-lived.

## Keys

- Keep the Portal API key (`mdl_…`) in an environment variable or secret manager, never in a repository. Revoke and recreate it if it leaks.
- Your coordinator's `X-Anahtar` is a separate shared key for your own workers; it is never given to the portal.

## Poisoning and malicious workers

Protocol v1 validation is **structural** (shape, dtype, NaN/Inf) plus the reference coordinator's outlier-norm elimination. It catches faulty or naive malicious results but **not a determined attacker**: a single shared key does not stop Sybil attacks, and double computation (assigning the same task to two workers) is not in the protocol yet. Start with a closed group, keep `--en-az` ≥ 3, watch delta norms in the log and evaluate after every round.

## Portal protections

API keys are stored as SHA-256 digests with rate limits and failed-attempt blocking; address verification is SSRF-hardened (https only, ports 443/8443, public IPs only, no redirects, 1 KB, 6 s); uploaded images are stripped of EXIF data.

## Reporting a vulnerability

Please do **not** open a public issue. E-mail [info@modelen.tr](mailto:info@modelen.tr) with details.
