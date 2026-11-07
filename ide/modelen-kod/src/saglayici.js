"use strict";
// Sağlayıcı katmanı: tek arayüz, birden çok arka uç.
//   tur "openai"    : OpenAI uyumlu /chat/completions (Modelen yerel sunucusu, Ollama, llama.cpp, OpenRouter, OpenAI, vb.)
//   tur "anthropic" : Anthropic Messages API
// Bağımlılık yok; Node 18+ ve VS Code'un gömülü Node'u için global fetch yeterli.
// API anahtarı çağıran tarafından verilir; bu modül anahtarı asla kaydetmez ya da günlüğe yazmaz.

function bosKaldir(s) {
  return String(s || "").replace(/\/+$/, "");
}

class SaglayiciHatasi extends Error {
  constructor(mesaj, durum) {
    super(mesaj);
    this.name = "SaglayiciHatasi";
    this.durum = durum;
  }
}

// SSE akışını satır satır okuyup her "data:" yükünü onData'ya verir.
async function sseOku(yanit, onData) {
  const okuyucu = yanit.body.getReader();
  const cozucu = new TextDecoder("utf-8");
  let tampon = "";
  for (;;) {
    const { done, value } = await okuyucu.read();
    if (done) break;
    tampon += cozucu.decode(value, { stream: true });
    let i;
    while ((i = tampon.indexOf("\n")) >= 0) {
      const satir = tampon.slice(0, i).replace(/\r$/, "");
      tampon = tampon.slice(i + 1);
      if (satir.startsWith("data:")) {
        const yuk = satir.slice(5).trim();
        if (yuk) onData(yuk);
      }
    }
  }
  const kalan = tampon.trim();
  if (kalan.startsWith("data:")) onData(kalan.slice(5).trim());
}

async function hataMetni(yanit) {
  let govde = "";
  try {
    govde = (await yanit.text()).slice(0, 400);
  } catch (_) {}
  return `HTTP ${yanit.status}${govde ? ": " + govde : ""}`;
}

// ayar: {tur, adres, model, anahtar?, maxToken?, sicaklik?}
// mesajlar: [{rol: "system"|"user"|"assistant", icerik: string}]
// onParca(metin) her metin parçasında çağrılır. Dönüş: tam metin.
async function sohbet(ayar, mesajlar, { onParca, signal } = {}) {
  if (!ayar || !ayar.tur) throw new SaglayiciHatasi("sağlayıcı türü yok");
  if (!ayar.adres) throw new SaglayiciHatasi("sağlayıcı adresi yok");
  if (!ayar.model) throw new SaglayiciHatasi("model adı yok");
  const adres = bosKaldir(ayar.adres);
  let tam = "";
  const parca = (t) => {
    if (!t) return;
    tam += t;
    if (onParca) onParca(t);
  };

  if (ayar.tur === "openai") {
    const basliklar = { "Content-Type": "application/json" };
    if (ayar.anahtar) basliklar["Authorization"] = `Bearer ${ayar.anahtar}`;
    const yanit = await fetch(`${adres}/chat/completions`, {
      method: "POST",
      headers: basliklar,
      signal,
      body: JSON.stringify({
        model: ayar.model,
        stream: true,
        max_tokens: ayar.maxToken || 1024,
        temperature: ayar.sicaklik ?? 0.2,
        messages: mesajlar.map((m) => ({ role: m.rol, content: m.icerik })),
      }),
    });
    if (!yanit.ok) throw new SaglayiciHatasi(await hataMetni(yanit), yanit.status);
    await sseOku(yanit, (yuk) => {
      if (yuk === "[DONE]") return;
      try {
        const j = JSON.parse(yuk);
        parca(j.choices && j.choices[0] && j.choices[0].delta && j.choices[0].delta.content);
      } catch (_) {
        /* bozuk satırı yok say */
      }
    });
    return tam;
  }

  if (ayar.tur === "anthropic") {
    const sistem = mesajlar.filter((m) => m.rol === "system").map((m) => m.icerik).join("\n\n");
    const govde = {
      model: ayar.model,
      stream: true,
      max_tokens: ayar.maxToken || 1024,
      messages: mesajlar.filter((m) => m.rol !== "system").map((m) => ({ role: m.rol, content: m.icerik })),
    };
    if (sistem) govde.system = sistem;
    if (ayar.sicaklik !== undefined) govde.temperature = ayar.sicaklik;
    const basliklar = { "Content-Type": "application/json", "anthropic-version": "2023-06-01" };
    if (ayar.anahtar) basliklar["x-api-key"] = ayar.anahtar;
    const yanit = await fetch(`${adres}/v1/messages`, { method: "POST", headers: basliklar, signal, body: JSON.stringify(govde) });
    if (!yanit.ok) throw new SaglayiciHatasi(await hataMetni(yanit), yanit.status);
    await sseOku(yanit, (yuk) => {
      try {
        const j = JSON.parse(yuk);
        if (j.type === "content_block_delta" && j.delta && j.delta.type === "text_delta") parca(j.delta.text);
        if (j.type === "error") throw new SaglayiciHatasi((j.error && j.error.message) || "akış hatası");
      } catch (e) {
        if (e instanceof SaglayiciHatasi) throw e;
      }
    });
    return tam;
  }

  throw new SaglayiciHatasi(`bilinmeyen tür: ${ayar.tur}`);
}

// Eklentinin kullandığı varsayılan sağlayıcı listesi (anahtarlar burada YOK).
const VARSAYILANLAR = [
  { ad: "Modelen (yerel)", tur: "openai", adres: "http://127.0.0.1:8760/v1", model: "modelen-qwen3-0.6b", anahtarGerekir: false },
  { ad: "Ollama (yerel)", tur: "openai", adres: "http://127.0.0.1:11434/v1", model: "qwen3:4b-instruct-2507-q4_K_M", anahtarGerekir: false },
  { ad: "OpenAI uyumlu (bulut)", tur: "openai", adres: "https://api.openai.com/v1", model: "", anahtarGerekir: true },
  { ad: "Anthropic", tur: "anthropic", adres: "https://api.anthropic.com", model: "", anahtarGerekir: true },
];

module.exports = { sohbet, SaglayiciHatasi, VARSAYILANLAR };
