//! Sağlayıcı katmanı: OpenAI uyumlu ve Anthropic akışlı sohbet. Anahtar çağıran tarafından verilir;
//! bu modül anahtarı kaydetmez ya da günlüğe yazmaz.

use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::io::{BufRead, BufReader, Read};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Duration;

#[derive(Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Debug)]
#[serde(rename_all = "lowercase")]
pub enum Tur {
    Openai,
    Anthropic,
}

#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct Saglayici {
    pub ad: String,
    pub tur: Tur,
    pub adres: String,
    pub model: String,
    pub anahtar_gerekir: bool,
}

#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct Mesaj {
    pub rol: String, // system | user | assistant
    pub icerik: String,
}

pub enum Olay {
    Parca(String),
    Bitti,
    Hata(String),
}

pub fn varsayilanlar() -> Vec<Saglayici> {
    let s = |ad: &str, tur, adres: &str, model: &str, a| Saglayici {
        ad: ad.into(),
        tur,
        adres: adres.into(),
        model: model.into(),
        anahtar_gerekir: a,
    };
    vec![
        s("Modelen (yerel)", Tur::Openai, "http://127.0.0.1:8760/v1", "modelen-qwen3-0.6b", false),
        s("Ollama (yerel)", Tur::Openai, "http://127.0.0.1:11434/v1", "qwen3:4b-instruct-2507-q4_K_M", false),
        s("OpenAI uyumlu (bulut)", Tur::Openai, "https://api.openai.com/v1", "", true),
        s("Anthropic", Tur::Anthropic, "https://api.anthropic.com", "", true),
    ]
}

fn bosluk_kes(s: &str) -> &str {
    s.trim_end_matches('/')
}

/// SSE satırından "data:" yükünü çıkarır.
pub fn sse_yuk(satir: &str) -> Option<&str> {
    let s = satir.trim_end_matches('\r');
    let y = s.strip_prefix("data:")?.trim();
    if y.is_empty() {
        None
    } else {
        Some(y)
    }
}

/// Bir SSE yükünden metin parçasını çıkarır. `Err` = akış içi hata.
pub fn parca_cikar(tur: Tur, yuk: &str) -> Result<Option<String>, String> {
    if yuk == "[DONE]" {
        return Ok(None);
    }
    let Ok(j) = serde_json::from_str::<Value>(yuk) else {
        return Ok(None); // bozuk satırı yok say
    };
    match tur {
        Tur::Openai => Ok(j["choices"][0]["delta"]["content"].as_str().filter(|s| !s.is_empty()).map(String::from)),
        Tur::Anthropic => {
            if j["type"] == "error" {
                return Err(j["error"]["message"].as_str().unwrap_or("akış hatası").to_string());
            }
            if j["type"] == "content_block_delta" && j["delta"]["type"] == "text_delta" {
                return Ok(j["delta"]["text"].as_str().map(String::from));
            }
            Ok(None)
        }
    }
}

pub fn istek_govdesi(s: &Saglayici, mesajlar: &[Mesaj], max_token: u32) -> Value {
    match s.tur {
        Tur::Openai => json!({
            "model": s.model, "stream": true, "max_tokens": max_token, "temperature": 0.2,
            "messages": mesajlar.iter().map(|m| json!({"role": m.rol, "content": m.icerik})).collect::<Vec<_>>(),
        }),
        Tur::Anthropic => {
            let sistem: Vec<&str> = mesajlar.iter().filter(|m| m.rol == "system").map(|m| m.icerik.as_str()).collect();
            let mut g = json!({
                "model": s.model, "stream": true, "max_tokens": max_token,
                "messages": mesajlar.iter().filter(|m| m.rol != "system")
                    .map(|m| json!({"role": m.rol, "content": m.icerik})).collect::<Vec<_>>(),
            });
            if !sistem.is_empty() {
                g["system"] = Value::String(sistem.join("\n\n"));
            }
            g
        }
    }
}

/// Akışlı sohbet; her olayda `cb` çağrılır. Bloklar, bu yüzden bir iş parçacığında çalıştırın.
pub fn sohbet(
    s: &Saglayici,
    anahtar: Option<&str>,
    mesajlar: &[Mesaj],
    max_token: u32,
    iptal: &Arc<AtomicBool>,
    mut cb: impl FnMut(Olay),
) {
    if s.adres.is_empty() {
        return cb(Olay::Hata("sağlayıcı adresi boş".into()));
    }
    if s.model.is_empty() {
        return cb(Olay::Hata("model adı boş (Ayarlar sekmesinden girin)".into()));
    }
    let adres = bosluk_kes(&s.adres);
    let agent = ureq::AgentBuilder::new()
        .timeout_connect(Duration::from_secs(10))
        .timeout_read(Duration::from_secs(180))
        .build();
    let mut istek = match s.tur {
        Tur::Openai => agent.post(&format!("{adres}/chat/completions")),
        Tur::Anthropic => agent.post(&format!("{adres}/v1/messages")).set("anthropic-version", "2023-06-01"),
    };
    if let Some(a) = anahtar.filter(|a| !a.is_empty()) {
        istek = match s.tur {
            Tur::Openai => istek.set("Authorization", &format!("Bearer {a}")),
            Tur::Anthropic => istek.set("x-api-key", a),
        };
    }
    let yanit = match istek.send_json(istek_govdesi(s, mesajlar, max_token)) {
        Ok(y) => y,
        Err(ureq::Error::Status(kod, y)) => {
            let mut g = String::new();
            let _ = y.into_reader().take(400).read_to_string(&mut g);
            return cb(Olay::Hata(format!("HTTP {kod}: {g}")));
        }
        Err(e) => return cb(Olay::Hata(format!("bağlantı hatası: {e}"))),
    };
    for satir in BufReader::new(yanit.into_reader()).lines() {
        if iptal.load(Ordering::Relaxed) {
            return cb(Olay::Bitti);
        }
        let Ok(satir) = satir else {
            return cb(Olay::Hata("akış koptu".into()));
        };
        if let Some(yuk) = sse_yuk(&satir) {
            match parca_cikar(s.tur, yuk) {
                Ok(Some(p)) => cb(Olay::Parca(p)),
                Ok(None) => {}
                Err(e) => return cb(Olay::Hata(e)),
            }
        }
    }
    cb(Olay::Bitti);
}

pub const SISTEM: &str = "Sen Modelen Kod'sun: Türkçe konuşan, kısa ve doğru cevap veren bir kodlama yardımcısı. \
Emin olmadığın şeyi uydurma, bilmiyorsan söyle. Kod verirken tek bir kod bloğu kullan ve dilini etiketle.";
const EN_COK_BAGLAM: usize = 12_000;

fn kirp(s: &str, sinir: usize) -> String {
    let n = s.chars().count();
    if n <= sinir {
        return s.to_string();
    }
    let y = sinir / 2;
    let bas: String = s.chars().take(y).collect();
    let son: String = s.chars().skip(n - y).collect();
    format!("{bas}\n/* … kırpıldı … */\n{son}")
}

/// Soru + (seçim ya da dosya) bağlamı ile mesaj listesini kurar.
pub fn mesajlari_kur(gecmis: &[Mesaj], soru: &str, dosya: &str, dil: &str, secim: &str, icerik: &str) -> Vec<Mesaj> {
    let mut m = vec![Mesaj { rol: "system".into(), icerik: SISTEM.into() }];
    m.extend(gecmis.iter().filter(|x| x.rol != "system").cloned());
    let (tur, parca) = if !secim.is_empty() {
        ("Seçili kod", kirp(secim, EN_COK_BAGLAM))
    } else if !icerik.is_empty() {
        ("Açık dosya", kirp(icerik, EN_COK_BAGLAM))
    } else {
        ("", String::new())
    };
    let kullanici = if parca.is_empty() {
        soru.to_string()
    } else {
        format!("{soru}\n\n[{tur}: {dosya}]\n```{dil}\n{parca}\n```")
    };
    m.push(Mesaj { rol: "user".into(), icerik: kullanici });
    m
}

/// Cevaptaki ilk kod bloğunun içeriği.
pub fn ilk_kod_blogu(metin: &str) -> Option<String> {
    let bas = metin.find("```")?;
    let sonra = &metin[bas + 3..];
    let satir_sonu = sonra.find('\n')?;
    let govde = &sonra[satir_sonu + 1..];
    let bit = govde.find("```")?;
    Some(govde[..bit].trim_end_matches('\n').to_string())
}

#[cfg(test)]
mod testler {
    use super::*;
    use std::io::Write;
    use std::net::TcpListener;
    use std::thread;

    /// Tek bağlantılık sahte sunucu: gelen isteği (başlık+gövde) döndürür, verilen yanıtı yazar.
    fn sahte(yanit: &'static str) -> (String, thread::JoinHandle<String>) {
        let l = TcpListener::bind("127.0.0.1:0").unwrap();
        let adres = format!("http://{}", l.local_addr().unwrap());
        let h = thread::spawn(move || {
            let (mut s, _) = l.accept().unwrap();
            let mut tampon = vec![0u8; 65536];
            let mut toplam = Vec::new();
            loop {
                let n = std::io::Read::read(&mut s, &mut tampon).unwrap();
                toplam.extend_from_slice(&tampon[..n]);
                let metin = String::from_utf8_lossy(&toplam).to_string();
                if let Some(i) = metin.find("\r\n\r\n") {
                    let uzun = metin[..i]
                        .lines()
                        .find_map(|l| l.to_ascii_lowercase().strip_prefix("content-length:").map(|v| v.trim().parse::<usize>().unwrap()))
                        .unwrap_or(0);
                    if toplam.len() >= i + 4 + uzun {
                        break;
                    }
                }
            }
            write!(s, "HTTP/1.1 {yanit}").unwrap();
            s.flush().unwrap();
            String::from_utf8_lossy(&toplam).to_string()
        });
        (adres, h)
    }

    fn sag(tur: Tur, adres: &str) -> Saglayici {
        Saglayici { ad: "t".into(), tur, adres: adres.into(), model: "m".into(), anahtar_gerekir: false }
    }

    fn calistir(s: &Saglayici, anahtar: Option<&str>) -> (String, Option<String>) {
        let iptal = Arc::new(AtomicBool::new(false));
        let (mut tam, mut hata) = (String::new(), None);
        sohbet(s, anahtar, &[Mesaj { rol: "user".into(), icerik: "selam".into() }], 64, &iptal, |o| match o {
            Olay::Parca(p) => tam.push_str(&p),
            Olay::Hata(e) => hata = Some(e),
            Olay::Bitti => {}
        });
        (tam, hata)
    }

    #[test]
    fn openai_akis_ve_basliklar() {
        let govde = "data: {\"choices\":[{\"delta\":{\"content\":\"Mer\"}}]}\n\ndata: {\"choices\":[{\"delta\":{\"content\":\"haba\"}}]}\n\ndata: [DONE]\n\n";
        let yanit: &'static str = Box::leak(format!("200 OK\r\nContent-Type: text/event-stream\r\nConnection: close\r\n\r\n{govde}").into_boxed_str());
        let (adres, h) = sahte(yanit);
        let (tam, hata) = calistir(&sag(Tur::Openai, &format!("{adres}/v1/")), Some("gizli"));
        let ist = h.join().unwrap();
        assert_eq!(hata, None);
        assert_eq!(tam, "Merhaba");
        assert!(ist.starts_with("POST /v1/chat/completions"), "{ist}");
        assert!(ist.to_lowercase().contains("authorization: bearer gizli"));
        assert!(ist.contains("\"stream\":true"));
    }

    #[test]
    fn anthropic_akis_sistem_ayrilir() {
        let govde = "event: content_block_delta\ndata: {\"type\":\"content_block_delta\",\"delta\":{\"type\":\"text_delta\",\"text\":\"Sel\"}}\n\nevent: ping\ndata: {\"type\":\"ping\"}\n\ndata: {\"type\":\"content_block_delta\",\"delta\":{\"type\":\"text_delta\",\"text\":\"am\"}}\n\n";
        let yanit: &'static str = Box::leak(format!("200 OK\r\nConnection: close\r\n\r\n{govde}").into_boxed_str());
        let (adres, h) = sahte(yanit);
        let s = sag(Tur::Anthropic, &adres);
        let iptal = Arc::new(AtomicBool::new(false));
        let mut tam = String::new();
        let mesajlar = [
            Mesaj { rol: "system".into(), icerik: "S".into() },
            Mesaj { rol: "user".into(), icerik: "U".into() },
        ];
        sohbet(&s, Some("k1"), &mesajlar, 64, &iptal, |o| {
            if let Olay::Parca(p) = o {
                tam.push_str(&p)
            }
        });
        let ist = h.join().unwrap();
        assert_eq!(tam, "Selam");
        assert!(ist.starts_with("POST /v1/messages"));
        assert!(ist.to_lowercase().contains("x-api-key: k1"));
        assert!(ist.to_lowercase().contains("anthropic-version: 2023-06-01"));
        assert!(ist.contains("\"system\":\"S\""));
    }

    #[test]
    fn http_hatasi_govdeyi_tasir() {
        let (adres, _h) = sahte("401 Unauthorized\r\nContent-Length: 22\r\nConnection: close\r\n\r\n{\"error\":\"kötü anahtar\"}");
        let (_, hata) = calistir(&sag(Tur::Openai, &adres), None);
        let h = hata.expect("hata beklenir");
        assert!(h.contains("401"), "{h}");
    }

    #[test]
    fn anahtarsiz_istekte_yetki_basligi_yok() {
        let yanit: &'static str = "200 OK\r\nConnection: close\r\n\r\ndata: [DONE]\n\n";
        let (adres, h) = sahte(yanit);
        let _ = calistir(&sag(Tur::Openai, &adres), None);
        assert!(!h.join().unwrap().to_lowercase().contains("authorization"));
    }

    #[test]
    fn bos_model_ve_adres_reddedilir() {
        let mut s = sag(Tur::Openai, "http://x");
        s.model.clear();
        assert!(calistir(&s, None).1.unwrap().contains("model adı boş"));
        let mut s = sag(Tur::Openai, "");
        s.model = "m".into();
        assert!(calistir(&s, None).1.unwrap().contains("adresi boş"));
    }

    #[test]
    fn ayristirma_bozuk_satiri_yok_sayar() {
        assert_eq!(parca_cikar(Tur::Openai, "{bozuk").unwrap(), None);
        assert_eq!(parca_cikar(Tur::Openai, "[DONE]").unwrap(), None);
        assert!(parca_cikar(Tur::Anthropic, "{\"type\":\"error\",\"error\":{\"message\":\"x\"}}").is_err());
        assert_eq!(sse_yuk("data: {\"a\":1}\r"), Some("{\"a\":1}"));
        assert_eq!(sse_yuk("event: ping"), None);
    }

    #[test]
    fn baglam_ve_kod_blogu() {
        let g = [Mesaj { rol: "user".into(), icerik: "a".into() }, Mesaj { rol: "assistant".into(), icerik: "b".into() }];
        let m = mesajlari_kur(&g, "bu ne?", "x.py", "python", "print(1)", "TAM");
        assert_eq!(m.len(), 4);
        assert!(m[3].icerik.contains("Seçili kod: x.py"));
        assert!(!m[3].icerik.contains("TAM"));
        let u = mesajlari_kur(&[], "s", "u", "", "", &"z".repeat(50_000));
        assert!(u[1].icerik.chars().count() < 13_000 && u[1].icerik.contains("kırpıldı"));
        assert_eq!(mesajlari_kur(&[], "yalın", "", "", "", "")[1].icerik, "yalın");
        assert_eq!(ilk_kod_blogu("a\n```js\nlet x=1;\n```\nb"), Some("let x=1;".into()));
        assert_eq!(ilk_kod_blogu("kod yok"), None);
    }
}

#[cfg(test)]
mod canli {
    use super::*;

    /// Çalışan yerel Modelen sunucusuna (127.0.0.1:8760) bağlanır. Sunucu yoksa atlanır.
    /// Çalıştırma: cargo test canli -- --ignored --nocapture
    #[test]
    #[ignore]
    fn yerel_modelen_sunucusu() {
        let s = varsayilanlar().remove(0);
        let iptal = Arc::new(AtomicBool::new(false));
        let (mut parca, mut tam, mut hata) = (0, String::new(), None);
        sohbet(&s, None, &[Mesaj { rol: "user".into(), icerik: "Merhaba, nasılsın?".into() }], 40, &iptal, |o| match o {
            Olay::Parca(p) => {
                parca += 1;
                tam.push_str(&p)
            }
            Olay::Hata(e) => hata = Some(e),
            Olay::Bitti => {}
        });
        println!("parça={parca} hata={hata:?}\n{tam}");
        assert!(hata.is_none(), "{hata:?}");
        assert!(parca > 0);
    }
}
