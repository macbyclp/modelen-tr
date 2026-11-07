"use strict";
const test = require("node:test");
const assert = require("node:assert");
const http = require("node:http");
const Module = require("node:module");
const { sohbet, SaglayiciHatasi } = require("../src/saglayici");
const { mesajlariKur, ilkKodBlogu } = require("../src/baglam");

function sunucu(isleyici) {
  return new Promise((coz) => {
    const s = http.createServer(isleyici);
    s.listen(0, "127.0.0.1", () => coz({ s, adres: `http://127.0.0.1:${s.address().port}` }));
  });
}
const oku = (r) => new Promise((c) => { let b = ""; r.on("data", (d) => (b += d)); r.on("end", () => c(b)); });

test("openai: akışı parçalara ayırır, başlık ve gövde doğru", async () => {
  let goruldu;
  const { s, adres } = await sunucu(async (req, res) => {
    goruldu = { yol: req.url, yetki: req.headers.authorization, govde: JSON.parse(await oku(req)) };
    res.writeHead(200, { "Content-Type": "text/event-stream" });
    // parçaları kasıtlı olarak satır ortasından böl
    const a = 'data: {"choices":[{"delta":{"content":"Mer"}}]}\n\ndata: {"choices":[{"delta":{"con';
    const b = 'tent":"haba"}}]}\n\ndata: [DONE]\n\n';
    res.write(a);
    setTimeout(() => { res.write(b); res.end(); }, 20);
  });
  const parcalar = [];
  const tam = await sohbet({ tur: "openai", adres: adres + "/v1/", model: "m", anahtar: "gizli" }, [{ rol: "user", icerik: "selam" }], { onParca: (p) => parcalar.push(p) });
  s.close();
  assert.strictEqual(tam, "Merhaba");
  assert.deepStrictEqual(parcalar, ["Mer", "haba"]);
  assert.strictEqual(goruldu.yol, "/v1/chat/completions");
  assert.strictEqual(goruldu.yetki, "Bearer gizli");
  assert.strictEqual(goruldu.govde.stream, true);
  assert.strictEqual(goruldu.govde.messages[0].content, "selam");
});

test("openai: anahtar yoksa Authorization başlığı gönderilmez", async () => {
  let yetki = "yok";
  const { s, adres } = await sunucu((req, res) => { yetki = req.headers.authorization; res.writeHead(200); res.end("data: [DONE]\n\n"); });
  await sohbet({ tur: "openai", adres, model: "m" }, [{ rol: "user", icerik: "x" }]);
  s.close();
  assert.strictEqual(yetki, undefined);
});

test("anthropic: sistem mesajı ayrılır, metin akışı okunur, anahtar başlıkta", async () => {
  let g;
  const { s, adres } = await sunucu(async (req, res) => {
    g = { yol: req.url, k: req.headers["x-api-key"], v: req.headers["anthropic-version"], govde: JSON.parse(await oku(req)) };
    res.writeHead(200, { "Content-Type": "text/event-stream" });
    res.write('event: content_block_delta\ndata: {"type":"content_block_delta","delta":{"type":"text_delta","text":"Sel"}}\n\n');
    res.write('event: ping\ndata: {"type":"ping"}\n\n');
    res.write('event: content_block_delta\ndata: {"type":"content_block_delta","delta":{"type":"text_delta","text":"am"}}\n\n');
    res.end();
  });
  const tam = await sohbet({ tur: "anthropic", adres, model: "c", anahtar: "k1" }, [{ rol: "system", icerik: "S" }, { rol: "user", icerik: "U" }]);
  s.close();
  assert.strictEqual(tam, "Selam");
  assert.strictEqual(g.yol, "/v1/messages");
  assert.strictEqual(g.k, "k1");
  assert.strictEqual(g.v, "2023-06-01");
  assert.strictEqual(g.govde.system, "S");
  assert.deepStrictEqual(g.govde.messages, [{ role: "user", content: "U" }]);
});

test("HTTP hatası SaglayiciHatasi olur ve gövdeyi taşır", async () => {
  const { s, adres } = await sunucu((req, res) => { res.writeHead(401); res.end('{"error":"kötü anahtar"}'); });
  await assert.rejects(sohbet({ tur: "openai", adres, model: "m" }, []), (e) => e instanceof SaglayiciHatasi && e.durum === 401 && /kötü anahtar/.test(e.message));
  s.close();
});

test("AbortSignal akışı keser", async () => {
  const { s, adres } = await sunucu((req, res) => { res.writeHead(200); res.write('data: {"choices":[{"delta":{"content":"a"}}]}\n\n'); /* kapatma */ });
  const ac = new AbortController();
  const p = sohbet({ tur: "openai", adres, model: "m" }, [], { signal: ac.signal, onParca: () => ac.abort() });
  await assert.rejects(p, (e) => e.name === "AbortError");
  s.closeAllConnections();
  s.close();
});

test("eksik ayar ve bilinmeyen tür reddedilir", async () => {
  await assert.rejects(sohbet({ tur: "openai", model: "m" }, []), /adresi yok/);
  await assert.rejects(sohbet({ tur: "x", adres: "http://a", model: "m" }, []), /bilinmeyen tür/);
});

test("bağlam: seçim öncelikli, uzun metin kırpılır, geçmiş korunur", () => {
  const m = mesajlariKur([{ rol: "user", icerik: "a" }, { rol: "assistant", icerik: "b" }], "bu ne?", { dosya: "x.py", dil: "python", secim: "print(1)", icerik: "TAM" });
  assert.strictEqual(m[0].rol, "system");
  assert.strictEqual(m.length, 4);
  assert.match(m[3].icerik, /Seçili kod: x\.py/);
  assert.doesNotMatch(m[3].icerik, /TAM/);
  const uzun = mesajlariKur([], "s", { dosya: "u", dil: "", secim: "", icerik: "z".repeat(50000) });
  assert.ok(uzun[1].icerik.length < 13000);
  assert.match(uzun[1].icerik, /kırpıldı/);
  assert.strictEqual(mesajlariKur([], "yalın", null)[1].icerik, "yalın");
});

test("ilkKodBlogu", () => {
  assert.strictEqual(ilkKodBlogu("a\n```js\nlet x=1;\n```\nb"), "let x=1;");
  assert.strictEqual(ilkKodBlogu("kod yok"), null);
});

test("eklenti: vscode taklidiyle etkinleşir, komutlar kayıtlı, anahtar webview'a gitmez", async () => {
  const komutlar = {};
  const mesajlar = [];
  let iletim;
  const sahte = {
    commands: { registerCommand: (ad, f) => ((komutlar[ad] = f), { dispose() {} }) },
    workspace: {
      getConfiguration: () => ({ get: (k) => ({ saglayicilar: [{ ad: "T", tur: "openai", adres: "", model: "m", anahtarGerekir: true }], varsayilan: "T", maxToken: 64 })[k] }),
      asRelativePath: (u) => String(u),
    },
    window: {
      activeTextEditor: undefined,
      createWebviewPanel: () => ({
        webview: { cspSource: "csp", set html(h) { sahte._html = h; }, postMessage: (m) => mesajlar.push(m), onDidReceiveMessage: (f) => (iletim = f) },
        reveal() {}, onDidDispose() {},
      }),
      showInformationMessage() {}, showWarningMessage() {}, showQuickPick: async () => undefined, showInputBox: async () => undefined,
    },
    ViewColumn: { Beside: 2 },
  };
  const eskiYukle = Module._load;
  Module._load = function (ist, ...r) { return ist === "vscode" ? sahte : eskiYukle.call(this, ist, ...r); };
  const e = require("../src/extension");
  Module._load = eskiYukle;
  const gizli = new Map();
  const ctx = { subscriptions: [], secrets: { get: async (k) => gizli.get(k), store: async (k, v) => gizli.set(k, v), delete: async (k) => gizli.delete(k) } };
  e.activate(ctx);
  assert.deepStrictEqual(Object.keys(komutlar).sort(), ["modelen.anahtarAyarla", "modelen.anahtarSil", "modelen.secimiSor", "modelen.sohbetAc"]);
  komutlar["modelen.sohbetAc"]();
  assert.match(sahte._html, /Content-Security-Policy/);
  assert.doesNotMatch(sahte._html, /innerHTML/);
  await iletim({ t: "hazir" });
  assert.deepStrictEqual(mesajlar[0].adlar, ["T"]);
  await iletim({ t: "sor", ad: "T", soru: "merhaba" }); // anahtar yok -> hata
  assert.strictEqual(mesajlar[mesajlar.length - 1].t, "hata");
  assert.match(mesajlar[mesajlar.length - 1].m, /anahtar yok/);
  // sayfadaki betik sözdizimi geçerli mi
  const betik = /<script nonce="[^"]+">([\s\S]*)<\/script>/.exec(sahte._html)[1];
  new Function("acquireVsCodeApi", "document", "window", betik); // yalnızca ayrıştırma
});
