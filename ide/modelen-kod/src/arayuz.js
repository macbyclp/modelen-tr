"use strict";
// Sohbet paneli HTML'i. Model çıktısı yalnızca textContent ile yazılır (HTML enjeksiyonu yok);
// CSP: betik yalnızca nonce'lu satır içi betik.
function sayfa(nonce, kaynak) {
  return `<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${kaynak} 'unsafe-inline'; script-src 'nonce-${nonce}';">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{font:13px/1.5 var(--vscode-font-family);color:var(--vscode-foreground);margin:0;display:flex;flex-direction:column;height:100vh}
#bar{display:flex;gap:6px;padding:8px;border-bottom:1px solid var(--vscode-panel-border)}
select,textarea,button{font:inherit;color:var(--vscode-input-foreground);background:var(--vscode-input-background);border:1px solid var(--vscode-input-border,#555);border-radius:4px;padding:4px 8px}
button{cursor:pointer;background:var(--vscode-button-background);color:var(--vscode-button-foreground);border:0}
#log{flex:1;overflow:auto;padding:8px}
.m{margin:0 0 10px;padding:8px;border-radius:6px;white-space:pre-wrap;word-break:break-word}
.k{background:var(--vscode-editor-inactiveSelectionBackground)}
.a{border:1px solid var(--vscode-panel-border)}
.h{color:var(--vscode-errorForeground);border:1px solid var(--vscode-errorForeground)}
#alt{display:flex;gap:6px;padding:8px;border-top:1px solid var(--vscode-panel-border)}
#soru{flex:1;resize:none;height:56px}
</style></head><body>
<div id="bar"><select id="sag"></select><button id="uyg" disabled>Seçimi değiştir</button><button id="sif">Yeni sohbet</button></div>
<div id="log"></div>
<div id="alt"><textarea id="soru" placeholder="Sorunuzu yazın (Ctrl+Enter)"></textarea><button id="gon">Gönder</button><button id="dur" disabled>Dur</button></div>
<script nonce="${nonce}">
const v=acquireVsCodeApi();const $=i=>document.getElementById(i);let cur=null,kod=null;
function ekle(sinif,metin){const d=document.createElement('div');d.className='m '+sinif;d.textContent=metin;$('log').appendChild(d);$('log').scrollTop=1e9;return d}
function gonder(){const s=$('soru').value.trim();if(!s)return;ekle('k',s);$('soru').value='';v.postMessage({t:'sor',ad:$('sag').value,soru:s})}
$('gon').onclick=gonder;$('dur').onclick=()=>v.postMessage({t:'dur'});
$('sif').onclick=()=>{$('log').textContent='';kod=null;$('uyg').disabled=true;v.postMessage({t:'sifirla'})};
$('uyg').onclick=()=>{if(kod)v.postMessage({t:'uygula',kod})};
$('soru').addEventListener('keydown',e=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){e.preventDefault();gonder()}});
window.addEventListener('message',e=>{const m=e.data;
 if(m.t==='liste'){for(const a of m.adlar){const o=document.createElement('option');o.textContent=a;o.value=a;$('sag').appendChild(o)}if(m.adlar.includes(m.varsayilan))$('sag').value=m.varsayilan}
 else if(m.t==='kullanici')ekle('k',m.m);
 else if(m.t==='basla'){cur=ekle('a','');kod=null;$('uyg').disabled=true;$('gon').disabled=true;$('dur').disabled=false}
 else if(m.t==='parca'&&cur){cur.textContent+=m.m;$('log').scrollTop=1e9}
 else if(m.t==='bitti'){kod=m.kod||null;$('uyg').disabled=!kod;$('gon').disabled=false;$('dur').disabled=true;cur=null}
 else if(m.t==='hata'){ekle('h',m.m);$('gon').disabled=false;$('dur').disabled=true;cur=null}
});
v.postMessage({t:'hazir'});
</script></body></html>`;
}
module.exports = { sayfa };
