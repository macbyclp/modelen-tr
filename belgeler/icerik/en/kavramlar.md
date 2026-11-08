---
baslik: Concepts
bolum: Getting started
sira: 3
ozet: Terms used in Modelen: coordinator, worker, round, adapter, LoRA, DiLoCo and more.
---

# Concepts

| Term | Meaning |
|---|---|
| **Volunteer** | A person who lends their GPU to training. Runs the desktop app under a pseudonym; no personal data. |
| **Worker** | The training process on the volunteer's machine (`istemci/isci.py`, started by the app as a child process). |
| **Coordinator** | The server that runs rounds and holds the adapter. Hands out tasks, validates and averages worker results. |
| **Portal** | `modelen.tr`: accounts, coordinator applications and approval, the public directory, the Portal API. |
| **Base model** | A frozen open language model. Currently only **Qwen3-0.6B-Base** (Apache-2.0). Lives on the volunteer's disk; never crosses the network. |
| **LoRA adapter** | Small trainable weights attached to the base model. Here r=16 on all linear layers: 392 tensors, ~10.1 M parameters, **~40.4 MB** (float32). |
| **Fine-tuning** | Adapting a ready-made model with new data. In Modelen this means freezing the base model and training only the LoRA adapter. |
| **Round** | One coordinator cycle: hand out tasks → workers train → results collected → average + outer step → new adapter. |
| **H (inner steps)** | Local steps a worker takes per round (`ic_adim`, default 20). Synchronisation happens every H steps, not every step. |
| **DiLoCo** | Distributed training with infrequent synchronisation: workers take many local steps, then merge via the coordinator. |
| **Outer step** | The optimiser step the coordinator applies to the worker average (reference: Nesterov, lr 1.0, momentum 0.5). |
| **Data shard (`parca`)** | One of `n_parca` equal parts of the training data; each worker is assigned one. If the coordinator serves data (`--veri`), the worker downloads only its own shard. |
| **Heartbeat** | The coordinator telling the portal "I'm alive" (see [Heartbeat](/en/nabiz/)). |
| **Address verification** | A `.well-known` file check proving the coordinator address is yours. |
| **API key** | An `mdl_...` key for the Portal API. Created in the panel, shown once. |
| **Protocol v1** | The HTTP contract between the volunteer app and a coordinator ([details](/en/protokol/)). |
| **API v1** | The JSON interface the portal exposes to coordinators ([details](/en/api/)). |

:::not
The **protocol** and the **API** are different things. The *protocol* is between the volunteer app and **your coordinator**. The *Portal API* is between **you and the Modelen portal** (applications, heartbeat, directory).
:::
