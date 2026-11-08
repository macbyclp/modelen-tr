---
baslik: API introduction
bolum: Portal API
sira: 1
ozet: Modelen Portal API v1 - API keys, authentication, error codes, rate limits and examples.
---

# Portal API introduction

The Portal API lets coordinators manage their portal presence programmatically: application and profile updates, [heartbeat](/en/nabiz/), address verification and the public coordinator directory.

- **Base URL:** `https://modelen.tr/api/v1`
- **Format:** JSON (UTF-8)
- **Schema:** [`/api/v1/openapi.json`](https://modelen.tr/api/v1/openapi.json) and the [endpoint reference](/en/api-referans/)

## Public endpoints

No key needed; CORS is open.

```bash
curl -s https://modelen.tr/api/v1/saglik
curl -s https://modelen.tr/api/v1/koordinatorler
```

## Creating an API key

1. Sign up on [modelen.tr](https://modelen.tr) and verify your e-mail.
2. Open **Panel → For developers → API keys** (`/panel/api`).
3. Name and create a key. The `mdl_…` key is shown **only once**.

:::uyari
Treat the key like a password. Only its SHA-256 digest is stored; a lost key cannot be recovered, so revoke it and create a new one. Never put it in client-side code or public repositories. You can have at most 5 active keys.
:::

## Authentication

```bash
curl -s https://modelen.tr/api/v1/ben -H "Authorization: Bearer $MODELEN_API_ANAHTARI"
```

```python
import json, os, urllib.request
req = urllib.request.Request("https://modelen.tr/api/v1/ben",
    headers={"Authorization": "Bearer " + os.environ["MODELEN_API_ANAHTARI"]})
print(json.load(urllib.request.urlopen(req)))
```

```javascript
const res = await fetch("https://modelen.tr/api/v1/ben", {
  headers: { Authorization: `Bearer ${process.env.MODELEN_API_ANAHTARI}` },
});
console.log(await res.json());
```

A ready-made Python client lives in `istemci/ornekler/modelen_api.py`.

## Application and updates

```bash
curl -s -X POST https://modelen.tr/api/v1/koordinator \
  -H "Authorization: Bearer $MODELEN_API_ANAHTARI" -H "Content-Type: application/json" \
  -d '{"ad":"Example Lab","kisa":"Volunteer training coordinator for open models","adres":"https://coordinator.example.org"}'
```

Allowed fields: `ad`, `kisa`, `ayrinti`, `baglanti`, `adres`, `hf`, `iletisim`. `201` = application created; `200` = updated; `202` = change to an **approved** profile saved as a draft awaiting review.

## Errors

```json
{"hata": "Anahtar başına dakikada en çok 120 istek.", "kod": "hiz_siniri"}
```

`kod` is stable and machine-readable; `hata` is a (Turkish) human message. Common codes: `yetkisiz` (401), `eposta_dogrulanmadi` (403), `onayli_degil` (403), `basvuru_yok` (404), `basvuru_var` / `askida` (409), `dogrulama` / `bilinmeyen_alan` (400), `hiz_siniri` (429).

## Rate limits

| Limit | Value |
|---|---|
| Per key | 120 requests / minute |
| Per IP | 240 requests / minute |
| Failed-key attempts | 30 per 10 minutes |
| Heartbeat | 6 / minute |
| Address verification check | 10 per 10 minutes |

`429` responses carry `Retry-After` (seconds).

## CORS

Public endpoints are callable from any origin. Do not use keys in browser code; call keyed endpoints from your server.

## Versioning

Additive changes stay in `/api/v1`; breaking changes arrive as `/api/v2`. Ignore unknown fields in responses.
