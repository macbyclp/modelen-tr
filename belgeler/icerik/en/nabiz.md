---
baslik: Heartbeat
bolum: Portal API
sira: 2
ozet: Send heartbeats so your coordinator shows as online in the directory.
---

# Heartbeat

An approved coordinator reports that it is alive by POSTing a **heartbeat**. The public page and the directory show an "online / delayed" badge based on it.

```bash
curl -s -X POST https://modelen.tr/api/v1/koordinator/nabiz \
  -H "Authorization: Bearer $MODELEN_API_ANAHTARI" -H "Content-Type: application/json" \
  -d '{"durum":"calisiyor","tur":3,"toplam_tur":20,"aktif_isci":7,"protokol":"1","surum":"0.4.0"}'
```

| Field | Type | Required | Meaning |
|---|---|---|---|
| `durum` | string | **yes** | `calisiyor` (running), `bekliyor` (waiting), `bakimda` (maintenance), `durdu` (stopped) |
| `tur`, `toplam_tur`, `aktif_isci` | integer ≥ 0 | no | current round, planned rounds, active workers |
| `protokol` | string ≤ 10 | no | e.g. `"1"` |
| `surum` | string ≤ 30 | no | your software version |
| `mesaj` | string ≤ 120 | no | short note |

Unknown fields → `400 bilinmeyen_alan`. Only approved coordinators may send (`403 onayli_degil`). Limit: 6 per minute.

## Public status

| Status | Condition |
|---|---|
| `cevrimici` (online) | running/waiting and last heartbeat ≤ 15 min ago |
| `gecikmeli` (delayed) | running/waiting and last heartbeat ≤ 24 h ago |
| `bakimda` / `durdu` | reported in the last 24 h |
| `bilinmiyor` (unknown) | none, or older than 24 h |

So send at least every 15 minutes; every 5 minutes is a good interval. With the example client:

```bash
python istemci/ornekler/modelen_api.py nabiz-dongusu --koordinator http://127.0.0.1:8750 --aralik 300
```
