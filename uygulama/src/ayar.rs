//! Ayarlar (JSON, %APPDATA%\Modelen) ve API anahtarları (işletim sistemi kimlik kasası; dosyaya yazılmaz).

use crate::saglayici::{varsayilanlar, Saglayici};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

#[derive(Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct Ayarlar {
    pub saglayicilar: Vec<Saglayici>,
    pub secili: usize,
    pub max_token: u32,
    /// Modelen proje klasörü (içinde istemci/isci.py ve sunucu/modelen_sunucu.py olmalı)
    pub modelen_klasoru: String,
    pub python: String,
    pub koordinator: String,
    pub takma_ad: String,
    pub adaptor: String,
    pub calisma_klasoru: String,
    /// Açılışta tek sayfalık kolay mod
    pub kolay_mod: bool,
    /// Onaylı koordinatör listesinin adresi (site)
    pub dizin_adresi: String,
}

impl Default for Ayarlar {
    fn default() -> Self {
        let klasor = klasor_bul().unwrap_or_default();
        let py = Path::new(&klasor).join(".venv").join("Scripts").join("python.exe");
        Ayarlar {
            saglayicilar: varsayilanlar(),
            secili: 0,
            max_token: 1024,
            python: if py.exists() { py.to_string_lossy().into_owned() } else { "python".into() },
            modelen_klasoru: klasor,
            koordinator: "http://127.0.0.1:8750".into(),
            takma_ad: "gonullu".into(),
            adaptor: String::new(),
            calisma_klasoru: String::new(),
            kolay_mod: true,
            dizin_adresi: crate::dizin::DIZIN_ADRESI.into(),
        }
    }
}

/// Çalışan exe'nin üst klasörlerinde ya da MODELEN_KLASORU'nde istemci/isci.py arar.
fn klasor_bul() -> Option<String> {
    let mut adaylar: Vec<PathBuf> = Vec::new();
    if let Ok(v) = std::env::var("MODELEN_KLASORU") {
        adaylar.push(v.into());
    }
    if let Ok(exe) = std::env::current_exe() {
        adaylar.extend(exe.ancestors().map(Path::to_path_buf));
    }
    if let Ok(cwd) = std::env::current_dir() {
        adaylar.extend(cwd.ancestors().map(Path::to_path_buf));
    }
    adaylar.into_iter().find(|p| p.join("istemci").join("isci.py").exists()).map(|p| p.to_string_lossy().into_owned())
}

fn yol() -> PathBuf {
    let taban = std::env::var("APPDATA").map(PathBuf::from).unwrap_or_else(|_| PathBuf::from("."));
    taban.join("Modelen").join("ayarlar.json")
}

pub fn yukle() -> Ayarlar {
    let mut a: Ayarlar = std::fs::read_to_string(yol()).ok().and_then(|s| serde_json::from_str(&s).ok()).unwrap_or_default();
    if a.saglayicilar.is_empty() {
        a.saglayicilar = varsayilanlar();
    }
    a.secili = a.secili.min(a.saglayicilar.len() - 1);
    a
}

pub fn kaydet(a: &Ayarlar) -> Result<(), String> {
    let p = yol();
    if let Some(d) = p.parent() {
        std::fs::create_dir_all(d).map_err(|e| e.to_string())?;
    }
    std::fs::write(p, serde_json::to_string_pretty(a).map_err(|e| e.to_string())?).map_err(|e| e.to_string())
}

fn giris(ad: &str) -> Result<keyring::Entry, String> {
    keyring::Entry::new("modelen-uygulama", ad).map_err(|e| e.to_string())
}

pub fn anahtar_oku(ad: &str) -> Option<String> {
    giris(ad).ok()?.get_password().ok().filter(|s| !s.is_empty())
}

pub fn anahtar_yaz(ad: &str, deger: &str) -> Result<(), String> {
    giris(ad)?.set_password(deger).map_err(|e| e.to_string())
}

pub fn anahtar_sil(ad: &str) -> Result<(), String> {
    giris(ad)?.delete_credential().map_err(|e| e.to_string())
}
