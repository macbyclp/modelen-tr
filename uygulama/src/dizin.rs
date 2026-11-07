//! Koordinatör dizini: admin onaylı koordinatörlerin listesi (siteden `koordinatorler.json`).
//! Onay, sitedeki listeye girişle olur; uygulama yalnızca `onayli: true` ve güvenli adresli kayıtları gösterir.

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::path::PathBuf;
use std::time::Duration;

pub const DIZIN_ADRESI: &str = "https://modelen.tr/koordinatorler.json";

#[derive(Clone, Serialize, Deserialize, PartialEq, Debug)]
pub struct Koordinator {
    pub ad: String,
    pub adres: String,
    pub aciklama: String,
}

/// Yerel deneme koordinatörü: her zaman listede, internet gerekmez.
pub fn yerel_test() -> Koordinator {
    Koordinator { ad: "Yerel test".into(), adres: "http://127.0.0.1:8750".into(), aciklama: "Bu bilgisayarda deneme koordinatörü".into() }
}

/// Adres güvenli mi: https, ya da yalnızca yerel makine için http.
fn adres_gecerli(a: &str) -> bool {
    if a.len() > 200 || a.contains(char::is_whitespace) {
        return false;
    }
    a.starts_with("https://") && a.len() > 10 || a.starts_with("http://127.0.0.1:") || a.starts_with("http://localhost:")
}

/// JSON gövdesini (`{"koordinatorler":[{ad,adres,aciklama,onayli}]}`) doğrulanmış listeye çevirir.
pub fn ayikla(v: &Value) -> Vec<Koordinator> {
    let Some(dizi) = v["koordinatorler"].as_array() else { return vec![] };
    let mut cikti: Vec<Koordinator> = vec![];
    for k in dizi {
        let ad = k["ad"].as_str().unwrap_or("").trim();
        let adres = k["adres"].as_str().unwrap_or("").trim().trim_end_matches('/');
        let aciklama = k["aciklama"].as_str().unwrap_or("").trim();
        if k["onayli"].as_bool() != Some(true) || ad.is_empty() || ad.chars().count() > 60 || aciklama.chars().count() > 200 || !adres_gecerli(adres) {
            continue;
        }
        if cikti.iter().any(|c| c.adres == adres) {
            continue;
        }
        cikti.push(Koordinator { ad: ad.into(), adres: adres.into(), aciklama: aciklama.into() });
    }
    cikti
}

pub fn getir(adres: &str) -> Result<Vec<Koordinator>, String> {
    let ajan = ureq::AgentBuilder::new().timeout(Duration::from_secs(6)).build();
    let v: Value = ajan.get(adres).call().map_err(|e| e.to_string())?.into_json().map_err(|e| e.to_string())?;
    Ok(ayikla(&v))
}

fn onbellek_yolu() -> PathBuf {
    let taban = std::env::var("APPDATA").map(PathBuf::from).unwrap_or_else(|_| PathBuf::from("."));
    taban.join("Modelen").join("dizin.json")
}

pub fn onbellekten_oku() -> Vec<Koordinator> {
    std::fs::read_to_string(onbellek_yolu()).ok().and_then(|s| serde_json::from_str(&s).ok()).unwrap_or_default()
}

pub fn onbellege_yaz(l: &[Koordinator]) {
    let p = onbellek_yolu();
    if let Some(d) = p.parent() {
        let _ = std::fs::create_dir_all(d);
    }
    let _ = std::fs::write(p, serde_json::to_string_pretty(l).unwrap_or_default());
}

/// Gösterilecek liste: yerel test + (varsa) onaylı koordinatörler.
pub fn birlestir(uzak: &[Koordinator]) -> Vec<Koordinator> {
    let mut l = uzak.to_vec();
    let y = yerel_test();
    if !l.iter().any(|k| k.adres == y.adres) {
        l.push(y);
    }
    l
}

#[cfg(test)]
mod testler {
    use super::*;

    #[test]
    fn yalniz_onayli_ve_guvenli_adresler() {
        let v: Value = serde_json::from_str(
            r#"{"koordinatorler":[
              {"ad":"Ali Lab","adres":"https://koord.ornek.org/","aciklama":"Türkçe LoRA","onayli":true},
              {"ad":"Onaysız","adres":"https://x.org","aciklama":"","onayli":false},
              {"ad":"Düz http","adres":"http://x.org","aciklama":"","onayli":true},
              {"ad":"Yerel","adres":"http://127.0.0.1:9000","aciklama":"test","onayli":true},
              {"ad":"Tekrar","adres":"https://koord.ornek.org","aciklama":"","onayli":true},
              {"ad":"","adres":"https://y.org","aciklama":"","onayli":true},
              {"ad":"Boşluklu","adres":"https://y .org","aciklama":"","onayli":true}
            ]}"#,
        )
        .unwrap();
        let l = ayikla(&v);
        let adlar: Vec<&str> = l.iter().map(|k| k.ad.as_str()).collect();
        assert_eq!(adlar, ["Ali Lab", "Yerel"]);
        assert_eq!(l[0].adres, "https://koord.ornek.org");
    }

    #[test]
    fn bozuk_json_bos_liste_verir() {
        assert!(ayikla(&serde_json::json!({"x": 1})).is_empty());
        assert!(ayikla(&serde_json::json!({"koordinatorler": "yok"})).is_empty());
    }

    #[test]
    fn yerel_test_her_zaman_listede() {
        let l = birlestir(&[]);
        assert_eq!(l.len(), 1);
        assert_eq!(l[0].adres, "http://127.0.0.1:8750");
        assert_eq!(birlestir(&l).len(), 1);
    }
}
