"use strict";
const vscode = require("vscode");
const { sohbet } = require("./saglayici");
const { mesajlariKur, ilkKodBlogu } = require("./baglam");
const { sayfa } = require("./arayuz");

let panel = null;
let iptal = null;
let gecmis = [];

function saglayicilar() {
  return vscode.workspace.getConfiguration("modelen").get("saglayicilar") || [];
}

function anahtarAdi(ad) {
  return `modelen.anahtar.${ad}`;
}

function etkinBaglam() {
  const ed = vscode.window.activeTextEditor;
  if (!ed) return null;
  const secim = ed.selection.isEmpty ? "" : ed.document.getText(ed.selection);
  return { dosya: vscode.workspace.asRelativePath(ed.document.uri), dil: ed.document.languageId, secim, icerik: ed.document.getText() };
}

async function sorguGonder(ctx, ad, soru) {
  const ayar = saglayicilar().find((s) => s.ad === ad);
  if (!ayar) return panel.webview.postMessage({ t: "hata", m: `Sağlayıcı yok: ${ad}` });
  const anahtar = ayar.anahtarGerekir ? await ctx.secrets.get(anahtarAdi(ad)) : undefined;
  if (ayar.anahtarGerekir && !anahtar) {
    return panel.webview.postMessage({ t: "hata", m: "Bu sağlayıcı için anahtar yok. Komut paleti: 'Modelen: API anahtarı ayarla'." });
  }
  if (!ayar.model) return panel.webview.postMessage({ t: "hata", m: "Ayarlarda bu sağlayıcı için 'model' adı boş." });
  const mesajlar = mesajlariKur(gecmis, soru, etkinBaglam());
  iptal = new AbortController();
  panel.webview.postMessage({ t: "basla" });
  try {
    const maxToken = vscode.workspace.getConfiguration("modelen").get("maxToken");
    const tam = await sohbet({ ...ayar, anahtar, maxToken }, mesajlar, {
      signal: iptal.signal,
      onParca: (p) => panel && panel.webview.postMessage({ t: "parca", m: p }),
    });
    gecmis.push({ rol: "user", icerik: soru }, { rol: "assistant", icerik: tam });
    gecmis = gecmis.slice(-12);
    panel && panel.webview.postMessage({ t: "bitti", kod: ilkKodBlogu(tam) });
  } catch (e) {
    const durdu = e && e.name === "AbortError";
    panel && panel.webview.postMessage({ t: durdu ? "bitti" : "hata", m: durdu ? "" : String(e.message || e) });
  } finally {
    iptal = null;
  }
}

function paneliAc(ctx) {
  if (panel) return panel.reveal();
  panel = vscode.window.createWebviewPanel("modelenSohbet", "Modelen Kod", vscode.ViewColumn.Beside, { enableScripts: true });
  const nonce = Array.from({ length: 16 }, () => Math.floor(Math.random() * 36).toString(36)).join("");
  panel.webview.html = sayfa(nonce, panel.webview.cspSource);
  panel.onDidDispose(() => {
    panel = null;
    if (iptal) iptal.abort();
  });
  panel.webview.onDidReceiveMessage(async (m) => {
    if (m.t === "hazir") {
      const varsayilan = vscode.workspace.getConfiguration("modelen").get("varsayilan");
      panel.webview.postMessage({ t: "liste", adlar: saglayicilar().map((s) => s.ad), varsayilan });
    } else if (m.t === "sor" && typeof m.soru === "string" && m.soru.trim()) {
      await sorguGonder(ctx, String(m.ad), m.soru.trim());
    } else if (m.t === "dur" && iptal) {
      iptal.abort();
    } else if (m.t === "sifirla") {
      gecmis = [];
    } else if (m.t === "uygula" && typeof m.kod === "string") {
      // Yalnızca kullanıcı düğmeye bastığında ve yalnızca seçimi değiştirir.
      const ed = vscode.window.activeTextEditor;
      if (!ed || ed.selection.isEmpty) return vscode.window.showWarningMessage("Değiştirmek için editörde bir seçim yapın.");
      await ed.edit((b) => b.replace(ed.selection, m.kod));
    }
  });
}

function activate(ctx) {
  ctx.subscriptions.push(
    vscode.commands.registerCommand("modelen.sohbetAc", () => paneliAc(ctx)),
    vscode.commands.registerCommand("modelen.secimiSor", async () => {
      paneliAc(ctx);
      const soru = await vscode.window.showInputBox({ prompt: "Seçili kod hakkında sorunuz" });
      if (soru && panel) {
        const ad = vscode.workspace.getConfiguration("modelen").get("varsayilan");
        panel.webview.postMessage({ t: "kullanici", m: soru });
        await sorguGonder(ctx, ad, soru);
      }
    }),
    vscode.commands.registerCommand("modelen.anahtarAyarla", async () => {
      const gerekli = saglayicilar().filter((s) => s.anahtarGerekir).map((s) => s.ad);
      const ad = await vscode.window.showQuickPick(gerekli, { placeHolder: "Hangi sağlayıcı için?" });
      if (!ad) return;
      const anahtar = await vscode.window.showInputBox({ prompt: `${ad} API anahtarı`, password: true, ignoreFocusOut: true });
      if (anahtar) {
        await ctx.secrets.store(anahtarAdi(ad), anahtar);
        vscode.window.showInformationMessage("Anahtar işletim sistemi anahtar kasasına kaydedildi.");
      }
    }),
    vscode.commands.registerCommand("modelen.anahtarSil", async () => {
      const ad = await vscode.window.showQuickPick(saglayicilar().map((s) => s.ad), { placeHolder: "Hangisinin anahtarı silinsin?" });
      if (ad) await ctx.secrets.delete(anahtarAdi(ad));
    })
  );
}

function deactivate() {
  if (iptal) iptal.abort();
}

module.exports = { activate, deactivate };
