"use strict";
// Modele gidecek mesajları kurar. Saf fonksiyonlar; VS Code'a bağımlı değil (test edilebilir).

const SISTEM =
  "Sen Modelen Kod'sun: Türkçe konuşan, kısa ve doğru cevap veren bir kodlama yardımcısı. " +
  "Emin olmadığın şeyi uydurma, bilmiyorsan söyle. Kod verirken tek bir kod bloğu kullan ve dilini etiketle.";

const EN_COK_BAGLAM = 12000; // karakter; model bağlamını taşırmamak için

function kirp(metin, sinir) {
  if (metin.length <= sinir) return metin;
  const yarim = Math.floor(sinir / 2);
  return metin.slice(0, yarim) + "\n/* … kırpıldı … */\n" + metin.slice(metin.length - yarim);
}

// gecmis: [{rol, icerik}], soru: string, baglam: {dosya?, dil?, secim?, icerik?}
function mesajlariKur(gecmis, soru, baglam) {
  const mesajlar = [{ rol: "system", icerik: SISTEM }];
  for (const m of gecmis || []) mesajlar.push({ rol: m.rol, icerik: m.icerik });
  let kullanici = soru;
  if (baglam && (baglam.secim || baglam.icerik)) {
    const parca = baglam.secim ? kirp(baglam.secim, EN_COK_BAGLAM) : kirp(baglam.icerik, EN_COK_BAGLAM);
    const tur = baglam.secim ? "Seçili kod" : "Açık dosya";
    kullanici =
      `${soru}\n\n[${tur}: ${baglam.dosya || "adsız"}]\n` + "```" + (baglam.dil || "") + "\n" + parca + "\n```";
  }
  mesajlar.push({ rol: "user", icerik: kullanici });
  return mesajlar;
}

// Cevaptaki ilk kod bloğunu çıkarır ("Seçimi değiştir" düğmesi için). Yoksa null.
function ilkKodBlogu(metin) {
  const e = /```[^\n`]*\n([\s\S]*?)```/.exec(metin || "");
  return e ? e[1].replace(/\n$/, "") : null;
}

module.exports = { mesajlariKur, ilkKodBlogu, SISTEM };
