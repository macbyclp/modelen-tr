---
baslik: Address verification
bolum: Becoming a coordinator
sira: 2
ozet: Prove your coordinator address is yours with a .well-known file: steps, server examples and troubleshooting.
---

# Address verification

Showing an address anyone can type in the directory would let someone present another person's server as their own. So you prove you control the address: you publish a value the portal gives you at your address, and the portal fetches it.

Verified addresses show `adres_dogrulandi: true` on the public page and in the API. If you change the address, verification is **reset automatically**.

## Steps

**1. Start verification.** You need a registered `https://` address.

```bash
curl -s -X POST https://modelen.tr/api/v1/koordinator/adres-dogrula \
  -H "Authorization: Bearer $MODELEN_API_ANAHTARI"
```

```json
{
  "adres": "https://coordinator.example.org",
  "dosya": "https://coordinator.example.org/.well-known/modelen-dogrulama.txt",
  "icerik": "modelen-dogrulama-AbC123..."
}
```

**2. Publish the file.** Serve a text file at `dosya` whose body is exactly the `icerik` value (leading/trailing whitespace and newlines do not matter).

With Caddy:

```text
coordinator.example.org {
    handle /.well-known/modelen-dogrulama.txt {
        respond "modelen-dogrulama-AbC123..." 200
    }
    reverse_proxy 127.0.0.1:8750
}
```

With nginx:

```text
location = /.well-known/modelen-dogrulama.txt {
    default_type text/plain;
    return 200 "modelen-dogrulama-AbC123...";
}
```

**3. Ask the portal to check.**

```bash
curl -s -X POST https://modelen.tr/api/v1/koordinator/adres-dogrula/kontrol \
  -H "Authorization: Bearer $MODELEN_API_ANAHTARI"
# {"adres_dogrulandi":true}
```

You may remove the file afterwards, but changing the address requires verifying again.

## How does the portal read your address?

The portal server sends a request to your address. Strict rules keep this from being abused:

- **https** only, with a valid **TLS certificate** for the name.
- Ports **443** and **8443** only.
- The address must be a **domain name** (not an IP) resolving to the **public internet**. Private/local addresses (`10.x`, `192.168.x`, `127.x`, `169.254.x`, …) and names that resolve to them are rejected.
- **Redirects are not followed**; the response must be `200` directly.
- At most **1 KB** is read, with a 6 s timeout.

## Troubleshooting

| `kod` | Meaning | What to do |
|---|---|---|
| `baslatilmadi` | You did not start verification first | Call step 1 |
| `adres_yok` | You have no registered https address | Add `adres` with `PATCH /koordinator` |
| `okunamadi` | The file could not be read (404, certificate error, timeout, private IP…) | Read the message; check with `curl -i` that the file returns 200 over https |
| `icerik_uyusmuyor` | File found but content differs | Copy the value exactly; if you restarted, use the new value, not the old one |
| `hiz_siniri` | More than 10 checks in 10 minutes | Wait a little |

:::ipucu
To self-test: `curl -sS -i https://your-address/.well-known/modelen-dogrulama.txt` should show `HTTP/… 200` and the expected text. If it gives a certificate error, the portal cannot read it either.
:::
