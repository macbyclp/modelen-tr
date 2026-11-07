"""Modelen yerel sunucusu: Qwen3-0.6B-Base + (isteğe bağlı) Modelen LoRA adaptörü, OpenAI uyumlu uç.

  python sunucu/modelen_sunucu.py --adaptor istemci/calisma/tur-3.safetensors

IDE eklentisi (ide/modelen-kod) bu uca `http://127.0.0.1:8760/v1` ile bağlanır.
Dürüstlük notu: taban model talimat ayarlı değildir. Sohbet biçimi basit bir döküm olarak kurulur;
çıktı kalitesi bir sohbet asistanı düzeyinde BEKLENMEMELİDİR. Bu sunucu, kendi modelimizi IDE'ye bağlama hattının kanıtıdır.
Yalnızca 127.0.0.1 dinler.
"""
import argparse
import json
import os
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import torch
from transformers import TextIteratorStreamer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "istemci"))
import ortak  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--model", default="models/qwen3-0.6b-base")
ap.add_argument("--adaptor", default="", help="safetensors adaptör (boşsa yalnızca taban model)")
ap.add_argument("--ad", default="modelen-qwen3-0.6b")
ap.add_argument("--port", type=int, default=8760)
A = ap.parse_args()

from transformers import AutoTokenizer  # noqa: E402

tok = AutoTokenizer.from_pretrained(A.model)
m = ortak.yeni_model(A.model, 0, "cuda")
if A.adaptor:
    ortak.adaptor_yaz(m, ortak.bayttan(open(A.adaptor, "rb").read()))
m.eval()
m.gradient_checkpointing_disable()
m.config.use_cache = True
KIL = threading.Lock()  # tek GPU: istekler sırayla
ETIKET = {"system": "Sistem", "user": "Kullanıcı", "assistant": "Asistan"}


def istem(mesajlar):
    satir = [f"{ETIKET.get(x.get('role'), 'Kullanıcı')}: {x.get('content', '')}" for x in mesajlar]
    return "\n\n".join(satir) + "\n\nAsistan:"


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, kod, obj):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(kod)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path.rstrip("/") == "/v1/models":
            return self._json(200, {"object": "list", "data": [{"id": A.ad, "object": "model", "owned_by": "modelen"}]})
        self._json(404, {"error": "yok"})

    def do_POST(self):
        if self.path.rstrip("/") != "/v1/chat/completions":
            return self._json(404, {"error": "yok"})
        try:
            n = int(self.headers.get("Content-Length", "0"))
            ist = json.loads(self.rfile.read(n))
            mesajlar = ist["messages"]
        except Exception:
            return self._json(400, {"error": "geçersiz istek"})
        akis = bool(ist.get("stream"))
        maks = min(int(ist.get("max_tokens") or 256), 1024)
        sic = float(ist.get("temperature", 0.2))
        cid = "chatcmpl-" + uuid.uuid4().hex[:12]
        girdi = tok(istem(mesajlar), return_tensors="pt").to("cuda")
        stopl = ["\n\nKullanıcı:", "\n\nSistem:"]
        streamer = TextIteratorStreamer(tok, skip_prompt=True, skip_special_tokens=True)
        kw = dict(**girdi, max_new_tokens=maks, do_sample=sic > 0, streamer=streamer, stop_strings=stopl, tokenizer=tok,
                  pad_token_id=tok.eos_token_id)
        if sic > 0:
            kw["temperature"] = sic

        def calistir():
            with KIL, torch.no_grad():
                m.generate(**kw)

        threading.Thread(target=calistir, daemon=True).start()
        if akis:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
        tam = ""
        try:
            for parca in streamer:
                for s in stopl:  # durdurma dizisinin başı çıktıya sızmasın
                    if s in tam + parca:
                        parca = (tam + parca).split(s)[0][len(tam):]
                tam += parca
                if akis and parca:
                    veri = {"id": cid, "object": "chat.completion.chunk", "model": A.ad,
                            "choices": [{"index": 0, "delta": {"content": parca}, "finish_reason": None}]}
                    self.wfile.write(f"data: {json.dumps(veri, ensure_ascii=False)}\n\n".encode())
                    self.wfile.flush()
            if akis:
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
            else:
                self._json(200, {"id": cid, "object": "chat.completion", "created": int(time.time()), "model": A.ad,
                                 "choices": [{"index": 0, "message": {"role": "assistant", "content": tam.strip()}, "finish_reason": "stop"}]})
        except (BrokenPipeError, ConnectionResetError):
            pass


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", A.port), H)
    print(f"[modelen-sunucu] http://127.0.0.1:{A.port}/v1  model={A.ad}  adaptör={A.adaptor or 'yok'}", flush=True)
    srv.serve_forever()
