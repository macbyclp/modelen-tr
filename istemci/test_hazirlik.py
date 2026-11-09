"""Koordinatör hazırlık araçlarının testleri: adaptor_uret.py ve veri_hazirla.py.

  .venv/Scripts/python.exe -m unittest istemci.test_hazirlik       (torch + safetensors gerekir)
Yerel taban model (models/qwen3-0.6b-base) varsa baslat.py çıktısıyla karşılaştırma ve belirteçleme testleri de koşar; yoksa atlanır.
"""
import math
import os
import subprocess
import sys
import tempfile
import unittest

import torch
from safetensors.torch import load_file

KOK = os.path.dirname(os.path.abspath(__file__))
DEPO = os.path.dirname(KOK)
sys.path.insert(0, KOK)
import adaptor_uret  # noqa: E402
import ortak  # noqa: E402

MODEL = os.path.join(DEPO, "models", "qwen3-0.6b-base")
MODEL_VAR = os.path.exists(os.path.join(MODEL, "config.json"))


class AdaptorUret(unittest.TestCase):
    def test_bicim_belgedekiyle_ayni(self):
        d = adaptor_uret.uret(0)
        self.assertEqual(len(d), 392)  # 28 katman x 7 modül x (A, B)
        self.assertEqual(sum(t.numel() for t in d.values()), 10_092_544)
        for t in d.values():
            self.assertEqual(t.dtype, torch.float32)
        self.assertEqual(tuple(d["base_model.model.model.layers.0.self_attn.q_proj.lora_A.default.weight"].shape), (16, 1024))
        self.assertEqual(tuple(d["base_model.model.model.layers.0.self_attn.q_proj.lora_B.default.weight"].shape), (2048, 16))
        self.assertEqual(tuple(d["base_model.model.model.layers.27.mlp.down_proj.lora_A.default.weight"].shape), (16, 3072))
        self.assertEqual(tuple(d["base_model.model.model.layers.27.mlp.down_proj.lora_B.default.weight"].shape), (1024, 16))
        self.assertEqual(tuple(d["base_model.model.model.layers.5.self_attn.o_proj.lora_A.default.weight"].shape), (16, 2048))

    def test_baslangic_peft_gibi(self):
        d = adaptor_uret.uret(0)
        for ad, t in d.items():
            if ".lora_B." in ad:
                self.assertEqual(float(t.abs().sum()), 0.0, ad)  # B sıfır
            else:
                sinir = 1 / math.sqrt(t.shape[1])
                self.assertLessEqual(float(t.abs().max()), sinir + 1e-9, ad)
                self.assertGreater(float(t.abs().max()), 0.9 * sinir, ad)  # düzgün dağılım

    def test_tohum_belirler(self):
        a, b, c = adaptor_uret.uret(7), adaptor_uret.uret(7), adaptor_uret.uret(8)
        k = "base_model.model.model.layers.3.mlp.up_proj.lora_A.default.weight"
        self.assertTrue(torch.equal(a[k], b[k]))
        self.assertFalse(torch.equal(a[k], c[k]))

    def test_cikti_dosyasi_koordinatorle_uyumlu_safetensors(self):
        with tempfile.TemporaryDirectory() as t:
            yol = os.path.join(t, "tur-0.safetensors")
            r = subprocess.run([sys.executable, os.path.join(KOK, "adaptor_uret.py"), "--cikti", yol], capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertAlmostEqual(os.path.getsize(yol) / 1e6, 40.4, delta=0.2)
            self.assertEqual(len(load_file(yol)), 392)

    @unittest.skipUnless(MODEL_VAR, "yerel taban model yok")
    def test_baslat_ciktisiyla_ayni_anahtar_ve_sekiller(self):
        m = ortak.yeni_model(MODEL, 0, cihaz="cpu")
        gercek = ortak.adaptor_al(m)
        uretilen = adaptor_uret.uret(0)
        self.assertEqual(set(gercek), set(uretilen))
        for ad in gercek:
            self.assertEqual(gercek[ad].shape, uretilen[ad].shape, ad)
            self.assertEqual(gercek[ad].dtype, uretilen[ad].dtype, ad)


@unittest.skipUnless(MODEL_VAR, "yerel belirteçleyici yok")
class VeriHazirla(unittest.TestCase):
    def calistir(self, *arg):
        return subprocess.run([sys.executable, os.path.join(KOK, "veri_hazirla.py"), "--belirtecleyici", MODEL, *arg], capture_output=True, text=True, encoding="utf-8", errors="replace")

    def test_metinden_belirtec_uretir(self):
        with tempfile.TemporaryDirectory() as t:
            os.makedirs(os.path.join(t, "alt"))
            open(os.path.join(t, "a.txt"), "w", encoding="utf-8").write("Merhaba dünya. Bu bir deneme metnidir. " * 200)
            open(os.path.join(t, "alt", "b.md"), "w", encoding="utf-8").write("İkinci belge ğüşiöç. " * 200)
            open(os.path.join(t, "c.jsonl"), "w", encoding="utf-8").write('{"text": "Üçüncü belge. ' + "kelime " * 300 + '"}\n{"text": ""}\n')
            open(os.path.join(t, "yok.bin"), "wb").write(b"\x00\x01")  # desteklenmeyen uzantı: yok sayılır
            cikti = os.path.join(t, "veri.safetensors")
            r = self.calistir("--girdi", t, "--cikti", cikti)
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            ids = load_file(cikti)["ids"]
            self.assertEqual(ids.dtype, torch.int32)
            self.assertGreater(len(ids), 1000)
            eos = 151643  # Qwen <|endoftext|>
            self.assertEqual(int((ids == eos).sum()), 3)  # her dosyanın sonunda bir EOS

    def test_belirtec_siniri(self):
        with tempfile.TemporaryDirectory() as t:
            open(os.path.join(t, "a.txt"), "w", encoding="utf-8").write("kelime " * 5000)
            cikti = os.path.join(t, "v.safetensors")
            r = self.calistir("--girdi", os.path.join(t, "a.txt"), "--cikti", cikti, "--en-cok-belirtec", "700")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(len(load_file(cikti)["ids"]), 700)

    def test_girdi_yoksa_hata(self):
        r = self.calistir("--girdi", "/yok/boyle/bir/yer", "--cikti", "x.safetensors")
        self.assertNotEqual(r.returncode, 0)

    def test_az_veri_uyarisi(self):
        with tempfile.TemporaryDirectory() as t:
            open(os.path.join(t, "k.txt"), "w", encoding="utf-8").write("kısa")
            r = self.calistir("--girdi", os.path.join(t, "k.txt"), "--cikti", os.path.join(t, "v.safetensors"))
            self.assertEqual(r.returncode, 0)
            self.assertIn("UYARI", r.stderr)


if __name__ == "__main__":
    unittest.main()
